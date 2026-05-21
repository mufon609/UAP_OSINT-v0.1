"""Shared renderer helpers — loaders, sort utilities, generic block renderers.

Imported by ``_universal`` and every per-type renderer module. Holds the
small cross-cutting helpers that have no per-type semantics: artifact /
frontmatter loaders, natural-sort + chronological-sort routines, path
wrapping, cell escaping, period formatting, source-path lookup, manifest
SHA-256 cache, and the three statement-block renderers shared by
person / event / transcript / media / organization / location / finding.

Per-type renderer modules under ``scripts/build/renderers/`` import from
this file. Everything that depends on a particular node type's shape
belongs in the per-type module, not here.
"""

import re
import sys

import yaml

from lib._common import REPO_ROOT, iter_artifacts, parse_date_tuple, strict_yaml_load


SECTION_SEP = "\n---\n\n"

# Sentinel used by ``sort_by_date`` to land undated entries last. Kept
# out of ``parse_date_tuple`` itself so the parser stays consumer-neutral.
_END_OF_TIME = (9999, 0, 0)

# Sub-threshold for ``_render_statement_block`` — quotes shorter than this
# many non-whitespace characters render in compact form (single blockquote
# line + italicized attribution continuation) rather than the standard
# blockquote + verification-table pair.
_COMPACT_STATEMENT_CHAR_THRESHOLD = 30


# ============================================================================
# Loaders
# ============================================================================

def load_artifact(path):
    with open(path) as f:
        data = strict_yaml_load(f)
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
        fm = strict_yaml_load(fm_yaml)
    except yaml.YAMLError:
        return None, None
    block_end = end + len("\n---")
    if block_end < len(text) and text[block_end] == "\n":
        block_end += 1
    return fm, text[:block_end]


# ============================================================================
# Sort utilities
# ============================================================================

