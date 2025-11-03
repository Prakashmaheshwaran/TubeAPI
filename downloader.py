import os
import tempfile
import logging
import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import yt_dlp
from pytube import YouTube
from models import (
    DownloadRequest,
    FormatType,
    VideoQuality,
    VideoFormat,
    AudioFormat,
    AudioQuality,
    FormatInfo,
    StorageProvider
)
from storage import SupabaseUploader, S3Uploader

# Configure logging (only if not already configured)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger(__name__)


class VideoDownloader:
    """
    YouTube video downloader with yt-dlp primary and pytube fallback.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the downloader.

        Args:
            output_dir: Directory to save downloads. Defaults to temp directory.
        """
        self.output_dir = output_dir or tempfile.gettempdir()
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"VideoDownloader initialized with output_dir: {self.output_dir}")

        # Cleanup configuration
        self.cleanup_enabled = os.getenv("CLEANUP_ENABLED", "true").lower() == "true"
        self.cleanup_interval = int(os.getenv("CLEANUP_INTERVAL_MINUTES", "60"))  # Default: 1 hour
        self.max_file_age_hours = int(os.getenv("MAX_FILE_AGE_HOURS", "24"))  # Default: 24 hours
        self.max_storage_mb = int(os.getenv("MAX_STORAGE_MB", "1024"))  # Default: 1GB
        self.cleanup_task: Optional[asyncio.Task] = None

        # Initialize storage uploaders
        self.supabase_uploader = SupabaseUploader()
        self.s3_uploader = S3Uploader()

        logger.info(f"Cleanup configured: enabled={self.cleanup_enabled}, interval={self.cleanup_interval}min, "
                   f"max_age={self.max_file_age_hours}h, max_storage={self.max_storage_mb}MB")
    
    def _get_quality_format(self, quality: VideoQuality, video_format: VideoFormat) -> str:
        """
        Convert quality enum to yt-dlp format string.
        
        Args:
            quality: Video quality enum
            video_format: Video format enum
            
        Returns:
            yt-dlp format string
        """
        if quality == VideoQuality.BEST:
            return f"bestvideo[ext={video_format.value}]+bestaudio/best[ext={video_format.value}]/best"
        elif quality == VideoQuality.WORST:
            return f"worstvideo[ext={video_format.value}]+worstaudio/worst[ext={video_format.value}]/worst"
        else:
            # Extract height from quality (e.g., "720p" -> "720")
            height = quality.value.replace("p", "")
            return f"bestvideo[height<={height}][ext={video_format.value}]+bestaudio/best[height<={height}]/best"
    
    def download_with_ytdlp(self, request: DownloadRequest) -> Dict[str, Any]:
        """
        Download video using yt-dlp.
        
        Args:
            request: Download request parameters
            
        Returns:
            Dictionary with download results
            
        Raises:
            Exception: If download fails
        """
        logger.info(f"Attempting download with yt-dlp for URL: {request.video_url}")
        
        # Base output template
        output_template = os.path.join(self.output_dir, "%(title)s.%(ext)s")
        
        # Build ydl_opts based on request
        ydl_opts = {
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
        }
        
        if request.format_type == FormatType.AUDIO:
            # Audio-only download
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': request.audio_format.value,
                'preferredquality': request.audio_quality.value.replace('k', ''),
            }]
        else:
            # Video download
            format_string = self._get_quality_format(request.quality, request.video_format)
            ydl_opts['format'] = format_string
            
            # Post-processor to merge video and audio
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': request.video_format.value,
            }]
            
            # Handle subtitles
            if request.download_subtitles:
                ydl_opts['writesubtitles'] = True
                ydl_opts['subtitleslangs'] = [request.subtitle_language]
                
                if request.embed_subtitles:
                    ydl_opts['postprocessors'].append({
                        'key': 'FFmpegEmbedSubtitle',
                    })
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first
                info = ydl.extract_info(request.video_url, download=False)
                video_title = info.get('title', 'video')
                
                # Download the video
                info = ydl.extract_info(request.video_url, download=True)
                
                # Determine the actual filename
                if request.format_type == FormatType.AUDIO:
                    filename = ydl.prepare_filename(info)
                    # Replace extension with audio format
                    filename = os.path.splitext(filename)[0] + f".{request.audio_format.value}"
                else:
                    filename = ydl.prepare_filename(info)
                    # Ensure correct extension
                    base_filename = os.path.splitext(filename)[0]
                    filename = f"{base_filename}.{request.video_format.value}"
                
                # Check if file exists
                if not os.path.exists(filename):
                    # Try alternative naming
                    filename = os.path.join(
                        self.output_dir,
                        f"{video_title}.{request.audio_format.value if request.format_type == FormatType.AUDIO else request.video_format.value}"
                    )
                
                if not os.path.exists(filename):
                    raise FileNotFoundError(f"Downloaded file not found: {filename}")
                
                file_size = os.path.getsize(filename)
                
                logger.info(f"Successfully downloaded with yt-dlp: {filename} ({file_size} bytes)")
                
                return {
                    'success': True,
                    'filepath': filename,
                    'filename': os.path.basename(filename),
                    'file_size': file_size,
                    'title': video_title,
                    'method': 'yt-dlp'
                }
                
        except Exception as e:
            logger.error(f"yt-dlp download failed: {str(e)}")
            raise
    
    def download_with_pytube(self, request: DownloadRequest) -> Dict[str, Any]:
        """
        Download video using pytube as fallback.
        
        Args:
            request: Download request parameters
            
        Returns:
            Dictionary with download results
            
        Raises:
            Exception: If download fails
        """
        logger.info(f"Attempting download with pytube for URL: {request.video_url}")
        
        try:
            yt = YouTube(request.video_url)
            
            if request.format_type == FormatType.AUDIO:
                # Download audio only
                stream = yt.streams.filter(only_audio=True).first()
                if not stream:
                    raise Exception("No audio stream available")
                
                filename = stream.download(output_path=self.output_dir)
                
                # Rename to requested audio format
                base_name = os.path.splitext(filename)[0]
                new_filename = f"{base_name}.{request.audio_format.value}"
                
                # Note: pytube doesn't convert formats, so we keep the original
                # In production, you'd want to use ffmpeg to convert
                if filename != new_filename:
                    os.rename(filename, new_filename)
                    filename = new_filename
                    
            else:
                # Download video
                if request.quality == VideoQuality.BEST:
                    stream = yt.streams.filter(
                        progressive=True,
                        file_extension=request.video_format.value
                    ).order_by('resolution').desc().first()
                    
                    if not stream:
                        # Fallback to any progressive stream
                        stream = yt.streams.filter(progressive=True).order_by('resolution').desc().first()
                        
                elif request.quality == VideoQuality.WORST:
                    stream = yt.streams.filter(
                        progressive=True,
                        file_extension=request.video_format.value
                    ).order_by('resolution').asc().first()
                    
                    if not stream:
                        stream = yt.streams.filter(progressive=True).order_by('resolution').asc().first()
                else:
                    # Specific resolution
                    resolution = request.quality.value  # e.g., "720p"
                    stream = yt.streams.filter(
                        progressive=True,
                        resolution=resolution,
                        file_extension=request.video_format.value
                    ).first()
                    
                    if not stream:
                        # Try without format filter
                        stream = yt.streams.filter(
                            progressive=True,
                            resolution=resolution
                        ).first()
                    
                    if not stream:
                        # Fallback to closest resolution
                        stream = yt.streams.filter(progressive=True).order_by('resolution').desc().first()
                
                if not stream:
                    raise Exception("No suitable video stream found")
                
                filename = stream.download(output_path=self.output_dir)
            
            file_size = os.path.getsize(filename)
            
            logger.info(f"Successfully downloaded with pytube: {filename} ({file_size} bytes)")
            
            return {
                'success': True,
                'filepath': filename,
                'filename': os.path.basename(filename),
                'file_size': file_size,
                'title': yt.title,
                'method': 'pytube'
            }
            
        except Exception as e:
            logger.error(f"pytube download failed: {str(e)}")
            raise
    
    def download(self, request: DownloadRequest) -> Dict[str, Any]:
        """
        Download video with automatic fallback.
        Tries yt-dlp first, falls back to pytube if it fails.
        
        Args:
            request: Download request parameters
            
        Returns:
            Dictionary with download results
            
        Raises:
            Exception: If both methods fail
        """
        ytdlp_error = None
        pytube_error = None
        
        # Try yt-dlp first
        try:
            return self.download_with_ytdlp(request)
        except Exception as e:
            ytdlp_error = str(e)
            logger.warning(f"yt-dlp failed, trying pytube fallback. Error: {ytdlp_error}")
        
        # Fallback to pytube
        try:
            return self.download_with_pytube(request)
        except Exception as e:
            pytube_error = str(e)
            logger.error(f"pytube also failed. Error: {pytube_error}")
        
        # Both failed
        error_msg = f"Both download methods failed. yt-dlp error: {ytdlp_error}. pytube error: {pytube_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def get_video_formats(self, video_url: str) -> Dict[str, Any]:
        """
        Get available formats for a video.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Dictionary with video info and available formats
            
        Raises:
            Exception: If extraction fails
        """
        logger.info(f"Extracting formats for URL: {video_url}")
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                formats = []
                for fmt in info.get('formats', []):
                    format_info = FormatInfo(
                        format_id=fmt.get('format_id', ''),
                        extension=fmt.get('ext', ''),
                        resolution=fmt.get('resolution'),
                        filesize=fmt.get('filesize'),
                        vcodec=fmt.get('vcodec'),
                        acodec=fmt.get('acodec'),
                        fps=fmt.get('fps'),
                        quality=str(fmt.get('quality')) if fmt.get('quality') is not None else None
                    )
                    formats.append(format_info)
                
                return {
                    'success': True,
                    'video_id': info.get('id', ''),
                    'title': info.get('title', ''),
                    'formats': formats,
                    'thumbnail': info.get('thumbnail'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader')
                }
                
        except Exception as e:
            logger.error(f"Failed to extract formats: {str(e)}")
            raise
    
    def upload_to_storage(self, filepath: str, filename: str, storage_provider: StorageProvider) -> str:
        """
        Upload a file to cloud storage and delete local file after successful upload.
        
        Args:
            filepath: Local path to the file
            filename: Name of the file
            storage_provider: Storage provider to use
            
        Returns:
            Public URL of the uploaded file
            
        Raises:
            Exception: If upload fails
        """
        uploader = None
        
        if storage_provider == StorageProvider.SUPABASE:
            uploader = self.supabase_uploader
        elif storage_provider == StorageProvider.S3:
            uploader = self.s3_uploader
        else:
            raise ValueError(f"Invalid storage provider: {storage_provider}")
        
        try:
            # Upload file to cloud storage
            public_url = uploader.upload_file(filepath, filename)
            
            # Delete local file after successful upload
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info(f"Deleted local file after successful upload: {filepath}")
                except Exception as e:
                    logger.warning(f"Failed to delete local file {filepath}: {str(e)}")
            
            return public_url
            
        except Exception as e:
            logger.error(f"Storage upload failed: {str(e)}")
            raise
    
    def cleanup_file(self, filepath: str) -> bool:
        """
        Delete a downloaded file.

        Args:
            filepath: Path to file to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up file: {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup file {filepath}: {str(e)}")
            return False

    def start_cleanup_task(self):
        """Start the background cleanup task."""
        if not self.cleanup_enabled:
            logger.info("Cleanup task disabled by configuration")
            return

        if self.cleanup_task and not self.cleanup_task.done():
            logger.warning("Cleanup task already running")
            return

        self.cleanup_task = asyncio.create_task(self._cleanup_worker())
        logger.info(f"Started cleanup task (interval: {self.cleanup_interval} minutes)")

    def stop_cleanup_task(self):
        """Stop the background cleanup task."""
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            logger.info("Stopped cleanup task")

    async def _cleanup_worker(self):
        """Background worker for periodic cleanup."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval * 60)  # Convert minutes to seconds
                await self._perform_cleanup()
            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup worker: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _perform_cleanup(self):
        """Perform the actual cleanup operation."""
        try:
            logger.info("Starting scheduled cleanup...")

            # Clean up local files
            await self._cleanup_local_files()
            
            # Clean up cloud storage files
            await self._cleanup_cloud_storage()

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    async def _cleanup_local_files(self):
        """Clean up local files in output directory."""
        try:
            # Get all files in output directory
            output_path = Path(self.output_dir)
            if not output_path.exists():
                return

            files = []
            total_size = 0

            # Collect file information
            for file_path in output_path.iterdir():
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        files.append({
                            'path': file_path,
                            'size': stat.st_size,
                            'mtime': stat.st_mtime
                        })
                        total_size += stat.st_size
                    except OSError as e:
                        logger.warning(f"Could not stat file {file_path}: {e}")

            # Sort files by modification time (oldest first)
            files.sort(key=lambda x: x['mtime'])

            current_time = time.time()
            max_age_seconds = self.max_file_age_hours * 3600
            max_size_bytes = self.max_storage_mb * 1024 * 1024

            cleaned_count = 0
            cleaned_size = 0

            # Clean up old files
            for file_info in files:
                file_age = current_time - file_info['mtime']

                # Remove if older than max age
                if file_age > max_age_seconds:
                    if self.cleanup_file(str(file_info['path'])):
                        cleaned_count += 1
                        cleaned_size += file_info['size']
                        total_size -= file_info['size']
                    continue

                # If still over size limit, remove oldest files
                if total_size > max_size_bytes:
                    if self.cleanup_file(str(file_info['path'])):
                        cleaned_count += 1
                        cleaned_size += file_info['size']
                        total_size -= file_info['size']

            if cleaned_count > 0:
                logger.info(f"Local cleanup completed: removed {cleaned_count} files, "
                          f"freed {cleaned_size / (1024*1024):.2f} MB")
        except Exception as e:
            logger.error(f"Error during local file cleanup: {str(e)}")
    
    async def _cleanup_cloud_storage(self):
        """Clean up files in cloud storage using same age/size logic."""
        try:
            current_time = time.time()
            max_age_seconds = self.max_file_age_hours * 3600
            max_size_bytes = self.max_storage_mb * 1024 * 1024
            
            # Clean up Supabase storage
            if self.supabase_uploader.enabled:
                await self._cleanup_storage_provider(
                    self.supabase_uploader,
                    "Supabase",
                    current_time,
                    max_age_seconds,
                    max_size_bytes
                )
            
            # Clean up S3 storage
            if self.s3_uploader.enabled:
                await self._cleanup_storage_provider(
                    self.s3_uploader,
                    "S3",
                    current_time,
                    max_age_seconds,
                    max_size_bytes
                )
        except Exception as e:
            logger.error(f"Error during cloud storage cleanup: {str(e)}")
    
    async def _cleanup_storage_provider(
        self,
        uploader,
        provider_name: str,
        current_time: float,
        max_age_seconds: int,
        max_size_bytes: int
    ):
        """Clean up files for a specific storage provider."""
        try:
            # List all files
            files = uploader.list_files()
            
            if not files:
                return
            
            # Parse file metadata and calculate total size
            file_metadata = []
            total_size = 0
            
            for file_info in files:
                try:
                    # Parse created_at timestamp
                    created_at_str = file_info.get('created_at', '')
                    if created_at_str:
                        if isinstance(created_at_str, str):
                            # Try parsing ISO format
                            try:
                                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                                created_at_timestamp = created_at.timestamp()
                            except:
                                # Fallback: use current time if parsing fails
                                created_at_timestamp = current_time
                        else:
                            created_at_timestamp = current_time
                    else:
                        created_at_timestamp = current_time
                    
                    file_metadata.append({
                        'path': file_info['path'],
                        'size': file_info.get('size', 0),
                        'created_at': created_at_timestamp
                    })
                    total_size += file_info.get('size', 0)
                except Exception as e:
                    logger.warning(f"Failed to parse file metadata for {file_info.get('path', 'unknown')}: {e}")
            
            # Sort by creation time (oldest first)
            file_metadata.sort(key=lambda x: x['created_at'])
            
            cleaned_count = 0
            cleaned_size = 0
            
            # Clean up old files
            for file_info in file_metadata:
                file_age = current_time - file_info['created_at']
                
                # Remove if older than max age
                if file_age > max_age_seconds:
                    if uploader.delete_file(file_info['path']):
                        cleaned_count += 1
                        cleaned_size += file_info['size']
                        total_size -= file_info['size']
                    continue
                
                # If still over size limit, remove oldest files
                if total_size > max_size_bytes:
                    if uploader.delete_file(file_info['path']):
                        cleaned_count += 1
                        cleaned_size += file_info['size']
                        total_size -= file_info['size']
            
            if cleaned_count > 0:
                logger.info(f"{provider_name} cleanup completed: removed {cleaned_count} files, "
                          f"freed {cleaned_size / (1024*1024):.2f} MB")
        except Exception as e:
            logger.error(f"Error during {provider_name} cleanup: {str(e)}")

