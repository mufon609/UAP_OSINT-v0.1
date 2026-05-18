#!/usr/bin/env python3
"""normalize-locations.py — diagnostic for quote source.location refs.

Surveys the corpus for location refs that depend on extraction-version
line numbers (``lines N-M`` and ``line N`` forms), and for each such
quote reports where the quote text actually lives in the current source
extract. Contributors use the report to convert refs to canonical forms
(``p. N, ¶M``, ``¶N``, ``[MM:SS]``, ``p. N``) per ``meta/conventions.md``
"Quote location refs: source-anchored, not extraction-anchored".

Read-only — does not modify any artifact. The boundary-inclusion class
(contributor-authored ranges that include adjoining material) requires a
per-source read against the underlying document; this tool surfaces the
actual line range where the quote text lives in the current extract so
that verification is fast.

Usage:
  scripts/tools/normalize-locations.py                # corpus-wide survey
  scripts/tools/normalize-locations.py PATH           # per-artifact diagnostic
  scripts/tools/normalize-locations.py --all          # include canonical refs
  scripts/tools/normalize-locations.py --csv [PATH]   # machine-readable
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import yaml

# scripts/tools/normalize-locations.py — put the scripts/ parent on
# sys.path so `from lib._common` resolves from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import (
    strict_yaml_load,
    REPO_ROOT,
    SOURCES_DIR,
    extract_source_text,
    manifest_format,
)

RESEARCH_DIR = REPO_ROOT / "meta" / "research"


# --- Location-form classification -------------------------------------------

# Deprecated: pure line-number refs that depend on which extractor
# produced the bytes the contributor was reading.
RE_LINES_RANGE = re.compile(r"^\s*lines\s+\d+\s*-\s*\d+\s*$", re.IGNORECASE)
RE_LINE_SINGLE = re.compile(r"^\s*lines?\s+\d+\s*$", re.IGNORECASE)

# Canonical-form indicators (any one of these makes the ref acceptable).
RE_PAGE = re.compile(r"\bp\.?\s*\d+", re.IGNORECASE)
RE_PARA = re.compile(r"¶\s*\d+")
RE_TIMESTAMP = re.compile(r"\[\d+:\d+(?::\d+)?\]")
RE_OF_THE_EXTRACT = re.compile(r"\bof\s+the\s+extract\b", re.IGNORECASE)


def classify_location(loc: str) -> str:
    """Return one of: 'deprecated', 'canonical', 'other'."""
    s = (loc or "").strip()
    if not s:
        return "other"
    if RE_OF_THE_EXTRACT.search(s):
        return "canonical"
    if RE_LINES_RANGE.match(s) or RE_LINE_SINGLE.match(s):
        return "deprecated"
    if RE_PAGE.search(s) or RE_PARA.search(s) or RE_TIMESTAMP.search(s):
        return "canonical"
    return "other"


# --- Quote-to-source line mapping -------------------------------------------

def _light_normalize(t: str) -> str:
    """Whitespace-preserving normalization. Smart quotes / dashes / NBSP only.
    Line counts in the result equal line counts in the input."""
    return (
        t.replace("“", '"').replace("”", '"')
         .replace("‘", "'").replace("’", "'")
         .replace("—", "-").replace("–", "-")
         .replace(" ", " ")
    )


def find_quote_lines(quote_text: str, source_text: str):
    """Return (start_line, end_line) for the quote's location in source.
    Lines are 1-indexed. Returns None if the quote text cannot be located.
    """
    if not quote_text or not source_text:
        return None
    qt = re.sub(r"^\[\d+:\d+(?::\d+)?\]\s*", "", quote_text.strip())
    qt = re.sub(r"(?m)^>\s?", "", qt).strip()
    if not qt:
        return None
    qt = _light_normalize(qt)
    src = _light_normalize(source_text)

    def regex_for(s: str) -> str:
        # Build a whitespace-tolerant pattern by splitting on whitespace
        # and rejoining with `\s+`. Avoids re.escape's whitespace-handling
        # surprises (Python 3.13 escapes spaces; older versions don't).
        words = s.split()
        if not words:
            return None
        return r"\s+".join(re.escape(w) for w in words)

    anchor = qt[: min(80, len(qt))].strip()
    pat = regex_for(anchor)
    m = re.search(pat, src) if pat else None
    if not m and len(qt) > 30:
        anchor = qt[:30].strip()
        pat = regex_for(anchor)
        m = re.search(pat, src) if pat else None
    if not m:
        return None

    start_idx = m.start()
    start_line = src.count("\n", 0, start_idx) + 1

    end_anchor = qt[-min(80, len(qt)):].strip()
    end_pat = regex_for(end_anchor)
    em = re.search(end_pat, src[start_idx:]) if end_pat else None
    if em:
        end_idx = start_idx + em.end()
        end_line = src.count("\n", 0, end_idx) + 1
    else:
        end_line = start_line + qt.count("\n")

    return start_line, end_line


# --- Canonical-form proposal ------------------------------------------------

def _line_to_char(text: str, line_no: int) -> int:
    if line_no <= 1:
        return 0
    n = 0
    for i, ch in enumerate(text):
        if ch == "\n":
            n += 1
            if n == line_no - 1:
                return i + 1
    return len(text)


def propose_canonical(source_path: Path, source_text: str, start_line: int, end_line: int):
    """Return (proposed_form, needs_verification, note).

    proposed_form: a string the contributor can verify and apply, OR None
        if the source shape requires manual computation against the
        rendered source.
    needs_verification: True when the contributor must verify the proposal
        against the rendered source page (most cases). Only False when the
        proposal is fully mechanical (caption [MM:SS]).
    note: one-line hint describing why no proposal / what to check.
    """
    suffix = source_path.suffix.lower()
    try:
        rel_path = str(source_path.relative_to(SOURCES_DIR))
    except ValueError:
        rel_path = None
    fmt = manifest_format(rel_path) if rel_path else None

    is_caption = (
        source_path.name.endswith("-downloaded.md")
        or source_path.name.endswith("-downloaded.json")
        or fmt == "transcript"
    )
    if is_caption:
        lines = source_text.splitlines()
        si = max(0, min(start_line - 1, len(lines) - 1))
        ei = max(0, min(end_line - 1, len(lines) - 1))
        # Leading [MM:SS]: the closest marker at or before start_line.
        first_ts = None
        for i in range(si, -1, -1):
            m = RE_TIMESTAMP.search(lines[i])
            if m:
                first_ts = m.group(0)
                break
        # Trailing [MM:SS]: the last marker at or before end_line.
        last_ts = None
        for i in range(ei, -1, -1):
            m = RE_TIMESTAMP.search(lines[i])
            if m:
                last_ts = m.group(0)
                break
        if first_ts and last_ts and first_ts != last_ts:
            return f"{first_ts}–{last_ts}", False, "caption transcript — mechanical"
        if first_ts:
            return first_ts, False, "caption transcript — mechanical"
        return None, True, "caption transcript — no nearby [MM:SS] marker"

    if suffix == ".pdf" or fmt == "pdf":
        if "\f" in source_text:
            char_idx = _line_to_char(source_text, start_line)
            page = source_text.count("\f", 0, char_idx) + 1
            return (
                f"p. {page}*",
                True,
                "extract-derived page; verify against rendered PDF "
                "(government page numbers may differ from extract page index)",
            )
        return None, True, "PDF without form-feed page markers (likely .txt sibling) — count paragraphs against rendered PDF"

    if suffix in (".html", ".htm") or fmt == "html":
        return None, True, "HTML — count ¶ in rendered article"

    if suffix in (".txt", ".md"):
        return None, True, "text source — verify line / paragraph against rendered original"

    return None, True, f"unrecognized source shape ({suffix or fmt or 'unknown'})"


# --- Artifact walking -------------------------------------------------------

def iter_artifacts(target):
    if target is None:
        for p in sorted(RESEARCH_DIR.glob("*.yaml")):
            yield p
    else:
        p = Path(target)
        if not p.is_absolute():
            # Try as-given, then relative to repo root
            if not p.exists():
                p = REPO_ROOT / target
        if p.is_dir():
            for q in sorted(p.glob("*.yaml")):
                yield q
        elif p.exists():
            yield p
        else:
            print(f"error: {target}: not found", file=sys.stderr)
            sys.exit(2)


def walk_artifact(artifact_path: Path, include_canonical: bool):
    """Yield diagnostic rows for an artifact's quotes."""
    try:
        with open(artifact_path) as f:
            data = strict_yaml_load(f)
    except Exception as e:
        print(f"warning: {artifact_path}: parse failed ({e})", file=sys.stderr)
        return
    if not isinstance(data, dict):
        return
    quotes = data.get("quotes") or []
    for q in quotes:
        if not isinstance(q, dict):
            continue
        src = q.get("source")
        if not isinstance(src, dict):
            continue
        loc = src.get("location") or ""
        klass = classify_location(loc)
        if klass == "canonical" and not include_canonical:
            continue

        src_path_str = src.get("path") or ""
        src_path = SOURCES_DIR / src_path_str
        actual = (None, None, None)  # start, end, line_count
        proposal = (None, True, "")
        if klass == "deprecated" and src_path.exists():
            extract = extract_source_text(src_path)
            if extract:
                lines = find_quote_lines(q.get("text") or "", extract)
                if lines:
                    s, e = lines
                    actual = (s, e, e - s + 1)
                    proposal = propose_canonical(src_path, extract, s, e)

        # Compare contributor's stated lines to actual
        boundary_delta = ""
        if klass == "deprecated" and actual[0] is not None:
            m = re.match(r"^\s*lines?\s+(\d+)(?:\s*-\s*(\d+))?\s*$", loc, re.IGNORECASE)
            if m:
                stated_n = int(m.group(1))
                stated_m = int(m.group(2)) if m.group(2) else stated_n
                actual_n, actual_m, _ = actual
                delta_start = actual_n - stated_n
                delta_end = actual_m - stated_m
                if delta_start != 0 or delta_end != 0:
                    boundary_delta = f"stated [{stated_n}-{stated_m}] vs actual [{actual_n}-{actual_m}]"
                else:
                    boundary_delta = "match"

        yield {
            "artifact": artifact_path.name,
            "quote_id": q.get("id") or "",
            "source_path": src_path_str,
            "current": loc,
            "class": klass,
            "actual_start": actual[0] or "",
            "actual_end": actual[1] or "",
            "actual_lines": actual[2] or "",
            "boundary": boundary_delta,
            "proposed": proposal[0] or "",
            "proposal_note": proposal[2] or "",
            "needs_verification": proposal[1],
        }


