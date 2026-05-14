"""Document-type renderer.

Renders document nodes (gov-doc and non-gov-doc kinds) from research
artifacts. Section composition per ``meta/schema.yaml`` document
required_sections — Provenance is gov-doc-only; all other sections
emit on both kinds.
"""

from ._common import (
    SECTION_SEP,
    _source_path,
    sort_by_id,
)
from ._universal import (
    render_associated_nodes,
    render_description,
    render_preserved_disagreements,
    render_provenance,
    render_source_form_notes,
)


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
    if not rows:
        lines.append("<!-- TODO: populate `document_intrinsic` / `context_extrinsic` / `primary_sources` in the research artifact -->")
        return "\n".join(lines) + "\n"
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    for k, v in rows:
        lines.append(f"| {k} | {v} |")
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
        for qline in text.split("\n"):
            lines.append(f"> {qline}" if qline else ">")
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
    if node_kind == "gov-doc":
        sections.append(render_provenance(artifact))
    sections.extend([
        render_key_passages(artifact),
        render_source_form_notes(artifact),
        render_preserved_disagreements(artifact),
        render_associated_nodes(),
    ])
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined
