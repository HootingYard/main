# Archive.org API Guide for Hooting Yard Content Retrieval

## Overview

This document provides comprehensive guidance on retrieving Hooting Yard content from archive.org. The complete collection is available at https://archive.org/details/hooting-yard and contains 526 episodes as of September 2024.

## API Endpoints

### 1. Search API (Advanced Search)

**Endpoint:** `https://archive.org/advancedsearch.php`

**Purpose:** Search and filter items with specific criteria

**Example Request:**
```bash
curl "https://archive.org/advancedsearch.php?q=collection:hooting-yard&fl=identifier,title,date,description,item_size&sort=date+asc&output=json&rows=10"
```

**Parameters:**
- `q`: Query (use `collection:hooting-yard` for all episodes)
- `fl`: Fields to return (comma-separated)
- `sort`: Sort order (e.g., `date asc`)
- `output`: Output format (`json`, `xml`, `csv`)
- `rows`: Number of results
- `page`: Page number for pagination

**Available Fields:**
- `identifier`: Unique item ID
- `title`: Episode title
- `date`: Broadcast date
- `description`: Episode contents with timestamps
- `creator`: "Frank Key"
- `item_size`: Total size in bytes
- `downloads`: Download count

### 2. Metadata API

**Endpoint:** `https://archive.org/metadata/{identifier}`

**Purpose:** Get detailed metadata for a specific item

**Example Request:**
```bash
curl "https://archive.org/metadata/hy0_hooting_yard_2004-04-14"
```

**Response Structure:**
```json
{
  "created": 1757897999,
  "d1": "ia601802.us.archive.org",
  "d2": "ia801802.us.archive.org",
  "dir": "/19/items/hy0_hooting_yard_2004-04-14",
  "files": [...],
  "metadata": {
    "identifier": "hy0_hooting_yard_2004-04-14",
    "collection": ["hooting-yard", "podcasts"],
    "creator": "Frank Key",
    "date": "2004-04-14",
    "description": "Episode content with timestamps...",
    "mediatype": "audio",
    "title": "Hooting Yard On The Air: Burnt Maps"
  }
}
```

### 3. Scrape API (Collection Statistics)

**Endpoint:** `https://archive.org/services/search/v1/scrape`

**Purpose:** Get collection statistics and complete item list

**Example Request:**
```bash
curl "https://archive.org/services/search/v1/scrape?q=collection:hooting-yard&count=10000"
```

**Response:**
```json
{
  "items": [...],
  "count": 526,
  "total": 526
}
```

## Download URLs

### Direct Download Pattern

MP3 files can be downloaded using this pattern:
```
https://archive.org/download/{identifier}/{filename}
```

Example:
```
https://archive.org/download/hy0_hooting_yard_2004-04-14/hooting_yard_2004-04-14.mp3
```

Note: These URLs redirect to CDN servers (e.g., `ia801802.us.archive.org`)

### File Types Available

Each episode typically includes:
- `.mp3` - Main audio file (VBR MP3 format)
- `.png` - Waveform visualization
- `_spectrogram.png` - Audio spectrogram
- `.afpk` - Columbia Peaks data
- `_meta.xml` - Metadata in XML format
- `_files.xml` - File listing

## Python Implementation Examples

### Using urllib (Standard Library)

```python
import json
from urllib.request import urlopen, urlretrieve
from urllib.parse import urlencode

def search_episodes(rows=10, page=1):
    """Search for Hooting Yard episodes."""
    params = {
        'q': 'collection:hooting-yard',
        'fl': 'identifier,title,date,description',
        'sort': 'date asc',
        'output': 'json',
        'rows': rows,
        'page': page
    }
    url = f"https://archive.org/advancedsearch.php?{urlencode(params)}"

    with urlopen(url) as response:
        data = json.loads(response.read())

    return data['response']['docs']

def get_episode_metadata(identifier):
    """Get detailed metadata for an episode."""
    url = f"https://archive.org/metadata/{identifier}"

    with urlopen(url) as response:
        data = json.loads(response.read())

    return data

def download_episode(identifier, output_path):
    """Download episode MP3 file."""
    # Get metadata to find MP3 filename
    metadata = get_episode_metadata(identifier)

    # Find MP3 file in files list
    mp3_file = None
    for file in metadata['files']:
        if file.get('format') == 'VBR MP3':
            mp3_file = file['name']
            break

    if not mp3_file:
        raise ValueError(f"No MP3 file found for {identifier}")

    # Download URL
    url = f"https://archive.org/download/{identifier}/{mp3_file}"

    # Download with progress
    urlretrieve(url, output_path)

    return output_path
```

### Using requests Library

```python
import requests

class ArchiveOrgClient:
    BASE_URL = "https://archive.org"

    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'HootingYard-Migration/1.0'
        })

    def search(self, collection='hooting-yard', **kwargs):
        """Search archive.org with parameters."""
        params = {
            'q': f'collection:{collection}',
            'output': 'json',
            **kwargs
        }

        response = self.session.get(
            f"{self.BASE_URL}/advancedsearch.php",
            params=params
        )
        response.raise_for_status()

        return response.json()

    def get_metadata(self, identifier):
        """Get item metadata."""
        response = self.session.get(
            f"{self.BASE_URL}/metadata/{identifier}"
        )
        response.raise_for_status()

        return response.json()

    def download_file(self, identifier, filename, output_path,
                     chunk_size=8192, progress_callback=None):
        """Download file with progress tracking."""
        url = f"{self.BASE_URL}/download/{identifier}/{filename}"

        response = self.session.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback:
                        progress_callback(downloaded, total_size)

        return output_path
```

### Using internetarchive Library

