#!/usr/bin/env python3
"""Integration test for downloading a real episode from Archive.org.

This script tests the actual download functionality with a real episode.
Run with: python tests/integration_test_download.py
"""

import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hooting_yard_migration.retrieval import EpisodeDownloader, ArchiveOrgClient


def test_real_download():
    """Test downloading a real episode from Archive.org."""
    print("=" * 60)
    print("Integration Test: Download Real Episode from Archive.org")
    print("=" * 60)

    # Create temporary directory for download
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"\nUsing temporary directory: {temp_path}")

        # Create client and downloader
        client = ArchiveOrgClient()
        downloader = EpisodeDownloader(client=client)

        # Test episode identifier (first Hooting Yard episode)
        identifier = "hy0_hooting_yard_2004-04-14"
        url = f"https://archive.org/details/{identifier}"

        print(f"\nDownloading episode: {identifier}")
        print(f"URL: {url}")

        # Progress tracking
        def progress_callback(downloaded, total):
            if total:
                percent = (downloaded / total) * 100
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                print(f"Progress: {mb_downloaded:.1f}/{mb_total:.1f} MB ({percent:.1f}%)", end="\r")

        # Download the episode
        result = downloader.download_episode(
            identifier,
            temp_path,
            progress_callback=progress_callback,
        )

        print()  # New line after progress

        # Display results
        if result.success:
            print("\n✅ Download successful!")
            print(f"\nEpisode Details:")
            print(f"  Identifier: {result.episode_identifier}")
            print(f"  Title: {result.metadata.title}")
            print(f"  Creator: {result.metadata.creator}")
            print(f"  Date: {result.metadata.date.strftime('%Y-%m-%d')}")
            print(f"\nFile Details:")
            print(f"  Path: {result.file_path}")
            print(f"  Size: {result.file_size / (1024 * 1024):.1f} MB")
            print(f"  MD5: {result.md5_hash}")
            print(f"  Download time: {result.download_time:.1f} seconds")

            # Verify file exists
            if result.file_path.exists():
                print(f"\n✅ File exists at: {result.file_path}")
                actual_size = result.file_path.stat().st_size
                print(f"  Actual size on disk: {actual_size / (1024 * 1024):.1f} MB")
            else:
                print(f"\n❌ File not found at expected path!")

            # Show first part of description
            if result.metadata.description:
                print(f"\nEpisode Description (first 200 chars):")
                print(f"  {result.metadata.description[:200]}...")

        else:
            print(f"\n❌ Download failed!")
            print(f"  Error: {result.error_message}")

        # Test downloading from URL
        print("\n" + "-" * 40)
        print("Testing download from full URL...")

        result2 = downloader.download_episode_from_url(
            url,
            temp_path,
        )

        if result2.success:
            print("✅ URL download successful!")
            # File should already exist from first download
            if result.file_path == result2.file_path:
                print("  (Same file as previous download)")
        else:
            print(f"❌ URL download failed: {result2.error_message}")

        # List all files in temp directory
        print(f"\nFiles in temporary directory:")
        for file in temp_path.iterdir():
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f"  - {file.name} ({size_mb:.1f} MB)")

    # After exiting context manager, temp directory is cleaned up
    print("\n✅ Temporary directory cleaned up")
    print("\nIntegration test complete!")


def test_metadata_only():
    """Test fetching metadata without downloading."""
    print("\n" + "=" * 60)
    print("Test: Fetch Metadata Only")
    print("=" * 60)

    client = ArchiveOrgClient()

    # Get episode metadata
    identifier = "hy0_hooting_yard_2004-04-14"
    print(f"\nFetching metadata for: {identifier}")

    episode = client.get_episode_metadata(identifier)

    print(f"\nEpisode Information:")
    print(f"  Identifier: {episode.identifier}")
    print(f"  Title: {episode.metadata.title}")
    print(f"  Date: {episode.metadata.date}")
    print(f"  Collections: {', '.join(episode.metadata.collection)}")
    print(f"  Server: {episode.server}")

    print(f"\nFiles in episode:")
    for file in episode.files:
        size_mb = file.size / (1024 * 1024) if file.size else 0
        print(f"  - {file.name} ({file.format}) - {size_mb:.1f} MB")

    if episode.mp3_file:
        print(f"\nMain MP3 file:")
        print(f"  Name: {episode.mp3_file.name}")
        print(f"  Size: {episode.mp3_file.size / (1024 * 1024):.1f} MB")
        print(f"  Duration: {episode.mp3_file.length:.1f} seconds")
        print(f"  MD5: {episode.mp3_file.md5}")
        print(f"  Download URL: {episode.download_url}")


def test_collection_search():
    """Test searching the collection."""
    print("\n" + "=" * 60)
    print("Test: Search Collection")
    print("=" * 60)

    client = ArchiveOrgClient()

    # Get collection count
    count = client.get_collection_count("hooting-yard")
    print(f"\nTotal episodes in collection: {count}")

    # Search for first 5 episodes
    print("\nSearching for first 5 episodes...")
    result = client.search_collection(
        "hooting-yard",
        fields=["identifier", "title", "date"],
        rows=5,
        sort="date asc",
    )

    print(f"Found {result['response']['numFound']} total episodes")
    print("\nFirst 5 episodes:")
    for doc in result["response"]["docs"]:
        date = doc.get("date", "Unknown date")
        if isinstance(date, str) and "T" in date:
            date = date.split("T")[0]
        print(f"  - {date}: {doc['identifier']}")
        print(f"    {doc.get('title', 'No title')}")


if __name__ == "__main__":
    try:
        # Run tests
        test_metadata_only()
        test_collection_search()
        test_real_download()

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)