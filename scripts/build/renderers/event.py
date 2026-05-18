"""Event-type renderer.

Renders event nodes across both kinds (hearing, encounter). Hearings
emit a sub-grouped Participants section (by capacity) + Key Testimony
+ Witnesses & Testimony; encounters emit a flat Confirmed/Flagged
Participants table + Corroboration.
"""

import sys

from ._common import (
    SECTION_SEP,
    _escape_table_cell,
    _render_statement_block,
    _wrap_path,
    sort_by_date,
)
from ._universal import (
    render_associated_nodes,
    render_corroboration,
    render_description,
    render_preserved_disagreements,
    render_primary_source_contradictions,
    render_public_record_claims,
    render_source_form_notes,
    render_timeline,
)


# Participant capacity → sub-section header used in hearing Participants.
# Encounter Participants uses the flat Confirmed/Flagged table instead.
_HEARING_CAPACITY_SUBSECTION = {
    "witness-eyewitness":     "Witnesses — Eyewitness Testimony",
    "witness-whistleblower":  "Witnesses — Whistleblower Testimony",
    "witness-institutional":  "Witnesses — Institutional Testimony",
    "committee-member":       "Committee Members",
}

# Order of sub-sections within hearing Participants (matches the schema's
# participants_structure.confirmed_subsections list).
_HEARING_CAPACITY_ORDER = [
    "witness-eyewitness",
    "witness-whistleblower",
    "witness-institutional",
    "committee-member",
]

# Capacities whose empty case carries analytical meaning — always render
# the sub-subsection even with zero entries. committee-member: absence
# of committee members would be newsworthy (oversight failure), so the
# empty state is a finding worth surfacing. Witness capacities are
# suppressed when empty — different hearings naturally carry different
# witness compositions, and empty witness tables read as "data missing"
# rather than "category N/A here".
_HEARING_CAPACITY_RENDER_WHEN_EMPTY = {"committee-member"}


def render_title_event(artifact):
    """H1 title for event nodes. Prefers context_extrinsic.display_title,
    then event_intrinsic.hearing_title (hearings) or a date+slug
    composition (encounters)."""
    slug = artifact["target_node"].split("/", 1)[1] if "/" in artifact["target_node"] else ""
    ei = artifact.get("event_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    title = (
        ctx.get("display_title")
        or ei.get("hearing_title")
        or ei.get("display_title")
        or (slug and " ".join(w.capitalize() for w in slug.split("-")))
        or ""
    )
    return f"# {title}\n"


def render_event_summary(artifact, kind):
    """Event Summary table — populated from event_intrinsic. Fields
    differ by kind; renderer emits whichever keys are present."""
    ei = artifact.get("event_intrinsic") or {}
    lines = ["## Event Summary", "", "| Field | Value |", "|---|---|"]
    rows_emitted = False

    def row(label, value):
        nonlocal rows_emitted
        if value in (None, "", [], {}):
            return
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value)
        lines.append(f"| {label} | {value} |")
        rows_emitted = True

    if kind == "hearing":
        row("Full Title",      ei.get("hearing_title"))
        row("Convening Body",  ei.get("committee"))
        row("Session",         ei.get("session"))
        row("Congress",        ei.get("congress_number") or ei.get("congress"))
        row("Status",          ei.get("status"))
        row("Date",            ei.get("date"))
        row("Scheduled Time",  ei.get("scheduled_time"))
        row("Convened Time",   ei.get("convened_time"))
        row("Adjourned Time",  ei.get("adjourned_time"))
        row("Location",        ei.get("location"))
        row("Chair",           ei.get("chair"))
        row("Ranking Member",  ei.get("ranking_member"))
    else:  # encounter
        row("Date",            ei.get("date"))
        row("Location",        _wrap_path(ei.get("location_path")) or ei.get("location"))
        row("Duration",        ei.get("duration"))
        row("Weather",         ei.get("weather"))
        row("Instruments Involved", ei.get("instruments_involved"))

    if not rows_emitted:
        lines.append("|  |  |")
    return "\n".join(lines) + "\n"


def _participant_row(e):
    """Render one participant row. Cells: participant (wrap_path), role,
    source.path, note."""
    p = _wrap_path(e.get("participant_path"))
    return (
        f"| {p} | "
        f"{e.get('role') or ''} | "
        f"{(e.get('source') or {}).get('path') or ''} | "
        f"{_escape_table_cell(e.get('note'))} |"
    )


