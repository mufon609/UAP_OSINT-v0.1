"""org-relationships check — type-conditional research-artifact check.

Org-to-org structured relationships. Present on organization artifacts.
Each entry: required {organization_path, relationship_type, source},
optional {flagged, note}.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``8d377c0`` (F.5a — "schema + template
+ validator + scaffolder for organization renderer"). Same renderer-
coupled-defensive shape as the F.1a / F.1b / F.2 / F.5 entry-list
family — entry-shape enforcement so the F.5 organization renderer
can rely on the structured data when emitting the Relationships
table.

CLOSED relationship_type enum {parent, subsidiary, predecessor,
successor, contractor, contracting-agency, partner, other} — same
pattern as ``participants.capacity`` (closed; ERROR on unknown;
``other`` is fixed miscellaneous bucket, not extensibility escape).

BACKLOG B1 cross-reference. This check is THE primary site where
the broader "table renderers drop .note across 8 list-section
entry shapes" gap surfaces in practice. Real corpus cases
documented in B1's Manifestation 1:

  - AARO ``or1`` (DoD parent) and ``or5`` (OUSD(I&S) supervisory)
    both render as bare ``parent`` relationship type with no
    visible distinction; the late-July 2023 DEPSECDEF reporting-
    line shift documented in description prose has no structural
    counterpart in the relationship table.
  - AARO AOIMSG-vs-UAPTF predecessor disambiguation: AOIMSG is the
    immediate predecessor (Hicks memo amendment); UAPTF is indirect
    (disestablished by direction in the same memo). Both render as
    bare ``predecessor`` with no distinction.
  - AARO IPMO co-location vs partner: IPMO listed as ``partner``
    (justified by Sancorp cross-contracting); five other co-located
    OUSD(I&S) offices share only co-location and have no clean
    relationship_type. Could use ``other`` + ``note`` but the note
    doesn't render.
  - UAPTF audit earlier flagged AARO-as-downstream-successor and
    EXCOM-as-oversight collapsing into bare ``other`` relationship
    type with .note carrying the disambiguation.

The check itself is doing its job (entry-shape enforcement is
correct); the gap is downstream in the renderer's table emission.
B1 schedules a coordinated renderer pass to surface ``.note``
content across all 8 affected entry shapes.

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


CHECK_NAME = "org_relationships"


def check(ctx):
    if not section_in_scope(ctx, "org_relationships"):
        return
    if "org_relationships" not in ctx.data:
        return

    valid_relationship_type = ctx.schema["types"]["research-artifact"][
        "org_relationship_entry"]["relationship_type_values"]

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
        if rt is not None and rt not in valid_relationship_type:
            yield Issue(
                ctx.rel, "error",
                f"org_relationships[{i}] ({e.get('id')!r}): "
                f"relationship_type {rt!r} not in {sorted(valid_relationship_type)}",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "org_relationships", i, ctx.manifest_paths, CHECK_NAME,
        )
