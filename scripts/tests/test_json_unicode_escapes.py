#!/usr/bin/env python3
"""Regression guard for JSON ``\\uXXXX`` decoding in the shared source reader
(`decode_json_unicode_escapes` + the .json branch of `extract_source_text`,
`scripts/lib/_common.py`).

Gson-serialized payloads (e.g. an ADP job-requisition API record) store "&"
as ``\\u0026``, so an HTML "&amp;" inside a JSON string is the ten bytes
``\\u0026amp;`` — text no quote can reproduce. The contract:
  - ``\\uXXXX`` decodes (``\\u0026amp;`` → "&amp;", then the verbatim
    normalizer's html.unescape → "&");
  - a surrogate pair decodes to its single code point; a lone surrogate
    stays literal;
  - an escaped backslash before "u" (``\\\\u0026``) is NOT an escape and
    stays literal;
  - no other JSON escape (``\\"`` ``\\\\`` ``\\n``) and no JSON syntax is
    touched, so a quote that carries raw ``"key":"value"`` syntax still
    matches;
  - .txt sources are read raw (no decoding).

Uses real temp files so the actual `extract_source_text` branch and the
`verbatim_quotes` check run (no mock of the mechanism under test);
monkeypatches only `SOURCES_DIR` and `manifest_format`.
"""

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from checks import verbatim_quotes as vq
from lib._common import decode_json_unicode_escapes as dec

BS = "\\"

CASES = []


def record(label, ok, detail=""):
    CASES.append((label, ok, detail))


class _Ctx:
    rel = "test"

    def __init__(self, quotes):
        self.data = {"quotes": quotes}


def _issues(rel_path, text, sources_dir):
    orig_dir, orig_fmt = vq.SOURCES_DIR, vq.manifest_format
    vq.SOURCES_DIR = sources_dir
    vq.manifest_format = lambda rel: "txt"
    try:
        q = {"id": "q1", "text": text, "source": {"path": rel_path}}
        return list(vq.check(_Ctx([q])))
    finally:
        vq.SOURCES_DIR, vq.manifest_format = orig_dir, orig_fmt


def unit_cases():
    amp = f"Test {BS}u0026amp; Evaluation"
    record("\\u0026amp; decodes to &amp;", dec(amp) == "Test &amp; Evaluation", repr(dec(amp)))

    pair = f"x {BS}ud83d{BS}ude00 y"
    record("surrogate pair decodes to one code point",
           dec(pair) == "x \U0001F600 y", repr(dec(pair)))

    lone = f"a {BS}ud83d b {BS}ude00"
    record("lone surrogates stay literal", dec(lone) == lone, repr(dec(lone)))

    esc_bs = f"path {BS}{BS}u0026 end"
    record("escaped backslash before u stays literal", dec(esc_bs) == esc_bs, repr(dec(esc_bs)))

    odd = f"{BS}{BS}{BS}u0026"
    record("escaped backslash + live escape → backslash pair kept, escape decoded",
           dec(odd) == f"{BS}{BS}&", repr(dec(odd)))

    others = f'"k":"a{BS}"b{BS}{BS}c{BS}nd{BS}/e"'
    record("other JSON escapes and syntax untouched", dec(others) == others, repr(dec(others)))

    record("uppercase hex decodes", dec(f"{BS}u003C") == "<", repr(dec(f"{BS}u003C")))


def reader_cases(tmp):
    news = tmp / "news"
    news.mkdir()
    payload = ('{"requisitionTitle":"Field Operations ' + BS + 'u0026 Sensor",'
               '"requisitionDescription":"' + BS + 'u003cp' + BS + 'u003eResearch, '
               'Development, Test ' + BS + 'u0026amp; Evaluation Activities within '
               '(OUSW(I' + BS + 'u0026amp;S)) All-Domain Anomaly Resolution Office '
               '(AARO).' + BS + 'u003c/p' + BS + 'u003e"}')
    (news / "req.json").write_text(payload, encoding="utf-8")
    (news / "req.txt").write_text(payload, encoding="utf-8")

    sentence = ("Research, Development, Test & Evaluation Activities within "
                "(OUSW(I&S)) All-Domain Anomaly Resolution Office (AARO).")
    iss = _issues("news/req.json", sentence, tmp)
    record(".json: quote across decoded \\u0026amp; matches", not iss,
           repr([(i.level, i.message) for i in iss]))

    raw_syntax = '"requisitionTitle":"Field Operations & Sensor"'
    iss = _issues("news/req.json", raw_syntax, tmp)
    record(".json: quote carrying raw \"key\":\"value\" syntax still matches", not iss,
           repr([(i.level, i.message) for i in iss]))

    iss = _issues("news/req.json", "Test & Evaluation Activities within the Pentagon", tmp)
    record(".json: non-matching quote still errors",
           len(iss) == 1 and iss[0].level == "error", repr([(i.level, i.message) for i in iss]))

    iss = _issues("news/req.txt", sentence, tmp)
    record(".txt: read raw (escapes not decoded) → decoded quote errors",
           len(iss) == 1 and iss[0].level == "error", repr([(i.level, i.message) for i in iss]))


def main():
    print("=" * 70)
    print(" JSON \\uXXXX source-reader decoding regression test")
    print("=" * 70)
    print()
    unit_cases()
    with tempfile.TemporaryDirectory() as d:
        reader_cases(Path(d))
    failures = [(label, detail) for label, ok, detail in CASES if not ok]
    if failures:
        print(f"  FAILED — {len(failures)}/{len(CASES)} case(s):")
        for label, detail in failures:
            print(f"    - {label}  {detail}")
        return 1
    print(f"  PASSED — {len(CASES)} cases "
          "(\\u0026amp; decoded; surrogate pair; escaped backslash literal; .txt raw)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
