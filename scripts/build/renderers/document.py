"""Document-type renderer.

Renders document nodes (gov-doc and non-gov-doc kinds) from research
artifacts. Section composition per ``meta/schema.yaml`` document
required_sections — Provenance is gov-doc-only; all other sections
emit on both kinds.
"""

import re

from ._common import (
    SECTION_SEP,
    _render_blockquote,
    _source_path,
    sort_by_id,
)
from ._universal import (
    render_associated_nodes,
    render_description,
    render_name_variants,
    render_preserved_disagreements,
    render_source_form_notes,
)

# Renderer-coverage contract — canonical H2 section titles render_body_document
# can emit. Checked against schema-required sections by renderer-coverage.py.
EMITS = frozenset({
    "Document Summary",
    "Description",
    "Key Passages",
    "Source-Form Notes",
    "Preserved Disagreements",
    "Name Variants",
    "References",
    "Associated Nodes",
})


def render_title(artifact):
    """H1 title for document nodes. Prefers ``context_extrinsic.display_title``,
    then ``document_intrinsic.internal_title``, then a humanized slug."""
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    title = ctx.get("display_title") or dm.get("internal_title")
    if not title:
        slug = artifact["target_node"].split("/", 1)[1]
        title = " ".join(w.capitalize() for w in slug.split("-"))
    return f"# {title}\n"


# Physical-page ref detector: a `p. N` / `pp. N` location naming an integer page.
# A sibling-backed (markerless OCR) source carries descriptive content-anchor
# locations and NO `p. N` refs; the
# page-citation note in render_document_summary is suppressed for such a node so
# it never advertises a citation form it does not use.
_PAGE_REF = re.compile(r"\bpp?\.\s*\d")


def _has_physical_page_ref(artifact):
    """True if any quote / cited-work / naming-quirk / timeline location names a
    physical `p. N` page — i.e. the node actually uses page-citation refs."""
    def _scan(loc):
        return isinstance(loc, str) and bool(_PAGE_REF.search(loc))
    for q in (artifact.get("quotes") or []):
        src = q.get("source") if isinstance(q, dict) else None
        if isinstance(src, dict) and _scan(src.get("location")):
            return True
    cw_value = artifact.get("cited_works")
    for cw in (cw_value if isinstance(cw_value, list) else []):
        src = cw.get("source") if isinstance(cw, dict) else None
        if isinstance(src, dict) and _scan(src.get("location")):
            return True
    for nq in (artifact.get("naming_quirks") or []):
        if isinstance(nq, dict) and _scan(nq.get("location")):
            return True
    for t in (artifact.get("timeline") or []):
        src = t.get("source") if isinstance(t, dict) else None
        if isinstance(src, dict) and _scan(src.get("location")):
            return True
    return False


