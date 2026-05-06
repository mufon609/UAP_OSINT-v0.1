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

Schema-validator gap (logged as BACKLOG C20, not fixed in this
investigation):

The schema declares ``timeline_category_values`` (9 canonical values:
affiliation, role, observation, testimony, publication, clearance,
incident, filing, other) with the comment "Extensible; validator
warns on unknown values but does not error." That warn behavior was
never implemented — neither at F.1a nor since. The check enforces
entry shape (date, event, source dict, manifest membership) but does
not validate category vocabulary at all. Contributors have organically
extended the vocabulary in the corpus (``contract``, ``foia``,
``certification``, ``founding``, etc.); the warn-on-unknown signal
that would surface these extensions for canonical adoption never
fired. See BACKLOG C20 for resolution paths.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the lift.

Anchor pattern: stable check / unimplemented schema-declared
behavior. Distinct from the foundational shapes investigated
previously — the discrepancy here is between schema documentation
and validator implementation, not between schema and contributor
practice. Worth recognizing as a sub-shape because resolving it
requires aligning two layers (schema comment vs check logic) rather
than tightening one.
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