# --- Output -----------------------------------------------------------------

def render_text(rows, summary_only=False):
    by_artifact = {}
    klass_totals = {"deprecated": 0, "canonical": 0, "other": 0}
    for r in rows:
        by_artifact.setdefault(r["artifact"], []).append(r)
        klass_totals[r["class"]] = klass_totals.get(r["class"], 0) + 1

    print("=" * 72)
    print(" Quote location-ref diagnostic")
    print("=" * 72)
    print()
    print("  Class totals (quotes scanned this run):")
    for k in ("deprecated", "other", "canonical"):
        print(f"    {klass_totals.get(k, 0):4d}  {k}")
    print()
    print(f"  Artifacts with rows reported: {len(by_artifact)}")
    print()

    if summary_only:
        return

    for a in sorted(by_artifact):
        artifact_rows = by_artifact[a]
        depr = sum(1 for r in artifact_rows if r["class"] == "deprecated")
        if depr == 0 and not any(r["class"] == "other" for r in artifact_rows):
            continue
        print("-" * 72)
        print(f"  {a}  ({depr} deprecated)")
        print("-" * 72)
        for r in artifact_rows:
            if r["class"] != "deprecated":
                continue
            print(f"    {r['quote_id']:>6s}  source: {r['source_path']}")
            print(f"            current:    {r['current']}")
            if r["actual_start"] != "":
                print(
                    f"            actual:     lines {r['actual_start']}-{r['actual_end']} "
                    f"({r['actual_lines']} line(s))"
                )
                if r["boundary"] and r["boundary"] != "match":
                    print(f"            boundary:   {r['boundary']}")
            else:
                print("            actual:     <quote text not located in current extract>")
            if r["proposed"]:
                tag = "" if not r["needs_verification"] else "  [verify]"
                print(f"            proposed:   {r['proposed']}{tag}")
            if r["proposal_note"]:
                print(f"            note:       {r['proposal_note']}")
            print()


def render_csv(rows):
    fieldnames = [
        "artifact", "quote_id", "source_path", "current", "class",
        "actual_start", "actual_end", "actual_lines",
        "boundary", "proposed", "proposal_note", "needs_verification",
    ]
    w = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(r)


# --- Main -------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(
        description="Diagnostic for extraction-version-dependent quote source.location refs",
    )
    p.add_argument("path", nargs="?", default=None,
                   help="research artifact YAML or directory (default: all of meta/research/)")
    p.add_argument("--all", action="store_true",
                   help="include canonical-form quotes in output (default: only deprecated/other)")
    p.add_argument("--csv", action="store_true",
                   help="emit machine-readable CSV instead of text")
    p.add_argument("--summary", action="store_true",
                   help="emit class totals only, no per-quote details")
    args = p.parse_args(argv)

    rows = []
    for artifact in iter_artifacts(args.path):
        for row in walk_artifact(artifact, include_canonical=args.all):
            rows.append(row)

    if args.csv:
        render_csv(rows)
    else:
        render_text(rows, summary_only=args.summary)


if __name__ == "__main__":
    main()