def render_document_summary(artifact):
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    path = _source_path(artifact)
    lines = ["## Document Summary", ""]
    rows = []
    title = dm.get("internal_title") or ctx.get("display_title")
    if title:
        rows.append(("Title", title))
    if dm.get("internal_date"):
        rows.append(("Authored Date (per document)", dm["internal_date"]))
    if ctx.get("hearing_date"):
        rows.append(("Hearing Date", ctx["hearing_date"]))
    authors = dm.get("authors_per_document")
    if authors:
        rows.append(("Author (per document)", "; ".join(authors) if isinstance(authors, list) else str(authors)))
    if dm.get("classification"):
        rows.append(("Classification", dm["classification"]))
    fmt_parts = []
    sources = artifact.get("primary_sources") or []
    if sources and isinstance(sources[0], dict) and sources[0].get("format"):
        fmt_parts.append(sources[0]["format"].upper())
    if dm.get("pages"):
        fmt_parts.append(f"{dm['pages']} pages")
    if fmt_parts:
        rows.append(("Format", ", ".join(fmt_parts)))
    if ctx.get("primary_source_url"):
        rows.append(("Primary Source URL", ctx["primary_source_url"]))
    if path:
        rows.append(("Local Archive", f"[sources/{path}](../sources/{path})"))
    # Content-block provenance for a sibling-backed (ocr-scan) source: which
    # pages, if any, the VLM page-image read was content-filter-blocked on and
    # PaddleOCR filled. A `Content Block` row in the Document Summary table so it
    # greps as `Content Block`; present only when the artifact's source carries
    # it (text-native sources omit it). See meta/schema-research-artifact.yaml.
    content_block = (sources[0].get("content_block")
                     if sources and isinstance(sources[0], dict) else None)
    if content_block:
        rows.append(("Content Block", content_block))
    if not rows:
        lines.append("<!-- TODO: populate `document_intrinsic` / `context_extrinsic` / `primary_sources` in the research artifact -->")
        return "\n".join(lines) + "\n"
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    for k, v in rows:
        lines.append(f"| {k} | {v} |")
    # Stated page-citation convention note for multi-page PDF sources that
    # actually carry `p. N` location refs. `p. N` refs are physical / PDF-viewer
    # pages (the Nth page of the file), which for composite documents — a cover,
    # a third-party FOIA distribution insert, roman front matter — run ahead of
    # the printed page number the document carries on its face. State it so a
    # reader following `p. N` opens the PDF to page N rather than hunting the
    # printed folio. A
    # sibling-backed (markerless OCR) source uses descriptive content-anchor
    # locations and no `p. N`, so the
    # note is suppressed — the node would otherwise advertise a form it never uses.
    src_fmt = (sources[0].get("format") if sources and isinstance(sources[0], dict) else None)
    try:
        npages = int(dm.get("pages"))  # tolerate int (30) or numeric string ('8')
    except (TypeError, ValueError):
        npages = 0
    if src_fmt == "pdf" and npages > 1 and _has_physical_page_ref(artifact):
        lines.append("")
        lines.append(
            "_Page citations (`p. N`) are physical / PDF-viewer pages — the Nth "
            "page of the file, counting any cover and front matter — which run "
            "ahead of the printed page number the document shows on the page "
            "itself._"
        )
    return "\n".join(lines) + "\n"


def render_key_passages(artifact):
    """Document Key Passages — H3 per quote, single Source link in the
    verification block (documents have one source; per-quote per-source
    fan-out lives on transcript / media / organization Key Passages)."""
    quotes = sort_by_id(artifact.get("quotes") or [])
    ctx = artifact.get("context_extrinsic") or {}
    attribution = ctx.get("quote_attribution") or ""
    path = _source_path(artifact)
    src_link = f"[archived source](../sources/{path})" if path else ""

    head = "## Key Passages\n"
    if not quotes:
        return head + "\n<!-- TODO: populate `quotes` in the research artifact -->\n"

    blocks = []
    for q in quotes:
        if not isinstance(q, dict):
            continue
        h3 = q.get("significance") or "Passage"
        text = (q.get("text") or "").rstrip("\n")
        loc = ""
        if isinstance(q.get("source"), dict):
            loc = q["source"].get("location") or ""
        lines = [f"### {h3}", ""]
        lines.append(_render_blockquote(text))
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|---|---|")
        if attribution:
            lines.append(f"| Attributed to | {attribution} |")
        if src_link:
            lines.append(f"| Source | {src_link} |")
        if loc:
            lines.append(f"| Location | {loc} |")
        blocks.append("\n".join(lines))

    return head + "\n" + "\n\n---\n\n".join(blocks) + "\n"


