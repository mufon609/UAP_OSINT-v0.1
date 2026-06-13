#!/usr/bin/env python3
"""Regression guard for the two location-grammar bans:

  1. location_format  — page-RANGE ban: `p. 9-37` / `pp. 1-33` are never a
     valid location (a quote anchors to a single page; a span-cite splits or
     names the single attesting page).
  2. quote_location_page — sibling-`p.N` ban: a physical-page ref on an
     OCR-scan / extraction-lossy source whose canonical extract is a markerless
     `.txt` sibling names a page nothing can verify; the schema requires a
     descriptive content anchor there. This guard is UNIVERSAL — it covers
     every section's `source.location`, not just the quote-bearing three.

Both were added after a corpus-wide conformance pass (212 non-conforming refs:
175 sibling-`p.N` quote/timeline/naming + 37 in relationship/personnel/cited-
works sections + 6 text-native ranges). Without these guards the class silently
re-accumulates, because the page-against-form-feed verifier skips sibling
sources by design. This test asserts both bans FIRE on bad data and do NOT
false-positive on the legitimate forms next to them.

Uses real corpus source paths so `_is_sibling_backed` exercises the manifest +
sibling-existence logic, not a mock. Cheap; no scaffolding.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from checks import location_format, quote_location_page

# A real OCR-scan source with a .txt sibling (sibling-backed) and a real
# text-native paginated source (not sibling-backed).
SIBLING_SRC = ("government/cia-kress-parapsychology-in-intelligence-studies-"
               "intelligence-1977-declassified-1996.pdf")
TEXTNATIVE_SRC = "government/congress-gov-house-hearing-transcript-20230726.pdf"


class _Ctx:
    def __init__(self, data):
        self.rel = "test"
        self.data = data


def _msgs(check, data):
    return [i.message for i in check(_Ctx(data))]


def _has(msgs, needle):
    return any(needle in m for m in msgs)


CASES = []  # (label, ok: bool, detail)


def record(label, ok, detail=""):
    CASES.append((label, ok, detail))


def run():
    # ---- range-ban (location_format), runs on every location string ----
    m = _msgs(location_format.check,
              {"quotes": [{"id": "q1", "text": "x",
                           "source": {"path": "government/foo.pdf", "location": "p. 9-37"}}]})
    record("range-ban fires on 'p. 9-37'", _has(m, "page-range location"))

    m = _msgs(location_format.check,
              {"timeline": [{"id": "t1", "event": "x",
                             "source": {"path": "government/foo.pdf", "location": "pp. 1-33"}}]})
    record("range-ban fires on 'pp. 1-33' (timeline)", _has(m, "page-range location"))

    # negative: a descriptive tail merely CONTAINING a hyphenated token
    m = _msgs(location_format.check,
              {"quotes": [{"id": "q1", "text": "x",
                           "source": {"path": "x",
                                      "location": "Section I Contract Clauses, DFARS 252.219-7009 full-text clause"}}]})
    record("range-ban NO false-positive on 'DFARS 252.219-7009'",
           not _has(m, "page-range location"))

    # ---- sibling-p.N ban (quote_location_page), universal across sections ----
    m = _msgs(quote_location_page.check,
              {"quotes": [{"id": "q1", "text": "x",
                           "source": {"path": SIBLING_SRC, "location": "p. 8, ¶2"}}]})
    record("sibling-ban fires on sibling-backed 'p. 8, ¶2' (quotes)",
           _has(m, "sibling-backed source"))

    # universal: same trap in a NON-quote section must also fire
    m = _msgs(quote_location_page.check,
              {"relationships": [{"id": "r1",
                                  "source": {"path": SIBLING_SRC, "location": "p. 2"}}]})
    record("sibling-ban fires universally (relationships section)",
           _has(m, "sibling-backed source"))

    # negative: a descriptive anchor on the SAME sibling source is fine
    m = _msgs(quote_location_page.check,
              {"quotes": [{"id": "q1", "text": "x",
                           "source": {"path": SIBLING_SRC, "location": "¶ abstract"}}]})
    record("sibling-ban NO false-positive on descriptive '¶ abstract'",
           not _has(m, "sibling-backed source"))

    # negative: a physical page on a TEXT-NATIVE source is legitimate
    m = _msgs(quote_location_page.check,
              {"quotes": [{"id": "q1", "text": "x",
                           "source": {"path": TEXTNATIVE_SRC, "location": "p. 43"}}]})
    record("sibling-ban NO false-positive on text-native 'p. 43'",
           not _has(m, "sibling-backed source"))


def main():
    print("=" * 70)
    print(" location-grammar bans regression test")
    print("=" * 70)
    print()
    run()
    failures = [(label, detail) for label, ok, detail in CASES if not ok]
    if failures:
        print(f"  FAILED — {len(failures)}/{len(CASES)} case(s):")
        for label, detail in failures:
            print(f"    - {label}  {detail}")
        return 1
    print(f"  PASSED — {len(CASES)} cases (both bans fire; no false positives)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
