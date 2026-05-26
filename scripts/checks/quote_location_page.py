"""location-page check — per-artifact ResearchContext check.

For every `source.location` (or naming-quirk `location`) that names a physical
page (`p. N`), confirm the cited page is the right one. The verbatim-quote check
confirms a quote's text appears *somewhere* in the source; it is page-blind.
This check closes that gap for `p. N` refs across the three artifact sections
that carry them — the check name keeps the primary `quote` case but the scope is
broader:

  - ``quotes[]``        — the quote ``text`` must appear on physical page N.
  - ``naming_quirks[]`` — the verbatim ``observed`` source-form token must appear
                          on physical page N (cited via ``source_path`` +
                          ``location``).
  - ``timeline[]``      — the ``event`` is a contributor paraphrase, not verbatim,
                          so only page EXISTENCE is mechanically checkable: page N
                          must exist in the source. A timeline `p. N` that is
                          off-by-a-few has no verbatim anchor to verify against and
                          rests on contributor care (see meta/conventions.md).

`p. N` is the **physical** page a PDF viewer shows: the Nth form-feed-delimited
block of the extract. This check verifies `p. N` **only where the source's own
extraction yields form feeds natively** — text-native PDFs via `pdftotext`,
where the wrong page (the easy error when physical pages diverge from printed
page numbers — a cover, a front-matter block, a FOIA insert all shift the
count) is caught here instead of passing silently.

A sibling-backed source (OCR-scan / extraction-lossy) carries **no synthetic
page markers** — never manufacture page structure in a sibling — so its extract
has no form feeds and this check skips it **by design**, not as a silent defect.
For such a source `p. N` is a verbatim-anchored navigation hint: the
verbatim-quote check confirms the text is in the source, and page-precision
rests on contributor care (see meta/conventions.md).

Eligibility is one signal: does the extract carry form-feed page separators?
Everything else is skipped, so the check never false-fails: locations that
aren't `p. N` (roman `p. ii`, `¶N`, `[MM:SS]`, `Doc N`); and sources whose
extract has no form feed (HTML/TXT `¶N` articles, single-page PDFs, and all
sibling-backed sources — any stray form feed is stripped by
`extract_source_text`).

A quote (or observed token) on no single page straddles a page boundary —
page-spanning quotes split at the boundary into two ≤1-page quotes — and is
reported as such.
"""

import re

from checks import Issue
from checks._research_utils import entries
from lib._common import SOURCES_DIR, extract_source_text, normalize_for_compare


CHECK_NAME = "quote_location_page"

# Leading `p. N` / `p.N` with an integer page. Roman numerals (`p. ii`),
# `¶N`, `[MM:SS]`, and `Doc N` carry no physical-page claim and don't match.
_PAGE_REF = re.compile(r"^\s*p\.\s*(\d+)\b")


def _cited_page(location):
    """Return the integer physical page a `p. N` location names, or None."""
    if not isinstance(location, str):
        return None
    m = _PAGE_REF.match(location)
    return int(m.group(1)) if m else None


def _pages(rel_source):
    """Return the source's physical pages as a list of block strings, or None
    if the extract has no form-feed page structure (HTML/TXT, single-page PDF,
    or an unpaginated sibling whose stray form feeds were stripped)."""
    source_file = SOURCES_DIR / rel_source
    if not source_file.exists():
        return None  # the verbatim / path checks own the missing-file error
    text = extract_source_text(source_file)
    if not text or "\f" not in text:
        return None
    pages = text.split("\f")
    while len(pages) > 1 and pages[-1].strip() == "":
        pages.pop()  # drop pdftotext's trailing form-feed block
    return pages


def _verify_on_page(ctx, section, i, eid, rel_source, page, pages, text,
                    label, span_hint):
    """Yield an Issue if the verbatim ``text`` isn't on physical page ``page``."""
    n_pages = len(pages)
    norm = normalize_for_compare(text)
    found = [p + 1 for p, pg in enumerate(pages)
             if norm in normalize_for_compare(pg)]
    if page in found:
        return
    if found:
        where = f"the {label} is on p. {', '.join(map(str, found))}"
    elif page > n_pages:
        where = (f"sources/{rel_source} has {n_pages} page(s) and the {label} "
                 f"appears on no single page")
    else:
        where = f"the {label} appears on no single page of sources/{rel_source}"
        if span_hint:
            where += " — it may span a page boundary; split it at the boundary per convention"
    preview = text[:60] + ("..." if len(text) > 60 else "")
    yield Issue(
        ctx.rel, "error",
        f"{section}[{i}] ({eid!r}): cites p. {page} but {where}: \"{preview}\"",
        check_name=CHECK_NAME,
    )


def check(ctx):
    # quotes[] — the quote text must be on the cited physical page
    for i, q in enumerate(entries(ctx.data, "quotes")):
        if not isinstance(q, dict):
            continue
        text = q.get("text")
        src = q.get("source")
        if not text or not isinstance(text, str) or not isinstance(src, dict):
            continue  # the `quotes` shape check yields the diagnostic
        rel_source = src.get("path")
        page = _cited_page(src.get("location"))
        if not rel_source or page is None:
            continue
        pages = _pages(rel_source)
        if pages is None:
            continue
        yield from _verify_on_page(ctx, "quotes", i, q.get("id"), rel_source,
                                   page, pages, text, "text", span_hint=True)

    # naming_quirks[] — the verbatim `observed` source-form token must be on the
    # cited page (its location is a flat `p. N` ref against `source_path`)
    for i, nq in enumerate(entries(ctx.data, "naming_quirks")):
        if not isinstance(nq, dict):
            continue
        observed = nq.get("observed")
        rel_source = nq.get("source_path")
        page = _cited_page(nq.get("location"))
        if not observed or not isinstance(observed, str) or not rel_source or page is None:
            continue
        pages = _pages(rel_source)
        if pages is None:
            continue
        yield from _verify_on_page(ctx, "naming_quirks", i, nq.get("id"),
                                   rel_source, page, pages, observed,
                                   "observed form", span_hint=False)

    # timeline[] — the `event` is a paraphrase, not verbatim source text, so only
    # page EXISTENCE is checkable. Off-by-N timeline refs have no verbatim anchor
    # and rest on contributor care.
    for i, t in enumerate(entries(ctx.data, "timeline")):
        if not isinstance(t, dict):
            continue
        src = t.get("source")
        if not isinstance(src, dict):
            continue
        rel_source = src.get("path")
        page = _cited_page(src.get("location"))
        if not rel_source or page is None:
            continue
        pages = _pages(rel_source)
        if pages is None:
            continue
        if page > len(pages):
            yield Issue(
                ctx.rel, "error",
                f"timeline[{i}] ({t.get('id')!r}): cites p. {page} but "
                f"sources/{rel_source} has {len(pages)} page(s)",
                check_name=CHECK_NAME,
            )
