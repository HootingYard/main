# Technical Specification: Hooting Yard Archive-to-YouTube Migration

## Objective

Migrate the complete collection of Hooting Yard radio show episodes from archive.org to YouTube, converting each audio recording into a simple video with a static image and scheduled weekly release. The process must be scriptable, resumable, lightweight, and minimally dependent on third-party infrastructure.

## High-Level Workflow

1. Discover and retrieve audio episodes and metadata from archive.org
2. Convert each audio episode into a video with a static image using FFmpeg
3. Upload and schedule each video to YouTube using the YouTube Data API
4. Record progress using per-episode YAML files to allow safe resumption

## System Architecture

### 1. Retrieval Component

**Source:** Public archive.org collection of Hooting Yard (e.g., by year)

**Files to retrieve per episode:**
- `.mp3` (primary audio content)
- Metadata: title, description, date (scraped or pulled from archive.org metadata)
- Transcript: embedded in metadata or stored as `.txt`/`.html`

**Method:**
- Use direct HTTP downloads or archive.org's metadata API
- Store downloaded content in a local workspace (e.g., `downloads/YYYY/filename.mp3`)

### 2. Conversion Component

**Tool:** FFmpeg

**Input:**
- Static image (e.g., `assets/hooting-yard-cover.jpg`)
- Audio file (`.mp3`)

**Output:**
- `.mp4` video of fixed resolution and bitrate
- Video duration = audio duration

**Command template:**
```bash
ffmpeg -loop 1 -i cover.jpg -i episode.mp3 -shortest \
  -c:v libx264 -c:a aac -b:a 192k -pix_fmt yuv420p \
  -vf "scale=1280:720" output.mp4
```

### 3. Upload and Scheduling Component

**Tool:** YouTube Data API v3 via Python client

**Authentication:** OAuth 2.0 (manual consent required once)

**Per-video metadata:**
- Title (from archive.org metadata)
- Description (including transcript and episode info)
- Scheduled publish date (weekly interval)

**Scheduling strategy:**
- Start date configurable (e.g., `2025-10-01T10:00:00Z`)
- Subsequent videos published every 7 days

### 4. State Management

**Format:** One YAML file per processed episode

**Filename:** `processed/YYYY/hoot-episode-012.yaml`

**Contents:**
```yaml
episode_id: hoot-episode-012
source_url: https://archive.org/details/hoot-episode-012
audio_file: downloads/2012/hoot-episode-012.mp3
video_file: rendered/hoot-episode-012.mp4
youtube_video_id: a1b2c3d4e5
published_at: 2025-10-15T10:00:00Z
status: uploaded
```

**Purpose:**
- Prevent duplication
- Allow paused/resumed runs

## Dependencies

### Runtime Environment
- Python 3.8+
- FFmpeg (available in system PATH)
- Git Bash (or Bash-compatible shell on Windows/macOS/Linux)

### Python Libraries
- `google-api-python-client`
- `oauth2client` or `google-auth`
- `requests`
- `PyYAML`

### Optional CLI Tools
- `wget` or `curl` for bulk downloads
- `jq` (if scripting with JSON output from archive.org)

## Configuration

### Example: `config.yaml`

```yaml
archive_org_collection_url: https://archive.org/details/hooting-yard-2012
output_directory: ./downloads
cover_image_path: ./assets/hoot-cover.jpg
youtube_upload_start_date: 2025-10-01T10:00:00Z
schedule_interval_days: 7
processed_directory: ./processed
```

## Failure Modes & Resilience

| Component      | Failure Mode                         | Mitigation                               |
|----------------|--------------------------------------|------------------------------------------|
| Retrieval      | Network timeout, missing file        | Retry logic, skip with warning          |
| Conversion     | FFmpeg error                         | Halt or log and skip                    |
| Upload         | YouTube quota exceeded, auth expired | Retry with backoff, manual auth refresh |
| State tracking | YAML write failure                   | Atomic file writes; abort on failure    |

## Deliverables

**Fully functional Python script or CLI tool:**
- `migrate-hoot.py` or similar

**Directory structure:**
```
/downloads
/rendered
/processed
/assets/hoot-cover.jpg
config.yaml
```

**OAuth credentials file:** `client_secret.json`

**README with setup and usage instructions**