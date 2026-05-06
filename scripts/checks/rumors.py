"""rumors check — type-conditional research-artifact check.

Required on person / organization / event / location artifacts (the
fabrication-prevention catalogue of widely-circulated claims lacking
primary-source backing). Absent on other types.

Gating delegated to ``section_in_scope`` (schema-driven, reads
``conditional_keys`` from ``schema.yaml``); placement errors come
from ``iff_section``. This check focuses on per-entry validation
when the section is in scope and present.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    section_in_scope,
)


CHECK_NAME = "rumors"

VALID_STATUSES = {"not-primary-source-established", "primary-source-disputed"}


def check(ctx):
    if not section_in_scope(ctx, "rumors"):
        return  # iff_section handled placement; skip per-entry validation
    if "rumors" not in ctx.data:
        return  # iff_section emitted "required missing"; nothing to validate

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
        elif status not in VALID_STATUSES:
            yield Issue(
                ctx.rel, "error",
                f"rumors[{i}] ({r.get('id')!r}): status {status!r} "
                f"not in {sorted(VALID_STATUSES)}",
                check_name=CHECK_NAME,
            )
