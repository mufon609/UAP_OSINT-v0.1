#!/usr/bin/env python3
"""
Mechanical spot-check of a speaker-attribution sibling.

For each turn in `{slug}-attribution.yaml`, samples a BURST of frames evenly
spaced across the turn's source-line time window, runs dlib HOG face-detection
+ ResNet face-embedding matching against the photo-identity-log baselines on
each frame, and compares the resulting identity(ies) against the turn's
`speaker_id`.

Why a burst (not 3 stills) and why dominance (not co-presence)
-------------------------------------------------------------
The earlier version sampled three stills (beg/mid/end) and flagged
`contested-fold` whenever ANY other in-transcript speaker appeared in ANY ONE
frame. Measured against real footage that mis-fires badly: in a two-shot
podcast, a multi-camera interview, or a voiceover news package the non-speaking
participant's face is legitimately on screen (reaction shots, cutaways,
b-roll), so correct turns false-fold. The verdict tracked CAMERA FRAMING, not
attribution error — because face PRESENCE is not the same question as who is
SPEAKING.

This pass keeps the identity engine but changes what the verdict means:

  - Sample K frames across the whole turn window (denser, evenly spaced).
  - Decide by DOMINANCE / CONSISTENCY, not incidental co-presence:
      * the assigned speaker seen in a majority of face-frames → confirmed
        (a co-present other is a two-shot footnote, not a fold);
      * the assigned speaker NEVER seen AND exactly one other in-transcript
        speaker seen consistently → contested-fold (the genuine wrong-label
        signature);
      * an assigned speaker whose `on_camera_role` is voiceover / off-camera /
        mixed, not seen on camera → honestly-unverified (expected), never a fold.

Two evidence tiers (--asd mar)
------------------------------
Mouth-motion (MAR) active-speech evidence is ADMISSIBLE only on faces of at
least MAR_MIN_FACE px — measured at podcast resolutions (480p grid tiles,
74-130px), listener landmark jitter is indistinguishable from speech, so
small-face MAR decides nothing (it is still recorded in the CSV for
calibration). Where speech evidence is admissible it decides the verdict
(who is TALKING); everywhere else the verdict is the presence/dominance test
above, with contested-fold additionally guarded by window length
(MIN_FOLD_SECONDS) and the audio gate (a near-silent window is b-roll).
The honest limitation below the admissibility floor: a wrong label where
both speakers are continuously on camera (grid layout) is invisible to this
gate — the independent text-side verifier carries that case.

Per-turn verdict:
  - confirmed              — assigned speaker dominates the face-frames (co-present
                             others, if any, noted as two-shot/cutaway).
  - confirmed-with-footnote— assigned speaker seen, but not a clean majority;
                             recorded honestly, does NOT block a gate.
  - contested-fold         — assigned speaker never seen AND another in-this-YAML
                             speaker seen consistently. **The wrong-label signal.**
                             Highest-priority review; the gate signal.
  - contested-other        — a baseline identity NOT in this transcript's
                             speakers[] was the only match (b-roll / archival).
                             Informational; attribution may still be correct.
  - honestly-unverified    — assigned role is off-camera/voiceover/mixed and the
                             assigned face was not (or could not be) seen; this
                             is expected, not an error.
  - inconclusive           — no faces / no baseline matches, or signal too weak.
  - no-baseline            — the assigned speaker has no baseline directory
                             (cannot verify, honest signal).
  - n/a-foreign            — turn is foreign-*; not attributable to a live
                             speaker, image check is skipped.

Output:
  - CSV at `{stem}-spot-check.csv` (or `--output PATH`) — one row per turn.
  - Summary on stdout.

Usage:
  spot-check-attribution.py SIBLING.yaml --video VIDEO.mp4
  spot-check-attribution.py SIBLING.yaml --video VIDEO.mp4 --output PATH.csv
  spot-check-attribution.py SIBLING.yaml --video VIDEO.mp4 --frames 9
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Venv auto-relaunch — must happen before importing the detect-faces sibling
# (which needs face_recognition / dlib from .venv-face/). Same guarded re-exec
# idiom as detect-faces.py; doing it here, at process start, means the relaunch
# is deterministic rather than firing mid-function when the sibling module is
# exec'd. The venv is --system-site-packages, so PyYAML +
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
import tempfile
from typing import Optional

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib._common import REPO_ROOT  # noqa: E402
from checks.speaker_attribution_consistency import build_line_ts_map  # noqa: E402

TOOLS_DIR = Path(__file__).resolve().parent

# Burst sampling: K frames evenly spaced across each turn's source-line time
# window. Denser than the old 3-still beg/mid/end pattern so the dominance /
# consistency test is robust to a single off-frame cutaway. MIN_SPAN_S floors
# the window for single-line / sub-second turns so the K frames still differ.
NUM_SAMPLES = 7
MIN_SPAN_S = 2.0

# An assigned speaker with one of these roles can legitimately be off camera
# while speaking (voiceover narration, off-camera interviewer). For such a
# speaker, "assigned face not seen" is expected — honestly-unverified, never a
# fold. `mixed` is included because the speaker alternates on/off camera, so a
# not-seen window is ambiguous, not evidence of a wrong label.
OFF_CAMERA_ROLES = {"voiceover", "off-camera", "mixed"}

# Minimum face box size (min(w, h), px) for a MAR observation to count as
# ACTIVE-SPEECH EVIDENCE. Measured on the weaponized-114 480p grid (74-130px
# faces): listener landmark jitter alone produces MAR ranges to 0.19 and
# adjacent-frame (125-250ms) deltas to 0.14 — indistinguishable from speech
# (speaker median delta 0.044 vs listener 0.037), so below this floor MAR
# carries no speaking signal under ANY sampling design and verdicts ride on
# presence/dominance instead. No footage in the corpus has faces large enough
# to measure where separation begins; 200 is a conservative placeholder —
# recalibrate against known speaker/listener turns (the active-speaker.py CLI)
# before trusting MAR on higher-resolution footage. Inadmissible MAR is still
# recorded in the CSV active_speakers column for calibration.
MAR_MIN_FACE = 200

# Minimum number of recognized face-frames required before "assigned never seen,
# another seen consistently" is allowed to fold. A single recognized face-frame
# (the rest unrecognized) is too thin to overturn a label — one cutaway to the
# listener satisfies a majority-of-one. Below this floor the verdict is
# inconclusive (honest, does not block a gate); the contradiction must be
# corroborated across ≥2 frames to count.
MIN_FOLD_FRAMES = 2

# (Stage 2 / ASD) A fold needs enough on-camera time to establish who is
# speaking. Below this window length the assigned speaker's absence is
# uninformative — the camera may simply not have cut to them during a brief turn
# (e.g. a 3-second host question asked while the camera holds on the guest, who
# reacts / starts answering). Such turns are inconclusive, never folds; a genuine
# long mislabeled block (tens of seconds where one person talks throughout) still
# folds.
MIN_FOLD_SECONDS = 12.0


# ----------------------------------------------------------------------------
# detect-faces / extract-frames module loader (importlib — these filenames have
# hyphens, so they can't be loaded with a normal `import`)
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
    """Return {1-indexed line number: seconds} for every timestamped source
    line. Delegates to the shared hour-aware
    `speaker_attribution_consistency.build_line_ts_map`, so `[H:MM:SS]` ticks
    (sources past 1 h, e.g. jre-2194 → 2:14:58) are covered — the old local
    `[MM:SS]`-only regex silently dropped them, leaving every hour-format turn
    without a sample window. Lines without a leading tick (headers, blanks) are
    absent from the map."""
    return build_line_ts_map(source_path)


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


def sample_window(beg_ts: Optional[float], end_ts: Optional[float]):
    """Turn a turn's (first-line ts, last-line ts) into a (start, span) burst
    window. Returns None when the turn covers no timestamped source line.
    Floors the span at MIN_SPAN_S so single-line / single-tick turns still
    yield distinct frames."""
    if beg_ts is None and end_ts is None:
        return None
    start = beg_ts if beg_ts is not None else end_ts
    end = end_ts if end_ts is not None else beg_ts
    if end < start:
        start, end = end, start
    span = end - start
    if span < MIN_SPAN_S:
        span = MIN_SPAN_S
    return max(0.0, start), span


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


def assigned_roles_for(speaker_id, speakers_by_id) -> set:
    """Return the set of on_camera_role values for the assigned speaker(s)."""
    ids = speaker_id if isinstance(speaker_id, list) else [speaker_id]
    roles = set()
    for m in ids:
        sp = speakers_by_id.get(m)
        if sp and sp.get("on_camera_role"):
            roles.add(sp["on_camera_role"])
    return roles


def verdict_for_turn(expected: set, has_baseline: bool, matches_per_frame: list,
                     defined_baselines: set, yaml_speaker_identities: set,
                     assigned_roles: set):
    """Decide a turn's verdict by DOMINANCE / CONSISTENCY over K sampled frames.

    matches_per_frame  — list of per-frame identity-slug lists (one per sampled
                         frame; empty list = no recognized face in that frame).
    yaml_speaker_identities — identity slugs of this YAML's speakers[].
    defined_baselines  — all identities with baseline dirs anywhere in the corpus.
    assigned_roles     — on_camera_role(s) of the assigned speaker(s).

    Returns (verdict, notes_string). A genuine fold is the assigned speaker
    NEVER seen while another in-transcript speaker is seen consistently — not
    mere on-screen co-presence (two-shots, reaction cutaways, b-roll)."""
    if not has_baseline:
        return "no-baseline", "no baseline directory for assigned speaker(s)"

    n_total = len(matches_per_frame)
    face_frames = [set(f) for f in matches_per_frame if f]
    matched_frames = len(face_frames)
    off_camera_ok = bool(assigned_roles & OFF_CAMERA_ROLES)

    if matched_frames == 0:
        if off_camera_ok:
            return "honestly-unverified", (
                f"no on-camera face recognized across {n_total} frames; assigned "
                f"role {sorted(assigned_roles)} may be off-camera/voiceover")
        return "inconclusive", f"no faces detected or no baseline matches across {n_total} frames"

    assigned_frames = sum(1 for f in face_frames if f & expected)

    other_counts: dict = {}
    for f in face_frames:
        for ident in f:
            if ident in yaml_speaker_identities and ident not in expected:
                other_counts[ident] = other_counts.get(ident, 0) + 1
    outside_any = sorted({
        ident for f in face_frames for ident in f
        if ident in defined_baselines and ident not in yaml_speaker_identities
    })

    # Strict majority of the frames that recognized any face.
    majority = (matched_frames // 2) + 1
    consistent_others = sorted(i for i, c in other_counts.items() if c >= majority)

    # 1. Assigned speaker dominates → confirmed (co-present others = two-shot footnote).
    if assigned_frames >= majority:
        if other_counts:
            return "confirmed", (
                f"assigned speaker dominant ({assigned_frames}/{matched_frames} "
                f"face-frames); co-present (two-shot/cutaway): {sorted(other_counts)}")
        return "confirmed", f"assigned speaker seen in {assigned_frames}/{matched_frames} face-frames"

    # 2. Assigned seen but not a clean majority → honest footnote, not a block.
    if assigned_frames >= 1:
        extra = f"; other YAML-speaker(s) also present: {sorted(other_counts)}" if other_counts else ""
        return "confirmed-with-footnote", (
            f"assigned speaker seen in {assigned_frames}/{matched_frames} face-frames "
            f"(not a clean majority){extra}")

    # 3. Assigned speaker never seen.
    if off_camera_ok:
        others = sorted(other_counts) or outside_any
        return "honestly-unverified", (
            f"assigned speaker not seen in {matched_frames} face-frames; assigned "
            f"role {sorted(assigned_roles)} may be off-camera/voiceover "
            f"(others seen: {others})")
    # Require corroboration across ≥ MIN_FOLD_FRAMES before overturning a label;
    # a lone recognized frame is too thin (one cutaway to the listener).
    if matched_frames < MIN_FOLD_FRAMES:
        return "inconclusive", (
            f"assigned speaker not seen, but only {matched_frames} face-frame(s) "
            f"recognized — insufficient evidence to fold "
            f"(others seen: {sorted(other_counts) or outside_any})")
    if len(consistent_others) == 1:
        only = consistent_others[0]
        return "contested-fold", (
            f"assigned speaker NEVER seen across {matched_frames} face-frames; "
            f"{only} seen consistently ({other_counts[only]}/{matched_frames}) — "
            f"likely wrong label")
    if consistent_others:
        return "contested-fold", (
            f"assigned speaker NEVER seen; multiple YAML-speakers seen "
            f"consistently: {consistent_others}")
    if other_counts:
        # Assigned never seen, others only sporadic → genuinely can't tell.
        return "inconclusive", (
            f"assigned speaker not seen; other YAML-speaker(s) seen sporadically "
            f"(below majority): {sorted(other_counts)}")
    if outside_any:
        return "contested-other", (
            f"assigned speaker not seen; non-YAML identity matched "
            f"(b-roll/archival): {outside_any}")
    return "inconclusive", "only unknown identities matched"


def verdict_for_turn_asd(expected: set, has_baseline: bool, mar_by_identity: dict,
                         matches_per_frame: list, audio_rms, yaml_speaker_identities: set,
                         defined_baselines: set, assigned_roles: set,
                         mar_talk_range: float, silence_rms: float,
                         window_span: float = 0.0):
    """Speaking-aware verdict (Stage 2): active-speech evidence decides where
    it is ADMISSIBLE; presence/dominance decides everywhere else.

    mar_by_identity — {identity: [MAR values from ADMISSIBLE faces only —
                      min(w,h) >= MAR_MIN_FACE; the caller filters]}; a face is
                      *actively speaking* when its MAR RANGE (max-min) over ≥2
                      observations is ≥ mar_talk_range. Measured at podcast
                      resolutions (see MAR_MIN_FACE), small-face MAR is
                      landmark jitter, indistinguishable from speech — letting
                      it decide verdicts is what produced the weaponized-114
                      false folds, so it carries no verdict weight.
    matches_per_frame — per-frame identity lists (presence evidence).
    audio_rms       — window mean int16 RMS (None = unknown); below silence_rms
                      the window is treated as b-roll/music/dead air.

    With admissible speech evidence: a listening face on screen is NOT a
    wrong-label signal — only another identified person *speaking* in the
    assigned span folds. Without it, the verdict delegates to the
    presence/dominance test (`verdict_for_turn`), whose fold (assigned NEVER
    seen, another seen consistently) is additionally guarded here by window
    length (a brief window proves nothing about who is off-camera) and the
    audio gate (a near-silent window is b-roll, not evidence)."""
    if not has_baseline:
        return "no-baseline", "no baseline directory for assigned speaker(s)"

    off_camera_ok = bool(assigned_roles & OFF_CAMERA_ROLES)
    audio_present = audio_rms is not None and audio_rms >= silence_rms
    matched_frames = sum(1 for f in matches_per_frame if f)

    talking = {}
    for slug, mars in mar_by_identity.items():
        if len(mars) >= 2:
            rng = max(mars) - min(mars)
            if rng >= mar_talk_range:
                talking[slug] = rng

    if matched_frames == 0:
        if off_camera_ok:
            return "honestly-unverified", (
                "no on-camera face recognized; assigned role "
                f"{sorted(assigned_roles)} may be off-camera/voiceover")
        return "inconclusive", "no faces detected or no baseline matches"

    assigned_talking = sorted(s for s in talking if s in expected)
    other_yaml_talking = sorted(
        s for s in talking if s in yaml_speaker_identities and s not in expected)

    if assigned_talking:
        if other_yaml_talking:
            return "confirmed-with-footnote", (
                f"assigned speaker actively speaking; overlapping speech with "
                f"{other_yaml_talking} (crosstalk)")
        return "confirmed", (
            f"assigned speaker is the active on-camera speaker "
            f"(MAR range {talking[assigned_talking[0]]:.3f})")

    if other_yaml_talking:
        # A voiceover/mixed/off-camera assigned speaker may legitimately be
        # narrating over b-roll of another person talking (a news package over
        # interview footage). MAR sees the on-screen mouth move but cannot tell
        # whose voice is on the track — so this is ambiguous, not a fold.
        if off_camera_ok:
            return "honestly-unverified", (
                f"assigned speaker {sorted(assigned_roles)} not visibly speaking while "
                f"{other_yaml_talking} speaks on camera — ambiguous "
                f"(possible voiceover/narration over b-roll)")
        if window_span < MIN_FOLD_SECONDS:
            return "inconclusive", (
                f"{other_yaml_talking} seen speaking but the turn window is only "
                f"{window_span:.0f}s — too brief to confirm the assigned speaker is "
                f"off-camera (camera may not have cut to them)")
        if len(other_yaml_talking) == 1:
            return "contested-fold", (
                f"active on-camera speaker is {other_yaml_talking[0]}, NOT the "
                f"assigned speaker — likely wrong label")
        return "contested-fold", (
            f"active on-camera speakers {other_yaml_talking} ≠ assigned — likely wrong label")

    # No admissible active-speech evidence → presence/dominance decides, with
    # the fold additionally guarded by window length + the audio gate.
    verdict, notes = verdict_for_turn(
        expected, has_baseline, matches_per_frame, defined_baselines,
        yaml_speaker_identities, assigned_roles)
    if verdict == "contested-fold":
        if window_span < MIN_FOLD_SECONDS:
            return "inconclusive", (
                f"assigned speaker not seen, but the turn window is only "
                f"{window_span:.0f}s — too brief to confirm they are off-camera "
                f"(camera may not have cut to them)")
        if audio_rms is not None and not audio_present:
            return "inconclusive", (
                "assigned speaker not seen but window near-silent "
                "(b-roll/music/dead air) — presence proves nothing here")
        notes += " (presence signature; no admissible mouth-motion evidence at this face size)"
    return verdict, notes


# Verdict bookkeeping — order drives the summary print + CSV summary key set.
VERDICTS = (
    "confirmed", "confirmed-with-footnote", "contested-fold", "contested-other",
    "honestly-unverified", "inconclusive", "no-baseline", "n/a-foreign",
)


# ----------------------------------------------------------------------------
# Orchestrator
# ----------------------------------------------------------------------------

def spot_check(yaml_path: Path, video_path: Path, output_csv: Path,
               scratch_root: Path = None, embed_threshold: float = 0.50,
               num_samples: int = NUM_SAMPLES, asd_engine: str = "mar",
               mar_talk_range: float = 0.06, silence_rms: float = 200.0,
               mar_min_face: int = MAR_MIN_FACE):
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

    # Load detect-faces helpers + the cached baseline embedding index, and the
    # extract-frames burst primitive (one ffmpeg decode → K evenly-spaced frames).
    # The active-speaker engine (Stage 2 — MAR lip-motion) is loaded only when
    # asd_engine != "none"; with "none" the verdict falls back to the Stage-1
    # presence/dominance test.
    detect_faces_mod = _load_sibling("detect-faces.py")
    extract_frames_mod = _load_sibling("extract-frames.py")
    asd_mod = _load_sibling("active-speaker.py") if asd_engine == "mar" else None
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

    def fmt_ts(t):
        if t is None:
            return ""
        return f"{int(t // 60)}:{int(t % 60):02d}"

    rows = []
    summary = {k: 0 for k in VERDICTS}

    for t in data.get("turns", []):
        sid = t["speaker_id"]
        lr = t["line_range"]
        lo, hi = parse_range(lr)
        roles = assigned_roles_for(sid, speakers_by_id)
        role_str = "|".join(sorted(roles))

        if isinstance(sid, str) and sid.startswith("foreign-"):
            rows.append({
                "line_range": lr, "speaker_id": sid, "on_camera_role": "",
                "window": "", "n_frames": 0, "n_face_frames": 0,
                "assigned_frames": 0, "others_seen": "",
                "active_speakers": "", "audio_rms": "",
                "verdict": "n/a-foreign",
                "notes": "foreign content; no live-speaker check",
            })
            summary["n/a-foreign"] += 1
            continue

        beg_ts = first_ts_at_or_after(line_to_ts, lo, hi)
        end_ts = last_ts_at_or_before(line_to_ts, hi, lo)
        window = sample_window(beg_ts, end_ts)

        matches_per_frame = []
        mar_by_identity: dict = {}       # admissible faces only — verdict evidence
        mar_all_by_identity: dict = {}   # every face — CSV calibration record
        n_frames = 0
        audio_rms = None
        if window is not None:
            start, span = window
            frame_dir = scratch_root / "frames" / f"L{lo:05d}"
            frames = extract_frames_mod.extract_burst_individual(
                video_path, start, span, num_samples, frame_dir)
            n_frames = len(frames)
            if asd_mod is not None:
                audio_rms = asd_mod.window_audio_rms(video_path, start, span)
                for fp in frames:
                    idents = []
                    for bbox, enc, mar in asd_mod.analyze_frame(fp):
                        slug = detect_faces_mod.identify(enc, baseline_index, embed_threshold)
                        if slug:
                            idents.append(slug)
                            if mar is not None:
                                mar_all_by_identity.setdefault(slug, []).append(mar)
                                if min(bbox[2], bbox[3]) >= mar_min_face:
                                    mar_by_identity.setdefault(slug, []).append(mar)
                    matches_per_frame.append(idents)
            else:
                for fp in frames:
                    matches_per_frame.append(
                        identify_frame(fp, detect_faces_mod, baseline_index, embed_threshold))

        expected, has_baseline = expected_identities(sid, speakers_by_id, defined_baselines)
        face_frames = [set(f) for f in matches_per_frame if f]
        matched_frames = len(face_frames)

        if asd_mod is not None:
            verdict, notes = verdict_for_turn_asd(
                expected, has_baseline, mar_by_identity, matches_per_frame, audio_rms,
                yaml_speaker_identities, defined_baselines, roles,
                mar_talk_range, silence_rms,
                window_span=(window[1] if window is not None else 0.0))
        else:
            verdict, notes = verdict_for_turn(
                expected, has_baseline, matches_per_frame, defined_baselines,
                yaml_speaker_identities, roles)

        assigned_frames = sum(1 for f in face_frames if f & expected)
        others_count: dict = {}
        for f in face_frames:
            for ident in f:
                if ident not in expected:
                    others_count[ident] = others_count.get(ident, 0) + 1
        others_seen = ",".join(f"{k}:{v}" for k, v in sorted(others_count.items()))
        # CSV records ALL MAR ranges (admissible or not) for calibration; only
        # the admissible subset (mar_by_identity) carried verdict weight.
        active_speakers = ",".join(
            f"{k}:{(max(v) - min(v)):.3f}"
            for k, v in sorted(mar_all_by_identity.items()) if len(v) >= 2)

        win_str = ""
        if window is not None:
            win_str = f"{fmt_ts(window[0])}–{fmt_ts(window[0] + window[1])}"

        rows.append({
            "line_range": lr,
            "speaker_id": sid if isinstance(sid, str) else ",".join(sid),
            "on_camera_role": role_str,
            "window": win_str,
            "n_frames": n_frames,
            "n_face_frames": matched_frames,
            "assigned_frames": assigned_frames,
            "others_seen": others_seen,
            "active_speakers": active_speakers,
            "audio_rms": f"{audio_rms:.0f}" if audio_rms is not None else "",
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
          f"embed-threshold: {embed_threshold} (Euclidean)   "
          f"frames/turn: {num_samples}")
    print(f"  Total turns scanned: {len(rows)}")
    for k in VERDICTS:
        print(f"  {k:<24}: {summary[k]}")
    if summary["contested-fold"]:
        print()
        print("CONTESTED-FOLD turns (review urgently — likely wrong label):")
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
        description="Spot-check speaker-attribution sibling via a per-turn frame burst.",
    )
    ap.add_argument("yaml_path", help="path to {slug}-attribution.yaml")
    ap.add_argument("--video", required=True, help="path to source video file")
    ap.add_argument("--output", help="output CSV path (default: alongside yaml)")
    ap.add_argument(
        "--frames", type=int, default=NUM_SAMPLES,
        help=f"frames sampled per turn across its time window (default {NUM_SAMPLES}; "
             "denser sampling makes the dominance/consistency test more robust)",
    )
    ap.add_argument(
        "--asd", choices=["mar", "none"], default="mar",
        help="active-speaker engine: 'mar' (default) verifies WHO is speaking via "
             "mouth-motion (active-speaker.py); 'none' falls back to the Stage-1 "
             "presence/dominance test (who is on camera)",
    )
    ap.add_argument(
        "--mar-talk-range", type=float, default=0.06,
        help="minimum MAR range (max-min across the burst) for a face to count as "
             "actively speaking (default 0.06; --asd mar only)",
    )
    ap.add_argument(
        "--mar-min-face", type=int, default=MAR_MIN_FACE,
        help="minimum face box size (min(w,h), px) for MAR to count as active-"
             f"speech evidence (default {MAR_MIN_FACE}); below it, small-face "
             "landmark jitter is indistinguishable from speech, so verdicts "
             "ride on presence/dominance and MAR is recorded for calibration "
             "only (--asd mar only)",
    )
    ap.add_argument(
        "--silence-rms", type=float, default=200.0,
        help="window int16 audio RMS below which the window is treated as "
             "silent/b-roll (default 200; --asd mar only)",
    )
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

    spot_check(yaml_path, video_path, output, embed_threshold=args.embed_threshold,
               num_samples=args.frames, asd_engine=args.asd,
               mar_talk_range=args.mar_talk_range, silence_rms=args.silence_rms,
               mar_min_face=args.mar_min_face)


if __name__ == "__main__":
    main()
