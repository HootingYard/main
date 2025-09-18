"""Episode state - tracking our local processing and migration."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
import yaml


class ProcessingStage(Enum):
    """Stages in the episode processing pipeline."""

    DISCOVERED = "discovered"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    CONVERTING = "converting"
    CONVERTED = "converted"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProcessedEpisode:
    """Represents an episode we've processed locally."""

    # Identification (links to archive_org)
    archive_identifier: str  # e.g., "hy0_hooting_yard_2004-04-14"
    title: str
    date: datetime

    # Processing status
    stage: ProcessingStage = ProcessingStage.DISCOVERED
    status_message: str = ""

    # File locations
    audio_file: Optional[Path] = None
    video_file: Optional[Path] = None
    transcript_file: Optional[Path] = None
    thumbnail_file: Optional[Path] = None

    # Processing metadata
    download_started: Optional[datetime] = None
    download_completed: Optional[datetime] = None
    conversion_started: Optional[datetime] = None
    conversion_completed: Optional[datetime] = None
    upload_started: Optional[datetime] = None
    upload_completed: Optional[datetime] = None

    # YouTube metadata (once uploaded)
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    scheduled_publish_date: Optional[datetime] = None
    actual_publish_date: Optional[datetime] = None

    # Quality metrics
    audio_duration_seconds: Optional[float] = None
    audio_size_bytes: Optional[int] = None
    video_size_bytes: Optional[int] = None
    processing_time_seconds: Optional[float] = None

    # Tracking
    last_updated: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    error_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_yaml_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "identification": {
                "archive_identifier": self.archive_identifier,
                "title": self.title,
                "date": self.date.isoformat(),
            },
            "status": {
                "stage": self.stage.value,
                "message": self.status_message,
                "last_updated": self.last_updated.isoformat(),
                "retry_count": self.retry_count,
            },
            "files": {
                "audio": str(self.audio_file) if self.audio_file else None,
                "video": str(self.video_file) if self.video_file else None,
                "transcript": str(self.transcript_file) if self.transcript_file else None,
                "thumbnail": str(self.thumbnail_file) if self.thumbnail_file else None,
            },
            "processing_times": {
                "download_started": self.download_started.isoformat() if self.download_started else None,
                "download_completed": self.download_completed.isoformat() if self.download_completed else None,
                "conversion_started": self.conversion_started.isoformat() if self.conversion_started else None,
                "conversion_completed": self.conversion_completed.isoformat() if self.conversion_completed else None,
                "upload_started": self.upload_started.isoformat() if self.upload_started else None,
                "upload_completed": self.upload_completed.isoformat() if self.upload_completed else None,
            },
            "youtube": {
                "video_id": self.youtube_video_id,
                "url": self.youtube_url,
                "scheduled_publish": self.scheduled_publish_date.isoformat() if self.scheduled_publish_date else None,
                "actual_publish": self.actual_publish_date.isoformat() if self.actual_publish_date else None,
            },
            "metrics": {
                "audio_duration_seconds": self.audio_duration_seconds,
                "audio_size_bytes": self.audio_size_bytes,
                "video_size_bytes": self.video_size_bytes,
                "processing_time_seconds": self.processing_time_seconds,
            },
            "errors": self.error_history,
        }

    @classmethod
    def from_yaml_dict(cls, data: Dict[str, Any]) -> "ProcessedEpisode":
        """Create from YAML dictionary."""
        ident = data["identification"]
        status = data.get("status", {})
        files = data.get("files", {})
        times = data.get("processing_times", {})
        youtube = data.get("youtube", {})
        metrics = data.get("metrics", {})

        return cls(
            archive_identifier=ident["archive_identifier"],
            title=ident["title"],
            date=datetime.fromisoformat(ident["date"]),
            stage=ProcessingStage(status.get("stage", "discovered")),
            status_message=status.get("message", ""),
            last_updated=datetime.fromisoformat(status.get("last_updated", datetime.now().isoformat())),
            retry_count=status.get("retry_count", 0),
            audio_file=Path(files["audio"]) if files.get("audio") else None,
            video_file=Path(files["video"]) if files.get("video") else None,
            transcript_file=Path(files["transcript"]) if files.get("transcript") else None,
            thumbnail_file=Path(files["thumbnail"]) if files.get("thumbnail") else None,
            download_started=datetime.fromisoformat(times["download_started"]) if times.get("download_started") else None,
            download_completed=datetime.fromisoformat(times["download_completed"]) if times.get("download_completed") else None,
            conversion_started=datetime.fromisoformat(times["conversion_started"]) if times.get("conversion_started") else None,
            conversion_completed=datetime.fromisoformat(times["conversion_completed"]) if times.get("conversion_completed") else None,
            upload_started=datetime.fromisoformat(times["upload_started"]) if times.get("upload_started") else None,
            upload_completed=datetime.fromisoformat(times["upload_completed"]) if times.get("upload_completed") else None,
            youtube_video_id=youtube.get("video_id"),
            youtube_url=youtube.get("url"),
            scheduled_publish_date=datetime.fromisoformat(youtube["scheduled_publish"]) if youtube.get("scheduled_publish") else None,
            actual_publish_date=datetime.fromisoformat(youtube["actual_publish"]) if youtube.get("actual_publish") else None,
            audio_duration_seconds=metrics.get("audio_duration_seconds"),
            audio_size_bytes=metrics.get("audio_size_bytes"),
            video_size_bytes=metrics.get("video_size_bytes"),
            processing_time_seconds=metrics.get("processing_time_seconds"),
            error_history=data.get("errors", []),
        )

    def save_to_yaml(self, base_path: Path) -> Path:
        """Save to YAML file in year-based directory."""
        year = self.date.year
        dir_path = base_path / "processing_history" / str(year)
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / f"{self.archive_identifier}.yaml"
        with open(file_path, 'w') as f:
            yaml.dump(self.to_yaml_dict(), f, default_flow_style=False, sort_keys=False)

        return file_path

    @classmethod
    def load_from_yaml(cls, file_path: Path) -> "ProcessedEpisode":
        """Load from YAML file."""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_yaml_dict(data)

    def add_error(self, error_type: str, error_message: str, traceback: Optional[str] = None) -> None:
        """Add an error to the history."""
        self.error_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": error_message,
            "traceback": traceback,
            "stage": self.stage.value,
        })
        self.retry_count += 1
        self.last_updated = datetime.now()


