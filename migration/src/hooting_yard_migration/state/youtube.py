"""YouTube state - tracking our YouTube republishing."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
import yaml


class PublishStatus(Enum):
    """Status of YouTube video publication."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    PRIVATE = "private"
    UNLISTED = "unlisted"
    FAILED = "failed"


@dataclass
class YouTubeVideo:
    """Represents a video published to YouTube."""

    # Identification (links back to original episode)
    archive_identifier: str
    youtube_video_id: str
    title: str

    # Publication details
    status: PublishStatus = PublishStatus.DRAFT
    published_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None

    # YouTube metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)
    category_id: str = "22"  # People & Blogs
    privacy_status: str = "public"

    # Playlist associations
    playlist_ids: List[str] = field(default_factory=list)

    # Metrics (populated after publication)
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0

    # Tracking
    uploaded_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_yaml_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "identification": {
                "archive_identifier": self.archive_identifier,
                "youtube_video_id": self.youtube_video_id,
                "title": self.title,
            },
            "publication": {
                "status": self.status.value,
                "published_at": self.published_at.isoformat() if self.published_at else None,
                "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
                "uploaded_at": self.uploaded_at.isoformat(),
            },
            "metadata": {
                "description": self.description,
                "tags": self.tags,
                "category_id": self.category_id,
                "privacy_status": self.privacy_status,
            },
            "playlists": self.playlist_ids,
            "metrics": {
                "view_count": self.view_count,
                "like_count": self.like_count,
                "comment_count": self.comment_count,
            },
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_yaml_dict(cls, data: Dict[str, Any]) -> "YouTubeVideo":
        """Create from YAML dictionary."""
        ident = data["identification"]
        pub = data.get("publication", {})
        metadata = data.get("metadata", {})
        metrics = data.get("metrics", {})

        return cls(
            archive_identifier=ident["archive_identifier"],
            youtube_video_id=ident["youtube_video_id"],
            title=ident["title"],
            status=PublishStatus(pub.get("status", "draft")),
            published_at=datetime.fromisoformat(pub["published_at"]) if pub.get("published_at") else None,
            scheduled_for=datetime.fromisoformat(pub["scheduled_for"]) if pub.get("scheduled_for") else None,
            uploaded_at=datetime.fromisoformat(pub.get("uploaded_at", datetime.now().isoformat())),
            description=metadata.get("description", ""),
            tags=metadata.get("tags", []),
            category_id=metadata.get("category_id", "22"),
            privacy_status=metadata.get("privacy_status", "public"),
            playlist_ids=data.get("playlists", []),
            view_count=metrics.get("view_count", 0),
            like_count=metrics.get("like_count", 0),
            comment_count=metrics.get("comment_count", 0),
            last_updated=datetime.fromisoformat(data.get("last_updated", datetime.now().isoformat())),
        )

    def save_to_yaml(self, base_path: Path) -> Path:
        """Save to YAML file in youtube directory."""
        dir_path = base_path / "youtube"
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / f"{self.archive_identifier}.yaml"
        with open(file_path, 'w') as f:
            yaml.dump(self.to_yaml_dict(), f, default_flow_style=False, sort_keys=False)

        return file_path

    @classmethod
    def load_from_yaml(cls, file_path: Path) -> "YouTubeVideo":
        """Load from YAML file."""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_yaml_dict(data)


@dataclass
class YouTubeState:
    """Manages the collection of YouTube videos."""

    videos: Dict[str, YouTubeVideo] = field(default_factory=dict)
    channel_id: str = ""
    last_upload: Optional[datetime] = None

    def add_video(self, video: YouTubeVideo) -> None:
        """Add or update a video."""
        self.videos[video.archive_identifier] = video

    def get_video(self, archive_identifier: str) -> Optional[YouTubeVideo]:
        """Get video by archive identifier."""
        return self.videos.get(archive_identifier)

    def get_videos_by_status(self, status: PublishStatus) -> List[YouTubeVideo]:
        """Get all videos with a specific status."""
        return [
            video for video in self.videos.values()
            if video.status == status
        ]

    def get_published_videos(self) -> List[YouTubeVideo]:
        """Get all published videos."""
        return self.get_videos_by_status(PublishStatus.PUBLISHED)

    def save_index(self, base_path: Path) -> None:
        """Save index file with summary information."""
        index_path = base_path / "youtube" / "index.yaml"
        index_path.parent.mkdir(parents=True, exist_ok=True)

        # Calculate statistics by status
        status_counts = {}
        for status in PublishStatus:
            status_counts[status.value] = len(self.get_videos_by_status(status))

        index_data = {
            "channel_id": self.channel_id,
            "last_upload": self.last_upload.isoformat() if self.last_upload else None,
            "last_updated": datetime.now().isoformat(),
            "total_videos": len(self.videos),
            "status_counts": status_counts,
            "summary": {
                "published": len(self.get_published_videos()),
                "pending": len([v for v in self.videos.values() if v.status in [PublishStatus.DRAFT, PublishStatus.SCHEDULED]]),
                "total_views": sum(v.view_count for v in self.videos.values()),
            }
        }

        with open(index_path, 'w') as f:
            yaml.dump(index_data, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load_from_directory(cls, base_path: Path) -> "YouTubeState":
        """Load all videos from directory structure."""
        state = cls()
        youtube_path = base_path / "youtube"

        if not youtube_path.exists():
            return state

        # Load index if it exists
        index_path = youtube_path / "index.yaml"
        if index_path.exists():
            with open(index_path, 'r') as f:
                index_data = yaml.safe_load(f)
                state.channel_id = index_data.get("channel_id", "")
                if index_data.get("last_upload"):
                    state.last_upload = datetime.fromisoformat(index_data["last_upload"])

        # Load all video YAML files
        for yaml_file in youtube_path.glob("*.yaml"):
            if yaml_file.name != "index.yaml":
                try:
                    video = YouTubeVideo.load_from_yaml(yaml_file)
                    state.add_video(video)
                except Exception as e:
                    print(f"Error loading {yaml_file}: {e}")

        return state