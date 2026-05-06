"""rumors check — type-conditional research-artifact check.

Required on person / organization / event / location artifacts: the
fabrication-prevention catalogue of widely-circulated claims lacking
primary-source backing. Contributors record such claims so future
sessions don't unconsciously recirculate them into node prose.

Two status values:

  - ``not-primary-source-established`` — write-time discipline only;
    not rendered.
  - ``primary-source-disputed`` — primary sources actively refute the
    claim; renders as a ``## Primary-Source Contradictions`` section
    via ``build-from-research.py::render_primary_source_contradictions``.

When a rumor graduates to confirmed it becomes a quote and the rumor
entry is deleted — there's no "identified" intermediate state.

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


CHECK_NAME = "rumors"


def check(ctx):
    if not section_in_scope(ctx, "rumors"):
        return  # iff_section handled placement; skip per-entry validation
    if "rumors" not in ctx.data:
        return  # iff_section emitted "required missing"; nothing to validate

    valid_statuses = ctx.schema["types"]["research-artifact"][
        "rumor_entry"]["status_values"]

    items = entries(ctx.data, "rumors")
    yield from check_unique_ids(ctx.rel, items, "rumors", CHECK_NAME)
    for i, r in enumerate(items):
        if not isinstance(r, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, r, "rumors", i, CHECK_NAME)
        if "claim" not in r:
            yield Issue(
                ctx.rel, "error",
                f"rumors[{i}] ({r.get('id')!r}): missing required 'claim'",
                check_name=CHECK_NAME,
            )
        status = r.get("status")
        if status is None:
            yield Issue(
                ctx.rel, "error",
                f"rumors[{i}] ({r.get('id')!r}): missing required 'status'",
                check_name=CHECK_NAME,
            )
        elif status not in valid_statuses:
            yield Issue(
                ctx.rel, "error",
                f"rumors[{i}] ({r.get('id')!r}): status {status!r} "
                f"not in {sorted(valid_statuses)}",
                check_name=CHECK_NAME,
            )
