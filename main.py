import os
import logging
from contextlib import asynccontextmanager
from typing import Optional
import tempfile

from fastapi import FastAPI, HTTPException, status, Depends, Header, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from models import (
    DownloadRequest,
    DownloadResponse,
    FormatsListResponse,
    HealthResponse,
    ErrorResponse,
    ResponseType,
    StorageProvider
)
from downloader import VideoDownloader

# Configure logging (only if not already configured)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger(__name__)

# Global downloader instance
downloader: Optional[VideoDownloader] = None

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Authentication password from environment
API_PASSWORD = os.getenv("API_PASSWORD", "")
if not API_PASSWORD:
    logger.warning("API_PASSWORD not set in environment. Authentication disabled.")


async def verify_password(x_api_key: str = Header(..., alias="X-API-Key")):
    """
    Verify API password from header.
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Raises:
        HTTPException: If password is incorrect or not set
    """
    if not API_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API password not configured. Set API_PASSWORD environment variable."
        )
    
    if x_api_key != API_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API password"
        )
    
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global downloader

    # Startup
    output_dir = os.getenv("OUTPUT_DIR", os.path.join(tempfile.gettempdir(), "yt_downloads"))
    downloader = VideoDownloader(output_dir=output_dir)

    # Start cleanup task
    downloader.start_cleanup_task()

    logger.info(f"Application started. Output directory: {output_dir}")

    yield

    # Shutdown
    if downloader:
        downloader.stop_cleanup_task()
        logger.info("Application shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="YouTube Download API",
    description="REST API for downloading YouTube videos with yt-dlp",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_mime_type(filename: str) -> str:
    """
    Get MIME type based on file extension.
    
    Args:
        filename: Filename with extension
        
    Returns:
        MIME type string
    """
    extension = os.path.splitext(filename)[1].lower()
    
    mime_types = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.mkv': 'video/x-matroska',
        '.flv': 'video/x-flv',
        '.avi': 'video/x-msvideo',
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
        '.opus': 'audio/opus',
        '.ogg': 'audio/ogg',
        '.flac': 'audio/flac',
        '.wav': 'audio/wav',
    }
    
    return mime_types.get(extension, 'application/octet-stream')


