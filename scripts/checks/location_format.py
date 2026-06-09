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
# A printed-folio dual annotation: "printed p. N" / "(printed pp. N-M)".
_PRINTED = re.compile(r"\bprinted\s+pp?\.", re.IGNORECASE)


def check(ctx):
    data = ctx.data
    if not isinstance(data, dict):
        return
    for loc_path, loc in walk_locations(data):
        m = _ROMAN.search(loc)
        if m:
            yield Issue(
                ctx.rel, "error",
                f"{loc_path}: roman-numeral page ref \"p. {m.group(1)}\" — "
                f"`p. N` must be the physical / PDF-viewer page (an integer), "
                f"not the printed front-matter folio: \"{loc}\"",
                check_name=CHECK_NAME,
            )
        if _PRINTED.search(loc):
            yield Issue(
                ctx.rel, "error",
                f"{loc_path}: `printed p.` dual annotation — the convention is "
                f"physical-page-only location refs plus a single node-level "
                f"stated note, not per-quote printed-folio annotation: "
                f"\"{loc}\"",
                check_name=CHECK_NAME,
            )
