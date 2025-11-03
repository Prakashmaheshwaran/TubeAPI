FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY models.py .
COPY downloader.py .

# Create directory for downloads
RUN mkdir -p /tmp/yt_downloads

# Expose port
EXPOSE 8000

# Set environment variables
ENV PORT=8000
ENV HOST=0.0.0.0
ENV OUTPUT_DIR=/tmp/yt_downloads

# Run the application
CMD ["python", "main.py"]

