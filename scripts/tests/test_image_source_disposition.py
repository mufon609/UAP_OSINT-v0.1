#!/usr/bin/env python3
"""Regression guard for how `verbatim_quotes` disposes of image sources
(`scripts/checks/verbatim_quotes.py`) and the image branch of
`extract_source_text` (`scripts/lib/_common.py`).

An archived image carries no text layer. The contract:
  - image source WITHOUT a committed `.txt` sibling → the quote is ACCEPTED
    as a non-text reference (the archived image IS the reference; the `image`
    format tag labels it). No permanent, unclearable warning.
  - image source WITH a committed same-stem `.txt` sibling (a verified
    transcription — the route a book delivered as page images takes) → the
    quote is VERIFIED against the sibling: matches → clean, mismatches → error.
    Books earn real verification, not acceptance on faith.
  - video / audio (also binary) → still WARN: quote them via a companion
    transcript, not the binary directly.

Uses real temp files so the actual `extract_source_text` image branch runs
(no mock of the mechanism under test); monkeypatches only `SOURCES_DIR` and
`manifest_format` so no corpus file is required.
"""

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from checks import verbatim_quotes as vq

_FMT_BY_SUFFIX = {".jpeg": "image", ".jpg": "image", ".mp4": "video"}


class _Ctx:
    rel = "test"

    def __init__(self, quotes):
        self.data = {"quotes": quotes}


def _q(rel_path, text):
    return {"id": "q1", "text": text, "source": {"path": rel_path}}


def _issues(rel_path, text, sources_dir):
    orig_dir, orig_fmt = vq.SOURCES_DIR, vq.manifest_format
    vq.SOURCES_DIR = sources_dir
    vq.manifest_format = lambda rel: _FMT_BY_SUFFIX.get(Path(rel).suffix.lower())
    try:
        return list(vq.check(_Ctx([_q(rel_path, text)])))
    finally:
        vq.SOURCES_DIR, vq.manifest_format = orig_dir, orig_fmt


CASES = []


def record(label, ok, detail=""):
    CASES.append((label, ok, detail))


def run(tmp):
    sub = tmp / "social"
    sub.mkdir()
    quote = "Advisory Board Member Battelle Jul 2016 - Apr 2018"

    # image, NO sibling → accepted (no issue)
    (sub / "no-sibling.jpeg").write_bytes(b"\xff\xd8\xff")  # token JPEG bytes
    iss = _issues("social/no-sibling.jpeg", quote, tmp)
    record("image without sibling → accepted (no warn)",
           not iss, repr([(i.level, i.message) for i in iss]))

    # image WITH sibling containing the quote → verified clean (book route)
    (sub / "with-sibling.jpeg").write_bytes(b"\xff\xd8\xff")
    (sub / "with-sibling.txt").write_text(
        "Experience\n" + quote + "\nmore text", encoding="utf-8")
    iss = _issues("social/with-sibling.jpeg", quote, tmp)
    record("image with sibling containing quote → verified clean",
           not iss, repr([(i.level, i.message) for i in iss]))

    # image WITH sibling that does NOT contain the quote → error (mismatch caught)
    (sub / "bad-sibling.jpeg").write_bytes(b"\xff\xd8\xff")
    (sub / "bad-sibling.txt").write_text(
        "totally unrelated transcription text", encoding="utf-8")
    iss = _issues("social/bad-sibling.jpeg", quote, tmp)
    record("image with sibling missing the quote → error (NOT FOUND)",
           len(iss) == 1 and iss[0].level == "error" and "NOT FOUND" in iss[0].message,
           repr([(i.level, i.message) for i in iss]))

    # video, no sibling → still warns (unchanged)
    (tmp / "video").mkdir()
    (tmp / "video" / "clip.mp4").write_bytes(b"\x00\x00\x00")
    iss = _issues("video/clip.mp4", quote, tmp)
    record("video without sibling → warn (unchanged)",
           len(iss) == 1 and iss[0].level == "warn",
           repr([(i.level, i.message) for i in iss]))


def main():
    print("=" * 70)
    print(" image-source disposition regression test")
    print("=" * 70)
    print()
    with tempfile.TemporaryDirectory() as d:
        run(Path(d))
    failures = [(label, detail) for label, ok, detail in CASES if not ok]
    if failures:
        print(f"  FAILED — {len(failures)}/{len(CASES)} case(s):")
        for label, detail in failures:
            print(f"    - {label}  {detail}")
        return 1
    print(f"  PASSED — {len(CASES)} cases "
          "(image accepted w/o sibling; verified w/ sibling; video still warns)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
