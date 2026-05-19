#!/usr/bin/env python3
"""stitch-transcript.py — bridge from raw caption + diarization + baselines to
a speaker-labeled transcript for contributor reference.

The video-pipeline tooling produces three independent artifacts today:

  1. Auto-caption transcript (transcribe.py output) — flat timestamped lines,
     no speaker turns.
  2. Diarization segments.csv (diarize-audio.py output) — anonymous
     ``SPEAKER_00`` / ``SPEAKER_01`` turns.
  3. Identity baselines (detect-faces.py register output) — per-identity
     reference crops.

The contributor has historically had to merge these three artifacts mentally
when authoring transcript-artifact ``quotes[]``. This tool does the merge:

  - For each diarize segment, extracts a frame at the segment's midpoint.
  - Runs Haar-cascade face detection on the frame.
  - Computes a perceptual hash for each detected face, matches against the
    persistent baseline set (sources/photo-identity-log/baselines/).
  - Aggregates per anonymous speaker label: which identity slug appeared
    most often across this speaker's segment-midpoint frames?
  - Walks the auto-caption transcript; for each tick that falls inside a
    diarize segment, attaches the resolved identity slug. Emits the label
    at turn boundaries only (consecutive lines from the same speaker are
    not re-labeled — visual noise without information gain).

Output to ``/tmp/stitch-{slug}/`` (configurable):

  - ``stitched.md`` — speaker-labeled transcript, header carries the
    resolution table with confidence ratings.
  - ``speaker-map.csv`` — machine-readable rollup: speaker_label,
    identity_slug, n_matches, n_segments, confidence, all_identities_seen.
  - ``frames/`` — per-segment midpoint frames, kept so the contributor
    can spot-check a suspect assignment.

Confidence ratings:

  - ``high``   — single identity dominates this speaker's matches AND no
                 other speaker also resolves to the same identity (clean
                 single-camera coverage).
  - ``medium`` — single identity dominates but other speakers also see
                 it (split-screen / multi-feed ambiguity; visual baseline
                 alone can't disambiguate which face is actively speaking).
  - ``low``    — speaker had matches but no single identity dominated.
  - ``none``   — no baseline matches at all across this speaker's frames.

A reader of stitched.md sees the confidence inline and a "review required"
banner whenever any speaker resolves below ``high``.

Usage:

    python3 scripts/tools/stitch-transcript.py VIDEO_PATH
        [--transcript PATH]          # default: sources/transcripts/{slug}-downloaded.md
        [--diarize-segments PATH]    # default: /tmp/diarize-{slug}/segments.csv
        [--out DIR]                  # default: /tmp/stitch-{slug}/
        [--baselines-manifest PATH]  # default: sources/photo-identity-log/manifest.yaml

The tool is read-only with respect to the corpus — it writes only to
``--out`` (defaults to /tmp). It does not touch sources/photo-identity-log/
or sources/manifest.yaml. Output is contributor-diagnostic: read it, use
the resolved speaker labels to populate the ``speaker_id`` field on each
transcript quote in the research artifact.
"""

import argparse
import csv
import importlib.util
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

# ----------------------------------------------------------------------------
# Module loader — detect-faces.py and extract-frames.py have hyphens in their
# filenames (CLI convention) so they can't be imported via the normal `import`
# statement. importlib.util loads them as modules at runtime.
# ----------------------------------------------------------------------------

_TOOLS_DIR = Path(__file__).resolve().parent


def _load_sibling(rel_filename: str):
    name = rel_filename.removesuffix(".py").replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, _TOOLS_DIR / rel_filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


detect_faces_mod = _load_sibling("detect-faces.py")
extract_frames_mod = _load_sibling("extract-frames.py")


# ----------------------------------------------------------------------------
# Constants + dataclasses
# ----------------------------------------------------------------------------

REPO_ROOT = _TOOLS_DIR.parent.parent
DEFAULT_BASELINES_MANIFEST = REPO_ROOT / "sources" / "photo-identity-log" / "manifest.yaml"
DEFAULT_BASELINES_DIR = REPO_ROOT / "sources" / "photo-identity-log" / "baselines"

# Caption-tick regex — matches the [MM:SS] or [H:MM:SS] prefix on caption lines.
_CAPTION_TICK_RE = re.compile(r"^\[(\d{1,2}(?::\d{2})+)\]\s*(.*)$")


