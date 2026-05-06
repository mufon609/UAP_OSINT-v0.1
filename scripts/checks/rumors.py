"""rumors check — type-conditional research-artifact check.

Required on person / organization / event / location artifacts (the
fabrication-prevention catalogue of widely-circulated claims lacking
primary-source backing). Absent on other types.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
)


CHECK_NAME = "rumors"

RUMORS_TYPES = {"person", "organization", "event", "location"}
VALID_STATUSES = {"not-primary-source-established", "primary-source-disputed"}


def check(ctx):
    if ctx.target_type is None:
        return
    in_scope = ctx.target_type in RUMORS_TYPES
    if not in_scope:
        if "rumors" in ctx.data:
            yield Issue(
                ctx.rel, "error",
                f"'rumors' section should not be present "
                f"(target_node type {ctx.target_type!r} does not carry rumors)",
                check_name=CHECK_NAME,
            )
        return
    if "rumors" not in ctx.data:
        yield Issue(
            ctx.rel, "error",
            f"Required 'rumors' section missing "
            f"(target_node type is {ctx.target_type!r}, which requires rumors)",
            check_name=CHECK_NAME,
        )
        return

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
