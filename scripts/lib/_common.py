"""Cross-script shared helpers for source extraction and quote normalization.

Three scripts share a load-bearing cross-check guarantee per
`meta/conventions.md`: the verbatim-quote check (validate.py) fails any
commit where a quote's text does not appear in the extracted source.
For that guarantee to hold, the prose-drift check (validate-research.py)
and description-drift check (review-coverage.py) must tokenize against
the SAME extracted text under the SAME normalization. Drift between
the three breaks the guarantee silently — pre-commit gates pass while
the checks operate on different bytes.

Earlier versions duplicated these helpers inline across the three
scripts with `# Mirror validate.py exactly` comments. The duplication
drifted in practice as features shipped to validate.py without
parallel updates (HTML entity decode; YouTube caption timestamp
strip; OCR-scan / extraction-lossy `.txt` sibling logic). Centralizing
here makes lockstep mechanical instead of comment-discipline-based.

Investigator-facing content layers (`/people/`, `/organizations/`,
`/documents/`, `/events/`, `/transcripts/`, `/media/`, `/locations/`,
`/findings/`, `/sources/`) remain flat — the flatness rule is about
investigator UX on browseable content, not tooling. Research artifacts
live under `/meta/research/` (governance / structured-data backing
tier per `meta/conventions.md`), not the content tier.
"""

import html
import re
import subprocess
from pathlib import Path

import yaml


# Repo paths — computed from this file's location so scripts can be
# invoked from any cwd.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCES_DIR = REPO_ROOT / "sources"
MANIFEST_PATH = SOURCES_DIR / "manifest.yaml"


# Per-process caches.
_source_text_cache = {}             # Path -> extracted plain text or None
_extraction_type_cache = None       # rel-path str -> extraction_type str
_manifest_format_cache = None       # rel-path str -> format str


def _load_extraction_types():
    """Build a {path: extraction_type} map from sources/manifest.yaml.

    Lazy + cached. Returns an empty dict on parse failure or missing
    manifest (extract_source_text falls back to default behavior).
    """
    global _extraction_type_cache
    if _extraction_type_cache is not None:
        return _extraction_type_cache
    _extraction_type_cache = {}
    if not MANIFEST_PATH.exists():
        return _extraction_type_cache
    try:
        with open(MANIFEST_PATH) as f:
            entries = yaml.safe_load(f) or []
    except yaml.YAMLError:
        return _extraction_type_cache
    if not isinstance(entries, list):
        return _extraction_type_cache
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        et = entry.get("extraction_type")
        if path and et:
            _extraction_type_cache[path] = et
    return _extraction_type_cache


def manifest_format(rel_path):
    """Return the manifest's `format` value for a source path (relative to
    sources/), or None if the path or the field is absent. Lazy + cached.

    Used to distinguish binary-by-design sources (image/video/audio) from
    text-extractable formats when the verbatim-quote check needs to frame
    its warning accurately — pdftotext didn't fail on a .mp4; it was
    never going to run.
    """
    global _manifest_format_cache
    if _manifest_format_cache is not None:
        return _manifest_format_cache.get(rel_path)
    _manifest_format_cache = {}
    if not MANIFEST_PATH.exists():
        return None
    try:
        with open(MANIFEST_PATH) as f:
            entries = yaml.safe_load(f) or []
    except yaml.YAMLError:
        return None
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        fmt = entry.get("format")
        if path and fmt:
            _manifest_format_cache[path] = fmt
    return _manifest_format_cache.get(rel_path)


# HTML inline tags — replaced with empty string during cleaning so mid-word
# interleave (e.g., `Army<span dir="RTL">'</span>s liaison`) collapses back
# to the intended word. Block-level and unknown tags are replaced with
# whitespace to preserve word boundaries across paragraph / heading / list
# breaks.
_HTML_INLINE_TAGS = (
    r"span|b|i|em|strong|u|a|small|code|sub|sup|cite|q|mark|del|ins|"
    r"abbr|dfn|samp|kbd|var|bdi|bdo|s|wbr|ruby|rt|rp|time|data|meter|"
    r"progress|output|picture|tt|font"
)


# ---------------------------------------------------------------------------
# Markdown section extraction — used by node-body validators / checks for
# walking H2 sections and pulling their text. Pure functions: text in,
# structure out. Lifted to lib/_common.py during C11 session-2 migration
# (2026-05-05) so per-check modules in scripts/checks/ can consume them
# directly without importing from validate.py (which would invert the
# layering — checks shouldn't import from the orchestrator).
# ---------------------------------------------------------------------------