@dataclass
class Segment:
    """One diarize segment."""
    idx: int
    start: float
    end: float
    speaker: str

    @property
    def midpoint(self) -> float:
        return (self.start + self.end) / 2

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class CaptionLine:
    """One line of the auto-caption transcript."""
    ts_seconds: float
    ts_display: str         # the original [MM:SS] / [H:MM:SS] form
    text: str


@dataclass
class SpeakerResolution:
    """Resolved identity assignment for one anonymous diarize speaker label."""
    speaker: str                            # e.g., SPEAKER_00
    identity: Optional[str]                 # kebab-case identity slug or None
    confidence: str                         # high | medium | low | none
    n_segments: int                         # diarize-segments seen
    match_counts: Dict[str, int] = field(default_factory=dict)   # identity_slug → count
    total_speech_seconds: float = 0.0
    notes: List[str] = field(default_factory=list)


# ----------------------------------------------------------------------------
# Parsers
# ----------------------------------------------------------------------------

def parse_segments_csv(path: Path) -> List[Segment]:
    if not path.is_file():
        sys.exit(f"error: segments.csv not found: {path}")
    out = []
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader):
            try:
                start = float(row["start_seconds"])
                end = float(row["end_seconds"])
                speaker = row["speaker"].strip()
            except (KeyError, ValueError) as e:
                sys.exit(f"error: malformed segments.csv at row {i+1}: {e}")
            out.append(Segment(idx=i, start=start, end=end, speaker=speaker))
    return out


def parse_caption_file(path: Path) -> List[CaptionLine]:
    """Parse an auto-caption file (transcribe.py output). Lines look like
    ``[0:02] AASAP was the US government's largest`` — ``[MM:SS]`` or
    ``[H:MM:SS]`` followed by text. Skips header lines (markdown ``#``,
    ``---``, ``Source URL:``, etc.)."""
    if not path.is_file():
        sys.exit(f"error: transcript file not found: {path}")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _CAPTION_TICK_RE.match(line.rstrip())
        if not m:
            continue
        ts_display = m.group(1)
        ts_seconds = extract_frames_mod.parse_timestamp(ts_display)
        text = m.group(2).strip()
        if not text:
            continue
        out.append(CaptionLine(ts_seconds=ts_seconds, ts_display=ts_display, text=text))
    return out


def load_baselines(manifest_path: Path) -> List[Tuple[Path, int, str]]:
    """Load identity baselines: walks baselines/ on disk, computing pHash
    per file. The manifest is used to confirm the baselines directory
    location; the pHash + identity slug come from the on-disk file layout
    (baselines/{slug}/ref_NN.jpg)."""
    if not manifest_path.is_file():
        sys.exit(f"error: baselines manifest not found: {manifest_path}")
    return detect_faces_mod.baseline_phashes()


# ----------------------------------------------------------------------------
# Per-segment face detection + identity match
# ----------------------------------------------------------------------------

def detect_identities_in_frame(
    frame_path: Path, baseline_hashes: List[Tuple[Path, int, str]],
    crop_scratch_dir: Path,
) -> Tuple[List[str], int]:
    """Returns (matched_identities, n_faces). For each face detected in
    ``frame_path``, crops it, computes pHash, and matches against
    baselines. Returns the list of matched identity slugs (None matches
    omitted) plus the total face count."""
    faces = detect_faces_mod.detect_faces_in_image(frame_path)
    matched = []
    crop_scratch_dir.mkdir(parents=True, exist_ok=True)
    for i, bbox in enumerate(faces):
        crop_path = crop_scratch_dir / f"{frame_path.stem}_face_{i:02d}.jpg"
        if not detect_faces_mod.crop_and_save(frame_path, bbox, crop_path):
            continue
        phash = detect_faces_mod.perceptual_hash(crop_path)
        if phash is None:
            continue
        identity = detect_faces_mod.identify_against_baselines(phash, baseline_hashes)
        if identity:
            matched.append(identity)
    return matched, len(faces)


# ----------------------------------------------------------------------------
# Aggregation: speaker → identity with confidence
# ----------------------------------------------------------------------------

