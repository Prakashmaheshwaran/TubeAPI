# Contributing to TubeAPI

Thank you for your interest in contributing to TubeAPI! We welcome contributions from everyone.

## Ways to Contribute

- **Bug Reports**: Report bugs using GitHub issues
- **Feature Requests**: Suggest new features via GitHub issues
- **Code Contributions**: Submit pull requests with bug fixes or new features
- **Documentation**: Improve documentation, README, or code comments
- **Testing**: Write or improve tests

## Development Setup

### Prerequisites

- Python 3.8+
- FFmpeg
- Docker (optional, for containerized development)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/tubeapi.git
   cd tubeapi
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   ```bash
   export API_PASSWORD="your-test-password"
   export RATE_LIMIT="100/minute"  # Higher limit for development
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

6. **Test the API**
   ```bash
   # Health check
   curl http://localhost:8000/health

   # API docs
   open http://localhost:8000/docs
   ```

### Using Docker for Development

```bash
# Build and run with Docker
docker-compose up --build

# Or build manually
docker build -t tubeapi .
docker run -p 8000:8000 -e API_PASSWORD=test tubeapi
```

## Testing

Run the test suite:

```bash
python test_api.py
```

## Code Style

- Follow PEP 8 style guidelines
- Use type hints where possible
- Write descriptive commit messages
- Keep functions and classes focused on single responsibilities

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Pull Request Guidelines

- Provide a clear description of what your PR does
- Reference any related issues
- Include tests for new features
- Ensure all tests pass
- Update documentation if needed

## Reporting Issues

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to reproduce**: Step-by-step instructions
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**: OS, Python version, etc.
- **Logs**: Any relevant error logs

## License

By contributing to TubeAPI, you agree that your contributions will be licensed under the MIT License.
