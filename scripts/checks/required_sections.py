"""required-sections check — per-node NodeContext check.

Verifies every section listed in ``type_spec`` (after archetype/kind
routing and corpus-addendum merge) appears as an H2 heading in the
node body. Match is exact title or title prefix followed by ``" ("``
or ``" —"`` (so section names with parenthesized qualifiers or em-dash
clarifications still satisfy the requirement — e.g., a required
``Overview`` matches ``## Overview (deprecated)``).

Corpus addenda (per ``meta/topic/addenda/{name}.md``) declare
additional required sections; merged into the per-type list when the
node's frontmatter sets ``corpus``.

Lift from validate.py validate_node (C11 session-3 migration). Carries
``compute_required_sections`` and ``load_addendum_sections`` (both
only used by this check).
"""

import re
from pathlib import Path

from checks import Issue


CHECK_NAME = "required_sections"


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ADDENDA_DIR = _REPO_ROOT / "meta" / "topic" / "addenda"


def _load_addendum_sections(corpus):
    """Parse an addendum file for required sections."""
    path = _ADDENDA_DIR / f"{corpus}.md"
    if not path.exists():
        return []
    text = path.read_text()
    # Look for "## Additional required sections" block; then `## SectionName`
    m = re.search(
        r"##\s+Additional required sections\s*\n(.*?)(?=\n---|\n##\s|\Z)",
        text, re.DOTALL,
    )
    if not m:
        return []
    block = m.group(1)
    return re.findall(r"`##\s+([^`]+)`", block)


def _compute_required_sections(fm, type_spec):
    sections = []
    arch = fm.get("archetype")
    kind = fm.get("kind")
    if arch and "archetypes" in type_spec:
        sections = list(type_spec["archetypes"].get(arch, {}).get("required_sections", []))
    elif kind and "kinds" in type_spec:
        sections = list(type_spec["kinds"].get(kind, {}).get("required_sections", []))
    else:
        sections = list(type_spec.get("required_sections", []))
    corpus = fm.get("corpus")
    if corpus:
        sections.extend(_load_addendum_sections(corpus))
    return sections


def check(ctx):
    required = _compute_required_sections(ctx.fm, ctx.type_spec)
    h2_sections = ctx.h2_sections
    for req in required:
        found = any(s == req or s.startswith(req + " (") or s.startswith(req + " —")
                    for s in h2_sections)
        if not found:
            yield Issue(
                ctx.rel, "error",
                f"Missing required section '## {req}'",
                check_name=CHECK_NAME,
            )
