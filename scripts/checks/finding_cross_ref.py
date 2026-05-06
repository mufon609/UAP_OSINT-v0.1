"""finding-cross-ref check — per-node NodeContext check.

Verifies that every entity listed in a finding node's ``entities``
frontmatter list links back to the finding from its own body. Warns
on missing back-links (not an error — broken back-links are a
finding-author hygiene issue, not a structural validation failure;
if a back-link is genuinely needed, the contributor adds a wrap to
the finding's path).

No-ops on non-finding node types.

Origin: foundational from the initial commit (``af5f789``); listed
as check #10 in the original validate.py docstring ("Finding cross-
reference consistency (entities listed must link back)"). The check
was designed alongside the schema's ``finding`` type and codified
the bidirectional-link convention from day one — every finding's
entities[] list is matched by a wrap-link from each cited entity
back to the finding.

Currently dormant. The finding type has zero corpus instances
(F.7 finding renderer is the last unbuilt phase per
``meta/roadmap.md``); the check no-ops on every node currently in
the build state. When F.7 ships and the first finding node lands,
this check activates with the convention pre-established.

Anchor pattern: forward-defensive foundational ("designed but
dormant"). Distinct from stable/stable foundationals
(frontmatter_required, id_path_match) because the discipline
around the check hasn't been exercised yet — there's no
contributor-practice evolution yet; the convention exists pre-
corpus.

Severity is WARN, not error, because bidirectional links are
encouraged by ``meta/conventions.md`` "Finding nodes" but not
strictly required by the convention. Finding-author judgment
applies; the check surfaces missing links without blocking.

Pending rename per BACKLOG A4: the ``finding`` type will be
renamed to ``investigation`` in a future session. This check's
``if ctx.node_type != "finding"`` guard is among the 8 scripts
listed in A4 that need updating when the rename ships. Mechanical
rename; behavior unchanged.

Migration: ``60bb88d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the migration despite zero
corpus exercise.
"""

from pathlib import Path

from checks import Issue


CHECK_NAME = "finding_cross_ref"


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def check(ctx):
    if ctx.node_type != "finding":
        return
    entities = ctx.fm.get("entities") or []
    if not isinstance(entities, list):
        return
    fid = ctx.fm.get("id", "")
    if not fid:
        return
    for entity in entities:
        ep = _REPO_ROOT / entity.lstrip("/")
        ep_md = ep.with_suffix(".md") if not ep.suffix else ep
        if not ep_md.exists():
            continue
        entity_text = ep_md.read_text()
        if f"/{fid}" not in entity_text:
            yield Issue(
                ctx.rel, "warn",
                f"Entity {entity} does not link back to this finding",
                check_name=CHECK_NAME,
            )