def aggregate_speakers(
    segments: List[Segment],
    per_segment_matches: Dict[int, List[str]],
) -> Dict[str, SpeakerResolution]:
    """Per anonymous speaker label, aggregate matched identities across
    that speaker's segment-midpoint frames. Pick the dominant identity
    per speaker; rate confidence by separation from runner-up + whether
    the same identity is dominant for ANOTHER speaker (split-screen
    ambiguity signal)."""
    by_speaker: Dict[str, SpeakerResolution] = {}

    # Per-speaker totals first
    per_speaker_segments: Dict[str, List[Segment]] = defaultdict(list)
    for s in segments:
        per_speaker_segments[s.speaker].append(s)

    for speaker, segs in per_speaker_segments.items():
        counts: Counter[str] = Counter()
        for seg in segs:
            for ident in per_segment_matches.get(seg.idx, []):
                counts[ident] += 1
        by_speaker[speaker] = SpeakerResolution(
            speaker=speaker,
            identity=None,
            confidence="none",
            n_segments=len(segs),
            match_counts=dict(counts),
            total_speech_seconds=sum(s.duration for s in segs),
        )

    # First pass: pick the dominant identity per speaker
    for speaker, res in by_speaker.items():
        if not res.match_counts:
            continue
        # Most-common identity
        top_ident, top_count = max(res.match_counts.items(), key=lambda kv: kv[1])
        runner_up = sorted(res.match_counts.values(), reverse=True)
        runner_up_count = runner_up[1] if len(runner_up) > 1 else 0
        res.identity = top_ident
        # Initial confidence by intra-speaker separation
        if top_count > runner_up_count and top_count >= max(1, res.n_segments // 2):
            res.confidence = "high"
        elif top_count >= max(1, res.n_segments // 3):
            res.confidence = "medium"
        else:
            res.confidence = "low"

    # Second pass: downgrade confidence on split-screen ambiguity — when
    # the same identity dominates two different speakers, no single face
    # in any frame is actively-speaking-differentiable.
    identity_to_speakers: Dict[str, List[str]] = defaultdict(list)
    for speaker, res in by_speaker.items():
        if res.identity:
            identity_to_speakers[res.identity].append(speaker)
    for ident, speakers_using in identity_to_speakers.items():
        if len(speakers_using) > 1:
            for sp in speakers_using:
                res = by_speaker[sp]
                if res.confidence == "high":
                    res.confidence = "medium"
                res.notes.append(
                    f"split-screen ambiguity: identity {ident!r} also dominant for "
                    f"{[s for s in speakers_using if s != sp]}"
                )

    return by_speaker


# ----------------------------------------------------------------------------
# Stitching: caption → speaker-labeled transcript
# ----------------------------------------------------------------------------

_SEGMENT_SNAP_TOLERANCE = 1.0   # seconds


def find_segment_for_timestamp(
    ts: float, segments: List[Segment],
) -> Optional[Segment]:
    """Find the diarize segment containing ``ts``. Caption ticks are typically
    integer-second; diarize segment boundaries are sub-second. A caption tick
    that falls in a small gap between two adjacent segments (pyannote rounding
    artifact, not a real silence) gets snapped to the nearest segment within
    ``_SEGMENT_SNAP_TOLERANCE``. Returns None only when the timestamp is
    clearly outside any segment's reach (e.g., the caption is from a portion
    of the video that was never diarized)."""
    for s in segments:
        if s.start <= ts <= s.end:
            return s
    nearest = None
    nearest_distance = float("inf")
    for s in segments:
        if ts < s.start:
            d = s.start - ts
        else:
            d = ts - s.end
        if d < nearest_distance:
            nearest_distance = d
            nearest = s
    if nearest is not None and nearest_distance <= _SEGMENT_SNAP_TOLERANCE:
        return nearest
    return None


def stitch(
    captions: List[CaptionLine],
    segments: List[Segment],
    resolutions: Dict[str, SpeakerResolution],
) -> str:
    """Walk the caption lines; emit each line with a leading speaker label
    on speaker-change boundaries. Lines whose timestamp falls outside any
    diarize segment get a ``(unanalyzed)`` marker (typically because the
    diarize slice was narrower than the full transcript)."""
    out_lines = []
    _SENTINEL = object()
    previous_label = _SENTINEL
    for c in captions:
        seg = find_segment_for_timestamp(c.ts_seconds, segments)
        if seg is None:
            label = "_unanalyzed_"
            display_label = "_(unanalyzed)_"
        else:
            res = resolutions.get(seg.speaker)
            if res and res.identity:
                label = res.identity
                display_label = f"**{label}:**"
            else:
                label = seg.speaker
                display_label = f"_({seg.speaker})_"
        if label != previous_label:
            out_lines.append(f"[{c.ts_display}] {display_label} {c.text}")
            previous_label = label
        else:
            out_lines.append(f"[{c.ts_display}] {c.text}")
    return "\n".join(out_lines) + "\n"


# ----------------------------------------------------------------------------
# Output writers
# ----------------------------------------------------------------------------

def write_stitched(
    out_path: Path,
    video: Path,
    transcript_path: Path,
    segments_path: Path,
    segments: List[Segment],
    resolutions: Dict[str, SpeakerResolution],
    stitched_body: str,
    transcript_range_label: str,
):
    lines = [
        f"# Stitched transcript — {video.stem}",
        "",
        f"- Source video: `{video}`",
        f"- Caption source: `{transcript_path}`",
        f"- Diarize segments: `{segments_path}`",
        f"- Range analyzed: {transcript_range_label}",
        "",
        "## Speaker resolution",
        "",
        "| Speaker | Identity | Confidence | Visual matches | Speech | Notes |",
        "|---|---|---|---|---|---|",
    ]
    needs_review = False
    for sp in sorted(resolutions):
        res = resolutions[sp]
        matches_str = ", ".join(
            f"{ident}={n}" for ident, n in sorted(
                res.match_counts.items(), key=lambda kv: -kv[1]
            )
        ) or "(none)"
        speech_str = extract_frames_mod.format_display(res.total_speech_seconds)
        notes_str = "; ".join(res.notes) if res.notes else ""
        identity_str = res.identity or "_unresolved_"
        if res.confidence != "high":
            needs_review = True
        lines.append(
            f"| `{sp}` | `{identity_str}` | {res.confidence} | "
            f"{matches_str} ({res.n_segments} segs) | {speech_str} | {notes_str} |"
        )
    lines.extend(["", ""])
    if needs_review:
        lines.append(
            "> ⚠ **Manual review required** — one or more speakers resolved below "
            "`high` confidence. Inspect the per-segment frames in `frames/` and "
            "the `match_counts` per speaker; override the resolution manually if "
            "the automatic assignment is wrong before using this output to "
            "populate `speaker_id` on transcript-artifact quotes."
        )
        lines.append("")
    lines.append("## Stitched transcript")
    lines.append("")
    lines.append(stitched_body)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_speaker_map_csv(
    out_path: Path, resolutions: Dict[str, SpeakerResolution]
):
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "speaker", "identity", "confidence", "n_segments",
            "total_speech_seconds", "match_counts", "notes",
        ])
        for sp in sorted(resolutions):
            r = resolutions[sp]
            w.writerow([
                r.speaker,
                r.identity or "",
                r.confidence,
                r.n_segments,
                f"{r.total_speech_seconds:.2f}",
                "|".join(f"{k}:{v}" for k, v in sorted(r.match_counts.items())),
                "|".join(r.notes),
            ])


# ----------------------------------------------------------------------------
# Discovery + main
# ----------------------------------------------------------------------------

def discover_inputs(video: Path) -> Dict[str, Path]:
    """Auto-discover related files for this video by slug convention."""
    slug = video.stem
    transcripts_dir = REPO_ROOT / "sources" / "transcripts"
    # Look for any -downloaded* file matching the slug. Tries common
    # suffixes used by transcribe.py output.
    transcript = None
    for suffix in (
        "-downloaded.md", "-downloaded.txt",
        "-youtube-transcript.md", "-youtube-transcript.txt",
        "-vimeo-whisper-transcript.md", "-vimeo-whisper-transcript.txt",
    ):
        candidate = transcripts_dir / f"{slug}{suffix}"
        if candidate.is_file():
            transcript = candidate
            break
    segments = Path("/tmp") / f"diarize-{slug}" / "segments.csv"
    return {
        "transcript": transcript,
        "segments": segments if segments.is_file() else None,
    }


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("video", help="Path to the source video file")
    p.add_argument("--transcript", help="Path to the downloaded auto-caption transcript")
    p.add_argument("--diarize-segments", help="Path to the diarize segments.csv")
    p.add_argument(
        "--baselines-manifest", default=str(DEFAULT_BASELINES_MANIFEST),
        help=f"Path to photo-identity-log manifest (default: {DEFAULT_BASELINES_MANIFEST})",
    )
    p.add_argument("--out", help="Output directory (default: /tmp/stitch-{video-stem}/)")
    args = p.parse_args()

    video = Path(args.video).resolve()
    if not video.is_file():
        sys.exit(f"error: video not found: {video}")

    discovered = discover_inputs(video)
    transcript_path = Path(args.transcript) if args.transcript else discovered["transcript"]
    segments_path = Path(args.diarize_segments) if args.diarize_segments else discovered["segments"]
    if not transcript_path or not transcript_path.is_file():
        sys.exit(
            f"error: transcript file not found. Tried auto-discover; pass "
            f"--transcript PATH explicitly. (Looked in "
            f"{REPO_ROOT / 'sources' / 'transcripts'} for "
            f"{video.stem}-downloaded.* etc.)"
        )
    if not segments_path or not segments_path.is_file():
        sys.exit(
            f"error: diarize segments.csv not found at {segments_path}. "
            f"Run diarize-audio.py first, or pass --diarize-segments PATH."
        )

    out_dir = Path(args.out) if args.out else Path("/tmp") / f"stitch-{video.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "frames"
    crops_dir = out_dir / "_crops"
    frames_dir.mkdir(exist_ok=True)
    crops_dir.mkdir(exist_ok=True)

    print(f"Video:    {video}")
    print(f"Captions: {transcript_path}")
    print(f"Segments: {segments_path}")
    print(f"Out:      {out_dir}")
    print()

    # Load inputs
    segments = parse_segments_csv(segments_path)
    captions = parse_caption_file(transcript_path)
    baselines = load_baselines(Path(args.baselines_manifest))
    print(f"Loaded {len(segments)} segments, {len(captions)} caption lines, "
          f"{len(baselines)} baseline crops "
          f"({len({s for _, _, s in baselines})} identities).")
    print()

    # Per-segment frame extraction + identity matching
    per_segment_matches: Dict[int, List[str]] = {}
    print("Processing segments...")
    for seg in segments:
        ts_filename = extract_frames_mod.format_filename(seg.midpoint)
        frame_path = frames_dir / f"seg_{seg.idx:03d}_{ts_filename}.jpg"
        if not extract_frames_mod.extract_single_frame(video, seg.midpoint, frame_path, q=2):
            print(f"  seg {seg.idx:03d}: ffmpeg failed at midpoint "
                  f"{extract_frames_mod.format_display(seg.midpoint)}")
            per_segment_matches[seg.idx] = []
            continue
        matched, n_faces = detect_identities_in_frame(frame_path, baselines, crops_dir)
        per_segment_matches[seg.idx] = matched
        if matched:
            match_str = "+".join(matched)
        else:
            match_str = "(no identified faces)"
        print(f"  seg {seg.idx:03d} [{extract_frames_mod.format_display(seg.start)}–"
              f"{extract_frames_mod.format_display(seg.end)}] "
              f"{seg.speaker}: {n_faces} face(s); {match_str}")

    # Aggregate per anonymous speaker
    resolutions = aggregate_speakers(segments, per_segment_matches)

    # Compose stitched body
    stitched_body = stitch(captions, segments, resolutions)

    # Compute the range label
    if segments:
        first = extract_frames_mod.format_display(segments[0].start)
        last = extract_frames_mod.format_display(segments[-1].end)
        range_label = f"[{first}] – [{last}]"
    else:
        range_label = "(no segments)"

    # Write outputs
    write_stitched(
        out_dir / "stitched.md", video, transcript_path, segments_path,
        segments, resolutions, stitched_body, range_label,
    )
    write_speaker_map_csv(out_dir / "speaker-map.csv", resolutions)

    print()
    print("Speaker resolution:")
    for sp in sorted(resolutions):
        r = resolutions[sp]
        ident = r.identity or "(unresolved)"
        print(f"  {sp} → {ident} (confidence: {r.confidence}; "
              f"{r.n_segments} segs, "
              f"{extract_frames_mod.format_display(r.total_speech_seconds)} speech)")
    print()
    print(f"Wrote:")
    print(f"  {out_dir / 'stitched.md'}")
    print(f"  {out_dir / 'speaker-map.csv'}")
    print(f"  {frames_dir} ({len(segments)} segment-midpoint frames)")


if __name__ == "__main__":
    main()
