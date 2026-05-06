"""affiliations check — type-conditional research-artifact check.

Present on person artifacts. Each entry: required {organization_path,
role, source}, optional {period_start, period_end, flagged, note}.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
)


CHECK_NAME = "affiliations"


def check(ctx):
    if ctx.target_type is None:
        return
    if ctx.target_type != "person":
        if "affiliations" in ctx.data:
            yield Issue(
                ctx.rel, "error",
                f"'affiliations' key should not be present "
                f"(target_node type {ctx.target_type!r} is not person)",
                check_name=CHECK_NAME,
            )
        return
    if "affiliations" not in ctx.data:
        yield Issue(
            ctx.rel, "error",
            f"Required 'affiliations' key missing "
            f"(person artifacts require it)",
            check_name=CHECK_NAME,
        )
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
