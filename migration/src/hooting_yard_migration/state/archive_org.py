"""Archive.org state - our view of what's available on Archive.org."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml


@dataclass
class ArchiveOrgEpisode:
    """Represents an episode available on Archive.org."""

    # Core identification
    identifier: str  # e.g., "hy0_hooting_yard_2004-04-14"
    title: str
    date: datetime

    # Archive.org metadata
    collection: List[str] = field(default_factory=list)
    creator: str = "Frank Key"
    description: str = ""  # Short description with timestamps
    full_text: Optional[str] = None  # Full episode text/notes from Archive.org

    # File information
    mp3_filename: Optional[str] = None
    mp3_size: Optional[int] = None
    mp3_duration: Optional[float] = None
    mp3_md5: Optional[str] = None

    # Text content
    transcript_text: Optional[str] = None
    transcript_filename: Optional[str] = None
    subject_tags: List[str] = field(default_factory=list)
    language: str = "en"

    # Discovery metadata
    discovered_at: datetime = field(default_factory=datetime.now)
    last_checked: datetime = field(default_factory=datetime.now)

    # Status
    available: bool = True
    download_url: Optional[str] = None

    def to_yaml_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "identifier": self.identifier,
            "title": self.title,
            "date": self.date.isoformat(),
            "collection": self.collection,
            "creator": self.creator,
            "description": self.description,
            "full_text": self.full_text,
            "mp3": {
                "filename": self.mp3_filename,
                "size": self.mp3_size,
                "duration": self.mp3_duration,
                "md5": self.mp3_md5,
            } if self.mp3_filename else None,
            "text_content": {
                "transcript_text": self.transcript_text,
                "transcript_filename": self.transcript_filename,
                "subject_tags": self.subject_tags,
                "language": self.language,
            },
            "discovery": {
                "discovered_at": self.discovered_at.isoformat(),
                "last_checked": self.last_checked.isoformat(),
            },
            "status": {
                "available": self.available,
                "download_url": self.download_url,
            },
        }

    @classmethod
    def from_yaml_dict(cls, data: Dict[str, Any]) -> "ArchiveOrgEpisode":
        """Create from YAML dictionary."""
        mp3_data = data.get("mp3", {}) or {}
        text_content = data.get("text_content", {}) or {}
        discovery = data.get("discovery", {})
        status = data.get("status", {})

        return cls(
            identifier=data["identifier"],
            title=data["title"],
            date=datetime.fromisoformat(data["date"]),
            collection=data.get("collection", []),
            creator=data.get("creator", "Frank Key"),
            description=data.get("description", ""),
            full_text=data.get("full_text"),
            mp3_filename=mp3_data.get("filename"),
            mp3_size=mp3_data.get("size"),
            mp3_duration=mp3_data.get("duration"),
            mp3_md5=mp3_data.get("md5"),
            transcript_text=text_content.get("transcript_text"),
            transcript_filename=text_content.get("transcript_filename"),
            subject_tags=text_content.get("subject_tags", []),
            language=text_content.get("language", "en"),
            discovered_at=datetime.fromisoformat(discovery.get("discovered_at", datetime.now().isoformat())),
            last_checked=datetime.fromisoformat(discovery.get("last_checked", datetime.now().isoformat())),
            available=status.get("available", True),
            download_url=status.get("download_url"),
        )

    def save_to_yaml(self, base_path: Path) -> Path:
        """Save to YAML file in year-based directory."""
        year = self.date.year
        dir_path = base_path / "archive_org" / str(year)
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / f"{self.identifier}.yaml"
        with open(file_path, 'w') as f:
            yaml.dump(self.to_yaml_dict(), f, default_flow_style=False, sort_keys=False)

        return file_path

    @classmethod
    def load_from_yaml(cls, file_path: Path) -> "ArchiveOrgEpisode":
        """Load from YAML file."""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_yaml_dict(data)


@dataclass
class ArchiveOrgState:
    """Manages the collection of Archive.org episodes."""

    episodes: Dict[str, ArchiveOrgEpisode] = field(default_factory=dict)
    last_full_scan: Optional[datetime] = None
    total_episodes: int = 0

    def add_episode(self, episode: ArchiveOrgEpisode) -> None:
        """Add or update an episode."""
        self.episodes[episode.identifier] = episode
        self.total_episodes = len(self.episodes)

    def get_episode(self, identifier: str) -> Optional[ArchiveOrgEpisode]:
        """Get episode by identifier."""
        return self.episodes.get(identifier)

    def get_episodes_by_year(self, year: int) -> List[ArchiveOrgEpisode]:
        """Get all episodes from a specific year."""
        return [
            ep for ep in self.episodes.values()
            if ep.date.year == year
        ]

    def get_available_episodes(self) -> List[ArchiveOrgEpisode]:
        """Get all available episodes."""
        return [ep for ep in self.episodes.values() if ep.available]

    def save_index(self, base_path: Path) -> None:
        """Save index file with summary information."""
        index_path = base_path / "archive_org" / "index.yaml"
        index_path.parent.mkdir(parents=True, exist_ok=True)

        index_data = {
            "last_full_scan": self.last_full_scan.isoformat() if self.last_full_scan else None,
            "total_episodes": self.total_episodes,
            "episodes_by_year": {},
            "summary": {
                "available": len(self.get_available_episodes()),
                "unavailable": len([ep for ep in self.episodes.values() if not ep.available]),
            }
        }

        # Group episodes by year
        for episode in self.episodes.values():
            year = str(episode.date.year)
            if year not in index_data["episodes_by_year"]:
                index_data["episodes_by_year"][year] = []
            index_data["episodes_by_year"][year].append(episode.identifier)

        with open(index_path, 'w') as f:
            yaml.dump(index_data, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load_from_directory(cls, base_path: Path) -> "ArchiveOrgState":
        """Load all episodes from directory structure."""
        state = cls()
        archive_path = base_path / "archive_org"

        if not archive_path.exists():
            return state

        # Load index if it exists
        index_path = archive_path / "index.yaml"
        if index_path.exists():
            with open(index_path, 'r') as f:
                index_data = yaml.safe_load(f)
                if index_data.get("last_full_scan"):
                    state.last_full_scan = datetime.fromisoformat(index_data["last_full_scan"])

        # Load all episode YAML files
        for year_dir in archive_path.iterdir():
            if year_dir.is_dir() and year_dir.name.isdigit():
                for yaml_file in year_dir.glob("*.yaml"):
                    try:
                        episode = ArchiveOrgEpisode.load_from_yaml(yaml_file)
                        state.add_episode(episode)
                    except Exception as e:
                        print(f"Error loading {yaml_file}: {e}")

        return state