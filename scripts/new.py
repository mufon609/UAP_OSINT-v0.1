#!/usr/bin/env python3
"""
Scaffold a new node from meta/templates/.

Examples:
  new.py person --archetype eyewitness --slug chad-underwood --name "Chad Underwood"
  new.py organization --kind gov --slug aaro --name "AARO"
  new.py document --kind gov-doc --form testimony --slug written-testimony-fravor-2023
  new.py document --kind gov-doc --form technical-report --slug dird-01-metallic-glasses --corpus aawsap-dird
  new.py document --kind non-gov-doc --form article --slug 2017-nyt-tic-tac
  new.py document --kind non-gov-doc --form book --archival-status excerpts-only --slug skinwalkers-at-the-pentagon-2021
  new.py transcript --kind hearing --slug 2023-07-26-house-fravor
  new.py transcript --kind other --slug nell-sol-foundation-2023
  new.py event --kind hearing --slug 2023-07-26-house-oversight
  new.py media --kind video --slug gimbal-declassified
  new.py media --kind photo --slug dird-01-cover
  new.py location --slug skinwalker-ranch
  new.py finding --entities /people/sean-kirkpatrick,/organizations/aaro --slug kirkpatrick-ornl

Reads meta/schema.yaml + meta/templates/{type}.md + optionally meta/topic/addenda/{corpus}.md.
Writes to {type_dir}/{slug}.md.
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import date

try:
    import yaml  # noqa: F401  (kept for ImportError guidance)
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from lib._common import REPO_ROOT, content_type_dirs, load_schema

TEMPLATES_DIR = REPO_ROOT / "meta" / "templates"
ADDENDA_DIR = REPO_ROOT / "meta" / "topic" / "addenda"

# TYPE_DIRS is the schema-derived ``{type: dirname}`` mapping shared
# across every contributor script. The constant is bound at import
# time from the cached schema; mutating it after import is unsupported
# (treat as a frozen view into schema state).
TYPE_DIRS = content_type_dirs()

DEFAULT_STATUS = {
    "person": "active",
    "organization": "active",
    "event": "documented",
    "document": "primary-source-confirmed",
    "transcript": "primary-source-confirmed",
    "media": "primary-source-confirmed",
    "location": "active",
    "finding": "active",
}


def humanize(slug):
    """chad-underwood -> Chad Underwood"""
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


def insert_addendum(text, corpus):
    """Replace <!-- CORPUS-ADDENDUM-INSERT --> with a header for the addendum."""
    if not corpus:
        # Remove the marker line entirely
        return re.sub(
            r"<!-- CORPUS-ADDENDUM-INSERT:[^>]*-->\n?",
            "",
            text,
        )
    # For now, insert a scaffold header referencing the addendum file.
    # The contributor fills in the content per meta/topic/addenda/{corpus}.md rules.
    addendum_path = ADDENDA_DIR / f"{corpus}.md"
    if not addendum_path.exists():
        sys.exit(f"ERROR: Addendum not found: {addendum_path}")
    # Parse addendum for additional-required-sections list
    addendum_text = addendum_path.read_text()
    section_names = re.findall(
        r"###?\s+`##\s+([^`]+)`",
        addendum_text,
    )
    insert = ""
    for sec in section_names:
        insert += f"\n## {sec}\n\n<!-- Per meta/topic/addenda/{corpus}.md rules. -->\n\n---\n"
    return re.sub(
        r"<!-- CORPUS-ADDENDUM-INSERT:[^>]*-->\n?",
        insert,
        text,
    )


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
    parser.add_argument("--entities", help="Comma-separated entity paths (finding nodes)")
    parser.add_argument("--corpus", help="Corpus addendum (e.g., aawsap-dird)")
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
    # Validate archival-status value when supplied. Direct subscript
    # per the C21 no-silent-fallbacks principle — archival_status is
    # only set on document type, where ``archival_status_values`` is
    # always declared in schema.
    if args.archival_status:
        valid_archival = type_spec["archival_status_values"]
        if args.archival_status not in valid_archival:
            sys.exit(f"ERROR: Invalid --archival-status. Valid: {valid_archival}")

    if args.type == "finding" and not args.entities:
        sys.exit("ERROR: --entities required for finding")

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
    subs = {
        "slug": args.slug,
        "display_name": display_name,
        "today": date.today().isoformat(),
        "archetype": args.archetype or "",
        "kind": args.kind or "",
        "doc_form": args.form or "",
        "status": status,
        "archival_status": args.archival_status or "",
        "derivation_of": args.derivation_of or "",
        "source_medium": args.source_medium or "",
        "derived_from": args.derived_from or "",
        "corpus": args.corpus or "",
        "parent_slug": (args.derivation_of.rsplit("/", 1)[-1] if args.derivation_of else ""),
    }

    if args.type == "finding":
        ents = [e.strip() for e in args.entities.split(",")]
        for i in range(1, 4):
            subs[f"entity_path_{i}"] = ents[i - 1] if i <= len(ents) else ""

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

    # Handle corpus addendum insertion
    if args.type == "document":
        text = insert_addendum(text, args.corpus)

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

    text = apply_optional_frontmatter(
        text, "CORPUS", f"corpus: {args.corpus}" if args.corpus else None
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
    print("Next steps:")
    print(f"  1. Fill in {rel_path} — frontmatter TODO fields, Identity/Overview,")
    print("     Description, required tables. Archive cited URLs inline.")
    print("  2. Register sources:  python3 scripts/manifest.py add URL --path PATH")
    print(f"  3. Regenerate Associated Nodes:  python3 scripts/associate.py {rel_path}")
    print("  4. Validate:  python3 scripts/validate.py")


if __name__ == "__main__":
    main()
