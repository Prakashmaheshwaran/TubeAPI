import os
import tempfile
import logging
from typing import Optional, Dict, Any, List
import yt_dlp
from pytube import YouTube
from models import (
    DownloadRequest,
    FormatType,
    VideoQuality,
    VideoFormat,
    AudioFormat,
    AudioQuality,
    FormatInfo
)

# Configure logging
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

