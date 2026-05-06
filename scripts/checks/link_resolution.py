"""link-resolution check — per-node NodeContext check (metadata-only).

Walks ``[`/path`]`` body links + frontmatter node-path pointers
(``media.derivation_of``, ``transcript.derived_from``) and tracks any
that don't resolve to an existing repo file in
``ctx.broken_links`` — the out-of-band metadata channel on
BaseContext.

This check is the ONE deliberate exception to the "checks yield
Issues" contract per design doc Q2: broken stubs are backlog signal,
not violations, and intentionally do not fail commits. The orchestrator
reads ``ctx.broken_links`` after all per-node checks complete and
prints the registry; broken links never appear as Issues.

Frontmatter node-path field set defined per-type in
``NODE_PATH_FRONTMATTER_FIELDS`` — kept here as a module-level
constant rather than reading a schema annotation at runtime; short
and stable enough that the simplicity wins.

Origin: foundational design from the initial commit (``af5f789``;
listed as check #7 in the original validate.py docstring — "Internal
link resolution (reports broken-link registry as backlog)"). The
metadata-only design was load-bearing from day one because the
toolkit's own structure requires inter-node references that may
point to unbuilt nodes. Erroring on unbuilt references would force
either:

  - Pre-building every referenced stub before its referer (violates
    the one-node-per-session hard rule established by
    ``meta/toolkit-notes/pilot-failure-2026-04-17.md``)
  - Stubbing references in node prose (breaks the cross-reference
    graph integrity that ``stub_linking`` and the broken-link
    registry depend on)

Neither is acceptable. The registry IS the Priority Build Queue
surface — per ``CLAUDE.md``, "the broken-link list ... is the
Priority-Build-Queue signal and grows by design as new nodes
reference not-yet-built targets." A clean repo runs at 0 errors /
0 warnings AND a non-zero broken-link count.

Migration: pre-C11 each per-node validate call returned
``(issues, broken)`` as a tuple; the orchestrator collected the
``broken`` sets into a top-level registry. Commit ``60bb88d`` (C11
session 3) refactored to write directly into ``ctx.broken_links`` —
a defaultdict(set) on BaseContext keyed by link path with value =
set of referring node paths — explicitly carving out the "metadata
channel, no Issues" contract per the C11 design doc Q2. C18
confirmed byte-identity through the channel-shape change.
"""

import re
from pathlib import Path

# No Issue import — this check yields zero Issues by design. Provenance
# of broken links is carried in ctx.broken_links (defaultdict(set)).


CHECK_NAME = "link_resolution"


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_LINK_PATTERN = re.compile(r"\[`(/[^`]+)`\]")

# Frontmatter fields that carry node-path semantics. When set on a node
# of the listed type, the value is checked for target existence the
# same way body ``[`/path`]`` links are. Promote to schema-driven if
# the list grows past ~5 fields.
_NODE_PATH_FRONTMATTER_FIELDS = {
    "media":      ["derivation_of"],   # parent media node
    "transcript": ["derived_from"],    # underlying media or document node
}


def _extract_links(text):
    return set(_LINK_PATTERN.findall(text))


def check(ctx):
    """Walk body links + frontmatter node-path pointers; record any
    unresolved targets in ``ctx.broken_links`` keyed by link path with
    the node's relative path appended to the set of referers. Yields
    no Issues (link resolution is metadata, not a violation)."""
    links = _extract_links(ctx.text)
    for field in _NODE_PATH_FRONTMATTER_FIELDS.get(ctx.node_type, []):
        value = ctx.fm.get(field)
        if value:
            # Normalize to leading-slash form so the registry key shape
            # matches body-link entries. Accept both "/type/slug" and
            # "type/slug" on input.
            links.add("/" + str(value).lstrip("/"))

    rel_str = str(ctx.rel)
    for link in links:
        target = _REPO_ROOT / link.lstrip("/")
        target_md = target.with_suffix(".md") if not target.suffix else target
        if not target_md.exists() and not target.exists():
            ctx.broken_links[link].add(rel_str)
    return []  # link resolution yields no Issues by design (out-of-band metadata)
