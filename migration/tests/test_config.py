"""Tests for configuration loading and path resolution."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
import yaml

from hooting_yard_migration.config import Config, PathsConfig, ArchiveOrgConfig, ConversionConfig, YouTubeConfig


class TestConfigLoading:
    """Test configuration loading from various sources."""

    def test_default_config_creation(self):
        """Test that a default config can be created."""
        config = Config()

        # Check that all sections exist with defaults
        assert config.archive_org is not None
        assert config.conversion is not None
        assert config.youtube is not None
        assert config.paths is not None
        assert config.state is not None

        # Check some default values
        assert config.archive_org.collection_name == "hooting-yard"
        assert config.conversion.video_codec == "libx264"
        assert config.youtube.category == "Entertainment"
        assert config.paths.processed == Path("./processed")

    def test_config_from_nonexistent_yaml(self):
        """Test loading config from non-existent YAML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nonexistent.yaml"
            config = Config.from_yaml(config_path)

            # Should return default config
            assert config.archive_org.collection_name == "hooting-yard"
            assert config._config_root == config_path.parent.resolve()

    def test_config_from_yaml_with_path_resolution(self):
        """Test loading config from YAML file with proper path resolution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "test_config.yaml"

            # Create test YAML config
            config_data = {
                "archive_org": {
                    "collection_name": "test-collection",
                    "max_parallel_downloads": 5
                },
                "paths": {
                    "downloads": "./test_downloads",
                    "rendered": "./test_rendered",
                    "processed": "./test_state",
                    "logs": "./test_logs",
                    "temp": "./test_temp"
                },
                "conversion": {
                    "cover_image": "./assets/test-cover.jpg"
                },
                "youtube": {
                    "client_secret_file": "./creds/secret.json",
                    "token_file": "./creds/token.json"
                }
            }

            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)

            # Load config
            config = Config.from_yaml(config_path)

            # Check that config values were loaded
            assert config.archive_org.collection_name == "test-collection"
            assert config.archive_org.max_parallel_downloads == 5

            # Check that paths are resolved relative to config file
            assert config._config_root == temp_path.resolve()
            assert config.paths.downloads == temp_path.resolve() / "test_downloads"
            assert config.paths.rendered == temp_path.resolve() / "test_rendered"
            assert config.paths.processed == temp_path.resolve() / "test_state"
            assert config.paths.logs == temp_path.resolve() / "test_logs"
            assert config.paths.temp == temp_path.resolve() / "test_temp"

            # Check conversion and YouTube paths
            assert config.conversion.cover_image == temp_path.resolve() / "assets/test-cover.jpg"
            assert config.youtube.client_secret_file == temp_path.resolve() / "creds/secret.json"
            assert config.youtube.token_file == temp_path.resolve() / "creds/token.json"

            # All paths should be absolute
            assert config.paths.downloads.is_absolute()
            assert config.paths.rendered.is_absolute()
            assert config.paths.processed.is_absolute()
            assert config.conversion.cover_image.is_absolute()
            assert config.youtube.client_secret_file.is_absolute()

    def test_config_with_absolute_paths_unchanged(self):
        """Test that absolute paths in config remain unchanged."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "test_config.yaml"

            absolute_path = Path("/tmp/absolute_test_path")
            config_data = {
                "paths": {
                    "downloads": str(absolute_path),
                    "processed": "./relative_path"
                }
            }

            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)

            config = Config.from_yaml(config_path)

            # Absolute path should remain unchanged
            assert config.paths.downloads == absolute_path
            # Relative path should be resolved
            assert config.paths.processed == temp_path.resolve() / "relative_path"

    def test_config_from_env_defaults(self):
        """Test loading config from environment variables with defaults."""
        config = Config.from_env()

        # Should have default values when no env vars set
        assert config.archive_org.collection_name == "hooting-yard"
        assert config.paths.processed == Path("./processed")

    @patch.dict(os.environ, {
        'ARCHIVE_COLLECTION': 'test-env-collection',
        'MAX_PARALLEL_DOWNLOADS': '10',
        'YOUTUBE_CLIENT_SECRET_FILE': '/env/secret.json',
        'YOUTUBE_TOKEN_FILE': '/env/token.json'
    })
    def test_config_from_env_with_overrides(self):
        """Test loading config from environment variables with overrides."""
        config = Config.from_env()

        # Check environment overrides
        assert config.archive_org.collection_name == "test-env-collection"
        assert config.archive_org.max_parallel_downloads == 10
        assert config.youtube.client_secret_file == Path("/env/secret.json")
        assert config.youtube.token_file == Path("/env/token.json")

    def test_ensure_directories_creates_paths(self):
        """Test that ensure_directories creates all necessary paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "test_config.yaml"

            config_data = {
                "paths": {
                    "downloads": "./test_downloads",
                    "rendered": "./test_rendered",
                    "processed": "./test_state",
                    "logs": "./test_logs",
                    "temp": "./test_temp"
                }
            }

            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)

            config = Config.from_yaml(config_path)

            # Directories should not exist yet
            assert not config.paths.downloads.exists()
            assert not config.paths.rendered.exists()
            assert not config.paths.processed.exists()

            # Create directories
            config.ensure_directories()

            # All directories should now exist
            assert config.paths.downloads.exists()
            assert config.paths.rendered.exists()
            assert config.paths.processed.exists()
            assert config.paths.logs.exists()
            assert config.paths.temp.exists()

    def test_real_config_file_loading(self):
        """Test loading the actual config.yaml file from the project."""
        # Get path to the real config file
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config.yaml"

        if not config_path.exists():
            pytest.skip("config.yaml not found in project root")

        # Load the real config
        config = Config.from_yaml(config_path)

        # Check that config root is set correctly
        assert config._config_root == project_root.resolve()

        # Check that some expected values exist
        assert config.archive_org.collection_name == "hooting-yard"
        assert config.conversion.video_codec in ["libx264", "h264"]

        # Check that all paths are absolute and relative to project root
        assert config.paths.processed.is_absolute()
        assert str(config.paths.processed).startswith(str(project_root.resolve()))

        # The processed path should be project_root/state based on our config
        expected_state_path = project_root.resolve() / "state"
        assert config.paths.processed == expected_state_path

    def test_path_resolution_with_nested_config_directory(self):
        """Test path resolution when config file is in a subdirectory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested directory structure
            config_dir = temp_path / "subdir" / "config"
            config_dir.mkdir(parents=True)
            config_path = config_dir / "app.yaml"

            config_data = {
                "paths": {
                    "processed": "./state",
                    "downloads": "../downloads"  # Relative to parent of config
                }
            }

            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)

            config = Config.from_yaml(config_path)

            # Paths should be resolved relative to the config file location
            assert config._config_root == config_dir.resolve()
            assert config.paths.processed == config_dir.resolve() / "state"
            assert config.paths.downloads == config_dir.resolve().parent / "downloads"


