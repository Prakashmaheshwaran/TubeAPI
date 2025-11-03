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

## 🚀 Quickstart

### Docker Deployment (Recommended)

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

**API is now running at: http://localhost:8000**  
**📖 Interactive docs: http://localhost:8000/docs**

### Minimal Installation (Alternative)

For local development without Docker, use the provided start script:

```bash
# Make start script executable
chmod +x start.sh

# Run the start script
./start.sh
```

The script will automatically:
- Create a virtual environment if needed
- Install all dependencies
- Check for FFmpeg installation
- Start the server

**Note**: Ensure Python 3.8+ and FFmpeg are installed on your system.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_PASSWORD` | Yes | - | Password for API authentication |
| `PORT` | No | `8000` | Server port number |
| `HOST` | No | `0.0.0.0` | Server host address |
| `OUTPUT_DIR` | No | System temp | Directory for downloaded files |
| `RATE_LIMIT` | No | `10/minute` | Rate limit per endpoint (e.g., `20/minute`, `100/hour`) |
| `CLEANUP_ENABLED` | No | `true` | Enable automatic file cleanup |
| `CLEANUP_INTERVAL_MINUTES` | No | `60` | Cleanup check interval in minutes |
| `MAX_FILE_AGE_HOURS` | No | `24` | Maximum file age before cleanup in hours |
| `MAX_STORAGE_MB` | No | `1024` | Maximum storage size before cleanup in MB |
| `SUPABASE_URL` | No | - | Supabase project URL (for cloud storage) |
| `SUPABASE_KEY` | No | - | Supabase service role key (for cloud storage) |
| `SUPABASE_BUCKET` | No | - | Supabase storage bucket name (for cloud storage) |
| `AWS_ACCESS_KEY_ID` | No | - | AWS access key ID (for S3 storage) |
| `AWS_SECRET_ACCESS_KEY` | No | - | AWS secret access key (for S3 storage) |
| `AWS_S3_BUCKET` | No | - | AWS S3 bucket name (for S3 storage) |
| `AWS_REGION` | No | `us-east-1` | AWS region for S3 bucket |

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
  "storage_provider": null,
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
- `storage_provider` - `"supabase"`, `"s3"`, or `"filepath"` (optional, uploads to cloud if specified and `response_type` is `"filepath"`)
- `download_subtitles` - boolean (default: `false`)
- `embed_subtitles` - boolean (default: `false`)
- `subtitle_language` - language code (default: `"en"`)

**Response:**
- Binary mode: File stream with appropriate headers
- Filepath mode (no storage_provider): JSON with local file path and metadata
- Filepath mode (with storage_provider): JSON with public URL and metadata (local file deleted after upload)

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

### Download and Upload to Supabase

```bash
curl -X POST http://localhost:8000/download \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-password" \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=...",
    "response_type": "filepath",
    "storage_provider": "supabase"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Download completed and uploaded to supabase",
  "filename": "video.mp4",
  "file_size": 12345678,
  "public_url": "https://your-project.supabase.co/storage/v1/object/public/bucket/2024-01-15/video.mp4"
}
```

### Download and Upload to S3

```bash
curl -X POST http://localhost:8000/download \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-password" \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=...",
    "response_type": "filepath",
    "storage_provider": "s3"
  }'
```

### Python Example

```python
import requests

headers = {"X-API-Key": "your-password"}

# Download as binary
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

# Download and upload to Supabase
response = requests.post(
    "http://localhost:8000/download",
    headers=headers,
    json={
        "video_url": "https://www.youtube.com/watch?v=...",
        "response_type": "filepath",
        "storage_provider": "supabase"
    }
)

result = response.json()
print(f"Public URL: {result['public_url']}")
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

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
