"""Tests for episode downloader."""

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from hooting_yard_migration.retrieval import (
    EpisodeDownloader,
    ArchiveOrgClient,
    DownloadResult,
)
from hooting_yard_migration.retrieval.models import Episode, EpisodeMetadata, FileInfo


# Sample metadata response from Archive.org
SAMPLE_METADATA = {
    "created": 1757897999,
    "server": "ia601802.us.archive.org",
    "dir": "/19/items/hy0_hooting_yard_2004-04-14",
    "files": [
        {
            "name": "hooting_yard_2004-04-14.mp3",
            "source": "original",
            "mtime": "1608728601",
            "size": "28363609",
            "md5": "7e10053385866b87e64a09314be58618",
            "format": "VBR MP3",
            "length": "1771.86",
            "title": "Test Episode",
            "creator": "Frank Key",
        },
        {
            "name": "hooting_yard_2004-04-14.png",
            "format": "PNG",
            "size": "41341",
        },
    ],
    "metadata": {
        "identifier": "hy0_hooting_yard_2004-04-14",
        "collection": ["hooting-yard", "podcasts"],
        "creator": "Frank Key",
        "date": "2004-04-14T00:00:00Z",
        "description": "Test episode description",
        "mediatype": "audio",
        "title": "Hooting Yard On The Air: Burnt Maps",
    },
}


