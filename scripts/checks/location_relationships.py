"""location-relationships check — type-conditional research-artifact check.

Present on location artifacts. Heterogeneous entity_path target
(person / organization / document / event / transcript / media /
location / finding) — locations connect to anything the primary
source attests. Each entry: required {entity_path, relationship,
source}, optional {flagged, note}.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
)


CHECK_NAME = "location_relationships"


def check(ctx):
    if ctx.target_type is None:
        return
    if ctx.target_type != "location":
        if "location_relationships" in ctx.data:
            yield Issue(
                ctx.rel, "error",
                f"'location_relationships' key should not be present "
                f"(target_node type {ctx.target_type!r} is not location)",
                check_name=CHECK_NAME,
            )
        return
    if "location_relationships" not in ctx.data:
        yield Issue(
            ctx.rel, "error",
            f"Required 'location_relationships' key missing "
            f"(location artifacts require it)",
            check_name=CHECK_NAME,
        )
        return

    items = entries(ctx.data, "location_relationships")
    yield from check_unique_ids(ctx.rel, items, "location_relationships", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "location_relationships", i, CHECK_NAME)
        for field in ("entity_path", "relationship"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"location_relationships[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        ep = e.get("entity_path")
        if ep and not str(ep).startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"location_relationships[{i}] ({e.get('id')!r}): "
                f"entity_path {ep!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "location_relationships", i, ctx.manifest_paths, CHECK_NAME,
        )
