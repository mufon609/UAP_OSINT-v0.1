"""location_format check — per-artifact ResearchContext check.

Enforces the physical-page citation convention on every ``location`` field.
A page ref is ``p. N`` where N is the **physical / PDF-viewer page** — an
integer, the Nth page of the file. Two deviations are banned:

  - **roman-numeral page refs** (``p. ii``, ``p. v``, ``pp. iv-v``) — these
    are the printed front-matter folio a composite document carries on its
    face; physical pages are always integers.
  - **``printed p.`` dual annotations** (``(printed p. 8)``, ``printed pp.
    32-33``) — the per-quote printed-folio annotation. The convention is
    physical-only location refs with a single node-level stated note (emitted
    by the document renderer), not dual annotation.
  - **page-range refs** (``p. 9-37``, ``pp. 1-33``) — a location anchors a
    quote to its bounds, no more, no less; a quote sits on a single page (a
    boundary-spanning passage splits into two ≤1-page quotes). A range is a
    section span-cite masquerading as a page anchor — cite the single page the
    text actually sits on. timeline/existence refs name the single attesting
    page likewise. Anchored at the start so a descriptive tail that merely
    contains a hyphenated token (``DFARS 252.219-7009``) never matches.

This is the guard ``quote_location_page`` structurally cannot be: that check
skips sibling-backed OCR-scan sources (their canonical extract has no form
feeds), so a sibling-only check is needed there. This check is a pure string
check on the artifact data, so it runs regardless of extraction type — the
mechanical backstop that keeps a rebuilt or newly added node from
reintroducing printed/roman page refs.

Anchored on ``p.`` so a chapter/section roman numeral not prefixed by ``p.``
(e.g. ``(III. Origin of Zero-Point Field Energy)``) never matches; and a
``p. N`` integer page never matches the roman pattern.
"""

import re

from checks import Issue
from checks._research_utils import walk_locations

CHECK_NAME = "location_format"

# `p. <roman>` / `pp. <roman>` — front-matter printed folio (physical pages
# are integers). The trailing \b stops "p. vs" / "p. version" from matching.
_ROMAN = re.compile(r"\bpp?\.\s*([ivxlcdm]+)\b", re.IGNORECASE)
# A candidate run of roman letters is only a page ref if it is a *well-formed*
# roman numeral — otherwise the broad scan above false-flags ordinary words
# made entirely of i/v/x/l/c/d/m ("p. civil", "p. mid", "p. dim").
_ROMAN_WELLFORMED = re.compile(
    r"^m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$",
    re.IGNORECASE,
)
# A printed-folio dual annotation: "printed p. N" / "(printed pp. N-M)".
_PRINTED = re.compile(r"\bprinted\s+pp?\.", re.IGNORECASE)
# A leading integer page-range: `p. 9-37` / `pp. 1-33` (hyphen / en- / em-dash).
# Anchored at the start so `Section I ... DFARS 252.219-7009` never matches.
_RANGE = re.compile(r"^\s*pp?\.\s*\d+\s*[-–—]\s*\d+")


def check(ctx):
    data = ctx.data
    if not isinstance(data, dict):
        return
    for loc_path, loc in walk_locations(data):
        for m in _ROMAN.finditer(loc):
            if not _ROMAN_WELLFORMED.match(m.group(1)):
                continue  # an all-roman-letter word, not a numeral
            yield Issue(
                ctx.rel, "error",
                f"{loc_path}: roman-numeral page ref \"p. {m.group(1)}\" — "
                f"`p. N` must be the physical / PDF-viewer page (an integer), "
                f"not the printed front-matter folio: \"{loc}\"",
                check_name=CHECK_NAME,
            )
            break
        if _PRINTED.search(loc):
            yield Issue(
                ctx.rel, "error",
                f"{loc_path}: `printed p.` dual annotation — the convention is "
                f"physical-page-only location refs plus a single node-level "
                f"stated note, not per-quote printed-folio annotation: "
                f"\"{loc}\"",
                check_name=CHECK_NAME,
            )
        if _RANGE.match(loc):
            yield Issue(
                ctx.rel, "error",
                f"{loc_path}: page-range location \"{loc}\" — a quote anchors to "
                f"a single page (a boundary-spanning passage splits into two "
                f"≤1-page quotes); cite the single page the text sits on, not a "
                f"section span",
                check_name=CHECK_NAME,
            )
