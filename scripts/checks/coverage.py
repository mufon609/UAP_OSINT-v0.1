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
