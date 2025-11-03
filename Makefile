.PHONY: help install run test clean docker-build docker-run docker-stop

help:
	@echo "YouTube Download API - Available Commands"
	@echo ""
	@echo "  make install      - Install dependencies"
	@echo "  make run          - Start the API server"
	@echo "  make test         - Run test suite"
	@echo "  make clean        - Clean temporary files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run with Docker Compose"
	@echo "  make docker-stop  - Stop Docker containers"
	@echo ""

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "Done! Run 'make run' to start the server."

run:
	@echo "Starting YouTube Download API..."
	@echo "API available at: http://localhost:8000"
	@echo "API docs at: http://localhost:8000/docs"
	python main.py

test:
	@echo "Running tests..."
	python test_api.py

clean:
	@echo "Cleaning temporary files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.tmp" -delete
	find . -type f -name "*.log" -delete
	@echo "Clean complete!"

docker-build:
	@echo "Building Docker image..."
	docker build -t youtube-download-api .

docker-run:
	@echo "Starting with Docker Compose..."
	docker-compose up -d
	@echo "API available at: http://localhost:8000"

docker-stop:
	@echo "Stopping Docker containers..."
	docker-compose down

dev:
	@echo "Starting in development mode with auto-reload..."
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

