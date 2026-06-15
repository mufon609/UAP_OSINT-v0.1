#!/usr/bin/env python3
"""Regression guard for the speaker-attribution consistency check
(`scripts/checks/speaker_attribution_consistency.py`).

Pins the foreign-turn contract. A quote anchored in a `foreign-prepared`
(in-room speaker reading their OWN statement) or `foreign-recitation`
(in-room speaker reading a document aloud) turn is SPOKEN by a known
in-room person — the quote's speaker_id IS that reader. Knowing who is
reading is the point, so it must be **accepted silently**, never warned.
The one real fault is a contradiction: the read-aloud span unambiguously
bracketed by a single in-room speaker who is NOT the attributed one — a
genuine misattribution → **error**. A span at a speaker hand-off (two
different bracketing speakers) is ambiguous from structure alone, so the
declared speaker_id is trusted. Non-speaker foreign turns (music / ad /
intro / archival / …) carry no in-room speaker → **warn**. Live-vs-live
mismatch stays an **error**; a live match stays clean.

This guards the gap that previously emitted a permanent, non-actionable
WARN on every quote drawn from a read-aloud span — flooding the warning
channel with noise on the most common and most-correct case.

Monkeypatches `_load_siblings` with synthetic siblings so the check runs
off in-memory turns, no corpus files required.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from checks import speaker_attribution_consistency as sac

# Two in-room speakers shared by artifact and sibling layers (mapped by node_link).
_SPK = [
    {"id": "s2", "name": "James Lacatski", "node_link": "/people/james-lacatski"},
    {"id": "s1", "name": "Jeremy Corbell", "node_link": "/people/jeremy-corbell"},
]

# Sibling A — a foreign-prepared/foreign-recitation run bracketed on BOTH sides
# by the same in-room speaker (s2), plus a live s1 turn and a foreign-music turn.
# Turn i owns [start_ts_i, start_ts_{i+1}).
_SIB_A = {
    "verification_status": "verified",
    "source_path": "sources/transcripts/test-a.md",
    "speakers": _SPK,
    "turns": [
        {"speaker_id": "s2", "line_range": "1-5", "start_ts": 60},
        {"speaker_id": "foreign-prepared", "line_range": "6-100", "start_ts": 120},
        {"speaker_id": "foreign-recitation", "line_range": "101-150", "start_ts": 600},
        {"speaker_id": "s2", "line_range": "151-155", "start_ts": 900},
        {"speaker_id": "s1", "line_range": "156-160", "start_ts": 1000},
        {"speaker_id": "foreign-music", "line_range": "161", "start_ts": 1100},
        {"speaker_id": "s2", "line_range": "162", "start_ts": 1110},
    ],
}

# Sibling B — a foreign-prepared run at a hand-off: s2 before, s1 after (ambiguous).
_SIB_B = {
    "verification_status": "verified",
    "source_path": "sources/transcripts/test-b.md",
    "speakers": _SPK,
    "turns": [
        {"speaker_id": "s2", "line_range": "1-5", "start_ts": 60},
        {"speaker_id": "foreign-prepared", "line_range": "6-100", "start_ts": 120},
        {"speaker_id": "s1", "line_range": "101-105", "start_ts": 900},
    ],
}

_SIBLINGS = {"transcripts/test-a.md": _SIB_A, "transcripts/test-b.md": _SIB_B}


class _Ctx:
    target_type = "transcript"
    rel = "test"

    def __init__(self, quotes):
        self.data = {"speakers": _SPK, "quotes": quotes}


def _q(location, speaker_id, path="transcripts/test-a.md"):
    return {"id": "q1", "text": "x", "speaker_id": speaker_id,
            "source": {"path": path, "location": location}}


def _issues(quote):
    return list(sac.check(_Ctx([quote])))


CASES = []


def record(label, ok, detail=""):
    CASES.append((label, ok, detail))


def run():
    # foreign-prepared read by the attributed (bracketing) speaker → accepted
    iss = _issues(_q("[3:00]", "s2"))
    record("foreign-prepared by attributed speaker → accepted (silent)",
           not iss, repr([i.message for i in iss]))

    # foreign-recitation read by the attributed (bracketing) speaker → accepted
    iss = _issues(_q("[11:00]", "s2"))
    record("foreign-recitation by attributed speaker → accepted (silent)",
           not iss, repr([i.message for i in iss]))

    # foreign-prepared unambiguously bracketed by s2, attributed to s1 → ERROR
    iss = _issues(_q("[3:00]", "s1"))
    record("foreign-prepared by a DIFFERENT single bracketing speaker → error",
           len(iss) == 1 and iss[0].level == "error",
           repr([(i.level, i.message) for i in iss]))

    # foreign-prepared at a hand-off (s2 before, s1 after) → ambiguous → accepted
    iss = _issues(_q("[3:00]", "s2", path="transcripts/test-b.md"))
    record("foreign-prepared at a hand-off (ambiguous brackets) → accepted",
           not iss, repr([i.message for i in iss]))
    iss = _issues(_q("[3:00]", "s1", path="transcripts/test-b.md"))
    record("ambiguous-bracket span trusts declared speaker_id (no error)",
           not iss, repr([i.message for i in iss]))

    # non-speaker foreign turn (music) → WARN, never error
    iss = _issues(_q("[18:21]", "s2"))
    record("non-speaker foreign turn (music) → warn",
           len(iss) == 1 and iss[0].level == "warn"
           and "non-speaker foreign turn" in iss[0].message,
           repr([(i.level, i.message) for i in iss]))

    # live-vs-live: correct attribution → clean (mid-turn, clear of boundary slop)
    iss = _issues(_q("[16:50]", "s1"))
    record("live match → no issue", not iss, repr([i.message for i in iss]))

    # live-vs-live: wrong attribution → ERROR (unchanged behavior)
    iss = _issues(_q("[16:50]", "s2"))
    record("live mismatch → error",
           len(iss) == 1 and iss[0].level == "error",
           repr([(i.level, i.message) for i in iss]))


def main():
    print("=" * 70)
    print(" speaker-attribution consistency regression test")
    print("=" * 70)
    print()
    orig = sac._load_siblings
    sac._load_siblings = lambda: _SIBLINGS
    try:
        run()
    finally:
        sac._load_siblings = orig
    failures = [(label, detail) for label, ok, detail in CASES if not ok]
    if failures:
        print(f"  FAILED — {len(failures)}/{len(CASES)} case(s):")
        for label, detail in failures:
            print(f"    - {label}  {detail}")
        return 1
    print(f"  PASSED — {len(CASES)} cases "
          "(foreign-prepared/recitation accepted; contradiction + live mismatch error; "
          "non-speaker foreign warn)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
