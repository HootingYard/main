"""Archive.org retrieval functionality."""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from hooting_yard_migration.config import Config
from hooting_yard_migration.scan_archive_dot_org_episodes import ArchiveOrgScanner
from hooting_yard_migration.state.archive_org import ArchiveOrgEpisode

logger = logging.getLogger(__name__)


class ArchiveRetriever:
    """Retrieves episodes from Archive.org."""

    def __init__(self, config: Config):
        """Initialize the retriever.

        Args:
            config: Application configuration
        """
        self.config = config
        self.scanner = ArchiveOrgScanner(rate_limit_delay=1.0)

    async def discover_episodes(self) -> List[ArchiveOrgEpisode]:
        """Discover all episodes from Archive.org.

        Returns:
            List of discovered episodes
        """
        logger.info("Starting episode discovery from Archive.org")

        # Ensure the state directory exists
        self.config.paths.processed.mkdir(parents=True, exist_ok=True)

        # Use our scanner to discover episodes
        # Run in thread pool since scanner is synchronous
        loop = asyncio.get_event_loop()

        def _scan():
            # The scanner now saves state immediately as episodes are discovered
            return self.scanner.scan_all_episodes(
                collection=self.config.archive_org.collection_name,
                state_dir=self.config.paths.processed
            )

        state = await loop.run_in_executor(None, _scan)
        episodes = list(state.episodes.values())

        logger.info(f"Discovered {len(episodes)} episodes")
        return episodes

    async def download_episode(self, episode: ArchiveOrgEpisode) -> Path:
        """Download an episode from Archive.org.

        Args:
            episode: Episode to download

        Returns:
            Path to downloaded audio file

        Raises:
            RuntimeError: If download fails
        """
        # This is a stub - actual download implementation would go here
        logger.info(f"Downloading episode: {episode.identifier}")

        # For now, just return a placeholder path
        download_path = self.config.paths.downloads / f"{episode.identifier}.mp3"

        # Create the parent directory
        download_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a placeholder file for testing
        download_path.write_text("placeholder audio content")

        return download_path