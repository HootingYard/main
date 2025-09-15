"""Data models for retrieval module."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


@dataclass
class EpisodeMetadata:
    """Metadata for a Hooting Yard episode from Archive.org."""

    identifier: str
    title: str
    creator: str
    date: datetime
    description: str
    collection: List[str]
    mediatype: str
    scanner: Optional[str] = None
    uploader: Optional[str] = None
    publicdate: Optional[datetime] = None
    addeddate: Optional[datetime] = None
    notes: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_archive_metadata(cls, metadata: Dict[str, Any]) -> "EpisodeMetadata":
        """Create from Archive.org metadata dictionary."""
        # Parse dates
        date = datetime.fromisoformat(metadata["date"].replace("Z", "+00:00"))

        publicdate = None
        if pd := metadata.get("publicdate"):
            try:
                publicdate = datetime.strptime(pd, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        addeddate = None
        if ad := metadata.get("addeddate"):
            try:
                addeddate = datetime.strptime(ad, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        # Ensure collection is a list
        collection = metadata.get("collection", [])
        if isinstance(collection, str):
            collection = [collection]

        return cls(
            identifier=metadata["identifier"],
            title=metadata.get("title", ""),
            creator=metadata.get("creator", "Frank Key"),
            date=date,
            description=metadata.get("description", ""),
            collection=collection,
            mediatype=metadata.get("mediatype", "audio"),
            scanner=metadata.get("scanner"),
            uploader=metadata.get("uploader"),
            publicdate=publicdate,
            addeddate=addeddate,
            notes=metadata.get("notes"),
            raw_metadata=metadata,
        )


@dataclass
class FileInfo:
    """Information about a file in an Archive.org item."""

    name: str
    format: str
    size: int
    md5: Optional[str] = None
    sha1: Optional[str] = None
    crc32: Optional[str] = None
    length: Optional[float] = None  # Duration for audio files
    title: Optional[str] = None
    creator: Optional[str] = None
    album: Optional[str] = None
    track: Optional[str] = None
    genre: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileInfo":
        """Create from Archive.org file dictionary."""
        return cls(
            name=data["name"],
            format=data.get("format", ""),
            size=int(data.get("size", 0)),
            md5=data.get("md5"),
            sha1=data.get("sha1"),
            crc32=data.get("crc32"),
            length=float(data["length"]) if "length" in data else None,
            title=data.get("title"),
            creator=data.get("creator"),
            album=data.get("album"),
            track=data.get("track"),
            genre=data.get("genre"),
        )


@dataclass
class Episode:
    """Complete episode information."""

    identifier: str
    metadata: EpisodeMetadata
    files: List[FileInfo]
    server: str
    dir: str

    @property
    def mp3_file(self) -> Optional[FileInfo]:
        """Get the main MP3 file info."""
        for file in self.files:
            if file.format == "VBR MP3":
                return file
        return None

    @property
    def download_url(self) -> Optional[str]:
        """Get the download URL for the MP3 file."""
        if mp3 := self.mp3_file:
            return f"https://archive.org/download/{self.identifier}/{mp3.name}"
        return None


@dataclass
class DownloadResult:
    """Result of downloading an episode."""

    success: bool
    episode_identifier: str
    metadata: EpisodeMetadata
    file_path: Optional[Path] = None
    file_size: Optional[int] = None
    md5_hash: Optional[str] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    download_time: Optional[float] = None

    @property
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "episode_identifier": self.episode_identifier,
            "metadata": {
                "identifier": self.metadata.identifier,
                "title": self.metadata.title,
                "creator": self.metadata.creator,
                "date": self.metadata.date.isoformat(),
                "description": self.metadata.description,
                "collection": self.metadata.collection,
                "mediatype": self.metadata.mediatype,
            },
            "file_path": str(self.file_path) if self.file_path else None,
            "file_size": self.file_size,
            "md5_hash": self.md5_hash,
            "download_url": self.download_url,
            "error_message": self.error_message,
            "download_time": self.download_time,
        }