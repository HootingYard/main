# CLAUDE.md - Hooting Yard Migration Project

This file provides guidance to Claude Code (claude.ai/code) when working with the Hooting Yard migration tool.

## Project Overview

The Hooting Yard Migration Tool is a Python-based system that migrates 526 episodes from Archive.org to YouTube. It features:

- **Episode Discovery**: Scans Archive.org's hooting-yard collection for all episodes
- **State Management**: Three-part YAML-based state system (archive_org, processing_history, youtube)
- **Keyword Analysis**: Word frequency analysis for YouTube SEO optimization
- **Audio-to-Video Conversion**: FFmpeg-based conversion with cover images
- **YouTube Upload**: Automated publishing with metadata and scheduling

## Architecture

### State Management System
- `state/archive_org/`: Episode metadata from Archive.org including full text
- `state/processing_history/`: Migration progress tracking
- `state/youtube/`: Published episode tracking
- `state/keywords/`: Word frequency analysis for SEO

### Key Components
- **Configuration**: `config.yaml` with paths relative to project root
- **CLI Interface**: Poetry-based commands (`discover`, `keywords`, `download`, etc.)
- **Episode Models**: YAML-serializable dataclasses for state persistence
- **Keyword Analysis**: Stop word filtering and frequency mapping

## Path Management

**IMPORTANT**: All paths in `config.yaml` are resolved relative to the config file location (same directory as `pyproject.toml`). This ensures consistent path resolution across all modules.

## Development Practices

### Testing
- Use `poetry run pytest` for all tests
- Configuration tests validate path resolution
- Mock external APIs (Archive.org, YouTube) in unit tests

### Code Style
- Follow project CLAUDE.md preferences (type hints, Pathlib, etc.)
- Use Poetry for dependency management
- Maintain YAML-based human-readable state files

## Developer Diary

This project maintains a developer diary in `/diary/` to track progress, decisions, and learnings on a day-by-day basis.

### Diary Structure
- **Location**: `<project_root>/diary/`
- **Format**: One markdown file per significant work session or day
- **Naming**: `YYYY-MM-DD_brief-description.md`

### Entry Format
Each diary entry should include:

```markdown
# Development Diary Entry - YYYY-MM-DD

## Context
- **Date**: YYYY-MM-DD HH:MM UTC
- **Branch**: branch-name
- **Commit**: short-hash
- **Contributors**: Claude Code + User

## Problem Statement
What problem were we trying to solve? What was the user's request?

## Our Approach
What was our intended solution? What strategy did we take?

## Implementation
What specific changes did we make? Key files modified, features added, etc.

## Outcomes
- What worked well?
- What challenges did we encounter?
- How did we overcome difficulties?
- What did we learn?

## Next Steps
What remains to be done? What should we tackle next?
```

### When to Create Entries
- After completing significant features
- When making architectural changes
- After solving challenging problems
- Before/after major commits
- When learning something important about the codebase

### Benefits
- Provides context for future work
- Documents decision-making process
- Helps onboard new contributors
- Creates searchable project history
- Captures institutional knowledge

## Commands Reference

```bash
# Discovery and analysis
poetry run hooting-yard-migrate discover
poetry run hooting-yard-migrate keywords

# Pipeline operations
poetry run hooting-yard-migrate download
poetry run hooting-yard-migrate convert
poetry run hooting-yard-migrate upload

# Utilities
poetry run hooting-yard-migrate report
poetry run hooting-yard-migrate verify
```