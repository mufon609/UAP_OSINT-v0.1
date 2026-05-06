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

Lift from validate.py validate_node (C11 session-3 migration). Carries
the small ``_extract_links`` helper (only consumer was this walker).
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
