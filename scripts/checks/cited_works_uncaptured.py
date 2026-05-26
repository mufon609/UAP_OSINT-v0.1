"""cited-works-uncaptured check — a source reference list left uncaptured.

Hard-error gate closing the enforcement gap that let document nodes ship
with an empty ``cited_works[]`` even though their primary source carries a
formal References / Bibliography section. Capturing that list is mandatory
where the source contains it (``meta/conventions.md`` DIRD rubric, and the
document-artifact schema's required-but-emptyable ``cited_works``); the
``### Density is source-driven`` rule governs HOW MANY entries go in once a
section is populated, never WHETHER to capture a source-attested reference
list at all. Conflating the two — "the references aren't load-bearing, so
leave it empty" — is the exact failure this check forecloses.

Scope + firing:
  - Runs only for document artifacts (``cited_works`` is document-scoped;
    gated by ``section_in_scope``).
  - Fires only when ``cited_works`` is empty/absent AND at least one
    primary source's extracted text exhibits a reference-list signal — a
    ``References`` / ``Bibliography`` heading followed by a run of numbered
    citation markers, OR a dense headingless tail run of numbered markers
    (the endnote style some journal articles use). The empty list stays
    legitimate for a document whose source carries no reference list (an
    executive order, a short news item, a hearing transcript): those
    produce no signal and no error.

This detects the BINARY presence of an uncaptured list, never a count: it
does not compare entry counts or peer nodes (that pressure is what
``### Density is source-driven`` prohibits). Verbatim fidelity of the
entries once populated is the separate ``cited_works`` check; cross-layer
node-body coverage is ``coverage``. OCR-scan PDFs are read through their
verified ``.txt`` sibling via ``extract_source_text``.
"""

import re

from checks import Issue
from checks._research_utils import entries, section_in_scope
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
#   [1]     bracket                                    (dird-24)
#   (1)     parenthetical                              (dird-10)
#   ^1      superscript endnote/footnote, no period    (dird-01)
#   1.1     dotted chapter.ref                         (dird-09)
#   1.      plain numbered + space
# The marker set is path-dependent, and that split is load-bearing:
#   - AFTER a confirmed References heading the broad set is safe (we are
#     past any table of contents), and ``(N)`` is genuine reference
#     numbering (dird-10's references are "(1) Baibich, M. N., et al., …").
#   - On the HEADINGLESS path ``(N)`` is EXCLUDED — there it is the shape of
#     statutory/legislative enumeration (the proposed UAP Disclosure Act's
#     "(1) … (2) …" subsections), a costly false positive for a hard gate —
#     as are bare ``N.`` and dotted ``N.N`` (a table of contents / numbered
#     section list). Only ``[N]`` and ``^N`` survive headingless.
_HEADING_MARKER_RE = re.compile(
    r'(?m)^[ \t]*(?:\[\d{1,3}\]|\(\d{1,3}\)|\^\d{1,3}\b|'
    r'\d{1,2}\.\d{1,3}\b|\d{1,3}\.(?=[ \t]))'
)
_FOOTNOTE_MARKER_RE = re.compile(
    r'(?m)^[ \t]*(?:\[\d{1,3}\]|\^\d{1,3}\b)'
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
    # Already populated → nothing to flag (verbatim is the cited_works
    # check's job). Empty or absent → scan the sources.
    if entries(ctx.data, "cited_works"):
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
                ctx.rel, "error",
                f"cited_works is empty but primary source sources/{rel_source} "
                f"carries a reference list (References / Bibliography section "
                f"detected) — capture it into cited_works[]. The source "
                f"reference list is mandatory where present (meta/conventions.md "
                f"DIRD rubric + document-artifact schema); 'density is "
                f"source-driven' governs entry count, never whether to capture "
                f"the list.",
                check_name=CHECK_NAME,
            )
            return  # one diagnostic per artifact
