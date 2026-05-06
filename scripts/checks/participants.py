"""participants check — type-conditional research-artifact check.

Present on event artifacts (both kinds). Each entry: required
{participant_path, capacity, source}, optional {role, flagged, note}.
``capacity`` drives sub-section routing on hearing-kind events.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
    section_in_scope,
)


CHECK_NAME = "participants"

VALID_CAPACITY = {
    "witness-eyewitness", "witness-whistleblower", "witness-institutional",
    "committee-member", "observer", "official", "other",
}


def check(ctx):
    if not section_in_scope(ctx, "participants"):
        return
    if "participants" not in ctx.data:
        return

    items = entries(ctx.data, "participants")
    yield from check_unique_ids(ctx.rel, items, "participants", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "participants", i, CHECK_NAME)
        for field in ("participant_path", "capacity"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"participants[{i}] ({e.get('id')!r}): missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        pp = e.get("participant_path")
        if pp and not pp.startswith("/"):
            yield Issue(
                ctx.rel, "error",
                f"participants[{i}] ({e.get('id')!r}): "
                f"participant_path {pp!r} must start with '/'",
                check_name=CHECK_NAME,
            )
        cap = e.get("capacity")
        if cap and cap not in VALID_CAPACITY:
            yield Issue(
                ctx.rel, "error",
                f"participants[{i}] ({e.get('id')!r}): "
                f"capacity {cap!r} not in {sorted(VALID_CAPACITY)}",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "participants", i, ctx.manifest_paths, CHECK_NAME,
        )
