"""publication-record check — archetype-conditional research-artifact check.

Present on reporter person artifacts. Each entry: required
{publication, outlet, date, source}, optional {node_link, beat, note}.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``8007ef1`` (F.1a — person schema under
statements-only discipline) as one of the four archetype-conditional
checks landed together (alongside corroboration_items,
program_involvement, vouching_chain). Same renderer-coupled-
defensive shape; same F.1a anchor.

No enums. Distinct from the three sibling F.1a archetype-conditional
checks — corroboration_items has ``observation_type`` enum,
program_involvement and vouching_chain share ``evidentiary_basis`` +
``confidence`` enums. publication_record is shape-only:
publication / outlet / date are all free-text source-attested
fields. The simplification fits the reporter archetype's role —
publications are themselves source-attested records (with their own
``date`` field carrying the publication date), so the entry shape
defers vocabulary to the publishing record itself.

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


CHECK_NAME = "publication_record"


def check(ctx):
    if not section_in_scope(ctx, "publication_record"):
        return
    if "publication_record" not in ctx.data:
        return

    items = entries(ctx.data, "publication_record")
    yield from check_unique_ids(ctx.rel, items, "publication_record", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "publication_record", i, CHECK_NAME)
        for field in ("publication", "outlet", "date"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"publication_record[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        yield from require_source_dict(
            ctx.rel, e, "publication_record", i, ctx.manifest_paths, CHECK_NAME,
        )
