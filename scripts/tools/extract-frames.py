#!/usr/bin/env python3
"""extract-frames.py — speaker-identification frame extraction for multi-speaker
video sources (panel discussions, interviews, conferences).

Whisper and YouTube auto-caption transcripts do not preserve speaker identity.
When a source has multiple people on camera (or a moderator + panelist + audience
question), a single transcript line may belong to any of them. This tool extracts
still frames at specified timestamps so a contributor (or a multimodal agent
reading the frames) can visually verify who is actively speaking — and
distinguish in-frame speakers from off-frame narration / voiceover by examining
mouth motion across a short burst of frames.

Four modes, dispatched as subcommands:

  anchor     — extract frames at preset early-timestamps (0:15, 0:30, 1:00,
               2:00, 5:00) to anchor each on-camera speaker's visual identity
               before contested-passage analysis.

  burst      — for each timestamp, extract N frames spanning ~T seconds and
               combine them into a contact-sheet jpg. Mouth motion across the
               burst distinguishes active speech (mouth shapes vary) from
               listening (mouth closed / static) and from B-roll / narration
               (no on-camera speaker at all). Default mode for ad-hoc speaker
               identification.

  sweep      — extract a burst every N seconds across a range. Useful for an
               initial visual map of an unfamiliar source.

  transcript — read a transcribed-source file (transcribe.py output or a
               whisper transcript), extract a burst at each [MM:SS] caption
               tick (or every Nth tick). Exhaustive coverage; produces many
               frames; pair with --every to throttle.

Every run writes a markdown index (``index.md``) to the output directory listing
each timestamp + contact-sheet path, so a session walking the frames with a
multimodal Read tool has a single navigable file to iterate through.

The contact sheet uses ffmpeg's tile filter — a single jpg with all burst
frames side by side. Default is 5 frames in a 5×1 row (320px per frame, ~1600px
wide total). Configurable via ``--count`` / ``--span`` / ``--tile``.

Output is idempotent — re-running with the same args overwrites cleanly.

Requires ``ffmpeg`` and ``ffprobe`` in PATH.

Usage examples:
  # Anchor mode — preset early-timestamps for speaker visual anchoring
  ./extract-frames.py anchor --video sources/video/foo.mp4

  # Burst mode — multiple contested timestamps with default 5-frame burst
  ./extract-frames.py burst --video sources/video/foo.mp4 \\
      --timestamps "44:53,45:00,45:09,45:20"

  # Sweep mode — every 30 seconds from 40:00 to 50:00
  ./extract-frames.py sweep --video sources/video/foo.mp4 \\
      --from 40:00 --to 50:00 --every 30

  # Transcript-driven — every 5th caption tick
  ./extract-frames.py transcript --video sources/video/foo.mp4 \\
      --transcript sources/transcripts/foo-whisper-transcript.txt --every 5

Lives at scripts/tools/ per the directory convention (contributor diagnostic,
not part of the build pipeline). See scripts/tools/VIDEO-PIPELINE.md for the
end-to-end workflow this tool is step 2 of.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# scripts/tools/extract-frames.py — put scripts/ on sys.path so
# `from lib._common` resolves from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import REPO_ROOT, SOURCES_DIR, normalize_source_rel_path


# ----------------------------------------------------------------------------
# Timestamp parsing / formatting
# ----------------------------------------------------------------------------

# Accepts MM:SS, H:MM:SS, MM:SS.fff, H:MM:SS.fff, or plain seconds (123 / 12.5).
_TS_RE = re.compile(
    r"^\s*(?:(\d+):)?(?:(\d+):)?(\d+(?:\.\d+)?)\s*$"
)


def parse_timestamp(ts: str) -> float:
    """Parse a timestamp string to seconds (float).

    Accepted forms: ``MM:SS``, ``H:MM:SS``, ``MM:SS.fff``, ``H:MM:SS.fff``,
    or plain seconds (``123`` / ``12.5``). Raises ``ValueError`` on
    unparseable input.
    """
    m = _TS_RE.match(ts)
    if not m:
        raise ValueError(f"unparseable timestamp: {ts!r}")
    parts = [p for p in m.groups() if p is not None]
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def format_filename(seconds: float) -> str:
    """Format seconds as a filename-safe timestamp (``HH-MM-SS`` or
    ``MM-SS`` for under-hour). Drops fractional seconds for filesystem
    cleanliness — fractional offsets are an implementation detail of
    burst sampling, not contributor-supplied addresses."""
    total = int(seconds)
    if total >= 3600:
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h:01d}-{m:02d}-{s:02d}"
    m, s = divmod(total, 60)
    return f"{m:02d}-{s:02d}"


def format_display(seconds: float) -> str:
    """Format seconds as a display timestamp (``H:MM:SS`` or ``MM:SS``)."""
    total = int(seconds)
    if total >= 3600:
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}"
    m, s = divmod(total, 60)
    return f"{m:02d}:{s:02d}"


# ----------------------------------------------------------------------------
# ffmpeg / ffprobe wrappers
# ----------------------------------------------------------------------------

def ensure_tools() -> None:
    """Verify ffmpeg + ffprobe are available; exit 2 with a contributor-
    friendly install hint if not."""
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            sys.exit(
                f"error: {tool} not found in PATH. Install ffmpeg "
                f"(includes ffprobe) — on Debian / Ubuntu / Kali: "
                f"sudo apt install ffmpeg"
            )


def probe_duration(video: Path) -> float:
    """Return video duration in seconds via ffprobe. Raises
    ``RuntimeError`` if ffprobe fails or returns unparseable output."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed on {video}: {proc.stderr.strip()[:200]}"
        )
    out = proc.stdout.strip()
    try:
        return float(out)
    except ValueError:
        raise RuntimeError(
            f"ffprobe returned unparseable duration for {video}: {out!r}"
        )


