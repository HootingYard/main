# Hooting Yard Migration Tool

A Python tool to migrate Hooting Yard radio show episodes from Archive.org to YouTube.

## Overview

This tool automates the process of:
1. Discovering and downloading episodes from Archive.org
2. Converting audio files to video format with static images
3. Uploading videos to YouTube with proper metadata and scheduling
4. Managing state for resumable operations

## Installation

### Prerequisites

- Python 3.12 or higher
- FFmpeg installed and available in PATH
- Poetry for dependency management

### Setup

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

## Configuration

Create a `.env` file in the project root:

```env
# Archive.org settings
ARCHIVE_COLLECTION=hooting-yard

# YouTube settings
YOUTUBE_CLIENT_SECRET_FILE=credentials/client_secret.json
YOUTUBE_TOKEN_FILE=credentials/token.json

# Processing settings
MAX_PARALLEL_DOWNLOADS=3
MAX_PARALLEL_CONVERSIONS=2
```

Create a `config.yaml` file:

```yaml
archive_org:
  collection_url: https://archive.org/details/hooting-yard

conversion:
  cover_image: assets/hooting-yard-cover.jpg
  video_resolution: 1920x1080

youtube:
  start_date: 2025-10-01T10:00:00Z
  interval_days: 7

paths:
  downloads: ./downloads
  rendered: ./rendered
  processed: ./processed
```

## Usage

### Basic Commands

```bash
# Show help
hooting-yard-migrate --help

# Discover all episodes
hooting-yard-migrate discover

# Download episodes
hooting-yard-migrate download --limit 10

# Convert to video
hooting-yard-migrate convert

# Upload to YouTube
hooting-yard-migrate upload

# Run complete pipeline
hooting-yard-migrate run --dry-run
hooting-yard-migrate run
```

### Advanced Usage

```bash
# Process specific date range
hooting-yard-migrate run --start-date 2004-04-14 --end-date 2004-12-31

# Resume from last state
hooting-yard-migrate resume

# Generate progress report
hooting-yard-migrate report

# Verify all downloads
hooting-yard-migrate verify
```

## Project Structure

```
migration/
├── src/
│   └── hooting_yard_migration/
│       ├── __init__.py
│       ├── cli.py              # Command-line interface
│       ├── config.py           # Configuration management
│       ├── retrieval/          # Archive.org retrieval
│       │   ├── __init__.py
│       │   ├── client.py       # Archive.org API client
│       │   ├── downloader.py   # Download manager
│       │   └── models.py       # Data models
│       ├── conversion/         # Video conversion
│       │   ├── __init__.py
│       │   ├── converter.py    # FFmpeg wrapper
│       │   └── validator.py    # Output validation
│       ├── upload/            # YouTube upload
│       │   ├── __init__.py
│       │   ├── uploader.py    # YouTube API client
│       │   ├── scheduler.py   # Publishing scheduler
│       │   └── auth.py        # OAuth management
│       ├── state/             # State management
│       │   ├── __init__.py
│       │   ├── manager.py     # State coordination
│       │   └── models.py      # State models
│       └── utils/             # Utilities
│           ├── __init__.py
│           ├── logging.py     # Logging setup
│           └── progress.py    # Progress tracking
├── tests/                     # Test suite
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── assets/                    # Static assets
│   └── hooting-yard-cover.jpg
├── config.yaml               # Main configuration
├── pyproject.toml           # Poetry configuration
└── README.md                # This file
```

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/unit/test_retrieval.py
```

### Code Quality

```bash
# Format code
poetry run black src tests

# Lint code
poetry run ruff src tests

# Type checking
poetry run mypy src
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run manually
poetry run pre-commit run --all-files
```

## API Documentation

See the `/docs` directory for detailed component documentation:
- [Retrieval Component](../docs/retrieval_component.md)
- [Conversion Component](../docs/conversion_component.md)
- [Upload Component](../docs/upload_component.md)
- [State Management](../docs/state_management_component.md)
- [Archive.org API Guide](../docs/archive_org_api_guide.md)

## Troubleshooting

### Common Issues

1. **FFmpeg not found**: Ensure FFmpeg is installed and in PATH
2. **YouTube quota exceeded**: Wait 24 hours or reduce upload rate
3. **Download failures**: Check network connection and retry
4. **Memory issues**: Reduce parallel processing limits

### Logging

Logs are written to `logs/` directory:
- `migration.log`: Main application log
- `errors.log`: Error-specific log
- `youtube_api.log`: YouTube API interactions

## Contributing

Please follow the existing code style and add tests for new features.

### Testing Requirements

- **All functions must have unit tests** in the appropriate location under `tests/`
- Use **pytest style tests** rather than Python's built-in unittest framework
- Test files should follow the pattern `test_*.py` and match the module structure
- Tests should cover normal operation, edge cases, and error conditions
- Use mocking for external dependencies (Archive.org API, file system, etc.)

Example test structure:
```python
# tests/test_scan_archive_dot_org_episodes.py
import pytest
from unittest.mock import Mock, patch

def test_scanner_initialization():
    """Test that scanner initializes with default values."""
    scanner = ArchiveOrgScanner()
    assert scanner.rate_limit_delay == 1.0

def test_scan_episodes_with_mock_client():
    """Test scanning episodes with mocked client."""
    # Test implementation here
```

## License

See LICENSE file in the main repository.