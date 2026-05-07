#!/usr/bin/env python3
"""
Extract primary-source files to plaintext for Phase I research work.

Wraps `pdftotext` for PDFs (with `pdfinfo` metadata capture) and direct
read for HTML/TXT. Writes extracted text to deterministic scratch paths
so Phase I contributors can reference extracted content by predictable
locations.

Two modes:

  Batch mode — extract every primary source in a research artifact:
    extract-source.py --artifact meta/research/{slug}.yaml

  Single-source mode — extract one source file:
    extract-source.py --source government/file.pdf

Output paths (deterministic):
    /tmp/scratch-{artifact_slug}-{source_index}.txt  (batch mode)
    /tmp/scratch-{source_basename}.txt               (single mode)

Batch mode also prints PDF metadata for each source (useful for
populating document_intrinsic in the research artifact).

Does NOT modify the research artifact. Phase I contributor reads the
scratch file, extracts verbatim passages, and populates the artifact
manually (or via bounded agent tasks per prompts/build.md).
"""

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# Use the shared extraction layer so contributor scratch files match
# what the verbatim-quote / prose-drift / description-drift checks see
# byte-for-byte. The lib helper handles PDF (with .txt-sibling fallback
# for ocr-scan / extraction-lossy sources), HTML (with tag strip + entity
# decode), and TXT / MD / JSON. ``extract_pdf_metadata`` below stays
# local because pdfinfo metadata capture has no lib equivalent.
from lib._common import REPO_ROOT, SOURCES_DIR, extract_source_text  # noqa: E402

SCRATCH_DIR = Path("/tmp")


# =============================================================================
# Extraction
# =============================================================================

def extract_pdf_metadata(source_file):
    """Run pdfinfo; return dict of selected metadata fields, or {} on failure."""
    try:
        proc = subprocess.run(
            ["pdfinfo", str(source_file)],
            capture_output=True, text=True, timeout=15,
        )
        if proc.returncode != 0:
            return {}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}
    meta = {}
    for line in proc.stdout.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if key in ("Title", "Author", "Subject", "CreationDate", "ModDate", "Pages",
                   "Producer", "Creator"):
            meta[key] = val
    return meta


def extract(source_file):
    """Dispatch by extension. Returns (text, metadata) tuple.

    Text extraction delegates to ``lib._common.extract_source_text`` so
    Phase I scratch files reflect what the validator sees (including
    ``.txt`` sibling preference for ocr-scan / extraction-lossy PDFs).
    Metadata is captured only for PDFs via ``extract_pdf_metadata``;
    ``{}`` for other formats."""
    text = extract_source_text(source_file)
    if source_file.suffix.lower() == ".pdf" and text is not None:
        meta = extract_pdf_metadata(source_file)
    else:
        meta = {}
    return text, meta


# =============================================================================
# Modes
# =============================================================================

def do_single(source_rel_path):
    """Extract one source; write to /tmp/scratch-{basename}.txt."""
    full = SOURCES_DIR / source_rel_path
    if not full.exists():
        sys.exit(f"ERROR: source file not found: sources/{source_rel_path}")

    text, meta = extract(full)
    if text is None:
        sys.exit(f"ERROR: failed to extract text from sources/{source_rel_path} "
                 f"(format may be unsupported, or pdftotext is not installed)")

    basename = full.stem
    out_path = SCRATCH_DIR / f"scratch-{basename}.txt"
    out_path.write_text(text)

    line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
    print(f"✓ Extracted sources/{source_rel_path}")
    print(f"  → {out_path} ({line_count} lines)")
    if meta:
        print(f"  PDF metadata:")
        for k, v in meta.items():
            print(f"    {k}: {v}")


def do_batch(artifact_path):
    """Read a research artifact; extract every primary_sources[].path."""
    if not artifact_path.exists():
        sys.exit(f"ERROR: artifact not found: {artifact_path}")

    try:
        with open(artifact_path) as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        sys.exit(f"ERROR: could not parse {artifact_path}: {e}")

    sources = data.get("primary_sources", []) or []
    if not sources:
        print(f"No primary_sources listed in {artifact_path.name}. Nothing to extract.")
        print(f"(Add sources to primary_sources, or re-run research-scaffold.py with --sources.)")
        return

    slug = artifact_path.stem
    print(f"Extracting {len(sources)} source(s) for meta/research/{slug}.yaml:\n")

    # Binary primary-source formats — extraction is correctly skipped
    # (no text to pull). Mirrors the validator's silent-skip behavior in
    # the verbatim-quote check; the CLI message distinguishes "skipped
    # by design" from "extraction failed unexpectedly".
    BINARY_FORMATS = {"video", "audio", "image"}

    failures = 0
    skipped = 0
    for i, src in enumerate(sources):
        rel = src.get("path") if isinstance(src, dict) else None
        fmt = src.get("format", "") if isinstance(src, dict) else ""
        if not rel:
            print(f"  [{i}] SKIP — source entry has no 'path' field")
            failures += 1
            continue

        full = SOURCES_DIR / rel
        if not full.exists():
            print(f"  [{i}] MISSING — sources/{rel} not on disk")
            failures += 1
            continue

        if fmt in BINARY_FORMATS:
            print(f"  [{i}] skipped (binary format: {fmt}) sources/{rel}")
            skipped += 1
            continue

        text, meta = extract(full)
        if text is None:
            print(f"  [{i}] FAILED to extract sources/{rel}")
            failures += 1
            continue

        out_path = SCRATCH_DIR / f"scratch-{slug}-{i}.txt"
        out_path.write_text(text)
        line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
        print(f"  [{i}] ✓ sources/{rel}")
        print(f"       → {out_path} ({line_count} lines)")
        if meta:
            for k, v in meta.items():
                print(f"       {k}: {v}")

    print()
    if failures:
        msg = f"⚠  {failures} source(s) failed to extract"
        if skipped:
            msg += f"; {skipped} source(s) skipped (binary)"
        print(msg)
        sys.exit(1)
    if skipped:
        print(f"✓ {len(sources) - skipped} source(s) extracted; "
              f"{skipped} source(s) skipped (binary).")
        print()
        print("Next (Phase I steps, per prompts/build.md):")
        print(f"  - Review each /tmp/scratch-{slug}-N.txt")
        return
    print(f"✓ All {len(sources)} sources extracted.")
    print()
    print("Next (Phase I steps, per prompts/build.md):")
    print(f"  - Review each /tmp/scratch-{slug}-N.txt")
    print(f"  - Populate document_intrinsic / context_extrinsic in {artifact_path.relative_to(REPO_ROOT)}")
    print(f"  - Populate quotes, entities_referenced, naming_quirks")
    print(f"  - Validate: python3 scripts/validate-research.py {artifact_path.relative_to(REPO_ROOT)}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--artifact", metavar="PATH",
                       help="Research artifact path — extract all its primary_sources")
    group.add_argument("--source", metavar="PATH",
                       help="Single source path relative to sources/")
    args = parser.parse_args()

    if args.artifact:
        do_batch(Path(args.artifact).resolve())
    else:
        do_single(args.source)


if __name__ == "__main__":
    main()
