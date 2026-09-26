"""link-resolution check — per-node NodeContext check (metadata-only).

Walks ``[`/path`]`` body links + frontmatter node-path pointers
(``media.derivation_of``, ``transcript.derived_from``) and records
any that don't resolve to an existing repo file in
``ctx.broken_links`` — the out-of-band metadata channel on
BaseContext.

This check is the ONE deliberate exception to the "checks yield
Issues" contract: broken stubs are backlog signal, not violations,
and intentionally do not fail commits. The orchestrator reads
``ctx.broken_links`` after all per-node checks complete and prints
the registry; broken links never appear as Issues.

The metadata-only design is load-bearing because the toolkit
requires inter-node references to unbuilt nodes — the registry IS
the Priority Build Queue surface (per CLAUDE.md, "the broken-link
list ... is the Priority-Build-Queue signal and grows by design as
new nodes reference not-yet-built targets"). A clean repo runs at
0 errors / 0 warnings AND a non-zero broken-link count.

Erroring on unbuilt references would force either pre-building every
stub before its referer (violates the one-new-person-or-organization-
node-per-session rule when the stub is a person or org, which is the
common case) or stubbing references in prose (breaks the cross-
reference graph the registry depends on).

The frontmatter pointer map is ``lib._common.NODE_PATH_FRONTMATTER_FIELDS``
(shared with associate.py); promote to schema-driven if it grows past ~5
fields.
"""

import re
from pathlib import Path

from lib._common import frontmatter_node_paths

# No Issue import — this check yields zero Issues by design. Provenance
# of broken links is carried in ctx.broken_links (defaultdict(set)).


CHECK_NAME = "link_resolution"


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_LINK_PATTERN = re.compile(r"\[`(/[^`]+)`\]")


def _extract_links(text):
    return set(_LINK_PATTERN.findall(text))


def check(ctx):
    """Walk body links + frontmatter node-path pointers; record any
    unresolved targets in ``ctx.broken_links`` keyed by link path with
    the node's relative path appended to the set of referers. Yields
    no Issues (link resolution is metadata, not a violation)."""
    links = _extract_links(ctx.text)
    # Frontmatter pointers, normalized to leading-slash form so the
    # registry key shape matches body-link entries.
    links.update(frontmatter_node_paths(ctx.node_type, ctx.fm))

    rel_str = str(ctx.rel)
    for link in links:
        target = _REPO_ROOT / link.lstrip("/")
        target_md = target.with_suffix(".md") if not target.suffix else target
        if not target_md.exists() and not target.exists():
            ctx.broken_links[link].add(rel_str)
    return []  # link resolution yields no Issues by design (out-of-band metadata)
