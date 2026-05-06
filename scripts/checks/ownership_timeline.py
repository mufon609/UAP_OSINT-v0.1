"""ownership-timeline check — type-conditional research-artifact check.

Present on location artifacts. Chronological ownership-transition
record. Each entry: required {period_start, owner, use_status,
source}, optional {period_end, owner_path, note}.

Layered date discipline:

  - Shape only here (period_start required, owner / use_status
    required as non-empty strings). Period FORMAT is not validated
    at this layer.
  - Format validation deferred to the renderer's ``parse_date_tuple``
    (malformed dates fall through to the 9999 end-of-time sentinel
    rather than crashing the renderer).
  - Chronological ordering enforced downstream by the
    ``chronological_tables`` NodeContext check, which walks the
    rendered table after build-from-research.py emits it. The
    rendered table inherits the artifact's entry order; contributors
    are responsible for chronological ordering at the artifact layer.

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
