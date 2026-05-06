"""speakers check — type-conditional research-artifact check.

Present on every transcript artifact (both kinds). Each entry:
required {name, source}, optional {role, node_link, note}.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
)


CHECK_NAME = "speakers"


def check(ctx):
    if ctx.target_type is None:
        return
    if ctx.target_type != "transcript":
        if "speakers" in ctx.data:
            yield Issue(
                ctx.rel, "error",
                f"'speakers' section should not be present "
                f"(target_node type {ctx.target_type!r} is not transcript)",
                check_name=CHECK_NAME,
            )
        return
    if "speakers" not in ctx.data:
        yield Issue(
            ctx.rel, "error",
            f"Required 'speakers' section missing "
            f"(transcript artifacts require it)",
            check_name=CHECK_NAME,
        )
        return

    items = entries(ctx.data, "speakers")
    yield from check_unique_ids(ctx.rel, items, "speakers", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "speakers", i, CHECK_NAME)
        if "name" not in e or not str(e.get("name") or "").strip():
            yield Issue(
                ctx.rel, "error",
                f"speakers[{i}] ({e.get('id')!r}): missing required 'name'",
                check_name=CHECK_NAME,
            )
        nl = e.get("node_link")
        if nl and not str(nl).startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"speakers[{i}] ({e.get('id')!r}): "
                f"node_link {nl!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "speakers", i, ctx.manifest_paths, CHECK_NAME,
        )
