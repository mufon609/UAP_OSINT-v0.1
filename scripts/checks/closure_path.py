"""closure_path check — investigation-only research-artifact check.

Validates the entry shape of `closure_path[]` on investigation
artifacts. Each entry requires lifecycle fields (id, added_date) +
a non-empty `blocking_event` describing what external event would
unblock the investigation. `expected_unblock_path` is optional
speculation-tolerant prose describing the unblock pathway.

Separate from ``investigation_closure_path_when_paused``, which
enforces non-empty list when status==paused — this check verifies
the per-entry shape regardless of list length.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    section_in_scope,
)


CHECK_NAME = "closure_path"


def check(ctx):
    if not section_in_scope(ctx, "closure_path"):
        return
    if "closure_path" not in ctx.data:
        return

    items = entries(ctx.data, "closure_path")
    yield from check_unique_ids(ctx.rel, items, "closure_path", CHECK_NAME)
    for i, c in enumerate(items):
        if not isinstance(c, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, c, "closure_path", i, CHECK_NAME)
        if not (c.get("blocking_event") or "").strip():
            yield Issue(
                ctx.rel, "error",
                f"closure_path[{i}] ({c.get('id')!r}): missing required "
                f"'blocking_event' (description of what external event "
                f"would unblock the investigation)",
                check_name=CHECK_NAME,
            )
