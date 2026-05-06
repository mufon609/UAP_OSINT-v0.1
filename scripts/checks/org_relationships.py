"""org-relationships check — type-conditional research-artifact check.

Org-to-org structured relationships. Present on organization artifacts.
Each entry: required {organization_path, relationship_type, source},
optional {flagged, note}.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
)


CHECK_NAME = "org_relationships"

VALID_RELATIONSHIP_TYPE = {
    "parent", "subsidiary", "predecessor", "successor",
    "contractor", "contracting-agency", "partner", "other",
}


def check(ctx):
    if ctx.target_type is None:
        return
    if ctx.target_type != "organization":
        if "org_relationships" in ctx.data:
            yield Issue(
                ctx.rel, "error",
                f"'org_relationships' key should not be present "
                f"(target_node type {ctx.target_type!r} is not organization)",
                check_name=CHECK_NAME,
            )
        return
    if "org_relationships" not in ctx.data:
        yield Issue(
            ctx.rel, "error",
            f"Required 'org_relationships' key missing "
            f"(organization artifacts require it)",
            check_name=CHECK_NAME,
        )
        return

    items = entries(ctx.data, "org_relationships")
    yield from check_unique_ids(ctx.rel, items, "org_relationships", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "org_relationships", i, CHECK_NAME)
        for field in ("organization_path", "relationship_type"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"org_relationships[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        op = e.get("organization_path")
        if op and not op.startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"org_relationships[{i}] ({e.get('id')!r}): "
                f"organization_path {op!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        rt = e.get("relationship_type")
        if rt is not None and rt not in VALID_RELATIONSHIP_TYPE:
            yield Issue(
                ctx.rel, "error",
                f"org_relationships[{i}] ({e.get('id')!r}): "
                f"relationship_type {rt!r} not in {sorted(VALID_RELATIONSHIP_TYPE)}",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "org_relationships", i, ctx.manifest_paths, CHECK_NAME,
        )
