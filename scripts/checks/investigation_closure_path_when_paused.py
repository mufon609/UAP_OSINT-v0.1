"""investigation_closure_path_when_paused check — investigation-only research-artifact check.

Conditional requirement: when the target investigation node's
frontmatter ``status: paused``, the artifact's ``closure_path[]``
must be non-empty.

The closure_path field documents the external event that would
unblock the investigation (FOIA appeal resolving, registry access
becoming available, witness becoming available, etc.). A paused
investigation without a documented closure path is opaque to
future contributors — they can't tell when re-evaluation is
warranted.

When status is ``open`` or ``closed``, closure_path[] may be empty.

No-ops on non-investigation artifacts. Reads ``ctx.target_status``
(populated by validate-research.py target discovery).
"""

from checks import Issue
from checks._research_utils import entries


CHECK_NAME = "investigation_closure_path_when_paused"


def check(ctx):
    if ctx.target_type != "investigation":
        return
    target_status = getattr(ctx, "target_status", None)
    if target_status != "paused":
        return
    closure = entries(ctx.data, "closure_path")
    if not closure:
        yield Issue(
            ctx.rel, "error",
            f"investigation status is 'paused' but closure_path[] is empty. "
            f"Paused investigations must document the external event that "
            f"would unblock them (FOIA appeal, registry access, primary "
            f"source surfacing, etc.) so future contributors can tell "
            f"when re-evaluation is warranted.",
            check_name=CHECK_NAME,
        )
