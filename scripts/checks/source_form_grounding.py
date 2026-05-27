"""source-form-grounding check — cross-layer ResearchContext check.

Source-Form Notes carries no orphans. Every `naming_quirks` entry with
resolution ``preserve-as-sic-in-quotes`` must be GROUNDED — its
``observed`` form must appear on the rendered node somewhere the reader
meets it (inside a quote, or the heading / locator framing one), not
only in its own ``## Source-Form Notes`` table row.

This is the gate promotion of the long-standing
``coverage-suggest.py`` diagnostic (``report_quirk_grounding``): both
share ``lib._common.body_outside_source_form_notes`` +
``normalize_for_compare`` so the grounding definition is identical. An
ungrounded entry is an ERROR with a two-way fix, per
``meta/conventions.md`` "Off-node variants":

  - incidental source typo never quoted  → drop the entry
  - deliberate not-on-node variant kept for navigation / identity
    resolution → reclassify ``resolution: off-node-variant`` (renders
    in ``## Name Variants`` instead, keeping Source-Form Notes grounded)

Consumes ``ctx.node_text`` set by the review-coverage orchestrator after
target-node resolution; no-op on unbuilt nodes / artifacts with no
preserve-as-sic entries.
"""

from checks import Issue
from lib._common import body_outside_quirk_tables, normalize_for_compare


CHECK_NAME = "source_form_grounding"


def check(ctx):
    if ctx.node_text is None:
        return
    quirks = [
        nq for nq in (ctx.data.get("naming_quirks") or [])
        if isinstance(nq, dict)
        and nq.get("resolution") == "preserve-as-sic-in-quotes"
    ]
    if not quirks:
        return

    body = normalize_for_compare(body_outside_quirk_tables(ctx.node_text))
    for nq in quirks:
        observed = nq.get("observed") or ""
        if normalize_for_compare(observed) not in body:
            yield Issue(
                ctx.rel, "error",
                f"Source-Form Notes orphan: naming_quirks {nq.get('id')!r} "
                f"observed {observed!r} (preserve-as-sic-in-quotes) appears "
                f"only in its own ## Source-Form Notes row — ungrounded. Drop "
                f"it (incidental typo) or reclassify resolution: "
                f"off-node-variant (deliberate not-on-node variant; renders "
                f"in ## Name Variants). See meta/conventions.md "
                f'"Off-node variants".',
                check_name=CHECK_NAME,
            )
