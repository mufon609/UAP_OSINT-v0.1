"""Organization-type renderer.

Renders organization nodes across all three kinds (gov, gov-contractor,
private). Primary Contracts emits on gov-contractor only; the other
sections (Overview / Description / Key Personnel / Key Passages /
Timeline / Relationships) are common across kinds.
"""

import sys

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
    render_timeline,
)


# Row-label mapping for Overview fact-table rows. Keyed by
# document_intrinsic field name; value is the display label for the
# table row. Rows emit only for populated fields — empty keys skipped.
# Per-kind convention lives in schema-research-artifact.yaml's
# required_keys section (document_intrinsic field comment).
_ORG_OVERVIEW_LABELS = {
    # Common
    "full_name":                "Full Name",
    "internal_name":            "Internal Name",
    # gov agency/office
    "office_type":              "Type",
    "statutory_authority":      "Statutory Authority",
    "established_date":         "Established",
    "terminated_date":          "Terminated",
    "parent_organization_path": "Parent Organization",
    "current_director_path":    "Director",
    "jurisdiction":             "Jurisdiction",
    # gov military-unit
    "designator":               "Designator",
    "unit_class":               "Unit Class",
    "parent_unit_path":         "Parent Unit",
    "home_station":             "Home Station",
    "commissioned_date":        "Commissioned",
    "decommissioned_date":      "Decommissioned",
    "mission":                  "Mission",
    # gov military-service
    "branch_type":              "Branch Type",
    "founded_date":             "Founded",
    # gov-contractor
    "contracting_agency":       "Contracting Agency",
    "period_of_performance":    "Period of Performance",
    "primary_counterparty_path": "Primary Counterparty",
    "registered_status":        "Registered Status",
    "cage_code":                "CAGE Code",
    # private
    "org_type":                 "Type",
    "headquarters":             "Headquarters",
    "current_leadership_path":  "Current Leadership",
    "public_status":            "Public Status",
}

# Per-kind row ordering.
_ORG_OVERVIEW_ORDER_BY_KIND = {
    "gov": [
        "full_name", "internal_name",
        # Agency/office fields
        "office_type", "statutory_authority", "established_date", "terminated_date",
        "parent_organization_path", "current_director_path", "jurisdiction",
        # Military-unit fields
        "designator", "unit_class", "parent_unit_path", "home_station",
        "commissioned_date", "decommissioned_date", "mission",
        # Military-service fields
        "branch_type", "founded_date",
    ],
    "gov-contractor": [
        "full_name", "contracting_agency", "period_of_performance",
        "primary_counterparty_path", "registered_status", "cage_code",
    ],
    "private": [
        "full_name", "org_type", "founded_date", "headquarters",
        "current_leadership_path", "public_status",
    ],
}

# Leadership-class rendering order + heading for the Key Personnel
# sub-grouping.
_LEADERSHIP_CLASS_ORDER = ["director", "deputy", "staff", "advisor", "other"]
_LEADERSHIP_CLASS_HEADING = {
    "director": "Directors",
    "deputy":   "Deputy Leadership",
    "staff":    "Staff",
    "advisor":  "Advisors",
    "other":    "Other Named Personnel",
}


def render_title_organization(artifact):
    """H1 title for organization nodes. Prefers context_extrinsic.display_title,
    falls back to document_intrinsic.full_name or internal_name, then
    humanized slug."""
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    slug = artifact["target_node"].split("/", 1)[1] if "/" in artifact["target_node"] else ""
    title = (
        ctx.get("display_title")
        or dm.get("full_name")
        or dm.get("internal_name")
        or (slug and " ".join(w.capitalize() for w in slug.split("-")))
        or ""
    )
    return f"# {title}\n"