class TestConfigDataModels:
    """Test individual config data models."""

    def test_paths_config_defaults(self):
        """Test PathsConfig default values."""
        paths = PathsConfig()
        assert paths.downloads == Path("./downloads")
        assert paths.rendered == Path("./rendered")
        assert paths.processed == Path("./processed")
        assert paths.logs == Path("./logs")
        assert paths.temp == Path("./temp")

    def test_archive_org_config_defaults(self):
        """Test ArchiveOrgConfig default values."""
        archive = ArchiveOrgConfig()
        assert archive.collection_url == "https://archive.org/details/hooting-yard"
        assert archive.collection_name == "hooting-yard"
        assert archive.max_parallel_downloads == 3
        assert archive.retry_attempts == 3
        assert archive.verify_checksums is True

    def test_conversion_config_defaults(self):
        """Test ConversionConfig default values."""
        conversion = ConversionConfig()
        assert conversion.video_resolution == "1920x1080"
        assert conversion.video_codec == "libx264"
        assert conversion.audio_codec == "aac"
        assert conversion.fps == 30

    def test_youtube_config_defaults(self):
        """Test YouTubeConfig default values."""
        youtube = YouTubeConfig()
        assert youtube.category == "Entertainment"
        assert youtube.uploads_per_day == 5
        assert "Hooting Yard" in youtube.default_tags
        assert "Frank Key" in youtube.default_tags