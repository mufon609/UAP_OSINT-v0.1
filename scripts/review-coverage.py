#!/usr/bin/env python3
"""
Phase III — Coverage review between a research artifact and its regenerated node.

Mechanical consistency checks run after Phase II build. Complements
validate.py (node structure + verbatim quotes) and validate-research.py
(artifact structure); this script compares the two layers against each
other.

Checks:
  1. Coverage     — every artifact claim.statement and every quote.text
                    appears in the node body (whitespace/punctuation
                    normalized per validate.py rules).
  2. Boundary     — the node body (outside Associated Nodes) matches what
                    `build-from-research.py --dry-run` would regenerate
                    from the current artifact. Divergence means the
                    artifact drifted from the node, the node was
                    hand-edited, or the renderer changed.
  3. Stub-linking — every entities_referenced.wrap_path appears as a
                    [`/path`] link in the node body.
  4. OQ dedup     — the '## Open Questions / Research Gaps' items map 1:1
                    to unresolved research_gaps (plus any retained-DONE
                    resolved gaps).
  5. Claim drift  — every significant token (proper noun, designator,
                    number, quoted string) in a claim.statement appears
                    in the source text. Catches coarse drift: fabricated
                    facts, fabricated entities, contributor additions not
                    anchored in the source. For claims with quote_ref,
                    tokens present in source but NOT in the referenced
                    quote emit a warning — the contributor drew beyond
                    the cited anchor. Does NOT catch fine drift (dropped
                    qualifiers, rephrased inferences, voice changes);
                    those require semantic review (Phase III Step 2).
                    Paired with validate-research.py's quote_ref-required
                    check which ensures every claim has an anchor to
                    check against.
  6. Description  — every significant token in the node's ## Description
     drift         section appears in the artifact's grounding text:
                    source text + context_extrinsic strings +
                    document_intrinsic strings + naming_quirks canonical
                    forms + entities_referenced names. This closes the
                    drift surface the claims-layer elimination opened
                    wider: Description is the last contributor-prose
                    layer on document nodes. Same error semantics as
                    Check 5 — fabricated entities or abbreviation
                    expansions that don't match source become commit-
                    blocking errors. Fine drift (dropped qualifiers,
                    synonym rephrases at the lowercase level) is still
                    not caught — semantic review required.

Scope: document nodes only (matching build-from-research.py D.3). Other
node types are acknowledged and skipped — extension is BACKLOG work
alongside the per-type Phase II renderers.

This script handles mechanical rules only. Semantic / narrative-coherence
review (agent-assisted) is a separate pass referenced in
`prompts/build.md`.

Usage:
  review-coverage.py {artifact_path}
  review-coverage.py --all
  review-coverage.py --quiet

Expected execution order per prompts/build.md:
  validate-research.py {artifact}  →  build-from-research.py {artifact}
    →  validate.py {node}  →  review-coverage.py {artifact}
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from collections import defaultdict

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# =============================================================================
# Constants
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SOURCES_DIR = REPO_ROOT / "sources"
BUILD_FROM_RESEARCH = SCRIPTS_DIR / "build-from-research.py"
RESEARCH_DIR = REPO_ROOT / "research"

TYPE_DIRS = {
    "person": "people", "organization": "organizations", "document": "documents",
    "event": "events", "transcript": "transcripts", "media": "media",
    "location": "locations", "finding": "findings",
}
# Matches build-from-research.py SUPPORTED_TYPES. Expand in lockstep.
SUPPORTED_TYPES = {"document", "person", "event", "transcript", "media", "organization"}

LINK_PATTERN = re.compile(r"\[`(/[^`]+)`\]")

# --- Check 5 (Claim drift) patterns and vocab -------------------------------
# Markdown link syntax used to wrap entity paths in claim prose. Stripped
# before token extraction since wrap_paths are repo identifiers, not
# content claims about the source.
MARKDOWN_LINK_PATTERN = re.compile(r"\[`/[^`]+`\]")
# Wrap-inside-parens pattern — strips the PARENS ALONG WITH the wrap when
# the parens contain only the wrap path. Prevents orphan `()` in the
# stripped output when contributors write `Name ([`/path`])` inside a
# double-quoted span, which otherwise becomes `Name ()` and leaks into
# the description-drift check as a bogus token. Surfaced by the F.5
# UAPTF pilot (Norquist wrap inside a DoD press-release quote).
WRAP_IN_PARENS_PATTERN = re.compile(r"\s*\(\s*\[`/[^`]+`\]\s*\)")

# Designator patterns like VFA-41, CVN-68, F/A-18F, APG-73 — uppercase
# tokens combining letters and digits around a hyphen or slash. These
# should appear verbatim in the source when the claim cites them.
DESIGNATOR_PATTERN = re.compile(r"\b[A-Z][A-Z0-9]*[-/][A-Z0-9/-]*[A-Z0-9]\b")

# Digit sequences — years, altitudes, counts. Allows commas, periods,
# and trailing + ("10+").
NUMBER_PATTERN = re.compile(r"\b\d[\d,.]*\+?\b")

# Capitalized word pattern — proper-noun candidates. Matches hyphenated
# words like "Forty-One" as a single token.
CAPWORD_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9-]*\b")

# Capitalized words that are grammatical (pronouns, articles, prepositions,
# conjunctions, adverbs). Excluded from drift-check token collection so
# "Per Fravor," doesn't flag "Per" as a missing proper noun.
CAPITALIZED_STOPWORDS = frozenset({
    "I", "He", "She", "They", "We", "You", "It", "Me", "Us", "Them",
    "The", "A", "An",
    "Per", "This", "That", "These", "Those",
    "Here", "There", "When", "Where", "Why", "How",
    "But", "And", "Or", "So", "Yet", "For", "Nor",
    "In", "On", "At", "By", "To", "From", "With", "Of", "About",
    "After", "Before", "During", "Since", "Until", "Throughout",
    "As", "If", "While", "Though", "Although", "Because",
    "My", "Your", "His", "Her", "Their", "Our", "Its",
    "All", "Any", "Each", "Every", "Some", "Most", "Few", "Many",
    "No", "Not", "None", "Nothing",
    "Yes", "Now", "Then", "Also",
    "Both", "Either", "Neither",
})


# =============================================================================
# Types and reporting
# =============================================================================

class Issue:
    def __init__(self, path, level, message):
        self.path = str(path)
        self.level = level  # "error" | "warn" | "info"
        self.message = message


# =============================================================================
# Parsing helpers
# =============================================================================

def normalize_for_compare(text):
    """Mirror validate.py.normalize_for_compare exactly.

    Handles common rendering artifacts so a claim/quote from the artifact
    can be found as a substring in the rendered node body regardless of
    table-cell punctuation, line wrap, smart quotes, Markdown block-quote
    line-prefix markers, etc. Keep in lockstep with validate.py —
    divergence between the two breaks the cross-check guarantees the
    repository relies on.
    """
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    text = text.replace("\u00a0", " ")
    # Markdown block-quote markers at line start — strip `> ` / `>` prefix
    # so multi-line block quotes normalize to their underlying content.
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = re.sub(r"-\s+", "-", text)
    text = text.replace("-", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_artifact(path):
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        sys.exit(f"ERROR: artifact parse failure: {e}")
    if not isinstance(data, dict):
        sys.exit(f"ERROR: artifact root is not a YAML mapping: {path}")
    return data


def target_node_path(artifact):
    target = artifact.get("target_node") or ""
    if "/" not in target:
        return None
    return REPO_ROOT / f"{target}.md"


def target_node_type(artifact):
    target = artifact.get("target_node") or ""
    if "/" not in target:
        return None
    dir_name = target.split("/", 1)[0]
    reverse = {v: k for k, v in TYPE_DIRS.items()}
    return reverse.get(dir_name)


def excise_associated_nodes(text):
    """Strip the '## Associated Nodes' section (up to the next H2) so the
    boundary diff can focus on the Phase II-rendered body. The Associated
    Nodes section is regenerated by associate.py post-build and is not part
    of build-from-research.py's deterministic output (it emits a placeholder).
    """
    pattern = re.compile(
        r"^## Associated Nodes\s*$.*?(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return pattern.sub("", text).rstrip() + "\n"


def truncate(s, n=80):
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[:n] + "..."


# --- Check 5 helpers: source extraction and claim-token analysis -----------

_source_text_cache = {}  # Path -> extracted plaintext (or None on failure)


def extract_source_text(source_path):
    """Extract plaintext from an archived source file. Returns None on
    failure. Cached per validator run to avoid repeated subprocess calls
    for multi-source artifacts.

    Mirrors the extraction logic in validate.py (`extract_source_text`)
    and extract-source.py by design — the token drift check must see
    exactly what the verbatim-quote check sees to avoid normalization
    skew between the two layers.
    """
    if source_path in _source_text_cache:
        return _source_text_cache[source_path]
    result = None
    suffix = source_path.suffix.lower()
    if suffix == ".pdf":
        try:
            proc = subprocess.run(
                ["pdftotext", "-layout", str(source_path), "-"],
                capture_output=True, text=True, timeout=60,
            )
            if proc.returncode == 0:
                result = proc.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            result = None
    elif suffix in (".html", ".htm", ".txt", ".md"):
        try:
            result = source_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            result = None
    _source_text_cache[source_path] = result
    return result


def strip_markdown_links(text):
    """Remove [`/path/to/entity`] wrap-path link syntax from claim text.

    These are repository identifiers (navigational cross-references), not
    content claims about the source document. A claim that wraps
    `[`/organizations/vfa-41`]` around a squadron name is stating a repo
    fact (the canonical entity lives here), not a source fact (the
    document said "VFA-41"). Drift checks run on the bare prose left
    after stripping — the entity linkage is checked separately by the
    stub-linking pass.

    Two-pass strip:
      (1) Wraps inside empty parens `( [`/path`] )` are removed AS A
          UNIT (parens + wrap + interior whitespace). This prevents
          orphan `()` from leaking into the extracted text when
          contributors write `Name ([`/path`])` inside a double-quoted
          span. Without this pass, the bare `()` becomes part of any
          double-quoted token extracted for drift analysis and fails
          the description-drift substring check against source.
      (2) Any remaining bare wraps (not surrounded by empty parens) are
          stripped by the standard pattern.
    """
    text = WRAP_IN_PARENS_PATTERN.sub("", text)
    return MARKDOWN_LINK_PATTERN.sub("", text)


def extract_significant_tokens(claim_text):
    """Return set of tokens from a claim statement worth checking against
    the source. A "significant token" is one that, if fabricated, would
    represent real evidentiary drift:

      - Hyphen/slash designators (VFA-41, F/A-18F, CVN-68, APG-73)
      - Digit sequences (2004, 20,000, 10+)
      - Capitalized non-stopword words (proper nouns: Fravor, Pentagon,
        Nimitz, etc. — also compound pieces like "Forty-One")
      - Quoted strings (content inside " " or ' ') — direct source-word
        claims

    Grammatical / function words that happen to be capitalized (pronouns,
    articles, sentence-initial conjunctions) are filtered via the
    CAPITALIZED_STOPWORDS list. Single characters and empty strings are
    dropped.
    """
    text = strip_markdown_links(claim_text)
    tokens = set()

    # 1. Hyphen/slash designators (caps + digit/letter mix)
    for m in DESIGNATOR_PATTERN.finditer(text):
        tokens.add(m.group())

    # 2. Digit sequences
    for m in NUMBER_PATTERN.finditer(text):
        tokens.add(m.group())

    # 3. Capitalized words (proper-noun candidates). Remove designators
    #    and numbers first so they don't double-match.
    clean = DESIGNATOR_PATTERN.sub(" ", text)
    clean = NUMBER_PATTERN.sub(" ", clean)
    for m in CAPWORD_PATTERN.finditer(clean):
        word = m.group()
        if len(word) < 2:
            continue
        if word in CAPITALIZED_STOPWORDS:
            continue
        tokens.add(word)

    # 4. Double-quoted strings — content inside "..." is an explicit
    #    claim about source wording and must match verbatim.
    for m in re.finditer(r'"([^"]+)"', text):
        q = m.group(1).strip()
        if q:
            tokens.add(q)

    # Single-quoted strings are NOT extracted. In English prose, a naked
    # apostrophe is overwhelmingly a possessive or contraction (e.g.,
    # "Gallaudet's system and his deputy's"), not a quote delimiter.
    # Matching `'([^']+)'` over prose produces false positives like
    # "s system and his deputy" that flag as bogus drift. Any legitimate
    # single-quoted passage worth checking already gets caught by the
    # capitalized-word and designator extractors, or can be written with
    # double quotes if it must be matched as a phrase.

    return tokens


def gather_source_text(artifact):
    """Concatenate plaintext of every archived primary source on the
    artifact. Returns (combined_text, missing_paths) where
    missing_paths is any primary_sources[].path that could not be
    extracted."""
    chunks = []
    missing = []
    for ps in (artifact.get("primary_sources") or []):
        if not isinstance(ps, dict):
            continue
        rel_path = ps.get("path")
        if not rel_path:
            continue
        full = SOURCES_DIR / rel_path
        if not full.exists():
            missing.append(rel_path)
            continue
        text = extract_source_text(full)
        if text is None:
            missing.append(rel_path)
            continue
        chunks.append(text)
    return ("\n".join(chunks), missing)


def gather_grounding_text(artifact, source_text):
    """Build the text corpus against which Description prose tokens are
    checked (Check 6).

    Grounding sources:
      - source_text                        (what the document actually says)
      - context_extrinsic string values    (contextual metadata — hearing
                                            date, display title, provenance
                                            entries; facts the artifact
                                            declares from outside the doc)
      - document_intrinsic string values   (facts from inside the document —
                                            internal title, classification,
                                            authors_per_document)
      - naming_quirks[].canonical          (approved canonical forms to use
                                            in prose, even when source uses
                                            a different spelling — e.g.,
                                            "Leslie Kean" canonical vs
                                            source's "Leslie Keane")
      - entities_referenced[].name         (approved entity display names)

    Explicitly NOT in grounding (would be circular — grounding contributor
    prose with other contributor prose):
      - claims[].statement
      - entities_referenced[].context_summary
      - research_gaps[] text
      - rumors[] text
    """
    chunks = [source_text or ""]

    def collect_strings(obj):
        if isinstance(obj, str):
            chunks.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                collect_strings(item)
        elif isinstance(obj, dict):
            for v in obj.values():
                collect_strings(v)

    collect_strings(artifact.get("context_extrinsic") or {})
    collect_strings(artifact.get("document_intrinsic") or {})

    for nq in (artifact.get("naming_quirks") or []):
        if isinstance(nq, dict) and nq.get("canonical"):
            chunks.append(nq["canonical"])

    for e in (artifact.get("entities_referenced") or []):
        if isinstance(e, dict) and e.get("name"):
            chunks.append(e["name"])

    return "\n".join(chunks)


def extract_description_text(node_text):
    """Return the prose body of the node's `## Description` section, or
    None if the section is absent (e.g., non-document node type during
    the build-from-research per-type extension)."""
    m = re.search(
        r"^## Description\s*$(.*?)(?=^## |\Z)",
        node_text, re.MULTILINE | re.DOTALL,
    )
    if not m:
        return None
    return m.group(1).strip()


# =============================================================================
# Check 1 — Coverage
# =============================================================================

def check_coverage(artifact, node_text, rel):
    issues = []
    normalized_body = normalize_for_compare(node_text)

    for c in artifact.get("claims") or []:
        if not isinstance(c, dict):
            continue
        stmt = (c.get("statement") or "").strip()
        if not stmt:
            continue
        if normalize_for_compare(stmt) not in normalized_body:
            issues.append(Issue(rel, "error",
                f"Coverage: claim {c.get('id')!r} statement not found in node "
                f'body: "{truncate(stmt)}"'))

    for q in artifact.get("quotes") or []:
        if not isinstance(q, dict):
            continue
        text = (q.get("text") or "").strip()
        if not text:
            continue
        if normalize_for_compare(text) not in normalized_body:
            issues.append(Issue(rel, "error",
                f"Coverage: quote {q.get('id')!r} text not found in node "
                f'body: "{truncate(text)}"'))

    return issues


# =============================================================================
# Check 2 — Boundary (re-render + diff, excluding Associated Nodes)
# =============================================================================

def check_boundary(artifact_path, node_path, rel):
    issues = []
    try:
        proc = subprocess.run(
            ["python3", str(BUILD_FROM_RESEARCH),
             str(artifact_path), "--dry-run", "--no-validate"],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        issues.append(Issue(rel, "error",
            "Boundary: build-from-research.py timed out during dry-run"))
        return issues

    if proc.returncode != 0:
        detail = (proc.stderr.strip() or proc.stdout.strip())[:200]
        issues.append(Issue(rel, "error",
            f"Boundary: build-from-research.py exited {proc.returncode}: {detail}"))
        return issues

    regenerated = proc.stdout
    current = node_path.read_text()

    regen_excised = excise_associated_nodes(regenerated).strip()
    current_excised = excise_associated_nodes(current).strip()

    if regen_excised != current_excised:
        issues.append(Issue(rel, "error",
            "Boundary: node body diverges from build-from-research.py output. "
            "Either the artifact drifted from the node, or the node was "
            "hand-edited. Re-run build-from-research.py to resync."))
    return issues


# =============================================================================
# Check 3 — Stub-linking
# =============================================================================

def check_stub_linking(artifact, node_text, rel):
    issues = []
    links_in_node = set(LINK_PATTERN.findall(node_text))
    for e in artifact.get("entities_referenced") or []:
        if not isinstance(e, dict):
            continue
        wp = e.get("wrap_path")
        if not wp:
            continue
        if wp not in links_in_node:
            issues.append(Issue(rel, "error",
                f"Stub-linking: entity {e.get('id')!r} ({e.get('name')!r}) "
                f"wrap_path {wp!r} does not appear as a [`{wp}`] link in the node"))
    return issues


# =============================================================================
# Check 4 — OQ dedup (research_gaps ↔ Open Questions)
# =============================================================================

def extract_oq_items(node_text):
    """Return (unresolved_lines, resolved_lines) from the Open Questions section.
    Strips the leading '- [ ]' / '- [x]' marker."""
    m = re.search(
        r"^## Open Questions / Research Gaps\s*$(.*?)(?=^## |\Z)",
        node_text, re.MULTILINE | re.DOTALL,
    )
    if not m:
        return [], []
    section = m.group(1)
    unresolved, resolved = [], []
    for line in section.splitlines():
        s = line.strip()
        if s.startswith("- [ ]"):
            unresolved.append(s[5:].strip())
        elif s.startswith("- [x]"):
            resolved.append(s[5:].strip())
    return unresolved, resolved


def check_oq_dedup(artifact, node_text, rel):
    issues = []
    node_unresolved, node_resolved = extract_oq_items(node_text)

    gaps = artifact.get("research_gaps") or []
    artifact_unresolved = []
    artifact_retained = []
    for g in gaps:
        if not isinstance(g, dict):
            continue
        stmt = (g.get("statement") or "").strip()
        if not stmt:
            continue
        if g.get("resolved"):
            if g.get("retain_as_done"):
                artifact_retained.append(stmt)
        else:
            artifact_unresolved.append(stmt)

    node_u_norm = [normalize_for_compare(s) for s in node_unresolved]
    art_u_norm = [normalize_for_compare(s) for s in artifact_unresolved]
    node_r_norm = [normalize_for_compare(s) for s in node_resolved]
    art_r_norm = [normalize_for_compare(s) for s in artifact_retained]

    # Every unresolved artifact gap must appear in node unresolved items
    for stmt, nstmt in zip(artifact_unresolved, art_u_norm):
        if not any(nstmt in u for u in node_u_norm):
            issues.append(Issue(rel, "error",
                f'OQ: unresolved research_gap missing from node Open Questions: '
                f'"{truncate(stmt)}"'))

    # Every node unresolved item must map to an unresolved artifact gap
    for stmt, nstmt in zip(node_unresolved, node_u_norm):
        if not any(a in nstmt for a in art_u_norm):
            issues.append(Issue(rel, "error",
                f'OQ: node unresolved item does not map to an unresolved '
                f'research_gap: "{truncate(stmt)}"'))

    # Every retained-DONE artifact gap must appear in node resolved items
    for stmt, nstmt in zip(artifact_retained, art_r_norm):
        if not any(nstmt in r for r in node_r_norm):
            issues.append(Issue(rel, "error",
                f'OQ: retained-DONE gap missing from node Open Questions: '
                f'"{truncate(stmt)}"'))

    # Every node resolved item must map to a retained-DONE gap
    for stmt, nstmt in zip(node_resolved, node_r_norm):
        if not any(a in nstmt for a in art_r_norm):
            issues.append(Issue(rel, "error",
                f'OQ: node resolved item does not map to a retain_as_done '
                f'research_gap: "{truncate(stmt)}"'))

    return issues


# =============================================================================
# Check 5 — Claim token drift (against source and optional referenced quote)
# =============================================================================

def check_claim_token_drift(artifact, source_text, rel):
    """Verify every significant token in each claim.statement appears in
    the source text. For claims with a quote_ref, also emit a warning
    when the token appears in the source but NOT in the referenced quote
    — the contributor drew from outside the cited anchor.

    Error (in source / not in source) vs warning (in source / not in
    quote) is deliberate. Errors block commit because a token not in the
    source is either a fabrication or a wording drift that breaks
    grep-ability. Warnings don't block because the contributor may have
    legitimate reasons to reference broader source context, but the
    cited anchor should ideally be tight enough that no such expansion
    is needed.

    This check is paired with validate-research.py's claim-anchor
    requirement (every claim must have at least one quote_ref), so
    every claim reaches this check with an anchor to compare against.
    """
    issues = []
    if not source_text:
        # No source to check against (missing files already reported
        # elsewhere). Skip silently rather than false-positive.
        return issues

    quotes_by_id = {
        q.get("id"): q
        for q in (artifact.get("quotes") or [])
        if isinstance(q, dict) and q.get("id")
    }

    norm_source = normalize_for_compare(source_text).lower()

    for c in (artifact.get("claims") or []):
        if not isinstance(c, dict):
            continue
        statement = (c.get("statement") or "").strip()
        if not statement:
            continue
        claim_id = c.get("id", "?")

        tokens = extract_significant_tokens(statement)
        if not tokens:
            continue

        # Identify the referenced quote text (first source with a
        # quote_ref pointing to an existing quote wins). Concatenate
        # multiple if several sources carry quote_refs.
        quote_texts = []
        for src in (c.get("sources") or []):
            if not isinstance(src, dict):
                continue
            qref = src.get("quote_ref")
            if qref and qref in quotes_by_id:
                qt = quotes_by_id[qref].get("text")
                if qt:
                    quote_texts.append(qt)
        norm_quote = (
            normalize_for_compare("\n".join(quote_texts)).lower()
            if quote_texts else None
        )

        for token in sorted(tokens):
            norm_token = normalize_for_compare(token).lower()
            if not norm_token:
                continue

            in_source = norm_token in norm_source
            if not in_source:
                issues.append(Issue(rel, "error",
                    f"Drift: claim {claim_id!r} contains token {token!r} "
                    f"not found anywhere in the source text. Either "
                    f"correct the claim to match source wording, or add "
                    f"the source passage that supports it."))
                continue

            if norm_quote is not None:
                in_quote = norm_token in norm_quote
                if not in_quote:
                    issues.append(Issue(rel, "warn",
                        f"Drift: claim {claim_id!r} token {token!r} is in "
                        f"the source but not in the referenced quote "
                        f"(quote_ref). Claim may be drawing from outside "
                        f"the cited anchor — tighten the quote or split "
                        f"the claim."))
    return issues


# =============================================================================
# Check 6 — Description token drift (against artifact grounding)
# =============================================================================

def check_description_token_drift(artifact, node_text, source_text, rel):
    """Verify every significant token in the node's ## Description section
    appears in the artifact's grounding text (source + context_extrinsic +
    document_intrinsic + naming_quirks canonical + entities_referenced
    names). See gather_grounding_text() docstring for the full rationale.

    Closes the drift surface the claims-layer elimination opened wider:
    Description is the last contributor-prose layer on document nodes.
    Same error semantics as Check 5 — fabricated entities, abbreviation
    expansions that don't match source, numbers not in any grounding
    field become commit-blocking errors.

    Limit: fine drift at the lowercase level (e.g., "warning area" vs
    source's "early warning area") is NOT caught — "early" is lowercase
    and not extracted as a significant token. Semantic review (Phase III
    Step 2) remains required for that class of drift.
    """
    issues = []
    desc = extract_description_text(node_text)
    if desc is None:
        return issues

    tokens = extract_significant_tokens(desc)
    if not tokens:
        return issues

    if not source_text:
        # Missing-source error already reported by gather_source_text
        # caller; skip here to avoid duplicate noise
        return issues

    grounding = gather_grounding_text(artifact, source_text)
    norm_grounding = normalize_for_compare(grounding).lower()

    for token in sorted(tokens):
        norm_token = normalize_for_compare(token).lower()
        if not norm_token:
            continue
        if norm_token not in norm_grounding:
            issues.append(Issue(rel, "error",
                f"Description drift: token {token!r} not found in source, "
                f"context_extrinsic, document_intrinsic, naming_quirks "
                f"canonical, or entities_referenced names. Either correct "
                f"the description to match available grounding, or add "
                f"the supporting data to the artifact."))
    return issues


# =============================================================================
# Per-artifact orchestration
# =============================================================================

def review_artifact(artifact_path, quiet=False):
    """Return (issues, skipped_reason_or_None)."""
    rel = artifact_path.relative_to(REPO_ROOT)

    if not artifact_path.exists():
        return [Issue(rel, "error", "Artifact file does not exist")], None

    artifact = load_artifact(artifact_path)

    node_path = target_node_path(artifact)
    if node_path is None or not node_path.exists():
        return [Issue(rel, "error",
            f"target_node {artifact.get('target_node')!r} does not point to an existing file")], None

    node_type = target_node_type(artifact)
    if node_type not in SUPPORTED_TYPES:
        return [], f"node type {node_type!r} not yet supported in Phase III (BACKLOG)"

    node_text = node_path.read_text()

    # Gather source plaintext for claim-drift check (cached across calls)
    source_text, missing_sources = gather_source_text(artifact)

    issues = []
    for path in missing_sources:
        full = SOURCES_DIR / path
        if not full.exists():
            # File not on disk at all — legitimate error (source archival
            # discipline broken). Manifest points at a path that isn't
            # present.
            issues.append(Issue(rel, "error",
                f"Claim drift check: primary source {path!r} missing — "
                f"file not present on disk under sources/. Source-archival "
                f"integrity issue; verify the manifest entry and re-archive "
                f"if needed."))
        else:
            # File exists but isn't text-extractable — typical for binary
            # media (video/audio/image). The quote-verbatim check in
            # validate.py treats this as warn (not error) via the same
            # reasoning; the claim-token-drift check here follows suit.
            # Contributor takes responsibility for any verbatim quotes
            # from the media source (manual frame/audio inspection).
            # Non-blocking.
            issues.append(Issue(rel, "warn",
                f"Claim drift check: primary source {path!r} not text-"
                f"extractable (likely binary media — video/audio/image). "
                f"Claim tokens skipped for this source; verbatim quote "
                f"extraction from media sources requires manual "
                f"contributor verification."))

    issues.extend(check_coverage(artifact, node_text, rel))
    issues.extend(check_boundary(artifact_path, node_path, rel))
    issues.extend(check_stub_linking(artifact, node_text, rel))
    issues.extend(check_oq_dedup(artifact, node_text, rel))
    issues.extend(check_claim_token_drift(artifact, source_text, rel))
    issues.extend(check_description_token_drift(artifact, node_text, source_text, rel))
    return issues, None


def collect_artifacts():
    if not RESEARCH_DIR.is_dir():
        return []
    return sorted(RESEARCH_DIR.glob("*.yaml"))


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?",
                        help="Research artifact path (research/{slug}.yaml)")
    parser.add_argument("--all", action="store_true",
                        help="Review every artifact under research/")
    parser.add_argument("--quiet", action="store_true",
                        help="Errors only; suppress info/skip notices")
    args = parser.parse_args()

    if args.path:
        artifacts = [Path(args.path).resolve()]
    elif args.all:
        artifacts = collect_artifacts()
    else:
        parser.print_help()
        sys.exit(0)

    all_issues = []
    reviewed = 0
    skipped = []

    for p in artifacts:
        issues, skip_reason = review_artifact(p, quiet=args.quiet)
        if skip_reason:
            skipped.append((p.relative_to(REPO_ROOT), skip_reason))
            continue
        reviewed += 1
        all_issues.extend(issues)

    errors = [i for i in all_issues if i.level == "error"]
    warnings = [i for i in all_issues if i.level == "warn"]

    print("=" * 64)
    print(" Phase III — Coverage Review")
    print("=" * 64)
    print(f"\n  Artifacts reviewed: {reviewed}")
    print(f"  Skipped:            {len(skipped)}")
    print(f"  Errors:             {len(errors)}")
    if not args.quiet:
        print(f"  Warnings:           {len(warnings)}")

    if skipped and not args.quiet:
        print("\n" + "-" * 64)
        print(" Skipped")
        print("-" * 64)
        for p, reason in skipped:
            print(f"  {p} — {reason}")

    if all_issues:
        print("\n" + "-" * 64)
        print(" Issues")
        print("-" * 64)
        by_file = defaultdict(list)
        for issue in all_issues:
            if args.quiet and issue.level != "error":
                continue
            by_file[issue.path].append(issue)
        for f in sorted(by_file.keys()):
            print(f"\n  {f}")
            for issue in by_file[f]:
                tag = "ERROR" if issue.level == "error" else "WARN "
                print(f"    [{tag}] {issue.message}")

    print("\n" + "=" * 64)
    if errors:
        print(f"  FAILED — {len(errors)} error(s)")
        sys.exit(1)
    print(f"  PASSED — {len(warnings)} warning(s)")
    sys.exit(0)


if __name__ == "__main__":
    main()
