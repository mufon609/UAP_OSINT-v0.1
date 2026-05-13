"""does_not_establish check — finding-only research-artifact check.

Validates `does_not_establish[]` on finding artifacts as a list of
non-empty prose strings. Each item is one explicit caveat, gap, or
divergence the cross-source convergence does NOT reach. No
speculation; what the record does NOT carry.

Different shape from lifecycle-entry sections — strings, not dicts.
Empty list permitted (scaffold state); list must contain only non-
empty string elements when populated.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.
"""

from checks import Issue
from checks._research_utils import entries, section_in_scope


CHECK_NAME = "does_not_establish"


def check(ctx):
    if not section_in_scope(ctx, "does_not_establish"):
        return
    if "does_not_establish" not in ctx.data:
        return

    items = entries(ctx.data, "does_not_establish")
    for i, item in enumerate(items):
        if not isinstance(item, str):
            yield Issue(
                ctx.rel, "error",
                f"does_not_establish[{i}]: must be a string (got {type(item).__name__})",
                check_name=CHECK_NAME,
            )
            continue
        if not item.strip():
            yield Issue(
                ctx.rel, "error",
                f"does_not_establish[{i}]: empty string — every entry must "
                f"state a caveat or gap that the convergence does NOT reach",
                check_name=CHECK_NAME,
            )
