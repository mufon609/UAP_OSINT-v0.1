"""hypotheses check — investigation-only research-artifact check.

Validates the entry shape of `hypotheses[]` on investigation
artifacts. Each entry requires lifecycle fields (id, added_date) +
a non-empty `statement` field stating the hypothesis.

Hypothesis ids drive cross-reference resolution from
`hypothesis_evaluation[].hypothesis_id` and
`counter_evidence[].against_hypothesis_id`. Reserved id `h0` (the
null hypothesis) is permitted but not required; the
investigation_hypothesis_citation check handles cross-reference
resolution case-insensitively.

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


CHECK_NAME = "hypotheses"


def check(ctx):
    if not section_in_scope(ctx, "hypotheses"):
        return
    if "hypotheses" not in ctx.data:
        return

    items = entries(ctx.data, "hypotheses")
    yield from check_unique_ids(ctx.rel, items, "hypotheses", CHECK_NAME)
    for i, h in enumerate(items):
        if not isinstance(h, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, h, "hypotheses", i, CHECK_NAME)
        statement = (h.get("statement") or "").strip()
        if not statement:
            yield Issue(
                ctx.rel, "error",
                f"hypotheses[{i}] ({h.get('id')!r}): missing required "
                f"'statement' (one declarative sentence stating the hypothesis)",
                check_name=CHECK_NAME,
            )
