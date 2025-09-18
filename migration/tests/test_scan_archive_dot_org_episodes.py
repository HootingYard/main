"""Tests for Archive.org episode scanner."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from hooting_yard_migration.scan_archive_dot_org_episodes import ArchiveOrgScanner
from hooting_yard_migration.state.archive_org import ArchiveOrgEpisode, ArchiveOrgState
from hooting_yard_migration.retrieval.client import ArchiveOrgClient


# Sample data for testing
SAMPLE_SEARCH_RESPONSE = {
    "response": {
        "numFound": 2,
        "docs": [
            {
                "identifier": "hy0_hooting_yard_2004-04-14",
                "title": "Test Episode 1",
                "date": "2004-04-14T00:00:00Z"
            },
            {
                "identifier": "hy0_hooting_yard_2004-04-21",
                "title": "Test Episode 2",
                "date": "2004-04-21T00:00:00Z"
            }
        ]
    }
}

SAMPLE_EPISODE_METADATA = {
    "metadata": {
        "identifier": "hy0_hooting_yard_2004-04-14",
        "title": "Test Episode 1",
        "creator": "Frank Key",
        "date": "2004-04-14T00:00:00Z",
        "collection": ["hooting-yard", "podcasts"],
        "description": "Test episode description"
    },
    "files": [
        {
            "name": "test_episode.mp3",
            "format": "VBR MP3",
            "size": "1000000",
            "md5": "test_md5_hash",
            "length": "600.0"
        },
        {
            "name": "test_transcript.txt",
            "format": "Text",
            "size": "5000"
        }
    ],
    "server": "ia801802.us.archive.org",
    "dir": "/19/items/hy0_hooting_yard_2004-04-14"
}

SAMPLE_TEXT_CONTENT = "This is a test transcript\nof the episode content."


def test_scanner_initialization():
    """Test that scanner initializes with correct default values."""
    scanner = ArchiveOrgScanner()

    assert scanner.rate_limit_delay == 1.0
    assert isinstance(scanner.client, ArchiveOrgClient)


def test_scanner_initialization_with_params():
    """Test scanner initialization with custom parameters."""
    mock_client = Mock(spec=ArchiveOrgClient)
    scanner = ArchiveOrgScanner(client=mock_client, rate_limit_delay=2.5)

    assert scanner.client is mock_client
    assert scanner.rate_limit_delay == 2.5


def test_search_collection_single_page():
    """Test searching a collection with single page of results."""
    mock_client = Mock(spec=ArchiveOrgClient)
    mock_client.search_collection.return_value = SAMPLE_SEARCH_RESPONSE

    scanner = ArchiveOrgScanner(client=mock_client, rate_limit_delay=0.1)

    with patch('time.sleep'):  # Speed up test
        episodes = scanner._search_collection("hooting-yard")

    assert len(episodes) == 2
    assert episodes[0]["identifier"] == "hy0_hooting_yard_2004-04-14"
    assert episodes[1]["identifier"] == "hy0_hooting_yard_2004-04-21"

    mock_client.search_collection.assert_called_once_with(
        "hooting-yard",
        rows=100,
        page=1,
        sort="date asc"
    )


def test_search_collection_multiple_pages():
    """Test searching a collection with multiple pages."""
    mock_client = Mock(spec=ArchiveOrgClient)

    # First page
    page1_response = {
        "response": {
            "numFound": 150,
            "docs": [{"identifier": f"episode_{i}", "title": f"Episode {i}"}
                    for i in range(100)]
        }
    }

    # Second page
    page2_response = {
        "response": {
            "numFound": 150,
            "docs": [{"identifier": f"episode_{i}", "title": f"Episode {i}"}
                    for i in range(100, 150)]
        }
    }

    # Third page (empty)
    page3_response = {
        "response": {
            "numFound": 150,
            "docs": []
        }
    }

    mock_client.search_collection.side_effect = [
        page1_response, page2_response, page3_response
    ]

    scanner = ArchiveOrgScanner(client=mock_client, rate_limit_delay=0.1)

    with patch('time.sleep'):  # Speed up test
        episodes = scanner._search_collection("hooting-yard")

    assert len(episodes) == 150
    assert episodes[0]["identifier"] == "episode_0"
    assert episodes[149]["identifier"] == "episode_149"

    assert mock_client.search_collection.call_count == 2  # Should stop when we have all 150


@patch('hooting_yard_migration.scan_archive_dot_org_episodes.urlopen')
def test_fetch_episode_metadata_success(mock_urlopen):
    """Test successful fetching of episode metadata."""
    # Mock the episode metadata response
    mock_client = Mock(spec=ArchiveOrgClient)

    # Create mock episode object that our client would return
    from hooting_yard_migration.retrieval.models import Episode, EpisodeMetadata, FileInfo

    metadata = EpisodeMetadata(
        identifier="hy0_hooting_yard_2004-04-14",
        title="Test Episode 1",
        creator="Frank Key",
        date=datetime(2004, 4, 14),
        collection=["hooting-yard", "podcasts"],
        description="Test episode description",
        mediatype="audio"
    )

    mp3_file = FileInfo(
        name="test_episode.mp3",
        format="VBR MP3",
        size=1000000,
        md5="test_md5_hash",
        length=600.0
    )

    episode_data = Episode(
        identifier="hy0_hooting_yard_2004-04-14",
        metadata=metadata,
        files=[mp3_file],
        server="ia801802.us.archive.org",
        dir="/19/items/hy0_hooting_yard_2004-04-14"
    )

    mock_client.get_episode_metadata.return_value = episode_data

    # Mock text content fetching
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(SAMPLE_EPISODE_METADATA).encode()
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None
    mock_urlopen.return_value = mock_response

    scanner = ArchiveOrgScanner(client=mock_client)
    episode = scanner._fetch_episode_metadata("hy0_hooting_yard_2004-04-14")

    assert episode is not None
    assert isinstance(episode, ArchiveOrgEpisode)
    assert episode.identifier == "hy0_hooting_yard_2004-04-14"
    assert episode.title == "Test Episode 1"
    assert episode.creator == "Frank Key"
    assert episode.mp3_filename == "test_episode.mp3"
    assert episode.mp3_size == 1000000
    assert episode.mp3_duration == 600.0
    assert episode.available is True


def test_fetch_episode_metadata_failure():
    """Test handling of metadata fetch failure."""
    mock_client = Mock(spec=ArchiveOrgClient)
    mock_client.get_episode_metadata.side_effect = Exception("Network error")

    scanner = ArchiveOrgScanner(client=mock_client)
    episode = scanner._fetch_episode_metadata("invalid_identifier")

    assert episode is None


@patch('hooting_yard_migration.scan_archive_dot_org_episodes.urlopen')
def test_extract_text_content_success(mock_urlopen):
    """Test successful text content extraction."""
    # Mock metadata response
    metadata_response = MagicMock()
    metadata_response.read.return_value = json.dumps(SAMPLE_EPISODE_METADATA).encode()
    metadata_response.__enter__.return_value = metadata_response
    metadata_response.__exit__.return_value = None

    # Mock text file response
    text_response = MagicMock()
    text_response.read.return_value = SAMPLE_TEXT_CONTENT.encode('utf-8')
    text_response.__enter__.return_value = text_response
    text_response.__exit__.return_value = None

    mock_urlopen.side_effect = [metadata_response, text_response]

    scanner = ArchiveOrgScanner()
    text_content = scanner._extract_text_content("hy0_hooting_yard_2004-04-14")

    assert text_content is not None
    assert "test_transcript.txt" in text_content
    assert SAMPLE_TEXT_CONTENT in text_content


@patch('hooting_yard_migration.scan_archive_dot_org_episodes.urlopen')
def test_extract_text_content_no_text_files(mock_urlopen):
    """Test text content extraction when no text files are available."""
    # Metadata with no text files
    metadata_no_text = {
        "files": [
            {
                "name": "audio.mp3",
                "format": "VBR MP3"
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(metadata_no_text).encode()
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None
    mock_urlopen.return_value = mock_response

    scanner = ArchiveOrgScanner()
    text_content = scanner._extract_text_content("hy0_hooting_yard_2004-04-14")

    assert text_content is None


def test_is_recently_scanned():
    """Test the recently scanned check."""
    scanner = ArchiveOrgScanner()

    # Episode scanned 1 hour ago (recent)
    recent_episode = ArchiveOrgEpisode(
        identifier="test",
        title="Test",
        date=datetime.now(),
        last_checked=datetime.now()
    )

    assert scanner._is_recently_scanned(recent_episode, hours=24) is True

    # Episode scanned 25 hours ago (not recent)
    from datetime import timedelta
    old_episode = ArchiveOrgEpisode(
        identifier="test",
        title="Test",
        date=datetime.now(),
        last_checked=datetime.now() - timedelta(hours=25)
    )

    assert scanner._is_recently_scanned(old_episode, hours=24) is False

    # Episode never scanned
    never_scanned = ArchiveOrgEpisode(
        identifier="test",
        title="Test",
        date=datetime.now(),
        last_checked=None
    )

    assert scanner._is_recently_scanned(never_scanned, hours=24) is False


def test_scan_all_episodes_new_state():
    """Test scanning all episodes with a new state."""
    mock_client = Mock(spec=ArchiveOrgClient)
    mock_client.search_collection.return_value = SAMPLE_SEARCH_RESPONSE

    # Mock episode fetching
    def mock_fetch(identifier):
        return ArchiveOrgEpisode(
            identifier=identifier,
            title=f"Episode {identifier}",
            date=datetime(2004, 4, 14),
            available=True,
            last_checked=datetime.now()
        )

    scanner = ArchiveOrgScanner(client=mock_client, rate_limit_delay=0.1)

    with patch.object(scanner, '_fetch_episode_metadata', side_effect=mock_fetch):
        with patch('time.sleep'):  # Speed up test
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                state = scanner.scan_all_episodes("hooting-yard", temp_path)

    assert len(state.episodes) == 2
    assert state.last_full_scan is not None
    assert "hy0_hooting_yard_2004-04-14" in state.episodes
    assert "hy0_hooting_yard_2004-04-21" in state.episodes


def test_scan_all_episodes_skip_recent():
    """Test that recently scanned episodes are skipped."""
    mock_client = Mock(spec=ArchiveOrgClient)
    mock_client.search_collection.return_value = SAMPLE_SEARCH_RESPONSE

    # Create existing state with recently scanned episode
    existing_state = ArchiveOrgState()
    recent_episode = ArchiveOrgEpisode(
        identifier="hy0_hooting_yard_2004-04-14",
        title="Recent Episode",
        date=datetime(2004, 4, 14),
        last_checked=datetime.now(),  # Recently scanned
        available=True
    )
    existing_state.add_episode(recent_episode)

    scanner = ArchiveOrgScanner(client=mock_client, rate_limit_delay=0.1)

    with patch.object(ArchiveOrgState, 'load_from_directory', return_value=existing_state):
        with patch.object(scanner, '_fetch_episode_metadata') as mock_fetch:
            mock_fetch.return_value = ArchiveOrgEpisode(
                identifier="hy0_hooting_yard_2004-04-21",
                title="New Episode",
                date=datetime(2004, 4, 21),
                available=True
            )

            with patch('time.sleep'):  # Speed up test
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    # Create the archive_org directory to simulate existing state
                    (temp_path / "archive_org").mkdir()

                    state = scanner.scan_all_episodes("hooting-yard", temp_path)

    # Should have both episodes, but only fetched metadata for one
    assert len(state.episodes) == 2
    assert mock_fetch.call_count == 1  # Only called for non-recent episode
    mock_fetch.assert_called_with("hy0_hooting_yard_2004-04-21")


def test_scanner_error_handling():
    """Test error handling during scanning."""
    mock_client = Mock(spec=ArchiveOrgClient)
    mock_client.search_collection.return_value = SAMPLE_SEARCH_RESPONSE

    scanner = ArchiveOrgScanner(client=mock_client, rate_limit_delay=0.1)

    # Mock fetch that raises exception for first episode
    def mock_fetch_with_error(identifier):
        if identifier == "hy0_hooting_yard_2004-04-14":
            raise Exception("Test error")
        return ArchiveOrgEpisode(
            identifier=identifier,
            title=f"Episode {identifier}",
            date=datetime(2004, 4, 14),
            available=True
        )

    with patch.object(scanner, '_fetch_episode_metadata', side_effect=mock_fetch_with_error):
        with patch('time.sleep'):  # Speed up test
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                state = scanner.scan_all_episodes("hooting-yard", temp_path)

    # Should have only the successful episode
    assert len(state.episodes) == 1
    assert "hy0_hooting_yard_2004-04-21" in state.episodes
    assert "hy0_hooting_yard_2004-04-14" not in state.episodes


def test_main_function_argument_parsing():
    """Test the main function's argument parsing."""
    from hooting_yard_migration.scan_archive_dot_org_episodes import main

    # Test that main function exists and can be imported
    assert callable(main)

    # Test with mock arguments would require more complex mocking
    # This is a basic smoke test that the function exists