#!/usr/bin/env python3
"""detect-faces.py — face detection, crop logging, and identity-baseline tracking
for frames extracted by scripts/tools/extract-frames.py.

Multi-speaker video sources (panel discussions, interviews, documentaries) need
visual speaker identification to disambiguate whisper / YouTube auto-caption
transcripts that don't preserve speaker identity. extract-frames.py produces
still frames at contested timestamps; this tool runs face detection on those
frames, saves each detected face as its own crop, and tracks a persistent log
of who-is-who via contributor-curated baseline directories.

Three subcommands:

  detect    Process a directory of images (or an extract-frames index.md) and
            save face crops to sources/photo-identity-log/crops/. Reports the
            per-image and total counts of faces detected vs. faces identified
            (matched by perceptual hash against an existing baseline).

  register  Move a labeled crop from crops/ into baselines/{identity}/,
            compute its sha256, and append a manifest entry under
            sources/photo-identity-log/manifest.yaml. The crop becomes a
            persistent identity reference for future detect runs.

  prune     Remove crops in crops/ whose perceptual hash matches no baseline —
            i.e., unlabeled crops the contributor has decided not to keep.
            Default is interactive (prompts before deletion); --dry-run for
            preview; --force to skip the prompt.

Storage discipline:

  1. Perceptual-hash dedup at save time. Pillow's ``ImageHash``-equivalent
     8x8 DCT grayscale hash. New crops with a near-identical pHash to anything
     already in crops/ or baselines/ are skipped — no duplicate accumulation.
  2. Crops are 256×256 px, JPEG quality 85 (~8-15 KB average).
  3. detect-mode operates on contact sheets by default (one image per
     timestamp); cuts crop volume 5x vs. processing all individual burst
     frames.

The log is tracked in git. baselines/ + manifest.yaml are the persistent
identity reference set; crops/ is the working area for unidentified faces
awaiting contributor review.

Requires python3-opencv and opencv-data (Haar cascade XMLs). Run
scripts/tools/setup-photo-identity.sh once to install. See
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

import argparse
import csv
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

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

CROP_SIZE = 256        # px, square
JPEG_QUALITY = 85
MIN_FACE_SIZE = 80     # px, minimum face size to detect — filters tiny background faces
PADDING_FRAC = 0.30    # bbox padding (fraction of face dimension) added before crop

# pHash: Hamming distance threshold for "near-identical" duplicate detection.
# 8x8 DCT hash → 64-bit fingerprint; distance ≤ 5 reliably catches near-dupes
# of the same face at the same crop quality without merging visually-distinct
# crops of the same person at different poses (which Tier 2 embedding-match
# would catch but Tier 1 pHash should not).
PHASH_DUP_DISTANCE = 5

# Haar cascade XML — try cv2.data first (pip-installed opencv-python),
# then Debian / Ubuntu / Kali standard paths via opencv-data package.
CASCADE_CANDIDATES = [
    "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
    "/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml",
    "/usr/share/OpenCV/haarcascades/haarcascade_frontalface_default.xml",
]


# ----------------------------------------------------------------------------
# Dependency import (deferred so --help works without cv2 installed)
# ----------------------------------------------------------------------------

def _import_deps():
    """Import cv2 + PIL with a contributor-friendly error if missing. Returns
    (cv2, Image)."""
    try:
        import cv2
    except ImportError:
        sys.exit(
            "error: python3-opencv not installed. Run "
            "scripts/tools/setup-photo-identity.sh to install."
        )
    try:
        from PIL import Image
    except ImportError:
        sys.exit(
            "error: Pillow not installed (python3-pil)."
        )
    return cv2, Image


def _locate_cascade():
    """Return the path to haarcascade_frontalface_default.xml or exit with a
    contributor-friendly error. Probes cv2.data first (pip wheels), then the
    Debian / Ubuntu / Kali opencv-data package's standard install paths."""
    import cv2
    if hasattr(cv2, "data"):
        try:
            cv2_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
            if cv2_path.is_file():
                return str(cv2_path)
        except Exception:
            pass
    for candidate in CASCADE_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    sys.exit(
        "error: haarcascade_frontalface_default.xml not found.\n"
        "  Probed cv2.data.haarcascades and:\n    "
        + "\n    ".join(CASCADE_CANDIDATES)
        + "\n  Install opencv-data via scripts/tools/setup-photo-identity.sh."
    )


