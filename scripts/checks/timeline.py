"""timeline check — type-conditional research-artifact check.

Required on person / organization / event / finding artifacts. Each
entry: required {date, event, source}, optional {category, node_link,
end_date}. Absent on other types.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``8007ef1`` (F.1a — person schema under
statements-only discipline) as one of six entry-list-pattern checks
landed together (alongside chronological_tables and the four
archetype-conditional checks anchored in ``corroboration_items``).
Foundational at F.1a; check shape has stayed stable since.

The ``category`` field on entries is free-text by design. An earlier
``timeline_category_values`` schema list (9 suggested values) +
"validator warns on unknown" comment promised an enum-validation
behavior the validator never implemented. The C17 audit removed the
list as cargo-cult schema decoration: the field has always operated
as free-text, the corpus organically extended past the suggested
nine, and no tool consumed the list. Schema is now honest about the
field's role; contributors use whatever category labels fit their
entries.

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
