# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the main repository for Hooting Yard, containing three Git submodules:
- **keyml**: Derived artifacts from the archival project containing books and website content
- **ubercoordinator**: Tools to manage the Big Book of Key and produce static websites, ebooks, and print books
- **analysis**: Analysis data including stories, transcripts, and indexes

## Common Development Tasks

### Initial Setup
```bash
# Initialize and update all submodules
./update.sh
# Or manually:
git submodule init
git submodule update --recursive
```

### Python Environment Setup
For the ubercoordinator module:
```bash
cd ubercoordinator
pip install -r requirements.txt
# Or for development:
python setup.py develop
```

### Running Main Scripts
```bash
# Test Big Book of Key XHTML files
python ubercoordinator/src/bigbook.py

# Generate static website
python ubercoordinator/src/make_website.py
```

## Architecture Overview

### Repository Structure
- **Git Submodules**: The project uses three separate repositories as submodules, allowing independent versioning while maintaining a unified workspace
- **Content Organization**: Static content (keyml) is separated from processing tools (ubercoordinator) and analytical data (analysis)

### Ubercoordinator Module
The core processing engine with the following key components:

- **bigbook.py**: Validates XHTML files against DTD and Schematron schemas, checks for broken links
- **make_website.py**: Generates static website from templates using Mako templating engine
  - Default paths: `~/Projects/HootingYard/` for source, `~/Projects/HootingYard.github.io/` for output
- **index.py**: Manages indexing of content across repositories
- **xhtml.py**: XHTML processing utilities
- **formatting.py**: Text formatting helpers
- **date_index.py**: Date-based content indexing

### Content Structure
- **keyml/archive-2003-2006**: Historical archive content
- **keyml/books**: Book content in various formats (LaTeX, KeyML, XHTML)
- **keyml/hooting-yard-home-page**: Website homepage content
- **analysis/stories**: Story analysis data
- **analysis/transcripts**: Transcript files
- **analysis/index**: Index data

### Template System
Uses Mako templates located in `ubercoordinator/templates/website/` for generating static HTML pages

## Key Dependencies

### Python Dependencies (ubercoordinator)
- lxml (4.6.2): XML/XHTML processing and validation
- Pillow (8.0.1): Image processing
- PyYAML (5.3.1): YAML configuration handling
- Mako (1.1.3): Template engine
- unidecode (1.1.2): Unicode text processing
- num2words (0.5.10): Number to word conversion

### External Tools
- FFmpeg: Required for audio/video processing (see docs/archive_org_to_youtube_migration.md)
- Git: For submodule management

## Developer Diary

All projects should maintain a developer diary in `<project_root>/diary/` to track progress, decisions, and learnings.

### Diary Structure
- **Location**: `<project_root>/diary/`
- **Format**: One markdown file per significant work session or day
- **Naming Convention**: `YYYY-MM-DD_brief-description.md`

### Entry Template
Each diary entry should follow this structure:

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
- After completing significant features or architectural changes
- When solving challenging problems or learning something important
- Before/after major commits or releases
- When making decisions that affect project direction
- After troubleshooting difficult bugs

### Benefits
- Provides context for future development work
- Documents decision-making process and rationale
- Helps onboard new contributors to the project
- Creates searchable project history and institutional knowledge
- Enables better project management and progress tracking