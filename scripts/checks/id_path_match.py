"""id-path-match check — per-node NodeContext check.

Verifies the frontmatter ``id`` field matches the node's file path
(stripped of the ``.md`` suffix). The ``id`` field is the canonical
slug-of-record across cross-references; drift between id and path
produces broken navigation between linked nodes.

Absent id is handled by frontmatter_required; this check no-ops when
``id`` isn't set.

Lift from validate.py validate_node (C11 session-3 migration).
"""

from checks import Issue


CHECK_NAME = "id_path_match"


def check(ctx):
    expected_id = str(ctx.rel).removesuffix(".md")
    fm_id = ctx.fm.get("id")
    if fm_id and fm_id != expected_id:
        yield Issue(
            ctx.rel, "error",
            f"Frontmatter id '{fm_id}' does not match path '{expected_id}'",
            check_name=CHECK_NAME,
        )
