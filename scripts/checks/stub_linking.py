"""stub-linking check — cross-layer ResearchContext check.

Verifies every ``entities_referenced[].wrap_path`` appears as a
``[`/path`]`` link in the target node's body. Catches phantom
registered entities — entries in ``entities_referenced[]`` whose
``wrap_path`` doesn't appear as a wrap-link in the rendered node
body.

The cross-reference graph requires both layers to agree:
``entities_referenced[].wrap_path`` drives the broken-link registry
(unbuilt stubs become Priority Build Queue candidates), and
``[`/path`]`` wraps in the node body drive ``associate.py``'s
auto-generated Associated Nodes section.

Skips the artifact's own ``target_node`` — subjects don't self-wrap;
their identity lives in the node's Identity / Overview surface, not
in the entities list.

Inverse-direction limitation: this check only catches "registered
but not linked." It does NOT catch "named in prose but not
registered" (a contributor who writes ``CBS News`` without adding
``/organizations/cbs-news`` to entities_referenced[]). That
direction is contributor discipline — see ``meta/conventions.md``
"Cross-reference contract for interview-derived testimony" for the
registration rule that governs venues, hosts, and transcripts.

Consumes ``ctx.node_text`` set by the review-coverage orchestrator.
"""

import re

from checks import Issue


CHECK_NAME = "stub_linking"

_LINK_PATTERN = re.compile(r"\[`(/[^`]+)`\]")


def check(ctx):
    if ctx.node_text is None:
        return
    links_in_node = set(_LINK_PATTERN.findall(ctx.node_text))

    target_node = ctx.data.get("target_node") or ""
    self_path = (
        f"/{target_node}" if target_node and not target_node.startswith("/")
        else target_node
    )

    for e in ctx.data.get("entities_referenced") or []:
        if not isinstance(e, dict):
            continue
        wp = e.get("wrap_path")
        if not wp:
            continue
        if wp == self_path:
            continue  # subject of the artifact is not listed as an "other" entity
        if wp not in links_in_node:
            yield Issue(
                ctx.rel, "error",
                f"Stub-linking: entity {e.get('id')!r} ({e.get('name')!r}) "
                f"wrap_path {wp!r} does not appear as a [`{wp}`] link in the node",
                check_name=CHECK_NAME,
            )
