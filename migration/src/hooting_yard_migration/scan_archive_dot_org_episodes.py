"""Scan Archive.org for all Hooting Yard episodes and collect metadata and text."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.request import urlopen
import json
import time

from hooting_yard_migration.retrieval.client import ArchiveOrgClient
from hooting_yard_migration.state.archive_org import ArchiveOrgEpisode, ArchiveOrgState


logger = logging.getLogger(__name__)


class ArchiveOrgScanner:
    """Scanner to collect metadata and text content from Archive.org episodes."""

    def __init__(
        self,
        client: Optional[ArchiveOrgClient] = None,
        rate_limit_delay: float = 1.0,
    ) -> None:
        """Initialize the scanner.

        Args:
            client: Archive.org client (creates default if None)
            rate_limit_delay: Delay between requests in seconds
        """
        self.client = client or ArchiveOrgClient()
        self.rate_limit_delay = rate_limit_delay

    def scan_all_episodes(
        self,
        collection: str = "hooting-yard",
        state_dir: Optional[Path] = None,
    ) -> ArchiveOrgState:
        """Scan all episodes in the Hooting Yard collection.

        Args:
            collection: Archive.org collection to scan
            state_dir: Directory to save state files (optional)

        Returns:
            ArchiveOrgState with all discovered episodes
        """
        logger.info(f"Starting full scan of {collection} collection")

        # Load existing state if available
        state = ArchiveOrgState()
        if state_dir and (state_dir / "archive_org").exists():
            logger.info("Loading existing state")
            state = ArchiveOrgState.load_from_directory(state_dir)

        # Search for all episodes
        episodes_found = self._search_collection(collection)
        logger.info(f"Found {len(episodes_found)} episodes to process")

        # Process each episode
        processed_count = 0
        skipped_count = 0

        for i, episode_info in enumerate(episodes_found, 1):
            identifier = episode_info["identifier"]

            # Skip if we already have recent data
            existing = state.get_episode(identifier)
            if existing and self._is_recently_scanned(existing):
                logger.debug(f"Skipping {identifier} - recently scanned")
                skipped_count += 1
                continue

            logger.info(f"Processing {i}/{len(episodes_found)}: {identifier}")

            try:
                episode = self._fetch_episode_metadata(identifier)
                if episode:
                    state.add_episode(episode)
                    processed_count += 1

                    # Save individual episode immediately if state_dir provided
                    if state_dir:
                        episode.save_to_yaml(state_dir)

                        # Update index periodically (every 10 episodes)
                        if processed_count % 10 == 0:
                            state.save_index(state_dir)
                            logger.info(f"Saved index after {processed_count} new episodes")

            except Exception as e:
                logger.error(f"Error processing {identifier}: {e}")

            # Rate limiting
            time.sleep(self.rate_limit_delay)

        # Update scan timestamp and save final index
        state.last_full_scan = datetime.now()
        if state_dir:
            state.save_index(state_dir)

        logger.info(f"Scan complete: {len(state.episodes)} total episodes ({processed_count} new, {skipped_count} skipped)")
        return state

    def _search_collection(self, collection: str) -> List[Dict[str, Any]]:
        """Search for all episodes in a collection."""
        all_episodes = []
        page = 1
        rows = 100  # Archive.org max per request

        while True:
            start = (page - 1) * rows
            logger.debug(f"Fetching episodes {start} to {start + rows} (page {page})")

            search_results = self.client.search_collection(
                collection,
                rows=rows,
                page=page,
                sort="date asc",  # Consistent ordering
            )

            episodes = search_results.get("response", {}).get("docs", [])
            if not episodes:
                break

            all_episodes.extend(episodes)

            # Check if we've got all results
            num_found = search_results.get("response", {}).get("numFound", 0)
            if len(all_episodes) >= num_found:
                break

            page += 1
            time.sleep(self.rate_limit_delay)

        return all_episodes

    def _fetch_episode_metadata(self, identifier: str) -> Optional[ArchiveOrgEpisode]:
        """Fetch detailed metadata for a single episode."""
        try:
            # Get the full episode metadata from our client
            episode_data = self.client.get_episode_metadata(identifier)

            # Extract text content if available
            transcript_text = self._extract_text_content(identifier)

            # Create the Archive.org episode object
            episode = ArchiveOrgEpisode(
                identifier=identifier,
                title=episode_data.metadata.title,
                date=episode_data.metadata.date,
                collection=episode_data.metadata.collection,
                creator=episode_data.metadata.creator,
                description=episode_data.metadata.description,
                full_text=episode_data.metadata.notes if hasattr(episode_data.metadata, 'notes') else None,
                mp3_filename=episode_data.mp3_file.name if episode_data.mp3_file else None,
                mp3_size=episode_data.mp3_file.size if episode_data.mp3_file else None,
                mp3_duration=episode_data.mp3_file.length if episode_data.mp3_file else None,
                mp3_md5=episode_data.mp3_file.md5 if episode_data.mp3_file else None,
                transcript_text=transcript_text,
                download_url=episode_data.download_url,
                available=episode_data.mp3_file is not None,
                last_checked=datetime.now(),
            )

            return episode

        except Exception as e:
            logger.error(f"Failed to fetch metadata for {identifier}: {e}")
            return None

    def _extract_text_content(self, identifier: str) -> Optional[str]:
        """Extract text content (transcript) from Archive.org item."""
        try:
            # Try to fetch text files from the item
            metadata_url = f"https://archive.org/metadata/{identifier}"

            with urlopen(metadata_url) as response:
                metadata = json.loads(response.read().decode())

            # Look for text files in the files list
            files = metadata.get("files", [])
            text_content = []

            for file_info in files:
                filename = file_info.get("name", "")
                file_format = file_info.get("format", "")

                # Look for text, transcript, or subtitle files
                if any(ext in filename.lower() for ext in [".txt", ".srt", ".vtt"]) or \
                   any(fmt in file_format.lower() for fmt in ["text", "transcript"]):

                    text_url = f"https://archive.org/download/{identifier}/{filename}"
                    try:
                        with urlopen(text_url) as text_response:
                            text_data = text_response.read().decode('utf-8', errors='ignore')
                            text_content.append(f"=== {filename} ===\n{text_data}")
                    except Exception as e:
                        logger.warning(f"Could not fetch text file {filename}: {e}")

            return "\n\n".join(text_content) if text_content else None

        except Exception as e:
            logger.warning(f"Could not extract text content for {identifier}: {e}")
            return None

    def _is_recently_scanned(self, episode: ArchiveOrgEpisode, hours: int = 24) -> bool:
        """Check if episode was scanned recently."""
        if not episode.last_checked:
            return False

        time_diff = datetime.now() - episode.last_checked
        return time_diff.total_seconds() < (hours * 3600)


def main() -> None:
    """Main entry point for the scanner script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Scan Archive.org for Hooting Yard episodes"
    )
    parser.add_argument(
        "--collection",
        default="hooting-yard",
        help="Archive.org collection to scan (default: hooting-yard)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./state"),
        help="Directory to save state files (default: ./state)",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Set up logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Run the scanner
    scanner = ArchiveOrgScanner(rate_limit_delay=args.rate_limit)
    state = scanner.scan_all_episodes(
        collection=args.collection,
        state_dir=args.output_dir,
    )

    print(f"Scan complete!")
    print(f"Total episodes: {len(state.episodes)}")
    print(f"Available episodes: {len(state.get_available_episodes())}")
    print(f"State saved to: {args.output_dir}")


if __name__ == "__main__":
    main()