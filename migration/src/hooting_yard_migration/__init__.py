"""Hooting Yard Migration Tool.

A tool to migrate Hooting Yard episodes from Archive.org to YouTube.
"""

from hooting_yard_migration.config import Config
from hooting_yard_migration.retrieval.archive_retriever import ArchiveRetriever
from hooting_yard_migration.conversion.video_converter import VideoConverter
from hooting_yard_migration.upload.youtube_uploader import YouTubeUploader
from hooting_yard_migration.state_management import StateManager

__version__ = "0.1.0"
__author__ = "Hooting Yard Team"

__all__ = [
    "__version__",
    "__author__",
    "Config",
    "ArchiveRetriever",
    "VideoConverter",
    "YouTubeUploader",
    "StateManager",
]