@dataclass
class EpisodeState:
    """Manages the collection of processed episodes."""

    episodes: Dict[str, ProcessedEpisode] = field(default_factory=dict)

    def add_episode(self, episode: ProcessedEpisode) -> None:
        """Add or update an episode."""
        self.episodes[episode.archive_identifier] = episode

    def get_episode(self, archive_identifier: str) -> Optional[ProcessedEpisode]:
        """Get episode by archive identifier."""
        return self.episodes.get(archive_identifier)

    def get_episodes_by_stage(self, stage: ProcessingStage) -> List[ProcessedEpisode]:
        """Get all episodes at a specific processing stage."""
        return [
            ep for ep in self.episodes.values()
            if ep.stage == stage
        ]

    def get_episodes_by_year(self, year: int) -> List[ProcessedEpisode]:
        """Get all episodes from a specific year."""
        return [
            ep for ep in self.episodes.values()
            if ep.date.year == year
        ]

    def get_failed_episodes(self) -> List[ProcessedEpisode]:
        """Get all failed episodes that might need retry."""
        return [
            ep for ep in self.episodes.values()
            if ep.stage == ProcessingStage.FAILED
        ]

    def get_completed_episodes(self) -> List[ProcessedEpisode]:
        """Get all successfully published episodes."""
        return [
            ep for ep in self.episodes.values()
            if ep.stage == ProcessingStage.PUBLISHED
        ]

    def save_index(self, base_path: Path) -> None:
        """Save index file with summary information."""
        index_path = base_path / "processing_history" / "index.yaml"
        index_path.parent.mkdir(parents=True, exist_ok=True)

        # Calculate statistics by stage
        stage_counts = {}
        for stage in ProcessingStage:
            stage_counts[stage.value] = len(self.get_episodes_by_stage(stage))

        # Calculate year statistics
        years = {}
        for episode in self.episodes.values():
            year = str(episode.date.year)
            if year not in years:
                years[year] = []
            years[year].append(episode.archive_identifier)

        index_data = {
            "last_updated": datetime.now().isoformat(),
            "total_episodes": len(self.episodes),
            "stages": stage_counts,
            "episodes_by_year": years,
            "summary": {
                "completed": len(self.get_completed_episodes()),
                "failed": len(self.get_failed_episodes()),
                "in_progress": len([
                    ep for ep in self.episodes.values()
                    if ep.stage not in [ProcessingStage.PUBLISHED, ProcessingStage.FAILED, ProcessingStage.SKIPPED]
                ]),
            }
        }

        with open(index_path, 'w') as f:
            yaml.dump(index_data, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load_from_directory(cls, base_path: Path) -> "EpisodeState":
        """Load all episodes from directory structure."""
        state = cls()
        episodes_path = base_path / "processing_history"

        if not episodes_path.exists():
            return state

        # Load all episode YAML files
        for year_dir in episodes_path.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                for yaml_file in year_dir.glob("*.yaml"):
                    try:
                        episode = ProcessedEpisode.load_from_yaml(yaml_file)
                        state.add_episode(episode)
                    except Exception as e:
                        print(f"Error loading {yaml_file}: {e}")

        return state