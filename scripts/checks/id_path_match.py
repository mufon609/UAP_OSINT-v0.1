"""id-path-match check — per-node NodeContext check.

Verifies the frontmatter ``id`` field matches the node's file path
(with the ``.md`` suffix stripped). The ``id`` field is the canonical
slug-of-record across cross-references; drift between id and path
silently breaks any link resolver that keys off either form (broken-
link registry, associate.py).

Absent id is handled by ``frontmatter_required``; this check no-ops
when ``id`` isn't set so the two checks compose without double-
reporting.

Accepted gap: nullified id (``id:`` with no value) slips through
both this check and ``frontmatter_required``, since id has no
enum-validation downstream. Tightening would be defensive coverage
of a scenario that hasn't surfaced; contributor scaffolders populate
id automatically.
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
