"""program-involvement check — archetype-conditional research-artifact check.

Present on institutional-actor person artifacts. Each entry: required
{program, role, evidentiary_basis, confidence, source}, optional
{start_date, end_date, note}.

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


CHECK_NAME = "program_involvement"

VALID_EVIDENTIARY_BASIS = {
    "primary-source", "sworn-testimony", "on-record", "self-attested", "secondary",
}
VALID_CONFIDENCE = {"high", "medium", "low"}


def check(ctx):
    if not section_in_scope(ctx, "program_involvement"):
        return
    if "program_involvement" not in ctx.data:
        return

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
        if eb and eb not in VALID_EVIDENTIARY_BASIS:
            yield Issue(
                ctx.rel, "error",
                f"program_involvement[{i}] ({e.get('id')!r}): "
                f"evidentiary_basis {eb!r} not in {sorted(VALID_EVIDENTIARY_BASIS)}",
                check_name=CHECK_NAME,
            )
        conf = e.get("confidence")
        if conf and conf not in VALID_CONFIDENCE:
            yield Issue(
                ctx.rel, "error",
                f"program_involvement[{i}] ({e.get('id')!r}): "
                f"confidence {conf!r} not in {sorted(VALID_CONFIDENCE)}",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "program_involvement", i, ctx.manifest_paths, CHECK_NAME,
        )
