#!/usr/bin/env python3
"""Download a YouTube transcript (auto-generated or manual captions) and
save as markdown to sources/transcripts/.

Two extraction paths, tried in order:

  1. youtube-transcript-api — fast, no auth needed, but YouTube blocks
     many residential / VPN / cloud IP ranges with "YouTube is blocking
     requests from your IP".

  2. yt-dlp fallback — used automatically when the API path fails, OR
     unconditionally when --cookies is supplied. yt-dlp uses different
     network paths than the API and combined with authenticated cookies
     (see scripts/tools/extract-firefox-cookies.py) reliably reaches
     YouTube when the API path is blocked.

Usage:
    transcribe.py URL                              # API only; fallback to yt-dlp on failure
    transcribe.py URL --cookies /tmp/yt.txt        # skip API; yt-dlp with cookies from file
    transcribe.py URL --cookies -                  # skip API; yt-dlp with cookies from stdin
                                                   #   (cookies never touch disk)
    transcribe.py URL --slug custom-name           # custom output filename
    transcribe.py URL --raw                        # also save raw segments JSON

Stdin-cookies workflow (cookies stay in process memory throughout):

    # Single-video chain:
    extract-firefox-cookies.py --stdout | transcribe.py URL --cookies -

    # Multi-video with shell variable (extract once, transcribe many):
    COOKIES=$(extract-firefox-cookies.py --stdout)
    printf '%s' "$COOKIES" | transcribe.py URL1 --cookies -
    printf '%s' "$COOKIES" | transcribe.py URL2 --cookies -
    unset COOKIES

Cookies are produced by scripts/tools/extract-firefox-cookies.py (see
its docstring for Firefox-side prereqs).

Requires: youtube-transcript-api  (pip install youtube-transcript-api)
Optional: yt-dlp                  (pip install yt-dlp)
          deno                    (for yt-dlp JS challenge solver; only
                                   needed for video downloads, not for
                                   caption-only extraction)
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import REPO_ROOT  # noqa: E402

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
    ``{text, start, duration}`` dicts. Raises RuntimeError on any
    failure (caller decides whether to fall back)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        raise RuntimeError("youtube-transcript-api not installed (pip install youtube-transcript-api)")

    try:
        return YouTubeTranscriptApi().fetch(video_id).to_raw_data()
    except Exception as e:
        raise RuntimeError(f"youtube-transcript-api failed: {e}")


def fetch_via_ytdlp(video_id, cookies_path=None):
    """Fall back to yt-dlp when youtube-transcript-api is blocked or
    when the caller explicitly opts in via --cookies. Downloads JSON3
    captions, converts to the same ``{text, start, duration}`` shape
    fetch_via_api returns.

    ``cookies_path`` accepts a file path OR the literal string ``"-"``
    to read cookies from this process's stdin and pipe them to yt-dlp's
    stdin (zero disk write — cookies stay in process memory)."""
    if not shutil.which("yt-dlp"):
        raise RuntimeError("yt-dlp not installed (pip install yt-dlp)")

    stdin_cookies = None
    if cookies_path == "-":
        stdin_cookies = sys.stdin.read()
        if not stdin_cookies.strip():
            raise RuntimeError("--cookies - was set but stdin was empty")

    with tempfile.TemporaryDirectory(prefix="transcribe-ytdlp-") as tmpdir:
        output_stem = f"{tmpdir}/cap"
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-lang", "en",
            "--sub-format", "json3",
            "--ignore-no-formats-error",
            "-o", output_stem,
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        if cookies_path == "-":
            # yt-dlp's stdin-cookies syntax is /dev/stdin (Linux-specific).
            # The bare "-" form is silently ignored without auth — verified
            # 2026-05-17. Stays in-process: input=stdin_cookies pipes the
            # data via kernel pipe to yt-dlp's stdin which it reads via
            # /dev/stdin. No tmp file written.
            cmd[1:1] = ["--cookies", "/dev/stdin"]
        elif cookies_path:
            cmd[1:1] = ["--cookies", str(cookies_path)]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                input=stdin_cookies,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"yt-dlp failed:\n{e.stderr}")

        json3_path = f"{output_stem}.en.json3"
        if not os.path.exists(json3_path):
            raise RuntimeError(
                "yt-dlp completed but wrote no captions file. "
                "Video may have no English captions available."
            )

        with open(json3_path) as f:
            data = json.load(f)
        return _json3_to_segments(data)


def _json3_to_segments(data):
    """Convert yt-dlp JSON3 event format to the
    ``{text, start, duration}`` shape used by render_markdown.
    Skips window-setup events with no ``segs`` array and empty-text
    events."""
    segments = []
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if not text:
            continue
        segments.append({
            "text": text,
            "start": ev.get("tStartMs", 0) / 1000.0,
            "duration": ev.get("dDurationMs", 0) / 1000.0,
        })
    return segments


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
    parser.add_argument("--cookies", help=(
        "Path to a Netscape-format cookies.txt, OR the literal '-' to "
        "read cookies from stdin (no disk write). When supplied, the "
        "API path is skipped and yt-dlp is used directly. See "
        "extract-firefox-cookies.py for the cookies-acquisition workflow."
    ))
    parser.add_argument("--raw", action="store_true", help="Also save raw segments JSON")
    args = parser.parse_args()

    video_id = extract_video_id(args.url)
    if not video_id:
        sys.exit(f"ERROR: Could not extract video ID from: {args.url}")

    slug = args.slug or video_id
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch path selection:
    #   --cookies set → user explicitly wants yt-dlp; skip API
    #   otherwise → API first, yt-dlp fallback on failure
    segments = None
    if args.cookies:
        print("(--cookies supplied; using yt-dlp directly)", file=sys.stderr)
        try:
            segments = fetch_via_ytdlp(video_id, args.cookies)
        except RuntimeError as e:
            sys.exit(f"ERROR: {e}")
    else:
        try:
            segments = fetch_via_api(video_id)
        except RuntimeError as api_err:
            print(f"(API path failed: {api_err})", file=sys.stderr)
            print("(falling back to yt-dlp; supply --cookies if auth is needed)", file=sys.stderr)
            try:
                segments = fetch_via_ytdlp(video_id, cookies_path=None)
            except RuntimeError as ytdlp_err:
                sys.exit(f"ERROR: yt-dlp fallback also failed:\n  {ytdlp_err}")

    md_path = TRANSCRIPTS_DIR / f"{slug}-downloaded.md"
    md_path.write_text(render_markdown(segments, args.url, video_id, slug))
    print(f"✓ Saved {md_path.relative_to(REPO_ROOT)}")

    if args.raw:
        raw_path = TRANSCRIPTS_DIR / f"{slug}-raw.json"
        raw_path.write_text(json.dumps(segments, indent=2))
        print(f"✓ Saved {raw_path.relative_to(REPO_ROOT)}")

    print()
    print("Next: register source in manifest:")
    print(f"  python3 scripts/tools/manifest.py add {args.url} --path transcripts/{slug}-downloaded.md --format transcript")


if __name__ == "__main__":
    main()
