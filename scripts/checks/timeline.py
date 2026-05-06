"""timeline check — type-conditional research-artifact check.

Required on person / organization / event / finding artifacts. Each
entry: required {date, event, source}, optional {category, node_link,
end_date}. Absent on other types.

The ``category`` field is free-text by design — contributors use
whatever label fits the entry; no enum is enforced at the validator
layer.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
    section_in_scope,
)


CHECK_NAME = "timeline"


def check(ctx):
    if not section_in_scope(ctx, "timeline"):
        return
    if "timeline" not in ctx.data:
        return

    items = entries(ctx.data, "timeline")
    yield from check_unique_ids(ctx.rel, items, "timeline", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "timeline", i, CHECK_NAME)
        for field in ("date", "event"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"timeline[{i}] ({e.get('id')!r}): missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        yield from require_source_dict(
            ctx.rel, e, "timeline", i, ctx.manifest_paths, CHECK_NAME,
        )
