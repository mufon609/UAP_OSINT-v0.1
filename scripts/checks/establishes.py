"""establishes check — finding-only research-artifact check.

Validates `establishes[]` on finding artifacts as a list of non-
empty prose strings. Each item is one declarative claim about what
the cross-source convergence in evidence[] proves, with inline
references to specific evidence quote ids (e.g., "Claim citing q1 + q2").

Different shape from lifecycle-entry sections — strings, not dicts.
Empty list permitted (scaffold state); list must contain only non-
empty string elements when populated.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.
"""

from checks import Issue
from checks._research_utils import entries, section_in_scope


CHECK_NAME = "establishes"


def check(ctx):
    if not section_in_scope(ctx, "establishes"):
        return
    if "establishes" not in ctx.data:
        return

    items = entries(ctx.data, "establishes")
    for i, item in enumerate(items):
        if not isinstance(item, str):
            yield Issue(
                ctx.rel, "error",
                f"establishes[{i}]: must be a string (got {type(item).__name__})",
                check_name=CHECK_NAME,
            )
            continue
        if not item.strip():
            yield Issue(
                ctx.rel, "error",
                f"establishes[{i}]: empty string — every entry must state "
                f"a claim about what the convergence proves",
                check_name=CHECK_NAME,
            )
