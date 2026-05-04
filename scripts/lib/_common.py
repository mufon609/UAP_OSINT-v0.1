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
`/findings/`, `/research/`, `/sources/`) remain flat — the flatness
rule is about investigator UX on browseable content, not tooling.
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
