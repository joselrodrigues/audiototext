# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **audiototext** project - a Python-based video-to-text transcription tool that processes video files, converts them to audio, and transcribes the audio content using AI speech recognition services. It supports batch processing with both AI transcription and SRT subtitle extraction.

## Development Setup

This project uses **uv** as the package manager (not pip). To set up:

```bash
# Install dependencies
uv sync

# Run the main batch transcription
uv run python batch_transcribe.py

# Convert a single video to audio
uv run python video_to_audio.py

# Generate academic notes from transcripts
uv run python agents.py

# Process all transcripts to academic notes
uv run python agents.py batch

# Process a specific transcript
uv run python agents.py path/to/transcript.md
```

## Architecture

### Core Components

- **`batch_transcribe.py`** - Main entry point for batch video processing with AI transcription
- **`video_to_audio.py`** - FFmpeg wrapper utility for video-to-audio conversion  
- **`agents.py`** - LangGraph-based academic note generation system with deep research capabilities

### Directory Structure

```
input_videos/     # Source video files (*.mp4, *.avi, *.mov, etc.)
output_audio/     # Converted WAV audio files  
transcripts/      # Generated transcription output (.md files)
knowledge_base/   # Academic notes generated from transcripts (Obsidian-compatible)
```

### Processing Pipeline

**Video-to-Text Pipeline:**
1. Scans `input_videos/` for supported video formats
2. Converts videos to WAV using FFmpeg
3. Chunks large audio files (>25MB) for API compatibility
4. Transcribes via local AI gateway (Whisper model at 192.168.1.85:8150)
5. Extracts text from accompanying SRT files if available
6. Saves organized transcripts in Markdown format with sanitized filenames

**Academic Note Generation Pipeline:**
1. Extracts content from transcript files
2. Identifies main academic concepts for deep research
3. Performs comprehensive research on each concept
4. Fact-checks and corrects transcript content against research
5. Finds academic references (books, papers, URLs)
6. Generates Obsidian-compatible academic notes with cross-references

## Configuration

- **AI Gateway**: `http://192.168.1.85:8150/cosmos/genai-gateway`
- **Chunk Size Limit**: 0.95MB for local gateway
- **Supported Formats**: .mp4, .avi, .mov, .mkv, .webm, .flv, .wmv
- **Output Format**: Markdown files with sanitized filenames (lowercase, hyphens)

## Dependencies

- **langgraph>=0.5.4** - AI workflow orchestration (planned usage)
- **openai>=1.97.1** - API client for transcription service
- **pydub>=0.25.1** - Audio processing and chunking
- **srt>=3.5.3** - Subtitle file parsing
- **tqdm>=4.67.1** - Progress bars

## File Naming Convention

The system automatically sanitizes filenames by:
- Converting to lowercase
- Replacing spaces and special characters with hyphens
- Maintaining directory structure from input to output
- Preventing duplicate processing by checking existing files

## External Dependencies

- **FFmpeg** - Required for video-to-audio conversion
- **Python 3.9+** - Specified in .python-version