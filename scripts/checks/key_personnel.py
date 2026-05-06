"""key-personnel check — type-conditional research-artifact check.

Present on organization artifacts. Each entry: required {person_path,
role, source}, optional {period_start, period_end, leadership_class,
flagged, note}.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``8d377c0`` (F.5a — "schema + template
+ validator + scaffolder for organization renderer"). Same anchor
as ``contracts`` and ``org_relationships``; all three are F.5
organization-renderer-coupled entry-list checks.

CLOSED ``leadership_class`` enum {director, deputy, staff, advisor,
other} drives renderer sub-grouping in the Key Personnel section:
Directors / Deputy Leadership / Other Named Personnel buckets. Same
sub-grouping pattern as ``participants.capacity`` (events) — the
enum value mechanically routes the entry to its rendering subsection.

Distinct from participants.capacity in optionality: leadership_class
is OPTIONAL on entries (entries without it fall through to "Other
Named Personnel" bucket per the schema). Only INVALID values error;
absence is the graceful default. participants.capacity is
required (no graceful default; missing capacity is an error). The
softer optional-with-fallback design fits key_personnel's mixed
corpus — many personnel entries are documented from sources that
don't specify hierarchical role, so requiring leadership_class
would force contributor speculation.

``role`` is free-text (not enum). Same pattern as
``affiliations.role`` — free-text role descriptions allow the
diversity of org-specific titles ("Founding Director", "Acting
Deputy Secretary", "Director, Office of Naval Intelligence") that
no closed enum could cleanly capture.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the lift.
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
