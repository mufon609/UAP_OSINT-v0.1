"""ownership-timeline check — type-conditional research-artifact check.

Present on location artifacts. Chronological ownership-transition
record (chronological ordering enforced at node-render time by the
chronological-ordering check). Each entry: required {period_start,
owner, use_status, source}, optional {period_end, owner_path, note}.

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


CHECK_NAME = "ownership_timeline"


def check(ctx):
    if not section_in_scope(ctx, "ownership_timeline"):
        return
    if "ownership_timeline" not in ctx.data:
        return

    items = entries(ctx.data, "ownership_timeline")
    yield from check_unique_ids(ctx.rel, items, "ownership_timeline", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "ownership_timeline", i, CHECK_NAME)
        for field in ("period_start", "owner", "use_status"):
            if field not in e or not str(e.get(field) or "").strip():
                yield Issue(
                    ctx.rel, "error",
                    f"ownership_timeline[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        op = e.get("owner_path")
        if op and not str(op).startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"ownership_timeline[{i}] ({e.get('id')!r}): "
                f"owner_path {op!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "ownership_timeline", i, ctx.manifest_paths, CHECK_NAME,
        )