# ----------------------------------------------------------------------------
# Perceptual hash (8x8 DCT grayscale, Pillow only — no imagehash dependency)
# ----------------------------------------------------------------------------

def perceptual_hash(image_path: Path) -> Optional[int]:
    """Compute an 8x8 grayscale-mean perceptual hash for an image. Returns
    a 64-bit integer fingerprint, or None on read failure.

    Algorithm: resize to 8x8 grayscale via Pillow, compute mean pixel
    intensity, bit-encode each pixel as 1 if above mean else 0. Lightweight
    and adequate for "near-identical crop" dedup; not robust to large pose
    changes (Tier 2 face_recognition embeddings handle that)."""
    from PIL import Image
    try:
        with Image.open(image_path) as im:
            im = im.convert("L").resize((8, 8), Image.LANCZOS)
            pixels = list(im.getdata())
    except (OSError, ValueError):
        return None
    mean = sum(pixels) / 64
    bits = 0
    for p in pixels:
        bits = (bits << 1) | (1 if p > mean else 0)
    return bits


def hamming_distance(a: int, b: int) -> int:
    """Bit-distance between two 64-bit perceptual hashes."""
    return bin(a ^ b).count("1")


def collect_existing_hashes(dirs: Iterable[Path]) -> List[Tuple[Path, int]]:
    """Walk one or more directories and return (path, phash) for every
    .jpg / .jpeg / .png. Skips files whose pHash compute fails."""
    out = []
    for d in dirs:
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if not p.is_file():
                continue
            if p.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            h = perceptual_hash(p)
            if h is not None:
                out.append((p, h))
    return out


# ----------------------------------------------------------------------------
# Face detection + crop save
# ----------------------------------------------------------------------------

def detect_faces_in_image(image_path: Path) -> List[Tuple[int, int, int, int]]:
    """Return a list of (x, y, w, h) bounding boxes for faces in the image,
    detected via Haar cascade. Empty list on read failure or no faces.

    Filtering: drops detections smaller than MIN_FACE_SIZE on either axis.
    The cascade's own minNeighbors=5 + scaleFactor=1.1 is the standard
    "favor precision over recall" setting; tunable later if false positives
    or misses surface during use."""
    import cv2
    img = cv2.imread(str(image_path))
    if img is None:
        return []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    cascade = cv2.CascadeClassifier(_locate_cascade())
    faces = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5,
        minSize=(MIN_FACE_SIZE, MIN_FACE_SIZE),
    )
    return [tuple(int(v) for v in f) for f in faces]


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
    "phash", "identity", "identity_source", "run_date",
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


def baseline_phashes() -> List[Tuple[Path, int, str]]:
    """Walk baselines/ and return (path, phash, identity_slug) for every
    baseline crop. identity_slug is the immediate parent directory name."""
    out = []
    if not BASELINES_DIR.is_dir():
        return out
    for slug_dir in sorted(BASELINES_DIR.iterdir()):
        if not slug_dir.is_dir():
            continue
        identity = slug_dir.name
        for p in sorted(slug_dir.rglob("*")):
            if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png"):
                h = perceptual_hash(p)
                if h is not None:
                    out.append((p, h, identity))
    return out


