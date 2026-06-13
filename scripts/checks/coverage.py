"""coverage check — cross-layer ResearchContext check.

Verifies every artifact ``quotes[].text`` appears in the target node's
rendered body (whitespace / punctuation normalized via the same
``normalize_for_compare`` the verbatim-quote check uses, so the lockstep
guarantee per the scripts/lib lockstep holds).

Pairs with ``verbatim_quotes`` to bracket the evidentiary chain:

  verbatim_quotes: source text → artifact.quotes[].text
                   (is the quote actually in the cited source?)
  coverage:        artifact.quotes[].text → rendered node body
                   (does the rendered node include the quote?)

An unsourced fabrication entering the artifact trips verbatim_quotes;
an artifact diverging from its rendered node trips coverage. Both use
the same ``normalize_for_compare`` so the comparison shape is identical
at both ends of the chain.

Consumes ``ctx.node_text`` set by the orchestrator after target-node
resolution.
"""

from checks import Issue
from lib._common import normalize_for_compare


CHECK_NAME = "coverage"


def _truncate(s):
    s = s.replace("\n", " ").strip()
    return s if len(s) <= 80 else s[:80] + "..."


def check(ctx):
    if ctx.node_text is None:
        return
    normalized_body = normalize_for_compare(ctx.node_text)
    quotes = ctx.data.get("quotes") or []

    # Pointer quotes (person claim-group view): a quote that another group
    # member's `corroborated_by` points at renders as a compact "Also
    # attested" source-link pointer, NOT as full text — so its `text` will
    # not appear in the body by design. Exempt those from the full-text
    # assertion and verify the source link surfaced instead. Scoped to
    # person artifacts that actually use `claim_group` (the grouped
    # renderer); on every other artifact each quote still renders in full.
    # Grouped rendering is person-only (renderers/person.py); detect it
    # from the artifact's target_node rather than ctx.target_type, which
    # review-coverage.py does not populate on its ResearchContext.
    is_person = str(ctx.data.get("target_node") or "").startswith("people/")
    pointer_ids = set()
    if is_person and any(
        isinstance(q, dict) and q.get("claim_group") for q in quotes
    ):
        # Mirror the renderer's per-claim-group scoping (renderers/person.py):
        # a quote is only demoted to a pointer when the corroborated_by naming
        # it comes from a quote in the *same* group. A cross-group (or
        # ungrouped-source) reference does not demote the target, so the
        # target still renders in full and must keep its full-text check.
        group_of = {
            q.get("id"): q.get("claim_group")
            for q in quotes if isinstance(q, dict)
        }
        pointer_ids = {
            cid for q in quotes if isinstance(q, dict) and q.get("claim_group")
            for cid in (q.get("corroborated_by") or [])
            if group_of.get(cid) == q.get("claim_group")
        }

    for q in quotes:
        if not isinstance(q, dict):
            continue
        text = (q.get("text") or "").strip()
        if not text:
            continue
        if q.get("id") in pointer_ids:
            sp = (q.get("source") or {}).get("path") or ""
            if sp and sp not in ctx.node_text:
                yield Issue(
                    ctx.rel, "error",
                    f"Coverage: pointer quote {q.get('id')!r} source {sp!r} "
                    f"not found in node body — its 'Also attested' pointer "
                    f"did not render",
                    check_name=CHECK_NAME,
                )
            continue
        if normalize_for_compare(text) not in normalized_body:
            yield Issue(
                ctx.rel, "error",
                f"Coverage: quote {q.get('id')!r} text not found in node "
                f'body: "{_truncate(text)}"',
                check_name=CHECK_NAME,
            )
