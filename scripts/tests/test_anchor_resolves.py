#!/usr/bin/env python3
"""Regression guard for the descriptive-anchor resolution check
(`scripts/checks/anchor_resolves.py`).

A `¶ "<leading phrase>"` location anchor must resolve to EXACTLY ONE spot in the
source's extracted text — the schema defines it as a ctrl-F-able leading phrase.
0 occurrences = a dead handle (mis-transcribed / line-broken / wrong source);
2+ = an ambiguous handle. Both are errors; a free-form named-block anchor (no
`¶`) and any non-`¶` quoted string in a location are out of scope.

This guards the gap that let 5 broken anchors sit invisibly through the whole
location-grammar campaign: the verbatim check is blind to the `location` field,
and the grammar checks (`location_format` / `quote_location_page`) police the
location's shape but never confirm a descriptive anchor actually resolves.

Uses a real corpus source so `extract_source_text` exercises the real
sibling-aware extraction + `normalize_for_compare`, not a mock.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from checks import anchor_resolves

# A real sibling-backed source whose clean-text .txt is the canonical extract.
SIBLING_SRC = ("government/cia-rdp96-00789r002800180001-2-stargate-project-"
               "an-overview-19930430.pdf")
# A phrase verified to occur exactly once in that sibling, and one verified absent.
UNIQUE_PHRASE = "The effort at SRI was discontinued"
ABSENT_PHRASE = "this exact phrase does not occur in the source zzqqxx"


class _Ctx:
    def __init__(self, data):
        self.rel = "test"
        self.data = data


def _msgs(data):
    return [i.message for i in anchor_resolves.check(_Ctx(data))]


def _has(msgs, needle):
    return any(needle in m for m in msgs)


CASES = []


def record(label, ok, detail=""):
    CASES.append((label, ok, detail))


def _q(location, src=SIBLING_SRC):
    return {"quotes": [{"id": "q1", "text": "x",
                        "source": {"path": src, "location": location}}]}


def run():
    # fires on an anchor that resolves nowhere (0x)
    m = _msgs(_q(f'¶ "{ABSENT_PHRASE}"'))
    record("fires on 0-occurrence anchor", _has(m, "resolves nowhere"))

    # fires on an ambiguous anchor (a short phrase that recurs)
    m = _msgs(_q('¶ "the"'))
    record("fires on ambiguous (2+) anchor", _has(m, "is ambiguous"))

    # NO false-positive on an anchor that resolves to exactly one spot
    m = _msgs(_q(f'¶ "{UNIQUE_PHRASE}"'))
    record("no false-positive on unique anchor", not m, repr(m))

    # universal: the same trap in a NON-quote section fires too
    m = _msgs({"naming_quirks": [{"id": "nq1", "observed": "x",
                                  "source_path": SIBLING_SRC,
                                  "location": f'¶ "{ABSENT_PHRASE}"'}]})
    record("fires universally (naming_quirks section)", _has(m, "resolves nowhere"))

    # out of scope: a descriptive named-block anchor (no ¶) is never checked
    m = _msgs(_q("Figure 1 (KEY US RESEARCH EFFORTS table)"))
    record("ignores non-¶ named-block anchor", not m, repr(m))

    # out of scope: a non-¶ quoted string (section title / article name) is ignored
    m = _msgs(_q('Executive Summary, p. 8, "Named Companies Allegedly Experimenting"'))
    record("ignores non-¶ quoted descriptive string", not m, repr(m))

    # skip cleanly when the source can't be read (missing file) — owned elsewhere
    m = _msgs(_q(f'¶ "{ABSENT_PHRASE}"', src="government/does-not-exist.pdf"))
    record("skips missing source (no spurious error)", not m, repr(m))


def main():
    print("=" * 70)
    print(" descriptive-anchor resolution regression test")
    print("=" * 70)
    print()
    run()
    failures = [(label, detail) for label, ok, detail in CASES if not ok]
    if failures:
        print(f"  FAILED — {len(failures)}/{len(CASES)} case(s):")
        for label, detail in failures:
            print(f"    - {label}  {detail}")
        return 1
    print(f"  PASSED — {len(CASES)} cases (fires on 0x/2+; clean on unique + out-of-scope)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
