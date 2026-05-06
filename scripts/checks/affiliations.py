"""affiliations check — type-conditional research-artifact check.

Present on person artifacts. Each entry: required {organization_path,
role, source}, optional {period_start, period_end, flagged, note}.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``. Entry-shape validation delegates to
the ``_research_utils`` helpers that the full 18-check entry-list
family shares (check_unique_ids / check_lifecycle_fields /
require_source_dict).

Origin: commit ``491e6f3`` (F.1b — person renderer + five person-
required artifact keys) introduced ``affiliations[]`` as a structured
artifact field paired with the new person renderer, which emits the
Affiliations table with Confirmed/Flagged split sorted by
``period_start``. Free-prose affiliations couldn't drive that table
mechanically. F.1b extended the D.4-era entry-list pattern (already
covering corroboration_items / program_involvement /
publication_record / vouching_chain) to affiliations + relationships;
later F.X work extended it further to participants /
witnesses_testimony / speakers / media_versioning / key_personnel /
org_relationships / contracts / ownership_timeline /
uap_scope_activity / location_relationships. Migration: commit
``00a985d`` (C11 session 3) lifted to per-module shape; commit
``dc95d39`` (C15) wired the schema-driven section gate via
``section_in_scope``. C18 confirmed byte-identity through both.

Note: ``period_start`` / ``period_end`` format isn't validated at
this layer. Date parsing happens at render time
(``build-from-research.py::parse_date_tuple``), where malformed values
fall through to the 9999 end-of-time sentinel and sort last rather
than crash the renderer. Layering by design — entry-list checks
enforce shape; renderer handles temporal semantics.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
    section_in_scope,
)


CHECK_NAME = "affiliations"


def check(ctx):
    if not section_in_scope(ctx, "affiliations"):
        return
    if "affiliations" not in ctx.data:
        return

    items = entries(ctx.data, "affiliations")
    yield from check_unique_ids(ctx.rel, items, "affiliations", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "affiliations", i, CHECK_NAME)
        for field in ("organization_path", "role"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"affiliations[{i}] ({e.get('id')!r}): missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        op = e.get("organization_path")
        if op and not op.startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"affiliations[{i}] ({e.get('id')!r}): "
                f"organization_path {op!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "affiliations", i, ctx.manifest_paths, CHECK_NAME,
        )
