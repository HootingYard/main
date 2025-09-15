"""Episode downloader with progress tracking and verification."""

import hashlib
import logging
import time
from pathlib import Path
from typing import Optional, Callable
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from hooting_yard_migration.retrieval.client import ArchiveOrgClient
from hooting_yard_migration.retrieval.models import DownloadResult, Episode

logger = logging.getLogger(__name__)


class EpisodeDownloader:
    """Download episodes from Archive.org with verification."""

    def __init__(
        self,
        client: Optional[ArchiveOrgClient] = None,
        chunk_size: int = 8192,
        timeout: int = 30,
        verify_checksum: bool = True,
    ):
        """Initialize the downloader.

        Args:
            client: Archive.org API client (creates new if None)
            chunk_size: Download chunk size in bytes
            timeout: Request timeout in seconds
            verify_checksum: Whether to verify MD5 checksums
        """
        self.client = client or ArchiveOrgClient(timeout=timeout)
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.verify_checksum = verify_checksum

    def download_episode(
        self,
        identifier: str,
        output_dir: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> DownloadResult:
        """Download an episode by its identifier.

        Args:
            identifier: Archive.org item identifier or full URL
            output_dir: Directory to save the downloaded file
            progress_callback: Optional callback for progress updates (bytes_downloaded, total_bytes)

        Returns:
            DownloadResult with metadata and file path
        """
        start_time = time.time()

        # Handle both identifier and full URL
        if identifier.startswith("http"):
            # Extract identifier from URL
            # e.g., "https://archive.org/details/hy0_hooting_yard_2004-04-14"
            parts = identifier.rstrip("/").split("/")
            identifier = parts[-1]

        try:
            # Get episode metadata
            logger.info(f"Fetching metadata for {identifier}")
            episode = self.client.get_episode_metadata(identifier)

            # Find MP3 file
            mp3_file = episode.mp3_file
            if not mp3_file:
                return DownloadResult(
                    success=False,
                    episode_identifier=identifier,
                    metadata=episode.metadata,
                    error_message="No MP3 file found in episode",
                )

            # Prepare download
            download_url = episode.download_url
            if not download_url:
                return DownloadResult(
                    success=False,
                    episode_identifier=identifier,
                    metadata=episode.metadata,
                    error_message="Could not construct download URL",
                )

            # Create output directory
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Determine output filename
            output_path = output_dir / mp3_file.name

            # Download the file
            logger.info(f"Downloading {mp3_file.name} ({mp3_file.size / 1024 / 1024:.1f} MB)")
            downloaded_path, actual_md5 = self._download_file(
                download_url,
                output_path,
                expected_size=mp3_file.size,
                progress_callback=progress_callback,
            )

            # Verify checksum if requested
            if self.verify_checksum and mp3_file.md5:
                if actual_md5 != mp3_file.md5:
                    # Delete corrupted file
                    downloaded_path.unlink(missing_ok=True)
                    return DownloadResult(
                        success=False,
                        episode_identifier=identifier,
                        metadata=episode.metadata,
                        download_url=download_url,
                        error_message=f"MD5 checksum mismatch: expected {mp3_file.md5}, got {actual_md5}",
                    )
                logger.debug(f"MD5 checksum verified: {actual_md5}")

            download_time = time.time() - start_time

            return DownloadResult(
                success=True,
                episode_identifier=identifier,
                metadata=episode.metadata,
                file_path=downloaded_path,
                file_size=downloaded_path.stat().st_size,
                md5_hash=actual_md5,
                download_url=download_url,
                download_time=download_time,
            )

        except Exception as e:
            logger.error(f"Failed to download {identifier}: {e}")
            return DownloadResult(
                success=False,
                episode_identifier=identifier,
                metadata=(
                    episode.metadata
                    if "episode" in locals()
                    else None
                ),
                error_message=str(e),
                download_time=time.time() - start_time,
            )

    def _download_file(
        self,
        url: str,
        output_path: Path,
        expected_size: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> tuple[Path, str]:
        """Download a file from a URL.

        Args:
            url: Download URL
            output_path: Path to save the file
            expected_size: Expected file size for progress tracking
            progress_callback: Optional progress callback

        Returns:
            Tuple of (downloaded_path, md5_hash)
        """
        # Create request with headers
        request = Request(url)
        request.add_header("User-Agent", "HootingYard-Migration/1.0")

        md5_hash = hashlib.md5()
        bytes_downloaded = 0

        try:
            with urlopen(request, timeout=self.timeout) as response:
                # Get total size from headers if not provided
                if expected_size is None:
                    content_length = response.headers.get("Content-Length")
                    expected_size = int(content_length) if content_length else None

                # Download and write to file
                with open(output_path, "wb") as f:
                    while True:
                        chunk = response.read(self.chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        md5_hash.update(chunk)
                        bytes_downloaded += len(chunk)

                        if progress_callback and expected_size:
                            progress_callback(bytes_downloaded, expected_size)

        except (HTTPError, URLError) as e:
            # Clean up partial download
            output_path.unlink(missing_ok=True)
            raise Exception(f"Download failed: {e}")

        return output_path, md5_hash.hexdigest()

    def download_episode_from_url(
        self,
        url: str,
        output_dir: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> DownloadResult:
        """Download an episode from a direct URL.

        This is a convenience method that extracts the identifier from the URL
        and calls download_episode.

        Args:
            url: Archive.org URL (e.g., "https://archive.org/details/hy0_hooting_yard_2004-04-14")
            output_dir: Directory to save the downloaded file
            progress_callback: Optional callback for progress updates

        Returns:
            DownloadResult with metadata and file path
        """
        return self.download_episode(url, output_dir, progress_callback)