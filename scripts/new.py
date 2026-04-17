#!/usr/bin/env python3
"""
Scaffold a new node from meta/templates/.

Examples:
  new.py person --archetype eyewitness --slug chad-underwood --name "Chad Underwood"
  new.py organization --kind gov --slug aaro --name "AARO"
  new.py document --kind gov-doc --form testimony --slug written-testimony-fravor-2023
  new.py document --kind gov-doc --form technical-report --slug dird-01-metallic-glasses --corpus aawsap-dird
  new.py transcript --kind hearing --slug 2023-07-26-house-fravor
  new.py event --kind hearing --slug 2023-07-26-house-oversight
  new.py news --slug 2017-nyt-tic-tac
  new.py book --slug skinwalkers-at-the-pentagon-2021
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
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "meta" / "schema.yaml"
TEMPLATES_DIR = REPO_ROOT / "meta" / "templates"
ADDENDA_DIR = REPO_ROOT / "meta" / "topic" / "addenda"

TYPE_DIRS = {
    "person": "people",
    "organization": "organizations",
    "document": "documents",
    "event": "events",
    "transcript": "transcripts",
    "news": "news",
    "book": "books",
    "location": "locations",
    "finding": "findings",
}

DEFAULT_STATUS = {
    "person": "active",
    "organization": "active",
    "event": "documented",
    "document": "primary-source-confirmed",
    "transcript": "primary-source-confirmed",
    "news": "published",
    "book": "published",
    "location": "active",
    "finding": "active",
}


def load_schema():
    with open(SCHEMA_PATH) as f:
        return yaml.safe_load(f)


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
    parser.add_argument("--kind", help="Organization/document/event/transcript kind")
    parser.add_argument("--form", help="Document form (doc_form)")
    parser.add_argument("--status", help="Status (default: type-specific)")
    parser.add_argument("--archival-status", default="not-archived", help="Book archival_status")
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
    if args.type in ("organization", "document", "event", "transcript"):
        if not args.kind:
            sys.exit(f"ERROR: --kind required for {args.type}")
        valid = list(type_spec.get("kinds", {}).keys())
        if args.kind not in valid:
            sys.exit(f"ERROR: Invalid kind. Valid: {valid}")

    if args.type == "document" and not args.form:
        sys.exit("ERROR: --form required for document (see schema.yaml doc_form_values)")

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
        "archival_status": args.archival_status,
        "corpus": args.corpus or "",
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
    text = filter_conditional_blocks(text, markers)

    # Handle corpus addendum insertion
    if args.type == "document":
        text = insert_addendum(text, args.corpus)

    # Clean up runs of blank lines from removed blocks
    text = clean_blank_lines(text)

    # Handle corpus frontmatter. Regex matches the full CORPUS comment block
    # regardless of whether {{corpus}} has already been rendered — works
    # both before and after render_placeholders. If --corpus is set, the
    # commented template is replaced with an active `corpus: X` line. If
    # not set, the block is removed entirely. (Fix: previous .replace() logic
    # assumed the raw template text post-render, which was incorrect once
    # render_placeholders substituted {{corpus}}.)
    if args.corpus:
        text = re.sub(
            r"<!-- CORPUS:.*?-->",
            f"corpus: {args.corpus}",
            text,
            flags=re.DOTALL,
        )
    else:
        text = re.sub(
            r"<!-- CORPUS:.*?-->\n?",
            "",
            text,
            flags=re.DOTALL,
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
