#!/usr/bin/env python3
"""Source-coverage audit aid for a research artifact.

Read-only diagnostic. For each primary source on a research artifact,
surfaces two kinds of audit candidates the mechanical validators
cannot catch:

  1. **Unreferenced source paragraphs** — paragraphs of substantive
     length in the extracted source that no `quotes[].text` matches.
     The forward-direction complement of the verbatim-quote check:
     verbatim-quote confirms that every quote IS in the source;
     coverage-suggest surfaces what's IN the source that no quote
     references. Likely under-extraction candidates.

  2. **Unregistered capitalized tokens** — proper-noun-style
     capitalized terms that appear in the source but nowhere in the
     artifact's text fields (quotes, entries, prose). Likely missed
     entities (people, organizations, documents the source names).

Contributor judges each candidate manually — the tool surfaces
audit targets, never asserts they're under-extraction. Boilerplate,
navigation noise, and tangential content (a hearing transcript names
50 topics; a witness's person node only quotes 5) are legitimately
unreferenced.

Usage:
    coverage-suggest.py meta/research/{slug}.yaml

Options:
    --min-paragraph-chars N   Skip paragraphs shorter than N chars
                              (default: 80; raises signal on
                              boilerplate / nav-noise paragraphs)
    --top-token-count N       Show top N unregistered capitalized
                              tokens per source (default: 15)
    --max-paragraph-preview N Preview length per unreferenced
                              paragraph (default: 140 chars)

Exit codes:
    0  — diagnostic ran successfully (regardless of how many
         candidates were surfaced)
    1  — real error: artifact missing, artifact has no primary_sources,
         or every primary source failed extraction
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml  # noqa: F401  (kept for ImportError guidance)

# scripts/tools/coverage-suggest.py — put the scripts/ parent on sys.path
# so `from lib._common` resolves from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import (  # noqa: E402
    REPO_ROOT,
    SOURCES_DIR,
    STOPWORDS,
    extract_source_text,
    normalize_for_compare,
    strict_yaml_load,
)


# Capitalized-token gap heuristic — boilerplate terms that show up in
# many web sources and HTML wrappers. Filtering these reduces noise so
# the contributor's attention lands on actual named entities. The list
# stays small intentionally; any term flagged in real audit output that
# turns out to be boilerplate can be appended. Distinct from the
# tokenizer STOPWORDS in lib/_common.py — those are lowercase function-
# word filters used for prose-drift; this is title-case nav-noise.
NAV_NOISE = frozenset({
    "About", "Account", "Accept", "Advanced", "All", "Amazon",
    "Article", "Articles",
    "Back", "Banner", "Blog", "Buy",
    "Cite", "Citation", "Citations", "Click", "Close", "Contact",
    "Cookie", "Cookies", "Copy", "Copyright",
    "Click",
    "Email", "English",
    "Facebook", "Find", "Follow", "Footer", "Forward",
    "Get", "Google",
    "Header", "Help", "Home",
    "Image", "Images", "Index", "Information", "Instagram", "Internet",
    "Library", "Like", "Link", "LinkedIn", "Login", "Logo",
    "Made", "Many", "Mastodon", "Menu", "More",
    "Navigation", "Next",
    "Open", "Order", "Other",
    "Page", "Pages", "Photo", "Photos", "Pinterest", "Please",
    "Policy", "Post", "Previous", "Privacy", "Publication",
    "Read", "Reddit", "Reference", "References", "Reset",
    "Rights", "Reserved",
    "Save", "Scroll", "Search", "Section", "See", "Settings",
    "Share", "Sign", "Skip", "Submit", "Subscribe",
    "Tag", "Tags", "Terms", "The", "These", "This", "Top",
    "Twitter", "Type",
    "Update", "Use", "User",
    "View", "Vimeo",
    "Wayback", "Web", "WhatsApp",
    "X",
    "YouTube",
    "Yes", "No",
    # Month / day-of-week names — common in publication metadata but
    # rarely the load-bearing entity the contributor missed.
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday",
})


# Capitalized-token regex — words starting with uppercase, 3+ chars,
# allowing intra-word apostrophes / hyphens. Matches:
#   "Targ", "Lockheed", "Puthoff", "Stargate-precursor"
# Skips:
#   - All-caps acronyms (template noise; 2+ uppercase consecutive)
#   - Short words ("To", "By")
#   - Lowercase-starting tokens (handled by significant-token machinery
#     elsewhere)
_CAP_TOKEN_RE = re.compile(r"\b[A-Z][a-z][a-zA-Z\-']{1,}\b")


# Paragraph-split regex: blank line(s) between paragraphs. Tolerates
# whitespace-only "blank" lines that pdftotext sometimes emits.
_PARA_SPLIT_RE = re.compile(r"\n\s*\n+")


def split_paragraphs(text):
    """Split extracted source text into paragraphs.

    Convention: paragraphs separated by one or more blank lines.
    Each returned entry is stripped + non-empty.
    """
    out = []
    for chunk in _PARA_SPLIT_RE.split(text or ""):
        chunk = chunk.strip()
        if chunk:
            out.append(chunk)
    return out


def collect_artifact_text(data):
    """Pool all free-form text fields from the artifact into one blob.

    Captures: quote text + significance + context, entity name +
    wrap_path + context_summary, top-level prose fields, and every
    string value within entry lists. Used for the capitalized-token
    gap check — anything the contributor has already typed somewhere
    in the artifact shouldn't surface as a 'missed entity' candidate.
    """
    parts = []

    # Quotes
    for q in data.get("quotes") or []:
        if not isinstance(q, dict):
            continue
        for key in ("text", "significance", "context"):
            val = q.get(key)
            if isinstance(val, str):
                parts.append(val)

    # Entities
    for e in data.get("entities_referenced") or []:
        if not isinstance(e, dict):
            continue
        for key in ("name", "wrap_path", "context_summary"):
            val = e.get(key)
            if isinstance(val, str):
                parts.append(val)

    # Top-level prose
    for key in ("description", "background", "top_relevance",
                "credibility_notes", "pattern_statement"):
        val = data.get(key)
        if isinstance(val, str):
            parts.append(val)

    # Naming quirks
    for nq in data.get("naming_quirks") or []:
        if not isinstance(nq, dict):
            continue
        for key in ("observed", "canonical", "note"):
            val = nq.get(key)
            if isinstance(val, str):
                parts.append(val)

    # Rumors
    for r in data.get("rumors") or []:
        if not isinstance(r, dict):
            continue
        for key in ("claim", "note"):
            val = r.get(key)
            if isinstance(val, str):
                parts.append(val)
        for o in r.get("observed_sources") or []:
            if isinstance(o, str):
                parts.append(o)

    # Generic entry-list traversal for everything else — captures
    # affiliations / relationships / timeline / program_involvement /
    # ownership_timeline / top_scope_activity / location_relationships
    # / org_relationships / key_personnel / contracts / vouching_chain
    # / media_versioning / corroboration_items / speakers /
    # participants / witnesses_testimony etc. — without enumerating
    # each shape. We just walk dict values recursively.
    handled_keys = {
        "id", "type", "schema_version", "target_node", "status",
        "created", "updated", "primary_sources",
        "quotes", "entities_referenced", "naming_quirks", "rumors",
        "description", "background", "top_relevance",
        "credibility_notes", "pattern_statement", "document_intrinsic",
        "context_extrinsic",
    }
    for key, val in (data.items() if isinstance(data, dict) else []):
        if key in handled_keys:
            continue
        _collect_strings(val, parts)

    # document_intrinsic + context_extrinsic dict values
    for key in ("document_intrinsic", "context_extrinsic"):
        _collect_strings(data.get(key), parts)

    return " ".join(parts)


def _collect_strings(node, parts):
    """Recursively collect string values from a nested dict / list."""
    if isinstance(node, str):
        parts.append(node)
    elif isinstance(node, dict):
        for v in node.values():
            _collect_strings(v, parts)
    elif isinstance(node, list):
        for v in node:
            _collect_strings(v, parts)


def capitalized_tokens(text):
    """Return Counter of capitalized tokens in text.

    Lowercases nothing — preserves original casing. Filters:
      - NAV_NOISE — common web boilerplate (Home, About, Search, etc.)
      - STOPWORDS — sentence-starting function words like 'She',
        'And', 'Out', 'With' that the regex catches as capitalized
        but carry no entity signal. Reuses lib/_common.STOPWORDS
        (same set the prose-drift tokenizer filters) so the noise
        floor stays consistent across diagnostics.
    Symmetric: same function runs on source-side and artifact-side
    so the comparison is consistent.
    """
    if not text:
        return Counter()
    return Counter(
        m for m in _CAP_TOKEN_RE.findall(text)
        if m not in NAV_NOISE and m.lower() not in STOPWORDS
    )


def paragraph_coverage(paragraphs, quotes_for_source, min_chars):
    """Identify which paragraphs are referenced by at least one quote.

    Both sides go through normalize_for_compare so the match aligns
    with the verbatim-quote check's substring semantics: smart quotes,
    em/en dashes, hyphenation, and whitespace normalize identically
    before comparison.

    Returns list of (index, paragraph) tuples for paragraphs that:
      - are at least `min_chars` long (below threshold is likely nav
        noise / boilerplate), AND
      - contain no quote substring, AND
      - are not themselves contained in any quote

    Index is 1-based to match the contributor's `¶N` location-ref
    convention.
    """
    normalized_quotes = []
    for q in quotes_for_source:
        text = q.get("text") or ""
        if text.strip():
            normalized_quotes.append(normalize_for_compare(text))

    unreferenced = []
    for i, p in enumerate(paragraphs, start=1):
        if len(p) < min_chars:
            continue
        norm_p = normalize_for_compare(p)
        covered = False
        for nq in normalized_quotes:
            if not nq:
                continue
            # Either the quote is contained in the paragraph (typical
            # case — paragraph holds an inline quote), or the
            # paragraph is contained in a multi-paragraph quote.
            if nq in norm_p or norm_p in nq:
                covered = True
                break
        if not covered:
            unreferenced.append((i, p))
    return unreferenced


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Source-coverage audit aid — surface paragraphs and "
            "capitalized terms in primary sources that no artifact "
            "field references. Read-only diagnostic."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  coverage-suggest.py meta/research/russell-targ.yaml\n"
        ),
    )
    ap.add_argument("artifact_path",
                    help="Path to meta/research/{slug}.yaml")
    ap.add_argument("--min-paragraph-chars", type=int, default=80,
                    help="Skip paragraphs shorter than this (default 80)")
    ap.add_argument("--top-token-count", type=int, default=15,
                    help="Show top N unregistered capitalized tokens per source (default 15)")
    ap.add_argument("--max-paragraph-preview", type=int, default=140,
                    help="Preview length per unreferenced paragraph (default 140)")
    args = ap.parse_args()

    artifact_path = Path(args.artifact_path).resolve()
    if not artifact_path.exists():
        sys.exit(f"ERROR: artifact not found: {artifact_path}")

    with artifact_path.open() as f:
        data = strict_yaml_load(f) or {}

    primary_sources = data.get("primary_sources") or []
    if not primary_sources:
        sys.exit(f"ERROR: artifact has no primary_sources: {artifact_path}")

    quotes = data.get("quotes") or []
    artifact_text = collect_artifact_text(data)
    artifact_caps = set(capitalized_tokens(artifact_text).keys())

    rel_artifact = artifact_path.relative_to(REPO_ROOT) if REPO_ROOT in artifact_path.parents else artifact_path
    print(f"Coverage-suggest report for {rel_artifact}")
    print(f"  {len(primary_sources)} primary source(s); {len(quotes)} quote(s)")
    print()

    any_surfaced = False
    extracted_count = 0
    skipped_count = 0

    for ps in primary_sources:
        if not isinstance(ps, dict):
            continue
        path = ps.get("path")
        fmt = ps.get("format", "")
        if not path:
            continue

        source_file = SOURCES_DIR / path
        if not source_file.exists():
            print(f"⚠ {path}: source file missing — skipping")
            skipped_count += 1
            continue

        # Binary formats: extract_source_text returns None.
        text = extract_source_text(source_file)
        if not text:
            print(f"⚠ {path}: extraction empty (format={fmt or '?'}) — skipping")
            skipped_count += 1
            continue
        extracted_count += 1

        print(f"── {path} ──")

        # Paragraph coverage
        paragraphs = split_paragraphs(text)
        quotes_for_source = [q for q in quotes
                             if isinstance(q, dict)
                             and (q.get("source") or {}).get("path") == path]
        unreferenced = paragraph_coverage(
            paragraphs, quotes_for_source, args.min_paragraph_chars
        )

        if unreferenced:
            any_surfaced = True
            print(f"  Unreferenced substantive paragraphs ({len(unreferenced)} of {len(paragraphs)} total):")
            for idx, p in unreferenced[:10]:
                preview = p[:args.max_paragraph_preview]
                ellipsis = "…" if len(p) > args.max_paragraph_preview else ""
                print(f"    [¶~{idx}] {preview}{ellipsis}")
            if len(unreferenced) > 10:
                print(f"    … (+{len(unreferenced) - 10} more)")
        else:
            print(f"  ✓ Every substantive paragraph is quote-covered.")

        # Capitalized-token gap
        source_caps = capitalized_tokens(text)
        gap = Counter({
            tok: count for tok, count in source_caps.items()
            if tok not in artifact_caps
        })

        if gap:
            any_surfaced = True
            top = gap.most_common(args.top_token_count)
            print(f"  Unregistered capitalized terms (top {len(top)} by frequency):")
            for tok, cnt in top:
                print(f"    {tok}  ({cnt}x)")
            if len(gap) > args.top_token_count:
                print(f"    … (+{len(gap) - args.top_token_count} more, pass --top-token-count to see)")
        else:
            print(f"  ✓ No untracked capitalized terms above threshold.")

        print()

    if extracted_count == 0:
        sys.exit(
            f"\nERROR: no primary sources extracted successfully "
            f"({skipped_count} skipped). Check that source files exist "
            f"and pdftotext is available."
        )

    if not any_surfaced:
        print("No coverage gaps surfaced. The artifact appears to comprehensively cover its primary sources.")
    else:
        print("Read-only diagnostic. Judge each candidate manually:")
        print("  - Paragraph load-bearing for the subject? → add a quote")
        print("  - Capitalized term is a named entity? → register in entities_referenced[]")
        print("  - Boilerplate / navigation / tangential? → ignore (no action needed)")
        print()
        print("[¶~N] indices are paragraph-numbers in the EXTRACTED scratch text")
        print("(blank-line-delimited). Tightness convention for actual quote")
        print("location refs lives in meta/conventions.md.")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
