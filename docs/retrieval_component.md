# Retrieval Component Documentation

## Overview

The Retrieval Component is responsible for discovering and downloading Hooting Yard episodes from archive.org. This component interfaces with the Internet Archive API to locate episodes, extract metadata, and download audio files along with associated content.

## Architecture

### Core Responsibilities

1. **Episode Discovery**: Automatically locate all Hooting Yard episodes on archive.org
2. **Metadata Extraction**: Parse and store episode metadata (title, date, description, transcripts)
3. **Content Download**: Efficiently download MP3 files and associated materials
4. **Progress Tracking**: Maintain state to support resumable downloads
5. **Data Organization**: Store downloaded content in a structured directory hierarchy

## Implementation Details

### Archive.org API Integration

The component uses two primary API endpoints:

1. **Search API**: `https://archive.org/advancedsearch.php`
   - Query parameters: `q=hooting+yard`, `output=json`
   - Returns list of matching items with basic metadata
   - Supports pagination for large result sets

2. **Metadata API**: `https://archive.org/metadata/{identifier}`
   - Returns detailed metadata for specific items
   - Includes file listings, checksums, and download URLs

### Data Sources

Based on analysis of existing project metadata:

- **Archive.org Collection**: https://archive.org/details/hooting-yard - Complete collection containing 555+ episodes
- **Episode Identifiers**: Follow pattern `hy0_hooting_yard_YYYY-MM-DD`
- **Local Transcripts**: Available in `analysis/transcripts/` (521 files)
- **Story Mappings**: Available in `analysis/stories/` and `analysis/index/`

### Episode Metadata Structure

Each episode contains:
```yaml
identifier: hy0_hooting_yard_2004-05-12
title: "Hooting Yard On The Air: The Names of the Ponds"
creator: Frank Key
date: 2004-05-12
description: |
  Hello Darkness My Old Friend - 00:43
  The Names of the Ponds - 05:01
  ...
format: VBR MP3
duration: 1851.09
downloads: 171
files:
  - mp3: hooting_yard_2004-05-12.mp3
  - size: 29631348
  - md5: 2a1da1756f8f8c9fb6edb720c2c5d622
```

### Directory Structure

```
downloads/
├── 2004/
│   ├── hooting_yard_2004-04-14.mp3
│   ├── hooting_yard_2004-04-14.json
│   └── hooting_yard_2004-04-14.txt
├── 2005/
│   └── ...
└── metadata/
    └── episode_index.json
```

## Key Classes and Methods

### ArchiveRetriever

Main class responsible for episode retrieval.

```python
class ArchiveRetriever:
    def __init__(self, config: Config):
        """Initialize with configuration settings."""

    async def discover_episodes(self) -> List[Episode]:
        """Discover all available episodes from archive.org."""

    async def download_episode(self, episode: Episode) -> Path:
        """Download a single episode with retry logic."""

    def get_local_transcript(self, episode: Episode) -> Optional[str]:
        """Match episode with local transcript if available."""
```

### Episode

Data class representing a single episode.

```python
@dataclass
class Episode:
    identifier: str
    title: str
    date: datetime
    description: str
    audio_url: str
    duration: float
    file_size: int
    md5_hash: str
    local_transcript: Optional[Path] = None
    stories: List[StoryReference] = field(default_factory=list)
```

## Error Handling

### Network Failures
- Implements exponential backoff with max 3 retries
- Configurable timeout (default 30 seconds)
- Logs failed downloads for manual intervention

### Data Validation
- Verifies MD5 checksums after download
- Validates file size matches metadata
- Checks audio file integrity using mutagen library

### Resume Capability
- Tracks download progress in SQLite database
- Supports HTTP range requests for partial downloads
- Maintains download queue for batch processing

## Configuration

```yaml
retrieval:
  api_base_url: https://archive.org
  collection: hooting-yard
  concurrent_downloads: 3
  retry_attempts: 3
  retry_delay: 5
  timeout: 30
  chunk_size: 8192
  verify_checksums: true
  use_local_transcripts: true
  transcript_path: ./analysis/transcripts
```

## Integration Points

### With Existing Project Data

1. **Transcript Matching**: Cross-references with files in `analysis/transcripts/`
2. **Story Mapping**: Uses `analysis/index/shows_to_stories.yaml` for story associations
3. **Archive Management**: Integrates with `archive_management` submodule utilities

### With Other Components

1. **Outputs to Conversion Component**: Downloaded MP3 files
2. **Provides to State Manager**: Episode metadata and download status
3. **Reports to CLI**: Progress updates and error messages

## Performance Considerations

- **Parallel Downloads**: Supports concurrent downloads (default: 3)
- **Bandwidth Management**: Configurable rate limiting
- **Storage Optimization**: Optional compression for archived episodes
- **Memory Efficiency**: Streams large files rather than loading into memory

## Testing Strategy

1. **Unit Tests**: Mock archive.org API responses
2. **Integration Tests**: Test with sample episodes
3. **Performance Tests**: Validate concurrent download handling
4. **Resilience Tests**: Simulate network failures and interruptions

## Future Enhancements

1. **Smart Caching**: Cache API responses to reduce requests
2. **Differential Updates**: Only download new episodes
3. **Alternative Sources**: Support backup download sources
4. **Transcript Enhancement**: OCR for image-based transcripts
5. **Metadata Enrichment**: Extract additional metadata from audio files