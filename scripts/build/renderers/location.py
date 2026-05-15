"""Location-type renderer.

Renders location nodes (no kinds — a single key set drives the
Overview fact table). Section order: Overview → Description →
Ownership Timeline → {display_name}-Scope Activity → Key Passages →
Relationships → Associated Nodes.
"""

from lib._common import load_topic

from ._common import (
    SECTION_SEP,
    _escape_table_cell,
    _format_period,
    _render_attribution_block,
    _wrap_path,
    sort_by_date,
)
from ._universal import (
    render_associated_nodes,
    render_description,
    render_preserved_disagreements,
    render_primary_source_contradictions,
    render_public_record_claims,
    render_source_form_notes,
)


# Row-label mapping for Overview fact-table rows.
_LOCATION_OVERVIEW_LABELS = {
    "full_name":                 "Full Name",
    "alternate_names":           "Alternate Names",
    "location_type":             "Location Type",
    "geographic_location":       "Geographic Location",
    "coordinates":               "Coordinates",
    "legal_description":         "Legal Description",
    "ownership_history_summary": "Ownership History Summary",
    "scope_significance":        "Scope Significance",
}

# Row render order. Matches meta/templates/location.md. `status` comes
# from frontmatter (not document_intrinsic) and renders as the final row.
_LOCATION_OVERVIEW_ORDER = [
    "full_name",
    "alternate_names",
    "location_type",
    "geographic_location",
    "coordinates",
    "legal_description",
    "ownership_history_summary",
    "scope_significance",
]


def render_title_location(artifact):
    """H1 title for location nodes. Prefers context_extrinsic.display_title,
    falls back to document_intrinsic.full_name, then humanized slug."""
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    slug = artifact["target_node"].split("/", 1)[1] if "/" in artifact["target_node"] else ""
    title = (
        ctx.get("display_title")
        or dm.get("full_name")
        or (slug and " ".join(w.capitalize() for w in slug.split("-")))
        or ""
    )
    return f"# {title}\n"


def render_location_overview(artifact, fm):
    """Overview fact-table. 3-column layout (Field | Value | Source),
    matching meta/templates/location.md. Source cell left empty —
    document_intrinsic keys are attested by the union of primary_sources
    on the artifact, not per-row. Status row comes from frontmatter."""
    dm = artifact.get("document_intrinsic") or {}

    rows = []
    for key in _LOCATION_OVERVIEW_ORDER:
        val = dm.get(key)
        if val in (None, "", []):
            continue
        label = _LOCATION_OVERVIEW_LABELS.get(key, key)
        if isinstance(val, list):
            val = "; ".join(str(v) for v in val)
        rows.append(f"| {label} | {val} |  |")

    status = (fm or {}).get("status")
    if status:
        rows.append(f"| Status | {status} |  |")

    lines = ["## Overview", "", "| Field | Value | Source |", "|---|---|---|"]
    if rows:
        lines.extend(rows)
    else:
        lines.append("|  |  |  |")
    return "\n".join(lines) + "\n"


def render_ownership_timeline(artifact):
    """Ownership Timeline section — chronological table from
    ownership_timeline[]. Columns: Period | Owner | Use / Status |
    Source. Sorted ascending by period_start; the chronological-ordering
    check enforces chronological order on the rendered table."""
    items = sort_by_date(
        [e for e in (artifact.get("ownership_timeline") or []) if isinstance(e, dict)],
        "period_start",
    )
    lines = ["## Ownership Timeline", "",
             "| Period | Owner | Use / Status | Source | Note |",
             "|---|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |  |")
        return "\n".join(lines) + "\n"
    for e in items:
        period = _format_period(e)
        owner = e.get("owner") or ""
        owner_path = e.get("owner_path")
        if owner_path:
            wrap = _wrap_path(owner_path)
            owner_cell = f"{owner} {wrap}" if owner else wrap
        else:
            owner_cell = owner
        lines.append(
            f"| {period} | "
            f"{owner_cell} | "
            f"{e.get('use_status') or ''} | "
            f"{(e.get('source') or {}).get('path') or ''} | "
            f"{_escape_table_cell(e.get('note'))} |"
        )
    return "\n".join(lines) + "\n"


