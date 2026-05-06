"""key-personnel check — type-conditional research-artifact check.

Present on organization artifacts. Each entry: required {person_path,
role, source}, optional {period_start, period_end, leadership_class,
flagged, note}.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
)


CHECK_NAME = "key_personnel"

VALID_LEADERSHIP_CLASS = {"director", "deputy", "staff", "advisor", "other"}


def check(ctx):
    if ctx.target_type is None:
        return
    if ctx.target_type != "organization":
        if "key_personnel" in ctx.data:
            yield Issue(
                ctx.rel, "error",
                f"'key_personnel' key should not be present "
                f"(target_node type {ctx.target_type!r} is not organization)",
                check_name=CHECK_NAME,
            )
        return
    if "key_personnel" not in ctx.data:
        yield Issue(
            ctx.rel, "error",
            f"Required 'key_personnel' key missing "
            f"(organization artifacts require it)",
            check_name=CHECK_NAME,
        )
        return

    items = entries(ctx.data, "key_personnel")
    yield from check_unique_ids(ctx.rel, items, "key_personnel", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "key_personnel", i, CHECK_NAME)
        for field in ("person_path", "role"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"key_personnel[{i}] ({e.get('id')!r}): missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        pp = e.get("person_path")
        if pp and not pp.startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"key_personnel[{i}] ({e.get('id')!r}): "
                f"person_path {pp!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        lc = e.get("leadership_class")
        if lc is not None and lc not in VALID_LEADERSHIP_CLASS:
            yield Issue(
                ctx.rel, "error",
                f"key_personnel[{i}] ({e.get('id')!r}): "
                f"leadership_class {lc!r} not in {sorted(VALID_LEADERSHIP_CLASS)}",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "key_personnel", i, ctx.manifest_paths, CHECK_NAME,
        )
