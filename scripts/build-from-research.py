#!/usr/bin/env python3
"""
Regenerate a node body from its research artifact (Phase II of layered build).

Reads /research/{slug}.yaml and rewrites /{type}/{slug}.md. Frontmatter is
preserved from the existing node; body sections (H1 title onward) are
replaced entirely by content derived from the artifact.

SCOPE: document (D.3), person (F.1b), event (F.2b), transcript (F.3b).
Extension to the remaining four node types (organization, media,
location, finding) is tracked in BACKLOG.md — each requires per-type
section renderers and type-specific artifact field conventions, per
the Step F template on the roadmap.

Person renderer (F.1b):
  - Universal sections: Identity, Background, UAP Relevance,
    Affiliations, Statements, Timeline, Relationships, Credibility
    Notes, Associated Nodes, Open Questions
  - Statements split by `observation_type` into Direct Observations /
    Other Statements; sorted ascending by `statement_date` within each
  - Timeline sorted ascending by `date`
  - Archetype-specific section dispatched by frontmatter archetype:
      eyewitness          → Corroboration       (from corroboration_items)
      whistleblower       → Claim Inventory     (from quotes w/ category: filed-claim)
      institutional-actor → Program Involvement (from program_involvement)
      reporter            → Publication Record  (from publication_record, sorted)
  - Whistleblower-only: Vouching Chain section (from vouching_chain)

Event renderer (F.2b):
  - Universal sections: Event Summary (from event_intrinsic),
    Description, Participants, Timeline, Associated Nodes, Open
    Questions
  - Hearing kind additionally: Key Testimony (verbatim quotes),
    Witnesses & Testimony (cross-reference table — replaces the prior
    What The Hearing Established synthesis section per F.2a)
  - Encounter kind additionally: Corroboration (shares the
    corroboration_items entry shape + renderer with eyewitness
    person nodes; column layout revised in F.2a:
    Observer | Type | What It Confirms | Attested In)
  - Hearing Participants sub-structured by participant capacity
    (witness-eyewitness / whistleblower / institutional / committee-
    member); encounter Participants uses flat Confirmed/Flagged.

Transcript renderer (F.3b):
  - Universal sections: Publication Record, Summary, Speakers,
    Key Passages, Associated Nodes, Open Questions
  - Hearing kind additionally: Material Differences (cross-artifact
    written_ref + intra-artifact oral_ref, excerpt + anchor link
    cells per F.3 Q3-A)
  - `## Summary` is rendered from `artifact.description` per F.3 Q1-A
    (render-time field→section rename; keeps `description` as the
    universal top-level field while the rendered section name fits
    transcript semantics).
  - Publication Record auto-populates `Source Medium` and `Underlying
    X Node` rows from frontmatter (`source_medium` / `derived_from`)
    per F.3 Decision 1 — frontmatter stays the single source of
    truth for those fields; no artifact-side duplication.
  - Key Passages uses H3 per quote (significance field) like document
    Key Passages, providing navigability for transcripts that may
    carry many quotes.

DETERMINISM: given the same artifact + node frontmatter, output is
byte-for-byte identical across runs. Entries are rendered in id-sorted
order (q1, q2, …); no date-of-build or wall-clock state is embedded.

USAGE:
  build-from-research.py research/{slug}.yaml
  build-from-research.py research/{slug}.yaml --dry-run
  build-from-research.py research/{slug}.yaml --no-validate

  --dry-run        : render to stdout only — do not write or invoke associate/validate
  --no-validate    : skip pre-flight research-artifact validation and
                     post-build node validation (speed / debugging)

PIPELINE WIRING:
  Pre-flight:  python3 scripts/validate-research.py {artifact} --quiet
  Regenerate:  this script (writes node body)
  Post-step:   python3 scripts/associate.py {node}   (rewrites Associated Nodes)
  Validate:    python3 scripts/validate.py {node} --quiet
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# =============================================================================
# Constants
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
VALIDATE_RESEARCH = SCRIPTS_DIR / "validate-research.py"
VALIDATE_NODE = SCRIPTS_DIR / "validate.py"
ASSOCIATE = SCRIPTS_DIR / "associate.py"

# Content-node type ↔ directory (mirrors research-scaffold.py / validate-research.py)
TYPE_DIRS = {
    "person": "people", "organization": "organizations", "document": "documents",
    "event": "events", "transcript": "transcripts", "media": "media",
    "location": "locations", "finding": "findings",
}

# Types this script can regenerate (D.3 scope: document;
# F.1b adds person; F.2b adds event; F.3b adds transcript)
SUPPORTED_TYPES = {"document", "person", "event", "transcript"}

# Archetype → archetype-specific artifact section name (person only)
ARCHETYPE_SECTION = {
    "eyewitness":           "corroboration_items",
    "institutional-actor":  "program_involvement",
    "reporter":             "publication_record",
    "whistleblower":        "vouching_chain",
}
# Archetype → H2 heading rendered for its archetype-specific section
ARCHETYPE_H2 = {
    "eyewitness":           "Corroboration",
    "institutional-actor":  "Program Involvement",
    "reporter":             "Publication Record",
    "whistleblower":        "Claim Inventory",
}

# Separator between H2 sections in the rendered node body.
# Matches repository convention: blank line, '---', blank line.
SECTION_SEP = "\n---\n\n"


# =============================================================================
# Loaders
# =============================================================================

def load_artifact(path):
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        sys.exit(f"ERROR: artifact root is not a YAML mapping: {path}")
    return data


def load_frontmatter(node_path):
    """Return (frontmatter_dict, raw_frontmatter_block_including_trailing_newline).
    Raw block is preserved verbatim so frontmatter survives regeneration
    with zero structural change (no yaml.dump reformatting)."""
    text = node_path.read_text()
    if not text.startswith("---"):
        return None, None
    end = text.find("\n---", 3)
    if end < 0:
        return None, None
    fm_yaml = text[3:end]
    try:
        fm = yaml.safe_load(fm_yaml)
    except yaml.YAMLError:
        return None, None
    # raw block ends right after closing `---` + its newline
    block_end = end + len("\n---")
    # Consume single newline after closing ---, if present (so body starts clean)
    if block_end < len(text) and text[block_end] == "\n":
        block_end += 1
    return fm, text[:block_end]


def sort_by_id(entries):
    """Natural-sort entries by id (q1, q2, …, q10) so output order is
    stable and human-expected (q10 doesn't land between q1 and q2)."""
    def key(e):
        if not isinstance(e, dict):
            return ("zzz", 0, "")
        eid = e.get("id") or ""
        m = re.match(r"^([a-zA-Z]+)(\d+)$", eid)
        if m:
            return (m.group(1), int(m.group(2)), eid)
        return ("zzz", 0, eid)
    return sorted(entries, key=key)


def parse_date_tuple(s):
    """Return (year, month, day) tuple from a date string, or (9999, 0, 0)
    for unparseable / missing dates so they sort LAST rather than first.
    Range cells take the leftmost date. Mirror of validate.py's
    parse_date_token but with an end-of-time sentinel for sort-stability.
    """
    if not s:
        return (9999, 0, 0)
    s = str(s).strip()
    if not s:
        return (9999, 0, 0)
    # Range: take the left side
    for sep in [" – ", " — ", " to ", " - ", "–", "—"]:
        if sep in s:
            s = s.split(sep, 1)[0].strip()
            break
    m = re.match(r"^(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?", s)
    if m:
        y = int(m.group(1))
        mo = int(m.group(2)) if m.group(2) else 0
        d = int(m.group(3)) if m.group(3) else 0
        return (y, mo, d)
    return (9999, 0, 0)


def sort_by_date(entries, date_key):
    """Stable-sort entries ascending by the date at `date_key`. Undated /
    unparseable entries land at the end (via the 9999 sentinel)."""
    def key(e):
        if not isinstance(e, dict):
            return ((9999, 0, 0), "")
        return (parse_date_tuple(e.get(date_key)), e.get("id") or "")
    return sorted(entries, key=key)


# =============================================================================
# Section renderers — each returns a trailing-newline-terminated block
# =============================================================================

def _source_path(artifact):
    sources = artifact.get("primary_sources") or []
    if sources and isinstance(sources[0], dict):
        return sources[0].get("path")
    return None


def render_title(artifact):
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
    # Format cell: combines file format + page count when available
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


def render_description(artifact):
    desc = (artifact.get("description") or "").strip()
    body = desc if desc else "<!-- TODO: populate `description` in the research artifact -->"
    return f"## Description\n\n{body}\n"


def render_provenance(artifact):
    ctx = artifact.get("context_extrinsic") or {}
    prov = ctx.get("provenance")
    lines = ["## Provenance", ""]
    if not isinstance(prov, list) or not prov:
        lines.append("<!-- TODO: populate `context_extrinsic.provenance` in the research artifact -->")
        return "\n".join(lines) + "\n"
    lines.append("| Step | Date | Entity | Verified |")
    lines.append("|---|---|---|---|")
    for step in prov:
        if not isinstance(step, dict):
            continue
        lines.append(
            f"| {step.get('step', '')} | {step.get('date', '')} | "
            f"{step.get('entity', '')} | {step.get('verified', '')} |"
        )
    return "\n".join(lines) + "\n"


def render_key_passages(artifact):
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
        lines.append("| Verified | ✅ Confirmed — verified verbatim against archived source |")
        if loc:
            lines.append(f"| Location | {loc} |")
        blocks.append("\n".join(lines))

    return head + "\n" + "\n\n---\n\n".join(blocks) + "\n"


def render_associated_nodes():
    # Placeholder — associate.py rewrites this section post-build by scanning
    # body links. We emit a stub so the section exists for associate.py to find.
    return (
        "## Associated Nodes\n\n"
        "<!-- Auto-generated by scripts/associate.py. Do not hand-edit. -->\n"
        "<!-- placeholder — associate.py rewrites this section post-build -->\n"
    )


def render_open_questions(artifact):
    gaps = sort_by_id(artifact.get("research_gaps") or [])
    head = "## Open Questions / Research Gaps\n"
    items = []
    for g in gaps:
        if not isinstance(g, dict):
            continue
        stmt = (g.get("statement") or "").strip()
        if not stmt:
            continue
        if g.get("resolved"):
            if not g.get("retain_as_done"):
                # Resolution lives in node body (as prose or a new quote); omit
                continue
            rd = g.get("resolved_date", "")
            rs = g.get("resolution_summary", "")
            items.append(f"- [x] {stmt} — DONE {rd}: {rs}")
        else:
            method = g.get("methodology") or ""
            items.append(f"- [ ] {stmt} — {method}" if method else f"- [ ] {stmt}")
    if not items:
        return head + "\n<!-- No open research gaps recorded in artifact. -->\n"
    return head + "\n" + "\n".join(items) + "\n"


# =============================================================================
# Person-type section renderers (F.1b)
# =============================================================================

def _wrap_path(path):
    """Render a node path (`/people/foo`) as the canonical backtick-bracket
    link form (``[`/people/foo`]``). Non-path values (empty, already-
    wrapped, non-/-prefixed) pass through unchanged. The backtick-
    bracket form is what validate.py's LINK_PATTERN, associate.py's
    scanner, and review-coverage's stub-linking check all look for;
    emitting raw paths silently breaks all three pipelines."""
    if not path:
        return ""
    s = str(path).strip()
    if not s:
        return ""
    if s.startswith("[`") and s.endswith("`]"):
        return s
    if s.startswith("/"):
        return f"[`{s}`]"
    return s


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
    lines = ["## Identity", "", "| Field | Value | Source |", "|---|---|---|"]
    for k, v in rows:
        lines.append(f"| {k} | {v} |  |")
    return "\n".join(lines) + "\n"


def render_background(artifact):
    body = (artifact.get("background") or "").strip()
    if not body:
        body = "<!-- TODO: populate `background` in the research artifact -->"
    return f"## Background\n\n{body}\n"


def render_uap_relevance(artifact):
    body = (artifact.get("uap_relevance") or "").strip()
    if not body:
        body = "<!-- TODO: populate `uap_relevance` in the research artifact -->"
    return f"## UAP Relevance\n\n{body}\n"


def _format_period(entry):
    start = entry.get("period_start") or ""
    end = entry.get("period_end") or ""
    if start and end:
        return f"{start} – {end}"
    return start or end or ""


def render_affiliations(artifact):
    """Affiliations table split into Confirmed / Flagged subsections.
    Sorted by period_start chronologically (check #15 enforces)."""
    items = artifact.get("affiliations") or []
    confirmed = sort_by_date([e for e in items if isinstance(e, dict) and not e.get("flagged")], "period_start")
    flagged   = sort_by_date([e for e in items if isinstance(e, dict) and e.get("flagged")],     "period_start")

    def render_row(e):
        org = _wrap_path(e.get("organization_path"))
        return (
            f"| {org} | "
            f"{e.get('role') or ''} | "
            f"{_format_period(e)} | "
            f"{(e.get('source') or {}).get('path') or ''} | "
            f"{org} |"
        )

    lines = ["## Affiliations", "", "### Confirmed", "",
             "| Organization | Role | Period | Source | Node Link |",
             "|---|---|---|---|---|"]
    if confirmed:
        for e in confirmed:
            lines.append(render_row(e))
    else:
        lines.append("|  |  |  |  |  |")
    if flagged:
        lines += ["", "### Flagged", "",
                  "| Organization | Role | Period | Source | Node Link |",
                  "|---|---|---|---|---|"]
        for e in flagged:
            lines.append(render_row(e))
    return "\n".join(lines) + "\n"


def _render_verification_block(quote, artifact):
    """Render the 3-field verification table for a person statement quote.
    Composes an Attributed-to line from quote.context (when set) + the
    quote's statement_date (when set)."""
    ctx = quote.get("context") or ""
    date = quote.get("statement_date") or ""
    attributed_to_parts = [p for p in [ctx, date] if p]
    attributed_to = ", ".join(attributed_to_parts) if attributed_to_parts else ""
    src = quote.get("source") or {}
    src_path = src.get("path") or ""
    src_link = f"[archived source](../sources/{src_path})" if src_path else ""
    loc = src.get("location") or ""

    rows = [
        "| Field | Value |",
        "|---|---|",
    ]
    if attributed_to:
        rows.append(f"| Attributed to | {attributed_to} |")
    if src_link:
        rows.append(f"| Source | {src_link} |")
    rows.append("| Verified | ✅ Confirmed — verified verbatim against archived source |")
    if loc:
        rows.append(f"| Location | {loc} |")
    return "\n".join(rows)


def _render_statement_block(quote, artifact):
    """Render a single block-quote + verification block pair."""
    text = (quote.get("text") or "").rstrip("\n")
    lines = []
    for qline in text.split("\n"):
        lines.append(f"> {qline}" if qline else ">")
    lines.append("")
    lines.append(_render_verification_block(quote, artifact))
    return "\n".join(lines)


def render_statements(artifact):
    """Statements section — split by observation_type into Direct
    Observations and Other Statements; sorted chronologically by
    statement_date within each subsection."""
    quotes = [q for q in (artifact.get("quotes") or []) if isinstance(q, dict)]
    direct = sort_by_date([q for q in quotes if q.get("observation_type") == "direct"], "statement_date")
    other  = sort_by_date([q for q in quotes if q.get("observation_type") != "direct"], "statement_date")

    lines = ["## Statements", "", "### Direct Observations"]
    if direct:
        lines.append("")
        for q in direct:
            lines.append(_render_statement_block(q, artifact))
            lines.append("")
    else:
        lines += ["", "<!-- No direct observations documented. -->"]

    lines += ["", "### Other Statements"]
    if other:
        lines.append("")
        for q in other:
            lines.append(_render_statement_block(q, artifact))
            lines.append("")
    else:
        lines += ["", "<!-- No other statements documented. -->"]

    return "\n".join(lines).rstrip() + "\n"


def render_timeline(artifact):
    """Timeline section — aggregated chronological dated facts with
    Category column. Sorted ascending by date."""
    items = sort_by_date(
        [e for e in (artifact.get("timeline") or []) if isinstance(e, dict)],
        "date",
    )
    lines = ["## Timeline", "", "| Date | Event | Category | Source | Node Link |",
             "|---|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |  |")
    for e in items:
        lines.append(
            f"| {e.get('date') or ''} | "
            f"{e.get('event') or ''} | "
            f"{e.get('category') or ''} | "
            f"{(e.get('source') or {}).get('path') or ''} | "
            f"{_wrap_path(e.get('node_link'))} |"
        )
    return "\n".join(lines) + "\n"


def render_relationships(artifact):
    items = artifact.get("relationships") or []
    confirmed = [e for e in items if isinstance(e, dict) and not e.get("flagged")]
    flagged   = [e for e in items if isinstance(e, dict) and e.get("flagged")]

    def row(e):
        person = _wrap_path(e.get("person_path"))
        return (
            f"| {person} | "
            f"{e.get('relationship') or ''} | "
            f"{person} |"
        )

    lines = ["## Relationships", "", "### Confirmed", "",
             "| Person | Relationship | Node Link |",
             "|---|---|---|"]
    if confirmed:
        for e in confirmed:
            lines.append(row(e))
    else:
        lines.append("|  |  |  |")
    if flagged:
        lines += ["", "### Flagged", "",
                  "| Person | Relationship | Node Link |",
                  "|---|---|---|"]
        for e in flagged:
            lines.append(row(e))
    return "\n".join(lines) + "\n"


def render_corroboration(artifact):
    """Corroboration section — renders on eyewitness person artifacts AND
    encounter event artifacts (same entry shape, same renderer). Column
    layout revised in F.2a: Observer first (what the investigator is
    looking for), Attested In last (the source documenting the
    corroboration); was Source | ... | Node Link which inverted the
    scan order.
    """
    items = artifact.get("corroboration_items") or []
    lines = ["## Corroboration", "",
             "| Observer | Type | What It Confirms | Attested In |",
             "|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |")
    for e in items:
        if not isinstance(e, dict):
            continue
        lines.append(
            f"| {_wrap_path(e.get('observer_path'))} | "
            f"{e.get('observation_type') or ''} | "
            f"{e.get('note') or ''} | "
            f"{(e.get('source') or {}).get('path') or ''} |"
        )
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
             "| Claim | Document | Status | Node Link |",
             "|---|---|---|---|"]
    if not quotes:
        lines.append("|  |  |  |  |")
    for q in quotes:
        text = (q.get("text") or "").strip().replace("\n", " ")
        # Truncate long claim text for readability in table
        if len(text) > 120:
            text = text[:117] + "…"
        src_path = (q.get("source") or {}).get("path") or ""
        node_link = _wrap_path(q.get("node_link"))
        lines.append(f"| {text} | {src_path} | ✅ Sworn / documented | {node_link} |")
    return "\n".join(lines) + "\n"


def render_program_involvement(artifact):
    items = artifact.get("program_involvement") or []
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
        # Program may be either a free-text program name (AAWSAP, AATIP)
        # or a `/organizations/...` path; wrap when it's a path.
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
             "| Name | Credentials | Statement | Source | Node Link |",
             "|---|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |  |")
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
            f"{(e.get('source') or {}).get('path') or ''} | "
            f"{voucher} |"
        )
    return "\n".join(lines) + "\n"


def render_credibility_notes(artifact, archetype):
    body = (artifact.get("credibility_notes") or "").strip()
    if not body:
        body = "<!-- TODO: populate `credibility_notes` in the research artifact -->"
    out = f"## Credibility Notes\n\n{body}\n"
    # Whistleblower archetype: Vouching Chain renders as a separate H2
    # after Credibility Notes (per the schema's required_sections
    # ordering). Keep it as a standalone section to preserve the
    # document structure.
    return out


# =============================================================================
# Event-type section renderers (F.2b)
# =============================================================================

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
    differ by kind; renderer emits whichever keys are present.
    """
    ei = artifact.get("event_intrinsic") or {}
    lines = ["## Event Summary", "", "| Field | Value |", "|---|---|"]

    def row(label, value):
        if value in (None, "", [], {}):
            return
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value)
        lines.append(f"| {label} | {value} |")

    if kind == "hearing":
        row("Full Title",     ei.get("hearing_title"))
        row("Convening Body", ei.get("committee"))
        row("Session",        ei.get("session"))
        row("Congress",       ei.get("congress_number"))
        row("Date",           ei.get("date"))
        row("Location",       ei.get("location"))
        row("Chair",          ei.get("chair"))
    else:  # encounter
        row("Date",            ei.get("date"))
        row("Location",        _wrap_path(ei.get("location_path")) or ei.get("location"))
        row("Duration",        ei.get("duration"))
        row("Weather",         ei.get("weather"))
        row("Instruments Involved", ei.get("instruments_involved"))

    # Placeholder row if no content
    if len(lines) == 4:
        lines.append("|  |  |")
    return "\n".join(lines) + "\n"


def render_event_description(artifact):
    body = (artifact.get("description") or "").strip()
    if not body:
        body = "<!-- TODO: populate `description` in the research artifact -->"
    return f"## Description\n\n{body}\n"


def _participant_row(e):
    """Render one participant row. Cells: participant (wrap_path), role,
    source.path, node-link (wrap_path)."""
    p = _wrap_path(e.get("participant_path"))
    return (
        f"| {p} | "
        f"{e.get('role') or ''} | "
        f"{(e.get('source') or {}).get('path') or ''} | "
        f"{p} |"
    )


def render_participants_encounter(artifact):
    """Flat Confirmed/Flagged split for encounter events."""
    items = artifact.get("participants") or []
    confirmed = [e for e in items if isinstance(e, dict) and not e.get("flagged")]
    flagged   = [e for e in items if isinstance(e, dict) and e.get("flagged")]

    lines = ["## Participants", "", "### Confirmed", "",
             "| Participant | Role | Source | Node Link |",
             "|---|---|---|---|"]
    if confirmed:
        for e in confirmed:
            lines.append(_participant_row(e))
    else:
        lines.append("|  |  |  |  |")
    if flagged:
        lines += ["", "### Flagged", "",
                  "| Participant | Role | Source | Node Link |",
                  "|---|---|---|---|"]
        for e in flagged:
            lines.append(_participant_row(e))
    return "\n".join(lines) + "\n"


def render_participants_hearing(artifact):
    """Hearing Participants — sub-sections by capacity. Flagged entries
    (any capacity) roll up into a single `### Flagged` subsection at the
    end, same as the Confirmed/Flagged pattern elsewhere."""
    items = [e for e in (artifact.get("participants") or []) if isinstance(e, dict)]
    confirmed = [e for e in items if not e.get("flagged")]
    flagged   = [e for e in items if e.get("flagged")]

    lines = ["## Participants", "", "### Confirmed"]
    for capacity in _HEARING_CAPACITY_ORDER:
        subsection_entries = [e for e in confirmed if e.get("capacity") == capacity]
        subheader = _HEARING_CAPACITY_SUBSECTION[capacity]
        lines.append("")
        lines.append(f"#### {subheader}")
        lines.append("")
        lines.append("| Participant | Role | Source | Node Link |")
        lines.append("|---|---|---|---|")
        if subsection_entries:
            for e in subsection_entries:
                lines.append(_participant_row(e))
        else:
            lines.append("|  |  |  |  |")

    # Catch entries with unknown capacity — they still need to render
    known = set(_HEARING_CAPACITY_ORDER)
    other_confirmed = [e for e in confirmed if e.get("capacity") not in known]
    if other_confirmed:
        lines += ["", "#### Other", "",
                  "| Participant | Role | Source | Node Link |",
                  "|---|---|---|---|"]
        for e in other_confirmed:
            lines.append(_participant_row(e))

    if flagged:
        lines += ["", "### Flagged", "",
                  "| Participant | Role | Source | Node Link |",
                  "|---|---|---|---|"]
        for e in flagged:
            lines.append(_participant_row(e))
    return "\n".join(lines) + "\n"


def render_key_testimony(artifact):
    """Key Testimony (hearing only) — verbatim quote blocks with
    verification tables. Reuses the person-node statement block shape:
    > quote + | Field | Value | table with Attributed to / Source /
    Verified rows. Sorted by statement_date when set. Empty-state
    emits an instructive stub pointing at the artifact's `quotes`
    list."""
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
    Replaces the prior `What The Hearing Established` synthesis section
    per the F.2a collapse. One row per witness pointing at transcript
    and written-testimony nodes."""
    items = [e for e in (artifact.get("witnesses_testimony") or []) if isinstance(e, dict)]
    lines = ["## Witnesses & Testimony", "",
             "| Witness | Oath Status | Transcript | Written Testimony |",
             "|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |")
    for e in items:
        lines.append(
            f"| {_wrap_path(e.get('witness_path'))} | "
            f"{e.get('oath_status') or ''} | "
            f"{_wrap_path(e.get('transcript_node'))} | "
            f"{_wrap_path(e.get('written_testimony_node'))} |"
        )
    return "\n".join(lines) + "\n"


