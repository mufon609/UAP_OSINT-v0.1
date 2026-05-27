"""Person-type renderer.

Renders person nodes across all four archetypes (eyewitness,
whistleblower, institutional-actor, reporter). Archetype-specific
sections live behind ``_ARCHETYPE_RENDERER`` dispatch:

  eyewitness          → render_corroboration   (from _universal)
  whistleblower       → render_claim_inventory (this module)
  institutional-actor → render_program_involvement (this module)
  reporter            → render_publication_record   (this module)

Whistleblower additionally renders ``## Vouching Chain`` as a separate
H2 between Credibility Notes and Associated Nodes.
"""

from lib._common import load_topic

from ._common import (
    SECTION_SEP,
    _escape_table_cell,
    _format_period,
    _render_statement_block,
    _wrap_path,
    sort_by_date,
)
from ._universal import (
    render_associated_nodes,
    render_corroboration,
    render_name_variants,
    render_preserved_disagreements,
    render_source_form_notes,
    render_timeline,
)

# Renderer-coverage contract — canonical H2 section titles render_body_person
# can emit (across all four archetypes). The Relevance heading keeps its raw
# {topic_display_name} placeholder so it matches schema's raw form. Checked
# against schema-required sections by renderer-coverage.py.
EMITS = frozenset({
    "Identity",
    "Background",
    "{topic_display_name} Relevance",
    "Affiliations",
    "Statements",
    "Timeline",
    "Relationships",
    "Corroboration",          # eyewitness archetype
    "Claim Inventory",        # whistleblower archetype
    "Program Involvement",    # institutional-actor archetype
    "Publication Record",     # reporter archetype
    "Credibility Notes",
    "Vouching Chain",         # whistleblower-only
    "Source-Form Notes",
    "Preserved Disagreements",
    "Name Variants",
    "Associated Nodes",
})


def _person_display_name(artifact, slug_hint=None):
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    return (
        ctx.get("display_title")
        or dm.get("full_name")
        or dm.get("internal_title")
        or (slug_hint and " ".join(w.capitalize() for w in slug_hint.split("-")))
        or ""
    )


def render_title_person(artifact):
    slug = artifact["target_node"].split("/", 1)[1] if "/" in artifact["target_node"] else ""
    name = _person_display_name(artifact, slug_hint=slug)
    return f"# {name}\n"


def render_identity(artifact):
    """Identity table — renders from document_intrinsic fields. Contributors
    populate document_intrinsic with person-specific keys (full_name,
    aliases, nationality, profession). Missing keys render as empty cells.
    """
    dm = artifact.get("document_intrinsic") or {}
    rows = [
        ("Full Name",   dm.get("full_name") or ""),
        ("Aliases",     "; ".join(dm["aliases"]) if isinstance(dm.get("aliases"), list) else (dm.get("aliases") or "")),
        ("Nationality", dm.get("nationality") or ""),
        ("Profession",  dm.get("profession") or ""),
    ]
    lines = ["## Identity", "", "| Field | Value |", "|---|---|"]
    for k, v in rows:
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines) + "\n"


def render_background(artifact):
    body = (artifact.get("background") or "").strip()
    if not body:
        body = "<!-- TODO: populate `background` in the research artifact -->"
    return f"## Background\n\n{body}\n"


def render_top_relevance(artifact):
    body = (artifact.get("top_relevance") or "").strip()
    if not body:
        body = "<!-- TODO: populate `top_relevance` in the research artifact -->"
    display_name = load_topic()["display_name"]
    return f"## {display_name} Relevance\n\n{body}\n"


def render_affiliations(artifact):
    """Affiliations table split into Confirmed / Flagged subsections.
    Sorted by period_start chronologically (the chronological-ordering
    check enforces)."""
    items = artifact.get("affiliations") or []
    confirmed = sort_by_date([e for e in items if isinstance(e, dict) and not e.get("flagged")], "period_start")
    flagged   = sort_by_date([e for e in items if isinstance(e, dict) and e.get("flagged")],     "period_start")

    def render_row(e):
        org = _wrap_path(e.get("organization_path"))
        return (
            f"| {org} | "
            f"{e.get('role') or ''} | "
            f"{_format_period(e)} | "
            f"{(e.get('source') or {}).get('path') or ''} |"
        )

    lines = ["## Affiliations", "", "### Confirmed", "",
             "| Organization | Role | Period | Source |",
             "|---|---|---|---|"]
    if confirmed:
        for e in confirmed:
            lines.append(render_row(e))
    else:
        lines.append("|  |  |  |  |")
    if flagged:
        lines += ["", "### Flagged", "",
                  "| Organization | Role | Period | Source |",
                  "|---|---|---|---|"]
        for e in flagged:
            lines.append(render_row(e))
    return "\n".join(lines) + "\n"