def extract_h2_sections(text):
    """Return the list of H2 heading titles (the text after ``## ``) in
    document order. Trailing whitespace stripped per heading. Used as
    the index into ``extract_section`` and for required-section walks.
    """
    return re.findall(r"^## (.+?)\s*$", text, re.MULTILINE)


def extract_section(text, title):
    """Return the body text of the named H2 section (everything between
    ``## {title}`` and the next ``## `` heading or end of document).
    None if the section is absent. Title match is exact (case-sensitive,
    no normalization).
    """
    pattern = re.compile(rf"^## {re.escape(title)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None
    start = match.end()
    next_h2 = re.search(r"^## ", text[start:], re.MULTILINE)
    end = start + next_h2.start() if next_h2 else len(text)
    return text[start:end]


def clean_html_for_text(raw):
    """Strip HTML tags and decode entities so the raw bytes of an archived
    .html file can be substring-matched against a verbatim quote. Handles:
      - script/style bodies removed (avoid dumping JS/CSS into the text pool)
      - inline tags stripped with empty replacement (mid-word interleave)
      - block / unknown tags stripped with whitespace (word-boundary preserve)
      - HTML entities decoded last
    """
    raw = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(rf"</?(?:{_HTML_INLINE_TAGS})(?:\s[^>]*)?>", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    return raw


def extract_source_text(source_path):
    """Extract plain text from a source file. Returns None if unavailable.
    Cached for the duration of one validator run.

    For PDFs flagged with a non-text-native `extraction_type` in
    `sources/manifest.yaml` (`ocr-scan`, `extraction-lossy`), prefers a
    same-stem `.txt` sibling (contributor-produced clean transcription)
    over pdftotext output. The PDF's text layer was either OCR'd from
    scans or extraction-lossy at the generation layer; the sibling
    restores the document's actual content as visually verified against
    the PDF. Falls back to pdftotext if no sibling exists.

    Post-extraction normalization (applied uniformly across formats):
    line-break hyphens are merged so PDF line-wrap of hyphenated
    compounds — `Geospatial-\\nIntelligence`, `All-\\nDomain`,
    `trans-\\nmedium` — collapses back to one token before any
    consumer tokenizes or substring-matches the bytes. Without this,
    `validate.py`'s verbatim-quote check (which re-runs the same merge
    in `normalize_for_compare`) and `validate-research.py`'s
    prose-drift tokenizer would diverge: substring-match would resolve
    the compound; tokenization would split it into a trailing-hyphen
    fragment plus an orphan word that never matches a contributor's
    canonical-form prose token. Centralizing the merge here keeps the
    three lockstep helpers (verbatim-quote, prose-drift, description-
    drift) seeing the same bytes per `meta/conventions.md`'s lockstep
    principle. Idempotent for `normalize_for_compare`, which still
    applies its own merge as defense-in-depth on quote text.

    Supported extensions:
      - .pdf            pdftotext (or .txt sibling for non-text-native)
      - .html / .htm    read + clean_html_for_text (tag strip + entity decode)
      - .txt / .md      raw read
      - .json           raw read (e.g., archived X.com tweet payloads —
                        the JSON contains tweet body text as string fields
                        that the tokenizer can pull meaningful tokens from)
    Returns None for any other extension or extraction failure.
    """
    if source_path in _source_text_cache:
        return _source_text_cache[source_path]
    result = None
    suffix = source_path.suffix.lower()
    if suffix == ".pdf":
        # For PDFs whose default extraction is unreliable (extraction_type
        # is non-text-native), prefer a same-stem .txt sibling.
        try:
            rel_path = str(source_path.relative_to(SOURCES_DIR))
        except ValueError:
            rel_path = None
        et = _load_extraction_types().get(rel_path) if rel_path else None
        used_sibling = False
        if et and et != "text-native":
            sibling = source_path.with_suffix(".txt")
            if sibling.exists():
                try:
                    result = sibling.read_text(encoding="utf-8", errors="replace")
                    used_sibling = True
                except OSError:
                    pass  # fall through to pdftotext
        if not used_sibling:
            try:
                proc = subprocess.run(
                    ["pdftotext", "-layout", str(source_path), "-"],
                    capture_output=True, text=True, timeout=60,
                )
                if proc.returncode == 0:
                    result = proc.stdout
            except (FileNotFoundError, subprocess.TimeoutExpired):
                result = None
    elif suffix in (".html", ".htm"):
        try:
            result = clean_html_for_text(source_path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            result = None
    elif suffix in (".txt", ".md", ".json"):
        try:
            result = source_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            result = None
    if result is not None:
        result = re.sub(r"-\s+", "-", result)
    _source_text_cache[source_path] = result
    return result


def normalize_for_compare(text):
    """Normalize text for substring comparison.

    Handles common PDF-extraction + Markdown-rendering artifacts so a
    quote from an artifact substring-matches its source bytes regardless of:
      - HTML entities in source (`&rsquo;`, `&ldquo;`, `&mdash;` -> chars)
      - smart quotes (curly -> ASCII straight)
      - em / en dashes (-> ASCII hyphen, then stripped)
      - non-breaking spaces (-> regular space)
      - YouTube caption timestamp markers ([MM:SS] / [H:MM:SS]) stripped
      - Markdown block-quote line-prefix markers (`> `) stripped
      - hyphens stripped uniformly (PDF line-wrap, compound, em-dash)
      - whitespace collapsed to single space
    """
    # HTML entities -> their character equivalents. Pre-existing contributor
    # pastes of raw HTML bytes into quote text continue to match; source
    # text has already been decoded in clean_html_for_text so this is a
    # no-op on that side.
    text = html.unescape(text)
    # Smart quotes -> straight
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    # Em/en dash -> hyphen (will be stripped next)
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    # Non-breaking space -> space
    text = text.replace("\u00a0", " ")
    # YouTube-caption timestamp markers — strip [MM:SS] and [H:MM:SS].
    # transcribe.py prefixes every caption line with a timing marker
    # (typically every 2-5 seconds); those are caption-file-format
    # metadata, not content. Stripping at normalization lets contributors
    # anchor a quote with a single leading [MM:SS] for reader navigation
    # without preserving every intermediate caption tick inside the quote
    # body. Both source and quote go through the same normalization so
    # match integrity is preserved.
    text = re.sub(r"\[\d+:\d+(?::\d+)?\]", "", text)
    # Markdown block-quote markers at line start — strip `> ` / `>` prefix
    # so multi-line block quotes normalize to their underlying content.
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    # Collapse hyphen+whitespace to just hyphen, so PDF line-wrap "brand-\nnew"
    # and hand-written "brand-new" normalize the same way after hyphen-strip
    text = re.sub(r"-\s+", "-", text)
    # Strip all hyphens uniformly (see docstring)
    text = text.replace("-", "")
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Prose-drift tokenizer — used by validate-research.py's prose-drift check
# and by check-vocab.py (the contributor pre-flight tool). Centralized here
# (2026-05-05) for the same lockstep reason `extract_source_text` and
# `normalize_for_compare` were centralized 2026-05-01: multiple scripts
# must agree on tokenization byte-for-byte, and prior duplication was
# contributor-discipline-based with a real drift surface.
#
# Scope: ONLY the prose-drift tokenizer. review-coverage.py's
# `extract_description_drift_tokens` is a DIFFERENT algorithm
# (proper-noun + designator + quoted-string extraction for the
# description-drift check) and lives there; the naming was deliberately
# distinguished to prevent future "let's deduplicate" mistakes.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Stopwords for the prose-drift check — function words filtered before
# tokens compare across prose ↔ source. Regression-guarded by
# scripts/tests/test_stopwords.py (gate 2/6 in pre-commit).
#
# WHY THIS EXISTS. The prose-drift check pools significant tokens from
# source and warns on prose tokens not in the pool. Function words
# ("the", "of", "is") appear in essentially every English document — they
# carry no signal because they're never the variable. Including them
# produces noise that drowns out real drift warnings. Filtering them out
# raises the signal-to-noise ratio so each remaining warning is meaningful
# enough for a contributor to review per-case.
#
# WHAT'S IN. Function words only — articles, pronouns, auxiliaries,
# modals, prepositions, conjunctions, negations / degree intensifiers,
# determiners / quantifiers. Every entry is content-blind by design.
# Entries shorter than 3 characters are NOT listed — the tokenizer's
# regex+length filter (`r"[a-z0-9][a-z0-9\-']+"` + `len >= 3`) already
# excludes them, so listing "a" / "of" / "is" / "be" here would be
# belt-and-suspenders. STOPWORDS contains only 3+ char entries that
# would otherwise pass the length filter and need explicit filtering.
#
# WHAT'S DELIBERATELY OUT. Any word that carries evidentiary weight, even
# common ones — investigative verbs (investigate, confirm, attest,
# established), reporting verbs (report, submit, publish, issue, signed),
# institutional / role nouns (intelligence, agency, office, director,
# civilian), testimony language (testify, sworn, witness, hearing),
# provenance / archival vocabulary (document, archive, primary, source).
# Plus three deliberate exclusions tightened during the 2026-05-05 audit:
#   - Cardinal numbers ("one", "two", "three") — counting drift is
#     evidentiary drift even when the word is grammatically a determiner
#     ("investigated three cases" vs "investigated one case").
#   - "may" — collides with the month "May" after lowercasing; filtering
#     would mask month-attestation drift.
#   - Generic verbs ("said", "took", "made", "went", "got", "came", "go",
#     and their inflections) — were previously a category here. Empirical
#     audit surfaced 6 real word-form drift cases when removed (took/take
#     tense substitutions, said/stated paraphrases). Filtering them
#     enabled the very paraphrase drift class the check is designed to
#     catch. Now: prose using a generic verb warns when source uses a
#     different verb. Standard prose-drift discipline applies.
# Filtering any of these would silently weaken drift detection for whole
# classes of evidentiary claims. The CONTENT_WORDS set in
# scripts/tests/test_stopwords.py codifies this prohibition so it
# survives contributor turnover.
#
# KNOWN LIMITATIONS — architectural, not bandaid-able by tuning STOPWORDS.
# These are real classes of drift that the prose-drift check cannot catch
# regardless of how the stopword list is configured (each filtered token
# is a function word that genuinely carries no content; a contributor
# substitution within the category produces no token-level signal):
#   - Negation flipping ("did not investigate" ↔ "did investigate") —
#     "not" / "never" are filtered, so polarity reversal passes
#     trivially.
#   - Modal flipping ("might investigate" ↔ "will investigate") —
#     modals are filtered, so certainty changes pass too.
#   - Quantifier flipping ("all cases" ↔ "some cases") — "all" / "some" /
#     "every" filtered.
#   - Paraphrase preserving vocabulary — same tokens rearranged into a
#     different claim.
# All caught only by Phase III semantic review, not by the prose-drift
# check. The trade-off is deliberate: a vocabulary-comparison check is
# deterministic and dependency-free; semantic comparison would need NLP
# machinery and produce nondeterministic results.
#
# ADDITION DISCIPLINE. A new STOPWORDS entry must be:
#   (a) a function word, not a content word — test_stopwords.py enforces
#       this against CONTENT_WORDS and will fail the pre-commit gate if
#       a content word is added; AND
#   (b) justified in the commit message with the specific contributor
#       pattern that motivated the addition (e.g., "audit found `however`
#       triggering as drift across N artifacts").
# Adding a content word here to silence false-positive warnings is the
# wrong fix — rewrite the prose to use source vocabulary instead, or
# capture the variance as evidentiary data (naming_quirks / rumors /
# a new quote).
# ---------------------------------------------------------------------------

STOPWORDS = {
    # Articles (1–2 char articles "a", "an" are filtered by the
    # tokenizer's len>=3 floor, so only "the" needs explicit listing).
    "the",
    # Pronouns (3+ chars only — "he", "it", "we", "my" filtered by length).
    "she", "they", "you", "his", "her", "their",
    "its", "our", "your", "this", "that", "these", "those", "who",
    "whom", "whose", "which", "what",
    # Auxiliaries (3+ chars — "is", "be", "am", "do" filtered by length).
    "was", "are", "were", "been", "being",
    "have", "has", "had", "does", "did", "done",
    # Modals — known limitation: certainty / possibility flips ("may"
    # vs "will" vs "must") pass the check trivially. Caught by Phase III.
    # NOTE: "may" deliberately excluded — collides with month "May" after
    # lowercasing, which IS content.
    "will", "would", "can", "could", "should", "might", "must", "shall",
    # Prepositions (3+ chars only — "of", "in", "on", "at", "to", "by",
    # "as" filtered by length).
    "from", "for", "with",
    "into", "onto", "upon", "off", "out", "over", "under", "above",
    "below", "between", "among", "through", "during", "within",
    "without", "against", "about", "across", "after", "before", "behind",
    # Conjunctions (3+ chars — "or", "if", "so" filtered by length).
    "and", "but", "because", "since", "until",
    "unless", "when", "where", "while", "although", "though", "than",
    "yet", "whether",
    # Negations / degree — known limitation: polarity / degree flips
    # pass the check trivially. Caught by Phase III.
    "not", "never", "also", "then", "now", "just", "only", "even",
    "else", "still", "already", "ever", "again", "very", "too",
    "quite", "rather", "much", "more", "most", "less", "least",
    # Determiners / quantifiers. Cardinal numbers ("one", "two", "three")
    # deliberately excluded — they carry counting content (1-vs-3-cases
    # drift is real evidentiary drift), even when grammatically used as
    # determiners. Universal/existential quantifiers ("all", "every",
    # "any") known-limitation class with negation flipping.
    "some", "any", "all", "each", "every", "both", "either", "neither",
    "other", "another", "same", "such", "own",
    "here", "there",
    # Generic verbs deliberately NOT filtered (was previously a category
    # here; removed 2026-05-05 after empirical audit). Filtering "said"
    # / "took" / "made" / "went" / "got" / "came" enabled paraphrase
    # drift the check is designed to catch — "Stratton said" paraphrasing
    # source's "Stratton stated" passed silently because both verbs
    # collapsed to filtered tokens. Now: prose using a generic verb
    # warns when source uses a different verb. Standard prose-drift
    # discipline applies (rewrite to source morphology, or document the
    # variance).
}


# Cache source-file tokens per process so a multi-artifact or multi-entry
# run doesn't re-tokenize the same file N times.
_source_token_cache = {}


def extract_significant_tokens(text):
    """Return a set of significant tokens: lowercase words, ≥3 chars,
    excluding STOPWORDS. Preserves intra-word hyphens (so `f/a-18f`,
    `cvn-68`, `world-famous` survive). Strips possessive `'s` suffix
    (so `fravor's` → `fravor`) — possessive forms are noise against
    source text that typically uses first-person `my` / `I`. Strips
    backtick-bracket repo-path wraps (they're identifiers, not
    source-attested content) and markdown emphasis characters.
    """
    if not text:
        return set()
    # HTML entities -> character equivalents. Symmetric with validate.py
    # normalize_for_compare: pre-existing contributor pastes of raw HTML
    # entity bytes in prose ("department&#39;s") tokenize the same way as
    # the cleaned source ("department's") after both sides are decoded.
    # No-op on source text, which has already been decoded upstream in
    # clean_html_for_text.
    text = html.unescape(str(text))
    text = re.sub(r"\[`/[^`]+`\]", "", text)
    # Strip markdown emphasis / code-fence chars; replace with space so
    # underscore-separated identifiers (`period_start`, `FY_2021`) don't
    # collapse into a single unmatchable token. Emphasis markers always
    # sit at word boundaries, so replacing with space is semantically
    # identical to stripping for the emphasis case.
    text = re.sub(r"[*_`]", " ", text)
    # Typographic-dash handling diverges from the verbatim-quote check
    # by design. The verbatim-quote check is substring-matching quote
    # text — there, em-dash and en-dash both normalize to ASCII hyphen
    # so source "F–18" and prose "F-18" substring-match. The prose-drift check is
    # TOKENIZING — different use case. Em-dash (U+2014) is a sentence-
    # level word boundary in modern English typography ("NRO—reservist
    # capacity" is three words, not two), so we map it to a space
    # before tokenization; a greedy regex over hyphens would otherwise
    # merge it into a single token "nro-reservist" that never matches
    # the standalone prose token "reservist". En-dash (U+2013) stays
    # mapped to ASCII hyphen because it legitimately joins compounds
    # and ranges ("F–18", "2004–2023").
    text = text.replace("—", " ").replace("–", "-")
    text = text.lower()
    words = re.findall(r"[a-z0-9][a-z0-9\-']+", text)
    # Strip trailing possessive `'s` to collapse "fravor" ↔ "fravor's".
    # (Leaves intra-word apostrophes alone: "don't" stays "don't".)
    words = [re.sub(r"'s$", "", w) for w in words]
    return {w for w in words if len(w) >= 3 and w not in STOPWORDS}


def load_source_tokens(source_rel_path):
    """Load and tokenize a source file. source_rel_path is relative to
    sources/ (matches the manifest.yaml and artifact source.path shape).
    Cached per-process. Returns a set of significant tokens, or None if the
    source is missing / unextractable.
    """
    if source_rel_path in _source_token_cache:
        return _source_token_cache[source_rel_path]
    source_abs = SOURCES_DIR / source_rel_path
    if not source_abs.exists():
        _source_token_cache[source_rel_path] = None
        return None
    text = extract_source_text(source_abs)
    if text is None:
        _source_token_cache[source_rel_path] = None
        return None
    tokens = extract_significant_tokens(text)
    _source_token_cache[source_rel_path] = tokens
    return tokens
