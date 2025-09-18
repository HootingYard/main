"""State management for the migration pipeline."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from hooting_yard_migration.state.archive_org import ArchiveOrgState, ArchiveOrgEpisode
from hooting_yard_migration.state.episodes import EpisodeState, ProcessedEpisode, ProcessingStage
from hooting_yard_migration.state.youtube import YouTubeState, YouTubeVideo

logger = logging.getLogger(__name__)


class StateManager:
    """Manages the state of the migration process across all three views."""

    def __init__(self, base_path: Path):
        """Initialize the state manager.

        Args:
            base_path: Base directory for state files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Load existing states
        self.archive_state = ArchiveOrgState.load_from_directory(self.base_path)
        self.episode_state = EpisodeState.load_from_directory(self.base_path)
        self.youtube_state = YouTubeState.load_from_directory(self.base_path)

    def register_episode(self, archive_episode: ArchiveOrgEpisode) -> None:
        """Register a discovered episode from Archive.org.

        Args:
            archive_episode: Episode discovered from Archive.org
        """
        # Add to archive state
        self.archive_state.add_episode(archive_episode)
        archive_episode.save_to_yaml(self.base_path)

        # Create corresponding processing episode if not exists
        if not self.episode_state.get_episode(archive_episode.identifier):
            processed_episode = ProcessedEpisode(
                archive_identifier=archive_episode.identifier,
                title=archive_episode.title,
                date=archive_episode.date,
                stage=ProcessingStage.DISCOVERED
            )
            self.episode_state.add_episode(processed_episode)
            processed_episode.save_to_yaml(self.base_path)

        # Save indices
        self.archive_state.save_index(self.base_path)
        self.episode_state.save_index(self.base_path)

    def get_pending_downloads(
        self,
        limit: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[ProcessedEpisode]:
        """Get episodes pending download.

        Args:
            limit: Maximum number of episodes to return
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)

        Returns:
            List of episodes pending download
        """
        episodes = self.episode_state.get_episodes_by_stage(ProcessingStage.DISCOVERED)

        # Apply date filters if provided
        if start_date or end_date:
            from datetime import datetime
            if start_date:
                start = datetime.fromisoformat(start_date)
                episodes = [ep for ep in episodes if ep.date >= start]
            if end_date:
                end = datetime.fromisoformat(end_date)
                episodes = [ep for ep in episodes if ep.date <= end]

        # Apply limit
        if limit:
            episodes = episodes[:limit]

        return episodes

    def mark_downloaded(self, identifier: str, file_path: Path) -> None:
        """Mark an episode as downloaded.

        Args:
            identifier: Episode identifier
            file_path: Path to downloaded file
        """
        episode = self.episode_state.get_episode(identifier)
        if episode:
            episode.audio_file = file_path
            episode.stage = ProcessingStage.DOWNLOADED
            episode.status_message = "Download completed"
            episode.save_to_yaml(self.base_path)

    def mark_failed(self, identifier: str, error_message: str) -> None:
        """Mark an episode as failed.

        Args:
            identifier: Episode identifier
            error_message: Error description
        """
        episode = self.episode_state.get_episode(identifier)
        if episode:
            episode.stage = ProcessingStage.FAILED
            episode.add_error("ProcessingError", error_message)
            episode.save_to_yaml(self.base_path)

    def get_pending_conversions(self, limit: Optional[int] = None) -> List[ProcessedEpisode]:
        """Get episodes pending conversion."""
        episodes = self.episode_state.get_episodes_by_stage(ProcessingStage.DOWNLOADED)
        if limit:
            episodes = episodes[:limit]
        return episodes

    def mark_converted(self, identifier: str, video_path: Path) -> None:
        """Mark an episode as converted."""
        episode = self.episode_state.get_episode(identifier)
        if episode:
            episode.video_file = video_path
            episode.stage = ProcessingStage.CONVERTED
            episode.status_message = "Conversion completed"
            episode.save_to_yaml(self.base_path)

    def get_pending_uploads(self, limit: Optional[int] = None) -> List[ProcessedEpisode]:
        """Get episodes pending upload."""
        episodes = self.episode_state.get_episodes_by_stage(ProcessingStage.CONVERTED)
        if limit:
            episodes = episodes[:limit]
        return episodes

    def mark_uploaded(self, identifier: str, video_id: str) -> None:
        """Mark an episode as uploaded."""
        episode = self.episode_state.get_episode(identifier)
        if episode:
            episode.youtube_video_id = video_id
            episode.stage = ProcessingStage.PUBLISHED
            episode.status_message = "Upload completed"
            episode.save_to_yaml(self.base_path)

            # Also create YouTube state entry
            youtube_video = YouTubeVideo(
                archive_identifier=identifier,
                youtube_video_id=video_id,
                title=episode.title
            )
            self.youtube_state.add_video(youtube_video)
            youtube_video.save_to_yaml(self.base_path)

    def get_statistics(self) -> Dict[str, int]:
        """Get current migration statistics."""
        stats = {
            "total": len(self.episode_state.episodes),
            "discovered": len(self.episode_state.get_episodes_by_stage(ProcessingStage.DISCOVERED)),
            "downloaded": len(self.episode_state.get_episodes_by_stage(ProcessingStage.DOWNLOADED)),
            "converted": len(self.episode_state.get_episodes_by_stage(ProcessingStage.CONVERTED)),
            "uploaded": len(self.episode_state.get_episodes_by_stage(ProcessingStage.PUBLISHED)),
            "failed": len(self.episode_state.get_episodes_by_stage(ProcessingStage.FAILED)),
        }

        # Calculate pending counts
        stats["pending_downloads"] = stats["discovered"]
        stats["pending_conversions"] = stats["downloaded"]
        stats["pending_uploads"] = stats["converted"]

        return stats

    def generate_report(self) -> str:
        """Generate HTML progress report."""
        stats = self.get_statistics()

        # Simple HTML report (could be enhanced)
        html = f"""
        <html>
        <head><title>Migration Progress Report</title></head>
        <body>
        <h1>Hooting Yard Migration Progress</h1>
        <table border="1">
        <tr><th>Stage</th><th>Count</th></tr>
        <tr><td>Total Episodes</td><td>{stats['total']}</td></tr>
        <tr><td>Discovered</td><td>{stats['discovered']}</td></tr>
        <tr><td>Downloaded</td><td>{stats['downloaded']}</td></tr>
        <tr><td>Converted</td><td>{stats['converted']}</td></tr>
        <tr><td>Uploaded</td><td>{stats['uploaded']}</td></tr>
        <tr><td>Failed</td><td>{stats['failed']}</td></tr>
        </table>
        </body>
        </html>
        """
        return html

    def get_downloaded_episodes(self) -> List[ProcessedEpisode]:
        """Get all downloaded episodes."""
        return self.episode_state.get_episodes_by_stage(ProcessingStage.DOWNLOADED)

    def get_converted_episodes(self) -> List[ProcessedEpisode]:
        """Get all converted episodes."""
        return self.episode_state.get_episodes_by_stage(ProcessingStage.CONVERTED)