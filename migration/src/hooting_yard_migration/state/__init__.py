"""State management with YAML-based storage.

The state is organized into three views:
- archive_org: Our view of what's available on Archive.org
- episodes: What we've migrated and processed locally
- youtube: What we've republished to YouTube
"""

from hooting_yard_migration.state.archive_org import ArchiveOrgState, ArchiveOrgEpisode
from hooting_yard_migration.state.episodes import EpisodeState, ProcessingStage
from hooting_yard_migration.state.youtube import YouTubeState, YouTubeVideo

__all__ = [
    # Archive.org view
    "ArchiveOrgState",
    "ArchiveOrgEpisode",

    # Local episode processing
    "EpisodeState",
    "ProcessingStage",

    # YouTube republishing
    "YouTubeState",
    "YouTubeVideo",
]