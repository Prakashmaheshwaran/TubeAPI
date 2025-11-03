FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including FFmpeg, curl, and unzip (for Deno installation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno for yt-dlp JavaScript runtime support
RUN curl -fsSL https://deno.land/install.sh | sh && \
    mv /root/.deno/bin/deno /usr/local/bin/deno

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY models.py .
COPY downloader.py .
COPY storage.py .

# Create directory for downloads
RUN mkdir -p /tmp/yt_downloads

# Expose port
EXPOSE 8000

# Set environment variables
ENV PORT=8000
ENV HOST=0.0.0.0
ENV OUTPUT_DIR=/tmp/yt_downloads

# Run the application with uvicorn directly (better for production)
# Use shell form to allow environment variable substitution
CMD uvicorn main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000}

