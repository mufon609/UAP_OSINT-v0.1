"""coverage check — cross-layer ResearchContext check.

Verifies every artifact ``quotes[].text`` appears in the target node's
rendered body (whitespace / punctuation normalized via the same
``normalize_for_compare`` the verbatim-quote check uses, so the lockstep
guarantee per ``meta/conventions.md`` holds).

Phase III review (cross-layer): the artifact and the rendered node
body must agree on what quotes the artifact contributed. Drift means
the artifact was edited but the node not regenerated, OR the renderer
emits something different from what the artifact contains.

Consumes ``ctx.node_text`` (set by the review-coverage orchestrator
after target-node resolution).

Origin: shipped at commit ``0a56989`` (D.4 — introduction of Phase III
review-coverage.py) as one of four mechanical checks
(Coverage / Boundary / Stub-linking / OQ dedup). Originally checked
both ``claims[].statement`` AND ``quotes[].text`` against the rendered
node body. The check simplified at commit ``cde69cf`` (claims[] layer
elimination, 2026-04-21) — the claim.statement loop was deleted when
claims[] was removed repo-wide and quotes[] became the universal
evidentiary primitive.

Forms a paired-check family with verbatim_quotes that brackets the
evidentiary integrity chain:

  verbatim_quotes: source text → artifact.quotes[].text
                   (is the artifact's quote actually in the cited source?)
  coverage:        artifact.quotes[].text → rendered node body
                   (does the rendered node include the artifact's quotes?)

Drift at either end of the source ← quote → node-body chain is
caught: an unsourced fabrication entering the artifact trips
verbatim_quotes; an artifact diverging from its rendered node trips
coverage. Both checks use the same ``normalize_for_compare`` from
``lib._common.py`` so the comparison shape is identical at both ends
of the chain.

Migration: lift to per-module shape at commit ``363212d`` (C11
session 3 — lift all 4 review-coverage.py checks). C18 confirmed
byte-identity through both the claims-elimination and the per-module
moves.
"""

from checks import Issue
from lib._common import normalize_for_compare


CHECK_NAME = "coverage"


def _truncate(s, n=80):
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[:n] + "..."


def check(ctx):
    if ctx.node_text is None:
        return
    normalized_body = normalize_for_compare(ctx.node_text)

    for q in ctx.data.get("quotes") or []:
        if not isinstance(q, dict):
            continue
        text = (q.get("text") or "").strip()
        if not text:
            continue
        if normalize_for_compare(text) not in normalized_body:
            yield Issue(
                ctx.rel, "error",
                f"Coverage: quote {q.get('id')!r} text not found in node "
                f'body: "{_truncate(text)}"',
                check_name=CHECK_NAME,
            )
