"""anchor_resolves check — per-artifact ResearchContext check.

A `¶ "<leading phrase>"` location anchor is a navigation handle: the schema
(`location` grammar) defines it as "the paragraph's leading words (ctrl-F-able
in the source)". This check confirms it actually IS — the quoted phrase must
occur **exactly once** in the source's extracted text:

  - **0 occurrences** — the anchor resolves nowhere; ctrl-F finds nothing. A
    dead navigation handle (a mis-transcribed phrase, a line-broken token the
    literal string can't match, or the wrong source).
  - **2+ occurrences** — the anchor is ambiguous: which paragraph? Not a unique
    handle; the leading phrase must be extended until it is.

This is the guard the verbatim and location-grammar checks structurally are not.
`verbatim_quotes` confirms a quote's `text` appears in the source but is blind to
the `location` field; `location_format` / `quote_location_page` police the
location's *grammar* (no ranges, no sibling `p. N`) but never confirm a
descriptive anchor *resolves*. A `¶ "<phrase>"` that points nowhere passes both
yet is a broken citation — invisible until someone tries to follow it.

Scope is deliberately narrow: ONLY the explicit `¶ "<phrase>"` form, where the
contributor committed to a ctrl-F-able quoted phrase. Free-form named-block
anchors (`title-page identity block`, `Figure 1 (KEY US RESEARCH EFFORTS
table)`, `Section A`, `transmittal letter signature block`) are descriptions of
a location, not verbatim source substrings, and are out of scope — as are the
many other quoted strings that appear in `location` fields as descriptive
context (a section title, an article name, a `"date_signed"` field reference).

Both the phrase and the source go through `normalize_for_compare` (the same
normalization the verbatim check uses), so smart quotes, em/en dashes, hyphens,
line-wrap hyphenation, and whitespace differences never cause a false miss. The
universal walk (`_walk_source_locations`) covers EVERY section's
`source.location` — quotes, naming_quirks, timeline, relationships, cited_works
— because a broken anchor traps the same way wherever it sits. Sources that are
missing, binary-by-design, or extraction-failed are skipped here; the verbatim /
path checks own those diagnostics.
"""

import re

from checks import Issue
from checks.quote_location_page import _walk_source_locations
from lib._common import (
    SOURCES_DIR,
    extract_source_text,
    normalize_for_compare,
)

CHECK_NAME = "anchor_resolves"

# The `¶ "<phrase>"` ctrl-F anchor, straight or curly quotes. Only this explicit
# quoted-phrase form is in scope — a descriptive named-block anchor carries no `¶`.
_ANCHOR = re.compile(r'¶\s*["“]([^"”]+)["”]')


def check(ctx):
    data = ctx.data
    if not isinstance(data, dict):
        return
    # rel_source -> normalized source text, or None when the source can't be read
    # (missing / binary / extraction failure — those errors are owned elsewhere).
    norm_cache = {}
    for jpath, rel_source, location in _walk_source_locations(data):
        phrases = _ANCHOR.findall(location)
        if not phrases:
            continue
        if rel_source not in norm_cache:
            source_file = SOURCES_DIR / rel_source
            if not source_file.exists():
                norm_cache[rel_source] = None
            else:
                text = extract_source_text(source_file)
                norm_cache[rel_source] = (
                    normalize_for_compare(text) if text is not None else None
                )
        norm_source = norm_cache[rel_source]
        if norm_source is None:
            continue
        for phrase in phrases:
            norm = normalize_for_compare(phrase)
            if not norm:
                yield Issue(
                    ctx.rel, "error",
                    f'{jpath}: ¶ anchor "{phrase}" normalizes to empty — choose a '
                    f"real leading phrase from the source",
                    check_name=CHECK_NAME,
                )
                continue
            count = norm_source.count(norm)
            if count == 0:
                yield Issue(
                    ctx.rel, "error",
                    f'{jpath}: ¶ anchor "{phrase}" resolves nowhere — occurs 0 times '
                    f"in sources/{rel_source}; a `¶ \"<leading phrase>\"` anchor must be "
                    f"a ctrl-F-able phrase present in the source (mind line-broken / "
                    f"quote-wrapped tokens — pick the paragraph's clean leading words)",
                    check_name=CHECK_NAME,
                )
            elif count > 1:
                yield Issue(
                    ctx.rel, "error",
                    f'{jpath}: ¶ anchor "{phrase}" is ambiguous — occurs {count} times '
                    f"in sources/{rel_source}; extend it to a longer leading phrase that "
                    f"appears exactly once",
                    check_name=CHECK_NAME,
                )
