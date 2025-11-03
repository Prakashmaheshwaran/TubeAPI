#!/bin/bash

# YouTube Download API - Start Script
# Handles all installation and startup cases

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "YouTube Download API - Startup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python version
print_info "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed!"
    echo "Please install Python 3.8 or higher:"
    echo "  macOS: brew install python3"
    echo "  Ubuntu/Debian: sudo apt install python3"
    echo "  Or download from: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    print_error "Python 3.8+ is required. Found: Python $PYTHON_VERSION"
    exit 1
fi

print_info "Python version: $PYTHON_VERSION ✓"

# Check pip
print_info "Checking pip installation..."
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    print_error "pip is not installed!"
    echo "Please install pip:"
    echo "  python3 -m ensurepip --upgrade"
    exit 1
fi

# Use python3 -m pip if pip3 is not available
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
else
    PIP_CMD="python3 -m pip"
fi

print_info "pip found ✓"

# Check/create virtual environment
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        print_error "Failed to create virtual environment!"
        exit 1
    fi
    print_info "Virtual environment created ✓"
else
    print_info "Virtual environment already exists ✓"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

if [ $? -ne 0 ]; then
    print_error "Failed to activate virtual environment!"
    exit 1
fi

# Upgrade pip in virtual environment
print_info "Upgrading pip..."
$PIP_CMD install --upgrade pip --quiet

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found!"
    exit 1
fi

# Check if dependencies are installed
print_info "Checking dependencies..."
MISSING_DEPS=0

while IFS= read -r line; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    
    # Extract package name (remove version specifiers)
    PACKAGE=$(echo "$line" | sed 's/[>=<].*//' | tr -d '[:space:]')
    
    if [ -n "$PACKAGE" ]; then
        if ! python3 -c "import ${PACKAGE//-/_}" 2>/dev/null; then
            MISSING_DEPS=1
            break
        fi
    fi
done < requirements.txt

# Install dependencies if needed
if [ $MISSING_DEPS -eq 1 ] || [ ! -f "$VENV_DIR/.deps_installed" ]; then
    print_info "Installing dependencies from requirements.txt..."
    $PIP_CMD install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        print_error "Failed to install dependencies!"
        exit 1
    fi
    
    touch "$VENV_DIR/.deps_installed"
    print_info "Dependencies installed ✓"
else
    print_info "Dependencies already installed ✓"
fi

# Check for FFmpeg
print_info "Checking FFmpeg installation..."
if ! command -v ffmpeg &> /dev/null; then
    print_warn "FFmpeg not found!"
    echo ""
    echo "FFmpeg is required for full functionality (audio conversion, etc.)"
    echo "Install FFmpeg:"
    echo "  macOS:     brew install ffmpeg"
    echo "  Ubuntu:    sudo apt install ffmpeg"
    echo "  Debian:    sudo apt install ffmpeg"
    echo "  Fedora:    sudo dnf install ffmpeg"
    echo "  Arch:      sudo pacman -S ffmpeg"
    echo "  Windows:   Download from https://ffmpeg.org/download.html"
    echo ""
    read -p "Continue without FFmpeg? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n 1)
    print_info "FFmpeg found: $FFMPEG_VERSION ✓"
fi

# Check environment variables
print_info "Checking environment configuration..."

if [ -f ".env" ]; then
    print_info "Loading environment variables from .env file..."
    set -a
    source .env
    set +a
fi

if [ -z "$API_PASSWORD" ]; then
    print_warn "API_PASSWORD not set!"
    echo ""
    echo "Set API_PASSWORD environment variable:"
    echo "  export API_PASSWORD='your-secret-password'"
    echo ""
    echo "Or create a .env file with:"
    echo "  API_PASSWORD=your-secret-password"
    echo ""
    read -p "Continue without API_PASSWORD? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_info "API_PASSWORD configured ✓"
fi

# Set defaults for optional variables
export PORT=${PORT:-8000}
export HOST=${HOST:-0.0.0.0}
export RATE_LIMIT=${RATE_LIMIT:-10/minute}
export CLEANUP_ENABLED=${CLEANUP_ENABLED:-true}

print_info "Server configuration:"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Rate Limit: $RATE_LIMIT"
echo "  Cleanup Enabled: $CLEANUP_ENABLED"
echo ""

# Start the server
echo "=========================================="
print_info "Starting YouTube Download API server..."
echo "=========================================="
echo ""
echo "API will be available at: http://localhost:$PORT"
echo "API docs available at: http://localhost:$PORT/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the server
python3 main.py