def extract_single_frame(
    video: Path, seconds: float, out_path: Path, q: int = 2
) -> bool:
    """Extract a single frame at ``seconds`` offset to ``out_path``. Returns
    True on success; prints ffmpeg stderr and returns False on failure.

    Uses ``-ss BEFORE -i`` (fast input-seek) since the videos we work with
    are typically multi-minute or hour-long and per-frame decode-from-start
    would be prohibitive. Modern ffmpeg input-seek is precise enough for
    speaker-identification frames (single-second granularity)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{seconds:.3f}", "-i", str(video),
        "-frames:v", "1", "-q:v", str(q), str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(
            f"  ffmpeg failed at {format_display(seconds)}: "
            f"{proc.stderr.strip()[:200]}",
            file=sys.stderr,
        )
        return False
    return True


def extract_contact_sheet(
    video: Path, start: float, span: float, count: int,
    out_path: Path, scale_width: int = 320, q: int = 2,
    tile: Optional[str] = None,
) -> bool:
    """Extract ``count`` frames evenly spaced over ``span`` seconds starting
    at ``start``, tiled into a single contact-sheet jpg at ``out_path``.

    Implementation uses ffmpeg's ``fps`` + ``scale`` + ``tile`` filter
    chain — a single decode pass produces the composite image, faster than
    N separate decodes. ``tile`` argument overrides the default Nx1
    horizontal row.

    The fps rate is computed as count/span. For count=5, span=2.0 →
    fps=2.5 → ffmpeg yields exactly 5 frames over the 2-second window.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fps = count / max(span, 0.001)
    if tile is None:
        tile = f"{count}x1"
    vf = (
        f"fps={fps},"
        f"scale={scale_width}:-1:flags=lanczos,"
        f"tile={tile}"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-t", f"{span:.3f}", "-i", str(video),
        "-vf", vf, "-frames:v", "1", "-q:v", str(q), str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(
            f"  ffmpeg failed at {format_display(start)} "
            f"(burst {count}×{span:.1f}s): "
            f"{proc.stderr.strip()[:200]}",
            file=sys.stderr,
        )
        return False
    return True


def extract_burst_individual(
    video: Path, start: float, span: float, count: int,
    out_dir: Path, q: int = 2,
) -> List[Path]:
    """Extract ``count`` frames evenly spaced over ``span`` seconds starting
    at ``start``, written as individual frame_NN.jpg files in ``out_dir``.
    Returns the list of paths written (empty on ffmpeg failure).

    Companion to ``extract_contact_sheet`` — same sampling math, different
    output layout. Useful when the contributor wants per-frame inspection
    rather than (or alongside) the tiled composite."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fps = count / max(span, 0.001)
    pattern = str(out_dir / "frame_%02d.jpg")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-t", f"{span:.3f}", "-i", str(video),
        "-vf", f"fps={fps}",
        "-q:v", str(q), pattern,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(
            f"  ffmpeg failed at {format_display(start)} "
            f"(burst {count}×{span:.1f}s individual frames): "
            f"{proc.stderr.strip()[:200]}",
            file=sys.stderr,
        )
        return []
    return sorted(out_dir.glob("frame_*.jpg"))


# ----------------------------------------------------------------------------
# Transcript parsing
# ----------------------------------------------------------------------------

# Matches [MM:SS] and [H:MM:SS] caption tick markers used by transcribe.py
# output and faster-whisper transcripts.
_TICK_RE = re.compile(r"\[(\d+:\d+(?::\d+)?)\]")


def parse_transcript_ticks(transcript_path: Path) -> List[float]:
    """Extract every [MM:SS] / [H:MM:SS] timestamp from a transcript file.

    Returns a sorted, deduplicated list of seconds. Empty list on missing
    file or no ticks found."""
    if not transcript_path.exists():
        return []
    text = transcript_path.read_text(encoding="utf-8", errors="replace")
    ticks = set()
    for m in _TICK_RE.finditer(text):
        try:
            ticks.add(parse_timestamp(m.group(1)))
        except ValueError:
            continue
    return sorted(ticks)


# ----------------------------------------------------------------------------
# Output index writer
# ----------------------------------------------------------------------------

def write_index(
    out_dir: Path,
    video: Path,
    duration: float,
    mode: str,
    extractions: List[dict],
) -> Path:
    """Write a markdown index of extractions to ``out_dir/index.md``.

    Each extraction dict carries: ``timestamp`` (seconds), ``contact_sheet``
    (Path, optional), ``frames`` (list of Paths, optional), ``label``
    (string, optional — e.g. 'anchor' / 'burst' / 'sweep' / 'tick').

    The markdown is structured so a multimodal agent reading the index can
    iterate timestamps in order, follow each contact_sheet path, and walk
    the source's speaker timeline systematically."""
    index_path = out_dir / "index.md"
    lines = [
        f"# Frame extraction index — {video.stem}",
        "",
        f"Source: `{video}`",
        f"Duration: {format_display(duration)}",
        f"Mode: {mode}",
        f"Total extractions: {len(extractions)}",
        "",
        "| # | Timestamp | Label | Contact sheet | Individual frames |",
        "|---|---|---|---|---|",
    ]
    for i, e in enumerate(extractions, start=1):
        ts_display = format_display(e["timestamp"])
        contact = e.get("contact_sheet")
        contact_str = (
            f"`{contact.relative_to(out_dir)}`" if contact else "—"
        )
        frames = e.get("frames") or []
        frames_str = f"{len(frames)} frames" if frames else "—"
        label = e.get("label") or ""
        lines.append(
            f"| {i} | [{ts_display}] | {label} | {contact_str} | {frames_str} |"
        )
    lines.append("")
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path


# ----------------------------------------------------------------------------
# Mode dispatchers
# ----------------------------------------------------------------------------

# Default anchor times — covers typical intro / title-card / first-speaker
# windows for conference and interview formats.
DEFAULT_ANCHORS = [15, 30, 60, 120, 300]


def cmd_anchor(args, video: Path, duration: float, out_dir: Path) -> List[dict]:
    """Extract single anchor frames at preset early timestamps to establish
    each on-camera speaker's visual identity before contested-passage
    analysis."""
    anchors = (
        [parse_timestamp(t) for t in args.timestamps.split(",")]
        if args.timestamps else list(DEFAULT_ANCHORS)
    )
    anchors = [t for t in anchors if t < duration]
    extractions = []
    print(f"Anchor mode — {len(anchors)} timestamps")
    for t in anchors:
        out_path = out_dir / "anchor" / f"{format_filename(t)}.jpg"
        if extract_single_frame(video, t, out_path, q=args.q):
            print(f"  [{format_display(t)}] → {out_path.relative_to(out_dir)}")
            extractions.append({
                "timestamp": t,
                "contact_sheet": out_path,
                "label": "anchor",
            })
    return extractions


def _do_burst(
    video: Path, timestamp: float, span: float, count: int,
    out_dir: Path, args, label: str = "burst",
) -> Optional[dict]:
    """Shared per-timestamp burst extraction. Returns extraction dict on
    success, None on ffmpeg failure."""
    ts_filename = format_filename(timestamp)
    contact_path = out_dir / "burst" / f"{ts_filename}_contact.jpg"
    if not extract_contact_sheet(
        video, timestamp, span, count, contact_path,
        scale_width=args.scale, q=args.q, tile=args.tile,
    ):
        return None
    frames = []
    if args.frames:
        frame_dir = out_dir / "burst" / f"{ts_filename}_frames"
        frames = extract_burst_individual(
            video, timestamp, span, count, frame_dir, q=args.q,
        )
    print(
        f"  [{format_display(timestamp)}] "
        f"{count}×{span:.1f}s → {contact_path.relative_to(out_dir)}"
        + (f"  (+{len(frames)} individual)" if frames else "")
    )
    return {
        "timestamp": timestamp,
        "contact_sheet": contact_path,
        "frames": frames,
        "label": label,
    }


def cmd_burst(args, video: Path, duration: float, out_dir: Path) -> List[dict]:
    """Per-timestamp burst extraction. Each input timestamp yields a contact
    sheet of count×span frames; optionally individual frames too via
    ``--frames``."""
    timestamps = [parse_timestamp(t) for t in args.timestamps.split(",")]
    timestamps = [t for t in timestamps if t + args.span < duration]
    extractions = []
    print(
        f"Burst mode — {len(timestamps)} timestamps, "
        f"{args.count}×{args.span:.1f}s each"
    )
    for t in timestamps:
        # Center the burst on the timestamp by starting half a span earlier
        # so the contributor-supplied address lands mid-burst rather than at
        # the burst's leading edge. Improves "active speech at exactly this
        # moment" verification.
        start = max(0.0, t - args.span / 2)
        extraction = _do_burst(video, start, args.span, args.count, out_dir, args)
        if extraction:
            # Record the contributor-supplied timestamp, not the
            # half-span-earlier start, in the index — the address is what
            # the contributor will recognize.
            extraction["timestamp"] = t
            extractions.append(extraction)
    return extractions


def cmd_sweep(args, video: Path, duration: float, out_dir: Path) -> List[dict]:
    """Periodic burst extraction across a range. Yields a burst every
    ``--every`` seconds from ``--from`` to ``--to`` (defaults: 0 to video
    duration)."""
    start = parse_timestamp(args.start) if args.start else 0.0
    end = parse_timestamp(args.end) if args.end else duration
    end = min(end, duration)
    timestamps = []
    t = start
    while t < end:
        timestamps.append(t)
        t += args.every
    extractions = []
    print(
        f"Sweep mode — {format_display(start)} to {format_display(end)}, "
        f"every {args.every}s, {len(timestamps)} timestamps"
    )
    for t in timestamps:
        if t + args.span > duration:
            break
        extraction = _do_burst(
            video, t, args.span, args.count, out_dir, args, label="sweep",
        )
        if extraction:
            extractions.append(extraction)
    return extractions


def cmd_transcript(
    args, video: Path, duration: float, out_dir: Path,
) -> List[dict]:
    """Transcript-driven burst extraction. Reads ``--transcript`` for every
    ``[MM:SS]`` caption tick and extracts a burst at each (or every Nth via
    ``--every``)."""
    transcript_path = Path(args.transcript).resolve()
    if not transcript_path.exists():
        # Try interpreting as a sources-relative path.
        candidate = SOURCES_DIR / normalize_source_rel_path(args.transcript)
        if candidate.exists():
            transcript_path = candidate
        else:
            sys.exit(f"error: transcript not found: {args.transcript}")
    ticks = parse_transcript_ticks(transcript_path)
    if not ticks:
        sys.exit(f"error: no [MM:SS] ticks found in {transcript_path}")
    if args.every > 1:
        ticks = ticks[:: args.every]
    ticks = [t for t in ticks if t + args.span < duration]
    extractions = []
    print(
        f"Transcript mode — {transcript_path.name}, {len(ticks)} ticks "
        f"(every {args.every}), {args.count}×{args.span:.1f}s burst each"
    )
    for t in ticks:
        extraction = _do_burst(
            video, t, args.span, args.count, out_dir, args, label="tick",
        )
        if extraction:
            extractions.append(extraction)
    return extractions


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def resolve_video_path(arg: str) -> Path:
    """Resolve a contributor-supplied video path. Accepts absolute paths,
    repo-relative paths, and sources/-relative paths (e.g.,
    ``video/foo.mp4`` or ``sources/video/foo.mp4``)."""
    p = Path(arg)
    if p.is_absolute() and p.exists():
        return p
    # repo-relative
    repo_candidate = REPO_ROOT / arg
    if repo_candidate.exists():
        return repo_candidate
    # sources-relative
    src_candidate = SOURCES_DIR / normalize_source_rel_path(arg)
    if src_candidate.exists():
        return src_candidate
    sys.exit(f"error: video not found: {arg}")


def resolve_out_dir(arg: Optional[str], video: Path) -> Path:
    """Resolve the output directory. Default: ``/tmp/frames-{video_stem}/``.
    Created if absent."""
    if arg:
        out = Path(arg).resolve()
    else:
        out = Path(f"/tmp/frames-{video.stem}")
    out.mkdir(parents=True, exist_ok=True)
    return out


def _add_common_burst_args(parser: argparse.ArgumentParser) -> None:
    """Shared --count / --span / --scale / --tile / --q / --frames args."""
    parser.add_argument(
        "--count", type=int, default=5,
        help="Frames per burst (default: 5)",
    )
    parser.add_argument(
        "--span", type=float, default=2.0,
        help="Burst span in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--scale", type=int, default=320,
        help="Per-frame width in contact sheet (default: 320px)",
    )
    parser.add_argument(
        "--tile", default=None,
        help="ffmpeg tile filter geometry (default: COUNTx1 horizontal row). "
             "Example: '3x2' for 6 frames in 3-wide-by-2-high grid.",
    )
    parser.add_argument(
        "-q", "--q", type=int, default=2,
        help="ffmpeg JPEG quality (1=best, 31=worst; default: 2)",
    )
    parser.add_argument(
        "--frames", action="store_true",
        help="Also emit individual frame files alongside the contact sheet",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    # Shared video / out args go on each subparser (not the parent) so
    # `extract-frames.py --help` and `extract-frames.py burst --help` are
    # both informative without duplicating the global-options listing.
    def _add_video_and_out(p):
        p.add_argument("--video", required=True, help="Path to video file")
        p.add_argument("--out", default=None, help="Output directory (default: /tmp/frames-{stem})")

    # anchor
    p_anchor = sub.add_parser(
        "anchor",
        help="Extract single anchor frames at preset early timestamps",
        description=cmd_anchor.__doc__,
    )
    _add_video_and_out(p_anchor)
    p_anchor.add_argument(
        "--timestamps", default=None,
        help="Comma-separated anchor timestamps (default: 0:15,0:30,1:00,2:00,5:00)",
    )
    p_anchor.add_argument(
        "-q", "--q", type=int, default=2,
        help="ffmpeg JPEG quality (1=best, 31=worst; default: 2)",
    )

    # burst
    p_burst = sub.add_parser(
        "burst",
        help="Per-timestamp burst extraction (contact-sheet output)",
        description=cmd_burst.__doc__,
    )
    _add_video_and_out(p_burst)
    p_burst.add_argument(
        "--timestamps", required=True,
        help="Comma-separated MM:SS timestamps",
    )
    _add_common_burst_args(p_burst)

    # sweep
    p_sweep = sub.add_parser(
        "sweep",
        help="Periodic burst extraction across a range",
        description=cmd_sweep.__doc__,
    )
    _add_video_and_out(p_sweep)
    p_sweep.add_argument(
        "--from", dest="start", default=None,
        help="Range start (default: 0:00)",
    )
    p_sweep.add_argument(
        "--to", dest="end", default=None,
        help="Range end (default: video duration)",
    )
    p_sweep.add_argument(
        "--every", type=float, required=True,
        help="Interval between bursts, in seconds (e.g., 30)",
    )
    _add_common_burst_args(p_sweep)

    # transcript
    p_tr = sub.add_parser(
        "transcript",
        help="Burst at each [MM:SS] tick of a transcribed source",
        description=cmd_transcript.__doc__,
    )
    _add_video_and_out(p_tr)
    p_tr.add_argument(
        "--transcript", required=True,
        help="Path to transcript file (sources/transcripts/foo-*.txt or absolute)",
    )
    p_tr.add_argument(
        "--every", type=int, default=1,
        help="Sample every Nth tick (default: 1 — every tick; use higher to throttle)",
    )
    _add_common_burst_args(p_tr)

    args = parser.parse_args()

    ensure_tools()
    video = resolve_video_path(args.video)
    out_dir = resolve_out_dir(args.out, video)
    try:
        duration = probe_duration(video)
    except RuntimeError as e:
        sys.exit(f"error: {e}")

    print(f"Video:    {video}")
    print(f"Duration: {format_display(duration)}")
    print(f"Output:   {out_dir}")
    print()

    dispatch = {
        "anchor": cmd_anchor,
        "burst": cmd_burst,
        "sweep": cmd_sweep,
        "transcript": cmd_transcript,
    }
    extractions = dispatch[args.mode](args, video, duration, out_dir)

    if not extractions:
        sys.exit("error: no frames extracted")

    index_path = write_index(
        out_dir, video, duration, args.mode, extractions,
    )
    print()
    print(f"Wrote index: {index_path}")
    print(f"Extracted {len(extractions)} timestamp(s) to {out_dir}")


if __name__ == "__main__":
    main()
