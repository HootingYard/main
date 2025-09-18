"""Configuration management for the migration tool."""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


class ArchiveOrgConfig(BaseModel):
    """Archive.org configuration."""

    collection_url: str = "https://archive.org/details/hooting-yard"
    collection_name: str = "hooting-yard"
    max_parallel_downloads: int = 3
    retry_attempts: int = 3
    retry_delay: int = 5
    timeout: int = 30
    chunk_size: int = 8192
    verify_checksums: bool = True


class ConversionConfig(BaseModel):
    """Video conversion configuration."""

    cover_image: Path = Path("assets/hooting-yard-cover.jpg")
    video_resolution: str = "1920x1080"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    fps: int = 30
    preset: str = "medium"
    crf: int = 23
    max_parallel: int = 2
    ffmpeg_path: str = "ffmpeg"


class YouTubeConfig(BaseModel):
    """YouTube upload configuration."""

    client_secret_file: Path = Path("credentials/client_secret.json")
    token_file: Path = Path("credentials/token.json")
    start_date: str = "2025-10-01T10:00:00Z"
    interval_days: int = 7
    category: str = "Entertainment"
    default_tags: list[str] = Field(
        default_factory=lambda: ["Hooting Yard", "Frank Key", "Spoken Word"]
    )
    uploads_per_day: int = 5
    chunk_size: int = 52428800  # 50MB


class PathsConfig(BaseModel):
    """File path configuration."""

    downloads: Path = Path("./downloads")
    rendered: Path = Path("./rendered")
    processed: Path = Path("./processed")
    logs: Path = Path("./logs")
    temp: Path = Path("./temp")


class StateConfig(BaseModel):
    """State management configuration."""

    database_file: str = "state.db"
    auto_resume: bool = True
    max_retries: Dict[str, int] = Field(
        default_factory=lambda: {"download": 3, "conversion": 2, "upload": 3}
    )
    retry_delay: int = 300


class Config(BaseModel):
    """Main configuration class."""

    model_config = {"arbitrary_types_allowed": True}

    archive_org: ArchiveOrgConfig = Field(default_factory=ArchiveOrgConfig)
    conversion: ConversionConfig = Field(default_factory=ConversionConfig)
    youtube: YouTubeConfig = Field(default_factory=YouTubeConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    state: StateConfig = Field(default_factory=StateConfig)

    # Internal field to track the config file's directory
    _config_root: Optional[Path] = None

    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        """Load configuration from YAML file."""
        config_root = path.parent.resolve()

        if not path.exists():
            config = cls()
        else:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            config = cls(**data) if data else cls()

        # Store the config root and resolve all relative paths
        config._config_root = config_root
        config._resolve_paths()
        return config

    def _resolve_paths(self) -> None:
        """Resolve all relative paths to be relative to the config file directory."""
        if self._config_root is None:
            return

        # Resolve all paths in PathsConfig relative to config root
        for field_name in ["downloads", "rendered", "processed", "logs", "temp"]:
            current_path = getattr(self.paths, field_name)
            if not current_path.is_absolute():
                resolved_path = (self._config_root / current_path).resolve()
                setattr(self.paths, field_name, resolved_path)

        # Resolve conversion paths
        if not self.conversion.cover_image.is_absolute():
            self.conversion.cover_image = (self._config_root / self.conversion.cover_image).resolve()

        # Resolve YouTube credential paths
        if not self.youtube.client_secret_file.is_absolute():
            self.youtube.client_secret_file = (self._config_root / self.youtube.client_secret_file).resolve()

        if not self.youtube.token_file.is_absolute():
            self.youtube.token_file = (self._config_root / self.youtube.token_file).resolve()

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config = cls()

        # Override with environment variables
        if value := os.getenv("ARCHIVE_COLLECTION"):
            config.archive_org.collection_name = value

        if value := os.getenv("MAX_PARALLEL_DOWNLOADS"):
            config.archive_org.max_parallel_downloads = int(value)

        if value := os.getenv("YOUTUBE_CLIENT_SECRET_FILE"):
            config.youtube.client_secret_file = Path(value)

        if value := os.getenv("YOUTUBE_TOKEN_FILE"):
            config.youtube.token_file = Path(value)

        return config

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        for path in [
            self.paths.downloads,
            self.paths.rendered,
            self.paths.processed,
            self.paths.logs,
            self.paths.temp,
        ]:
            path.mkdir(parents=True, exist_ok=True)