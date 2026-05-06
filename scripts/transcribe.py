#!/usr/bin/env python3
"""
Download a YouTube transcript (auto-generated or manual captions) and save
as markdown to sources/transcripts/.

Usage:
  transcribe.py URL
  transcribe.py URL --slug custom-name
  transcribe.py URL --raw              # also save raw JSON segments

Requires: yt-dlp (for fallback) OR youtube-transcript-api.
Install:  pip install youtube-transcript-api
"""

import argparse
import json
import re
import sys
from datetime import date

from lib._common import REPO_ROOT

TRANSCRIPTS_DIR = REPO_ROOT / "sources" / "transcripts"


def extract_video_id(url):
    for pattern in [
        r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def fetch_via_api(video_id):
    """Fetch transcript via youtube-transcript-api. Returns list of
    ``{text, start, duration}`` dicts via the instance method
    ``YouTubeTranscriptApi().fetch(video_id).to_raw_data()``.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("ERROR: pip install youtube-transcript-api", file=sys.stderr)
        sys.exit(1)

    try:
        return YouTubeTranscriptApi().fetch(video_id).to_raw_data()
    except Exception as e:
        print(f"ERROR fetching transcript: {e}", file=sys.stderr)
        sys.exit(1)


def format_timestamp(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def render_markdown(segments, url, video_id, slug):
    today = date.today().isoformat()
    lines = [
        f"# YouTube Transcript — {slug}",
        "",
        f"Source URL: {url}",
        f"Video ID: {video_id}",
        f"Downloaded: {today}",
        "",
        "---",
        "",
    ]
    for seg in segments:
        ts = format_timestamp(seg.get("start", 0))
        text = seg.get("text", "").replace("\n", " ")
        lines.append(f"[{ts}] {text}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url")
    parser.add_argument("--slug", help="Output slug (default: video ID)")
    parser.add_argument("--raw", action="store_true", help="Also save raw JSON")
    args = parser.parse_args()

    video_id = extract_video_id(args.url)
    if not video_id:
        sys.exit(f"ERROR: Could not extract video ID from: {args.url}")

    slug = args.slug or video_id
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    segments = fetch_via_api(video_id)

    md_path = TRANSCRIPTS_DIR / f"{slug}-downloaded.md"
    md_path.write_text(render_markdown(segments, args.url, video_id, slug))
    print(f"✓ Saved {md_path.relative_to(REPO_ROOT)}")

    if args.raw:
        raw_path = TRANSCRIPTS_DIR / f"{slug}-raw.json"
        raw_path.write_text(json.dumps(segments, indent=2))
        print(f"✓ Saved {raw_path.relative_to(REPO_ROOT)}")

    print()
    print("Next: register source in manifest:")
    print(f"  python3 scripts/manifest.py add {args.url} --path transcripts/{slug}-downloaded.md --format transcript")


if __name__ == "__main__":
    main()
