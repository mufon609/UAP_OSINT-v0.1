#!/usr/bin/env python3
"""active-speaker.py — mouth-aspect-ratio (MAR) active-speaker detection.

Answers WHICH on-screen face is actually talking during a turn. Composed with
the dlib identity engine (detect-faces.py — WHO each face is), it lets
spot-check-attribution.py verify the *speaking* attribution rather than mere
on-camera presence. Presence is the wrong question: in a two-shot, a reaction
cutaway, or a voiceover package the non-speaking participant's face is
legitimately on screen. The speaker is the face whose MOUTH MOVES.

How it works
------------
Per frame it detects each face (dlib HOG), computes:
  - a 128-d ResNet embedding (identity, via the same face_recognition stack
    detect-faces.py uses, so the encodings feed detect-faces.identify directly), and
  - a mouth-aspect-ratio (MAR) from the 68-point lip landmarks.

Across a per-turn burst of frames, a face whose MAR VARIES (mouth opening and
closing) is speaking; a static, near-closed mouth is listening. The signal is
the RANGE of a face's MAR across the burst (per-person baseline differences
cancel out), not its absolute value. A light window-level audio-RMS gate
separates a real speech window from silence / music / b-roll, so "no face is
talking" can be read as "speaker is off-camera" rather than "dead air".

Pure CPU; no GPU. No model download beyond what face_recognition bundles (the
68-point predictor ships in face_recognition_models). Auto-relaunches under
.venv-face like its sibling tools.

Primary use is as a library for spot-check-attribution.py. The CLI extracts a
burst from a video window and prints per-face MAR per frame — useful for
calibrating --mar-talk-range against known speaker/listener turns.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Venv auto-relaunch — same guarded re-exec idiom as detect-faces.py /
# spot-check-attribution.py; needs face_recognition / dlib / numpy from
# .venv-face. Guarded on the venv existing so --help works under bare Python.
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

import argparse  # noqa: E402

# px; match detect-faces.py so the same faces are kept. 60 (not 80): a 480p
# three-tile grid (weaponized-114) renders side-tile faces at 74-75px, which
# HOG detects and the embedding engine identifies at 0.24-0.34 Euclidean —
# well inside the 0.50 match threshold — so an 80 floor silently dropped
# correctly-identifiable speakers. identify()'s distance threshold, not this
# floor, is the precision gate; the floor only screens background faces.
MIN_FACE_SIZE = 60

# A face must move its mouth by at least this much MAR (range across the burst)
# to count as actively speaking. Calibrated against the sibling corpus; exposed
# as a flag on both this CLI and spot-check-attribution.py.
DEFAULT_MAR_TALK_RANGE = 0.06

# int16 RMS below this is treated as a near-silent window (b-roll / music /
# dead air), so "no on-camera speaker" reads as silence rather than off-camera.
DEFAULT_SILENCE_RMS = 200.0


# ----------------------------------------------------------------------------
# Deferred dependency import (so --help works without dlib installed)
# ----------------------------------------------------------------------------

_DEPS = None


def _deps():
    """Import + cache (face_recognition, numpy). Exits with a contributor hint
    if the face stack is missing."""
    global _DEPS
    if _DEPS is None:
        try:
            import face_recognition
            import numpy as np
        except ImportError:
            sys.exit(
                "error: face_recognition / dlib not installed. Run "
                "scripts/tools/setup-face-embeddings.sh to create .venv-face/ "
                "(this tool auto-relaunches under it)."
            )
        _DEPS = (face_recognition, np)
    return _DEPS


def _to_xywh(loc: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    """face_recognition (top, right, bottom, left) → (x, y, w, h)."""
    top, right, bottom, left = loc
    return (int(left), int(top), int(right - left), int(bottom - top))


# ----------------------------------------------------------------------------
# Mouth-aspect-ratio
# ----------------------------------------------------------------------------

def mouth_aspect_ratio(landmarks: dict, np) -> Optional[float]:
    """Mouth openness for one face from its 68-point lip landmarks.

    MAR = (vertical extent of all lip points) / (horizontal extent), so an open
    mouth scores higher than a closed one and the measure is scale-invariant
    (normalised by mouth width → distance-from-camera independent). Ordering of
    the lip points doesn't matter — we use only their bounding extents.
    Returns None when lip landmarks are unavailable."""
    top = landmarks.get("top_lip")
    bottom = landmarks.get("bottom_lip")
    if not top or not bottom:
        return None
    pts = np.array(top + bottom, dtype=np.float32)
    width = float(pts[:, 0].max() - pts[:, 0].min())
    height = float(pts[:, 1].max() - pts[:, 1].min())
    if width <= 0:
        return None
    return height / width


def analyze_frame(image_path: Path) -> List[Tuple[Tuple[int, int, int, int], "object", Optional[float]]]:
    """Detect every face in a frame and return [((x,y,w,h), encoding, mar), ...].
    `encoding` is the 128-d ResNet embedding (feeds detect-faces.identify);
    `mar` is the mouth-aspect-ratio (None when lip landmarks are unavailable).
    Empty list on read failure / no faces."""
    fr, np = _deps()
    try:
        img = fr.load_image_file(str(image_path))
    except (OSError, ValueError):
        return []
    locs = fr.face_locations(img, model="hog")
    locs = [
        l for l in locs
        if (l[1] - l[3]) >= MIN_FACE_SIZE and (l[2] - l[0]) >= MIN_FACE_SIZE
    ]
    if not locs:
        return []
    encs = fr.face_encodings(img, known_face_locations=locs)
    lms = fr.face_landmarks(img, face_locations=locs)
    out = []
    for loc, enc, lm in zip(locs, encs, lms):
        out.append((_to_xywh(loc), enc, mouth_aspect_ratio(lm, np)))
    return out


# ----------------------------------------------------------------------------
# Audio energy (window-level speech-present gate)
# ----------------------------------------------------------------------------

def window_audio_rms(video_path: Path, start: float, span: float) -> Optional[float]:
    """Mean int16 RMS amplitude of the [start, start+span] audio window.
    Decodes mono 16 kHz s16le via ffmpeg to a pipe and computes RMS with numpy.
    Returns None on ffmpeg failure or empty output (caller treats None as
    'unknown', not 'silent')."""
    _fr, np = _deps()
    cmd = [
        "ffmpeg", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-t", f"{span:.3f}", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "pipe:1",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0 or not proc.stdout:
        return None
    samples = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return None
    return float(np.sqrt(np.mean(samples ** 2)))


# ----------------------------------------------------------------------------
# CLI (ad-hoc calibration: print per-face MAR per frame for a video window)
# ----------------------------------------------------------------------------

def _extract_burst(video: Path, start: float, span: float, count: int, out_dir: Path) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fps = count / max(span, 0.001)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-t", f"{span:.3f}", "-i", str(video),
        "-vf", f"fps={fps}", "-q:v", "2", str(out_dir / "frame_%02d.jpg"),
    ]
    if subprocess.run(cmd, capture_output=True).returncode != 0:
        return []
    return sorted(out_dir.glob("frame_*.jpg"))


def main():
    ap = argparse.ArgumentParser(
        description="Mouth-aspect-ratio active-speaker inspection for a video window.",
    )
    ap.add_argument("video", help="path to source video")
    ap.add_argument("--start", type=float, required=True, help="window start (seconds)")
    ap.add_argument("--span", type=float, default=4.0, help="window length (seconds)")
    ap.add_argument("--frames", type=int, default=7, help="frames sampled across the window")
    args = ap.parse_args()

    video = Path(args.video)
    if not video.is_file():
        sys.exit(f"error: video not found: {video}")

    scratch = Path(tempfile.mkdtemp(prefix="active-speaker-"))
    frames = _extract_burst(video, args.start, args.span, args.frames, scratch)
    rms = window_audio_rms(video, args.start, args.span)
    print(f"window {args.start:.1f}s +{args.span:.1f}s  frames={len(frames)}  "
          f"audio_rms={rms:.0f}" if rms is not None else
          f"window {args.start:.1f}s +{args.span:.1f}s  frames={len(frames)}  audio_rms=NA")
    for i, fp in enumerate(frames):
        faces = analyze_frame(fp)
        descs = [f"face{j}@{bbox} mar={mar:.3f}" if mar is not None else f"face{j}@{bbox} mar=NA"
                 for j, (bbox, _enc, mar) in enumerate(faces)]
        print(f"  frame {i}: {descs if descs else 'no faces'}")
    print(f"\nscratch: {scratch}")


if __name__ == "__main__":
    main()