def render_top_scope_activity(artifact):
    """{display_name}-Scope Activity section — chronological table from
    top_scope_activity[]. Columns: Period | Activity | Source. When
    actor_paths is populated, wraps are appended inline to the Activity
    cell as `— [`/path1`]; [`/path2`]`. Sorted ascending by period_start;
    the chronological-ordering check enforces chronological order. Header
    text uses display_name from meta/topic/overview.md frontmatter."""
    items = sort_by_date(
        [e for e in (artifact.get("top_scope_activity") or []) if isinstance(e, dict)],
        "period_start",
    )
    display_name = load_topic()["display_name"]
    lines = [f"## {display_name}-Scope Activity", "",
             "| Period | Activity | Source | Note |",
             "|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |")
        return "\n".join(lines) + "\n"
    for e in items:
        period = _format_period(e)
        activity = e.get("activity") or ""
        actors = e.get("actor_paths") or []
        if actors:
            actor_wraps = "; ".join(_wrap_path(p) for p in actors if p)
            activity_cell = f"{activity} — {actor_wraps}" if activity else actor_wraps
        else:
            activity_cell = activity
        lines.append(
            f"| {period} | "
            f"{activity_cell} | "
            f"{(e.get('source') or {}).get('path') or ''} | "
            f"{_escape_table_cell(e.get('note'))} |"
        )
    return "\n".join(lines) + "\n"


def render_location_key_passages(artifact):
    """Key Passages section — verbatim excerpts from primary sources
    ABOUT the location. Mirrors render_org_key_passages pattern. H3
    per quote using `significance` field; block-quote text + per-quote
    verification block. Sorted by `statement_date` with natural-sort
    tie-break on id."""
    quotes = [q for q in (artifact.get("quotes") or []) if isinstance(q, dict)]
    quotes = sort_by_date(quotes, "statement_date")

    head = "## Key Passages\n"
    if not quotes:
        return head + "\n<!-- TODO: populate `quotes` in the research artifact -->\n"

    blocks = []
    for q in quotes:
        h3 = q.get("significance") or "Passage"
        text = (q.get("text") or "").rstrip("\n")
        lines = [f"### {h3}", ""]
        for qline in text.split("\n"):
            lines.append(f"> {qline}" if qline else ">")
        lines.append("")
        lines.append(_render_attribution_block(q, artifact))
        blocks.append("\n".join(lines))
    return head + "\n" + "\n\n---\n\n".join(blocks) + "\n"


def render_location_relationships(artifact):
    """Relationships section — location_relationships[] with Confirmed /
    Flagged split. Heterogeneous entity_path targets (any node type)."""
    items = [e for e in (artifact.get("location_relationships") or []) if isinstance(e, dict)]
    confirmed = [e for e in items if not e.get("flagged")]
    flagged   = [e for e in items if e.get("flagged")]

    def row(e):
        ep = _wrap_path(e.get("entity_path"))
        return (
            f"| {ep} | "
            f"{e.get('relationship') or ''} | "
            f"{_escape_table_cell(e.get('note'))} |"
        )

    lines = ["## Relationships", "", "### Confirmed", "",
             "| Entity | Relationship | Note |",
             "|---|---|---|"]
    if confirmed:
        for e in confirmed:
            lines.append(row(e))
    else:
        lines.append("|  |  |  |")
    if flagged:
        lines += ["", "### Flagged", "",
                  "| Entity | Relationship | Note |",
                  "|---|---|---|"]
        for e in flagged:
            lines.append(row(e))
    return "\n".join(lines) + "\n"


def render_body_location(artifact, fm):
    """Location-type body composition. Section order matches the
    schema's required_sections: Overview → Description → Ownership
    Timeline → {Topic}-Scope Activity → Key Passages → Relationships →
    Associated Nodes ({Topic} = display_name from
    meta/topic/overview.md). Location has no kinds, so no per-kind
    dispatch."""
    title = render_title_location(artifact).rstrip("\n") + "\n"
    sections = [
        render_location_overview(artifact, fm),
        render_description(artifact),
        render_ownership_timeline(artifact),
        render_top_scope_activity(artifact),
        render_location_key_passages(artifact),
        render_location_relationships(artifact),
        render_primary_source_contradictions(artifact),
        render_public_record_claims(artifact),
        render_source_form_notes(artifact),
        render_preserved_disagreements(artifact),
        render_associated_nodes(),
    ]
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined
