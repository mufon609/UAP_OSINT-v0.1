"""synthesis-prose-entry-ids check — research-artifact ResearchContext check.

Errors on internal entry IDs (``q39``, ``nq4``, ``t8``, "aaro q13", …) in
top-level synthesis prose — ``description``,
``background``, ``top_relevance``, ``credibility_notes``, ``establishes`` /
``does_not_establish``, hypothesis and counter-evidence text,
``context_extrinsic`` — the Builder's organize step (organize phase).
Prose names the source (document, date, section), never an entry ID.

One of the phase-scoped dispatches of ``checks._entry_id_prose``, which
carries the token rule, the exempt fields and the rationale. The fields
this module scans are the sections whose owning phase is this check's
phase in ``_phases.CHECK_PHASE``.
"""

from checks._entry_id_prose import scan


CHECK_NAME = "synthesis_prose_entry_ids"


def check(ctx):
    yield from scan(ctx, CHECK_NAME)
