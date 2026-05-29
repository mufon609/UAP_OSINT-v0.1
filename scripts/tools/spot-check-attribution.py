#!/usr/bin/env python3
"""
Mechanical spot-check of a speaker-attribution sibling.

For each turn in `{slug}-attribution.yaml`, extracts THREE frames from the
source video at the timestamps of the FIRST, MIDDLE, and LAST source lines
covered by the turn, runs dlib HOG face-detection + ResNet face-embedding
matching against the photo-identity-log baselines on each frame, and compares
the resulting identity(ies) against the turn's `speaker_id`.

The beginning/middle/end sampling pattern catches the fold-up failure mode
that the producer + verifier text-passes cannot catch:

  - If turn 380-466 is labeled `s2` (Elizondo) and the START frame at
    [13:23] shows Elizondo AND the END frame at [16:47] shows Elizondo
    BUT the MIDDLE frame at [15:05] shows Rogan, then the turn has
    silently folded an embedded Rogan question into Elizondo's
    monologue. Spot-check surfaces it; text-pass cannot.

Per-turn verdict:
  - confirmed         — at least one of the 3 frames matched the assigned
                        speaker; no other DEFINED speaker (in speakers[])
                        was detected.
  - contested-fold    — assigned speaker may or may not have been seen,
                        AND another speaker FROM THE SAME YAML's speakers[]
                        was detected in at least one frame. **This is the
                        fold-up signal.** Highest-priority review.
  - contested-other   — a baseline identity NOT in this transcript's
                        speakers[] was detected (b-roll footage of another
                        person, or an archival clip). Embedding matching makes
                        a look-alike false-positive far less likely than the
                        old perceptual-hash engine. Informational; the assigned
                        attribution may still be correct.
  - inconclusive      — no faces detected, or no baseline matches at all.
  - no-baseline       — the assigned speaker has no baseline directory
                        (cannot verify, honest signal).
  - n/a-foreign       — turn is foreign-*; not attributable to a live
                        speaker, image check is skipped.

Output:
  - CSV at `{stem}-spot-check.csv` (or `--output PATH`) — one row per
    turn with line_range, speaker_id, three timestamps, three matched
    identities, verdict, notes.
  - Summary on stdout.

Usage:
  spot-check-attribution.py SIBLING.yaml --video VIDEO.mp4
  spot-check-attribution.py SIBLING.yaml --video VIDEO.mp4 --output PATH.csv
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Venv auto-relaunch — must happen before importing the detect-faces sibling
# (which needs face_recognition / dlib from .venv-face/). Same guarded re-exec
# idiom as detect-faces.py / diarize-audio.py; doing it here, at process start,
# means the relaunch is deterministic rather than firing mid-function when the
# sibling module is exec'd. The venv is --system-site-packages, so PyYAML +
# ffmpeg-driving stdlib stay available after the relaunch. Guarded on the venv
# existing so --help works under bare system Python (help-check stays green).
# ---------------------------------------------------------------------------
_VENV_DIR = Path(__file__).resolve().parent.parent.parent / ".venv-face"
_VENV_PYTHON = _VENV_DIR / "bin" / "python3"
if (
    _VENV_PYTHON.is_file()
    and Path(sys.prefix).resolve() != _VENV_DIR.resolve()
    and os.environ.get("FACE_VENV_ACTIVE") != "1"
):
    os.environ["FACE_VENV_ACTIVE"] = "1"
    os.execv(str(_VENV_PYTHON), [str(_VENV_PYTHON)] + sys.argv)

import argparse
import csv
import importlib.util
import re
import shutil
import subprocess
import tempfile
from typing import Optional

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib._common import REPO_ROOT  # noqa: E402

TOOLS_DIR = Path(__file__).resolve().parent
TS_RE = re.compile(r"^\[(\d+):(\d+)\]")


# ----------------------------------------------------------------------------
# detect-faces module loader (same importlib pattern stitch-transcript uses
# — detect-faces.py has hyphens, can't `import`)
# ----------------------------------------------------------------------------

def _load_sibling(rel_filename: str):
    path = TOOLS_DIR / rel_filename
    spec = importlib.util.spec_from_file_location(rel_filename.replace(".py", "").replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ----------------------------------------------------------------------------
# Source line → timestamp mapping
# ----------------------------------------------------------------------------

def build_line_timestamp_map(source_path: Path) -> dict:
    """Return {1-indexed line number: seconds} for every `[MM:SS] text` line.
    Lines without a timestamp prefix (file headers, blanks) are absent from
    the map."""
    out = {}
    with source_path.open() as f:
        for i, line in enumerate(f, start=1):
            m = TS_RE.match(line)
            if m:
                out[i] = int(m.group(1)) * 60 + int(m.group(2))
    return out


def first_ts_at_or_after(line_to_ts: dict, target_line: int, max_line: int) -> Optional[float]:
    """Walk forward from target_line looking for any line with a timestamp,
    up to max_line. Header/blank lines skip cleanly."""
    for ln in range(target_line, max_line + 1):
        if ln in line_to_ts:
            return line_to_ts[ln]
    return None


def last_ts_at_or_before(line_to_ts: dict, target_line: int, min_line: int) -> Optional[float]:
    """Walk backward from target_line looking for any line with a timestamp."""
    for ln in range(target_line, min_line - 1, -1):
        if ln in line_to_ts:
            return line_to_ts[ln]
    return None


# ----------------------------------------------------------------------------
# Frame extraction (ffmpeg)
# ----------------------------------------------------------------------------

def extract_frame(video_path: Path, ts_seconds: float, out_path: Path) -> bool:
    """Extract a single frame from video at `ts_seconds` to `out_path`.
    Returns True on success."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{ts_seconds:.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(out_path),
    ]
    res = subprocess.run(cmd, capture_output=True)
    return res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0


