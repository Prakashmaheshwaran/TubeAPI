# Changelog

All notable changes to TubeAPI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of TubeAPI
- REST API for downloading YouTube videos and audio
- Support for multiple video qualities (144p to 2160p/4K)
- Audio-only downloads in various formats (MP3, M4A, OPUS, FLAC, WAV)
- Automatic fallback from yt-dlp to pytube
- Password authentication via API key
- Rate limiting for API endpoints
- Docker and Docker Compose support
- Comprehensive API documentation with FastAPI
- Health check endpoint
- Format listing endpoint for available video qualities

### Technical Details
- Built with FastAPI and Python 3.8+
- Uses yt-dlp as primary downloader with pytube fallback
- Supports multiple output formats (MP4, WebM, MKV, FLV, AVI)
- Configurable via environment variables
- Production-ready with Gunicorn deployment option
