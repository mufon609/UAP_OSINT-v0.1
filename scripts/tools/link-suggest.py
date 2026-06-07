#!/usr/bin/env python3
"""Cross-reference link-coverage aid for a research artifact.

Read-only diagnostic — the heuristic complement to the mechanical
``prose_entity_link`` validator check. The universal-stub rule (see
``meta/conventions.md`` "## Associated Nodes") requires every entity a
node names **in its own authored prose** to carry a ``[`/{type}/{slug}`]``
stub so it reaches the ``## Associated Nodes`` index. The validator check
enforces that for entities that ALREADY have a node (people /
organizations — a closed, mechanically-matchable set). This tool covers
the other direction: capitalized names in the authored prose that are NOT
yet wrapped and likely have **no node yet** — the physicist cited by
surname, the program named once, the official mentioned in passing. Those
are the stub-candidates the closed-set check cannot see.

What it does, per artifact:

  1. Pools the **authored-prose** fields — ``description``,
     ``background``, ``top_relevance``, ``credibility_notes``,
     ``pattern_statement``, each ``quote.significance``, each
     ``timeline[].event``, and per-entry ``.attestation`` / ``.note``
     synthesis fields. It deliberately EXCLUDES verbatim ``quote.text``:
     a source's own words are never wrapped (they stay source-faithful),
     so a name appearing only inside a quote is not a stub candidate here.

  2. Subtracts what is already linked. Every ``[`/path`]`` wrap in the
     artifact contributes its slug words (``/people/gary-stephenson`` ->
     ``gary``, ``stephenson``); a capitalized prose token whose lowercase
     is one of those words is already carried navigationally and is
     dropped. The target node's own slug words are dropped too (a node
     naming its own subject is not a cross-reference).

  3. Surfaces the remaining capitalized tokens — the names the prose
     introduces but does not link. The contributor judges each: a real
     entity (person / org / program / place) -> wrap it with its
     canonical ``[`/{type}/{slug}`]`` stub (the node need not exist yet —
     the stub joins the Priority Build Queue); boilerplate / a generic
     term / a sentence-initial word -> ignore.

Usage:
    link-suggest.py meta/research/{slug}.yaml

Options:
    --top-token-count N   Show top N unwrapped capitalized tokens
                          (default: 40; pass 0 for all)

Exit codes:
    0  — diagnostic ran (regardless of how many candidates surfaced)
    1  — real error: artifact missing / unreadable / not a dict
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

# scripts/tools/link-suggest.py — put scripts/ on sys.path so
# `from lib._common` resolves from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import (  # noqa: E402
    REPO_ROOT,
    STOPWORDS,
    strict_yaml_load,
)

# Backtick-bracketed canonical path — same grammar associate.py reads.
_LINK_RE = re.compile(r"\[`(/[^`]+)`\]")

# The capitalized name phrase that sits immediately before a wrap IS the
# entity's spelled-out form — "Defense Intelligence Agency ([`/.../dia`])",
# "the Laser Interferometer Gravitational Observatory, or LIGO
# ([`/.../ligo`])". Its words are already carried navigationally even when
# the slug is an acronym (dia) or the target node is an unbuilt stub, so we
# fold them into the covered set. Captures a run of Capitalized tokens
# joined by lowercase connectors (of/the/for/and/&/de/von/van) or commas,
# terminating at an optional "(" then the wrap.
_NAME_BEFORE_WRAP_RE = re.compile(
    r"((?:[A-Z][A-Za-z0-9'’.\-]*)"
    r"(?:(?:[ \t]+(?:of|the|for|and|de|von|van|or)\b|,)?[ \t]+"
    r"[A-Z][A-Za-z0-9'’.\-]*)*)"
    r"[ \t]*\(?[ \t]*\[`/[^`]+`\]"
)

# Capitalized-token regex — shared shape with coverage-suggest.py: a word
# starting uppercase + lowercase, 3+ chars, intra-word apostrophe/hyphen
# allowed. Skips all-caps acronyms and short function words.
_CAP_TOKEN_RE = re.compile(r"\b[A-Z][a-z][a-zA-Z\-']{1,}\b")

# Trailing possessive — "Elizondo's" / "Elizondo’s" → "Elizondo" before the
# covered/noise test, so a wrapped entity's possessive form isn't re-flagged.
_POSSESSIVE_RE = re.compile(r"['’]s$")

# Title-case navigation / boilerplate noise. The months/days + generic-noun
# template words (DIRD cover pages, hearing boilerplate, synthesis scaffold)
# that recur capitalized but are never a standalone entity. Spelled-out
# ORG-name fragments (Defense / Intelligence / Agency …) are handled
# structurally by _NAME_BEFORE_WRAP_RE, not here — so a genuinely unwrapped
# org still surfaces.
_NAV_NOISE = frozenset({
    "About", "All", "Also", "April", "August",
    "December", "February", "Friday",
    "January", "July", "June",
    "March", "May", "Monday", "November",
    "October", "Other", "Saturday", "September", "Sunday",
    "The", "These", "This", "Thursday", "Tuesday", "Wednesday",
    # Generic template / synthesis-scaffold nouns
    "Administrative", "Appendix", "Application", "Applications",
    "Author", "Board", "Bracketed", "Command", "Committee", "Core",
    "Council", "Department", "Director", "Document", "Documents",
    "Establishes", "Group", "Headline", "Manager", "Note", "Office",
    "Operations", "Per", "Prepared", "Program", "Project", "Provenance",
    "Quantitative", "Record", "Reference", "Report", "Scientist",
    "Section", "Secretary", "Service", "Services", "Statement",
    "Subcommittee", "Summary", "Support", "System",
    # Template adjectives / scaffold descriptors (never a standalone entity)
    "Advanced", "Anomalous", "Approach", "Beyond", "Central",
    "First", "Foundational", "Frames", "New", "Opening", "Operative",
    "Public", "Series", "Special", "Standard", "Theoretical",
    "Thesis", "Unidentified", "Utilizing",
})


def _add(parts, val):
    if isinstance(val, str):
        parts.append(val)


def collect_authored_prose(data):
    """Pool the artifact's authored-prose surfaces — everything the repo
    writes in its own voice. Verbatim ``quote.text`` is excluded by
    design."""
    parts = []
    for key in ("description", "background", "top_relevance",
                "credibility_notes", "pattern_statement"):
        _add(parts, data.get(key))

    for q in data.get("quotes") or []:
        if isinstance(q, dict):
            _add(parts, q.get("significance"))   # authored; NOT q['text']

    for t in data.get("timeline") or []:
        if isinstance(t, dict):
            _add(parts, t.get("event"))

    # Per-entry synthesis fields across every structured entry list — the
    # `.attestation` / `.note` the repo authors. Walk generically so new
    # entry shapes are covered without enumeration; skip `text` keys
    # (verbatim) wherever they appear.
    _walk_synthesis(data, parts)
    return " ".join(parts)


def _walk_synthesis(node, parts, _key=None):
    """Recursively collect ``attestation`` / ``note`` string fields from
    nested entry lists/dicts. Verbatim ``text`` is never collected."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("attestation", "note") and isinstance(v, str):
                parts.append(v)
            elif k != "text":
                _walk_synthesis(v, parts, k)
    elif isinstance(node, list):
        for v in node:
            _walk_synthesis(v, parts, _key)


