#!/usr/bin/env python3
"""diarize-audio.py — speaker diarization for multi-speaker video sources.

Whisper and YouTube auto-caption transcripts preserve timestamps and text
but not who is speaking. detect-faces.py answers "who is on screen" via
visual baselines; this tool answers "how many distinct voices are present,
and when does each one speak" via audio-side speaker diarization.

The output is intentionally identity-blind. Diarization yields anonymous
labels (SPEAKER_00, SPEAKER_01, ...) — "this voice is different from that
voice." Combining a diarization with extract-frames.py + detect-faces.py
output is what produces an actual speaker attribution: at a contested
[MM:SS], the diarization says SPEAKER_01 was talking, the frame at that
timestamp shows identity X, X is now attributed to SPEAKER_01 throughout
the source.

Wraps pyannote.audio's ``speaker-diarization-3.1`` pipeline. The model is
gated on Hugging Face; ``setup-diarize-audio.sh`` walks contributors
through the one-time HF user-conditions + token setup.

Two outputs are written to the output directory:

  segments.csv  — start_seconds, end_seconds, duration_seconds, speaker
                  one row per detected turn. Canonical machine-readable
                  form for downstream tooling.

  segments.md   — per-speaker total speech time + percentage of analyzed
                  range, chronological segment list with [HH:MM:SS]
                  anchors, and per-speaker segment groups for quick
                  navigation to a specific speaker's appearances.

For long videos (multi-hour documentaries, panel discussions), use
``--start`` / ``--end`` to slice the analyzed range — diarization runs at
roughly real-time on CPU, so a 2:47:09 source takes hours. A 5-minute
slice around the contested passage is usually what you want.

Requires pyannote.audio, torch, torchaudio, ffmpeg. Run
``scripts/tools/setup-diarize-audio.sh`` once to install dependencies
and walk through the HF auth steps. See
``scripts/tools/VIDEO-PIPELINE.md`` for the end-to-end pipeline this tool
is step 2.5 of (run before detect-faces.py to know which timestamps
warrant frame extraction).

Usage examples:
  # Full-video diarization (slow on long sources)
  ./diarize-audio.py sources/video/foo.mp4

  # Slice a specific range (recommended for >10 min sources)
  ./diarize-audio.py sources/video/foo.mp4 --start 19:00 --end 22:00

  # Override output directory + keep the extracted audio for inspection
  ./diarize-audio.py sources/video/foo.mp4 --out /tmp/diarize-foo --keep-audio
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Venv auto-relaunch — must happen before importing anything pyannote-touched.
# pyannote.audio is installed inside .venv-diarize/ at the repo root (PEP 668
# blocks system-wide pip on Debian/Kali, and pyannote's torch dependency is
# too heavy to want system-wide anyway). Re-exec under the venv Python so
# contributors don't need to source the activate script.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parent.parent.parent  # scripts/tools/diarize-audio.py → repo root
_VENV_PYTHON = _REPO_ROOT / ".venv-diarize" / "bin" / "python3"
if (
    _VENV_PYTHON.is_file()
    and os.path.realpath(sys.executable) != os.path.realpath(_VENV_PYTHON)
    and os.environ.get("DIARIZE_VENV_ACTIVE") != "1"
):
    os.environ["DIARIZE_VENV_ACTIVE"] = "1"
    os.execv(str(_VENV_PYTHON), [str(_VENV_PYTHON)] + sys.argv)

import argparse
import csv
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import List, Optional, Tuple

# scripts/tools/diarize-audio.py — scripts/ on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import REPO_ROOT  # noqa: E402


PYANNOTE_MODEL = "pyannote/speaker-diarization-3.1"

# ----------------------------------------------------------------------------
# Timestamp parsing / formatting
# ----------------------------------------------------------------------------

_TS_RE = re.compile(r"^\s*(?:(\d+):)?(?:(\d+):)?(\d+(?:\.\d+)?)\s*$")


def parse_timestamp(ts: str) -> float:
    """Parse MM:SS / H:MM:SS / plain-seconds → float seconds."""
    m = _TS_RE.match(ts)
    if not m:
        raise ValueError(f"unparseable timestamp: {ts!r}")
    parts = [p for p in m.groups() if p is not None]
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def format_timestamp(seconds: float) -> str:
    """seconds → ``HH:MM:SS`` (zero-padded, suitable for markdown anchors)."""
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def format_duration(seconds: float) -> str:
    """seconds → ``M:SS`` (or ``H:MM:SS`` for >= 1 hour). Compact."""
    s = int(round(seconds))
    if s >= 3600:
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        return f"{h}:{m:02d}:{sec:02d}"
    m, sec = divmod(s, 60)
    return f"{m}:{sec:02d}"


# ----------------------------------------------------------------------------
# ffmpeg audio extraction
# ----------------------------------------------------------------------------


def extract_audio(
    video_path: Path,
    audio_path: Path,
    start: Optional[float] = None,
    end: Optional[float] = None,
) -> None:
    """Extract mono 16 kHz WAV from video_path → audio_path.

    pyannote.audio's models are trained at 16 kHz. ffmpeg downmixes to mono
    (``-ac 1``), resamples (``-ar 16000``), and drops the video stream
    (``-vn``). If ``start`` / ``end`` are set, only that span is extracted.
    """
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", str(video_path)]
    if end is not None and start is not None:
        cmd += ["-t", str(end - start)]
    elif end is not None:
        cmd += ["-to", str(end)]
    cmd += ["-vn", "-ac", "1", "-ar", "16000", str(audio_path)]
    subprocess.run(cmd, check=True)


def video_duration(video_path: Path) -> float:
    """Return video duration in seconds via ffprobe."""
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(video_path),
        ],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out)


# ----------------------------------------------------------------------------
# pyannote.audio diarization
# ----------------------------------------------------------------------------


def run_diarization(
    audio_path: Path,
    hf_token: Optional[str],
    num_speakers: Optional[int] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
) -> List[Tuple[float, float, str]]:
    """Run pyannote ``speaker-diarization-3.1`` on the audio file.

    Returns a list of ``(start_seconds, end_seconds, speaker_label)`` tuples,
    chronologically ordered. Speaker labels are pyannote's anonymous form
    (``SPEAKER_00``, ``SPEAKER_01``, ...).

    Fails with an actionable error if pyannote.audio isn't installed or the
    HF token / model-conditions aren't set up — points at
    ``setup-diarize-audio.sh``.
    """
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        sys.exit(
            "error: pyannote.audio not installed.\n"
            "  Run scripts/tools/setup-diarize-audio.sh to install."
        )

    if not hf_token:
        sys.exit(
            "error: HF_TOKEN not set.\n"
            f"  pyannote's {PYANNOTE_MODEL} is gated on Hugging Face.\n"
            "  Run scripts/tools/setup-diarize-audio.sh for the one-time\n"
            "  setup (accept user conditions + export HF_TOKEN)."
        )

    try:
        pipeline = Pipeline.from_pretrained(PYANNOTE_MODEL, use_auth_token=hf_token)
    except Exception as e:
        sys.exit(
            f"error: failed to load {PYANNOTE_MODEL}: {e}\n"
            "  Most common cause: user conditions not accepted at\n"
            f"  https://hf.co/{PYANNOTE_MODEL}\n"
            "  See scripts/tools/setup-diarize-audio.sh."
        )

    kwargs: dict = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers
    elif min_speakers is not None or max_speakers is not None:
        if min_speakers is not None:
            kwargs["min_speakers"] = min_speakers
        if max_speakers is not None:
            kwargs["max_speakers"] = max_speakers

    diarization = pipeline(str(audio_path), **kwargs)

    segments: List[Tuple[float, float, str]] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append((float(turn.start), float(turn.end), str(speaker)))
    segments.sort(key=lambda s: s[0])
    return segments


# ----------------------------------------------------------------------------
# Output writers
# ----------------------------------------------------------------------------


def write_segments_csv(
    out_path: Path, segments: List[Tuple[float, float, str]], time_offset: float,
) -> None:
    """Write the canonical CSV. ``time_offset`` is added to each segment's
    start/end so timestamps map back to the original video (not the
    extracted-slice-relative coordinates)."""
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["start_seconds", "end_seconds", "duration_seconds", "speaker"])
        for start, end, speaker in segments:
            s = start + time_offset
            e = end + time_offset
            w.writerow([f"{s:.3f}", f"{e:.3f}", f"{e - s:.3f}", speaker])


def write_segments_md(
    out_path: Path,
    segments: List[Tuple[float, float, str]],
    video_path: Path,
    range_start: float,
    range_end: float,
    time_offset: float,
    run_date: str,
) -> None:
    """Human-readable markdown summary + segment list."""
    per_speaker_total: dict = {}
    per_speaker_count: dict = {}
    per_speaker_segments: dict = {}
    for start, end, speaker in segments:
        dur = end - start
        per_speaker_total[speaker] = per_speaker_total.get(speaker, 0.0) + dur
        per_speaker_count[speaker] = per_speaker_count.get(speaker, 0) + 1
        per_speaker_segments.setdefault(speaker, []).append((start, end))

    analyzed = range_end - range_start

    lines = [
        f"# Diarization — {video_path.stem}",
        "",
        f"- Source video: `{video_path}`",
        f"- Range analyzed: [{format_timestamp(range_start)}] – [{format_timestamp(range_end)}] ({format_duration(analyzed)})",
        f"- Run date (UTC): {run_date}",
        f"- Model: `{PYANNOTE_MODEL}`",
        f"- Unique speakers detected: **{len(per_speaker_total)}**",
        f"- Total segments: **{len(segments)}**",
        "",
        "Speaker labels are identity-blind (`SPEAKER_00`, `SPEAKER_01`, ...). "
        "Pair with extract-frames.py + detect-faces.py at contested timestamps "
        "to map labels → identities.",
        "",
        "## Per-speaker totals",
        "",
        "| Speaker | Segments | Total speech | % of analyzed |",
        "|---|---|---|---|",
    ]
    for speaker in sorted(per_speaker_total.keys()):
        total = per_speaker_total[speaker]
        pct = (total / analyzed * 100.0) if analyzed > 0 else 0.0
        lines.append(
            f"| `{speaker}` | {per_speaker_count[speaker]} | "
            f"{format_duration(total)} | {pct:.1f}% |"
        )
    lines.append("")

    lines += [
        "## Segments (chronological)",
        "",
        "| # | Start | End | Duration | Speaker |",
        "|---|---|---|---|---|",
    ]
    for i, (start, end, speaker) in enumerate(segments, start=1):
        s = start + time_offset
        e = end + time_offset
        lines.append(
            f"| {i} | [{format_timestamp(s)}] | [{format_timestamp(e)}] | "
            f"{format_duration(end - start)} | `{speaker}` |"
        )
    lines.append("")

    lines += ["## Per-speaker segments", ""]
    for speaker in sorted(per_speaker_segments.keys()):
        lines.append(f"### `{speaker}`")
        lines.append("")
        for start, end in per_speaker_segments[speaker]:
            s = start + time_offset
            e = end + time_offset
            lines.append(
                f"- [{format_timestamp(s)}] – [{format_timestamp(e)}] "
                f"({format_duration(end - start)})"
            )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def main() -> None:
    p = argparse.ArgumentParser(
        description="Speaker diarization (identity-blind) for multi-speaker video sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Output is two files in --out (defaults to /tmp/diarize-{video-stem}/):\n"
            "  segments.csv — canonical per-turn rows\n"
            "  segments.md  — per-speaker totals + chronological + per-speaker views\n\n"
            "First run? See scripts/tools/setup-diarize-audio.sh for the one-time\n"
            "pyannote.audio + Hugging Face setup."
        ),
    )
    p.add_argument("video", help="Path to video file")
    p.add_argument("--out", help="Output directory (default: /tmp/diarize-{stem})")
    p.add_argument("--start", help="Start timestamp (MM:SS / H:MM:SS / seconds)")
    p.add_argument("--end", help="End timestamp (MM:SS / H:MM:SS / seconds)")
    p.add_argument(
        "--num-speakers", type=int,
        help="Fix the speaker count if known (overrides min/max)",
    )
    p.add_argument(
        "--min-speakers", type=int,
        help="Minimum speakers to detect (pyannote tuning hint)",
    )
    p.add_argument(
        "--max-speakers", type=int,
        help="Maximum speakers to detect (pyannote tuning hint)",
    )
    p.add_argument(
        "--keep-audio", action="store_true",
        help="Keep the extracted 16 kHz mono WAV in --out (default: temp-only)",
    )
    p.add_argument(
        "--hf-token",
        help="Hugging Face token (defaults to HF_TOKEN env var)",
    )
    args = p.parse_args()

    video_path = Path(args.video).resolve()
    if not video_path.is_file():
        sys.exit(f"error: video not found: {video_path}")

    if shutil.which("ffmpeg") is None:
        sys.exit("error: ffmpeg not in PATH. See scripts/tools/setup-photo-identity.sh.")
    if shutil.which("ffprobe") is None:
        sys.exit("error: ffprobe not in PATH (ships with ffmpeg).")

    duration = video_duration(video_path)
    start_s = parse_timestamp(args.start) if args.start else 0.0
    end_s = parse_timestamp(args.end) if args.end else duration
    if end_s <= start_s:
        sys.exit(f"error: --end ({end_s}) must be after --start ({start_s})")
    if end_s > duration + 0.5:
        sys.exit(
            f"error: --end ({format_timestamp(end_s)}) exceeds video duration "
            f"({format_timestamp(duration)})"
        )

    out_dir = Path(args.out).resolve() if args.out else (
        Path(tempfile.gettempdir()) / f"diarize-{video_path.stem}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    hf_token = args.hf_token or os.environ.get("HF_TOKEN")

    analyzed = end_s - start_s
    print(f"Video:    {video_path}")
    print(f"Duration: {format_timestamp(duration)}")
    print(f"Range:    [{format_timestamp(start_s)}] – [{format_timestamp(end_s)}]  ({format_duration(analyzed)})")
    print(f"Output:   {out_dir}")
    print()

    # Audio extraction — to out_dir if --keep-audio, else to a temp file
    if args.keep_audio:
        audio_path = out_dir / "audio.wav"
        temp_dir = None
    else:
        temp_dir = Path(tempfile.mkdtemp(prefix="diarize-"))
        audio_path = temp_dir / "audio.wav"

    print(f"Extracting audio → {audio_path.name} (16 kHz mono)...")
    try:
        extract_audio(video_path, audio_path, start=start_s, end=end_s)
    except subprocess.CalledProcessError as e:
        sys.exit(f"error: ffmpeg failed during audio extraction: {e}")

    print("Running pyannote diarization (may take a while on CPU)...")
    segments = run_diarization(
        audio_path,
        hf_token=hf_token,
        num_speakers=args.num_speakers,
        min_speakers=args.min_speakers,
        max_speakers=args.max_speakers,
    )

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    csv_path = out_dir / "segments.csv"
    md_path = out_dir / "segments.md"
    write_segments_csv(csv_path, segments, time_offset=start_s)
    write_segments_md(
        md_path, segments, video_path,
        range_start=start_s, range_end=end_s,
        time_offset=start_s, run_date=run_date,
    )

    if temp_dir is not None:
        shutil.rmtree(temp_dir, ignore_errors=True)

    unique = sorted({s[2] for s in segments})
    print()
    print(f"Detected {len(unique)} unique speaker(s) across {len(segments)} segment(s).")
    print(f"  segments.csv → {csv_path}")
    print(f"  segments.md  → {md_path}")
    print()
    print("Next: open segments.md to navigate by speaker. Pair with")
    print("extract-frames.py + detect-faces.py at contested timestamps")
    print("to map SPEAKER_NN labels onto visual identities.")


if __name__ == "__main__":
    main()