# =============================================================================
# Transcript-type section renderers (F.3b)
# =============================================================================

def _escape_table_cell(value):
    """Escape a value for safe inclusion in a markdown table cell.
    Collapses newlines to spaces and backslash-escapes pipe characters
    (which would otherwise break column alignment). `None` → empty
    string."""
    if value is None:
        return ""
    s = str(value).replace("\n", " ")
    s = s.replace("|", "\\|")
    return s


def _excerpt_for_table(text, max_chars=150):
    """Produce a short excerpt of a quote suitable for a Material
    Differences table cell. Prefers the first sentence; caps at
    max_chars with ellipsis on a word boundary. Wraps the excerpt in
    double quotes to signal verbatim-source content. Empty/missing
    text returns empty string.

    Per F.3 design (Q3-A): first-sentence-preferred, ~150 char cap,
    never truncates mid-word. The excerpt IS the fine-grained locator
    — investigators can Ctrl+F for it within the linked Key Passages
    section without needing anchor-level precision.
    """
    if not text:
        return ""
    s = re.sub(r"\s+", " ", str(text)).strip()
    if not s:
        return ""
    # Try first sentence — stop at ., !, ? (followed by space, end, or
    # closing quote). Must be ≤ max_chars to use.
    m = re.search(r'^[^.!?]+[.!?]', s)
    if m and len(m.group(0).strip()) <= max_chars:
        return f'"{m.group(0).strip()}"'
    # Fall back: cap at max_chars on a word boundary, add ellipsis
    if len(s) <= max_chars:
        return f'"{s}"'
    trunc = s[:max_chars]
    last_space = trunc.rfind(" ")
    if last_space > max_chars // 2:
        trunc = trunc[:last_space]
    return f'"{trunc}…"'


