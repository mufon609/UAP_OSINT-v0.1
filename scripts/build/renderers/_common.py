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

from lib._common import REPO_ROOT, parse_date_tuple, strict_yaml_load


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
# Manifest sha256 lookup (cached)
# ============================================================================

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
                    entries = strict_yaml_load(f) or []
                _manifest_sha256_cache = {
                    e.get("path"): e.get("sha256")
                    for e in entries
                    if isinstance(e, dict) and e.get("path") and e.get("sha256")
                }
            except (yaml.YAMLError, OSError):
                _manifest_sha256_cache = {}
    return _manifest_sha256_cache.get(path, "") or ""


# ============================================================================
# Statement block renderers (used by person / event / transcript /
# media / organization / location / finding)
# ============================================================================

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
    """Render a single block-quote + verification block pair.

    Sub-threshold quotes (Q&A answer fragments, short terminology
    extracts) render in compact form: blockquote line + italicized
    attribution continuation, no verification table. Disproportionate
    table noise for one-word answers like ``"Yes."`` is what motivates
    the demotion; long-form quotes keep the standard block."""
    text = (quote.get("text") or "").rstrip("\n")
    if len(text.strip()) < _COMPACT_STATEMENT_CHAR_THRESHOLD:
        return _render_compact_statement_block(quote, text)
    lines = []
    for qline in text.split("\n"):
        lines.append(f"> {qline}" if qline else ">")
    lines.append("")
    lines.append(_render_attribution_block(quote, artifact))
    return "\n".join(lines)


def _render_compact_statement_block(quote, text):
    """One-line blockquote + italicized attribution continuation for
    sub-threshold quotes. Preserves Attributed-to / Source / Location
    inline without the 3-4-row verification table."""
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

    parts = [p for p in [attributed_to, src_link, loc] if p]
    attr_line = "; ".join(parts)

    quote_line = f"> {text}" if text else ">"
    if attr_line:
        # Blank line breaks the blockquote — attribution renders as a
        # separate italicized paragraph. Keeps it out of the
        # verbatim-quote check's blockquote scan.
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
