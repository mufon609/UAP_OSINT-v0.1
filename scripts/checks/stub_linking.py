"""stub-linking check — cross-layer ResearchContext check.

Verifies every ``entities_referenced[].wrap_path`` appears as a
``[`/path`]`` link in the target node's body. Skips the artifact's
own ``target_node`` (subjects don't self-wrap; their identity lives
in the node's Identity / Overview surface, not in the entities list).

Consumes ``ctx.node_text`` (set by the review-coverage orchestrator).

Origin: shipped at commit ``0a56989`` (D.4 — introduction of Phase III
review-coverage.py) as one of four mechanical checks
(Coverage / Boundary / Stub-linking / OQ dedup). The class of failure
protected against is "phantom registered entity": a contributor
adds an entity to ``entities_referenced[]`` (intentionally or as
scaffolder leftover) but the corresponding ``[`/wrap_path`]`` link
doesn't appear in the rendered node body. That breaks the cross-
reference graph integrity:

  - ``entities_referenced[].wrap_path`` drives the broken-link registry
    (validate.py surfaces unbuilt stubs as Priority Build Queue
    candidates).
  - ``[`/path`]`` markdown wraps in the node body drive
    associate.py's auto-generated Associated Nodes section.
  - The two layers must agree — a registered entity with no wrap-link
    creates a phantom registry reference that associate.py can't
    resolve.

Reactive refinement: commit ``efd4588`` ("Fix three pilot findings
surfaced during the Graves person pilot") added the self-reference
skip. Original D.4 logic fired spuriously when a contributor
included the artifact's own subject in entities_referenced[] —
person nodes don't self-wrap, so the check expected
``[`/people/ryan-graves`]`` as a wrap-link in Graves's own node body
and didn't find it. Fix: skip any entity whose wrap_path resolves
to ``ctx.data['target_node']``. Convention is unchanged (subject
isn't in entities_referenced); the fix just turns a contributor
mistake into a soft skip rather than a spurious error.

Inverse-direction limitation: the check only catches "registered but
not linked." It does NOT catch "named in prose but not registered"
— a contributor who writes ``CBS News`` in Timeline event text
without adding ``/organizations/cbs-news`` to entities_referenced[]
gets no error here. That direction is contributor discipline (see
``feedback_interview_node_entities`` for the canonical statement of
the rule); the check has no signal for entities that lack a
``wrap_path`` because they aren't registered.

Migration: ``efd4588`` (self-skip refinement) → ``363212d`` (C11
session 3 lift to per-module shape). C18 confirmed byte-identity
through the lift.
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
