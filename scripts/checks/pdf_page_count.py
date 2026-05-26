"""pdf_page_count check — per-artifact ResearchContext check.

For an artifact whose primary source is a PDF, ``document_intrinsic.pages``
must equal the PDF's physical page count — what a PDF viewer's page counter
shows, read from the page tree via ``pdfinfo``. The drift this catches: a
``pages`` value taken from the highest *printed* folio, which undercounts by
the front-matter length (cover + Black Vault insert + roman front matter), or
one copied from a third-party page listing. Source of truth is the archived
file itself.

The count is read from the PDF's page tree (never a ``.txt`` sibling, never the
text layer), so it is correct for OCR-scan sources whose canonical extract is a
sibling — precisely the sources ``quote_location_page`` skips — and for
image-only scans with no text layer.

Scope is deliberately the declared count only. A "no ``p. N`` beyond the last
physical page" guard was considered and dropped: it false-flags the legitimate
cases where a ``p. N`` is *not* the source's physical page — a journal article
scan cited by its journal pagination, or a location annotation that names
another document's page — and printed-folio drift itself *undercounts*, so it
would not even catch the pattern this cleanup targets. ``location_format``
(roman / printed-folio refs) and this declared-count guard cover that;
content-on-page correctness for OCR-scan sources stays uncheckable mechanically
and rests on contributor care + the source-image re-verification pass
(meta/conventions.md).
"""

from checks import Issue
from lib._common import SOURCES_DIR, pdf_physical_page_count

CHECK_NAME = "pdf_page_count"


def _pdf_source(data):
    """Return (rel_path, abs_path) of the first PDF primary source, or None."""
    srcs = data.get("primary_sources")
    if not isinstance(srcs, list):
        return None
    for s in srcs:
        if (isinstance(s, dict) and isinstance(s.get("path"), str)
                and s["path"].lower().endswith(".pdf")):
            return s["path"], SOURCES_DIR / s["path"]
    return None


def check(ctx):
    data = ctx.data
    if not isinstance(data, dict):
        return
    src = _pdf_source(data)
    if not src:
        return
    rel_path, abs_path = src
    n = pdf_physical_page_count(abs_path)
    if n is None:
        return  # file absent / pdfinfo unavailable — path checks own that

    dm = data.get("document_intrinsic")
    declared = dm.get("pages") if isinstance(dm, dict) else None
    if declared is None:
        return
    try:
        declared_int = int(declared)
    except (TypeError, ValueError):
        return  # non-numeric pages — the shape check owns that
    if declared_int != n:
        yield Issue(
            ctx.rel, "error",
            f"document_intrinsic.pages = {declared!r} but sources/{rel_path} "
            f"has {n} physical pages (pdfinfo) — the declared count must be the "
            f"file's physical page count, not the highest printed folio.",
            check_name=CHECK_NAME,
        )
