# TubeAPI

> A simple and reliable REST API for downloading YouTube videos and audio. Built with FastAPI and powered by yt-dlp with pytube fallback.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)

## ✨ Features

- 🎥 **Video Downloads**: Quality selection from 144p to 2160p/4K
- 🎵 **Audio Downloads**: MP3, M4A, OPUS, FLAC, WAV formats
- 🔄 **Smart Fallback**: yt-dlp primary with pytube backup
- 📹 **Multiple Formats**: MP4, WebM, MKV, FLV, AVI support
- 🔐 **Secure Authentication**: Password-protected API access
- 🛡️ **Rate Limiting**: Configurable request limits
- 📤 **Flexible Response**: Binary stream or filepath output
- 🏥 **Health Monitoring**: Built-in health check endpoint
- 📋 **Format Discovery**: List available video qualities
- 🧹 **Automatic Cleanup**: Configurable background cleanup of old files

## 🧹 Automatic File Cleanup

TubeAPI includes automatic cleanup of downloaded files to prevent storage accumulation:

- **Age-based cleanup**: Files older than configurable hours are removed
- **Size-based cleanup**: When storage exceeds limit, oldest files are removed first
- **Configurable intervals**: Cleanup runs periodically (default: every hour)
- **Smart prioritization**: Old files removed first, then by size if still over limit

**Default Settings:**
- Cleanup interval: 60 minutes
- Max file age: 24 hours
- Max storage: 1024 MB (1GB)

Configure via environment variables or `.env` file.

## 🚀 Quickstart

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/tubeapi.git
cd tubeapi

# Copy and configure environment variables
cp .env.example .env
# Edit .env file with your API password

# Start with Docker Compose
docker-compose up -d

# Test the API
curl http://localhost:8000/health
```

### Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env file with your API password

# Load environment variables and start server
source .env
python main.py
```

**API is now running at: http://localhost:8000**  
**📖 Interactive docs: http://localhost:8000/docs**

### Download a Video

```bash
curl -X POST http://localhost:8000/download \
  -H "X-API-Key: your-secret-password" \
  -d '{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}' \
  --output video.mp4
```

## Installation

### Prerequisites

- Python 3.8+
- FFmpeg

**Install FFmpeg:**
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export API_PASSWORD="your-secret-password"
export RATE_LIMIT="10/minute"  # Optional, default: 10/minute
export PORT=8000  # Optional, default: 8000
export OUTPUT_DIR="/tmp/downloads"  # Optional

# Start server
python main.py
```

Server runs at `http://localhost:8000`  
API docs at `http://localhost:8000/docs`

## Environment Variables

- `API_PASSWORD` (required) - Password for API authentication
- `RATE_LIMIT` (optional) - Rate limit per endpoint (default: "10/minute")
- `PORT` (optional) - Server port (default: 8000)
- `OUTPUT_DIR` (optional) - Download directory (default: system temp)
- `CLEANUP_ENABLED` (optional) - Enable automatic cleanup (default: "true")
- `CLEANUP_INTERVAL_MINUTES` (optional) - Cleanup check interval in minutes (default: 60)
- `MAX_FILE_AGE_HOURS` (optional) - Maximum file age before cleanup in hours (default: 24)
- `MAX_STORAGE_MB` (optional) - Maximum storage size before cleanup in MB (default: 1024)

## API Endpoints

### POST /download

Download video or audio.

**Headers:**
- `X-API-Key: your-password`

**Request Body:**
```json
{
  "video_url": "https://www.youtube.com/watch?v=...",
  "format_type": "video",
  "quality": "720p",
  "video_format": "mp4",
  "audio_format": "mp3",
  "audio_quality": "192k",
  "response_type": "binary",
  "download_subtitles": false,
  "embed_subtitles": false,
  "subtitle_language": "en"
}
```