def render_org_overview(artifact, kind):
    """Overview fact-table section. Populates from organization-kind keys
    in document_intrinsic. Rows emit in the order defined by
    _ORG_OVERVIEW_ORDER_BY_KIND for the artifact's kind; empty keys
    skipped. `_path`-suffixed keys render as backtick-bracket wraps so
    investigators can click through to linked nodes (Parent, Director,
    Counterparty, Leadership)."""
    dm = artifact.get("document_intrinsic") or {}
    order = _ORG_OVERVIEW_ORDER_BY_KIND.get(kind, [])

    rows = []
    for key in order:
        val = dm.get(key)
        if val in (None, "", []):
            continue
        # head_title overrides the generic "Director" label on
        # current_director_path for under-secretariats / departments /
        # services / commands where the head's true title isn't "Director".
        if key == "current_director_path" and dm.get("head_title"):
            label = dm["head_title"]
        else:
            label = _ORG_OVERVIEW_LABELS.get(key, key)
        if key.endswith("_path"):
            val = _wrap_path(str(val))
        rows.append(f"| {label} | {val} |")

    lines = ["## Overview", "", "| Field | Value |", "|---|---|"]
    if rows:
        lines.extend(rows)
    else:
        lines.append("|  |  |")
    return "\n".join(lines) + "\n"


def _org_key_personnel_row(e):
    """Render a single Key Personnel row — person wrap + role + period
    + source.path + note (parallels the person affiliations row shape)."""
    person = _wrap_path(e.get("person_path"))
    return (
        f"| {person} | "
        f"{e.get('role') or ''} | "
        f"{_format_period(e)} | "
        f"{(e.get('source') or {}).get('path') or ''} | "
        f"{_escape_table_cell(e.get('note'))} |"
    )


def render_org_key_personnel(artifact):
    """Key Personnel section — sub-grouped by leadership_class within
    Confirmed / Flagged split. Empty sub-subsections are suppressed.
    Contributor-unset leadership_class routes to the 'other' bucket.
    Each subsection sorts by period_start ascending."""
    items = [e for e in (artifact.get("key_personnel") or []) if isinstance(e, dict)]
    confirmed = [e for e in items if not e.get("flagged")]
    flagged   = [e for e in items if e.get("flagged")]

    def bucket_by_class(entries):
        buckets = {c: [] for c in _LEADERSHIP_CLASS_ORDER}
        for e in entries:
            cls = e.get("leadership_class") or "other"
            if cls not in buckets:
                cls = "other"
            buckets[cls].append(e)
        for cls in buckets:
            buckets[cls] = sort_by_date(buckets[cls], "period_start")
        return buckets

    def render_subsections(buckets, h4_level="####"):
        out = []
        any_rendered = False
        for cls in _LEADERSHIP_CLASS_ORDER:
            if not buckets[cls]:
                continue
            any_rendered = True
            out += [
                f"{h4_level} {_LEADERSHIP_CLASS_HEADING[cls]}",
                "",
                "| Name | Role | Period | Source | Note |",
                "|---|---|---|---|---|",
            ]
            for e in buckets[cls]:
                out.append(_org_key_personnel_row(e))
            out.append("")
        if not any_rendered:
            # Empty bucket fallback — emit a prose placeholder rather
            # than a malformed empty table row.
            out += [
                "_No personnel attested in primary sources to date._",
                "",
            ]
        return out

    lines = ["## Key Personnel", "", "### Confirmed", ""]
    lines += render_subsections(bucket_by_class(confirmed))

    if flagged:
        lines += ["### Flagged", ""]
        lines += render_subsections(bucket_by_class(flagged))

    return "\n".join(lines).rstrip() + "\n"


def render_org_key_passages(artifact):
    """Key Passages section — verbatim excerpts from primary sources
    ABOUT the organization. Each passage: H3 (significance) + block-
    quote + per-quote verification block. Uses the same shape as
    transcript Key Passages — per-quote source attribution so orgs
    can draw from multiple primary sources. Sorted by statement_date
    when set; falls through to id-order."""
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