# ----------------------------------------------------------------------------
# Per-frame identification
# ----------------------------------------------------------------------------

def identify_frame(frame_path: Path, detect_faces_mod, baseline_index,
                   embed_threshold: float):
    """Detect + embed every face in frame_path (dlib HOG + ResNet, one pass on
    the original pixels) and match each against the baseline embedding index.
    Returns the list of identity slugs detected — one best match per face,
    within embed_threshold Euclidean distance (may be empty)."""
    if not frame_path.exists():
        return []
    try:
        faces = detect_faces_mod.encode_faces_in_image(frame_path)
    except Exception:
        return []
    identities = []
    for _bbox, enc in faces:
        slug = detect_faces_mod.identify(enc, baseline_index, embed_threshold)
        if slug:
            identities.append(slug)
    return identities


# ----------------------------------------------------------------------------
# Speaker_id → identity slug mapping
# ----------------------------------------------------------------------------

def speaker_to_identity_slug(speaker: dict) -> Optional[str]:
    """Derive the photo-identity-log baseline directory name for a speaker.
    Precedence: node_link slug > kebab-cased name. Returns the slug string
    or None if no usable mapping (caller checks baseline existence)."""
    nl = speaker.get("node_link")
    if nl and nl.startswith("/people/"):
        return nl.rsplit("/", 1)[-1]
    name = speaker.get("name", "")
    if not name:
        return None
    # Kebab-case the name
    return re.sub(r"\s+", "-", name.strip().lower())


def baselines_available(baselines_root: Path) -> set:
    """Return set of identity-slug directory names present under baselines/."""
    if not baselines_root.is_dir():
        return set()
    return {p.name for p in baselines_root.iterdir() if p.is_dir()}


# ----------------------------------------------------------------------------
# Per-turn verdict
# ----------------------------------------------------------------------------

def parse_range(s: str):
    if "-" in s:
        lo, hi = s.split("-", 1)
        return int(lo), int(hi)
    n = int(s)
    return n, n


def expected_identities(speaker_id, speakers_by_id, available_baselines):
    """Return (set of expected identity slugs, has_any_baseline). For mixed-
    exchange [s1, s2], any of the listed speakers' identities counts as a
    match."""
    if isinstance(speaker_id, list):
        ids = [speaker_to_identity_slug(speakers_by_id[m]) for m in speaker_id if m in speakers_by_id]
    else:
        ids = [speaker_to_identity_slug(speakers_by_id.get(speaker_id, {}))]
    ids = [i for i in ids if i]
    has_baseline = any(i in available_baselines for i in ids)
    return set(ids), has_baseline


