"""extrinsic-authorship check — research-artifact ResearchContext check.

``context_extrinsic.extrinsic_authorship`` is STRUCTURED METADATA: the
provenance note for a ``(b)(6)``-redacted document author identified only
from an external index (the DIA-to-Congress products list). It documents
*why* the attribution is made; it is NOT rendered into the node body (the
document renderer does not consume the field — see
``scripts/build/renderers/document.py``), and the redacted-author
convention holds that such an author is *carried by the link*, never
asserted on the node (see the ``scripts/checks/prose_drift.py`` docstring).

Reachability of the externally-attested author AND the institution
attributed to it is handled by ``associated_entities`` like any other
entity: they are listed there and ``associate.py`` unions them into
``## Associated Nodes``. A ``[`/type/slug`]`` link wrap placed *inside*
extrinsic_authorship therefore renders nowhere and merely duplicates the
``associated_entities`` entry — dead weight that reads as a working link.

This check ERRORS on any such wrap: the field carries prose only; the
entities it names live in ``associated_entities``. Resolution — remove the
wrap (keep the bare name) and ensure the entity is in
``associated_entities`` (the associated_entities check + the auditor's
cold re-read enforce that completeness).
"""

import re

from checks import Issue


CHECK_NAME = "extrinsic_authorship"

# Same wrap form associate.py harvests and the verbatim-quote check bans
# inside quote.text: [`/type/slug`].
_WRAP = re.compile(r"\[`(/[^`]+)`\]")


def check(ctx):
    ctx_ex = ctx.data.get("context_extrinsic")
    if not isinstance(ctx_ex, dict):
        return
    text = ctx_ex.get("extrinsic_authorship")
    if not isinstance(text, str):
        return
    for wrap in _WRAP.findall(text):
        yield Issue(
            ctx.rel, "error",
            f"context_extrinsic.extrinsic_authorship contains a link wrap "
            f"{wrap!r} — the field is structured metadata and renders "
            f"nowhere; the entity reaches ## Associated Nodes via "
            f"associated_entities. Remove the wrap (keep the bare name), "
            f"and list {wrap!r} in associated_entities if it is not already.",
            check_name=CHECK_NAME,
        )
