"""FOIA-type renderer.

Renders foia nodes (kinds ``foia`` and ``mdr``) from research artifacts —
one records request, its correspondence, and the documents its release
produced. Section composition per ``meta/schema.yaml`` foia
required_sections; both kinds share one section set (appeals are
correspondence entries, not a separate kind).

Overview facts come from ``document_intrinsic`` (foia key conventions in
``schema-research-artifact.yaml::required_keys``); the Request State row
mirrors the node's frontmatter ``request_state`` — the single home of
that value (the investigation ``question`` precedent). The Timeline
merges ``timeline[]`` with one row per ``correspondence[]`` entry, so a
letter's date is recorded once, on its correspondence entry.
"""

import sys

from ._common import (
    SECTION_SEP,
    _escape_table_cell,
    _render_attribution_block,
    _render_blockquote,
    _render_passage_head,
    _wrap_path,
    sort_by_date,
    sort_by_id,
)
from ._universal import (
    render_associated_nodes,
    render_description,
    render_name_variants,
    render_preserved_disagreements,
    render_source_form_notes,
    render_timeline,
)

# Renderer-coverage contract — canonical H2 section titles render_body_foia
# can emit. Checked against schema-required sections by renderer-coverage.py.
EMITS = frozenset({
    "Overview",
    "Description",
    "Records Sought",
    "Correspondence",
    "Key Passages",
    "Released Records",
    "Timeline",
    "Source-Form Notes",
    "Preserved Disagreements",
    "Name Variants",
    "Associated Nodes",
})

_KIND_LABEL = {
    "foia": "FOIA — 5 U.S.C. § 552",
    "mdr": "Mandatory Declassification Review — E.O. 13526 § 3.5",
}

_FEE_CATEGORY_LABEL = {
    "commercial": "Commercial use",
    "educational": "Educational institution",
    "noncommercial-scientific": "Non-commercial scientific institution",
    "news-media": "Representative of the news media",
    "other": "All other requesters",
}

_SCHEME_LABEL = {
    "piid": "PIID",
    "solicitation-number": "Solicitation No.",
    "document-number": "Document No.",
    "report-number": "Report No.",
    "case-number": "Case No.",
    "other": "Identifier",
}


def _label(value):
    """Kebab-case vocabulary value → display label (`final-response` →
    `Final response`)."""
    s = str(value or "").replace("-", " ").strip()
    return s[:1].upper() + s[1:]


def _party(text, path):
    """Free-text party name and/or its node path → one table cell."""
    text = _escape_table_cell(text).strip()
    wrap = _wrap_path(path)
    if text and wrap:
        return f"{text} ({wrap})"
    return text or wrap


def _source_cell(src):
    """``source: {path, location}`` → archived-source link + location."""
    if not isinstance(src, dict) or not src.get("path"):
        return ""
    path = src["path"]
    cell = f"[sources/{path}](../sources/{path})"
    loc = _escape_table_cell(src.get("location")).strip()
    return f"{cell}, {loc}" if loc else cell


def render_title_foia(artifact):
    """H1 title. Prefers ``context_extrinsic.display_title``, then
    "{agency} request {tracking_number}", then a humanized slug."""
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    title = ctx.get("display_title")
    if not title and dm.get("tracking_number"):
        agency = dm.get("agency") or ""
        title = f"{agency} request {dm['tracking_number']}".strip()
    if not title:
        slug = artifact["target_node"].split("/", 1)[1]
        title = " ".join(w.capitalize() for w in slug.split("-"))
    return f"# {title}\n"


def render_foia_overview(artifact, kind, fm):
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    rows = [("Request Type", _KIND_LABEL.get(kind, kind or ""))]
    if fm.get("request_state"):
        rows.append(("Request State", fm["request_state"]))
    for label, text_key, path_key in (
        ("Requester", "requester", "requester_path"),
        ("Agency", "agency", "agency_path"),
        ("Component", "component", "component_path"),
    ):
        cell = _party(dm.get(text_key), dm.get(path_key))
        if cell:
            rows.append((label, cell))
    if dm.get("tracking_number"):
        rows.append(("Tracking Number", _escape_table_cell(dm["tracking_number"])))
    if dm.get("submitted_date"):
        rows.append(("Submitted", dm["submitted_date"]))
    if dm.get("fee_category"):
        fee = dm["fee_category"]
        rows.append(("Fee Category", _FEE_CATEGORY_LABEL.get(fee, fee)))
    if dm.get("fee_waiver"):
        rows.append(("Fee Waiver", _escape_table_cell(dm["fee_waiver"])))
    if ctx.get("primary_source_url"):
        rows.append(("Primary Source URL", ctx["primary_source_url"]))

    lines = ["## Overview", "", "| Field | Value |", "|---|---|"]
    lines.extend(f"| {k} | {v} |" for k, v in rows)
    return "\n".join(lines) + "\n"


