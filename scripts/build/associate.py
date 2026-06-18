#!/usr/bin/env python3
"""
Regenerate the '## Associated Nodes' section of a node from body references.

Scans the node body for every [`/path/to/...`] reference (excluding the
Associated Nodes section itself and self-references), groups by target
type, and rewrites the section.

Usage:
  associate.py PATH            # regenerate one node
  associate.py --all           # regenerate every node
  associate.py --check         # report stale sections (exit 1 if any)
"""

import argparse
import re
import sys
from pathlib import Path
from collections import defaultdict

# scripts/build/associate.py — put the scripts/ parent on sys.path so
# `from lib._common` resolves from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import REPO_ROOT, content_dirs, RESEARCH_DIR, strict_yaml_load

CONTENT_DIRS = content_dirs()

# Display order of groups in the Associated Nodes section
GROUP_ORDER = [
    "People",
    "Organizations",
    "Events",
    "Documents",
    "Transcripts",
    "Media",
    "Locations",
    "Findings",
]

DIR_TO_GROUP = {
    "people": "People",
    "organizations": "Organizations",
    "events": "Events",
    "documents": "Documents",
    "transcripts": "Transcripts",
    "media": "Media",
    "locations": "Locations",
    "findings": "Findings",
}

LINK_PATTERN = re.compile(r"\[`(/[^`]+)`\]")


def extract_links(text, exclude_self=None):
    links = set(LINK_PATTERN.findall(text))
    if exclude_self:
        links.discard(exclude_self)
        links.discard(f"/{exclude_self}")
    return links


def group_links(links):
    groups = defaultdict(list)
    for link in links:
        parts = link.strip("/").split("/")
        if len(parts) < 2:
            continue
        group = DIR_TO_GROUP.get(parts[0], parts[0].capitalize())
        groups[group].append(link)
    return groups


def generate_section(groups):
    """Generate the `## Associated Nodes` section. Associated Nodes is
    always the final section of a node body, so no trailing `---`
    separator is emitted."""
    lines = ["## Associated Nodes", ""]
    for group in GROUP_ORDER:
        if group not in groups:
            continue
        links = sorted(set(groups[group]))
        lines.append(f"### {group}")
        lines.append("")
        for link in links:
            lines.append(f"- [`{link}`]")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def replace_section(text, new_section):
    """Replace the `## Associated Nodes` section in place, or append it at
    end-of-body if absent.

    `new_section` carries no separator of its own (`generate_section` ends with
    `.rstrip() + "\\n"`). The `---` that precedes `## Associated Nodes` in a
    rendered node lives in `text[:start]` and is preserved by `prefix`. The
    section is the node's final section by the directional contract, so in
    practice `next_h2` is None and `end` is end-of-text; the next-H2 branch is
    a guard for the unexpected mid-body case.
    """
    match = re.search(r"^## Associated Nodes\s*$", text, re.MULTILINE)
    if match:
        start = match.start()
        after = text[match.end():]
        next_h2 = re.search(r"^## ", after, re.MULTILINE)
        end = match.end() + next_h2.start() if next_h2 else len(text)
        prefix = text[:start].rstrip() + "\n\n"
        suffix = text[end:]
        return prefix + new_section + suffix

    # No existing section — append at end
    return text.rstrip() + "\n\n" + new_section


def artifact_associated_entities(node_path, self_id):
    """Read the backing research artifact's ``associated_entities`` list and
    return it as a link set, so an entity the source names ONLY inside a
    verbatim quote (un-wrappable — the verbatim-quote check rejects a link
    injected into ``quote.text``) still reaches ``## Associated Nodes``
    without depending on the author re-naming it in prose. See
    ``schema-research-artifact.yaml::conditional_keys.associated_entities``
    and the build-protocol "name it, wrap it" contract. The field is required
    on the source-backed types and absent on the rest; associate is
    non-authoritative and type-agnostic, so a missing field / missing
    artifact / parse error all yield the empty set rather than breaking the
    run (the artifact stem is the node stem, 1:1 by slug)."""
    artifact = RESEARCH_DIR / f"{node_path.stem}.yaml"
    if not artifact.is_file():
        return set()
    try:
        data = strict_yaml_load(artifact.read_text()) or {}
    except Exception:
        return set()
    out = set()
    for p in (data.get("associated_entities") or []):
        if isinstance(p, str) and p.startswith("/"):
            out.add(p)
    out.discard(self_id)
    out.discard(f"/{self_id}")
    return out


def associate_node(node_path, dry_run=False):
    text = node_path.read_text()
    self_id = str(node_path.relative_to(REPO_ROOT)).removesuffix(".md")

    # Remove existing Associated Nodes section before scanning (avoid self-amplification)
    scan_text = text
    existing = re.search(
        r"^## Associated Nodes\s*$.*?(?=^## |\Z)",
        text, re.MULTILINE | re.DOTALL,
    )
    if existing:
        scan_text = text[:existing.start()] + text[existing.end():]

    links = extract_links(scan_text, exclude_self=self_id)
    links |= artifact_associated_entities(node_path, self_id)
    groups = group_links(links)
    new_section = generate_section(groups)
    new_text = replace_section(text, new_section)

    if new_text != text:
        if not dry_run:
            node_path.write_text(new_text)
        return True
    return False


def collect_all_nodes():
    nodes = []
    for d in CONTENT_DIRS:
        cd = REPO_ROOT / d
        if cd.is_dir():
            nodes.extend(sorted(cd.glob("*.md")))
    return nodes


def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--check", action="store_true",
                        help="Report stale sections without writing")
    args = parser.parse_args()

    if args.check or args.all:
        nodes = collect_all_nodes()
        changed = 0
        for node in nodes:
            if associate_node(node, dry_run=args.check):
                changed += 1
                print(f"  {'STALE ' if args.check else 'UPDATE'}  {node.relative_to(REPO_ROOT)}")
        if args.check:
            print(f"\n{changed} stale Associated Nodes sections")
            sys.exit(1 if changed else 0)
        print(f"\n{changed} nodes updated")
    elif args.path:
        node = Path(args.path).resolve()
        if not node.exists():
            sys.exit(f"ERROR: {node} not found")
        if associate_node(node):
            print(f"✓ Updated {node.relative_to(REPO_ROOT)}")
        else:
            print(f"  No change: {node.relative_to(REPO_ROOT)}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
