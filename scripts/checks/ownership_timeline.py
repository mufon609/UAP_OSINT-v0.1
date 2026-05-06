"""ownership-timeline check — type-conditional research-artifact check.

Present on location artifacts. Chronological ownership-transition
record (chronological ordering enforced at node-render time by the
chronological-ordering check). Each entry: required {period_start,
owner, use_status, source}, optional {period_end, owner_path, note}.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``5a67ec1`` (F.6a — "schema +
validator + scaffolder for location-type research artifacts").
Same anchor as ``location_relationships`` and
``top_scope_activity``; F.6a added all three location-specific
structured fields together when locations gained Phase II
rendering.

Layered date discipline. This check enforces shape (period_start
required, owner / use_status required as non-empty strings) but
NOT period FORMAT or chronological ordering:

  - Format validation deferred to renderer's
    ``parse_date_tuple`` (per the affiliations docstring layering
    note): malformed dates fall through to the 9999 end-of-time
    sentinel rather than crashing the renderer.
  - Chronological ordering enforced downstream by the
    ``chronological_tables`` NodeContext check, which walks the
    rendered table after build-from-research.py emits it. The
    rendered table inherits the artifact's entry order; the
    contributor is responsible for chronological ordering at the
    artifact layer.

Period-convention pending pattern. The schema's period_start /
period_end shape is shared across four entry types
(``ownership_timeline``, ``key_personnel``, ``contracts``,
``affiliations``). All four currently support three period
shapes: ``period_start`` alone (renders "ongoing");
``period_start – period_end`` (closed period); ``– period_end``
(unknown start, known end). NO convention exists yet for
"known start, unknown end (but not ongoing)" — surfaced by the
AARO Phillips Deputy Director kp2 case (key_personnel entry where
Phillips' departure date is undocumented in archived sources but
the role is attested-vacant by later coverage). Documented as
pending-corpus-wide-convention-question in
``meta/topic/research-queue.md``; awaits a 3+ node pattern before
codifying. Affects this check whenever a location ownership has
documented start + ambiguous end-but-not-ongoing.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the lift.
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