def verdict_for_turn(expected: set, has_baseline: bool, matches_per_frame: list,
                     defined_baselines: set, yaml_speaker_identities: set):
    """matches_per_frame = list of 3 lists of identity slugs (beg, mid, end).
    yaml_speaker_identities = identity slugs of speakers in this YAML's
    speakers[] (the in-this-transcript set).
    defined_baselines = all identities with baseline dirs anywhere in the
    corpus (broader set).
    Returns (verdict, notes_string).

    A match against a speaker IN this YAML's speakers[] is a fold-up signal
    (contested-fold). A match against any OTHER baseline is contested-other
    — could be b-roll or archival footage (embedding matching makes a
    look-alike false-positive far less likely than the old engine)."""
    if not has_baseline:
        return "no-baseline", "no baseline directory for assigned speaker(s)"

    all_matches = [m for frame_matches in matches_per_frame for m in frame_matches]
    if not all_matches:
        return "inconclusive", "no faces detected or no baseline matches across 3 frames"

    assigned_hits = sum(1 for m in all_matches if m in expected)
    # Split "other" detections by whether the identity is in this YAML's
    # speaker set (fold-up risk) or not (b-roll / false-positive territory).
    other_in_yaml = sorted({m for m in all_matches if m in yaml_speaker_identities and m not in expected})
    other_outside_yaml = sorted({m for m in all_matches if m in defined_baselines and m not in yaml_speaker_identities})

    if other_in_yaml:
        if assigned_hits:
            return "contested-fold", (
                f"assigned speaker seen ({assigned_hits}/3 frames) AND another "
                f"YAML-speaker also seen: {other_in_yaml}"
            )
        return "contested-fold", f"assigned speaker not detected; another YAML-speaker seen: {other_in_yaml}"

    if other_outside_yaml:
        if assigned_hits:
            # Confirmed (assigned seen) but also saw a non-YAML identity →
            # informational footnote, not a contested verdict.
            return "confirmed", (
                f"{assigned_hits}/3 frames matched assigned speaker; "
                f"non-YAML identity also detected (b-roll/archival/false-positive): "
                f"{other_outside_yaml}"
            )
        return "contested-other", (
            f"assigned speaker not detected; non-YAML identity matched "
            f"(b-roll/archival/false-positive): {other_outside_yaml}"
        )

    if assigned_hits:
        return "confirmed", f"{assigned_hits}/3 frames matched assigned speaker"
    return "inconclusive", f"only unknown identities matched: {sorted(set(all_matches))}"


# ----------------------------------------------------------------------------
# Orchestrator
# ----------------------------------------------------------------------------

