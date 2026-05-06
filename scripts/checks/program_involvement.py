"""program-involvement check — archetype-conditional research-artifact check.

Present on institutional-actor person artifacts. Each entry: required
{program, role, evidentiary_basis, confidence, source}, optional
{start_date, end_date, note}.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.

Origin: introduced at commit ``8007ef1`` (F.1a — person schema under
statements-only discipline) as one of the four archetype-conditional
checks landed together (alongside corroboration_items,
publication_record, vouching_chain). Same renderer-coupled-defensive
shape; same F.1a anchor.

Closed enums shared with ``vouching_chain``:

  - ``evidentiary_basis``: {primary-source, sworn-testimony,
    on-record, self-attested, secondary} — classifies how the
    contributor knows about the program involvement
  - ``confidence``: {high, medium, low} — contributor's evidentiary
    confidence in the involvement record

The shared vocabulary represents the toolkit's common evidentiary-
quality classification across credibility-attestation cross-
references (program_involvement on institutional-actors;
vouching_chain on whistleblowers).

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


CHECK_NAME = "program_involvement"


def check(ctx):
    if not section_in_scope(ctx, "program_involvement"):
        return
    if "program_involvement" not in ctx.data:
        return

    # ``evidentiary_basis_values`` and ``confidence_values`` are
    # research-artifact-level shared classifications (also consumed by
    # vouching_chain).
    research_artifact = ctx.schema["types"]["research-artifact"]
    valid_evidentiary_basis = research_artifact["evidentiary_basis_values"]
    valid_confidence = research_artifact["confidence_values"]

    items = entries(ctx.data, "program_involvement")
    yield from check_unique_ids(ctx.rel, items, "program_involvement", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "program_involvement", i, CHECK_NAME)
        for field in ("program", "role", "evidentiary_basis", "confidence"):
            if field not in e:
                yield Issue(
                    ctx.rel, "error",
                    f"program_involvement[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        eb = e.get("evidentiary_basis")
        if eb and eb not in valid_evidentiary_basis:
            yield Issue(
                ctx.rel, "error",
                f"program_involvement[{i}] ({e.get('id')!r}): "
                f"evidentiary_basis {eb!r} not in {sorted(valid_evidentiary_basis)}",
                check_name=CHECK_NAME,
            )
        conf = e.get("confidence")
        if conf and conf not in valid_confidence:
            yield Issue(
                ctx.rel, "error",
                f"program_involvement[{i}] ({e.get('id')!r}): "
                f"confidence {conf!r} not in {sorted(valid_confidence)}",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "program_involvement", i, ctx.manifest_paths, CHECK_NAME,
        )