def identify_against_baselines(
    crop_phash: int, baseline_hashes: List[Tuple[Path, int, str]],
) -> Optional[str]:
    """Return the identity slug of the closest-matching baseline if its
    Hamming distance is within PHASH_DUP_DISTANCE, else None."""
    best = None
    best_dist = PHASH_DUP_DISTANCE + 1
    for _, h, identity in baseline_hashes:
        d = hamming_distance(crop_phash, h)
        if d < best_dist:
            best_dist = d
            best = identity
    return best if best_dist <= PHASH_DUP_DISTANCE else None


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
    cv2, _ = _import_deps()
    _locate_cascade()  # fail-fast if cascade missing

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

    # Pre-clean: any existing crop in crops/ that pHash-matches a registered
    # baseline is stale — the baseline already represents that face. Drop the
    # crop + its index row. This handles the case where a crop was registered
    # as a baseline (via the `register` subcommand) but a copy was left behind
    # in crops/ (e.g., from a re-detect that ran before the register).
    baseline_hashes = baseline_phashes()
    index_rows = load_index()
    crop_hashes = collect_existing_hashes([CROPS_DIR])
    stale_removed = 0
    for crop_path, crop_h in crop_hashes:
        if identify_against_baselines(crop_h, baseline_hashes):
            rel = str(crop_path.relative_to(LOG_DIR))
            crop_path.unlink()
            index_rows = [r for r in index_rows if r["crop_path"] != rel]
            stale_removed += 1
    if stale_removed:
        print(f"  pre-clean: removed {stale_removed} crop(s) now represented by baselines")
        crop_hashes = collect_existing_hashes([CROPS_DIR])

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

    # Dedup-set spans BOTH crops/ and baselines/ — re-detecting a face that
    # already has a baseline entry shouldn't churn a new crop into crops/.
    # Each entry is (phash, identity_or_None_for_unlabeled_crops).
    dedup_set: List[Tuple[int, Optional[str]]] = []
    for _, h in crop_hashes:
        dedup_set.append((h, None))
    for _, h, identity in baseline_hashes:
        dedup_set.append((h, identity))

    # Working directory for unconfirmed crops — written here first, only moved
    # into CROPS_DIR after pHash dedup passes. Prevents the
    # "overwrite-existing-then-delete" idempotency bug where re-detecting the
    # same source image would destroy the existing crop in place.
    import tempfile
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
            boxes = detect_faces_in_image(image_path)
            if not boxes:
                print(f"  {image_path.name} [{timestamp}]: 0 faces")
                continue
            per_image_id = 0
            for i, bbox in enumerate(boxes, start=1):
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
                h = perceptual_hash(temp_path)
                if h is None:
                    temp_path.unlink(missing_ok=True)
                    continue
                # Check dedup against crops/ AND baselines/. A match against
                # a baseline marks this as identified; either way we skip
                # saving since the face is already represented.
                matched_identity = None
                matched_at_all = False
                for existing_h, existing_identity in dedup_set:
                    if hamming_distance(h, existing_h) <= PHASH_DUP_DISTANCE:
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
                # No dedup match — commit the temp file to CROPS_DIR.
                final_path = CROPS_DIR / out_name
                final_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(temp_path), str(final_path))
                dedup_set.append((h, None))
                total_saved += 1
                # New crop — not currently identified (no baseline match).
                row = {
                    "crop_path": str(final_path.relative_to(LOG_DIR)),
                    "source_image": str(image_path),
                    "source_timestamp": timestamp,
                    "bbox_x": bbox[0], "bbox_y": bbox[1],
                    "bbox_w": bbox[2], "bbox_h": bbox[3],
                    "phash": f"{h:016x}",
                    "identity": "",
                    "identity_source": "",
                    "run_date": run_date,
                }
                # Idempotent: overwrite any prior row at the same crop_path
                # (re-runs against the same source produce stable filenames).
                index_rows = [r for r in index_rows if r["crop_path"] != row["crop_path"]]
                index_rows.append(row)
            print(
                f"  {image_path.name} [{timestamp}]: "
                f"{len(boxes)} detected, "
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
    cv2, _ = _import_deps()
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
    """Remove crops in crops/ that have no matching baseline (by pHash).
    Interactive confirmation unless --force; --dry-run for preview-only."""
    baseline_hashes = baseline_phashes()
    if not CROPS_DIR.is_dir():
        print("no crops/ directory; nothing to prune")
        return
    candidates = []
    for p in sorted(CROPS_DIR.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        h = perceptual_hash(p)
        if h is None:
            continue
        match = identify_against_baselines(h, baseline_hashes)
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

    args = parser.parse_args()
    {"detect": cmd_detect, "register": cmd_register, "prune": cmd_prune}[args.cmd](args)


if __name__ == "__main__":
    main()
