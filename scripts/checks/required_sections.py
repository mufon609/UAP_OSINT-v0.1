"""required-sections check — per-node NodeContext check.

Verifies every section listed in the type_spec (after archetype/kind
routing and corpus-addendum merge) appears as an H2 heading in the
node body. Match is exact title or title prefix followed by ``" ("``
or ``" —"`` so qualified renames satisfy the requirement (a required
``Overview`` matches ``## Overview (deprecated)``,
``## Identity — Aliases``). The over-permissive shape doesn't open a
loophole: the boundary check catches structural divergence between
artifact and rendered node.

Corpus addenda (``meta/topic/addenda/{name}.md``) contribute additional
required sections via their "Additional required sections" block when
a node's frontmatter sets ``corpus``.

Layering: when archetype or kind is null or absent, this check falls
through to the top-level required_sections — ``status_archetype_kind``
is responsible for erroring on missing/null enum values, so the
fall-through is correct rather than a layering gap. Invalid
contributor data (archetype/kind set but not in the enum) returns an
empty list here to avoid double-firing on the same defect; schema
drift (a per-archetype/kind block missing ``required_sections``)
surfaces as a loud KeyError.
"""

import re
from pathlib import Path

from checks import Issue
from lib._common import topic_substitute


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
    top-level ``required_sections``) surfaces as a loud KeyError.
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
    # Substitute {topic_display_name} placeholders before returning so
    # the validator matches the rendered H2 headers (which the renderer
    # composes via load_topic() at render time). Schema stays topic-
    # neutral; this is the symmetric resolution at validation time.
    return [topic_substitute(s) for s in sections]


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