**Parameters:**
- `video_url` (required) - YouTube video URL
- `format_type` - `"video"` or `"audio"` (default: `"video"`)
- `quality` - `"best"`, `"worst"`, `"144p"`, `"240p"`, `"360p"`, `"480p"`, `"720p"`, `"1080p"`, `"1440p"`, `"2160p"` (default: `"best"`)
- `video_format` - `"mp4"`, `"webm"`, `"mkv"`, `"flv"`, `"avi"` (default: `"mp4"`)
- `audio_format` - `"mp3"`, `"m4a"`, `"opus"`, `"vorbis"`, `"flac"`, `"wav"` (default: `"mp3"`)
- `audio_quality` - `"128k"`, `"192k"`, `"256k"`, `"320k"` (default: `"192k"`)
- `response_type` - `"binary"` or `"filepath"` (default: `"binary"`)
- `download_subtitles` - boolean (default: `false`)
- `embed_subtitles` - boolean (default: `false`)
- `subtitle_language` - language code (default: `"en"`)

**Response:**
- Binary mode: File stream with appropriate headers
- Filepath mode: JSON with file path and metadata

### GET /formats

Get available formats for a video.

**Headers:**
- `X-API-Key: your-password`

**Query Parameters:**
- `url` (required) - YouTube video URL

**Response:**
```json
{
  "success": true,
  "video_id": "...",
  "title": "Video Title",
  "formats": [...],
  "thumbnail": "...",
  "duration": 120,
  "uploader": "..."
}
```

### GET /health

Health check (no authentication required).

**Response:**
```json
{
  "status": "healthy",
  "message": "Service is running",
  "ytdlp_available": true,
  "pytube_available": true
}
```

## Usage Examples

### Download Best Quality Video

```bash
curl -X POST http://localhost:8000/download \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-password" \
  -d '{"video_url": "https://www.youtube.com/watch?v=..."}' \
  --output video.mp4
```

### Download 720p Video

```bash
curl -X POST http://localhost:8000/download \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-password" \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=...",
    "quality": "720p",
    "video_format": "mp4"
  }' \
  --output video.mp4
```

### Download Audio Only (MP3)

```bash
curl -X POST http://localhost:8000/download \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-password" \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=...",
    "format_type": "audio",
    "audio_format": "mp3",
    "audio_quality": "320k"
  }' \
  --output audio.mp3
```

### Get Available Formats

```bash
curl "http://localhost:8000/formats?url=https://www.youtube.com/watch?v=..." \
  -H "X-API-Key: your-password"
```

### Python Example

```python
import requests

headers = {"X-API-Key": "your-password"}
response = requests.post(
    "http://localhost:8000/download",
    headers=headers,
    json={
        "video_url": "https://www.youtube.com/watch?v=...",
        "quality": "720p"
    }
)

with open("video.mp4", "wb") as f:
    f.write(response.content)
```

## Authentication

All endpoints except `/health` require authentication via `X-API-Key` header. Set the password using `API_PASSWORD` environment variable.

## Rate Limiting

Rate limiting is enabled by default:
- `/download`: 10 requests per minute
- `/formats`: 30 requests per minute

Configure via `RATE_LIMIT` environment variable (e.g., `"20/minute"`, `"100/hour"`).

## Error Responses

```json
{
  "success": false,
  "error": "Error message",
  "details": "Additional details"
}
```

HTTP Status Codes:
- `200` - Success
- `400` - Bad request (invalid parameters)
- `401` - Unauthorized (invalid password)
- `429` - Too many requests (rate limit exceeded)
- `500` - Server error

## Testing

Run test suite:
```bash
python test_api.py
```

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Docker

```bash
docker build -t youtube-api .
docker run -d -p 8000:8000 -e API_PASSWORD=your-password youtube-api
```

### Docker Compose

```bash
docker-compose up -d
```

## Troubleshooting

**FFmpeg not found:**
- Install FFmpeg and ensure it's in PATH
- Verify: `ffmpeg -version`

**Download fails:**
- Check video URL is valid and accessible
- Update yt-dlp: `pip install --upgrade yt-dlp`
- Check server logs for details

**Authentication errors:**
- Ensure `API_PASSWORD` is set
- Verify `X-API-Key` header matches password

**Rate limit exceeded:**
- Wait for rate limit window to reset
- Adjust `RATE_LIMIT` environment variable

---

## 📞 Contact

**Prakash Maheshwaran**

New York, US | pmaheshwaran@binghamton.edu | https://linkedin.com/in/prakash-maheshwaran |

https://github.com/Prakashmaheshwaran

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
