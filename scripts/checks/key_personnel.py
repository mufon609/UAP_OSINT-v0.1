"""key-personnel check — type-conditional research-artifact check.

Present on organization artifacts. Each entry: required {person_path,
role, source}, optional {period_start, period_end, leadership_class,
flagged, note}.

CLOSED ``leadership_class`` enum {director, deputy, staff, advisor,
other} drives renderer sub-grouping in the Key Personnel section
(Directors / Deputy Leadership / Other Named Personnel buckets).
The field is OPTIONAL — entries without it fall through to "Other
Named Personnel" per the schema; only invalid VALUES error. This
softer optional-with-fallback design (vs ``participants.capacity``,
which is required) fits the mixed corpus where many personnel
entries are documented from sources that don't specify hierarchical
role.

``role`` is free-text. Same pattern as ``affiliations.role`` —
free-text role descriptions accommodate org-specific titles
("Founding Director", "Acting Deputy Secretary", "Director, Office
of Naval Intelligence") that no closed enum could cleanly capture.

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


CHECK_NAME = "key_personnel"


def check(ctx):
    if not section_in_scope(ctx, "key_personnel"):
        return
    if "key_personnel" not in ctx.data:
        return

    valid_leadership_class = ctx.schema["types"]["research-artifact"][
        "key_personnel_entry"]["leadership_class_values"]

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
        if lc is not None and lc not in valid_leadership_class:
            yield Issue(
                ctx.rel, "error",
                f"key_personnel[{i}] ({e.get('id')!r}): "
                f"leadership_class {lc!r} not in {sorted(valid_leadership_class)}",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "key_personnel", i, ctx.manifest_paths, CHECK_NAME,
        )
