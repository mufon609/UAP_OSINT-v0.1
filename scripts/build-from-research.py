#!/usr/bin/env python3
"""
Regenerate a node body from its research artifact (Phase II of layered build).

Reads /meta/research/{slug}.yaml and rewrites /{type}/{slug}.md. Frontmatter is
preserved from the existing node; body sections (H1 title onward) are
replaced entirely by content derived from the artifact.

SCOPE: document, person, event, transcript, media, organization,
location. Finding is the last remaining type; F.7 design pass is open
(see meta/roadmap.md).

Person renderer:
  - Universal sections: Identity, Background, {Topic} Relevance,
    Affiliations, Statements, Timeline, Relationships, Credibility
    Notes, Associated Nodes
    ({Topic} = display_name from meta/topic/overview.md frontmatter;
    "UAP" on this fork)
  - Statements split by `observation_type` into Direct Observations /
    Other Statements; sorted ascending by `statement_date` within each
  - Timeline sorted ascending by `date`
  - Archetype-specific section dispatched by frontmatter archetype:
      eyewitness          → Corroboration       (from corroboration_items)
      whistleblower       → Claim Inventory     (from quotes w/ category: filed-claim)
      institutional-actor → Program Involvement (from program_involvement)
      reporter            → Publication Record  (from publication_record, sorted)
  - Whistleblower-only: Vouching Chain section (from vouching_chain)

Event renderer:
  - Universal sections: Event Summary (from event_intrinsic),
    Description, Participants, Timeline, Associated Nodes
  - Hearing kind additionally: Key Testimony (verbatim quotes),
    Witnesses & Testimony (cross-reference table — replaces the prior
    What The Hearing Established synthesis section)
  - Encounter kind additionally: Corroboration (shares the
    corroboration_items entry shape + renderer with eyewitness
    person nodes; column layout: Observer | Type | What It Confirms |
    Attested In)
  - Hearing Participants sub-structured by participant capacity
    (witness-eyewitness / whistleblower / institutional / committee-
    member); encounter Participants uses flat Confirmed/Flagged.

Transcript renderer:
  - Universal sections: Publication Record, Summary, Speakers,
    Key Passages, Associated Nodes
  - `## Summary` is rendered from `artifact.description` (render-time
    field→section rename; keeps `description` as the universal
    top-level field while the rendered section name fits transcript
    semantics).
  - Publication Record auto-populates `Source Medium` and `Underlying
    X Node` rows from frontmatter (`source_medium` / `derived_from`)
    — frontmatter stays the single source of truth for those fields;
    no artifact-side duplication.
  - Key Passages uses H3 per quote (significance field) like document
    Key Passages, providing navigability for transcripts that may
    carry many quotes.

Media renderer:
  - Universal sections across all kinds (photo / video / audio /
    imagery-other): Media Summary, Description, Provenance, Key
    Passages, Associated Nodes
  - Conditional Media Versioning section — rendered only when the
    artifact's `media_versioning` list has entries. Omitted entirely
    for canonical / original media. Columns: Aspect / Parent / This /
    Source / Note.
  - Media Summary emits rows from the union of `document_intrinsic`
    + `context_extrinsic` + manifest sha256 lookup. Rows with empty
    values skip (matches transcript Publication Record pattern) —
    Summary adapts to what the source + contributor populated.
  - Key Passages use the shared `_render_attribution_block` helper;
    `source.location` flows through flexibly (timestamp /
    timestamp+coordinate / spatial-only).
  - May be empty when the source has no extractable speech or
    visible text (heavy speech content spins up a separate transcript
    node pointing to the media via `derived_from`).

DETERMINISM: given the same artifact + node frontmatter, output is
byte-for-byte identical across runs. Entries are rendered in id-sorted
order (q1, q2, …); no date-of-build or wall-clock state is embedded.

USAGE:
  build-from-research.py meta/research/{slug}.yaml
  build-from-research.py meta/research/{slug}.yaml --dry-run
  build-from-research.py meta/research/{slug}.yaml --no-validate

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


# Make scripts/lib/ importable so the renderer can read topic config
# via the shared load_topic() helper.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib._common import load_topic  # noqa: E402


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

# Types this script can regenerate (document, person, event,
# transcript, media, organization, location). Finding pending F.7.
SUPPORTED_TYPES = {"document", "person", "event", "transcript", "media", "organization", "location"}

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


def _id_natural_key(eid):
    """Return a natural-sort key for an id string like 'q1', 'q10', 'md3',
    'tl15b'. Splits alpha prefix + numeric core + optional alpha suffix so
    q10 sorts AFTER q2 (not before), and tl15b sorts AFTER tl15 but BEFORE
    tl16. Non-conforming ids fall to a 'zzz' bucket to sort last, preserving
    sort stability for malformed entries.

    The trailing-alpha suffix supports the established repo convention where
    `tl15b`, `t3b`, `kp4a` etc. denote sub-step entries derived from a
    parent numeric ID. Without it, those IDs fall to the 'zzz' bucket and
    render last among same-date siblings — masked today by accident when
    dates happen to be unique, fragile when same-date siblings appear.
    """
    if not eid:
        return ("zzz", 0, "")
    m = re.match(r"^([a-zA-Z]+)(\d+)([a-zA-Z]*)$", str(eid))
    if m:
        return (m.group(1), int(m.group(2)), m.group(3))
    return ("zzz", 0, str(eid))


def sort_by_id(entries):
    """Natural-sort entries by id (q1, q2, …, q10) so output order is
    stable and human-expected (q10 doesn't land between q1 and q2)."""
    def key(e):
        if not isinstance(e, dict):
            return ("zzz", 0, "")
        return _id_natural_key(e.get("id") or "")
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
    unparseable entries land at the end (via the 9999 sentinel). Tie-break
    by natural-sort on id — prevents lex-sort from placing q10 between
    q1 and q2 when all entries share the same date (common on transcripts
    where every quote carries the hearing date)."""
    def key(e):
        if not isinstance(e, dict):
            return ((9999, 0, 0), ("zzz", 0, ""))
        return (parse_date_tuple(e.get(date_key)), _id_natural_key(e.get("id") or ""))
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


def render_primary_source_contradictions(artifact):
    """Emit a `## Primary-Source Contradictions` section listing rumors
    whose status is `primary-source-disputed` — widely-circulated
    secondary-source claims that primary-source evidence refutes.

    Returns empty string when no disputed rumors exist. Disputed
    rumors are analytical findings worth surfacing to readers; the
    `not-primary-source-established` status stays artifact-only
    (pure fabrication-prevention, never renders).

    Applies to the four target types whose schema rules require
    `rumors` (person / organization / event / location per
    schema.yaml::conditional_keys). Document / transcript / media
    artifacts don't carry rumors and never emit this section.
    """
    rumors = artifact.get("rumors") or []
    disputed = [
        r for r in rumors
        if isinstance(r, dict) and r.get("status") == "primary-source-disputed"
    ]
    if not disputed:
        return ""

    parts = [
        "## Primary-Source Contradictions",
        "",
        "Widely-circulated secondary-source claims contradicted by primary-source evidence.",
        "",
    ]
    for r in disputed:
        claim = (r.get("claim") or "").strip()
        if not claim:
            continue
        parts.append(f'### "{claim}"')
        parts.append("")
        obs = r.get("observed_sources")
        if obs:
            if isinstance(obs, list):
                obs_str = "; ".join(str(o) for o in obs)
            else:
                obs_str = str(obs)
            parts.append(f"**Circulates in:** {obs_str}")
            parts.append("")
        note = (r.get("note") or "").strip()
        if note:
            parts.append(f"**Primary-source refutation:** {note}")
            parts.append("")
    return "\n".join(parts).rstrip() + "\n"


# =============================================================================
# Person-type section renderers
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


def render_top_relevance(artifact):
    body = (artifact.get("top_relevance") or "").strip()
    if not body:
        body = "<!-- TODO: populate `top_relevance` in the research artifact -->"
    display_name = load_topic()["display_name"]
    return f"## {display_name} Relevance\n\n{body}\n"


def _format_period(entry):
    start = entry.get("period_start") or ""
    end = entry.get("period_end") or ""
    if start and end:
        return f"{start} – {end}"
    if end and not start:
        # End-only: convention is "– {end}" to signal bracketed end with
        # unknown start (primary source gives an upper bound via past-tense
        # language like "former X" without a specific departure date).
        return f"– {end}"
    return start or ""


def render_affiliations(artifact):
    """Affiliations table split into Confirmed / Flagged subsections.
    Sorted by period_start chronologically (the chronological-ordering check enforces)."""
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


def _render_attribution_block(quote, artifact):
    """Render the attribution table for a quote — Attributed-to / Source /
    Location. Composes an Attributed-to line from quote.context (when set)
    and quote.statement_date (when set); skips the date append if it
    already appears in the context string. The block carries no
    verification marker — confirmation against the underlying source is
    a precondition for inclusion (enforced by validate.py's verbatim-quote
    check), not a rendered claim. See meta/conventions.md."""
    ctx = quote.get("context") or ""
    date = quote.get("statement_date") or ""
    if date and date in ctx:
        attributed_to = ctx
    else:
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
    lines.append(_render_attribution_block(quote, artifact))
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


def render_corroboration(artifact):
    """Corroboration section — renders on eyewitness person artifacts AND
    encounter event artifacts (same entry shape, same renderer). Column
    layout: Observer first (what the investigator is looking for),
    Attested In last (the source documenting the corroboration).
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
# Event-type section renderers
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

# Capacities whose empty case carries analytical meaning — always render
# the sub-subsection even with zero entries. committee-member: absence
# of committee members would be newsworthy (oversight failure), so the
# empty state is a finding worth surfacing. Witness capacities are
# suppressed when empty — different hearings naturally carry different
# witness compositions (an oversight hearing may have no institutional
# witnesses, a SASC hearing may have no whistleblowers), and empty
# witness tables read as "data missing" rather than "category N/A here".
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
    source.path."""
    p = _wrap_path(e.get("participant_path"))
    return (
        f"| {p} | "
        f"{e.get('role') or ''} | "
        f"{(e.get('source') or {}).get('path') or ''} |"
    )


def render_participants_encounter(artifact):
    """Flat Confirmed/Flagged split for encounter events."""
    items = artifact.get("participants") or []
    confirmed = [e for e in items if isinstance(e, dict) and not e.get("flagged")]
    flagged   = [e for e in items if isinstance(e, dict) and e.get("flagged")]

    lines = ["## Participants", "", "### Confirmed", "",
             "| Participant | Role | Source |",
             "|---|---|---|"]
    if confirmed:
        for e in confirmed:
            lines.append(_participant_row(e))
    else:
        lines.append("|  |  |  |")
    if flagged:
        lines += ["", "### Flagged", "",
                  "| Participant | Role | Source |",
                  "|---|---|---|"]
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
        # Suppress empty witness sub-subsections — their empty case is
        # per-hearing variance rather than an analytical finding. Committee
        # Members always render (see _HEARING_CAPACITY_RENDER_WHEN_EMPTY).
        if not subsection_entries and capacity not in _HEARING_CAPACITY_RENDER_WHEN_EMPTY:
            continue
        subheader = _HEARING_CAPACITY_SUBSECTION[capacity]
        lines.append("")
        lines.append(f"#### {subheader}")
        lines.append("")
        lines.append("| Participant | Role | Source |")
        lines.append("|---|---|---|")
        if subsection_entries:
            for e in subsection_entries:
                lines.append(_participant_row(e))
        else:
            lines.append("|  |  |  |")

    # Catch entries with unknown capacity — they still need to render
    known = set(_HEARING_CAPACITY_ORDER)
    other_confirmed = [e for e in confirmed if e.get("capacity") not in known]
    if other_confirmed:
        lines += ["", "#### Other", "",
                  "| Participant | Role | Source |",
                  "|---|---|---|"]
        for e in other_confirmed:
            lines.append(_participant_row(e))

    if flagged:
        lines += ["", "### Flagged", "",
                  "| Participant | Role | Source |",
                  "|---|---|---|"]
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
    Replaces the prior `What The Hearing Established` synthesis section.
    One row per witness pointing at transcript and written-testimony
    nodes."""
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
# Transcript-type section renderers
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
    source of truth for those fields rather than duplicating into the
    artifact."""
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
        # of the same event; neither derives from the other, so
        # derived_from's "this IS a rendering of that" semantic doesn't
        # fit.
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
        lines.append(_render_attribution_block(q, artifact))
        blocks.append("\n".join(lines))
    return head + "\n" + "\n\n---\n\n".join(blocks) + "\n"


# =============================================================================
# Composition
# =============================================================================

def render_body_document(artifact, node_kind):
    # H1 title stands alone — no `---` separator between H1 and first H2.
    # Document nodes have no What This Establishes synthesis section: the
    # document IS the fact record, and Key Passages carries the verbatim
    # evidentiary content. See meta/conventions.md "Statements as the
    # universal evidentiary primitive" for the repo-wide discipline.
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
        render_top_relevance(artifact),
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
        render_primary_source_contradictions(artifact),
        render_associated_nodes(),
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
        render_primary_source_contradictions(artifact),
        render_associated_nodes(),
    ])
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined


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
        render_associated_nodes(),
    ]
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined


_manifest_sha256_cache = None


def _manifest_sha256_for(path):
    """Look up the sha256 for a given source path from sources/manifest.yaml.
    Loaded once per build, cached. Returns empty string when the path is
    missing from the manifest or has no sha256 field (e.g., pending /
    blocked sources)."""
    global _manifest_sha256_cache
    if _manifest_sha256_cache is None:
        manifest_path = REPO_ROOT / "sources" / "manifest.yaml"
        if not manifest_path.exists():
            _manifest_sha256_cache = {}
        else:
            try:
                with open(manifest_path) as f:
                    entries = yaml.safe_load(f) or []
                _manifest_sha256_cache = {
                    e.get("path"): e.get("sha256")
                    for e in entries
                    if isinstance(e, dict) and e.get("path") and e.get("sha256")
                }
            except (yaml.YAMLError, OSError):
                _manifest_sha256_cache = {}
    return _manifest_sha256_cache.get(path, "") or ""


def render_title_media(artifact):
    """H1 title for media nodes. Prefers context_extrinsic.display_title,
    falls back to document_intrinsic.internal_title, then humanized slug."""
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    slug = artifact["target_node"].split("/", 1)[1] if "/" in artifact["target_node"] else ""
    title = (
        ctx.get("display_title")
        or dm.get("internal_title")
        or (slug and " ".join(w.capitalize() for w in slug.split("-")))
        or ""
    )
    return f"# {title}\n"


def render_media_summary(artifact, kind):
    """Media Summary table — kind-agnostic row emission from
    document_intrinsic + context_extrinsic + primary_sources + manifest
    sha256 lookup. Field conventions documented in schema.yaml's
    document_intrinsic comment for media. Rows with empty values are
    skipped — the Summary adapts to what the source and contributor
    populated rather than showing "N/A" placeholders. `kind` comes
    from the node frontmatter (photo / video / audio / imagery-other)
    and renders as the Kind row."""
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    path = _source_path(artifact)
    sources = artifact.get("primary_sources") or []
    fmt = None
    if sources and isinstance(sources[0], dict):
        fmt = sources[0].get("format")

    lines = ["## Media Summary", "", "| Field | Value |", "|---|---|"]

    def row(label, value):
        if value in (None, "", [], {}):
            return
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value)
        lines.append(f"| {label} | {_escape_table_cell(value)} |")

    row("Title", ctx.get("display_title") or dm.get("internal_title"))
    row("Kind", kind)
    row("Date Captured", dm.get("capture_date") or dm.get("original_creation_date"))
    row("Date Released", ctx.get("release_date"))
    # Duration + Dimensions: label adapts to what's populated. Video
    # typically has both → "Duration / Dimensions"; audio has only
    # duration → "Duration"; photo / imagery-other has only dimensions
    # → "Dimensions". Keeps the label honest about what the row covers
    # rather than presenting a "half-populated combined field" look.
    has_dur = bool(dm.get("duration"))
    has_dim = bool(dm.get("dimensions"))
    if has_dur and has_dim:
        row("Duration / Dimensions", f"{dm['duration']} / {dm['dimensions']}")
    elif has_dur:
        row("Duration", dm.get("duration"))
    elif has_dim:
        row("Dimensions", dm.get("dimensions"))
    # Format: document_intrinsic.file_format takes precedence (precise),
    # fall back to primary_sources[0].format (the manifest-registered
    # container type).
    row("Format", dm.get("file_format") or (fmt.upper() if fmt else None))
    row("Codec", dm.get("codec"))
    row("Color Mode", dm.get("color_mode"))
    row("File Size", dm.get("file_size"))
    row("Camera / Device", dm.get("camera_device"))
    row("EXIF / Container Metadata", dm.get("embedded_metadata"))
    if path:
        sha = _manifest_sha256_for(path)
        if sha:
            row("SHA256", sha)
    row("Primary Source URL", ctx.get("primary_source_url"))
    if path:
        row("Local Archive", f"[sources/{path}](../sources/{path})")

    # Placeholder row when nothing is populated (Title through Local
    # Archive all empty) — keeps the table well-formed for downstream
    # markdown consumers.
    if len(lines) == 4:
        lines.append("|  |  |")
    return "\n".join(lines) + "\n"


def render_media_versioning(artifact, fm):
    """Media Versioning table. Emission rules:
      - When the node frontmatter has `derivation_of` set, the section
        MUST emit (per schema.yaml media.conditionally_required) — even
        if `media_versioning` is empty, render a placeholder row so the
        node-body validator's required-section check passes. The
        validate-research.py "empty media_versioning + derivation_of"
        warn surfaces the missing content as a non-blocking signal.
      - When `derivation_of` is absent, the section is omitted entirely
        (empty string returned; caller drops it from the body) — canonical
        / original media nodes have no derivation to document.
    Columns: Aspect / Parent / This / Source / Note.
    """
    items = sort_by_id([
        e for e in (artifact.get("media_versioning") or []) if isinstance(e, dict)
    ])
    is_derivative = bool((fm or {}).get("derivation_of"))
    if not items and not is_derivative:
        return ""  # Canonical / original media — omit the section entirely

    lines = ["## Media Versioning", "",
             "<!-- Per-aspect differences between the parent (derivation_of) "
             "media node and this derivative. Aspect enum: duration / "
             "encoding / metadata / content / provenance / other. -->",
             "",
             "| Aspect | Parent | This | Source | Note |",
             "|---|---|---|---|---|"]
    if not items:
        # Placeholder row when derivation_of is set but the artifact's
        # media_versioning list is empty. Keeps the required-section
        # contract satisfied; validate-research.py's warn on the empty
        # list flags the missing content.
        lines.append("|  |  |  |  |  |")
        return "\n".join(lines) + "\n"
    for e in items:
        aspect = _escape_table_cell(e.get("aspect"))
        parent = _escape_table_cell(e.get("parent_form"))
        this_v = _escape_table_cell(e.get("this_form"))
        src = e.get("source") or {}
        src_path = src.get("path") if isinstance(src, dict) else ""
        src_loc = src.get("location") if isinstance(src, dict) else ""
        if src_path:
            src_cell = f"[archived source](../sources/{src_path})"
            if src_loc:
                src_cell = f"{src_cell} — {src_loc}"
        else:
            src_cell = ""
        src_cell = _escape_table_cell(src_cell)
        note = _escape_table_cell(e.get("note"))
        lines.append(f"| {aspect} | {parent} | {this_v} | {src_cell} | {note} |")
    return "\n".join(lines) + "\n"


def render_media_key_passages(artifact):
    """Key Passages on media — verbatim speech or visible text. Uses
    the shared `_render_attribution_block` so the flexible source.location
    (timestamp / timestamp+coordinate / spatial-only) flows through.
    H3 per quote using `significance`. May be empty when the source has
    no extractable speech or visible text."""
    quotes = sort_by_id([
        q for q in (artifact.get("quotes") or []) if isinstance(q, dict)
    ])
    head = "## Key Passages\n"
    if not quotes:
        return head + (
            "\n<!-- May be empty when the source has no extractable speech "
            "or visible text. Heavy speech content spins up a separate "
            "transcript node pointing to this media via `derived_from`. -->\n"
        )

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


def render_body_media(artifact, kind, fm):
    """Media-type body composition. All four kinds (photo / video /
    audio / imagery-other) share the same section structure; per-kind
    variation happens within Media Summary (field list adapts to what
    document_intrinsic contains). Media Versioning is conditional on
    the artifact having media_versioning entries — omitted entirely
    for canonical / original media.
    """
    title = render_title_media(artifact).rstrip("\n") + "\n"
    sections = [
        render_media_summary(artifact, kind),
        render_description(artifact),
        render_provenance(artifact),
    ]
    mv_section = render_media_versioning(artifact, fm)
    if mv_section:
        sections.append(mv_section)
    sections.extend([
        render_media_key_passages(artifact),
        render_associated_nodes(),
    ])
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined


# =============================================================================
# Organization renderer
# =============================================================================

# Row-label mapping for Overview fact-table rows. Keyed by
# document_intrinsic field name; value is the display label for the
# table row. Rows emit only for populated fields — empty keys skipped.
# Per-kind convention lives in schema.yaml document_intrinsic comment;
# this dict mirrors those keys.
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

# Per-kind row ordering. A kind's list enumerates which document_intrinsic
# keys render (in what order) on an Overview fact table. The gov list
# accommodates all three sub-shapes (agency/office + military-unit +
# military-service) — only populated keys emit rows, so empty shape-
# mismatched fields are silently skipped.
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
# sub-grouping. Entries with unset / unknown leadership_class fall
# through to the "other" bucket (rendered as "Other Named Personnel").
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
        # Opt-in; falls back to the generic label when unset.
        if key == "current_director_path" and dm.get("head_title"):
            label = dm["head_title"]
        else:
            label = _ORG_OVERVIEW_LABELS.get(key, key)
        if key.endswith("_path"):
            # Render path-valued fields as wrap links.
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
    + source.path (parallels the person affiliations row shape)."""
    person = _wrap_path(e.get("person_path"))
    return (
        f"| {person} | "
        f"{e.get('role') or ''} | "
        f"{_format_period(e)} | "
        f"{(e.get('source') or {}).get('path') or ''} |"
    )


def render_org_key_personnel(artifact):
    """Key Personnel section — sub-grouped by leadership_class within
    Confirmed / Flagged split. Empty sub-subsections are suppressed
    (addresses the empty-witnesses BACKLOG pattern for new code).
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
                "| Name | Role | Period | Source |",
                "|---|---|---|---|",
            ]
            for e in buckets[cls]:
                out.append(_org_key_personnel_row(e))
            out.append("")
        if not any_rendered:
            # Empty confirmed-side fallback — emit a one-line placeholder
            # rather than a malformed empty table row. Surfaced 2026-04-30
            # by Sancorp audit R1; the empty `|  |  |  |  |` row was
            # technically valid markdown but read as a placeholder bug.
            out += [
                "_No personnel attested in primary sources to date._",
                "",
            ]
        return out

    lines = ["## Key Personnel", "", "### Confirmed", ""]
    lines += render_subsections(bucket_by_class(confirmed))

    if flagged:
        # Each render_subsections block ends with a trailing blank line
        # so we don't prepend one here — avoids a double-blank before
        # ### Flagged.
        lines += ["### Flagged", ""]
        lines += render_subsections(bucket_by_class(flagged))

    return "\n".join(lines).rstrip() + "\n"


def render_org_key_passages(artifact):
    """Key Passages section — verbatim excerpts from primary sources
    ABOUT the organization. Each passage: H3 (significance) + block-
    quote + per-quote verification block. Uses the same shape as
    transcript Key Passages — per-quote source attribution so orgs
    can draw from multiple primary sources (establishment press
    releases, IG findings, statutory documents). Sorted by
    statement_date when set; falls through to id-order."""
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
    render as a bulleted sub-list beneath each row — accommodates
    AAWSAP-scale contracts with many document deliverables without
    bloating the main table."""
    items = [e for e in (artifact.get("contracts") or []) if isinstance(e, dict)]
    items = sort_by_date(items, "period_start")

    lines = ["## Primary Contracts", "",
             "| Contract | Contracting Agency | Period | Value | Counterparty | Subject | Source |",
             "|---|---|---|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |  |  |  |")
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
            f"{(e.get('source') or {}).get('path') or ''} |"
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
    Flagged split. Different renderer from render_relationships()
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
            f"{(e.get('source') or {}).get('path') or ''} |"
        )

    lines = ["## Relationships", "", "### Confirmed", "",
             "| Organization | Relationship | Source |",
             "|---|---|---|"]
    if confirmed:
        for e in confirmed:
            lines.append(row(e))
    else:
        lines.append("|  |  |  |")
    if flagged:
        lines += ["", "### Flagged", "",
                  "| Organization | Relationship | Source |",
                  "|---|---|---|"]
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
        render_associated_nodes(),
    ])
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined


# =============================================================================
# Location renderer
# =============================================================================

# Row-label mapping for Overview fact-table rows. Keyed by
# document_intrinsic field name; value is the display label. Locations
# have no kinds (unlike organizations), so a single key set drives the
# table. Rows emit only for populated fields — empty keys skipped.
# Per-location convention lives in schema.yaml document_intrinsic comment.
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
    Source. Sorted ascending by period_start; the chronological-ordering check enforces
    chronological order on the rendered table."""
    items = sort_by_date(
        [e for e in (artifact.get("ownership_timeline") or []) if isinstance(e, dict)],
        "period_start",
    )
    lines = ["## Ownership Timeline", "",
             "| Period | Owner | Use / Status | Source |",
             "|---|---|---|---|"]
    if not items:
        lines.append("|  |  |  |  |")
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
            f"{(e.get('source') or {}).get('path') or ''} |"
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
             "| Period | Activity | Source |",
             "|---|---|---|"]
    if not items:
        lines.append("|  |  |  |")
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
            f"{(e.get('source') or {}).get('path') or ''} |"
        )
    return "\n".join(lines) + "\n"


def render_location_key_passages(artifact):
    """Key Passages section — verbatim excerpts from primary sources
    ABOUT the location. Mirrors render_org_key_passages pattern. H3
    per quote using `significance` field; block-quote text + per-quote
    verification block. Sorted by `statement_date` with natural-sort
    tie-break on id. Supports evidentiary anchoring on location nodes
    parallel to organization nodes."""
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
    Flagged split. Heterogeneous entity_path targets (any node type).
    Distinct from person render_relationships (person-to-person) and
    render_org_relationships (org-to-org) by allowing entity_path of
    any type. Columns: Entity | Relationship. The entity_path wrap-link
    in the first column serves as the navigation target; no redundant
    Node Link column (wrap-path-as-first-column tables don't need a
    trailing Node Link — it would duplicate the first cell)."""
    items = [e for e in (artifact.get("location_relationships") or []) if isinstance(e, dict)]
    confirmed = [e for e in items if not e.get("flagged")]
    flagged   = [e for e in items if e.get("flagged")]

    def row(e):
        ep = _wrap_path(e.get("entity_path"))
        return (
            f"| {ep} | "
            f"{e.get('relationship') or ''} |"
        )

    lines = ["## Relationships", "", "### Confirmed", "",
             "| Entity | Relationship |",
             "|---|---|"]
    if confirmed:
        for e in confirmed:
            lines.append(row(e))
    else:
        lines.append("|  |  |")
    if flagged:
        lines += ["", "### Flagged", "",
                  "| Entity | Relationship |",
                  "|---|---|"]
        for e in flagged:
            lines.append(row(e))
    return "\n".join(lines) + "\n"


def render_body_location(artifact, fm):
    """Location-type body composition. Section order matches the
    schema's required_sections: Overview → Description → Ownership
    Timeline → {Topic}-Scope Activity → Key Passages → Relationships →
    Associated Nodes ({Topic} = display_name from
    meta/topic/overview.md). Location has no kinds, so no per-kind
    dispatch. Key Passages covers evidentiary quotes about the
    location; parallels organization's Key Passages pattern."""
    title = render_title_location(artifact).rstrip("\n") + "\n"
    sections = [
        render_location_overview(artifact, fm),
        render_description(artifact),
        render_ownership_timeline(artifact),
        render_top_scope_activity(artifact),
        render_location_key_passages(artifact),
        render_location_relationships(artifact),
        render_primary_source_contradictions(artifact),
        render_associated_nodes(),
    ]
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
    if node_type == "media":
        return render_body_media(artifact, fm.get("kind"), fm)
    if node_type == "organization":
        return render_body_organization(artifact, fm.get("kind"))
    if node_type == "location":
        return render_body_location(artifact, fm)
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
    parser.add_argument("artifact", help="Path to research artifact (meta/research/{slug}.yaml)")
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
                 f"Finding extension is tracked as F.7 in "
                 f"meta/roadmap.md.")

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
