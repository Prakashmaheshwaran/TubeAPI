from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, Literal, List
from enum import Enum


class FormatType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"


class ResponseType(str, Enum):
    BINARY = "binary"
    FILEPATH = "filepath"


class VideoQuality(str, Enum):
    BEST = "best"
    WORST = "worst"
    P144 = "144p"
    P240 = "240p"
    P360 = "360p"
    P480 = "480p"
    P720 = "720p"
    P1080 = "1080p"
    P1440 = "1440p"
    P2160 = "2160p"


class VideoFormat(str, Enum):
    MP4 = "mp4"
    WEBM = "webm"
    MKV = "mkv"
    FLV = "flv"
    AVI = "avi"


class AudioFormat(str, Enum):
    MP3 = "mp3"
    M4A = "m4a"
    OPUS = "opus"
    VORBIS = "vorbis"
    FLAC = "flac"
    WAV = "wav"


class AudioQuality(str, Enum):
    Q128K = "128k"
    Q192K = "192k"
    Q256K = "256k"
    Q320K = "320k"


class DownloadRequest(BaseModel):
    video_url: str = Field(..., description="YouTube video URL")
    format_type: FormatType = Field(
        default=FormatType.VIDEO, description="Download format type (video or audio)"
    )
    quality: Optional[VideoQuality] = Field(
        default=VideoQuality.BEST, description="Video quality"
    )
    video_format: Optional[VideoFormat] = Field(
        default=VideoFormat.MP4, description="Video container format"
    )
    audio_format: Optional[AudioFormat] = Field(
        default=AudioFormat.MP3, description="Audio format (used when format_type is audio)"
    )
    audio_quality: Optional[AudioQuality] = Field(
        default=AudioQuality.Q192K, description="Audio bitrate quality"
    )
    response_type: ResponseType = Field(
        default=ResponseType.BINARY, description="Response type (binary stream or filepath)"
    )
    download_subtitles: bool = Field(
        default=False, description="Download subtitles"
    )
    embed_subtitles: bool = Field(
        default=False, description="Embed subtitles in video"
    )
    subtitle_language: Optional[str] = Field(
        default="en", description="Subtitle language code (e.g., 'en', 'es', 'fr')"
    )

    @field_validator("video_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("video_url must be a non-empty string")
        # Basic YouTube URL validation
        if not any(domain in v.lower() for domain in ["youtube.com", "youtu.be"]):
            raise ValueError("URL must be a valid YouTube URL")
        return v


class DownloadResponse(BaseModel):
    success: bool
    message: str
    filepath: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None


class FormatInfo(BaseModel):
    format_id: str
    extension: str
    resolution: Optional[str] = None
    filesize: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    fps: Optional[float] = None
    quality: Optional[str] = None


class FormatsListResponse(BaseModel):
    success: bool
    video_id: str
    title: str
    formats: List[FormatInfo]
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    uploader: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    message: str
    ytdlp_available: bool
    pytube_available: bool


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None

