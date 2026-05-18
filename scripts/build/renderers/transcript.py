"""Transcript-type renderer.

Renders transcript nodes across both kinds (hearing, other). Hearing
transcripts render hearing metadata + companion written-testimony
cross-ref; ``other`` transcripts render outlet/host/source-medium
metadata. Both kinds emit the same section set (Publication Record,
Summary, Speakers, Key Passages).
"""

import sys

from ._common import (
    SECTION_SEP,
    _escape_table_cell,
    _render_attribution_block,
    _wrap_path,
    sort_by_date,
    sort_by_id,
)
from ._universal import (
    render_associated_nodes,
    render_preserved_disagreements,
    render_source_form_notes,
)


def render_title_transcript(artifact):
    """H1 title for transcript nodes. Prefers context_extrinsic.display_title,
    falls back to context_extrinsic.hearing_title, then humanized slug."""
    slug = artifact["target_node"].split("/", 1)[1] if "/" in artifact["target_node"] else ""
    ctx = artifact.get("context_extrinsic") or {}
    title = (
        ctx.get("display_title")
        or ctx.get("hearing_title")
        or (slug and " ".join(w.capitalize() for w in slug.split("-")))
        or ""
    )
    return f"# {title}\n"


def render_transcript_publication_record(artifact, kind, fm):
    """Publication Record table — kind-dispatched. Hearing emits full
    hearing metadata + companion written-testimony cross-ref; `other`
    emits outlet/host/source-medium metadata. Auto-populates
    `Source Medium` and `Underlying X` rows from frontmatter
    (`source_medium` / `derived_from`) — frontmatter stays the single
    source of truth for those fields."""
    ctx = artifact.get("context_extrinsic") or {}
    lines = ["## Publication Record", "", "| Field | Value |", "|---|---|"]

    def row(label, value):
        if value in (None, "", [], {}):
            return
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value)
        lines.append(f"| {label} | {_escape_table_cell(value)} |")

    derived_from = (fm or {}).get("derived_from") or ctx.get("derived_from")
    source_medium = (fm or {}).get("source_medium") or ctx.get("source_medium")

    if kind == "hearing":
        row("Full Hearing Title", ctx.get("hearing_title"))
        row("Convening Body",     ctx.get("committee") or ctx.get("convening_body"))
        row("Session",            ctx.get("session"))
        row("Serial No.",         ctx.get("serial_no"))
        row("Date",               ctx.get("hearing_date") or ctx.get("date"))
        row("Location",           ctx.get("location"))
        row("Witness",            ctx.get("witness"))
        row("Oath Status",        ctx.get("oath_status"))
        row("Transcript URL",     ctx.get("primary_source_url"))
        row("Transcript Verified", ctx.get("transcript_verified"))
        row("Event Node",         _wrap_path(ctx.get("event_node")))
        # Companion Written Testimony. Hearing transcripts and their
        # companion written testimony are independent primary records
        # of the same event; neither derives from the other.
        if ctx.get("companion_written_testimony"):
            row("Companion Written Testimony", _wrap_path(ctx.get("companion_written_testimony")))
    else:  # other
        row("Outlet / Platform",  ctx.get("outlet") or ctx.get("platform"))
        row("Program / Show / Venue", ctx.get("program") or ctx.get("venue"))
        row("Date",               ctx.get("air_date") or ctx.get("date"))
        row("Host(s) / Interviewer(s)", ctx.get("hosts") or ctx.get("interviewers"))
        row("Primary Speaker(s)", ctx.get("primary_speakers"))
        row("Format",             ctx.get("format"))
        row("Source Medium",      source_medium)
        if derived_from:
            dfs = str(derived_from)
            if dfs.startswith("/media/"):
                row("Underlying Media Node", _wrap_path(derived_from))
            elif dfs.startswith("/documents/"):
                row("Underlying Document", _wrap_path(derived_from))
            else:
                row("Underlying Source", _wrap_path(derived_from))
        row("Source URL",         ctx.get("primary_source_url"))
        row("Transcript Verified", ctx.get("transcript_verified"))
        row("Citation Style",     ctx.get("citation_style"))

    if len(lines) == 4:
        lines.append("|  |  |")
    return "\n".join(lines) + "\n"


def render_transcript_summary(artifact):
    """Summary section — renders `artifact.description` as `## Summary`.
    Transcripts semantically summarize speech content; the render-time
    field→section rename keeps `description` as the universal top-level
    required field while the rendered section name fits transcript
    semantics."""
    desc = (artifact.get("description") or "").strip()
    body = desc if desc else "<!-- TODO: populate `description` in the research artifact -->"
    return f"## Summary\n\n{body}\n"


def render_transcript_speakers(artifact):
    """Speakers section — cross-reference table for who spoke in this
    transcript. Rendered from the `speakers` artifact field. NOT a
    statement surface — actual statements live in `quotes` and render
    as `## Key Passages`."""
    items = sort_by_id([s for s in (artifact.get("speakers") or []) if isinstance(s, dict)])
    lines = ["## Speakers", "",
             "| Name | Role | Node Link | Note |",
             "|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |")
        return "\n".join(lines) + "\n"
    for s in items:
        lines.append(
            f"| {_escape_table_cell(s.get('name'))} | "
            f"{_escape_table_cell(s.get('role'))} | "
            f"{_wrap_path(s.get('node_link'))} | "
            f"{_escape_table_cell(s.get('note'))} |"
        )
    return "\n".join(lines) + "\n"


def render_transcript_key_passages(artifact):
    """Key Passages section — verbatim block-quote + verification-block
    pairs, one per quote in the artifact. Uses H3 per quote (significance
    field) like document Key Passages — transcripts typically carry many
    quotes and H3 breaks provide navigability. Sorted by statement_date
    when set; falls through to id-order for undated quotes.
    """
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


def render_body_transcript(artifact, kind, fm):
    """Transcript-type body composition. Section order matches the
    schema's required_sections for the given kind. Both hearing and
    other kinds emit the same section set (Publication Record, Summary,
    Speakers, Key Passages). The renderer threads `fm` through to
    Publication Record so it can read `derived_from` + `source_medium`
    from the transcript node's frontmatter.
    """
    if kind not in ("hearing", "other"):
        sys.exit(f"ERROR: render_body_transcript: unknown transcript kind {kind!r}")
    title = render_title_transcript(artifact).rstrip("\n") + "\n"
    sections = [
        render_transcript_publication_record(artifact, kind, fm),
        render_transcript_summary(artifact),
        render_transcript_speakers(artifact),
        render_transcript_key_passages(artifact),
        render_source_form_notes(artifact),
        render_preserved_disagreements(artifact),
        render_associated_nodes(),
    ]
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined
