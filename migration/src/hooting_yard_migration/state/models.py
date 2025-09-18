"""State models for episode processing pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any


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
class ProcessingError:
    """Error information for failed processing."""

    timestamp: datetime
    stage: ProcessingStage
    error_type: str
    error_message: str
    traceback: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "stage": self.stage.value,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingError":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            stage=ProcessingStage(data["stage"]),
            error_type=data["error_type"],
            error_message=data["error_message"],
            traceback=data.get("traceback"),
            retry_count=data.get("retry_count", 0),
        )


@dataclass
class EpisodeState:
    """Complete state information for an episode."""

    # Identification
    episode_id: str
    archive_identifier: str
    title: str
    date: datetime

    # Current status
    stage: ProcessingStage
    status_message: str = ""
    last_updated: datetime = field(default_factory=datetime.now)

    # File references
    source_url: Optional[str] = None
    audio_file: Optional[Path] = None
    video_file: Optional[Path] = None
    transcript_file: Optional[Path] = None

    # Processing metadata
    download_attempts: int = 0
    conversion_attempts: int = 0
    upload_attempts: int = 0

    # YouTube metadata
    youtube_video_id: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    published_date: Optional[datetime] = None
    playlist_ids: List[str] = field(default_factory=list)

    # Quality metrics
    audio_duration: Optional[float] = None
    audio_size: Optional[int] = None
    video_size: Optional[int] = None
    processing_time: Optional[float] = None

    # Error tracking
    error_history: List[ProcessingError] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Check if episode processing is complete."""
        return self.stage in [ProcessingStage.PUBLISHED, ProcessingStage.SKIPPED]

    @property
    def has_failed(self) -> bool:
        """Check if episode has failed processing."""
        return self.stage == ProcessingStage.FAILED

    @property
    def can_retry(self) -> bool:
        """Check if episode can be retried."""
        if not self.has_failed:
            return False

        max_attempts = {
            ProcessingStage.DOWNLOADING: 3,
            ProcessingStage.CONVERTING: 2,
            ProcessingStage.UPLOADING: 3,
        }

        # Check the stage where it failed
        if self.error_history:
            last_error = self.error_history[-1]
            stage = last_error.stage

            if stage == ProcessingStage.DOWNLOADING:
                return self.download_attempts < max_attempts.get(stage, 0)
            elif stage == ProcessingStage.CONVERTING:
                return self.conversion_attempts < max_attempts.get(stage, 0)
            elif stage == ProcessingStage.UPLOADING:
                return self.upload_attempts < max_attempts.get(stage, 0)

        return False

    def add_error(self, error: Exception, stage: Optional[ProcessingStage] = None) -> None:
        """Add an error to the history."""
        self.error_history.append(
            ProcessingError(
                timestamp=datetime.now(),
                stage=stage or self.stage,
                error_type=type(error).__name__,
                error_message=str(error),
                retry_count=len([e for e in self.error_history if e.stage == (stage or self.stage)]),
            )
        )
        self.stage = ProcessingStage.FAILED
        self.status_message = str(error)
        self.last_updated = datetime.now()

    def transition_to(self, new_stage: ProcessingStage, message: str = "") -> None:
        """Transition to a new processing stage."""
        self.stage = new_stage
        self.status_message = message
        self.last_updated = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "episode_id": self.episode_id,
            "archive_identifier": self.archive_identifier,
            "title": self.title,
            "date": self.date.isoformat(),
            "stage": self.stage.value,
            "status_message": self.status_message,
            "last_updated": self.last_updated.isoformat(),
            "files": {
                "source_url": self.source_url,
                "audio_file": str(self.audio_file) if self.audio_file else None,
                "video_file": str(self.video_file) if self.video_file else None,
                "transcript_file": str(self.transcript_file) if self.transcript_file else None,
            },
            "attempts": {
                "download": self.download_attempts,
                "conversion": self.conversion_attempts,
                "upload": self.upload_attempts,
            },
            "youtube": {
                "video_id": self.youtube_video_id,
                "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
                "published_date": self.published_date.isoformat() if self.published_date else None,
                "playlist_ids": self.playlist_ids,
            },
            "metrics": {
                "audio_duration": self.audio_duration,
                "audio_size": self.audio_size,
                "video_size": self.video_size,
                "processing_time": self.processing_time,
            },
            "error_history": [e.to_dict() for e in self.error_history],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpisodeState":
        """Create from dictionary."""
        files = data.get("files", {})
        attempts = data.get("attempts", {})
        youtube = data.get("youtube", {})
        metrics = data.get("metrics", {})

        state = cls(
            episode_id=data["episode_id"],
            archive_identifier=data["archive_identifier"],
            title=data["title"],
            date=datetime.fromisoformat(data["date"]),
            stage=ProcessingStage(data["stage"]),
            status_message=data.get("status_message", ""),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            source_url=files.get("source_url"),
            audio_file=Path(files["audio_file"]) if files.get("audio_file") else None,
            video_file=Path(files["video_file"]) if files.get("video_file") else None,
            transcript_file=Path(files["transcript_file"]) if files.get("transcript_file") else None,
            download_attempts=attempts.get("download", 0),
            conversion_attempts=attempts.get("conversion", 0),
            upload_attempts=attempts.get("upload", 0),
            youtube_video_id=youtube.get("video_id"),
            scheduled_date=datetime.fromisoformat(youtube["scheduled_date"]) if youtube.get("scheduled_date") else None,
            published_date=datetime.fromisoformat(youtube["published_date"]) if youtube.get("published_date") else None,
            playlist_ids=youtube.get("playlist_ids", []),
            audio_duration=metrics.get("audio_duration"),
            audio_size=metrics.get("audio_size"),
            video_size=metrics.get("video_size"),
            processing_time=metrics.get("processing_time"),
        )

        # Reconstruct error history
        for error_data in data.get("error_history", []):
            state.error_history.append(ProcessingError.from_dict(error_data))

        return state


