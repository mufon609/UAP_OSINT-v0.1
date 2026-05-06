"""corroboration-items check — archetype/kind-conditional research-artifact check.

Present on eyewitness person artifacts (other observers of events the
person witnessed) OR encounter event artifacts (observers of this
encounter). Absent on other archetypes / kinds — emit error if present
elsewhere unless the artifact is shared between the two valid contexts.

Each entry: required {observer_path, observation_type, source},
optional {observed_event_ref, note}.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
)


CHECK_NAME = "corroboration_items"

VALID_OBSERVATION_TYPES = {
    "testimonial", "instrumented", "government-statement", "documentary",
}


def _expected(ctx):
    """corroboration_items required iff:
      - person artifact with archetype eyewitness, OR
      - event artifact with kind encounter."""
    if ctx.target_type == "person" and ctx.target_archetype == "eyewitness":
        return True
    if ctx.target_type == "event" and ctx.target_kind == "encounter":
        return True
    return False


def check(ctx):
    if ctx.target_type is None:
        return
    expected = _expected(ctx)
    if not expected:
        if "corroboration_items" in ctx.data:
            yield Issue(
                ctx.rel, "error",
                f"'corroboration_items' section should not be present "
                f"(present only on eyewitness person artifacts and "
                f"encounter event artifacts)",
                check_name=CHECK_NAME,
            )
        return
    if "corroboration_items" not in ctx.data:
        yield Issue(
            ctx.rel, "error",
            f"Required 'corroboration_items' section missing "
            f"(target context requires it)",
            check_name=CHECK_NAME,
        )
        return

    items = entries(ctx.data, "corroboration_items")
    yield from check_unique_ids(ctx.rel, items, "corroboration_items", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "corroboration_items", i, CHECK_NAME)
        for field in ("observer_path", "observation_type"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"corroboration_items[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        ot = e.get("observation_type")
        if ot and ot not in VALID_OBSERVATION_TYPES:
            yield Issue(
                ctx.rel, "error",
                f"corroboration_items[{i}] ({e.get('id')!r}): "
                f"observation_type {ot!r} not in {sorted(VALID_OBSERVATION_TYPES)}",
                check_name=CHECK_NAME,
            )
        op = e.get("observer_path")
        if op and not op.startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"corroboration_items[{i}] ({e.get('id')!r}): "
                f"observer_path {op!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "corroboration_items", i, ctx.manifest_paths, CHECK_NAME,
        )
