#!/bin/bash

# YouTube Download API - Start Script

echo "Starting YouTube Download API..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! pip show fastapi > /dev/null 2>&1; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    echo "Dependencies already installed."
fi

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo "WARNING: FFmpeg not found!"
    echo "Please install FFmpeg for full functionality:"
    echo "  macOS: brew install ffmpeg"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo ""
fi

# Start the server
echo ""
echo "Starting server..."
echo "API will be available at: http://localhost:8000"
echo "API docs available at: http://localhost:8000/docs"
echo ""

python main.py