@dataclass
class StateMetrics:
    """Aggregate metrics for migration progress."""

    total_episodes: int = 0
    discovered: int = 0
    downloaded: int = 0
    converted: int = 0
    uploaded: int = 0
    scheduled: int = 0
    published: int = 0
    failed: int = 0
    skipped: int = 0

    # Performance metrics
    total_download_size: int = 0
    total_video_size: int = 0
    total_processing_time: float = 0
    average_download_speed: float = 0
    average_conversion_time: float = 0
    average_upload_time: float = 0

    # Error metrics
    total_errors: int = 0
    download_errors: int = 0
    conversion_errors: int = 0
    upload_errors: int = 0

    @property
    def completion_percentage(self) -> float:
        """Calculate overall completion percentage."""
        if self.total_episodes == 0:
            return 0.0
        return (self.published / self.total_episodes) * 100

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        completed = self.published + self.scheduled
        if self.total_episodes == 0:
            return 0.0
        return (completed / self.total_episodes) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_episodes": self.total_episodes,
            "stages": {
                "discovered": self.discovered,
                "downloaded": self.downloaded,
                "converted": self.converted,
                "uploaded": self.uploaded,
                "scheduled": self.scheduled,
                "published": self.published,
                "failed": self.failed,
                "skipped": self.skipped,
            },
            "performance": {
                "total_download_size": self.total_download_size,
                "total_video_size": self.total_video_size,
                "total_processing_time": self.total_processing_time,
                "average_download_speed": self.average_download_speed,
                "average_conversion_time": self.average_conversion_time,
                "average_upload_time": self.average_upload_time,
            },
            "errors": {
                "total": self.total_errors,
                "download": self.download_errors,
                "conversion": self.conversion_errors,
                "upload": self.upload_errors,
            },
            "summary": {
                "completion_percentage": self.completion_percentage,
                "success_rate": self.success_rate,
            },
        }