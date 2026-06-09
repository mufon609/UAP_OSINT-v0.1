"""cited-works-uncaptured check — cross-check on the NONE affirmation.

WARN-level cross-check, paired with the explicit three-state affirmation
on ``cited_works`` (see the ``cited_works`` check). The primary
enforcement is now structural:
a document artifact's ``cited_works`` must be ``NONE`` (source has no
reference list), ``IGNORED`` (source has one, deliberately not captured),
or a non-empty list of entries; a bare ``cited_works: []`` is rejected
outright. This check exists to catch the one residual failure mode the
structural form can't — a contributor affirming ``NONE`` when the source
actually does carry a reference list (a false affirmation).

Scope + firing:
  - Runs only for document artifacts (``cited_works`` is document-scoped;
    gated by ``section_in_scope``).
  - Fires only when ``cited_works == 'NONE'`` AND at least one primary
    source's extracted text exhibits a reference-list signal — a
    ``References`` / ``Bibliography`` heading followed by a run of
    numbered citation markers, OR a dense run of high-confidence
    citation markers anywhere in the text with no heading (the appended-
    endnote style, e.g. Unicode-superscript ``¹ Author …`` entries).
  - Explicitly does NOT fire on ``cited_works == 'IGNORED'`` — the
    contributor has affirmed the source HAS a list and is deliberately
    skipping it; signal-in-source is the EXPECTED state and warning on
    it would be noise. The audit surface for ``IGNORED`` is the
    rendered node + a repo-wide grep, NOT this check.
  - Detection regexes intentionally retain documented false negatives
    (bare ``N␣Author``, unnumbered bibliographies, headingless ``N.``)
    — those formats no longer matter as a gate now that affirmation is
    explicit. The heuristic stays cheap and zero-false-positive; the
    affirmation is doing the structural work.

This detects the BINARY presence of an unaffirmed list, never a count:
it does not compare entry counts or peer nodes (that pressure is what
build-protocol "Density is source-driven" prohibits). Verbatim fidelity of
populated entries is the ``cited_works`` check; cross-layer node-body
coverage is ``coverage``. OCR-scan PDFs are read through their verified
``.txt`` sibling via ``extract_source_text``.
"""

import re

from checks import Issue
from checks._research_utils import section_in_scope
from lib._common import (
    BINARY_FORMATS,
    SOURCES_DIR,
    extract_source_text,
    manifest_format,
)

CHECK_NAME = "cited_works_uncaptured"

# A reference-list section heading: optional leading section number
# (arabic or roman), then one of the canonical heading words alone on its
# line. Case-insensitive; tolerant of a trailing colon from OCR.
_HEADING_RE = re.compile(
    r'(?im)^[ \t]*'
    r'(?:\d{1,2}[.)]?[ \t]+|[ivxlcdm]{1,5}[.)][ \t]+)?'
    r'(?:references(?:[ \t]+and[ \t]+notes|[ \t]+cited)?|bibliography|'
    r'works[ \t]+cited|literature[ \t]+cited|reference[ \t]+list)'
    r'[ \t]*:?[ \t]*$'
)

# Line-initial citation markers, in the formats observed across the corpus:
#   [1]     bracket
#   (1)     parenthetical
#   ^1      ASCII-caret superscript, no period
#   ¹       Unicode superscript endnote
#   1.1     dotted chapter.ref
#   1.      plain numbered + space
# The marker set is path-dependent, and that split is load-bearing:
#   - AFTER a confirmed References heading the broad set is safe (past any
#     table of contents); there ``(N)`` is genuine reference numbering.
#   - On the HEADINGLESS path ``(N)`` is EXCLUDED — there it is the shape of
#     statutory/legislative enumeration in legal text (``(1) … (2) …``
#     numbered subsections), a costly false positive for a hard gate — as
#     are bare ``N.`` and dotted ``N.N`` (a table of contents / numbered
#     section list). Only the unambiguous endnote markers survive headingless:
#     ``[N]``, ASCII ``^N``, and line-initial Unicode superscripts (inline
#     superscript CALLOUTS are not line-initial, so they don't match).
_SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"
_HEADING_MARKER_RE = re.compile(
    r'(?m)^[ \t]*(?:\[\d{1,3}\]|\(\d{1,3}\)|\^\d{1,3}\b|[' + _SUP + r']{1,3}(?=[ \t])|'
    r'\d{1,2}\.\d{1,3}\b|\d{1,3}\.(?=[ \t]))'
)
_FOOTNOTE_MARKER_RE = re.compile(
    r'(?m)^[ \t]*(?:\[\d{1,3}\]|\^\d{1,3}\b|[' + _SUP + r']{1,3}(?=[ \t]))'
)

# After a heading a handful of markers confirms a real list; the
# headingless endnote path demands a denser run to stay clear of
# incidental line-initial numerals.
_MIN_MARKERS_AFTER_HEADING = 3
_MIN_MARKERS_HEADINGLESS = 10


def _reference_list_signal(text):
    """True if ``text`` exhibits a reference list — a canonical heading
    followed by a run of numbered citation markers, or (headingless) a
    dense run of high-confidence citation markers anywhere in the text
    (the superscript/bracket endnote style some sources use with no
    heading)."""
    if not text:
        return False
    m = _HEADING_RE.search(text)
    if m and len(_HEADING_MARKER_RE.findall(text[m.end():])) >= _MIN_MARKERS_AFTER_HEADING:
        return True
    return len(_FOOTNOTE_MARKER_RE.findall(text)) >= _MIN_MARKERS_HEADINGLESS


def check(ctx):
    # Document-scoped only (same gate as the cited_works entry check).
    if not section_in_scope(ctx, "cited_works"):
        return
    # Fires only on the NONE affirmation — the false-affirmation case.
    # IGNORED expects a signal-bearing source and is the right answer
    # there (the audit surface is the rendered node + grep, not this
    # check). A populated list is handled by the cited_works entry
    # check. A bare [] errors structurally in cited_works (the primary
    # gate) — no need to second-flag it here.
    if ctx.data.get("cited_works") != "NONE":
        return

    for src in (ctx.data.get("primary_sources") or []):
        if not isinstance(src, dict):
            continue
        rel_source = src.get("path")
        if not rel_source:
            continue
        fmt = manifest_format(rel_source) or src.get("format")
        if fmt in BINARY_FORMATS:
            continue  # can't text-scan an image/video for a reference list
        source_file = SOURCES_DIR / rel_source
        if not source_file.exists():
            continue  # missing-file errors come from other checks
        source_text = extract_source_text(source_file)
        if not source_text:
            continue  # extraction failure surfaced elsewhere
        if _reference_list_signal(source_text):
            yield Issue(
                ctx.rel, "warn",
                f"cited_works: NONE affirms the source carries no reference "
                f"list, but a References / Bibliography signal was detected "
                f"in sources/{rel_source} — likely a false affirmation. "
                f"Re-verify the source, then either capture the entries or "
                f"flip the affirmation to IGNORED (deliberate skip).",
                check_name=CHECK_NAME,
            )
            return  # one diagnostic per artifact
