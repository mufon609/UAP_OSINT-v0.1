"""rumors check — type-conditional research-artifact check.

Required on person / organization / event / location artifacts (the
fabrication-prevention catalogue of widely-circulated claims lacking
primary-source backing). Absent on other types.

Gating delegated to ``section_in_scope`` (schema-driven, reads
``conditional_keys`` from ``schema.yaml``); placement errors come
from ``iff_section``. This check focuses on per-entry validation
when the section is in scope and present.

Origin: foundational from the initial commit (``af5f789``). The
fabrication-prevention catalogue role was load-bearing from day one
— rumors are artifact-only investigator memory: contributors record
widely-circulated claims lacking primary-source backing so a future
session doesn't unconsciously recirculate them into node prose
(per the schema's ``rumor_entry`` doc-block).

Refinement at ``e44a8e2`` (2026-04-21 architectural-correction
wave): three coordinated changes split the rumors mechanism's
visibility:

  1. Status enum trimmed 3 → 2. Dropped ``primary-source-identified``
     (never used — when a rumor graduates to confirmed it becomes a
     quote and the rumor entry is deleted, never transitioning
     through an "identified" intermediate state). Two values remain:
     ``not-primary-source-established`` (write-time discipline only)
     and ``primary-source-disputed`` (primary sources actively
     refute the circulating claim — analytically significant).
  2. Schema rumor_entry.optional dropped ``primary_source_search``
     (orphan lead-tracking from the pre-Open-Questions era).
  3. Renderer added ``render_primary_source_contradictions()`` —
     disputed rumors now render as a visible
     ``## Primary-Source Contradictions`` section on person /
     organization / event / location node bodies. The
     not-established status stays invisible (write-time discipline
     only); only the actively-refuted-by-primary-source category
     surfaces to readers.

Anchor pattern: stable-check / refinement-and-renderer-surface.
Distinct from naming_quirks (stable check / evolving discipline via
incidents, no schema change) and from the multi-stage shapes
(quotes, entities, artifact_top_level, cross_refs) which had more
substantial check-shape evolution. Here the check shape stayed
simple while one schema enum value + one optional field were
dropped, and the renderer gained a read-time surface.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the migration despite the
e44a8e2 enum reduction.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    section_in_scope,
)


CHECK_NAME = "rumors"

VALID_STATUSES = {"not-primary-source-established", "primary-source-disputed"}


def check(ctx):
    if not section_in_scope(ctx, "rumors"):
        return  # iff_section handled placement; skip per-entry validation
    if "rumors" not in ctx.data:
        return  # iff_section emitted "required missing"; nothing to validate

    items = entries(ctx.data, "rumors")
    yield from check_unique_ids(ctx.rel, items, "rumors", CHECK_NAME)
    for i, r in enumerate(items):
        if not isinstance(r, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, r, "rumors", i, CHECK_NAME)
        if "claim" not in r:
            yield Issue(
                ctx.rel, "error",
                f"rumors[{i}] ({r.get('id')!r}): missing required 'claim'",
                check_name=CHECK_NAME,
            )
        status = r.get("status")
        if status is None:
            yield Issue(
                ctx.rel, "error",
                f"rumors[{i}] ({r.get('id')!r}): missing required 'status'",
                check_name=CHECK_NAME,
            )
        elif status not in VALID_STATUSES:
            yield Issue(
                ctx.rel, "error",
                f"rumors[{i}] ({r.get('id')!r}): status {status!r} "
                f"not in {sorted(VALID_STATUSES)}",
                check_name=CHECK_NAME,
            )