def file_iterator(filepath: str, chunk_size: int = 8192):
    """
    Generator to stream file in chunks.
    
    Args:
        filepath: Path to file
        chunk_size: Size of chunks to read
        
    Yields:
        File chunks
    """
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(chunk_size):
                yield chunk
    finally:
        # Clean up the file after streaming
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"Cleaned up temporary file: {filepath}")
            except Exception as e:
                logger.error(f"Failed to cleanup file {filepath}: {str(e)}")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "YouTube Download API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "download": "/download (POST)",
            "formats": "/formats?url={video_url} (GET)"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify service status and dependencies.
    """
    ytdlp_available = False

    # Check yt-dlp
    try:
        import yt_dlp
        ytdlp_available = True
    except ImportError:
        logger.warning("yt-dlp not available")

    if not ytdlp_available:
        return HealthResponse(
            status="unhealthy",
            message="No download backend available",
            ytdlp_available=False
        )

    return HealthResponse(
        status="healthy",
        message="Service is running",
        ytdlp_available=ytdlp_available
    )


@app.post("/download", tags=["Download"])
@limiter.limit(os.getenv("RATE_LIMIT", "10/minute"))
async def download_video(
    request: Request,
    download_request: DownloadRequest,
    verified: bool = Depends(verify_password)
):
    """
    Download a YouTube video or audio.
    
    - **video_url**: YouTube video URL (required)
    - **format_type**: "video" or "audio" (default: "video")
    - **quality**: Video quality like "best", "720p", "1080p" (default: "best")
    - **video_format**: Video container format like "mp4", "webm" (default: "mp4")
    - **audio_format**: Audio format like "mp3", "m4a" (default: "mp3")
    - **audio_quality**: Audio bitrate like "128k", "192k", "320k" (default: "192k")
    - **response_type**: "binary" or "filepath" (default: "binary")
    - **storage_provider**: "supabase", "s3", or "filepath" (optional, uploads to cloud if specified)
    - **download_subtitles**: Whether to download subtitles (default: false)
    - **embed_subtitles**: Whether to embed subtitles (default: false)
    - **subtitle_language**: Subtitle language code (default: "en")
    
    Returns either a binary stream (default), file path information, or public URL if storage_provider is set.
    """
    global downloader
    
    if not downloader:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Downloader not initialized"
        )
    
    try:
        # Download the video
        result = downloader.download(download_request)

        if download_request.response_type == ResponseType.BINARY:
            # Stream the file as binary response
            filepath = result['filepath']
            filename = result['filename']
            
            if not os.path.exists(filepath):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Downloaded file not found: {filepath}"
                )
            
            mime_type = get_mime_type(filename)
            
            return StreamingResponse(
                file_iterator(filepath),
                media_type=mime_type,
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
            )
        else:
            # Handle storage provider if specified
            public_url = None
            filepath = result['filepath']
            filename = result['filename']
            
            if download_request.storage_provider:
                if download_request.storage_provider == StorageProvider.FILEPATH:
                    # Return local filepath (existing behavior)
                    return DownloadResponse(
                        success=True,
                        message="Download completed successfully",
                        filepath=filepath,
                        filename=filename,
                        file_size=result['file_size']
                    )
                else:
                    # Upload to cloud storage (Supabase or S3)
                    try:
                        public_url = downloader.upload_to_storage(
                            filepath,
                            filename,
                            download_request.storage_provider
                        )
                        logger.info(f"File uploaded to {download_request.storage_provider.value}: {public_url}")
                        
                        return DownloadResponse(
                            success=True,
                            message=f"Download completed and uploaded to {download_request.storage_provider.value}",
                            filename=filename,
                            file_size=result['file_size'],
                            public_url=public_url
                        )
                    except Exception as upload_error:
                        logger.error(f"Upload to {download_request.storage_provider.value} failed: {str(upload_error)}")
                        # Fallback to returning local filepath if upload fails
                        return DownloadResponse(
                            success=True,
                            message=f"Download completed but upload failed: {str(upload_error)}",
                            filepath=filepath,
                            filename=filename,
                            file_size=result['file_size']
                        )
            else:
                # Return local filepath (no storage provider specified)
                return DownloadResponse(
                    success=True,
                    message="Download completed successfully",
                    filepath=filepath,
                    filename=filename,
                    file_size=result['file_size']
                )
            
    except ValueError as e:
        # Validation errors
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Other errors
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {str(e)}"
        )


@app.get("/formats", response_model=FormatsListResponse, tags=["Information"])
@limiter.limit(os.getenv("RATE_LIMIT", "30/minute"))
async def get_video_formats(
    request: Request,
    url: str,
    verified: bool = Depends(verify_password)
):
    """
    Get available formats for a YouTube video.
    
    - **url**: YouTube video URL (required)
    
    Returns video information and list of available formats.
    Useful for checking what qualities and formats are available before downloading.
    """
    global downloader
    
    if not downloader:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Downloader not initialized"
        )
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL parameter is required"
        )
    
    try:
        result = downloader.get_video_formats(url)
        
        return FormatsListResponse(
            success=result['success'],
            video_id=result['video_id'],
            title=result['title'],
            formats=result['formats'],
            thumbnail=result.get('thumbnail'),
            duration=result.get('duration'),
            uploader=result.get('uploader')
        )
        
    except Exception as e:
        logger.error(f"Format extraction error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract formats: {str(e)}"
        )


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with consistent error response format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error=exc.detail,
            details=None
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error="Internal server error",
            details=str(exc)
        ).model_dump()
    )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    # Disable reload in production/Docker environments
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port} (reload={reload})")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