def _resolve_cross_artifact_quote(ref):
    """Resolve a {artifact: <type>/<slug>, quote_id: qN} reference to
    the actual quote entry in the referenced research artifact.
    Returns (quote_dict, artifact_ref_string) on success, (None, None)
    on any failure (malformed ref, missing file, missing quote id).
    Resolver errors are separately surfaced by validate-research.py's
    check_material_differences; this function stays silent and just
    returns None so the renderer can emit a placeholder cell.
    """
    if not isinstance(ref, dict):
        return None, None
    artifact_ref = ref.get("artifact")
    quote_id = ref.get("quote_id")
    if not artifact_ref or not quote_id or "/" not in str(artifact_ref):
        return None, None
    _, slug = str(artifact_ref).split("/", 1)
    ref_path = REPO_ROOT / "research" / f"{slug}.yaml"
    if not ref_path.exists():
        return None, None
    try:
        with open(ref_path) as f:
            ref_data = yaml.safe_load(f)
    except yaml.YAMLError:
        return None, None
    if not isinstance(ref_data, dict):
        return None, None
    for q in ref_data.get("quotes", []) or []:
        if isinstance(q, dict) and q.get("id") == quote_id:
            return q, artifact_ref
    return None, None


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
    (`source_medium` / `derived_from`) per F.3 Decision 1 — keeps
    frontmatter as the single source of truth for those fields rather
    than duplicating into the artifact."""
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
        # derived_from on a hearing transcript typically points at a
        # /documents/... node (the companion written testimony). Emit
        # as "Companion Written Testimony" row in that case.
        if derived_from and str(derived_from).startswith("/documents/"):
            row("Companion Written Testimony", _wrap_path(derived_from))
        else:
            row("Companion Written Testimony", _wrap_path(ctx.get("companion_written_testimony")))
    else:  # other
        row("Outlet / Platform",  ctx.get("outlet") or ctx.get("platform"))
        row("Program / Show / Venue", ctx.get("program") or ctx.get("venue"))
        row("Date",               ctx.get("air_date") or ctx.get("date"))
        row("Host(s) / Interviewer(s)", ctx.get("hosts") or ctx.get("interviewers"))
        row("Primary Speaker(s)", ctx.get("primary_speakers"))
        row("Format",             ctx.get("format"))
        row("Source Medium",      source_medium)
        # derived_from on an `other` transcript typically points at a
        # /media/... node (the underlying media the transcript renders).
        if derived_from and str(derived_from).startswith("/media/"):
            row("Underlying Media Node", _wrap_path(derived_from))
        elif derived_from and str(derived_from).startswith("/documents/"):
            row("Underlying Document", _wrap_path(derived_from))
        row("Source URL",         ctx.get("primary_source_url"))
        row("Transcript Verified", ctx.get("transcript_verified"))
        row("Citation Style",     ctx.get("citation_style"))

    # Placeholder row when no fields are populated
    if len(lines) == 4:
        lines.append("|  |  |")
    return "\n".join(lines) + "\n"


def render_transcript_summary(artifact):
    """Summary section — renders `artifact.description` as `## Summary`
    per F.3 Decision 1 (Q1-A). Transcripts semantically summarize speech
    content; the render-time field→section rename keeps
    `description` as the universal top-level required field while the
    rendered section name fits transcript semantics."""
    desc = (artifact.get("description") or "").strip()
    body = desc if desc else "<!-- TODO: populate `description` in the research artifact -->"
    return f"## Summary\n\n{body}\n"


def render_transcript_speakers(artifact):
    """Speakers section — cross-reference table for who spoke in this
    transcript. Rendered from the `speakers` artifact field (Q2-A
    decision). NOT a statement surface — actual statements live in
    `quotes` and render as `## Key Passages`."""
    items = sort_by_id([s for s in (artifact.get("speakers") or []) if isinstance(s, dict)])
    lines = ["## Speakers", "",
             "| Name | Role | Node Link |",
             "|---|---|---|"]
    if not items:
        lines.append("|  |  |  |")
        return "\n".join(lines) + "\n"
    for s in items:
        lines.append(
            f"| {_escape_table_cell(s.get('name'))} | "
            f"{_escape_table_cell(s.get('role'))} | "
            f"{_wrap_path(s.get('node_link'))} |"
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
        lines.append(_render_verification_block(q, artifact))
        blocks.append("\n".join(lines))
    return head + "\n" + "\n\n---\n\n".join(blocks) + "\n"


def render_transcript_material_differences(artifact):
    """Material Differences section (hearing only) — per-divergence table
    with excerpted cross-references to the written and oral quote
    sources. Written Quote cell: excerpt + link to the companion
    document's `## Key Passages` anchor. Oral Quote cell: excerpt + link
    to THIS transcript's `## Key Passages` anchor. Per F.3 Q3-A, cells
    use first-sentence-preferred ~150-char excerpts; investigators Ctrl+F
    the excerpt text within the linked Key Passages section to find the
    full verbatim passage.

    Unresolvable refs (artifact missing, quote_id absent) produce a
    placeholder comment cell rather than silent rendering — the
    validator-side resolver (check_material_differences) already fires
    an error; this renderer should make the same failure visible in the
    rendered body for contributor inspection.
    """
    items = sort_by_id([e for e in (artifact.get("material_differences") or []) if isinstance(e, dict)])
    lines = ["## Material Differences", "",
             "<!-- Analytically significant divergences between the prepared "
             "written statement and the live oral testimony. Excerpts "
             "per F.3 design; full verbatim text lives in each artifact's "
             "## Key Passages section. -->",
             "",
             "| Topic | Class | Written Quote | Oral Quote | Note |",
             "|---|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |  |")
        return "\n".join(lines) + "\n"

    # Intra-artifact quote index for oral_ref resolution
    own_quotes = {q.get("id"): q for q in (artifact.get("quotes") or []) if isinstance(q, dict)}

    for e in items:
        topic = _escape_table_cell(e.get("topic"))
        dclass = _escape_table_cell(e.get("divergence_class"))

        # Written cell — cross-artifact resolution
        wref = e.get("written_ref")
        w_quote, w_artifact_ref = _resolve_cross_artifact_quote(wref)
        if w_quote and w_artifact_ref:
            w_excerpt = _excerpt_for_table(w_quote.get("text"))
            w_link = f"../{w_artifact_ref}.md#key-passages"
            w_cell = _escape_table_cell(f"{w_excerpt} [→ Key Passages]({w_link})")
        else:
            w_cell = "<!-- unresolvable written_ref -->"

        # Oral cell — intra-artifact resolution
        oref = e.get("oral_ref")
        o_quote = own_quotes.get(oref) if isinstance(oref, str) else None
        if o_quote:
            o_excerpt = _excerpt_for_table(o_quote.get("text"))
            o_cell = _escape_table_cell(f"{o_excerpt} [→ Key Passages](#key-passages)")
        else:
            o_cell = "<!-- unresolvable oral_ref -->"

        note = _escape_table_cell(e.get("note"))

        lines.append(f"| {topic} | {dclass} | {w_cell} | {o_cell} | {note} |")

    return "\n".join(lines) + "\n"


# =============================================================================
# Composition
# =============================================================================

def render_body_document(artifact, node_kind):
    # H1 title stands alone — no `---` separator between H1 and first H2.
    # Document nodes have no What This Establishes / claims section: the
    # document IS the fact record, and Key Passages carries the verbatim
    # evidentiary content. See schema.yaml document.kinds commentary.
    title = render_title(artifact).rstrip("\n") + "\n"
    sections = [
        render_document_summary(artifact),
        render_description(artifact),
    ]
    if node_kind == "gov-doc":
        sections.append(render_provenance(artifact))
    sections.extend([
        render_key_passages(artifact),
        render_associated_nodes(),
        render_open_questions(artifact),
    ])
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined


def render_body_person(artifact, archetype):
    """Person-type body composition. Section order matches the schema's
    required_sections for the given archetype. Whistleblower adds a
    Vouching Chain section between Credibility Notes and Associated
    Nodes; all other archetypes skip it."""
    title = render_title_person(artifact).rstrip("\n") + "\n"
    sections = [
        render_identity(artifact),
        render_background(artifact),
        render_uap_relevance(artifact),
        render_affiliations(artifact),
        render_statements(artifact),
        render_timeline(artifact),
        render_relationships(artifact),
        render_archetype_section(artifact, archetype),
        render_credibility_notes(artifact, archetype),
    ]
    if archetype == "whistleblower":
        sections.append(render_vouching_chain(artifact))
    sections.extend([
        render_associated_nodes(),
        render_open_questions(artifact),
    ])
    # Drop empty section strings (archetype dispatcher returns "" on unknown)
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined


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
        render_event_description(artifact),
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
        render_associated_nodes(),
        render_open_questions(artifact),
    ])
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined


def render_body_transcript(artifact, kind, fm):
    """Transcript-type body composition. Section order matches the
    schema's required_sections for the given kind. Universal sections
    (Publication Record, Summary, Speakers, Key Passages) emit for
    both kinds; Material Differences is hearing-only. The renderer
    threads `fm` through to Publication Record so it can read
    `derived_from` + `source_medium` from the transcript node's
    frontmatter per F.3 Decision 1.
    """
    title = render_title_transcript(artifact).rstrip("\n") + "\n"
    sections = [
        render_transcript_publication_record(artifact, kind, fm),
        render_transcript_summary(artifact),
        render_transcript_speakers(artifact),
        render_transcript_key_passages(artifact),
    ]
    if kind == "hearing":
        sections.append(render_transcript_material_differences(artifact))
    elif kind != "other":
        sys.exit(f"ERROR: render_body_transcript: unknown transcript kind {kind!r}")
    sections.extend([
        render_associated_nodes(),
        render_open_questions(artifact),
    ])
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined


def render_body(artifact, node_type, fm):
    """Dispatch by node_type. `fm` is the existing node frontmatter
    (needed for kind / archetype context the renderer can't derive from
    the artifact alone)."""
    if node_type == "document":
        return render_body_document(artifact, fm.get("kind"))
    if node_type == "person":
        return render_body_person(artifact, fm.get("archetype"))
    if node_type == "event":
        return render_body_event(artifact, fm.get("kind"))
    if node_type == "transcript":
        return render_body_transcript(artifact, fm.get("kind"), fm)
    sys.exit(f"ERROR: build-from-research.py does not yet support node_type {node_type!r}")


def compose_node(raw_frontmatter, body):
    return raw_frontmatter.rstrip() + "\n\n" + body.lstrip()


# =============================================================================
# Pre-flight / post-build validators
# =============================================================================

def preflight_validate_artifact(artifact_path):
    proc = subprocess.run(
        ["python3", str(VALIDATE_RESEARCH), str(artifact_path), "--quiet"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        sys.exit("ERROR: research artifact failed validation — aborting build.")


def post_build_validate(node_path):
    proc = subprocess.run(
        ["python3", str(VALIDATE_NODE), str(node_path), "--quiet"],
        capture_output=True, text=True,
    )
    sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode == 0


def run_associate(node_path):
    subprocess.run(
        ["python3", str(ASSOCIATE), str(node_path)],
        check=False,
    )


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("artifact", help="Path to research artifact (research/{slug}.yaml)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Render to stdout, do not write node or invoke associate/validate")
    parser.add_argument("--no-validate", action="store_true",
                        help="Skip pre-flight research-validation and post-build node-validation")
    args = parser.parse_args()

    artifact_path = Path(args.artifact).resolve()
    if not artifact_path.exists():
        sys.exit(f"ERROR: artifact not found: {artifact_path}")

    if not args.no_validate:
        preflight_validate_artifact(artifact_path)

    artifact = load_artifact(artifact_path)

    target_node = artifact.get("target_node") or ""
    if "/" not in target_node:
        sys.exit(f"ERROR: artifact target_node {target_node!r} is malformed")
    dir_name, slug = target_node.split("/", 1)
    reverse = {v: k for k, v in TYPE_DIRS.items()}
    node_type = reverse.get(dir_name)
    if node_type is None:
        sys.exit(f"ERROR: unknown content-dir {dir_name!r} in target_node")
    if node_type not in SUPPORTED_TYPES:
        sys.exit(f"ERROR: build-from-research.py currently supports "
                 f"{sorted(SUPPORTED_TYPES)} only (got {node_type!r}). "
                 f"Extension to other node types is tracked in BACKLOG.md.")

    node_path = REPO_ROOT / dir_name / f"{slug}.md"
    if not node_path.exists():
        sys.exit(f"ERROR: target node does not exist: {node_path.relative_to(REPO_ROOT)}\n"
                 f"  Run scripts/new.py to scaffold the node first.")

    fm, raw_fm = load_frontmatter(node_path)
    if fm is None or raw_fm is None:
        sys.exit(f"ERROR: cannot parse frontmatter of {node_path.relative_to(REPO_ROOT)}")

    body = render_body(artifact, node_type, fm)
    new_text = compose_node(raw_fm, body)

    if args.dry_run:
        sys.stdout.write(new_text)
        return

    node_path.write_text(new_text)
    print(f"✓ Regenerated {node_path.relative_to(REPO_ROOT)} "
          f"from {artifact_path.relative_to(REPO_ROOT)}")

    run_associate(node_path)

    if not args.no_validate:
        ok = post_build_validate(node_path)
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    main()
