#!/bin/bash
# YouTube Download API - Production Deployment Script

set -e

echo "🚀 YouTube Download API - Production Deployment"
echo "=============================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# YouTube Download API Configuration

# API Security
API_PASSWORD=change-me-in-production

# Rate Limiting (requests per minute)
RATE_LIMIT=10/minute

# Cleanup Configuration
CLEANUP_ENABLED=true
CLEANUP_INTERVAL_MINUTES=60
MAX_FILE_AGE_HOURS=24
MAX_STORAGE_MB=1024

# Storage Configuration (optional)
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_BUCKET=

# AWS S3 Configuration (optional)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=
AWS_REGION=us-east-1

# Server Configuration
PORT=8000
HOST=0.0.0.0
OUTPUT_DIR=/tmp/yt_downloads
EOF
    echo "✅ Created .env file. Please edit it with your production values."
    echo "⚠️  IMPORTANT: Change API_PASSWORD from 'change-me-in-production'!"
    echo ""
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down || true

# Build the image
echo "🔨 Building Docker image..."
docker-compose build --no-cache

# Start the services
echo "▶️  Starting services..."
docker-compose up -d

# Wait for health check
echo "🏥 Waiting for health check..."
sleep 10

# Check if the service is healthy
echo "🔍 Checking service health..."
if curl -f http://localhost:8000/health &> /dev/null; then
    echo "✅ Service is healthy and running!"
    echo ""
    echo "🌐 API is available at: http://localhost:8000"
    echo "📚 API documentation: http://localhost:8000/docs"
    echo "🏥 Health check: http://localhost:8000/health"
    echo ""
    echo "📋 Useful commands:"
    echo "  • View logs: docker-compose logs -f"
    echo "  • Stop service: docker-compose down"
    echo "  • Restart: docker-compose restart"
    echo "  • Update: docker-compose pull && docker-compose up -d"
    echo ""
    echo "🔐 Remember to configure your API_PASSWORD in the .env file!"
else
    echo "❌ Service failed to start properly."
    echo "📋 Check logs with: docker-compose logs"
    exit 1
fi
