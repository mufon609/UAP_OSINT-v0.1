"""Finding-type renderer.

Renders finding nodes — multi-source patterns that become visible only
when several primary sources are read together. Section order: Pattern
Statement → Description → Evidence → What the Record Establishes →
What the Record Doesn't Establish → (Apparent Contradictions if
populated) → (Timeline if populated) → Source-Form Notes → Associated
Nodes.

Findings cite primary sources directly via ``evidence[].source.path``;
no entity-node references in the directional contract (enforced by
``finding_no_investigation_refs`` and by convention).
"""

from ._common import (
    SECTION_SEP,
    _wrap_path,
    sort_by_date,
)
from ._universal import (
    render_associated_nodes,
    render_description,
    render_preserved_disagreements,
    render_source_form_notes,
)


def render_title_finding(artifact):
    """H1 title for finding nodes. ``document_intrinsic.full_name``
    overrides when populated — preserves acronyms (SCIF / SAP-F /
    FY) that title-casing the slug would lose. Falls back to slug-
    derived display name when full_name is absent."""
    di = artifact.get("document_intrinsic") or {}
    name = di.get("full_name")
    if name:
        return f"# {name}\n"
    target = artifact.get("target_node") or ""
    slug = target.rsplit("/", 1)[-1] if "/" in target else target
    display = slug.replace("-", " ").title() if slug else "Finding"
    return f"# {display}\n"


def render_pattern_statement(artifact):
    """`## Pattern Statement` — one declarative sentence stating the
    cross-source pattern this finding documents. Sourced from the
    artifact's `pattern_statement` field."""
    pattern = (artifact.get("pattern_statement") or "").strip()
    lines = ["## Pattern Statement", ""]
    if pattern:
        lines.append(pattern)
    else:
        lines.append("<!-- TODO: populate `pattern_statement` in the research artifact -->")
    return "\n".join(lines) + "\n"


def render_finding_evidence(artifact):
    """`## Evidence` — H3-per-quote cards from quotes[]. Each card
    renders the verbatim attestation as a blockquote followed by a
    verification table with Attributed-to / Tier / Attestor / Source /
    Location rows. The Tier row surfaces `attestation_tier` so readers
    see evidentiary weight per row when convergence spans mixed tiers.
    Sorted ascending by statement_date with natural-sort tie-break."""
    quotes = [q for q in (artifact.get("quotes") or []) if isinstance(q, dict)]
    quotes = sort_by_date(quotes, "statement_date")

    head = "## Evidence\n"
    if not quotes:
        return head + "\n<!-- TODO: populate `quotes` in the research artifact -->\n"

    blocks = []
    for q in quotes:
        h3 = q.get("significance") or "Attestation"
        text = (q.get("text") or "").rstrip("\n")
        lines = [f"### {h3}", ""]
        for qline in text.split("\n"):
            lines.append(f"> {qline}" if qline else ">")
        lines.append("")

        # Verification block, extended with Tier + Attestor rows
        ctx = q.get("context") or ""
        date = q.get("statement_date") or ""
        if date and date in ctx:
            attributed_to = ctx
        else:
            parts = [p for p in [ctx, date] if p]
            attributed_to = ", ".join(parts) if parts else ""
        src = q.get("source") or {}
        src_path = src.get("path") or ""
        src_link = f"[archived source](../sources/{src_path})" if src_path else ""
        loc = src.get("location") or ""
        tier = q.get("attestation_tier") or ""
        attestor = q.get("attestor_path") or ""

        rows = ["| Field | Value |", "|---|---|"]
        if attributed_to:
            rows.append(f"| Attributed to | {attributed_to} |")
        if tier:
            rows.append(f"| Tier | {tier} |")
        if attestor:
            rows.append(f"| Attestor | {_wrap_path(attestor)} |")
        if src_link:
            rows.append(f"| Source | {src_link} |")
        if loc:
            rows.append(f"| Location | {loc} |")
        lines.append("\n".join(rows))
        blocks.append("\n".join(lines))

    return head + "\n" + "\n\n---\n\n".join(blocks) + "\n"


def render_finding_establishes(artifact):
    """`## What the Record Establishes` — bullet list from
    `establishes[]`. Each entry is a prose string with inline
    references to evidence quote ids."""
    items = artifact.get("establishes") or []
    lines = ["## What the Record Establishes", ""]
    if not items:
        lines.append("<!-- TODO: populate `establishes` in the research artifact -->")
        return "\n".join(lines) + "\n"
    for item in items:
        if isinstance(item, str) and item.strip():
            lines.append(f"- {item.strip()}")
    return "\n".join(lines) + "\n"


def render_finding_does_not_establish(artifact):
    """`## What the Record Doesn't Establish` — bullet list from
    `does_not_establish[]`. Caveats, gaps, divergences (without
    speculation)."""
    items = artifact.get("does_not_establish") or []
    lines = ["## What the Record Doesn't Establish", ""]
    if not items:
        lines.append("<!-- TODO: populate `does_not_establish` in the research artifact -->")
        return "\n".join(lines) + "\n"
    for item in items:
        if isinstance(item, str) and item.strip():
            lines.append(f"- {item.strip()}")
    return "\n".join(lines) + "\n"


def render_finding_contradictions(artifact):
    """`## Apparent Contradictions` — structured divergences within
    the finding's scope. Conditional: returns empty string when
    contradictions[] is empty (section auto-suppressed)."""
    items = [c for c in (artifact.get("contradictions") or []) if isinstance(c, dict)]
    if not items:
        return ""
    lines = ["## Apparent Contradictions", ""]
    for c in items:
        question = (c.get("question") or "").strip()
        if question:
            lines.append(f"### {question}")
            lines.append("")
        positions = c.get("positions") or []
        if positions:
            lines.append("| Evidence | Position |")
            lines.append("|---|---|")
            for p in positions:
                if not isinstance(p, dict):
                    continue
                eid = p.get("evidence_id") or ""
                pos = (p.get("position") or "").replace("|", "\\|")
                lines.append(f"| `{eid}` | {pos} |")
        note = (c.get("note") or "").strip()
        if note:
            lines.append("")
            lines.append(note)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_finding_timeline(artifact):
    """`## Timeline` — chronological table from timeline[]. Conditional:
    returns empty string when timeline[] is empty (section auto-
    suppressed for non-temporal findings)."""
    items = sort_by_date(
        [t for t in (artifact.get("timeline") or []) if isinstance(t, dict)],
        "date",
    )
    if not items:
        return ""
    lines = ["## Timeline", "",
             "| Date | Event | Source | Node Link |",
             "|---|---|---|---|"]
    for t in items:
        date = t.get("date") or ""
        event = (t.get("event") or "").replace("|", "\\|")
        src = (t.get("source") or {}).get("path") or ""
        node_link = t.get("node_link") or ""
        if node_link:
            node_link = _wrap_path(node_link)
        lines.append(f"| {date} | {event} | {src} | {node_link} |")
    return "\n".join(lines) + "\n"


def render_body_finding(artifact, fm):
    """Finding-type body composition. Section order matches the
    schema's required_sections: Pattern Statement → Description →
    Evidence → What the Record Establishes → What the Record Doesn't
    Establish → (Apparent Contradictions if populated) → (Timeline if
    populated) → Source-Form Notes (if entries) → Associated Nodes."""
    title = render_title_finding(artifact).rstrip("\n") + "\n"
    sections = [
        render_pattern_statement(artifact),
        render_description(artifact),
        render_finding_evidence(artifact),
        render_finding_establishes(artifact),
        render_finding_does_not_establish(artifact),
        render_finding_contradictions(artifact),       # conditional
        render_finding_timeline(artifact),             # conditional
        render_source_form_notes(artifact),            # conditional
        render_preserved_disagreements(artifact),      # conditional
        render_associated_nodes(),
    ]
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined
