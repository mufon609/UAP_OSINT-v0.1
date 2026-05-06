"""participants check — type-conditional research-artifact check.

Present on event artifacts (both kinds). Each entry: required
{participant_path, capacity, source}, optional {role, flagged, note}.
``capacity`` drives sub-section routing on hearing-kind events.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``13a2859`` (F.2a — event schema
work); shipped alongside ``witnesses_testimony`` in the same F.2a
landing. Different scope from witnesses_testimony though:
``participants`` runs on both event kinds (encounter + hearing),
while witnesses_testimony is hearing-only. Co-introduced but serve
different audiences — participants tracks every named participant
in any documented event; witnesses_testimony tracks the witness-
to-transcript / witness-to-written-testimony cross-reference
specific to formal proceedings.

Capacity enum is CLOSED, not extensible. Distinct from
``media_versioning``'s aspect enum (extensible-with-warn-on-
unknown). The design choice is driven by renderer requirements:
``capacity`` drives mechanical sub-grouping in the F.2 hearing
renderer's Participants section — ``witness-eyewitness`` →
"Eyewitness Testimony" subsection, ``witness-whistleblower`` →
"Whistleblower Testimony" subsection, ``witness-institutional``
→ "Institutional Testimony" subsection, ``committee-member`` →
"Committee Members" subsection, etc. Unknown capacity values
can't be mechanically routed; closed enum + ERROR on unknown
fits the routing-mandate.

The ``other`` value IS in the enum as the documented
miscellaneous bucket for cases that don't fit the witness /
committee / observer / official categorization. Unlike
media_versioning's ``other`` (which is paired with warn-on-
unknown for extensibility), capacity's ``other`` is a fixed final
category — adding new capacity values requires schema +
renderer updates, not contributor extensibility.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the C11 migration.
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


def check(ctx):
    if not section_in_scope(ctx, "participants"):
        return
    if "participants" not in ctx.data:
        return

    # Schema-driven enum for ``capacity`` from
    # ``participant_entry.capacity_values``.
    valid_capacity = ctx.schema["types"]["research-artifact"][
        "participant_entry"]["capacity_values"]

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
        if cap and cap not in valid_capacity:
            yield Issue(
                ctx.rel, "error",
                f"participants[{i}] ({e.get('id')!r}): "
                f"capacity {cap!r} not in {sorted(valid_capacity)}",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "participants", i, ctx.manifest_paths, CHECK_NAME,
        )