def spot_check(yaml_path: Path, video_path: Path, output_csv: Path,
               scratch_root: Path = None, embed_threshold: float = 0.50):
    with yaml_path.open() as f:
        data = yaml.safe_load(f)

    source_path = REPO_ROOT / data["source_path"]
    if not source_path.is_file():
        sys.exit(f"error: source_path file not found: {source_path}")
    if not video_path.is_file():
        sys.exit(f"error: video file not found: {video_path}")

    speakers_by_id = {sp["id"]: sp for sp in data.get("speakers", [])}
    yaml_speaker_identities = {
        slug for slug in (speaker_to_identity_slug(sp) for sp in data.get("speakers", []))
        if slug
    }

    # Load detect-faces helpers + the cached baseline embedding index
    detect_faces_mod = _load_sibling("detect-faces.py")
    baseline_index = detect_faces_mod.build_baseline_index()
    baselines_root = REPO_ROOT / "sources/photo-identity-log/baselines"
    defined_baselines = baselines_available(baselines_root)

    # Build source line → timestamp map (header lines won't have a timestamp;
    # foreign-other turns over the header rows will skip cleanly)
    line_to_ts = build_line_timestamp_map(source_path)
    max_line = data["source_line_count"]

    if scratch_root is None:
        scratch_root = Path(tempfile.mkdtemp(prefix=f"spot-check-{data['slug']}-"))
    print(f"scratch dir: {scratch_root}")

    rows = []
    summary = {"confirmed": 0, "contested-fold": 0, "contested-other": 0,
               "inconclusive": 0, "no-baseline": 0, "n/a-foreign": 0}

    for t in data.get("turns", []):
        sid = t["speaker_id"]
        lr = t["line_range"]
        lo, hi = parse_range(lr)

        if isinstance(sid, str) and sid.startswith("foreign-"):
            rows.append({
                "line_range": lr, "speaker_id": sid,
                "beg_ts": "", "beg_matches": "",
                "mid_ts": "", "mid_matches": "",
                "end_ts": "", "end_matches": "",
                "verdict": "n/a-foreign",
                "notes": "foreign content; no live-speaker check",
            })
            summary["n/a-foreign"] += 1
            continue

        # Three target lines: first, middle, last in range
        mid = (lo + hi) // 2
        beg_ts = first_ts_at_or_after(line_to_ts, lo, hi)
        mid_ts = first_ts_at_or_after(line_to_ts, mid, hi)
        end_ts = last_ts_at_or_before(line_to_ts, hi, lo)

        # If beg=end (single line) keep all three as same timestamp
        timestamps = [beg_ts, mid_ts, end_ts]

        # Extract + identify each frame
        matches_per_frame = []
        frame_labels = ["beg", "mid", "end"]
        seen_paths = {}
        for label, ts in zip(frame_labels, timestamps):
            if ts is None:
                matches_per_frame.append([])
                continue
            # Dedupe: if beg_ts == mid_ts == end_ts, only extract once
            if ts in seen_paths:
                matches_per_frame.append(seen_paths[ts])
                continue
            frame_path = scratch_root / "frames" / f"L{lo:05d}-{label}-{int(ts):05d}s.jpg"
            ok = extract_frame(video_path, ts, frame_path)
            if not ok:
                matches_per_frame.append([])
                continue
            idents = identify_frame(frame_path, detect_faces_mod,
                                    baseline_index, embed_threshold)
            matches_per_frame.append(idents)
            seen_paths[ts] = idents

        expected, has_baseline = expected_identities(sid, speakers_by_id, defined_baselines)
        verdict, notes = verdict_for_turn(expected, has_baseline,
                                           matches_per_frame, defined_baselines,
                                           yaml_speaker_identities)

        def fmt_ts(t):
            if t is None: return ""
            return f"{int(t//60)}:{int(t%60):02d}"

        rows.append({
            "line_range": lr, "speaker_id": sid if isinstance(sid, str) else ",".join(sid),
            "beg_ts": fmt_ts(beg_ts),
            "beg_matches": "|".join(matches_per_frame[0]),
            "mid_ts": fmt_ts(mid_ts),
            "mid_matches": "|".join(matches_per_frame[1]),
            "end_ts": fmt_ts(end_ts),
            "end_matches": "|".join(matches_per_frame[2]),
            "verdict": verdict,
            "notes": notes,
        })
        summary[verdict] += 1

    # Write CSV
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    print(f"\nWrote {output_csv}")
    print()
    print(f"Spot-check verdict — {data['slug']}")
    print(f"  engine: dlib HOG + ResNet embeddings   "
          f"embed-threshold: {embed_threshold} (Euclidean)")
    print(f"  Total turns scanned: {len(rows)}")
    for k in ("confirmed", "contested-fold", "contested-other",
              "inconclusive", "no-baseline", "n/a-foreign"):
        print(f"  {k:<16}: {summary[k]}")
    if summary["contested-fold"]:
        print()
        print("CONTESTED-FOLD turns (review urgently — potential fold-up):")
        for r in rows:
            if r["verdict"] == "contested-fold":
                print(f"  lines {r['line_range']:>12} (assigned {r['speaker_id']}): {r['notes']}")
    if summary["contested-other"]:
        print()
        print("CONTESTED-OTHER turns (informational — non-YAML identity detected):")
        for r in rows:
            if r["verdict"] == "contested-other":
                print(f"  lines {r['line_range']:>12} (assigned {r['speaker_id']}): {r['notes']}")
    return summary


def main():
    ap = argparse.ArgumentParser(
        description="Spot-check speaker-attribution sibling via beg/mid/end frames.",
    )
    ap.add_argument("yaml_path", help="path to {slug}-attribution.yaml")
    ap.add_argument("--video", required=True, help="path to source video file")
    ap.add_argument("--output", help="output CSV path (default: alongside yaml)")
    ap.add_argument(
        "--embed-threshold", type=float, default=0.50,
        help="max Euclidean distance between a frame face embedding and a "
             "baseline reference to count as a match (default 0.50; dlib's own "
             "compare_faces tolerance is 0.6 — 0.50 is tighter, favouring "
             "precision over recall to keep contested-other false positives low)",
    )
    args = ap.parse_args()

    yaml_path = Path(args.yaml_path)
    video_path = Path(args.video)
    if args.output:
        output = Path(args.output)
    else:
        output = yaml_path.with_name(yaml_path.stem.replace("-attribution", "") + "-spot-check.csv")

    spot_check(yaml_path, video_path, output, embed_threshold=args.embed_threshold)


if __name__ == "__main__":
    main()