def render_statements(artifact):
    """Statements section.

    When any quote carries a ``claim_group``, render grouped-by-claim:
    statements organize by topic, and same-claim duplicates across the
    person's own sources collapse to one verbatim quote + compact "Also
    attested" pointers (see ``_render_statements_grouped``). Otherwise fall
    back to the legacy chronological Direct Observations / Other Statements
    split — this keeps every claim_group-free person node byte-identical."""
    quotes = [q for q in (artifact.get("quotes") or []) if isinstance(q, dict)]
    if any(q.get("claim_group") for q in quotes):
        return _render_statements_grouped(artifact, quotes)
    return _render_statements_flat(artifact, quotes)


def _render_statements_flat(artifact, quotes):
    """Legacy Direct/Other chronological split — preserved verbatim for
    person nodes that have not adopted claim_group grouping."""
    direct = sort_by_date([q for q in quotes if q.get("observation_type") == "direct"], "statement_date")
    other  = sort_by_date([q for q in quotes if q.get("observation_type") != "direct"], "statement_date")

    lines = ["## Statements", "", "### Direct Observations"]
    if direct:
        lines.append("")
        for q in direct:
            lines.append(_render_statement_block(q, artifact))
            lines.append("")
    else:
        lines += ["", "_No direct observations documented._"]

    lines += ["", "### Other Statements"]
    if other:
        lines.append("")
        for q in other:
            lines.append(_render_statement_block(q, artifact))
            lines.append("")
    else:
        lines += ["", "_No other statements documented._"]

    return "\n".join(lines).rstrip() + "\n"


