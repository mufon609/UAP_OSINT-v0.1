"""finding-cross-ref check — per-node NodeContext check.

Verifies that every entity listed in a finding node's ``entities``
frontmatter list links back to the finding from its own body. Warns
on missing back-links (not an error — broken back-links are a
finding-author hygiene issue, not a structural validation failure;
if a back-link is genuinely needed, the contributor adds a wrap to
the finding's path).

No-ops on non-finding node types.

Lift from validate.py validate_node (C11 session-3 migration).
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
