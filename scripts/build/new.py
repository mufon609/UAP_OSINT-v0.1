#!/usr/bin/env python3
"""
Scaffold a new node from meta/templates/.

Examples:
  new.py person --archetype eyewitness --slug jane-doe --name "Jane Doe"
  new.py organization --kind gov --slug example-agency --name "Example Agency"
  new.py document --kind gov-doc --form testimony --archival-status excerpts-only --slug example-testimony-2024
  new.py location --slug example-site
  new.py investigation --slug example-inquiry --question "Does Acme Widgets house the example materials?"

Reads meta/schema.yaml + meta/templates/{type}.md.
Writes to {type_dir}/{slug}.md.
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml  # noqa: F401  (kept for ImportError guidance)
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# scripts/build/new.py — put the scripts/ parent on sys.path so
# `from lib._common` resolves from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import REPO_ROOT, content_type_dirs, load_schema, load_topic

TEMPLATES_DIR = REPO_ROOT / "meta" / "templates"

# Schema-derived ``{type: dirname}`` mapping. Bound at import time
# from the cached schema; treat as a frozen view (do not mutate).
TYPE_DIRS = content_type_dirs()

DEFAULT_STATUS = {
    "person": "active",
    "organization": "active",
    "event": "documented",
    "document": "primary-source-confirmed",
    "transcript": "primary-source-confirmed",
    "media": "primary-source-confirmed",
    "location": "active",
    "investigation": "open",
}


def humanize(slug):
    """jane-doe -> Jane Doe"""
    return " ".join(w.capitalize() for w in slug.split("-"))


def render_placeholders(text, subs):
    for key, value in subs.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def filter_conditional_blocks(text, markers):
    """
    Remove blocks bracketed by <!-- MARKER: value --> ... <!-- /MARKER -->
    whose value does not match the selected value for MARKER.
    """
    for marker_name, selected in markers.items():
        pattern = re.compile(
            rf"<!-- {marker_name}: ([\w-]+) -->\n?(.*?)<!-- /{marker_name} -->\n?",
            re.DOTALL,
        )

        def replace(match):
            block_value = match.group(1)
            block_content = match.group(2)
            if block_value == selected:
                return block_content
            return ""

        text = pattern.sub(replace, text)
    return text


def clean_blank_lines(text):
    return re.sub(r"\n{3,}", "\n\n", text)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("type", choices=TYPE_DIRS.keys())
    parser.add_argument("--slug", required=True)
    parser.add_argument("--name", help="Display name (default: humanized slug)")
    parser.add_argument("--archetype", help="Person archetype")
    parser.add_argument("--kind", help="Organization/document/event/transcript/media kind")
    parser.add_argument("--form", help="Document form (doc_form)")
    parser.add_argument("--status", help="Status (default: type-specific)")
    parser.add_argument("--archival-status", help="Document archival_status (required for doc_form=book)")
    parser.add_argument("--derivation-of", help="Media derivation_of: path to parent media node for derivative media")
    parser.add_argument("--source-medium", help="Transcript source_medium (free-text; e.g., youtube, podcast, broadcast)")
    parser.add_argument("--derived-from", help="Transcript derived_from: path to underlying media/document node")
    parser.add_argument("--question", help="Open question (investigation nodes — frontmatter `question` field)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing")
    args = parser.parse_args()

    schema = load_schema()
    type_spec = schema["types"].get(args.type)
    if not type_spec:
        sys.exit(f"ERROR: Unknown type: {args.type}")

    # Validate archetype
    if args.type == "person":
        if not args.archetype:
            sys.exit("ERROR: --archetype required for person")
        valid = list(type_spec.get("archetypes", {}).keys())
        if args.archetype not in valid:
            sys.exit(f"ERROR: Invalid archetype. Valid: {valid}")

    # Validate kind
    if args.type in ("organization", "document", "event", "transcript", "media"):
        if not args.kind:
            sys.exit(f"ERROR: --kind required for {args.type}")
        valid = list(type_spec.get("kinds", {}).keys())
        if args.kind not in valid:
            sys.exit(f"ERROR: Invalid kind. Valid: {valid}")

    if args.type == "document" and not args.form:
        sys.exit("ERROR: --form required for document (see schema.yaml doc_form_values)")

    # Conditional: document doc_form=book requires --archival-status
    if args.type == "document" and args.form == "book" and not args.archival_status:
        sys.exit(
            "ERROR: --archival-status required when doc_form=book. "
            "Valid values: full-text-archived, excerpts-only, not-archived"
        )
    if args.archival_status:
        if args.type != "document":
            sys.exit(
                "ERROR: --archival-status only applies to --type document"
            )
        valid_archival = type_spec["archival_status_values"]
        if args.archival_status not in valid_archival:
            sys.exit(f"ERROR: Invalid --archival-status. Valid: {valid_archival}")

    if args.type == "investigation" and not args.question:
        sys.exit("ERROR: --question required for investigation")

    # Output path
    type_dir = REPO_ROOT / TYPE_DIRS[args.type]
    type_dir.mkdir(parents=True, exist_ok=True)
    out_path = type_dir / f"{args.slug}.md"
    if out_path.exists() and not args.force:
        sys.exit(f"ERROR: {out_path} exists. Use --force to overwrite.")

    # Load template
    template_path = TEMPLATES_DIR / f"{args.type}.md"
    if not template_path.exists():
        sys.exit(f"ERROR: Template not found: {template_path}")
    text = template_path.read_text()

    # Substitutions
    display_name = args.name or humanize(args.slug)
    status = args.status or DEFAULT_STATUS.get(args.type, "active")
    # ``topic_display_name`` is the toolkit-instance topic's display name
    # (e.g. "UAP" on this fork) — distinct from ``display_name`` which
    # is THIS NODE's title. Templates that
    # reference the topic in section headers / comments use
    # ``{{topic_display_name}}`` so the scaffolded body matches what the
    # renderer would emit (the renderer composes the same headers from
    # ``meta/topic/overview.md::display_name``). Keeps fork targets from
    # seeing hardcoded UAP literals during the gap between scaffold and
    # first build.
    subs = {
        "slug": args.slug,
        "display_name": display_name,
        "topic_display_name": load_topic()["display_name"],
        "archetype": args.archetype or "",
        "kind": args.kind or "",
        "doc_form": args.form or "",
        "status": status,
        "archival_status": args.archival_status or "",
        "derivation_of": args.derivation_of or "",
        "source_medium": args.source_medium or "",
        "derived_from": args.derived_from or "",
        "parent_slug": (args.derivation_of.rsplit("/", 1)[-1] if args.derivation_of else ""),
        "question": (args.question or "").replace("'", "''"),
    }

    # Render placeholders
    text = render_placeholders(text, subs)

    # Filter conditional archetype/kind blocks
    markers = {}
    if args.archetype:
        markers["ARCHETYPE"] = args.archetype
    if args.kind:
        markers["KIND"] = args.kind
    # Media: DERIVATIVE marker gates the Media Versioning section and is
    # orthogonal to KIND (a derivative can be any kind — photo, video,
    # audio, imagery-other). Always set for media nodes so the block is
    # either kept (when derivation_of is set) or dropped (when absent).
    # filter_conditional_blocks only processes markers that appear in the
    # dict; a missing marker would leave the block intact.
    if args.type == "media":
        markers["DERIVATIVE"] = "yes" if args.derivation_of else "no"
    text = filter_conditional_blocks(text, markers)

    # Clean up runs of blank lines from removed blocks
    text = clean_blank_lines(text)

    # Optional-frontmatter comment-block handling. Each optional frontmatter
    # field lives in the template as a commented-out block like:
    #   <!-- MARKER: ... active_line: {{value}} -->
    # When the corresponding CLI flag is supplied, the block is replaced
    # with the active frontmatter line. When omitted, the block is removed.
    # Regex matches the full block regardless of whether {{value}} has
    # already been rendered — works both before and after render_placeholders.
    def apply_optional_frontmatter(text, marker, active_line):
        if active_line is not None:
            return re.sub(
                rf"<!-- {marker}:.*?-->",
                active_line,
                text,
                flags=re.DOTALL,
            )
        return re.sub(
            rf"<!-- {marker}:.*?-->\n?",
            "",
            text,
            flags=re.DOTALL,
        )

    # Document: archival_status — required when doc_form=book (already
    # validated above); optional for other non-gov-doc forms.
    text = apply_optional_frontmatter(
        text,
        "ARCHIVAL_STATUS",
        f"archival_status: {args.archival_status}" if args.archival_status else None,
    )
    # Media: derivation_of — path to a parent media node for derivatives.
    text = apply_optional_frontmatter(
        text,
        "DERIVATION",
        f"derivation_of: {args.derivation_of}" if args.derivation_of else None,
    )
    # Transcript: source_medium — free-text source format metadata.
    text = apply_optional_frontmatter(
        text,
        "SOURCE_MEDIUM",
        f"source_medium: {args.source_medium}" if args.source_medium else None,
    )
    # Transcript: derived_from — path to underlying media/document node.
    text = apply_optional_frontmatter(
        text,
        "DERIVED_FROM",
        f"derived_from: {args.derived_from}" if args.derived_from else None,
    )

    out_path.write_text(text)

    # Report
    rel_path = out_path.relative_to(REPO_ROOT)
    print(f"✓ Created {rel_path}")
    print()
    print("Next steps — build via the /build skill (the multi-agent pipeline;")
    print("design rationale in prompts/topology.md).")
    print(f"  1. Register every primary source:  python3 scripts/tools/manifest.py add URL --path PATH")
    print(f"  2. Scaffold the research artifact:")
    print(f"     python3 scripts/build/research-scaffold.py --target {TYPE_DIRS[args.type]}/{args.slug} \\")
    print(f"         --sources <comma-separated paths relative to sources/>")
    print(f"  3. Phase I — extract sources + populate the artifact (do NOT hand-edit the node body):")
    print(f"     python3 scripts/build/extract-source.py --artifact meta/research/{args.slug}.yaml")
    print(f"     python3 scripts/build/validate-research.py meta/research/{args.slug}.yaml")
    print(f"  4. Phase II — render the node body from the artifact:")
    print(f"     python3 scripts/build/build-from-research.py meta/research/{args.slug}.yaml")
    print(f"  5. Phase III — coverage / boundary / stub-linking review:")
    print(f"     python3 scripts/build/review-coverage.py meta/research/{args.slug}.yaml")


if __name__ == "__main__":
    main()
