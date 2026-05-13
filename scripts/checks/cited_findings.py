"""cited_findings check — investigation-only research-artifact check.

Validates the entry shape of `cited_findings[]` on investigation
artifacts. Each entry requires lifecycle fields (id, added_date) +
`finding_path` (a /findings/... path) + `relevance` (contributor-
written prose describing how the finding bears on the investigation).
`pattern_statement` is optional — renderer auto-fills from the
target finding's own pattern_statement when omitted.

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


CHECK_NAME = "cited_findings"


def check(ctx):
    if not section_in_scope(ctx, "cited_findings"):
        return
    if "cited_findings" not in ctx.data:
        return

    items = entries(ctx.data, "cited_findings")
    yield from check_unique_ids(ctx.rel, items, "cited_findings", CHECK_NAME)
    for i, c in enumerate(items):
        if not isinstance(c, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, c, "cited_findings", i, CHECK_NAME)
        finding_path = (c.get("finding_path") or "").strip()
        if not finding_path:
            yield Issue(
                ctx.rel, "error",
                f"cited_findings[{i}] ({c.get('id')!r}): missing required "
                f"'finding_path' (must be a /findings/... path)",
                check_name=CHECK_NAME,
            )
        elif not finding_path.startswith("/findings/"):
            yield Issue(
                ctx.rel, "error",
                f"cited_findings[{i}] ({c.get('id')!r}): finding_path "
                f"{finding_path!r} must start with '/findings/'",
                check_name=CHECK_NAME,
            )
        if not (c.get("relevance") or "").strip():
            yield Issue(
                ctx.rel, "error",
                f"cited_findings[{i}] ({c.get('id')!r}): missing required "
                f"'relevance' (1-2 sentence prose describing how this "
                f"finding bears on the investigation)",
                check_name=CHECK_NAME,
            )
