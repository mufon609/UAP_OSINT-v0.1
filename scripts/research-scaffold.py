#!/usr/bin/env python3
"""
Scaffold an empty research artifact for a target node.

Produces research/{slug}.yaml with:
  - required top-level keys populated with defaults
  - empty lists for each content section
  - initial iteration entry (i0) logged
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
RESEARCH_DIR = REPO_ROOT / "research"
MANIFEST_PATH = REPO_ROOT / "sources" / "manifest.yaml"

# Target-node types that carry a `rumors` section on their research artifact
RUMORS_TYPES = {"person", "organization", "event", "location"}
TIMELINE_TYPES = {"person", "organization", "event", "finding"}

# person archetype → archetype-specific artifact section
ARCHETYPE_SECTION = {
    "eyewitness":           "corroboration_items",
    "whistleblower":        "vouching_chain",
    "institutional-actor":  "program_involvement",
    "reporter":             "publication_record",
}

# Per-node-type kind → kind-specific artifact section. Outer dict keyed
# by node_type so event and transcript share a kind label ("hearing")
# without clobbering each other. Transcript.other has no kind-specific
# section (absent entry rather than mapping to a no-op value).
KIND_SECTIONS_BY_TYPE = {
    "event": {
        "hearing":   "witnesses_testimony",
        "encounter": "corroboration_items",
    },
    "organization": {
        "gov-contractor": "contracts",
    },
}

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
    transcript / video). Unknown extensions fall back to html —
    intentional for web scraping where the source's extension is often
    absent or generic. Contributors archiving audio or image files must
    pass --format manually to override (schema format_values doesn't
    include audio/image yet; tracked in BACKLOG)."""
    ext = Path(path).suffix.lower()
    return {
        ".pdf": "pdf",
        ".html": "html",
        ".htm": "html",
        ".txt": "txt",
        ".md": "transcript",
        # Video extensions — schema format_values supports `video`.
        # Mirrors manifest.py FORMAT_BY_EXT.
        ".mp4": "video",
        ".m4v": "video",
        ".mov": "video",
        ".webm": "video",
        ".avi": "video",
        ".mkv": "video",
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


def build_scaffold(node_type, slug, source_paths, manifest):
    """Assemble the research-artifact YAML dict for the given target."""
    today = date.today().isoformat()
    artifact = {
        "id": f"research/{slug}",
        "type": "research-artifact",
        "schema_version": 1,
        "target_node": f"{TYPE_DIRS[node_type]}/{slug}",
        "status": "active",
        "created": today,
        "last_iteration": "i0",
        "description": "",
        "primary_sources": build_primary_sources_list(source_paths, manifest),
        "document_intrinsic": {},
        "context_extrinsic": {},
        "quotes": [],
        "claims": [],
        "entities_referenced": [],
        "naming_quirks": [],
        "research_gaps": [],
        "iterations": [
            {
                "id": "i0",
                "date": today,
                "trigger": "initial-build",
                "summary": "Scaffolded empty research artifact — to be populated during Phase I",
                "entries_added": [],
                "entries_modified": [],
            }
        ],
    }
    # Type-conditional `rumors` section
    if node_type in RUMORS_TYPES:
        artifact["rumors"] = []
    # Type-conditional `timeline` section — person / organization / event /
    # finding artifacts carry an aggregated chronological dated-facts list.
    if node_type in TIMELINE_TYPES:
        artifact["timeline"] = []
    # Person-specific biographical sections — required by the renderer.
    # Empty placeholders render as TODO stubs on the generated node body;
    # contributors populate during Phase I investigation.
    if node_type == "person":
        artifact["background"] = ""
        artifact["uap_relevance"] = ""
        artifact["affiliations"] = []
        artifact["relationships"] = []
        artifact["credibility_notes"] = ""
    # Event-specific universal sections. event_intrinsic carries
    # kind-conditional metadata (hearing_title / committee / date for
    # hearings; location_path / date / duration / weather for
    # encounters). participants is the structured participant list.
    if node_type == "event":
        artifact["event_intrinsic"] = {}
        artifact["participants"] = []
    # Transcript-specific universal sections. `speakers` required on
    # every transcript artifact regardless of kind (cross-reference
    # surface).
    if node_type == "transcript":
        artifact["speakers"] = []
    # Media-specific universal section. `media_versioning` required on
    # every media artifact regardless of kind (photo / video / audio /
    # imagery-other). Empty list when the media is canonical / original;
    # populated when the node's frontmatter has derivation_of set and
    # the derivative differs from its parent across one or more aspects
    # (duration / encoding / metadata / content / provenance / other).
    if node_type == "media":
        artifact["media_versioning"] = []
    # Organization-specific universal sections. key_personnel (people
    # + sourced roles at this org) and org_relationships (org-to-org
    # structured links) required on every organization artifact
    # regardless of kind. Kind-conditional `contracts` scaffolded
    # below via KIND_SECTIONS_BY_TYPE (gov-contractor only).
    if node_type == "organization":
        artifact["key_personnel"] = []
        artifact["org_relationships"] = []
    # Location-specific universal sections (F.6a). ownership_timeline
    # carries the chronological ownership-transition record;
    # uap_scope_activity tracks institutional UAP-scope activity at the
    # location; location_relationships is heterogeneous entity_path
    # links to connected nodes (owners, investigators, events, media,
    # adjacent locations, findings). Location has no kinds, so no
    # kind-conditional extensions layer on top.
    if node_type == "location":
        artifact["ownership_timeline"] = []
        artifact["uap_scope_activity"] = []
        artifact["location_relationships"] = []
    # Archetype-conditional section on person artifacts. Reads the target
    # node's frontmatter to get its archetype; scaffolds the corresponding
    # empty list. Only one of the four sections is ever scaffolded
    # per person artifact (the archetype decides which).
    archetype = read_target_archetype(node_type, slug)
    if archetype:
        section = ARCHETYPE_SECTION.get(archetype)
        if section:
            artifact[section] = []
    # Kind-conditional section on kind-bearing artifacts (event, transcript).
    # Dispatched by KIND_SECTIONS_BY_TYPE — see constant definition for the
    # full mapping. Absent inner entry (e.g., transcript.other) → no
    # section scaffolded.
    kind = read_target_kind(node_type, slug)
    if kind:
        section = KIND_SECTIONS_BY_TYPE.get(node_type, {}).get(kind)
        if section:
            artifact[section] = []
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
        for sp in source_paths:
            print(f"     pdftotext -layout sources/{sp} /tmp/scratch-{slug}.txt")
    else:
        print(f"     (add sources to primary_sources in {rel}, or re-scaffold with --sources)")
    print(f"  2. Fill in document_intrinsic and context_extrinsic from the extracted text")
    print(f"  3. Write `description` (1-3 paragraphs) — renders as the node's Description section")
    print(f"  4. Populate quotes (verbatim passages with location refs)")
    print(f"  5. Populate entities_referenced, naming_quirks, research_gaps")
    if node_type in RUMORS_TYPES:
        print(f"  6. Populate rumors (widely-reported claims lacking primary-source backing)")
    print(f"  7. Validate: python3 scripts/validate-research.py {rel}")
    print(f"     (see prompts/build.md Step 7 for claims-scope rule — `claims: []` on all renderer-supported types)")


if __name__ == "__main__":
    main()