def render_org_primary_contracts(artifact):
    """Primary Contracts section — gov-contractor only. Table with one
    row per contract_entry. Chronologically ordered by period_start.
    Columns: Contract | Contracting Agency | Period | Value |
    Counterparty | Subject | Source. Deliverables (when present)
    render as a bulleted sub-list beneath each row."""
    items = [e for e in (artifact.get("contracts") or []) if isinstance(e, dict)]
    items = sort_by_date(items, "period_start")

    lines = ["## Primary Contracts", "",
             "| Contract | Contracting Agency | Period | Value | Counterparty | Subject | Source | Note |",
             "|---|---|---|---|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |  |  |  |  |")
        return "\n".join(lines) + "\n"

    deliverable_blocks = []
    for e in items:
        counterparty = _wrap_path(e.get("primary_counterparty_path"))
        lines.append(
            f"| {e.get('contract_number') or ''} | "
            f"{e.get('contracting_agency') or ''} | "
            f"{_format_period(e)} | "
            f"{e.get('value') or ''} | "
            f"{counterparty} | "
            f"{e.get('subject') or ''} | "
            f"{(e.get('source') or {}).get('path') or ''} | "
            f"{_escape_table_cell(e.get('note'))} |"
        )
        deliverables = e.get("deliverables") or []
        if deliverables:
            block = [f"**{e.get('contract_number') or '(contract)'} — Deliverables:**", ""]
            for d in deliverables:
                block.append(f"- {_wrap_path(d)}")
            deliverable_blocks.append("\n".join(block))

    out = "\n".join(lines) + "\n"
    if deliverable_blocks:
        out += "\n" + "\n\n".join(deliverable_blocks) + "\n"
    return out


def render_org_relationships(artifact):
    """Relationships section — org_relationships[] with Confirmed /
    Flagged split. Different renderer from person.render_relationships
    (person-to-person) because shape differs: org-to-org uses
    organization_path + relationship_type (enum) rather than
    person_path + relationship (free-text)."""
    items = [e for e in (artifact.get("org_relationships") or []) if isinstance(e, dict)]
    confirmed = [e for e in items if not e.get("flagged")]
    flagged   = [e for e in items if e.get("flagged")]

    def row(e):
        org = _wrap_path(e.get("organization_path"))
        return (
            f"| {org} | "
            f"{e.get('relationship_type') or ''} | "
            f"{(e.get('source') or {}).get('path') or ''} | "
            f"{_escape_table_cell(e.get('note'))} |"
        )

    lines = ["## Relationships", "", "### Confirmed", "",
             "| Organization | Relationship | Source | Note |",
             "|---|---|---|---|"]
    if confirmed:
        for e in confirmed:
            lines.append(row(e))
    else:
        lines.append("|  |  |  |  |")
    if flagged:
        lines += ["", "### Flagged", "",
                  "| Organization | Relationship | Source | Note |",
                  "|---|---|---|---|"]
        for e in flagged:
            lines.append(row(e))
    return "\n".join(lines) + "\n"


def render_body_organization(artifact, kind):
    """Organization-type body composition. Section order matches the
    schema's required_sections for the given kind. Primary Contracts
    is gov-contractor-only; all other sections common across kinds.
    """
    title = render_title_organization(artifact).rstrip("\n") + "\n"
    sections = [
        render_org_overview(artifact, kind),
        render_description(artifact),
        render_org_key_personnel(artifact),
        render_org_key_passages(artifact),
    ]
    if kind == "gov-contractor":
        sections.append(render_org_primary_contracts(artifact))
    elif kind not in ("gov", "private"):
        sys.exit(f"ERROR: render_body_organization: unknown organization kind {kind!r}")
    sections.extend([
        render_timeline(artifact),
        render_org_relationships(artifact),
        render_primary_source_contradictions(artifact),
        render_public_record_claims(artifact),
        render_source_form_notes(artifact),
        render_preserved_disagreements(artifact),
        render_associated_nodes(),
    ])
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined
