#!/usr/bin/env python3
"""
Scaffold an empty research artifact for a target node.

Produces meta/research/{slug}.yaml with:
  - required top-level keys populated with defaults
  - empty lists for each content section
  - `rumors` section present only when target_node type ∈
    {person, organization, event, location} (per
    schema-research-artifact.yaml::conditional_keys)

Usage:
  research-scaffold.py --target {type}/{slug}
  research-scaffold.py --target documents/written-testimony-fravor-2023
  research-scaffold.py --target documents/written-testimony-fravor-2023 \\
      --sources government/oversight-house-gov-fravor-written-testimony-20230726.pdf
  research-scaffold.py --target ... --force    # overwrite existing artifact

The scaffolded artifact is a structurally valid empty shell. Phase I of
the build process fills it in. Contributors should run
`scripts/build/validate-research.py` after populating each section.
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

# scripts/build/research-scaffold.py — put the scripts/ parent on sys.path
# so `from lib._common` and `from checks` resolve from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# =============================================================================
# Constants
# =============================================================================

from lib._common import (
    strict_yaml_load,
    REPO_ROOT,
    content_node_types,
    content_type_dirs,
    format_from_path,
    load_manifest,
    load_schema,
    normalize_source_rel_path,
)

RESEARCH_DIR = REPO_ROOT / "meta" / "research"

# Type-set conditionals (which sections to scaffold for which target
# type / archetype / kind) come from
# schema-research-artifact.yaml::conditional_keys via the same
# ``evaluate_required_when`` helper the validators use, so schema edits
# propagate to the scaffolder automatically.

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
    # Finding artifact — single declarative sentence
    "pattern_statement": "",
    # Investigation artifact — single integrated answer object
    "best_current_answer": {},
}


def empty_for(section_name):
    """Return the empty value to scaffold under ``section_name``. Default
    is `[]` (most conditional sections are entry lists); explicit
    overrides for prose fields and event_intrinsic dict."""
    return EMPTY_SECTION_SHAPES.get(section_name, [])


# Schema-derived constants — bound at import time from the cached
# schema. ``content_node_types()`` returns the set of types that accept
# artifacts; ``content_type_dirs()`` is the {type: dirname} map.
VALID_TARGET_TYPES = content_node_types()
TYPE_DIRS = content_type_dirs()


# =============================================================================
# Helpers
# =============================================================================


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
    Validates each path appears in the manifest. Format is read from
    the manifest entry when available — the manifest is the source of
    truth — so scaffolded artifacts cannot diverge from the manifest at
    creation. Falls back to extension-based inference only when the
    path is absent from the manifest (which will trigger a validator
    error anyway)."""
    manifest_by_path = {e["path"]: e for e in manifest if e.get("path")}
    entries = []
    for path in source_paths:
        manifest_entry = manifest_by_path.get(path)
        if manifest_entry is None:
            print(f"WARNING: {path!r} not found in sources/manifest.yaml — "
                  f"scaffolder will still include it, but validate-research.py "
                  f"will error until the source is registered.",
                  file=sys.stderr)
            fmt = format_from_path(path)
        else:
            fmt = manifest_entry.get("format") or format_from_path(path)
        entry = {
            "path": path,
            "format": fmt,
        }
        entries.append(entry)
    return entries


def _read_target_frontmatter(node_type, slug):
    """Read the target node's frontmatter and return it as a dict (or
    empty dict on failure). Shared helper used for archetype (person)
    and kind (event) reads. Warns to stderr on read / parse failures
    so the contributor knows why the scaffold may be missing
    archetype/kind-specific sections."""
    path = target_node_file(node_type, slug)
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(
            f"research-scaffold.py: warning — couldn't read {path} "
            f"({type(e).__name__}: {e}); scaffold may be missing "
            f"archetype/kind-specific sections",
            file=sys.stderr,
        )
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    try:
        return strict_yaml_load(text[3:end]) or {}
    except yaml.YAMLError as e:
        print(
            f"research-scaffold.py: warning — frontmatter parse failed "
            f"for {path} ({e}); scaffold may be missing archetype/"
            f"kind-specific sections",
            file=sys.stderr,
        )
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
    """Assemble the research-artifact YAML dict for the given target.

    Universal top-level keys are populated unconditionally. Type /
    archetype / kind-conditional sections are dispatched schema-driven
    from ``schema-research-artifact.yaml::conditional_keys`` via ``evaluate_required_when``
    (the same helper the validators use).
    """
    today = date.today().isoformat()
    artifact = {
        "id": f"meta/research/{slug}",
        "type": "research-artifact",
        "schema_version": 1,
        "target_node": f"{TYPE_DIRS[node_type]}/{slug}",
        "status": "active",
        "created": today,
        "primary_sources": build_primary_sources_list(source_paths, manifest),
        "document_intrinsic": {},
        "context_extrinsic": {},
        "quotes": [],
        "entities_referenced": [],
        "naming_quirks": [],
    }

    # description is required by the validator on document / transcript /
    # media / event / organization / finding / location types (the types
    # whose renderers emit ## Description); person and investigation
    # renderers do not call render_description, so the field is unrendered
    # on those types. Skip emitting an empty placeholder for person to
    # avoid the "scaffolded but never rendered" trap. Investigation keeps
    # description as opt-in since its renderer DOES wire it up.
    if node_type != "person":
        artifact["description"] = ""

    # Schema-driven scaffolding for type / archetype / kind-conditional
    # sections. Reads conditional_keys once; walks each declared
    # section; adds an empty value of the right shape when the rules
    # match this target.
    archetype = read_target_archetype(node_type, slug)
    kind = read_target_kind(node_type, slug)
    # Direct subscript: schema malformation surfaces loudly rather than
    # silently scaffolding artifacts with no conditional sections.
    conditional_keys = load_schema()["types"]["research-artifact"]["conditional_keys"]
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
                 f"  Scaffold the target node first via `scripts/build/new.py`, then its research artifact.")

    # Compute output path
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESEARCH_DIR / f"{slug}.yaml"
    if out_path.exists() and not args.force:
        sys.exit(f"ERROR: {out_path.relative_to(REPO_ROOT)} exists. "
                 f"Use --force to overwrite.")

    # Parse sources — accept both ``news/foo.html`` (canonical sources/-
    # relative form) and ``sources/news/foo.html`` (repo-root form
    # contributors paste from grep / find output) per the shared
    # ``normalize_source_rel_path`` helper.
    source_paths = [
        normalize_source_rel_path(s) for s in args.sources.split(",") if s.strip()
    ]
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
        print(f"     python3 scripts/build/extract-source.py --artifact {rel}")
        print(f"     (writes /tmp/scratch-{slug}-N.txt — one per primary source)")
    else:
        print(f"     (add sources to primary_sources in {rel}, or re-scaffold with --sources)")
    print(f"  2. Fill in document_intrinsic and context_extrinsic from the extracted text")
    print(f"  3. Write `description` (1-3 paragraphs) — renders as the node's Description section")
    print(f"  4. Populate quotes (verbatim passages with location refs)")
    print(f"  5. Populate entities_referenced, naming_quirks")
    if "rumors" in artifact:
        print(f"  6. Populate rumors (widely-reported claims lacking primary-source backing)")
    print(f"  7. Validate: python3 scripts/build/validate-research.py {rel}")


if __name__ == "__main__":
    main()