def _render_statements_grouped(artifact, quotes):
    """Render quotes grouped by ``claim_group``.

    Each distinct ``claim_group`` becomes a ``### {claim_group}`` heading.
    Within a group, a quote that another group member's ``corroborated_by``
    points at is a *pointer* (renders compact: source + location); every
    other quote is a *primary* (renders as a full statement block via the
    shared ``_render_statement_block``). Each primary's ``corroborated_by``
    entries render beneath it as an "Also attested" list — so same-claim
    statements made across the person's own sources collapse to one
    verbatim quote plus pointers, with no verbatim loss (the pointer quotes
    keep full text + source in the artifact and are still verbatim-checked).
    Self-contradictions ("I did" / "I didn't") are separate primaries in the
    same group — both shown, no marker. Ungrouped quotes (no claim_group)
    render as their own headingless block. Groups order by earliest
    statement_date; primaries and pointers sort chronologically within."""
    by_id = {q.get("id"): q for q in quotes if q.get("id")}
    groups, order = {}, []
    for q in quotes:
        key = q.get("claim_group") or ("\x00" + str(q.get("id")))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(q)
    order.sort(key=lambda k: min((q.get("statement_date") or "9999-99-99") for q in groups[k]))

    lines = ["## Statements", ""]
    for key in order:
        gq = groups[key]
        pointer_ids = {cid for q in gq for cid in (q.get("corroborated_by") or [])}
        primaries = sort_by_date([q for q in gq if q.get("id") not in pointer_ids], "statement_date")
        if not key.startswith("\x00"):
            lines += [f"### {key}", ""]
        for p in primaries:
            lines.append(_render_statement_block(p, artifact))
            # The flat layout conveys observation_type via its Direct/Other
            # section split; the claim-group layout has no such split, so
            # mark first-hand observations inline to preserve the signal.
            if p.get("observation_type") == "direct":
                lines += ["", "_Direct observation._"]
            ptrs = sort_by_date(
                [by_id[c] for c in (p.get("corroborated_by") or []) if c in by_id],
                "statement_date",
            )
            if ptrs:
                lines += ["", "**Also attested:**", ""]
                for ptr in ptrs:
                    src = ptr.get("source") or {}
                    sp, loc = src.get("path") or "", src.get("location") or ""
                    link = f"[archived source](../sources/{sp})" if sp else ""
                    bits = [b for b in [ptr.get("context") or "", ptr.get("statement_date") or "", link, loc] if b]
                    lines.append(f"- {'; '.join(bits)}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_relationships(artifact):
    items = artifact.get("relationships") or []
    confirmed = [e for e in items if isinstance(e, dict) and not e.get("flagged")]
    flagged   = [e for e in items if isinstance(e, dict) and e.get("flagged")]

    def row(e):
        person = _wrap_path(e.get("person_path"))
        return (
            f"| {person} | "
            f"{e.get('relationship') or ''} |"
        )

    lines = ["## Relationships", "", "### Confirmed", "",
             "| Person | Relationship |",
             "|---|---|"]
    if confirmed:
        for e in confirmed:
            lines.append(row(e))
    else:
        lines.append("|  |  |")
    if flagged:
        lines += ["", "### Flagged", "",
                  "| Person | Relationship |",
                  "|---|---|"]
        for e in flagged:
            lines.append(row(e))
    return "\n".join(lines) + "\n"


def render_claim_inventory(artifact):
    """Claim Inventory (whistleblower) — render-time view of quotes
    tagged `category: filed-claim`. Document column references a
    related document/transcript node when the quote carries a
    `node_link` field; otherwise shows the sources/ path."""
    quotes = [q for q in (artifact.get("quotes") or [])
              if isinstance(q, dict) and q.get("category") == "filed-claim"]
    quotes = sort_by_date(quotes, "statement_date")
    lines = ["## Claim Inventory", "",
             "| Claim | Document | Node Link |",
             "|---|---|---|"]
    if not quotes:
        lines.append("|  |  |  |")
    for q in quotes:
        text = (q.get("text") or "").strip().replace("\n", " ")
        if len(text) > 120:
            text = text[:117] + "…"
        src_path = (q.get("source") or {}).get("path") or ""
        node_link = _wrap_path(q.get("node_link"))
        lines.append(f"| {text} | {src_path} | {node_link} |")
    return "\n".join(lines) + "\n"


def render_program_involvement(artifact):
    items = sort_by_date(
        [e for e in (artifact.get("program_involvement") or []) if isinstance(e, dict)],
        "period_start",
        fallback_key="period_end",
    )
    lines = ["## Program Involvement", "",
             "| Program | Role | Period | Evidentiary Basis | Confidence | Source |",
             "|---|---|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |  |  |")
    for e in items:
        if not isinstance(e, dict):
            continue
        period = _format_period(e)
        program = e.get("program") or ""
        program_cell = _wrap_path(program) if program.startswith("/") else program
        lines.append(
            f"| {program_cell} | "
            f"{e.get('role') or ''} | "
            f"{period} | "
            f"{e.get('evidentiary_basis') or ''} | "
            f"{e.get('confidence') or ''} | "
            f"{(e.get('source') or {}).get('path') or ''} |"
        )
    return "\n".join(lines) + "\n"


def render_publication_record(artifact):
    items = sort_by_date(
        [e for e in (artifact.get("publication_record") or []) if isinstance(e, dict)],
        "date",
    )
    lines = ["## Publication Record", "",
             "| Date | Publication | Outlet | Beat / Role | Source | Node Link |",
             "|---|---|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |  |  |")
    for e in items:
        outlet = e.get("outlet") or ""
        outlet_cell = _wrap_path(outlet) if outlet.startswith("/") else outlet
        lines.append(
            f"| {e.get('date') or ''} | "
            f"{e.get('publication') or ''} | "
            f"{outlet_cell} | "
            f"{e.get('beat') or ''} | "
            f"{(e.get('source') or {}).get('path') or ''} | "
            f"{_wrap_path(e.get('node_link'))} |"
        )
    return "\n".join(lines) + "\n"


_ARCHETYPE_RENDERER = {
    "eyewitness":          render_corroboration,
    "whistleblower":       render_claim_inventory,
    "institutional-actor": render_program_involvement,
    "reporter":            render_publication_record,
}


def render_archetype_section(artifact, archetype):
    fn = _ARCHETYPE_RENDERER.get(archetype)
    if fn is None:
        return ""
    return fn(artifact)


def render_vouching_chain(artifact):
    items = artifact.get("vouching_chain") or []
    lines = ["## Vouching Chain", "",
             "| Name | Credentials | Statement | Source |",
             "|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |")
    for e in items:
        if not isinstance(e, dict):
            continue
        attestation = (e.get("attestation") or "").strip().replace("\n", " ")
        if len(attestation) > 100:
            attestation = attestation[:97] + "…"
        voucher = _wrap_path(e.get("voucher_path"))
        lines.append(
            f"| {voucher} | "
            f"{e.get('evidentiary_basis') or ''} | "
            f"{attestation} | "
            f"{(e.get('source') or {}).get('path') or ''} |"
        )
    return "\n".join(lines) + "\n"


def render_credibility_notes(artifact):
    body = (artifact.get("credibility_notes") or "").strip()
    if not body:
        body = "<!-- TODO: populate `credibility_notes` in the research artifact -->"
    return f"## Credibility Notes\n\n{body}\n"


def render_body_person(artifact, archetype):
    """Person-type body composition. Section order matches the schema's
    required_sections for the given archetype. Whistleblower adds a
    Vouching Chain section between Credibility Notes and Associated
    Nodes; all other archetypes skip it."""
    title = render_title_person(artifact).rstrip("\n") + "\n"
    sections = [
        render_identity(artifact),
        render_background(artifact),
        render_top_relevance(artifact),
        render_affiliations(artifact),
        render_statements(artifact),
        render_timeline(artifact),
        render_relationships(artifact),
        render_archetype_section(artifact, archetype),
        render_credibility_notes(artifact),
    ]
    if archetype == "whistleblower":
        sections.append(render_vouching_chain(artifact))
    sections.extend([
        render_source_form_notes(artifact),
        render_preserved_disagreements(artifact),
        render_name_variants(artifact),
        render_associated_nodes(),
    ])
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined
