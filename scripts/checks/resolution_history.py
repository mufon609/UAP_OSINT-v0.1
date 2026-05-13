"""resolution_history check — investigation-only research-artifact check.

Validates the entry shape of `resolution_history[]` on investigation
artifacts. Each entry requires lifecycle fields (id, added_date) +
`date` (YYYY-MM-DD when the resolution event occurred) + `event`
(prose description of how the investigation evolved on that date).

Used for long-running investigations where evolution is itself
load-bearing — hypothesis additions, refutations, supersession.
Most investigations don't need this; renderer auto-suppresses the
section when the list is empty.

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


CHECK_NAME = "resolution_history"


def check(ctx):
    if not section_in_scope(ctx, "resolution_history"):
        return
    if "resolution_history" not in ctx.data:
        return

    items = entries(ctx.data, "resolution_history")
    yield from check_unique_ids(ctx.rel, items, "resolution_history", CHECK_NAME)
    for i, r in enumerate(items):
        if not isinstance(r, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, r, "resolution_history", i, CHECK_NAME)
        if not r.get("date"):
            yield Issue(
                ctx.rel, "error",
                f"resolution_history[{i}] ({r.get('id')!r}): missing required 'date'",
                check_name=CHECK_NAME,
            )
        if not (r.get("event") or "").strip():
            yield Issue(
                ctx.rel, "error",
                f"resolution_history[{i}] ({r.get('id')!r}): missing required "
                f"'event' (prose description of how the investigation "
                f"evolved on this date)",
                check_name=CHECK_NAME,
            )
