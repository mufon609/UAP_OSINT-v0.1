"""timeline check — type-conditional research-artifact check.

Required on person / organization / event / finding artifacts. Each
entry: required {date, event, source}, optional {category, node_link,
end_date}. Absent on other types.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
)


CHECK_NAME = "timeline"

TIMELINE_TYPES = {"person", "organization", "event", "finding"}


def check(ctx):
    if ctx.target_type is None:
        return
    in_scope = ctx.target_type in TIMELINE_TYPES
    if not in_scope:
        if "timeline" in ctx.data:
            yield Issue(
                ctx.rel, "error",
                f"'timeline' section should not be present "
                f"(target_node type {ctx.target_type!r} does not carry timeline)",
                check_name=CHECK_NAME,
            )
        return
    if "timeline" not in ctx.data:
        yield Issue(
            ctx.rel, "error",
            f"Required 'timeline' section missing "
            f"(target_node type is {ctx.target_type!r}, which requires timeline)",
            check_name=CHECK_NAME,
        )
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
