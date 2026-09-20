"""
YouTube Transcript extraction module for Vend.

Given a public YouTube URL, extracts available captions and returns
structured transcript with timestamped segments and model-sized chunks.
Uses the youtube-transcript-api library (v1.2.4).

Price: 0.0005 XNO per successful extraction.
"""

import re
from typing import Optional


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    if not url or not isinstance(url, str):
        return None

    url = url.strip()

    # Standard watch URL
    match = re.search(r"(?:v=)([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)

    # Short URLs: youtu.be/VIDEO_ID
    match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)

    # Embed / shorts URLs
    match = re.search(
        r"(?:youtube\.com|m\.youtube\.com)/(?:embed|v|shorts)/([a-zA-Z0-9_-]{11})",
        url,
    )
    if match:
        return match.group(1)

    return None


def _format_citation(video_id: str, start_seconds: float) -> str:
    """Format a YouTube deep-link citation from start seconds."""
    minutes = int(start_seconds // 60)
    seconds = int(start_seconds % 60)
    return f"https://youtube.com/watch?v={video_id}&t={int(start_seconds)}s"


def _format_timestamp(seconds: float) -> str:
    """Format seconds to MM:SS."""
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def youtube_transcript(url: str, language: str = "en") -> dict:
    """Extract transcript from a YouTube video URL.

    Args:
        url: Public YouTube video URL (any standard format).
        language: Language code for captions (default "en").

    Returns:
        dict with:
          - video_id: extracted video ID
          - language: caption language actually used
          - is_generated: whether captions are auto-generated
          - segments: list of {text, start, duration}
          - chunks: model-sized chunks (~2400 chars) with citations
          - full_text: complete transcript as plain text
    """
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        VideoUnavailable,
        TranscriptsDisabled,
        VideoUnplayable,
        YouTubeRequestFailed,
    )

    video_id = extract_video_id(url)
    if not video_id:
        return {
            "error": "Could not extract video ID from URL. "
            "Supported formats: youtube.com/watch?v=..., youtu.be/..."
        }

    try:
        api = YouTubeTranscriptApi()
        tx = api.fetch(video_id, languages=[language])
    except VideoUnavailable:
        return {"error": "Video is unavailable (private, deleted, or region-blocked).", "video_id": video_id}
    except TranscriptsDisabled:
        return {"error": "Captions are disabled for this video.", "video_id": video_id}
    except VideoUnplayable:
        return {"error": "Video is unplayable (live stream, age-restricted, or DRM-protected).", "video_id": video_id}
    except YouTubeRequestFailed as e:
        return {"error": f"YouTube request failed: {str(e)[:150]}", "video_id": video_id}
    except Exception as e:
        return {"error": f"Failed to fetch transcript: {str(e)[:200]}", "video_id": video_id}

    # Build segments from FetchedTranscriptSnippet objects
    segments = []
    for snippet in tx:
        segments.append({
            "text": snippet.text,
            "start": snippet.start,
            "duration": snippet.duration,
        })

    if not segments:
        return {"error": "No caption segments found for this video.", "video_id": video_id}

    # Build full text
    full_text = " ".join(s["text"] for s in segments)

    # Build model-sized chunks (~2400 chars each)
    chunks = []
    current_chunk = ""
    chunk_start = 0.0
    chunk_idx = 0

    for seg in segments:
        if not current_chunk:
            chunk_start = seg["start"]

        if current_chunk and len(current_chunk) + len(seg["text"]) + 1 > 2400:
            # Finalize current chunk
            chunks.append({
                "index": chunk_idx,
                "text": current_chunk.strip(),
                "citation": {
                    "label": f"{_format_timestamp(chunk_start)}–{_format_timestamp(seg['start'])}",
                    "url": _format_citation(video_id, chunk_start),
                },
            })
            chunk_idx += 1
            current_chunk = ""

        if current_chunk:
            current_chunk += " "
        current_chunk += seg["text"]

    # Last chunk
    if current_chunk:
        last_start = segments[-1]["start"] if segments else 0
        chunks.append({
            "index": chunk_idx,
            "text": current_chunk.strip(),
            "citation": {
                "label": f"{_format_timestamp(chunk_start)}+",
                "url": _format_citation(video_id, chunk_start),
            },
        })

    return {
        "video_id": video_id,
        "language": tx.language_code if hasattr(tx, "language_code") else language,
        "is_generated": tx.is_generated if hasattr(tx, "is_generated") else True,
        "segment_count": len(segments),
        "full_text": full_text,
        "segments": segments,
        "chunks": chunks,
    }