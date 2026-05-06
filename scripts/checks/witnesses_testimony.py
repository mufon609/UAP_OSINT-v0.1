"""witnesses-testimony check — kind-conditional research-artifact check.

Present on hearing-kind event artifacts. Cross-reference table mapping
witnesses to their oath status + transcript / written testimony nodes.
Each entry: required {witness_path, oath_status, source}, optional
{transcript_node, written_testimony_node, note}.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
)


CHECK_NAME = "witnesses_testimony"

VALID_OATH_STATUS = {"sworn", "unsworn", "affirmation", "unknown"}


def check(ctx):
    if ctx.target_type is None:
        return
    expected = ctx.target_type == "event" and ctx.target_kind == "hearing"
    if not expected:
        if "witnesses_testimony" in ctx.data:
            yield Issue(
                ctx.rel, "error",
                f"'witnesses_testimony' section should not be present "
                f"(belongs only on hearing-kind event artifacts)",
                check_name=CHECK_NAME,
            )
        return
    if "witnesses_testimony" not in ctx.data:
        yield Issue(
            ctx.rel, "error",
            f"Required 'witnesses_testimony' section missing "
            f"(target event kind is 'hearing', which requires it)",
            check_name=CHECK_NAME,
        )
        return

    items = entries(ctx.data, "witnesses_testimony")
    yield from check_unique_ids(ctx.rel, items, "witnesses_testimony", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "witnesses_testimony", i, CHECK_NAME)
        for field in ("witness_path", "oath_status"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"witnesses_testimony[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        wp = e.get("witness_path")
        if wp and not wp.startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"witnesses_testimony[{i}] ({e.get('id')!r}): "
                f"witness_path {wp!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        oath = e.get("oath_status")
        if oath and oath not in VALID_OATH_STATUS:
            yield Issue(
                ctx.rel, "error",
                f"witnesses_testimony[{i}] ({e.get('id')!r}): "
                f"oath_status {oath!r} not in {sorted(VALID_OATH_STATUS)}",
                check_name=CHECK_NAME,
            )
        for optional_path_field in ("transcript_node", "written_testimony_node"):
            v = e.get(optional_path_field)
            if v and not v.startswith("/"):
                yield Issue(
                    ctx.rel, "error",
                    f"witnesses_testimony[{i}] ({e.get('id')!r}): "
                    f"{optional_path_field} {v!r} must start with '/'",
                    check_name=CHECK_NAME,
                )
        yield from require_source_dict(
            ctx.rel, e, "witnesses_testimony", i, ctx.manifest_paths, CHECK_NAME,
        )