```python
from internetarchive import get_item, search_items, download

# Search for all episodes
def get_all_episodes():
    """Get all Hooting Yard episodes."""
    return search_items('collection:hooting-yard')

# Get specific episode
def get_episode(identifier):
    """Get episode item object."""
    return get_item(identifier)

# Download episode
def download_episode_ia(identifier, destdir='downloads'):
    """Download episode using internetarchive library."""
    item = get_item(identifier)

    # Download only MP3 files
    item.download(
        destdir=destdir,
        formats='VBR MP3',
        verbose=True,
        retries=3
    )

# Get metadata
def get_metadata_ia(identifier):
    """Get episode metadata."""
    item = get_item(identifier)
    return item.metadata
```

## Episode Identifiers

All Hooting Yard episodes follow this naming pattern:
```
hy0_hooting_yard_YYYY-MM-DD
```

Examples:
- `hy0_hooting_yard_2004-04-14` (first episode)
- `hy0_hooting_yard_2019-12-12` (last episode)

## Metadata Structure

### Episode Description Format

Descriptions contain story titles with timestamps:
```
Story Title 1 - HH:MM
Story Title 2 - HH:MM
Story Title 3 - HH:MM
```

Example:
```
Burnt Maps - 05:09
Today's Recipe - 09:37
Dark Star Crashes - 10:45
```

### File Metadata

Each MP3 file includes:
- `length`: Duration in seconds (e.g., "1771.86")
- `size`: File size in bytes
- `md5`: MD5 checksum for verification
- `format`: "VBR MP3"
- `title`, `creator`, `album`, `genre`: ID3 tags

## Rate Limiting and Best Practices

### Request Limits
- No official rate limit documented
- Recommended: 2-3 requests per second
- Use persistent HTTP sessions for efficiency

### Best Practices

1. **Use Checksums**: Verify downloads with MD5 hashes
2. **Handle Redirects**: Download URLs redirect to CDN servers
3. **Retry Logic**: Implement exponential backoff for failures
4. **Parallel Downloads**: Limit to 3-5 concurrent downloads
5. **Cache Metadata**: Store metadata locally to reduce API calls
6. **User-Agent**: Set descriptive User-Agent header

### Error Handling

Common HTTP status codes:
- `200`: Success
- `302`: Redirect (normal for downloads)
- `404`: Item not found
- `503`: Service temporarily unavailable

## Complete Retrieval Workflow

```python
import json
import time
from pathlib import Path
from urllib.request import urlopen, urlretrieve

def retrieve_all_episodes(output_dir='downloads'):
    """Complete workflow to retrieve all episodes."""

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Step 1: Get complete episode list
    print("Fetching episode list...")
    url = "https://archive.org/advancedsearch.php?q=collection:hooting-yard&fl=identifier,date,title&sort=date+asc&output=json&rows=1000"

    with urlopen(url) as response:
        data = json.loads(response.read())

    episodes = data['response']['docs']
    print(f"Found {len(episodes)} episodes")

    # Step 2: Process each episode
    for i, episode in enumerate(episodes, 1):
        identifier = episode['identifier']
        date = episode['date'][:10]  # YYYY-MM-DD
        year = date[:4]

        # Create year directory
        year_dir = output_dir / year
        year_dir.mkdir(exist_ok=True)

        # Check if already downloaded
        mp3_path = year_dir / f"{identifier.replace('hy0_', '')}.mp3"
        if mp3_path.exists():
            print(f"[{i}/{len(episodes)}] Skipping {identifier} - already exists")
            continue

        print(f"[{i}/{len(episodes)}] Processing {identifier}")

        # Step 3: Get metadata
        metadata_url = f"https://archive.org/metadata/{identifier}"
        with urlopen(metadata_url) as response:
            metadata = json.loads(response.read())

        # Step 4: Find MP3 file
        mp3_file = None
        for file in metadata['files']:
            if file.get('format') == 'VBR MP3':
                mp3_file = file['name']
                mp3_size = file.get('size', 0)
                mp3_md5 = file.get('md5')
                break

        if not mp3_file:
            print(f"  Warning: No MP3 found for {identifier}")
            continue

        # Step 5: Download MP3
        download_url = f"https://archive.org/download/{identifier}/{mp3_file}"
        print(f"  Downloading {mp3_file} ({mp3_size / 1024 / 1024:.1f} MB)...")

        try:
            urlretrieve(download_url, mp3_path)
            print(f"  Saved to {mp3_path}")
        except Exception as e:
            print(f"  Error downloading: {e}")
            continue

        # Step 6: Save metadata
        metadata_path = year_dir / f"{identifier.replace('hy0_', '')}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata['metadata'], f, indent=2)

        # Rate limiting
        time.sleep(1)

    print("Download complete!")
```

## Useful Collection URLs

- **Main Collection**: https://archive.org/details/hooting-yard
- **RSS Feed**: https://archive.org/services/collection-rss.php?collection=hooting-yard
- **All Items JSON**: https://archive.org/advancedsearch.php?q=collection:hooting-yard&output=json&rows=1000
- **Torrent Files**: Available for each episode (see `_archive.torrent` files)

## Integration with Existing Project Data

The project already contains:
- **Transcripts**: 521 files in `analysis/transcripts/` matching pattern `hooting_yard_YYYY-MM-DD.txt`
- **Story Metadata**: YAML files in `analysis/stories/`
- **Episode Index**: Mappings in `analysis/index/shows_to_stories.yaml`

These can be cross-referenced with archive.org data using the date portion of identifiers.

## Summary

The archive.org API provides comprehensive access to all 526 Hooting Yard episodes. The combination of Search API for discovery, Metadata API for details, and direct download URLs provides a complete solution for content retrieval. The existing project metadata can enhance the archive.org data with transcripts and story mappings.