def render_cited_works(artifact):
    """Document References — the three-state cited_works affirmation.

    Three valid shapes (see scripts/checks/cited_works.py):

      - ``cited_works: NONE``    — source carries no reference list. Render
                                   a one-line "Source carries no reference
                                   list." affirmation under ## References.
      - ``cited_works: IGNORED`` — source HAS a reference list, deliberately
                                   not captured (low-value release valve).
                                   Render a one-line "deliberately not
                                   captured" affirmation under ## References,
                                   reader-visible so the discretionary skip
                                   is observable on the node body itself.
      - non-empty list           — render the entries view (each entry's
                                   ``citation_verbatim`` as a keyed bullet,
                                   soft-wrap newlines collapsed to spaces —
                                   the same whitespace normalization the
                                   citation-verbatim check applies). The
                                   split bibliographic fields (``author`` /
                                   ``year`` / ``title``) are the artifact-
                                   side query dimension (recurring-author
                                   network) and not separately rendered:
                                   the verbatim already carries them, and
                                   the archived source is the fidelity
                                   backstop.

    Empty list / unknown shape returns ``""`` defensively — the validator
    rejects those structurally; rendering nothing keeps the node
    well-formed if the renderer runs on a pre-validation artifact."""
    value = artifact.get("cited_works")

    if value == "NONE":
        return (
            "## References\n"
            "\n"
            "*Source carries no reference list.*\n"
        )
    if value == "IGNORED":
        return (
            "## References\n"
            "\n"
            "*Source's reference list deliberately not captured (low-value).*\n"
        )
    if not isinstance(value, list):
        return ""

    works = [w for w in value if isinstance(w, dict)]
    if not works:
        return ""

    def _key(w):
        # Sort by numeric prefix, then any suffix — so "5" < "5-a" < "5-b" < "6"
        # (some documents carry sub-lettered entries like [5-a]/[5-b]/[5-c]).
        k = str(w.get("citation_key", "")).strip()
        m = re.match(r"(\d+)(.*)", k)
        return (0, int(m.group(1)), m.group(2)) if m else (1, 0, k)

    lines = ["## References", ""]
    lines.append(
        "Reference list carried by the source document, transcribed verbatim "
        "(source spelling preserved). Captured as an authorship-network "
        "dimension; not part of the document's argument."
    )
    lines.append("")
    for w in sorted(works, key=_key):
        key = str(w.get("citation_key", "")).strip()
        verbatim = " ".join((w.get("citation_verbatim") or "").split())
        # citation_verbatim is faithful and includes the source's own leading
        # marker — bracket "[N]" / "[N-a]", parenthetical "(N)",
        # caret-superscript "^N" endnote, Unicode superscript "¹" endnote,
        # dotted-decimal "N.M", number-dot "N.", or a bare leading number
        # "N "; strip it for display since the marker is re-emitted in bold
        # from citation_key (avoids a doubled "[1] [1]" prefix). Order
        # matters: "N.M" precedes "N." so the full dotted key is consumed,
        # and the bare-number branch is last + requires trailing whitespace
        # so it only fires as a list marker, never on a number that opens
        # the citation text. A garbled OCR marker (e.g. "^"/"O" sics for a
        # lost digit) is intentionally left in place — faithful to the
        # scan, and the citation_key still carries N.
        verbatim = re.sub(
            r"^(?:(?:\[\d+(?:-[a-z])?\]|\(\d+\)|\^\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹]+|\d+\.\d+|\d+\.)\s*"
            r"|\d+\s+)",
            "", verbatim)
        marker = f"**[{key}]** " if key else ""
        lines.append(f"- {marker}{verbatim}")
    return "\n".join(lines) + "\n"


def render_body_document(artifact, node_kind):
    """Document-type body composition. H1 title stands alone — no
    ``---`` separator between H1 and first H2. Document nodes have no
    What This Establishes synthesis section: the document IS the fact
    record, and Key Passages carries the verbatim evidentiary content.
    See meta/conventions.md "Statements as the universal evidentiary
    primitive"."""
    title = render_title(artifact).rstrip("\n") + "\n"
    sections = [
        render_document_summary(artifact),
        render_description(artifact),
    ]
    sections.extend([
        render_key_passages(artifact),
        render_source_form_notes(artifact),
        render_preserved_disagreements(artifact),
        render_name_variants(artifact),
        render_cited_works(artifact),
        render_associated_nodes(),
    ])
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined
