"""open_questions check — investigation-only research-artifact check.

Validates the entry shape of `open_questions[]` on investigation
artifacts. Each entry requires lifecycle fields (id, added_date) +
a non-empty `question` string. `what_would_resolve` is optional
contributor-written prose describing what primary-source material
would close the question — speculation-tolerant by design.

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


CHECK_NAME = "open_questions"


def check(ctx):
    if not section_in_scope(ctx, "open_questions"):
        return
    if "open_questions" not in ctx.data:
        return

    items = entries(ctx.data, "open_questions")
    yield from check_unique_ids(ctx.rel, items, "open_questions", CHECK_NAME)
    for i, q in enumerate(items):
        if not isinstance(q, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, q, "open_questions", i, CHECK_NAME)
        if not (q.get("question") or "").strip():
            yield Issue(
                ctx.rel, "error",
                f"open_questions[{i}] ({q.get('id')!r}): missing required "
                f"'question'",
                check_name=CHECK_NAME,
            )
