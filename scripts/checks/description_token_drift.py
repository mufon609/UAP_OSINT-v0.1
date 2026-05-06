"""description-token-drift check — cross-layer ResearchContext check.

Verifies every significant token in the node's ``## Description``
section appears in the artifact's grounding text:

  - source_text                       (what the document actually says)
  - context_extrinsic string values   (contextual metadata — hearing
                                       date, display title, provenance)
  - document_intrinsic string values  (facts from inside the document —
                                       internal title, classification)
  - naming_quirks[].canonical         (approved canonical forms)
  - entities_referenced[].name        (approved entity display names)

Description is the contributor-synthesis prose layer on document
nodes. Fabricated entities, abbreviation expansions that don't match
source, numbers not in any grounding field — all become
commit-blocking errors.

Limit: fine drift at the lowercase level (e.g., "warning area" vs
source's "early warning area") is NOT caught — "early" is lowercase
and not extracted as a significant token. Semantic review remains
required for that class of drift.

Different algorithm from ``lib._common.extract_significant_tokens``
(used by validate-research.py's prose_drift). This module extracts
proper-noun + designator + quoted-string drift candidates; the lib
tokenizer extracts lowercase content words. The naming distinction
(``extract_description_drift_tokens`` here vs
``extract_significant_tokens`` in lib) is deliberate to prevent
"let's deduplicate" refactors that would silently break either
drift check.

Severity differs from prose_drift: this check errors per unmatched
token rather than warn-then-error-at-100%. The rendered description
is a published artifact surface; unmatched tokens are either
fabrication or naming-quirks gaps that should be filed structurally
(add the canonical form to naming_quirks, the entity to
entities_referenced, or the metadata to context_extrinsic /
document_intrinsic) — not contributor-judgment territory.
"""

import re

from checks import Issue
from lib._common import normalize_for_compare


CHECK_NAME = "description_token_drift"


# Markdown link syntax used to wrap entity paths in prose. Stripped
# before token extraction since wrap_paths are repo identifiers, not
# content from the source.
_MARKDOWN_LINK_PATTERN = re.compile(r"\[`/[^`]+`\]")
# Wrap-inside-parens — strips the parens along with the wrap when the
# parens contain only the wrap path. Prevents orphan `()` in the
# stripped output when contributors write `Name ([`/path`])` inside a
# double-quoted span.
_WRAP_IN_PARENS_PATTERN = re.compile(r"\s*\(\s*\[`/[^`]+`\]\s*\)")

# Hyphen/slash designators (uppercase tokens combining letters and
# digits): VFA-41, F/A-18F, CVN-68, APG-73. Should appear verbatim in
# the source when prose cites them.
_DESIGNATOR_PATTERN = re.compile(r"\b[A-Z][A-Z0-9]*[-/][A-Z0-9/-]*[A-Z0-9]\b")
# Digit sequences — years, altitudes, counts. Allows commas, periods,
# and trailing + ("10+").
_NUMBER_PATTERN = re.compile(r"\b\d[\d,.]*\+?\b")
# Capitalized word — proper-noun candidates. Matches hyphenated words
# like "Forty-One" as a single token.
_CAPWORD_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9-]*\b")

# Capitalized words that are grammatical (pronouns, articles,
# prepositions, conjunctions, adverbs). Excluded from drift-check
# token collection so "Per Fravor," doesn't flag "Per" as a missing
# proper noun.
_CAPITALIZED_STOPWORDS = frozenset({
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


def _strip_markdown_links(text):
    """Remove ``[`/path`]`` link syntax from prose. Two-pass strip:
    (1) wraps inside empty parens get stripped as a unit (parens + wrap
    + interior whitespace) so contributors writing ``Name ([`/path`])``
    inside a double-quoted span don't leave orphan ``()`` in the
    stripped output; (2) any remaining bare wraps get stripped by the
    standard pattern."""
    text = _WRAP_IN_PARENS_PATTERN.sub("", text)
    return _MARKDOWN_LINK_PATTERN.sub("", text)


def _extract_description_drift_tokens(text):
    """Return set of tokens worth checking against the artifact's
    grounding. A drift token is one that, if fabricated, would
    represent real evidentiary drift in the rendered Description
    section: hyphen/slash designators, digit sequences, capitalized
    proper nouns, double-quoted strings."""
    text = _strip_markdown_links(text)
    tokens = set()

    for m in _DESIGNATOR_PATTERN.finditer(text):
        tokens.add(m.group())

    for m in _NUMBER_PATTERN.finditer(text):
        tokens.add(m.group())

    # Remove designators + numbers before capword extraction so they
    # don't double-match.
    clean = _DESIGNATOR_PATTERN.sub(" ", text)
    clean = _NUMBER_PATTERN.sub(" ", clean)
    for m in _CAPWORD_PATTERN.finditer(clean):
        word = m.group()
        if len(word) < 2:
            continue
        if word in _CAPITALIZED_STOPWORDS:
            continue
        tokens.add(word)

    # Double-quoted strings — content inside "..." must match verbatim.
    for m in re.finditer(r'"([^"]+)"', text):
        q = m.group(1).strip()
        if q:
            tokens.add(q)

    # Single-quoted strings deliberately NOT extracted — naked
    # apostrophes are overwhelmingly possessives / contractions.

    return tokens


def _extract_description_text(node_text):
    """Return the prose body of the node's ``## Description`` section,
    or None if the section is absent (person nodes have no Description
    section — their prose lives in background / top_relevance /
    credibility_notes instead)."""
    m = re.search(
        r"^## Description\s*$(.*?)(?=^## |\Z)",
        node_text, re.MULTILINE | re.DOTALL,
    )
    if not m:
        return None
    return m.group(1).strip()


def _gather_grounding_text(artifact, source_text):
    """Build the corpus against which Description tokens are checked."""
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

    for nq in artifact.get("naming_quirks") or []:
        if isinstance(nq, dict) and nq.get("canonical"):
            chunks.append(nq["canonical"])

    for e in artifact.get("entities_referenced") or []:
        if isinstance(e, dict) and e.get("name"):
            chunks.append(e["name"])

    return "\n".join(chunks)


def check(ctx):
    if ctx.node_text is None:
        return
    desc = _extract_description_text(ctx.node_text)
    if desc is None:
        return

    tokens = _extract_description_drift_tokens(desc)
    if not tokens:
        return

    if not ctx.source_text:
        # Missing-source warning handled by orchestrator at gather time.
        return

    grounding = _gather_grounding_text(ctx.data, ctx.source_text)
    norm_grounding = normalize_for_compare(grounding).lower()

    for token in sorted(tokens):
        norm_token = normalize_for_compare(token).lower()
        if not norm_token:
            continue
        if norm_token not in norm_grounding:
            yield Issue(
                ctx.rel, "error",
                f"Description drift: token {token!r} not found in source, "
                f"context_extrinsic, document_intrinsic, naming_quirks "
                f"canonical, or entities_referenced names. Either correct "
                f"the description to match available grounding, or add "
                f"the supporting data to the artifact.",
                check_name=CHECK_NAME,
            )
