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

Origin: foundational from the initial commit (``af5f789``). Both the
schema-driven dispatcher (archetype/kind routing + type-default
fallback) and the corpus-addendum extension mechanism shipped in
af5f789. Migration: ``60bb88d`` (C11 session 3 lift to per-module
shape). Carries ``_compute_required_sections`` and
``_load_addendum_sections`` (both only used by this check).

Anchor pattern: foundational schema-driven dispatcher. The check
code has been stable since af5f789; the schema's per-type /
per-archetype / per-kind required_sections lists evolved
substantially across F.1a–F.6 renderer landings (every new node
type or archetype shipped its own required_sections list), but the
check just walks whatever the schema declares. Same "schema as
single source of truth" pattern as ``iff_section`` (which formalized
the pattern for conditional_keys); required_sections is the earlier
instance.

Forward-defensive corpus-addendum extension. The addendum mechanism
allows corpus-specific structural requirements via
``meta/topic/addenda/{corpus}.md`` — affected nodes set
``corpus: {name}`` in frontmatter; the addendum's "Additional
required sections" block contributes additional H2 requirements.
The mechanism is in place + documented (the existing
``aawsap-dird.md`` file documents itself as the canonical template
for future corpus-specific addenda); currently no node in this
toolkit instance carries a ``corpus:`` frontmatter, so the
extension is dormant in practice. Forward-defensive — fork targets
on different topic instances can drop in their own corpus addenda
without modifying the check code.

Match semantics intentionally permissive: exact-title OR
title-prefix-followed-by-space-and-( OR title-prefix-followed-by-
space-and-em-dash. Allows section-rename-with-qualifier
(``## Overview (deprecated)``, ``## Identity — Aliases``) without
forcing schema updates for cosmetic header changes. The
boundary check (Phase III) catches structural divergence between
artifact and rendered node, so over-permissive matching here
doesn't open a real loophole.

Truthy archetype/kind routing is intentional and distinct from the
status_archetype_kind layering bug fixed during the C17 sweep:
required_sections falls through to top-level required_sections when
archetype/kind is null/absent, on the basis that archetype-validity
is delegated to ``status_archetype_kind``. By the time this check
runs with a null archetype, status_archetype_kind has already
errored on the missing/null enum value. The fall-through behavior
is correct, not a layering gap.

C18 confirmed byte-identity through the C11 migration.
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