def _id_natural_key(eid):
    """Return a natural-sort key for an id string like 'q1', 'q10', 'md3',
    'tl15b'. Splits alpha prefix + numeric core + optional alpha suffix so
    q10 sorts AFTER q2 (not before), and tl15b sorts AFTER tl15 but BEFORE
    tl16. Non-conforming ids fall to a 'zzz' bucket to sort last, preserving
    sort stability for malformed entries.

    The trailing-alpha suffix supports the established repo convention where
    `tl15b`, `t3b`, `kp4a` etc. denote sub-step entries derived from a
    parent numeric ID.
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


def sort_by_date(entries, date_key, fallback_key=None):
    """Stable-sort entries ascending by the date at `date_key`. When
    `fallback_key` is provided and an entry's primary key is missing /
    unparseable, the fallback key is consulted before the entry sinks
    to the end.

    Undated / unparseable entries land at the end (via the
    ``_END_OF_TIME`` sentinel applied here, NOT inside the parser).
    Tie-break by natural-sort on id."""
    def key(e):
        if not isinstance(e, dict):
            return (_END_OF_TIME, ("zzz", 0, ""))
        primary = parse_date_tuple(e.get(date_key))
        if primary is None and fallback_key is not None:
            primary = parse_date_tuple(e.get(fallback_key))
        return (
            primary or _END_OF_TIME,
            _id_natural_key(e.get("id") or ""),
        )
    return sorted(entries, key=key)


# ============================================================================
# Path / cell / period helpers
# ============================================================================

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


def _source_path(artifact):
    sources = artifact.get("primary_sources") or []
    if sources and isinstance(sources[0], dict):
        return sources[0].get("path")
    return None


# ============================================================================
# Statement block renderers (used by person / event / transcript /
# media / organization / location / finding)
# ============================================================================

def _compose_attributed_to(ctx, date):
    """Compose the Attributed-to value from a quote's context + statement_date.

    Appends the date as a trailing segment unless it already appears in the
    context (dedup). When the context ends in terminal punctuation, the date
    is separated by a space — the punctuation already closes the clause — so
    a credential or quoted phrase keeps its period intact
    (`…D.Eng. 2010-03-29`, `…Acting Director". 2022-05-27`). Otherwise the date
    joins as an appositive with a comma (`…in Tampa, 2024-05`)."""
    ctx = (ctx or "").rstrip()
    date = date or ""
    if not date or date in ctx:
        return ctx
    if not ctx:
        return date
    sep = " " if ctx.endswith((".", "?", "!")) else ", "
    return f"{ctx}{sep}{date}"


def _render_attribution_block(quote, artifact):
    """Render the attribution table for a quote — Speaker / Attributed-to /
    Source / Location. When ``quote.speaker_id`` is set (transcript
    artifacts), looks up the matching ``artifact.speakers[*].id`` entry
    and emits a Speaker row carrying the speaker's name + optional
    backtick-bracket node_link. Composes an Attributed-to line from
    quote.context (when set) and quote.statement_date (when set); skips
    the date append if it already appears in the context string. The
    block carries no verification marker — confirmation against the
    underlying source is a precondition for inclusion (enforced
    artifact-side by the verbatim-quote check), not a rendered claim.
    See meta/conventions.md."""
    attributed_to = _compose_attributed_to(
        quote.get("context"), quote.get("statement_date")
    )
    src = quote.get("source") or {}
    src_path = src.get("path") or ""
    src_link = f"[archived source](../sources/{src_path})" if src_path else ""
    loc = src.get("location") or ""

    speaker_cell = ""
    sid = quote.get("speaker_id")
    if sid:
        speakers = artifact.get("speakers") or []
        matched = next(
            (s for s in speakers if isinstance(s, dict) and s.get("id") == sid),
            None,
        )
        if matched:
            name = matched.get("name") or ""
            node_link = matched.get("node_link") or ""
            if name and node_link:
                speaker_cell = f"{name} ([`{node_link}`])"
            else:
                speaker_cell = name or node_link

    rows = [
        "| Field | Value |",
        "|---|---|",
    ]
    if speaker_cell:
        rows.append(f"| Speaker | {speaker_cell} |")
    if attributed_to:
        rows.append(f"| Attributed to | {attributed_to} |")
    if src_link:
        rows.append(f"| Source | {src_link} |")
    if loc:
        rows.append(f"| Location | {loc} |")
    return "\n".join(rows)


# List-marker line-starts that begin a new logical line (kept as their own
# blockquote line); any other non-blank line is soft-wrap and joins with a
# space. Covers the markers the corpus's quotes actually use — bullets
# (•/‣/·/▪/◦), en/em-dash bullets, and "1." / "1)" / "(1)" numbering.
_LIST_MARKER_RE = re.compile(r"^\s*([•‣·▪◦]|[-–—]\s|\d+[.)]\s|\(\d+\)\s)")


def _reflow_quote_text(text):
    """Collapse a quote's extraction soft-wrap newlines to spaces, preserving
    blank-line paragraph breaks and list-item line structure.

    Quote text copied verbatim from a YAML ``|`` literal block keeps the
    source's physical line-wrapping (PDF/HTML wrap at ~80 cols), which would
    otherwise render one ``> `` per wrapped line — a blockquote broken
    mid-sentence. This rejoins soft-wrapped prose into one line per paragraph
    while keeping intentional structure: a blank line stays a paragraph break,
    and a line that opens a list item (or its indented continuation) stays its
    own line. Verification is unaffected (the verbatim-quote check normalizes
    whitespace; this only changes display)."""
    out, current = [], ""
    for raw in (text or "").rstrip("\n").split("\n"):
        if raw.strip() == "":
            if current:
                out.append(current)
                current = ""
            out.append("")  # paragraph break
        elif current == "" or _LIST_MARKER_RE.match(raw):
            if current:
                out.append(current)
            current = raw.strip()
        else:
            current += " " + raw.strip()
    if current:
        out.append(current)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


def _render_blockquote(text):
    """Render quote text as a Markdown blockquote, reflowing soft-wrap
    newlines via ``_reflow_quote_text``. The single shared helper for every
    quote surface (person Statements, Key Passages, Key Testimony) so the
    blockquote form is consistent and not re-implemented per renderer."""
    reflowed = _reflow_quote_text(text)
    return "\n".join(f"> {ln}" if ln else ">" for ln in reflowed.split("\n"))


def _render_statement_block(quote, artifact):
    """Render a single block-quote + verification block pair.

    Sub-threshold quotes (Q&A answer fragments, short terminology
    extracts) render in compact form: blockquote line + italicized
    attribution continuation, no verification table. Disproportionate
    table noise for one-word answers like ``"Yes."`` is what motivates
    the demotion; long-form quotes keep the standard block."""
    text = (quote.get("text") or "").rstrip("\n")
    if len(text.strip()) < _COMPACT_STATEMENT_CHAR_THRESHOLD:
        return _render_compact_statement_block(quote, text)
    return (
        _render_blockquote(text) + "\n\n"
        + _render_attribution_block(quote, artifact)
    )


def _render_compact_statement_block(quote, text):
    """One-line blockquote + italicized attribution continuation for
    sub-threshold quotes. Preserves Attributed-to / Source / Location
    inline without the 3-4-row verification table."""
    attributed_to = _compose_attributed_to(
        quote.get("context"), quote.get("statement_date")
    )
    src = quote.get("source") or {}
    src_path = src.get("path") or ""
    src_link = f"[archived source](../sources/{src_path})" if src_path else ""
    loc = src.get("location") or ""

    parts = [p for p in [attributed_to, src_link, loc] if p]
    attr_line = "; ".join(parts)

    quote_line = _render_blockquote(text)
    if attr_line:
        # Blank line breaks the blockquote — attribution renders as a
        # separate italicized paragraph so the reader sees the quote
        # and its attribution as visually distinct surfaces.
        return f"{quote_line}\n\n_{attr_line}_"
    return quote_line


# ============================================================================
# Investigation Sources rollup (used by hypothesis_evaluation /
# best_current_answer / counter_evidence on investigation nodes)
# ============================================================================

def _render_sources_rollup(sources):
    """Render a per-subsection **Sources:** rollup. Each entry has
    either finding_path or entity_path + anchor, plus a required
    description. Returns "" when no sources (caller decides whether
    to emit a TODO comment)."""
    items = [s for s in (sources or []) if isinstance(s, dict)]
    if not items:
        return ""
    lines = ["**Sources:**", ""]
    for s in items:
        description = (s.get("description") or "").strip()
        if s.get("finding_path"):
            wrap = _wrap_path(s["finding_path"])
            lines.append(f"- {wrap} — {description}")
        elif s.get("entity_path"):
            wrap = _wrap_path(s["entity_path"])
            anchor = s.get("anchor") or ""
            anchor_str = f" {anchor}" if anchor else ""
            lines.append(f"- {wrap}{anchor_str} — {description}")
        else:
            lines.append(f"- (malformed source entry) — {description}")
    return "\n".join(lines) + "\n"
