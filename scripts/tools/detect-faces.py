#!/usr/bin/env python3
"""detect-faces.py — face detection, crop logging, and identity-baseline tracking
for frames extracted by scripts/tools/extract-frames.py.

Multi-speaker video sources (panel discussions, interviews, documentaries) need
visual speaker identification to disambiguate whisper / YouTube auto-caption
transcripts that don't preserve speaker identity. extract-frames.py produces
still frames at contested timestamps; this tool runs face detection on those
frames, saves each detected face as its own crop, and tracks a persistent log
of who-is-who via contributor-curated baseline directories.

Four subcommands:

  detect            Process a directory of images (or an extract-frames
                    index.md) and save face crops to
                    sources/photo-identity-log/crops/. Reports the per-image
                    and total counts of faces detected vs. faces identified
                    (matched by face embedding against an existing baseline).

  register          Move a labeled crop from crops/ into baselines/{identity}/,
                    compute its sha256, and append a manifest entry under
                    sources/photo-identity-log/manifest.yaml. The crop becomes
                    a persistent identity reference for future detect runs.

  prune             Remove crops in crops/ whose face embedding matches no
                    baseline identity — i.e., unlabeled crops the contributor
                    has decided not to keep. Default is interactive (prompts
                    before deletion); --dry-run for preview; --force to skip.

  encode-baselines  (Re)build the baseline-embedding cache and report
                    per-identity reference counts.

Storage discipline:

  1. Face-embedding dedup at save time. dlib's ResNet maps each detected face
     to a 128-d vector; new crops whose embedding is within EMBED_DEDUP_DISTANCE
     of anything already in crops/ or baselines/ are skipped. The threshold is
     tight (near-identical frames only) so distinct-angle shots of the same
     person survive — those are what make a rich multi-reference baseline.
  2. Crops are 256×256 px, JPEG quality 85 (~8-15 KB average).
  3. detect-mode operates on contact sheets by default (one image per
     timestamp); cuts crop volume 5x vs. processing all individual burst
     frames.

The log is tracked in git. baselines/ + manifest.yaml are the persistent
identity reference set; crops/ is the working area for unidentified faces
awaiting contributor review.

Matching engine: dlib HOG face detector + ResNet 128-d face embeddings via the
face_recognition library, installed in a project-local venv at .venv-face/ (run
scripts/tools/setup-face-embeddings.sh once). This tool auto-relaunches under
that venv's Python, so run it directly without activating anything. ffmpeg /
frame extraction prerequisites are covered by setup-photo-identity.sh. See
scripts/tools/VIDEO-PIPELINE.md for the end-to-end workflow this tool is
step 3 of.

Usage examples:
  # Detect faces in every frame referenced by an extract-frames index
  ./detect-faces.py detect --index /tmp/frames-foo/index.md

  # Detect in a single directory of images
  ./detect-faces.py detect --input /tmp/frames-foo/anchor/

  # Register a baseline reference for an identity
  ./detect-faces.py register --crop sources/photo-identity-log/crops/foo_face_01.jpg \\
      --identity jake-barber --source-video sources/video/foo.mp4 \\
      --source-timestamp 0:15 --bbox 480,120,180,180

  # Prune unidentified crops (interactive)
  ./detect-faces.py prune
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Venv auto-relaunch — must happen before importing anything dlib-touched.
# face_recognition + dlib live inside .venv-face/ at the repo root (PEP 668
# blocks system-wide pip on Debian/Kali, and dlib's C++ footprint is too heavy
# to want system-wide). The venv is created --system-site-packages, so cv2 /
# PIL / PyYAML stay importable after the re-exec. Same detection idiom as
# diarize-audio.py: compare sys.prefix to the venv dir (venv's bin/python3 is a
# symlink to the system interpreter, so realpath() can't distinguish them).
# Guarded on the venv existing so `--help` works under bare system Python and
# scripts/tests/help-check.sh stays green without .venv-face present.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parent.parent.parent  # scripts/tools/detect-faces.py → repo root
_VENV_DIR = _REPO_ROOT / ".venv-face"
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
import re
import shutil
from datetime import datetime, timezone
from typing import List, Optional, Tuple

# scripts/tools/detect-faces.py — scripts/ on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import REPO_ROOT, compute_sha256, strict_yaml_load


# ----------------------------------------------------------------------------
# Constants + paths
# ----------------------------------------------------------------------------

LOG_DIR = REPO_ROOT / "sources" / "photo-identity-log"
CROPS_DIR = LOG_DIR / "crops"
BASELINES_DIR = LOG_DIR / "baselines"
MANIFEST_PATH = LOG_DIR / "manifest.yaml"
INDEX_PATH = LOG_DIR / "index.csv"
# Derived cache of 128-d baseline embeddings (gitignored; rebuilt on demand
# from baselines/ via a sha256 fingerprint). See build_baseline_index().
BASELINE_ENCODINGS_PATH = LOG_DIR / "baseline-encodings.npz"

CROP_SIZE = 256        # px, square
JPEG_QUALITY = 85
MIN_FACE_SIZE = 80     # px, minimum face box to keep — filters tiny background faces
PADDING_FRAC = 0.30    # bbox padding (fraction of face dimension) added before crop

# Face-embedding distance thresholds (Euclidean / L2 over dlib's 128-d ResNet
# encodings). The library's own compare_faces() default tolerance is 0.6; same-
# person frames typically land ~0.3-0.5, different-person ~0.6+.
#
#   EMBED_DEDUP_DISTANCE — crops within this distance are treated as the same
#     shot and skipped at save time. Tight (0.20) so only near-identical frames
#     merge; distinct-angle shots of the same person survive into crops/ where
#     they can be promoted to additional baseline references.
#   EMBED_MATCH_DISTANCE — default identity-match tolerance for the `detect`
#     identity column and `prune`. Tighter than the library default to favour
#     precision (a false identity is the failure mode this engine exists to
#     kill). spot-check-attribution.py exposes this as --embed-threshold.
EMBED_DEDUP_DISTANCE = 0.20
EMBED_MATCH_DISTANCE = 0.50


# ----------------------------------------------------------------------------
# Dependency import (deferred so --help works without cv2 installed)
# ----------------------------------------------------------------------------

def _import_deps():
    """Import PIL (cropping) + face_recognition / numpy (detect + embed) with a
    contributor-friendly error if missing. Returns (Image, face_recognition, np)."""
    try:
        from PIL import Image
    except ImportError:
        sys.exit("error: Pillow not installed (python3-pil).")
    try:
        import face_recognition
        import numpy as np
    except ImportError:
        sys.exit(
            "error: face_recognition / dlib not installed. Run "
            "scripts/tools/setup-face-embeddings.sh to create .venv-face/ "
            "(this tool auto-relaunches under it)."
        )
    return Image, face_recognition, np


# ----------------------------------------------------------------------------
# Face detection + embedding (dlib HOG detector + ResNet 128-d encodings)
# ----------------------------------------------------------------------------

def _to_xywh(loc: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    """face_recognition (top, right, bottom, left) → (x, y, w, h)."""
    top, right, bottom, left = loc
    return (int(left), int(top), int(right - left), int(bottom - top))


def _to_css(bbox: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    """(x, y, w, h) → face_recognition (top, right, bottom, left)."""
    x, y, w, h = bbox
    return (int(y), int(x + w), int(y + h), int(x))


def detect_faces_in_image(image_path: Path) -> List[Tuple[int, int, int, int]]:
    """Return a list of (x, y, w, h) bounding boxes for faces in the image,
    detected via dlib's HOG detector. Empty list on read failure or no faces.

    Filtering: drops detections smaller than MIN_FACE_SIZE on either axis. HOG
    catches profile/angled/looking-down shots a frontal Haar cascade misses,
    which is the bulk of the recall gain over the old engine."""
    return [bbox for bbox, _ in encode_faces_in_image(image_path)]


def encode_faces_in_image(
    image_path: Path,
) -> List[Tuple[Tuple[int, int, int, int], "object"]]:
    """Detect every face in the image (HOG) and compute its 128-d ResNet
    embedding in a single pass on the original pixels — avoids the
    redetect-on-tight-crop failure that hurts accuracy. Returns
    [((x, y, w, h), encoding_ndarray), ...]; empty on read failure / no faces.
    Boxes smaller than MIN_FACE_SIZE on either axis are dropped."""
    _, face_recognition, _np = _import_deps()
    try:
        img = face_recognition.load_image_file(str(image_path))
    except (OSError, ValueError):
        return []
    locations = face_recognition.face_locations(img, model="hog")
    locations = [
        loc for loc in locations
        if (loc[1] - loc[3]) >= MIN_FACE_SIZE and (loc[2] - loc[0]) >= MIN_FACE_SIZE
    ]
    if not locations:
        return []
    encodings = face_recognition.face_encodings(img, known_face_locations=locations)
    return [(_to_xywh(loc), enc) for loc, enc in zip(locations, encodings)]


def encode_crop(image_path: Path) -> Optional["object"]:
    """Return the single 128-d embedding for a tightly-cropped face image (a
    baseline ref_NN.jpg or any crop). Detects the face first; if HOG finds none
    (tight crops sometimes leave too little margin), falls back to encoding the
    whole image as the face region so every baseline still yields a vector.
    Returns the ndarray, or None on read failure."""
    _, face_recognition, _np = _import_deps()
    try:
        img = face_recognition.load_image_file(str(image_path))
    except (OSError, ValueError):
        return None
    locations = face_recognition.face_locations(img, model="hog")
    if locations:
        # Largest detected face (by area) — robust if a stray background face
        # crept into the crop padding.
        locations.sort(key=lambda l: (l[2] - l[0]) * (l[1] - l[3]), reverse=True)
        box = [locations[0]]
    else:
        h, w = img.shape[:2]
        box = [(0, w, h, 0)]  # whole-image fallback (top, right, bottom, left)
    encodings = face_recognition.face_encodings(img, known_face_locations=box)
    return encodings[0] if encodings else None


def face_distance(enc_a, enc_b) -> float:
    """Euclidean (L2) distance between two 128-d face embeddings."""
    _, _fr, np = _import_deps()
    return float(np.linalg.norm(np.asarray(enc_a) - np.asarray(enc_b)))


def crop_and_save(
    source_image: Path, bbox: Tuple[int, int, int, int],
    out_path: Path,
) -> bool:
    """Crop the bbox region from source_image with PADDING_FRAC margin,
    resize to CROP_SIZE × CROP_SIZE, save as JPEG quality JPEG_QUALITY.
    Returns True on success."""
    from PIL import Image
    try:
        with Image.open(source_image) as im:
            iw, ih = im.size
            x, y, w, h = bbox
            pad_w = int(w * PADDING_FRAC)
            pad_h = int(h * PADDING_FRAC)
            x0 = max(0, x - pad_w)
            y0 = max(0, y - pad_h)
            x1 = min(iw, x + w + pad_w)
            y1 = min(ih, y + h + pad_h)
            crop = im.crop((x0, y0, x1, y1))
            crop = crop.convert("RGB").resize(
                (CROP_SIZE, CROP_SIZE), Image.LANCZOS,
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)
            crop.save(out_path, format="JPEG", quality=JPEG_QUALITY)
        return True
    except (OSError, ValueError) as e:
        print(f"  crop failed for {source_image}: {e}", file=sys.stderr)
        return False


# ----------------------------------------------------------------------------
# index.csv tracking
# ----------------------------------------------------------------------------

INDEX_COLUMNS = [
    "crop_path", "source_image", "source_timestamp",
    "bbox_x", "bbox_y", "bbox_w", "bbox_h",
    "embed_fingerprint", "identity", "identity_source", "run_date",
]


def load_index() -> List[dict]:
    """Read the existing index.csv (if any) and return as list of dicts."""
    if not INDEX_PATH.is_file():
        return []
    with open(INDEX_PATH, newline="") as f:
        return list(csv.DictReader(f))


def save_index(rows: List[dict]) -> None:
    """Write rows back to index.csv. Sorts by crop_path for stable diffs."""
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: r.get("crop_path", ""))
    with open(INDEX_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=INDEX_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in INDEX_COLUMNS})


def _baseline_files() -> List[Tuple[Path, str]]:
    """Walk baselines/ → [(image_path, identity_slug)] sorted for stability.
    identity_slug is the immediate parent directory name."""
    out = []
    if not BASELINES_DIR.is_dir():
        return out
    for slug_dir in sorted(BASELINES_DIR.iterdir()):
        if not slug_dir.is_dir():
            continue
        for p in sorted(slug_dir.rglob("*")):
            if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png"):
                out.append((p, slug_dir.name))
    return out


def _baseline_fingerprint(files: List[Tuple[Path, str]]) -> str:
    """sha256 over the sorted (rel_path, file_sha256) list of all baseline
    images. mtime-independent — survives git checkouts where mtimes reset and
    still flips the moment any baseline is added / removed / replaced."""
    import hashlib
    h = hashlib.sha256()
    for path, _slug in sorted(files, key=lambda t: str(t[0])):
        rel = str(path.relative_to(LOG_DIR))
        h.update(rel.encode())
        h.update((compute_sha256(path) or "").encode())
    return h.hexdigest()


def build_baseline_index(force: bool = False) -> dict:
    """Return {identity_slug: ndarray (k, 128)} of cached baseline embeddings.

    Encodes every baselines/{slug}/*.jpg once and caches the result to
    BASELINE_ENCODINGS_PATH (.npz — no pickle/code-exec surface). The cache is
    keyed by a sha256 fingerprint of the baseline set; a stale or missing cache
    is rebuilt transparently. `force=True` always re-encodes."""
    _, _fr, np = _import_deps()
    files = _baseline_files()
    fingerprint = _baseline_fingerprint(files)

    if not force and BASELINE_ENCODINGS_PATH.is_file():
        try:
            cached = np.load(BASELINE_ENCODINGS_PATH, allow_pickle=False)
            if str(cached["fingerprint"]) == fingerprint:
                slugs = [str(s) for s in cached["slugs"]]
                encs = cached["encodings"]
                index: dict = {}
                for slug, enc in zip(slugs, encs):
                    index.setdefault(slug, []).append(enc)
                return {s: np.stack(v) for s, v in index.items()}
        except (OSError, ValueError, KeyError):
            pass  # corrupt / old-format cache → re-encode

    index = {}
    flat_slugs: List[str] = []
    flat_encs: List = []
    for path, slug in files:
        enc = encode_crop(path)
        if enc is None:
            print(f"  warning: no encodable face in baseline {path}", file=sys.stderr)
            continue
        index.setdefault(slug, []).append(enc)
        flat_slugs.append(slug)
        flat_encs.append(enc)
    if flat_encs:
        BASELINE_ENCODINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            BASELINE_ENCODINGS_PATH,
            encodings=np.stack(flat_encs),
            slugs=np.array(flat_slugs),
            fingerprint=np.array(fingerprint),
        )
    return {s: np.stack(v) for s, v in index.items()}


def identify(encoding, baseline_index: dict, threshold: float) -> Optional[str]:
    """Return the identity slug whose reference set is closest to `encoding`,
    if that minimum Euclidean distance is within `threshold`; else None.
    min-distance across an identity's references (not centroid) so a multi-
    angle baseline set helps rather than dilutes."""
    _, _fr, np = _import_deps()
    best, best_dist = None, threshold
    enc = np.asarray(encoding)
    for slug, refs in baseline_index.items():
        d = float(np.min(np.linalg.norm(refs - enc, axis=1)))
        if d <= best_dist:
            best_dist = d
            best = slug
    return best


# ----------------------------------------------------------------------------
# extract-frames index.md parsing
# ----------------------------------------------------------------------------

_INDEX_ROW_RE = re.compile(
    # | n | [MM:SS] | label | `path` | frames |
    r"^\|\s*\d+\s*\|\s*\[([^\]]+)\]\s*\|\s*[^|]*\|\s*`([^`]+)`\s*\|",
)


def parse_extract_frames_index(index_path: Path) -> List[Tuple[str, Path]]:
    """Read an extract-frames.py index.md and return [(timestamp, image_path)]
    pairs for each row that names an actual image path (skips em-dash "—" rows
    where no contact sheet was produced).

    Image paths in the index are relative to the index file's parent directory
    (the extract-frames output dir)."""
    if not index_path.is_file():
        sys.exit(f"error: extract-frames index not found: {index_path}")
    out = []
    base = index_path.parent
    for line in index_path.read_text(encoding="utf-8").splitlines():
        m = _INDEX_ROW_RE.match(line.strip())
        if not m:
            continue
        ts = m.group(1).strip()
        rel = m.group(2).strip()
        full = (base / rel).resolve()
        if full.is_file():
            out.append((ts, full))
    return out


# ----------------------------------------------------------------------------
# Subcommand implementations
# ----------------------------------------------------------------------------

def cmd_detect(args) -> None:
    import hashlib
    import tempfile
    _, _fr, np = _import_deps()  # fail-fast if face_recognition missing

    # Collect images to process — either from --index or --input
    if args.index:
        pairs = parse_extract_frames_index(Path(args.index).resolve())
    else:
        ip = Path(args.input).resolve()
        if ip.is_dir():
            pairs = [
                ("", p) for p in sorted(ip.rglob("*"))
                if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png")
            ]
        elif ip.is_file():
            pairs = [("", ip)]
        else:
            sys.exit(f"error: --input path not found: {ip}")

    if not pairs:
        sys.exit("error: no input images to process")

    CROPS_DIR.mkdir(parents=True, exist_ok=True)
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)

    # Baseline embedding index (cached) + a flat (encoding, slug) view for the
    # dedup/identity scans below.
    baseline_index = build_baseline_index()
    baseline_flat: List[Tuple["object", str]] = [
        (enc, slug) for slug, refs in baseline_index.items() for enc in refs
    ]

    def min_dist_to_baseline(enc) -> float:
        if not baseline_flat:
            return float("inf")
        return min(face_distance(enc, b) for b, _ in baseline_flat)

    # Pre-clean: any existing crop in crops/ within EMBED_DEDUP_DISTANCE of a
    # registered baseline is a stale near-identical leftover (e.g. a copy left
    # behind when a crop was promoted via `register`). Drop it + its index row.
    # The tight dedup threshold means only literal same-shot leftovers go —
    # distinct-angle crops of an already-registered person are KEPT, so they
    # remain available as additional baseline references.
    index_rows = load_index()
    crop_encs: List[Tuple[Path, "object"]] = []
    for p in sorted(CROPS_DIR.rglob("*")):
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png"):
            e = encode_crop(p)
            if e is not None:
                crop_encs.append((p, e))
    stale_removed = 0
    kept_crop_encs: List[Tuple[Path, "object"]] = []
    for crop_path, e in crop_encs:
        if min_dist_to_baseline(e) <= EMBED_DEDUP_DISTANCE:
            rel = str(crop_path.relative_to(LOG_DIR))
            crop_path.unlink()
            index_rows = [r for r in index_rows if r["crop_path"] != rel]
            stale_removed += 1
        else:
            kept_crop_encs.append((crop_path, e))
    crop_encs = kept_crop_encs
    if stale_removed:
        print(f"  pre-clean: removed {stale_removed} crop(s) now represented by baselines")

    # Also drop index rows whose crop_path is a crops/* entry that no longer
    # exists on disk. crops/ is gitignored working state, so contributors will
    # routinely delete or never-receive the underlying jpgs; the index must
    # not retain rows pointing at absent files.
    orphan_removed = 0
    keep_rows = []
    for row in index_rows:
        crop_rel = row.get("crop_path", "")
        if crop_rel.startswith("crops/") and not (LOG_DIR / crop_rel).is_file():
            orphan_removed += 1
            continue
        keep_rows.append(row)
    index_rows = keep_rows
    if orphan_removed:
        print(f"  pre-clean: dropped {orphan_removed} index row(s) for absent crops")

    # Dedup-set spans BOTH crops/ and baselines/ — re-detecting a face already
    # represented shouldn't churn a new crop into crops/. Each entry is
    # (encoding, identity_or_None_for_unlabeled_crops).
    dedup_set: List[Tuple["object", Optional[str]]] = []
    for _, e in crop_encs:
        dedup_set.append((e, None))
    for enc, slug in baseline_flat:
        dedup_set.append((enc, slug))

    # Working directory for unconfirmed crops — written here first, only moved
    # into CROPS_DIR after dedup passes. Prevents the
    # "overwrite-existing-then-delete" idempotency bug where re-detecting the
    # same source image would destroy the existing crop in place.
    temp_dir = Path(tempfile.mkdtemp(prefix="detect-faces-"))

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_detected = 0
    total_saved = 0
    total_dedupd = 0
    total_identified = 0
    identity_counts: dict = {}

    print(f"Processing {len(pairs)} image(s)...")
    try:
        for timestamp, image_path in pairs:
            faces = encode_faces_in_image(image_path)  # detect + embed, one pass
            if not faces:
                print(f"  {image_path.name} [{timestamp}]: 0 faces")
                continue
            per_image_id = 0
            for i, (bbox, enc) in enumerate(faces, start=1):
                total_detected += 1
                # Compose the eventual filename so we can preserve it through
                # the temp → final move.
                stem = image_path.stem
                ts_part = timestamp.replace(":", "-") if timestamp else ""
                out_name = (
                    f"{stem}_{ts_part}_face_{i:02d}.jpg"
                    if ts_part else f"{stem}_face_{i:02d}.jpg"
                )
                temp_path = temp_dir / out_name
                if not crop_and_save(image_path, bbox, temp_path):
                    continue
                # Dedup against crops/ AND baselines/. A near-identical match
                # to a baseline marks this identified; either way we skip
                # saving since the face is already represented.
                matched_identity = None
                matched_at_all = False
                for existing_enc, existing_identity in dedup_set:
                    if face_distance(enc, existing_enc) <= EMBED_DEDUP_DISTANCE:
                        matched_at_all = True
                        if existing_identity:
                            matched_identity = existing_identity
                            break
                if matched_at_all:
                    temp_path.unlink(missing_ok=True)
                    total_dedupd += 1
                    if matched_identity:
                        total_identified += 1
                        per_image_id += 1
                        identity_counts[matched_identity] = (
                            identity_counts.get(matched_identity, 0) + 1
                        )
                    continue
                # Not a near-dup — commit to CROPS_DIR. Record a best-guess
                # identity hint (embed-auto) if it matches a baseline within
                # EMBED_MATCH_DISTANCE; the contributor still confirms it
                # explicitly via `register`.
                final_path = CROPS_DIR / out_name
                final_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(temp_path), str(final_path))
                dedup_set.append((enc, None))
                total_saved += 1
                auto_slug = identify(enc, baseline_index, EMBED_MATCH_DISTANCE)
                if auto_slug:
                    per_image_id += 1
                    identity_counts[auto_slug] = identity_counts.get(auto_slug, 0) + 1
                fingerprint = hashlib.sha1(np.asarray(enc).tobytes()).hexdigest()[:16]
                row = {
                    "crop_path": str(final_path.relative_to(LOG_DIR)),
                    "source_image": str(image_path),
                    "source_timestamp": timestamp,
                    "bbox_x": bbox[0], "bbox_y": bbox[1],
                    "bbox_w": bbox[2], "bbox_h": bbox[3],
                    "embed_fingerprint": fingerprint,
                    "identity": auto_slug or "",
                    "identity_source": "embed-auto" if auto_slug else "",
                    "run_date": run_date,
                }
                # Idempotent: overwrite any prior row at the same crop_path
                # (re-runs against the same source produce stable filenames).
                index_rows = [r for r in index_rows if r["crop_path"] != row["crop_path"]]
                index_rows.append(row)
            print(
                f"  {image_path.name} [{timestamp}]: "
                f"{len(faces)} detected, "
                f"{per_image_id} identified"
            )
    finally:
        # Clean up working dir (whether or not detection raised).
        shutil.rmtree(temp_dir, ignore_errors=True)

    save_index(index_rows)

    print()
    print(f"Summary:")
    print(f"  Faces detected:   {total_detected}")
    print(f"  Saved (new):      {total_saved}")
    print(f"  Skipped (dedup):  {total_dedupd}")
    print(f"  Identified:       {total_identified}")
    if identity_counts:
        for slug, n in sorted(identity_counts.items()):
            print(f"    {slug}: {n}")
    print()
    print(f"Crops:    {CROPS_DIR}")
    print(f"Index:    {INDEX_PATH}")
    if total_saved and not args.no_review_hint:
        print()
        print(
            f"Next: review crops in {CROPS_DIR}, then for each clearly-labeled "
            f"face:\n"
            f"  ./detect-faces.py register --crop CROPS/... --identity SLUG "
            f"\\\n      --source-video PATH --source-timestamp TS "
            f"--bbox X,Y,W,H [--note STR]"
        )


def cmd_register(args) -> None:
    # No face libs needed — register just moves an existing crop into
    # baselines/ and records the manifest entry. The baseline-encoding cache
    # auto-invalidates on the next detect/spot-check (fingerprint changes).
    crop_path = Path(args.crop).resolve()
    if not crop_path.is_file():
        sys.exit(f"error: crop not found: {crop_path}")
    if not crop_path.is_relative_to(CROPS_DIR):
        sys.exit(
            f"error: crop must live under {CROPS_DIR}, got {crop_path}"
        )
    identity = args.identity.strip().lower()
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", identity):
        sys.exit(
            f"error: identity slug must be kebab-case "
            f"(lowercase letters, digits, hyphens); got {identity!r}"
        )
    try:
        bbox = [int(v) for v in args.bbox.split(",")]
        if len(bbox) != 4:
            raise ValueError("must be x,y,w,h")
    except ValueError as e:
        sys.exit(f"error: --bbox parse failure: {e}")

    target_dir = BASELINES_DIR / identity
    target_dir.mkdir(parents=True, exist_ok=True)
    # Numerically suffixed filename so multiple baselines per identity coexist
    n = 1 + len(list(target_dir.glob("ref_*.jpg")))
    target = target_dir / f"ref_{n:02d}.jpg"
    shutil.move(str(crop_path), str(target))
    sha = compute_sha256(target)

    # Append manifest entry
    entries = _load_manifest()
    entry = {
        "identity": identity,
        "path": str(target.relative_to(LOG_DIR)),
        "sha256": sha,
        "source_video_path": args.source_video,
        "source_timestamp": args.source_timestamp,
        "bbox": bbox,
        "added_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    if args.source_video_url:
        entry["source_video_url"] = args.source_video_url
    if args.note:
        entry["note"] = args.note
    entries.append(entry)
    _save_manifest(entries)

    # Update index.csv to reflect the move + identity assignment
    rel_old = str(crop_path.relative_to(LOG_DIR))
    rel_new = str(target.relative_to(LOG_DIR))
    rows = load_index()
    for r in rows:
        if r["crop_path"] == rel_old:
            r["crop_path"] = rel_new
            r["identity"] = identity
            r["identity_source"] = "manual-register"
    save_index(rows)

    print(f"Registered {target} → identity '{identity}'")
    print(f"  sha256: {sha}")
    print(f"  manifest entries: {len(entries)}")


def cmd_prune(args) -> None:
    """Remove crops in crops/ that match no baseline identity (by face
    embedding, within EMBED_MATCH_DISTANCE). Interactive confirmation unless
    --force; --dry-run for preview-only."""
    baseline_index = build_baseline_index()
    if not CROPS_DIR.is_dir():
        print("no crops/ directory; nothing to prune")
        return
    candidates = []
    for p in sorted(CROPS_DIR.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        enc = encode_crop(p)
        if enc is None:
            continue
        match = identify(enc, baseline_index, EMBED_MATCH_DISTANCE)
        if not match:
            candidates.append(p)
    if not candidates:
        print("No unidentified crops to prune.")
        return
    print(f"{len(candidates)} unidentified crop(s) candidate for removal:")
    for p in candidates:
        print(f"  {p.relative_to(LOG_DIR)}")
    if args.dry_run:
        print("\n--dry-run: no files removed.")
        return
    if not args.force:
        resp = input(f"\nRemove these {len(candidates)} crops? [y/N]: ").strip().lower()
        if resp != "y":
            print("Aborted.")
            return
    removed = 0
    rows = load_index()
    rel_paths = {str(p.relative_to(LOG_DIR)) for p in candidates}
    for p in candidates:
        p.unlink()
        removed += 1
    rows = [r for r in rows if r["crop_path"] not in rel_paths]
    save_index(rows)
    print(f"Removed {removed} crop(s).")


def cmd_encode_baselines(args) -> None:
    """(Re)build the baseline-embedding cache and report per-identity counts.
    Run after editing baselines/ to warm BASELINE_ENCODINGS_PATH; otherwise it
    is built lazily on the first detect/prune/spot-check call."""
    index = build_baseline_index(force=args.force)
    total = sum(len(v) for v in index.values())
    print(f"Baseline embeddings cached → {BASELINE_ENCODINGS_PATH}")
    print(f"  identities: {len(index)}   reference vectors: {total}")
    for slug in sorted(index):
        print(f"    {slug}: {len(index[slug])}")


# ----------------------------------------------------------------------------
# Manifest helpers
# ----------------------------------------------------------------------------

def _load_manifest() -> list:
    if not MANIFEST_PATH.is_file():
        return []
    with open(MANIFEST_PATH) as f:
        return strict_yaml_load(f) or []


def _save_manifest(entries: list) -> None:
    """Write entries back to manifest.yaml. Sorts by (identity, path) for
    stable diffs."""
    import yaml
    entries.sort(key=lambda e: (e.get("identity", ""), e.get("path", "")))
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        yaml.dump(
            entries, f, sort_keys=False, default_flow_style=False,
            allow_unicode=True, width=9999,
        )


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # detect
    p_detect = sub.add_parser(
        "detect",
        help="Detect faces in frames; save crops; report counts",
        description=cmd_detect.__doc__,
    )
    src = p_detect.add_mutually_exclusive_group(required=True)
    src.add_argument("--index", help="Path to extract-frames index.md")
    src.add_argument("--input", help="Path to image file or directory")
    p_detect.add_argument(
        "--no-review-hint", action="store_true",
        help="Suppress the post-summary contributor next-step hint",
    )

    # register
    p_reg = sub.add_parser(
        "register",
        help="Move a crop to baselines/{identity}/ and append manifest entry",
        description=cmd_register.__doc__,
    )
    p_reg.add_argument("--crop", required=True, help="Path to crop in crops/")
    p_reg.add_argument(
        "--identity", required=True,
        help="Kebab-case identity slug (lowercase letters, digits, hyphens)",
    )
    p_reg.add_argument(
        "--source-video", required=True,
        help="Path to source video (relative to repo root)",
    )
    p_reg.add_argument(
        "--source-timestamp", required=True,
        help="Timestamp within source video (MM:SS or H:MM:SS)",
    )
    p_reg.add_argument(
        "--bbox", required=True,
        help="Face bounding box in source frame as X,Y,W,H",
    )
    p_reg.add_argument(
        "--source-video-url", help="Optional source video URL (for manifest)",
    )
    p_reg.add_argument(
        "--note", help="Optional free-text note for the manifest entry",
    )

    # prune
    p_prune = sub.add_parser(
        "prune",
        help="Remove unidentified crops (no baseline match)",
        description=cmd_prune.__doc__,
    )
    p_prune.add_argument(
        "--dry-run", action="store_true", help="Preview only; remove nothing",
    )
    p_prune.add_argument(
        "--force", action="store_true",
        help="Skip the interactive confirmation prompt",
    )

    # encode-baselines
    p_enc = sub.add_parser(
        "encode-baselines",
        help="(Re)build the baseline-embedding cache and report counts",
        description=cmd_encode_baselines.__doc__,
    )
    p_enc.add_argument(
        "--force", action="store_true",
        help="Re-encode even if the cache fingerprint is current",
    )

    args = parser.parse_args()
    {
        "detect": cmd_detect,
        "register": cmd_register,
        "prune": cmd_prune,
        "encode-baselines": cmd_encode_baselines,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
