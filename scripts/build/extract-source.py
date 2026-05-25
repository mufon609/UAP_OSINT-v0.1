#!/usr/bin/env python3
"""
Extract primary-source files to plaintext for Phase I research work.

Wraps `pdftotext` for PDFs (with `pdfinfo` metadata capture) and direct
read for HTML/TXT. Writes extracted text to deterministic scratch paths
so Phase I contributors can reference extracted content by predictable
locations. PDF scratch carries `--- page N ---` markers at the form-feed
page boundaries (physical pages) so a contributor authors the matching
`p. N` quote location directly — the index matches the quote_location_page
gate that verifies it.

Two modes:

  Batch mode — extract every primary source in a research artifact:
    extract-source.py --artifact meta/research/{slug}.yaml

  Single-source mode — extract one source file:
    extract-source.py --source government/file.pdf

Output paths (deterministic):
    /tmp/scratch-{artifact_slug}-{source_index}.txt     (batch mode)
    /tmp/scratch-{source_basename}.txt                  (single mode)

Batch mode also prints PDF metadata for each source (useful for
populating document_intrinsic in the research artifact).

Does NOT modify the research artifact. The contributor reads the scratch
file, extracts verbatim passages, and populates the artifact (the `/build`
worker role, or manually).
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

# scripts/build/extract-source.py — put the scripts/ parent on sys.path
# so `from lib._common` resolves from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Use the shared extraction layer so contributor scratch files match
# what the verbatim-quote / prose-drift / description-drift checks see
# byte-for-byte. The lib helper handles PDF (with .txt-sibling fallback
# for ocr-scan / extraction-lossy sources), HTML (with tag strip + entity
# decode), and TXT / MD / JSON. ``extract_pdf_metadata`` below stays
# local because pdfinfo metadata capture has no lib equivalent.
from lib._common import (  # noqa: E402
    BINARY_FORMATS,
    REPO_ROOT,
    SOURCES_DIR,
    extract_source_text,
    normalize_source_rel_path,
    strict_yaml_load,
)

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


def mark_pages(text):
    """Insert visible ``--- page N ---`` markers at the form-feed page
    separators so a contributor reads the physical page number directly off
    the scratch — and authors the matching ``p. N`` location without counting.

    The page index here is the same one the ``quote_location_page`` gate uses
    (both split the extract on form feeds, dropping a trailing empty block), so
    a ``p. N`` authored against a marker verifies at commit. Per-page content is
    byte-identical to what the verbatim / prose-drift checks see — the markers
    sit only at page boundaries, exactly where a quote must not span (a
    page-spanning passage splits into two ≤1-page quotes per
    ``meta/conventions.md``), so a within-page quote copied from the scratch
    still matches. Returns the text unchanged when it carries no form feeds
    (HTML / TXT / single-page PDFs / ``.txt`` siblings)."""
    if "\f" not in text:
        return text
    pages = text.split("\f")
    while len(pages) > 1 and pages[-1].strip() == "":
        pages.pop()
    return "".join(f"--- page {n} ---\n{pg}" for n, pg in enumerate(pages, 1))


# =============================================================================
# Modes
# =============================================================================

def do_single(source_rel_path):
    """Extract one source; write to /tmp/scratch-{basename}.txt.

    Accepts the path either relative to sources/ (e.g.
    ``news/foo.html``) or as a repo path (``sources/news/foo.html``).
    Both forms resolve to the same file under SOURCES_DIR — the shared
    ``normalize_source_rel_path`` helper handles the conversion."""
    source_rel_path = normalize_source_rel_path(source_rel_path)
    full = SOURCES_DIR / source_rel_path
    if not full.exists():
        sys.exit(f"ERROR: source file not found: sources/{source_rel_path}")

    text, meta = extract(full)
    if text is None:
        sys.exit(f"ERROR: failed to extract text from sources/{source_rel_path} "
                 f"(format may be unsupported, or pdftotext is not installed)")

    basename = full.stem
    out_path = SCRATCH_DIR / f"scratch-{basename}.txt"
    text = mark_pages(text)
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
            data = strict_yaml_load(f) or {}
    except yaml.YAMLError as e:
        sys.exit(f"ERROR: could not parse {artifact_path}: {e}")

    sources = data.get("primary_sources", []) or []
    if not sources:
        print(f"No primary_sources listed in {artifact_path.name}. Nothing to extract.")
        print(f"(Add sources to primary_sources, or re-run research-scaffold.py with --sources.)")
        return

    slug = artifact_path.stem
    print(f"Extracting {len(sources)} source(s) for meta/research/{slug}.yaml:\n")

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
        text = mark_pages(text)
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
    extracted = len(sources) - skipped
    if skipped:
        print(f"✓ {extracted} source(s) extracted; "
              f"{skipped} source(s) skipped (binary).")
    else:
        print(f"✓ All {len(sources)} sources extracted.")
    print()
    print("Next — populate the research artifact (the /build pipeline):")
    print(f"  - Review each /tmp/scratch-{slug}-N.txt")
    print(f"  - Populate document_intrinsic / context_extrinsic in {artifact_path.relative_to(REPO_ROOT)}")
    print(f"  - Populate quotes, naming_quirks")
    print(f"  - Validate: python3 scripts/build/validate-research.py {artifact_path.relative_to(REPO_ROOT)}")


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
