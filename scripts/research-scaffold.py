#!/usr/bin/env python3
"""
Scaffold an empty research artifact for a target node.

Produces meta/research/{slug}.yaml with:
  - required top-level keys populated with defaults
  - empty lists for each content section
  - `rumors` section present only when target_node type ∈
    {person, organization, event, location} (per schema.yaml
    research-artifact.conditional_keys)

Usage:
  research-scaffold.py --target {type}/{slug}
  research-scaffold.py --target documents/written-testimony-fravor-2023
  research-scaffold.py --target documents/written-testimony-fravor-2023 \\
      --sources government/oversight-house-gov-fravor-written-testimony-20230726.pdf
  research-scaffold.py --target ... --force    # overwrite existing artifact

The scaffolded artifact is a structurally valid empty shell. Phase I of
the build process fills it in. Contributors should run
`scripts/validate-research.py` after populating each section.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# =============================================================================
# Constants
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = REPO_ROOT / "meta" / "research"
SCHEMA_PATH = REPO_ROOT / "meta" / "schema.yaml"
MANIFEST_PATH = REPO_ROOT / "sources" / "manifest.yaml"

# Schema-driven scaffolding (BACKLOG C19). Type-set constants previously
# duplicated here (RUMORS_TYPES, TIMELINE_TYPES, ARCHETYPE_SECTION,
# KIND_SECTIONS_BY_TYPE) are now read from schema.yaml::types.research-
# artifact.conditional_keys via the same evaluate_required_when helper
# the validators use. One source of truth — schema edits propagate to
# scaffolder + validators automatically.

from checks._research_utils import evaluate_required_when

# Per-section empty-value shape lookup for schema-driven scaffolding.
# Most sections are entry lists ([]); the prose fields and event_intrinsic
# are exceptions. Default-list-via-fallback keeps the map small. Add a
# new entry only when introducing a non-list section.
EMPTY_SECTION_SHAPES = {
    # Prose fields on person artifacts
    "background": "",
    "top_relevance": "",
    "credibility_notes": "",
    # Single dict on event artifacts
    "event_intrinsic": {},
}


def empty_for(section_name):
    """Return the empty value to scaffold under ``section_name``. Default
    is `[]` (most conditional sections are entry lists); explicit
    overrides for prose fields and event_intrinsic dict."""
    return EMPTY_SECTION_SHAPES.get(section_name, [])


# All valid target-node types
VALID_TARGET_TYPES = {
    "person", "organization", "document", "event",
    "transcript", "media", "location", "finding",
}

# Map target-node type → content directory
TYPE_DIRS = {
    "person": "people",
    "organization": "organizations",
    "document": "documents",
    "event": "events",
    "transcript": "transcripts",
    "media": "media",
    "location": "locations",
    "finding": "findings",
}


# =============================================================================
# Helpers
# =============================================================================

def load_manifest():
    if not MANIFEST_PATH.exists():
        return []
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f) or []


def parse_target(target):
    """target = 'type/slug' (no .md). Returns (type, slug, content_dir_name)."""
    if "/" not in target:
        sys.exit(f"ERROR: --target must be 'type/slug' form (got {target!r})")
    parts = target.split("/", 1)
    type_part, slug = parts[0], parts[1]
    # Map plural content dir back to singular type (people → person, etc.)
    reverse_map = {v: k for k, v in TYPE_DIRS.items()}
    if type_part in reverse_map:
        node_type = reverse_map[type_part]
    elif type_part in VALID_TARGET_TYPES:
        node_type = type_part
    else:
        sys.exit(f"ERROR: unknown target type {type_part!r}. "
                 f"Valid: {sorted(VALID_TARGET_TYPES)}")
    return node_type, slug, TYPE_DIRS[node_type]


def target_node_file(node_type, slug):
    """Return the path to the target node's .md file."""
    return REPO_ROOT / TYPE_DIRS[node_type] / f"{slug}.md"


def build_primary_sources_list(source_paths, manifest):
    """For each provided source path, create a primary_sources entry.
    Validates each path appears in the manifest."""
    manifest_paths = {e.get("path") for e in manifest if e.get("path")}
    entries = []
    for path in source_paths:
        if path not in manifest_paths:
            print(f"WARNING: {path!r} not found in sources/manifest.yaml — "
                  f"scaffolder will still include it, but validate-research.py "
                  f"will error until the source is registered.",
                  file=sys.stderr)
        # Minimum shape — contributor fills in optional fields (extracted_text_path,
        # pdf_metadata) during Phase I
        entry = {
            "path": path,
            "format": infer_format(path),
        }
        entries.append(entry)
    return entries


def infer_format(path):
    """Map a source file path's extension to a manifest.yaml format value.
    Covers the schema's format_values vocabulary (pdf / html / txt /
    transcript / audio / image / video). Unknown extensions fall back to
    html — intentional for web scraping where the source's extension is
    often absent or generic. Mirrors manifest.py FORMAT_BY_EXT."""
    ext = Path(path).suffix.lower()
    return {
        ".pdf": "pdf",
        ".html": "html",
        ".htm": "html",
        ".txt": "txt",
        ".md": "transcript",
        # Video extensions — schema format_values supports `video`.
        ".mp4": "video",
        ".m4v": "video",
        ".mov": "video",
        ".webm": "video",
        ".avi": "video",
        ".mkv": "video",
        # Audio extensions — schema format_values supports `audio`.
        ".mp3": "audio",
        ".wav": "audio",
        ".flac": "audio",
        ".aac": "audio",
        ".ogg": "audio",
        ".m4a": "audio",
        # Image extensions — schema format_values supports `image`.
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".gif": "image",
        ".tiff": "image",
        ".tif": "image",
        ".webp": "image",
        ".bmp": "image",
        ".heic": "image",
    }.get(ext, "html")


def _read_target_frontmatter(node_type, slug):
    """Read the target node's frontmatter and return it as a dict (or
    empty dict on failure). Shared helper used for archetype (person)
    and kind (event) reads."""
    path = target_node_file(node_type, slug)
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}


def read_target_archetype(node_type, slug):
    """For person target-nodes, read the node's frontmatter to get its
    archetype. Returns None for non-person nodes or if unreadable. Used
    by build_scaffold to add the archetype-specific artifact section.
    """
    if node_type != "person":
        return None
    return _read_target_frontmatter(node_type, slug).get("archetype")


def read_target_kind(node_type, slug):
    """For kind-bearing target nodes, read the node's frontmatter to
    get its kind. Returns None otherwise or if unreadable.
      event        → hearing | encounter
      transcript   → hearing | other
      organization → gov | gov-contractor | private
    """
    if node_type not in ("event", "transcript", "organization"):
        return None
    return _read_target_frontmatter(node_type, slug).get("kind")


def _load_schema_conditional_keys():
    """Read schema.yaml and return the research-artifact conditional_keys
    dict, or {} on read/parse failure (defensive — scaffolder shouldn't
    crash on schema issues; validator catches them)."""
    try:
        with open(SCHEMA_PATH) as f:
            schema = yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        return {}
    return (
        (schema or {}).get("types", {})
                      .get("research-artifact", {})
                      .get("conditional_keys", {})
    )


def build_scaffold(node_type, slug, source_paths, manifest):
    """Assemble the research-artifact YAML dict for the given target.

    Universal top-level keys are populated unconditionally. Type /
    archetype / kind-conditional sections are dispatched schema-driven
    from ``schema.yaml::conditional_keys`` via ``evaluate_required_when``
    — same logic the validators use, single source of truth.
    """
    today = date.today().isoformat()
    artifact = {
        "id": f"meta/research/{slug}",
        "type": "research-artifact",
        "schema_version": 1,
        "target_node": f"{TYPE_DIRS[node_type]}/{slug}",
        "status": "active",
        "created": today,
        "description": "",
        "primary_sources": build_primary_sources_list(source_paths, manifest),
        "document_intrinsic": {},
        "context_extrinsic": {},
        "quotes": [],
        "entities_referenced": [],
        "naming_quirks": [],
    }

    # Schema-driven scaffolding for type / archetype / kind-conditional
    # sections. Reads conditional_keys once; walks each declared
    # section; adds an empty value of the right shape when the rules
    # match this target.
    archetype = read_target_archetype(node_type, slug)
    kind = read_target_kind(node_type, slug)
    conditional_keys = _load_schema_conditional_keys()
    for section_name, rules in conditional_keys.items():
        if evaluate_required_when(rules, node_type, archetype, kind):
            artifact[section_name] = empty_for(section_name)

    return artifact


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--target", required=True,
                        help="Target node: type/slug (e.g., documents/written-testimony-fravor-2023)")
    parser.add_argument("--sources", default="",
                        help="Comma-separated list of primary-source paths relative to sources/ "
                             "(e.g., government/file.pdf,video/gimbal.mp4). Optional — can be "
                             "added during Phase I.")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing research artifact")
    args = parser.parse_args()

    node_type, slug, _ = parse_target(args.target)

    # Target node must exist
    target_file = target_node_file(node_type, slug)
    if not target_file.exists():
        sys.exit(f"ERROR: target node not found: {target_file.relative_to(REPO_ROOT)}\n"
                 f"  Scaffold the target node first via `scripts/new.py`, then its research artifact.")

    # Compute output path
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESEARCH_DIR / f"{slug}.yaml"
    if out_path.exists() and not args.force:
        sys.exit(f"ERROR: {out_path.relative_to(REPO_ROOT)} exists. "
                 f"Use --force to overwrite.")

    # Parse sources
    source_paths = [s.strip() for s in args.sources.split(",") if s.strip()]
    manifest = load_manifest()

    # Build scaffold
    artifact = build_scaffold(node_type, slug, source_paths, manifest)

    # Write YAML — preserve key order via default_flow_style=False + sort_keys=False
    with open(out_path, "w") as f:
        yaml.dump(artifact, f, sort_keys=False, default_flow_style=False,
                  allow_unicode=True, width=9999)

    rel = out_path.relative_to(REPO_ROOT)
    print(f"✓ Created {rel}")
    print()
    print("Next steps (Phase I):")
    print(f"  1. Extract primary sources to plaintext:")
    if source_paths:
        print(f"     python3 scripts/extract-source.py --artifact {rel}")
        print(f"     (writes /tmp/scratch-{slug}-N.txt — one per primary source)")
    else:
        print(f"     (add sources to primary_sources in {rel}, or re-scaffold with --sources)")
    print(f"  2. Fill in document_intrinsic and context_extrinsic from the extracted text")
    print(f"  3. Write `description` (1-3 paragraphs) — renders as the node's Description section")
    print(f"  4. Populate quotes (verbatim passages with location refs)")
    print(f"  5. Populate entities_referenced, naming_quirks")
    if "rumors" in artifact:
        print(f"  6. Populate rumors (widely-reported claims lacking primary-source backing)")
    print(f"  7. Validate: python3 scripts/validate-research.py {rel}")


if __name__ == "__main__":
    main()