def _slug_words(path):
    """Lowercase word set from a canonical path's final slug segment:
    ``/people/gary-stephenson`` -> {'gary', 'stephenson'}."""
    slug = path.rstrip("/").rsplit("/", 1)[-1]
    return {w for w in re.split(r"[-_]", slug) if w}


def linked_words(data, blob):
    """All words already carried navigationally — the 'already covered' set
    the candidate tokens are filtered against. Three sources:

      1. Slug words of every ``[`/path`]`` wrap (``gary-stephenson`` ->
         {gary, stephenson}).
      2. The spelled-out name phrase immediately before each wrap
         (``Defense Intelligence Agency ([`/.../dia`])`` -> {defense,
         intelligence, agency}) — covers acronym slugs and stub targets.
      3. The target node's own slug (a node naming its own subject is not a
         cross-reference).
    """
    words = set()
    for path in _LINK_RE.findall(blob):
        words |= _slug_words(path)
    for phrase in _NAME_BEFORE_WRAP_RE.findall(blob):
        for w in re.split(r"[\s,]+", phrase):
            w = w.strip(".'’-")
            if w:
                words.add(w.lower())
    target = data.get("target_node")
    if isinstance(target, str):
        words |= _slug_words(target)
    return words


def candidate_tokens(blob, covered):
    """Capitalized prose tokens not already covered by a wrap. Returns a
    Counter keyed by token (original casing)."""
    out = Counter()
    for raw in _CAP_TOKEN_RE.findall(blob or ""):
        tok = _POSSESSIVE_RE.sub("", raw)   # "Elizondo's" -> "Elizondo"
        if not tok or tok in _NAV_NOISE or tok.lower() in STOPWORDS:
            continue
        if tok.lower() in covered:
            continue
        out[tok] += 1
    return out


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Cross-reference link-coverage aid — surface capitalized names "
            "in a research artifact's authored prose that are not yet "
            "wrapped as [`/path`] stubs. Read-only; heuristic complement to "
            "the prose_entity_link validator check."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  link-suggest.py meta/research/{slug}.yaml\n",
    )
    ap.add_argument("artifact_path", help="Path to meta/research/{slug}.yaml")
    ap.add_argument("--top-token-count", type=int, default=40,
                    help="Show top N unwrapped capitalized tokens "
                         "(default 40; 0 = all)")
    args = ap.parse_args()

    artifact_path = Path(args.artifact_path).resolve()
    if not artifact_path.exists():
        sys.exit(f"ERROR: artifact not found: {artifact_path}")

    with artifact_path.open() as f:
        data = strict_yaml_load(f) or {}
    if not isinstance(data, dict):
        sys.exit(f"ERROR: artifact is not a YAML mapping: {artifact_path}")

    # Wraps can live anywhere in the file, not only the prose blob; read the
    # whole text for the 'already linked' word set.
    full_text = artifact_path.read_text()
    blob = collect_authored_prose(data)
    covered = linked_words(data, full_text)
    candidates = candidate_tokens(blob, covered)

    rel = (artifact_path.relative_to(REPO_ROOT)
           if REPO_ROOT in artifact_path.parents else artifact_path)
    print(f"Link-suggest report for {rel}")
    print()

    if not candidates:
        print("  ✓ No unwrapped capitalized names in authored prose.")
        return 0

    items = candidates.most_common()
    shown = items if args.top_token_count == 0 else items[:args.top_token_count]
    print(f"  Unwrapped capitalized names in authored prose "
          f"({len(candidates)} distinct):")
    for tok, cnt in shown:
        print(f"    {tok}  ({cnt}x)")
    if len(items) > len(shown):
        print(f"    … (+{len(items) - len(shown)} more; "
              f"--top-token-count 0 for all)")
    print()
    print("Read-only. Judge each: a real entity (person / org / program / "
          "place)")
    print("→ wrap it [`/{type}/{slug}`] (stub is fine — node need not exist "
          "yet);")
    print("boilerplate / generic term / sentence-initial word → ignore.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