class TestEpisodeDownloader:
    """Test episode downloader functionality."""

    def test_download_episode_success(self):
        """Test successful episode download with MD5 verification."""
        # Create a temporary directory for downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Mock the client and responses
            mock_client = Mock(spec=ArchiveOrgClient)

            # Create Episode object from sample metadata
            metadata = EpisodeMetadata.from_archive_metadata(SAMPLE_METADATA["metadata"])
            files = [FileInfo.from_dict(f) for f in SAMPLE_METADATA["files"]]
            episode = Episode(
                identifier="hy0_hooting_yard_2004-04-14",
                metadata=metadata,
                files=files,
                server=SAMPLE_METADATA["server"],
                dir=SAMPLE_METADATA["dir"],
            )

            mock_client.get_episode_metadata.return_value = episode

            # Create test MP3 content
            test_content = b"This is test MP3 content for the episode"
            test_md5 = hashlib.md5(test_content).hexdigest()

            # Update the MD5 in our mock episode
            episode.files[0].md5 = test_md5

            # Mock the URL download - patch where it's used
            with patch("hooting_yard_migration.retrieval.downloader.urlopen") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.read.side_effect = [test_content, b""]  # Return content then EOF
                mock_response.headers.get.return_value = str(len(test_content))
                mock_response.__enter__.return_value = mock_response
                mock_response.__exit__.return_value = None
                mock_urlopen.return_value = mock_response

                # Create downloader and download
                downloader = EpisodeDownloader(client=mock_client)
                result = downloader.download_episode(
                    "hy0_hooting_yard_2004-04-14",
                    temp_path,
                )

            # Verify result
            assert result.success is True
            assert result.episode_identifier == "hy0_hooting_yard_2004-04-14"
            assert result.metadata.title == "Hooting Yard On The Air: Burnt Maps"
            assert result.file_path is not None
            assert result.file_path.exists()
            assert result.file_path.name == "hooting_yard_2004-04-14.mp3"
            assert result.md5_hash == test_md5
            assert result.file_size == len(test_content)
            assert result.error_message is None

            # Verify file content
            with open(result.file_path, "rb") as f:
                assert f.read() == test_content

        # Verify file is deleted after temp directory cleanup
        assert not result.file_path.exists()

    def test_download_episode_from_url(self):
        """Test downloading from a full Archive.org URL."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Mock the client
            mock_client = Mock(spec=ArchiveOrgClient)

            # Create Episode object
            metadata = EpisodeMetadata.from_archive_metadata(SAMPLE_METADATA["metadata"])
            files = [FileInfo.from_dict(f) for f in SAMPLE_METADATA["files"]]
            episode = Episode(
                identifier="hy0_hooting_yard_2004-04-14",
                metadata=metadata,
                files=files,
                server=SAMPLE_METADATA["server"],
                dir=SAMPLE_METADATA["dir"],
            )

            mock_client.get_episode_metadata.return_value = episode

            # Create test content
            test_content = b"Test MP3 content"
            episode.files[0].md5 = hashlib.md5(test_content).hexdigest()

            with patch("hooting_yard_migration.retrieval.downloader.urlopen") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.read.side_effect = [test_content, b""]
                mock_response.headers.get.return_value = str(len(test_content))
                mock_response.__enter__.return_value = mock_response
                mock_response.__exit__.return_value = None
                mock_urlopen.return_value = mock_response

                downloader = EpisodeDownloader(client=mock_client)
                result = downloader.download_episode_from_url(
                    "https://archive.org/details/hy0_hooting_yard_2004-04-14",
                    temp_path,
                )

            assert result.success is True
            assert result.episode_identifier == "hy0_hooting_yard_2004-04-14"
            # Client should have been called with just the identifier
            mock_client.get_episode_metadata.assert_called_once_with("hy0_hooting_yard_2004-04-14")

    def test_download_episode_no_mp3(self):
        """Test handling of episode without MP3 file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            mock_client = Mock(spec=ArchiveOrgClient)

            # Create episode with no MP3 files
            metadata = EpisodeMetadata.from_archive_metadata(SAMPLE_METADATA["metadata"])
            files = [FileInfo.from_dict(f) for f in SAMPLE_METADATA["files"] if f["format"] != "VBR MP3"]
            episode = Episode(
                identifier="hy0_hooting_yard_2004-04-14",
                metadata=metadata,
                files=files,
                server=SAMPLE_METADATA["server"],
                dir=SAMPLE_METADATA["dir"],
            )

            mock_client.get_episode_metadata.return_value = episode

            downloader = EpisodeDownloader(client=mock_client)
            result = downloader.download_episode(
                "hy0_hooting_yard_2004-04-14",
                temp_path,
            )

            assert result.success is False
            assert result.error_message == "No MP3 file found in episode"
            assert result.file_path is None

    def test_download_episode_checksum_mismatch(self):
        """Test handling of MD5 checksum mismatch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            mock_client = Mock(spec=ArchiveOrgClient)

            metadata = EpisodeMetadata.from_archive_metadata(SAMPLE_METADATA["metadata"])
            files = [FileInfo.from_dict(f) for f in SAMPLE_METADATA["files"]]
            episode = Episode(
                identifier="hy0_hooting_yard_2004-04-14",
                metadata=metadata,
                files=files,
                server=SAMPLE_METADATA["server"],
                dir=SAMPLE_METADATA["dir"],
            )

            # Set wrong MD5 in episode
            episode.files[0].md5 = "wrong_md5_hash"
            mock_client.get_episode_metadata.return_value = episode

            test_content = b"Test content"

            with patch("hooting_yard_migration.retrieval.downloader.urlopen") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.read.side_effect = [test_content, b""]
                mock_response.headers.get.return_value = str(len(test_content))
                mock_response.__enter__.return_value = mock_response
                mock_response.__exit__.return_value = None
                mock_urlopen.return_value = mock_response

                downloader = EpisodeDownloader(client=mock_client, verify_checksum=True)
                result = downloader.download_episode(
                    "hy0_hooting_yard_2004-04-14",
                    temp_path,
                )

            assert result.success is False
            assert "MD5 checksum mismatch" in result.error_message
            # File should be deleted after checksum failure
            mp3_path = temp_path / "hooting_yard_2004-04-14.mp3"
            assert not mp3_path.exists()

    def test_download_with_progress_callback(self):
        """Test download with progress tracking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            mock_client = Mock(spec=ArchiveOrgClient)

            metadata = EpisodeMetadata.from_archive_metadata(SAMPLE_METADATA["metadata"])
            files = [FileInfo.from_dict(f) for f in SAMPLE_METADATA["files"]]
            episode = Episode(
                identifier="hy0_hooting_yard_2004-04-14",
                metadata=metadata,
                files=files,
                server=SAMPLE_METADATA["server"],
                dir=SAMPLE_METADATA["dir"],
            )

            mock_client.get_episode_metadata.return_value = episode

            # Create test content in chunks
            chunk1 = b"Part 1 of content"
            chunk2 = b"Part 2 of content"
            full_content = chunk1 + chunk2
            episode.files[0].md5 = hashlib.md5(full_content).hexdigest()
            episode.files[0].size = len(full_content)  # Update size to match test data

            progress_updates = []

            def progress_callback(downloaded, total):
                progress_updates.append((downloaded, total))

            with patch("hooting_yard_migration.retrieval.downloader.urlopen") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.read.side_effect = [chunk1, chunk2, b""]
                mock_response.headers.get.return_value = str(len(full_content))
                mock_response.__enter__.return_value = mock_response
                mock_response.__exit__.return_value = None
                mock_urlopen.return_value = mock_response

                downloader = EpisodeDownloader(
                    client=mock_client,
                    chunk_size=len(chunk1),  # Use chunk size matching our test chunks
                )
                result = downloader.download_episode(
                    "hy0_hooting_yard_2004-04-14",
                    temp_path,
                    progress_callback=progress_callback,
                )

            assert result.success is True
            # Should have progress updates for each chunk
            assert len(progress_updates) == 2
            assert progress_updates[0] == (len(chunk1), len(full_content))
            assert progress_updates[1] == (len(full_content), len(full_content))

    def test_download_network_error(self):
        """Test handling of network errors during download."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            mock_client = Mock(spec=ArchiveOrgClient)
            mock_client.get_episode_metadata.side_effect = Exception("Network error")

            downloader = EpisodeDownloader(client=mock_client)
            result = downloader.download_episode(
                "hy0_hooting_yard_2004-04-14",
                temp_path,
            )

            assert result.success is False
            assert "Network error" in result.error_message
            assert result.file_path is None

    def test_tempdir_cleanup(self):
        """Test that files are properly cleaned up with temporary directory."""
        file_path = None

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a test file
            test_file = temp_path / "test_episode.mp3"
            test_file.write_bytes(b"Test content")

            # Verify file exists
            assert test_file.exists()
            file_path = test_file

        # After context manager exits, file should be deleted
        assert not file_path.exists()


class TestArchiveOrgClient:
    """Test Archive.org API client."""

    def test_get_episode_metadata(self):
        """Test fetching episode metadata."""
        with patch("hooting_yard_migration.retrieval.client.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(SAMPLE_METADATA).encode()
            mock_response.__enter__.return_value = mock_response
            mock_response.__exit__.return_value = None
            mock_urlopen.return_value = mock_response

            client = ArchiveOrgClient()
            episode = client.get_episode_metadata("hy0_hooting_yard_2004-04-14")

            assert episode.identifier == "hy0_hooting_yard_2004-04-14"
            assert episode.metadata.title == "Hooting Yard On The Air: Burnt Maps"
            assert episode.metadata.creator == "Frank Key"
            assert len(episode.files) == 2
            assert episode.mp3_file is not None
            assert episode.mp3_file.name == "hooting_yard_2004-04-14.mp3"
            assert episode.download_url == "https://archive.org/download/hy0_hooting_yard_2004-04-14/hooting_yard_2004-04-14.mp3"

    def test_search_collection(self):
        """Test searching a collection."""
        search_response = {
            "response": {
                "numFound": 526,
                "docs": [
                    {
                        "identifier": "hy0_hooting_yard_2004-04-14",
                        "title": "Test Episode",
                        "date": "2004-04-14T00:00:00Z",
                    }
                ],
            }
        }

        with patch("hooting_yard_migration.retrieval.client.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(search_response).encode()
            mock_response.__enter__.return_value = mock_response
            mock_response.__exit__.return_value = None
            mock_urlopen.return_value = mock_response

            client = ArchiveOrgClient()
            result = client.search_collection("hooting-yard", rows=1)

            assert result["response"]["numFound"] == 526
            assert len(result["response"]["docs"]) == 1
            assert result["response"]["docs"][0]["identifier"] == "hy0_hooting_yard_2004-04-14"