def render_participants_encounter(artifact):
    """Flat Confirmed/Flagged split for encounter events."""
    items = artifact.get("participants") or []
    confirmed = [e for e in items if isinstance(e, dict) and not e.get("flagged")]
    flagged   = [e for e in items if isinstance(e, dict) and e.get("flagged")]

    lines = ["## Participants", "", "### Confirmed", "",
             "| Participant | Role | Source | Note |",
             "|---|---|---|---|"]
    if confirmed:
        for e in confirmed:
            lines.append(_participant_row(e))
    else:
        lines.append("|  |  |  |  |")
    if flagged:
        lines += ["", "### Flagged", "",
                  "| Participant | Role | Source | Note |",
                  "|---|---|---|---|"]
        for e in flagged:
            lines.append(_participant_row(e))
    return "\n".join(lines) + "\n"


def render_participants_hearing(artifact):
    """Hearing Participants — sub-sections by capacity. Flagged entries
    (any capacity) roll up into a single `### Flagged` subsection at the
    end."""
    items = [e for e in (artifact.get("participants") or []) if isinstance(e, dict)]
    confirmed = [e for e in items if not e.get("flagged")]
    flagged   = [e for e in items if e.get("flagged")]

    lines = ["## Participants", "", "### Confirmed"]
    for capacity in _HEARING_CAPACITY_ORDER:
        subsection_entries = [e for e in confirmed if e.get("capacity") == capacity]
        if not subsection_entries and capacity not in _HEARING_CAPACITY_RENDER_WHEN_EMPTY:
            continue
        subheader = _HEARING_CAPACITY_SUBSECTION[capacity]
        lines.append("")
        lines.append(f"#### {subheader}")
        lines.append("")
        lines.append("| Participant | Role | Source | Note |")
        lines.append("|---|---|---|---|")
        if subsection_entries:
            for e in subsection_entries:
                lines.append(_participant_row(e))
        else:
            lines.append("|  |  |  |  |")

    known = set(_HEARING_CAPACITY_ORDER)
    other_confirmed = [e for e in confirmed if e.get("capacity") not in known]
    if other_confirmed:
        lines += ["", "#### Other", "",
                  "| Participant | Role | Source | Note |",
                  "|---|---|---|---|"]
        for e in other_confirmed:
            lines.append(_participant_row(e))

    if flagged:
        lines += ["", "### Flagged", "",
                  "| Participant | Role | Source | Note |",
                  "|---|---|---|---|"]
        for e in flagged:
            lines.append(_participant_row(e))
    return "\n".join(lines) + "\n"


def render_key_testimony(artifact):
    """Key Testimony (hearing only) — verbatim quote blocks with
    verification tables. Reuses the person-node statement block shape.
    Sorted by statement_date when set. Empty-state emits an instructive
    stub pointing at the artifact's `quotes` list."""
    quotes = [q for q in (artifact.get("quotes") or []) if isinstance(q, dict)]
    quotes = sort_by_date(quotes, "statement_date")
    lines = ["## Key Testimony", ""]
    if not quotes:
        lines.append("<!-- No key testimony quotes recorded in artifact. -->")
        return "\n".join(lines) + "\n"
    for q in quotes:
        lines.append(_render_statement_block(q, artifact))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_witnesses_testimony(artifact):
    """Witnesses & Testimony (hearing only) — cross-reference table.
    One row per witness pointing at transcript and written-testimony
    nodes."""
    items = [e for e in (artifact.get("witnesses_testimony") or []) if isinstance(e, dict)]
    lines = ["## Witnesses & Testimony", "",
             "| Witness | Oath Status | Transcript | Written Testimony | Note |",
             "|---|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |  |")
    for e in items:
        lines.append(
            f"| {_wrap_path(e.get('witness_path'))} | "
            f"{e.get('oath_status') or ''} | "
            f"{_wrap_path(e.get('transcript_node'))} | "
            f"{_wrap_path(e.get('written_testimony_node'))} | "
            f"{_escape_table_cell(e.get('note'))} |"
        )
    return "\n".join(lines) + "\n"


def render_body_event(artifact, kind):
    """Event-type body composition. Section order matches the schema's
    required_sections for the given kind. Hearing and encounter diverge
    after the universal Event Summary / Description / Participants /
    Timeline opener — hearings emit Key Testimony + Witnesses &
    Testimony; encounters emit Corroboration.
    """
    title = render_title_event(artifact).rstrip("\n") + "\n"
    sections = [
        render_event_summary(artifact, kind),
        render_description(artifact),
    ]
    if kind == "hearing":
        sections.extend([
            render_participants_hearing(artifact),
            render_timeline(artifact),
            render_key_testimony(artifact),
            render_witnesses_testimony(artifact),
        ])
    elif kind == "encounter":
        sections.extend([
            render_participants_encounter(artifact),
            render_timeline(artifact),
            render_corroboration(artifact),
        ])
    else:
        sys.exit(f"ERROR: render_body_event: unknown event kind {kind!r}")
    sections.extend([
        render_primary_source_contradictions(artifact),
        render_public_record_claims(artifact),
        render_source_form_notes(artifact),
        render_preserved_disagreements(artifact),
        render_associated_nodes(),
    ])
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined
