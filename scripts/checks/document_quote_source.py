"""document-quote-source check — per-node NodeContext check (document-only).

Closes a verbatim-integrity gap between what the verbatim-quote check
validates and what the document renderer displays.

The verbatim-quote check (``verbatim_quotes``) validates each quote's
``text`` against that quote's OWN ``source.path``. But the document
renderer (``renderers/document.py::render_key_passages``) displays the
node's FIRST ``primary_sources`` entry as the "Source" link for EVERY
Key Passage — document nodes are single-source by display. When a
quote's ``source.path`` differs from ``primary_sources[0].path`` (e.g. a
quote drawn from a second document), the verbatim check passes — the
words ARE in the cited ``source.path`` — while the rendered node points
the reader at a DIFFERENT source (``primary_sources[0]``) that does NOT
contain the words. The integrity guarantee — "follow the Source link,
find the words" — silently breaks. (This happened: a DIRD node carried a
Key Passage sourced from the DIA→Congress list but rendered as sourced
to the DIRD itself.)

This check asserts, for ``document``-type nodes ONLY, that every quote's
``source.path`` equals the node's ``primary_sources[0].path`` — the
single source the renderer displays for all Key Passages. The effect is
that the validated source is identical to the displayed source, so the
existing verbatim-quote check is guaranteed to be validating the exact
source the reader is pointed to.

Scoped to ``document`` only by design: the transcript / media /
organization renderers display a per-quote Source link, so the source
validated by ``verbatim_quotes`` is already the source displayed — no
display/validation divergence exists there to guard against.

The structured ``primary_sources`` / ``quotes`` fields live only in the
research artifact (the rendered node carries the display projection, not
the source paths), so this NodeContext check reads the node's research
artifact at ``meta/research/{slug}.yaml``. A node with no artifact, an
unparseable artifact, or no ``primary_sources`` is left to the
research-artifact validators; this check no-ops cleanly in those cases.
"""

from checks import Issue
from lib._common import RESEARCH_DIR, strict_yaml_load


CHECK_NAME = "document_quote_source"


def check(ctx):
    if ctx.node_type != "document":
        return

    # Structured primary_sources / quotes live in the research artifact,
    # not the rendered node body. Map node slug -> artifact path.
    artifact_path = RESEARCH_DIR / f"{ctx.path.stem}.yaml"
    if not artifact_path.exists():
        return  # research-artifact validators own the missing-artifact case

    try:
        with open(artifact_path) as f:
            data = strict_yaml_load(f)
    except Exception:
        return  # artifact_parse (validate-research.py) owns parse failures
    if not isinstance(data, dict):
        return

    sources = data.get("primary_sources") or []
    if not (sources and isinstance(sources[0], dict)):
        return  # no displayed source to compare against
    displayed = sources[0].get("path")
    if not displayed:
        return

    quotes = data.get("quotes") or []
    if not isinstance(quotes, list):
        return

    for i, q in enumerate(quotes):
        if not isinstance(q, dict):
            continue
        src = q.get("source")
        if not isinstance(src, dict):
            continue  # quotes shape check owns malformed source
        qpath = src.get("path")
        if not qpath:
            continue  # quotes shape check owns missing path
        if qpath != displayed:
            qid = q.get("id")
            yield Issue(
                ctx.rel, "error",
                f"quote {qid!r} (quotes[{i}]) cites source.path "
                f"{qpath!r}, but the document renderer displays "
                f"primary_sources[0] ({displayed!r}) as the Source link "
                f"for every Key Passage — the rendered node would point "
                f"the reader at a source that does not contain the quote.",
                check_name=CHECK_NAME,
            )
