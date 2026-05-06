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

Per-branch lookups separate two distinct cases: (1) invalid
contributor data (archetype/kind set but not in the schema's enum) —
``status_archetype_kind`` already errors on this, so this check
returns an empty section list to avoid double-firing on the same
defect; (2) schema drift (a per-archetype/kind block missing
``required_sections``, or a top-level type missing it) — direct
subscript surfaces a loud KeyError per the C21 no-silent-fallbacks
principle. The earlier ``.get(arch, {}).get("required_sections", [])``
chain conflated the two; the explicit guard + direct subscript shape
keeps each case visible.
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
    """Compute the required-sections list for a node from type_spec.

    Three layering shapes in the current schema:

      1. Per-archetype (person) — each archetype declares its own
         ``required_sections`` list; the type has no top-level one.
      2. Per-kind (organization / document / event / transcript) — each
         kind declares its own list; the type has no top-level one.
      3. Top-level (media / location / finding) — the type declares
         ``required_sections`` directly. Note that media also declares
         ``kinds`` for taxonomy, but those are description-only (no
         per-kind ``required_sections``); the type-level list applies
         to every kind.

    Invalid archetype/kind values are reported by ``status_archetype_kind``
    — this check returns ``[]`` cleanly rather than double-firing or
    crashing. Schema drift (a missing per-archetype, per-kind, or
    top-level ``required_sections``) surfaces as a loud KeyError per
    the C21 no-silent-fallbacks principle.
    """
    sections = []
    arch = fm.get("archetype")
    kind = fm.get("kind")
    if arch and "archetypes" in type_spec:
        if arch not in type_spec["archetypes"]:
            return []  # invalid archetype — status_archetype_kind already errored
        sections = list(type_spec["archetypes"][arch]["required_sections"])
    elif kind and "kinds" in type_spec:
        if kind not in type_spec["kinds"]:
            return []  # invalid kind
        kind_spec = type_spec["kinds"][kind]
        if "required_sections" in kind_spec:
            sections = list(kind_spec["required_sections"])
        else:
            # Per-kind block carries description-only metadata (e.g.,
            # media's photo/video/audio/imagery-other); the type-level
            # required_sections list applies uniformly across kinds.
            sections = list(type_spec["required_sections"])
    else:
        # location / finding — top-level required_sections, no kinds.
        sections = list(type_spec["required_sections"])
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