def render_records_sought(artifact):
    items = sort_by_id(
        [e for e in (artifact.get("records_sought") or []) if isinstance(e, dict)]
    )
    lines = ["## Records Sought", "",
             "| Item | Records Sought | Identifiers | Date Range | Source |",
             "|---|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |  |")
    for n, e in enumerate(items, 1):
        idents = []
        for ident in e.get("identifiers") or []:
            if not isinstance(ident, dict) or not ident.get("value"):
                continue
            scheme = _SCHEME_LABEL.get(ident.get("scheme"), _label(ident.get("scheme")))
            idents.append(f"{scheme} `{_escape_table_cell(ident['value'])}`")
        lines.append(
            f"| {_escape_table_cell(e.get('item_label')) or n} | "
            f"{_escape_table_cell(e.get('description'))} | "
            f"{'; '.join(idents)} | "
            f"{_escape_table_cell(e.get('date_range'))} | "
            f"{_source_cell(e.get('source'))} |"
        )
    return "\n".join(lines) + "\n"


def render_correspondence(artifact):
    items = sort_by_date(
        [e for e in (artifact.get("correspondence") or []) if isinstance(e, dict)],
        "date",
    )
    lines = ["## Correspondence", "",
             "| Date | Type | From | To | Tracking No. | Summary | Source |",
             "|---|---|---|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |  |  |  |")
    for e in items:
        lines.append(
            f"| {e.get('date') or ''} | "
            f"{_label(e.get('letter_type'))} | "
            f"{_party(e.get('sender'), e.get('sender_path'))} | "
            f"{_party(e.get('recipient'), e.get('recipient_path'))} | "
            f"{_escape_table_cell(e.get('tracking_number'))} | "
            f"{_escape_table_cell(e.get('summary'))} | "
            f"{_source_cell(e.get('source'))} |"
        )
    return "\n".join(lines) + "\n"


def render_foia_key_passages(artifact):
    """Key Passages — verbatim spans from the correspondence / release.
    Per-quote attribution block (a foia node draws on many letters, so
    each passage carries its own Source link). Sorted by statement_date
    when set; falls through to artifact order."""
    quotes = [q for q in (artifact.get("quotes") or []) if isinstance(q, dict)]
    quotes = sort_by_date(quotes, "statement_date")

    head = "## Key Passages\n"
    if not quotes:
        return head + "\n<!-- TODO: populate `quotes` in the research artifact -->\n"

    blocks = []
    for q in quotes:
        text = (q.get("text") or "").rstrip("\n")
        lines = _render_passage_head(q, "Passage")
        lines.append(_render_blockquote(text))
        lines.append("")
        lines.append(_render_attribution_block(q, artifact))
        blocks.append("\n".join(lines))
    return head + "\n" + "\n\n---\n\n".join(blocks) + "\n"


def render_released_records(artifact):
    items = sort_by_date(
        [e for e in (artifact.get("released_records") or []) if isinstance(e, dict)],
        "release_date",
    )
    lines = ["## Released Records", "",
             "| Document | Date Released | Disposition | Exemptions | Pages | Source |",
             "|---|---|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |  |  |")
    for e in items:
        doc = _wrap_path(e.get("document_path"))
        label = _escape_table_cell(e.get("release_label")).strip()
        if label:
            doc = f"{doc} ({label})"
        exemptions = e.get("exemptions") or []
        lines.append(
            f"| {doc} | "
            f"{e.get('release_date') or ''} | "
            f"{_label(e.get('disposition'))} | "
            f"{_escape_table_cell(', '.join(str(x) for x in exemptions))} | "
            f"{_escape_table_cell(e.get('pages'))} | "
            f"{_source_cell(e.get('source'))} |"
        )
    return "\n".join(lines) + "\n"


def _correspondence_timeline_rows(artifact):
    """One synthesized timeline entry per correspondence entry — the
    letter's date, type, and parties — so the Timeline carries the
    request's procedural history without a second copy of each date."""
    rows = []
    for e in artifact.get("correspondence") or []:
        if not isinstance(e, dict):
            continue
        event = _label(e.get("letter_type"))
        parties = [p for p in (e.get("sender"), e.get("recipient")) if p]
        if len(parties) == 2:
            event += f" — {parties[0]} to {parties[1]}"
        elif parties:
            event += f" — {parties[0]}"
        rows.append({
            "id": e.get("id"),
            "date": e.get("date"),
            "event": _escape_table_cell(event),
            "category": "correspondence",
            "source": e.get("source") or {},
        })
    return rows


def render_foia_timeline(artifact):
    merged = [e for e in (artifact.get("timeline") or []) if isinstance(e, dict)]
    merged += _correspondence_timeline_rows(artifact)
    return render_timeline({"timeline": merged})


def render_body_foia(artifact, kind, fm):
    """FOIA-type body composition. Section order matches the schema's
    required_sections (identical across the foia / mdr kinds)."""
    if kind not in _KIND_LABEL:
        sys.exit(f"ERROR: render_body_foia: unknown foia kind {kind!r}")
    title = render_title_foia(artifact).rstrip("\n") + "\n"
    sections = [
        render_foia_overview(artifact, kind, fm),
        render_description(artifact),
        render_records_sought(artifact),
        render_correspondence(artifact),
        render_foia_key_passages(artifact),
        render_released_records(artifact),
        render_foia_timeline(artifact),
        render_source_form_notes(artifact),
        render_preserved_disagreements(artifact),
        render_name_variants(artifact),
        render_associated_nodes(),
    ]
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined
