"""finding-cross-ref check — per-node NodeContext check.

Verifies that every entity listed in a finding node's ``entities``
frontmatter list links back to the finding from its own body. Warns
on missing back-links: bidirectional links are encouraged by
``meta/conventions.md`` "Finding nodes" but not strictly required.

Currently dormant — the finding type has zero corpus instances per
``meta/roadmap.md``. The check activates when the first finding node
lands.

No-ops on non-finding node types.
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
