"""contradictions check — finding-only research-artifact check.

Validates the entry shape of `contradictions[]` on finding artifacts.
Each entry requires lifecycle fields (id, added_date) + `question`
(the specific question on which sources within this finding diverge)
+ `positions` (list of objects with shape
`{evidence_id, position}`, ≥2 entries to constitute a contradiction).
`note` is optional contributor synthesis (prose-drift-checked
against the convergent source set).

Each position's evidence_id must reference an existing quote id in
this artifact's quotes[] (cross-reference resolution).

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    section_in_scope,
)


CHECK_NAME = "contradictions"


def check(ctx):
    if not section_in_scope(ctx, "contradictions"):
        return
    if "contradictions" not in ctx.data:
        return

    items = entries(ctx.data, "contradictions")
    yield from check_unique_ids(ctx.rel, items, "contradictions", CHECK_NAME)

    # Build the set of valid quote ids in this artifact for
    # cross-reference resolution.
    quote_ids = {
        q.get("id") for q in entries(ctx.data, "quotes")
        if isinstance(q, dict) and q.get("id")
    }

    for i, c in enumerate(items):
        if not isinstance(c, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, c, "contradictions", i, CHECK_NAME)
        if not (c.get("question") or "").strip():
            yield Issue(
                ctx.rel, "error",
                f"contradictions[{i}] ({c.get('id')!r}): missing required "
                f"'question' (the specific question on which sources diverge)",
                check_name=CHECK_NAME,
            )
        positions = c.get("positions")
        if not isinstance(positions, list) or len(positions) < 2:
            yield Issue(
                ctx.rel, "error",
                f"contradictions[{i}] ({c.get('id')!r}): 'positions' must be "
                f"a list of ≥2 objects (a contradiction requires at least "
                f"two opposing positions)",
                check_name=CHECK_NAME,
            )
            continue
        for j, p in enumerate(positions):
            if not isinstance(p, dict):
                yield Issue(
                    ctx.rel, "error",
                    f"contradictions[{i}].positions[{j}]: must be a dict "
                    f"with 'evidence_id' and 'position' fields",
                    check_name=CHECK_NAME,
                )
                continue
            eid = p.get("evidence_id")
            if not eid:
                yield Issue(
                    ctx.rel, "error",
                    f"contradictions[{i}].positions[{j}]: missing required "
                    f"'evidence_id' (must reference a quote id in this artifact)",
                    check_name=CHECK_NAME,
                )
            elif quote_ids and eid not in quote_ids:
                yield Issue(
                    ctx.rel, "error",
                    f"contradictions[{i}].positions[{j}]: evidence_id "
                    f"{eid!r} does not match any quote id in this artifact",
                    check_name=CHECK_NAME,
                )
            if not (p.get("position") or "").strip():
                yield Issue(
                    ctx.rel, "error",
                    f"contradictions[{i}].positions[{j}]: missing required "
                    f"'position' (verbatim or paraphrased summary of the "
                    f"divergent position)",
                    check_name=CHECK_NAME,
                )
