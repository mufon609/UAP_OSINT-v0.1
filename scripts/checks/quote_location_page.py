"""quote-location-page check — per-artifact ResearchContext check.

For every quote whose ``source.location`` names a physical page (``p. N``),
confirm the quote ``text`` actually appears on physical page N of the cited
source.

The verbatim-quote check confirms the quote text appears *somewhere* in the
source file; it is page-blind. This check closes that gap. It splits the
extracted source on the form-feed page separators ``pdftotext`` emits per page
(and ``lib._common.extract_source_text`` preserves) and verifies the cited page
is the one carrying the text. A ``p. N`` pointing at the wrong page — the easy
error when a composite PDF's physical pages diverge from its printed page
numbers (a cover letter, a questions attachment, an unnumbered first page each
shift the count) — is caught here instead of passing silently.

``p. N`` is the **physical** page: the page a PDF viewer shows = the Nth
form-feed-delimited block of the extract. See ``meta/conventions.md`` "Quote
location refs" for the convention this enforces.

Eligibility is decided by one signal — does the extract carry form-feed page
separators? Text-native PDFs get them from ``pdftotext``; OCR-scan /
extraction-lossy sources get them from their clean ``.txt`` sibling, where
``extract_source_text`` has normalized the ``----- PAGE BREAK -----`` marker
to ``\f`` (so an OCR source's ``p. N`` is its Nth document page = Nth sibling
block). Everything else is skipped, so the check never false-fails:
  - Only quotes whose location matches ``p. N`` (integer page). Roman-numeral
    front matter (``p. ii``), paragraph anchors (``¶N``), caption timestamps
    (``[MM:SS]``), and FOIA ``Doc N`` anchors carry no physical-page claim.
  - Sources whose extract has no form feed: HTML / TXT articles (``¶N``
    anchors), single-page PDFs, and OCR siblings that carry no page marker
    (``extract_source_text`` strips their stray form feeds) — no page structure
    to index.

A quote that matches no single page (its text straddles a page boundary) is a
convention violation in its own right — page-spanning quotes split at the
boundary into two adjacent ≤1-page quotes — and is reported as such.
"""

import re

from checks import Issue
from checks._research_utils import entries
from lib._common import SOURCES_DIR, extract_source_text, normalize_for_compare


CHECK_NAME = "quote_location_page"

# Leading `p. N` / `p.N` with an integer page. Roman numerals (`p. ii`),
# `¶N`, `[MM:SS]`, and `Doc N` carry no physical-page claim and don't match.
_PAGE_REF = re.compile(r"^\s*p\.\s*(\d+)\b")


def check(ctx):
    for i, q in enumerate(entries(ctx.data, "quotes")):
        if not isinstance(q, dict):
            continue
        text = q.get("text")
        src = q.get("source")
        if not text or not isinstance(text, str) or not isinstance(src, dict):
            continue  # the `quotes` shape check yields the diagnostic
        rel_source = src.get("path")
        location = src.get("location")
        if not rel_source or not isinstance(location, str):
            continue
        m = _PAGE_REF.match(location)
        if not m:
            continue  # not a `p. N` page ref — out of scope
        page = int(m.group(1))

        source_file = SOURCES_DIR / rel_source
        if not source_file.exists():
            continue  # verbatim_quotes yields the missing-file error
        source_text = extract_source_text(source_file)
        if not source_text or "\f" not in source_text:
            continue  # no form-feed page structure → nothing to index

        pages = source_text.split("\f")
        while len(pages) > 1 and pages[-1].strip() == "":
            pages.pop()  # drop pdftotext's trailing form-feed block
        n_pages = len(pages)
        norm_quote = normalize_for_compare(text)
        found = [p + 1 for p, pg in enumerate(pages)
                 if norm_quote in normalize_for_compare(pg)]
        if page in found:
            continue  # cited page is the page that carries the text

        qid = q.get("id")
        if found:
            where = f"the text is on p. {', '.join(map(str, found))}"
        elif page > n_pages:
            where = (f"sources/{rel_source} has {n_pages} page(s) and the text "
                     f"appears on no single page")
        else:
            where = ("the text appears on no single page — it may span a page "
                     "boundary; split it at the boundary per convention")
        preview = text[:60] + ("..." if len(text) > 60 else "")
        yield Issue(
            ctx.rel, "error",
            f"quotes[{i}] ({qid!r}): cites p. {page} of sources/{rel_source} "
            f'but {where}: "{preview}"',
            check_name=CHECK_NAME,
        )
