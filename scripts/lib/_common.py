"""Cross-script shared helpers.

The verbatim-quote check (validate.py), prose-drift check
(validate-research.py), and description-drift check (review-coverage.py)
must see identical source bytes under identical normalization or the
"confirmation against source" guarantee in `meta/conventions.md` breaks
silently. This module is the single implementation the three import.
"""

import hashlib
import html
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Strict YAML loader — rejects duplicate top-level mapping keys
# ---------------------------------------------------------------------------
#
# PyYAML's default ``SafeLoader`` silently uses the last occurrence of a
# duplicate mapping key. That's the failure mode that bit the Ryder build
# session: an Edit-tool old_string mismatch produced a research artifact
# with two ``credibility_notes:`` blocks; the loader silently used the
# trailing one (which was the OLD content), so the validator passed
# despite the new content being unreachable.
#
# ``StrictYAMLLoader`` overrides ``construct_mapping`` to raise
# ``yaml.constructor.ConstructorError`` (subclass of ``yaml.YAMLError``)
# on any duplicate key. Existing ``except yaml.YAMLError`` blocks at
# parse-step modules catch it for free; contributors see a clean error
# message naming the duplicate key + its line, instead of a silent
# "validator passed but the change didn't take" failure.
#
# All YAML reads in the repo should go through ``strict_yaml_load`` —
# manifest, schema, artifacts, frontmatter, scaffolders. Loading via
# ``yaml.safe_load`` directly bypasses the protection.

class StrictYAMLLoader(yaml.SafeLoader):
    """SafeLoader that raises on duplicate mapping keys instead of
    silently overwriting. Drop-in replacement for ``yaml.SafeLoader``."""
    pass


def _strict_construct_mapping(loader, node, deep=False):
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(
            None, None,
            f"expected a mapping node, but found {node.id}",
            node.start_mark)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictYAMLLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _strict_construct_mapping)


def strict_yaml_load(stream):
    """Project-wide YAML loader. Same shape as ``yaml.safe_load`` but
    raises ``yaml.YAMLError`` (specifically a ``ConstructorError``) on
    duplicate mapping keys, instead of silently using the last value.

    Parse-step modules already catch ``yaml.YAMLError`` and convert to
    fatal Issues, so this surfaces as a clean validator error rather
    than a Python traceback."""
    return yaml.load(stream, Loader=StrictYAMLLoader)


# Repo paths — computed from this file's location so scripts can be
# invoked from any cwd.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCES_DIR = REPO_ROOT / "sources"
MANIFEST_PATH = SOURCES_DIR / "manifest.yaml"
SCHEMA_PATH = REPO_ROOT / "meta" / "schema.yaml"


# Per-process caches.
_source_text_cache = {}             # Path -> extracted plain text or None
_extraction_type_cache = None       # rel-path str -> extraction_type str
_manifest_format_cache = None       # rel-path str -> format str
_schema_cache = None                # parsed meta/schema.yaml


def load_schema():
    """Parse meta/schema.yaml once per process and cache. All scripts
    that need schema data should import + call this rather than
    duplicating the open + safe_load + SCHEMA_PATH boilerplate.
    Errors loudly on parse failure or missing file (schema is
    foundational toolkit contract; absence is fatal)."""
    global _schema_cache
    if _schema_cache is None:
        with open(SCHEMA_PATH) as f:
            _schema_cache = strict_yaml_load(f)
    return _schema_cache


def content_type_dirs():
    """Return ``{type: dirname}`` mapping for content-node types,
    derived from each type's ``path`` field in the schema. Excludes
    ``meta`` and ``research-artifact`` (which have no ``path``)."""
    schema = load_schema()
    return {
        t: spec["path"]
        for t, spec in schema["types"].items()
        if isinstance(spec, dict) and "path" in spec
    }


def content_dirs():
    """Ordered list of content-directory names (people, organizations,
    documents, …). Convenience wrapper around ``content_type_dirs()``
    for callers that only need the directory names."""
    return list(content_type_dirs().values())


def content_node_types():
    """Set of content-node type names (person, organization, …).
    Derived from schema."""
    return frozenset(content_type_dirs().keys())


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
            entries = strict_yaml_load(f) or []
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
            entries = strict_yaml_load(f) or []
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
# Markdown helpers — pure functions for parsing node frontmatter and walking
# H2 sections. Imported by both the orchestrators and per-check modules
# under scripts/checks/, so checks don't have to import from validate.py
# (which would invert the layering).
# ---------------------------------------------------------------------------


def parse_frontmatter(text):
    """Parse YAML frontmatter from a markdown document. Returns
    ``(frontmatter_dict, body)`` or ``(None, None)`` on absent or
    malformed frontmatter. Body is the text after the closing ``---``
    delimiter.
    """
    if not text.startswith("---"):
        return None, None
    end = text.find("\n---", 3)
    if end < 0:
        return None, None
    try:
        fm = strict_yaml_load(text[3:end])
        return fm, text[end + 4:]
    except yaml.YAMLError:
        return None, None


# Topic-config — meta/topic/overview.md frontmatter declares the
# instance's `topic` (lowercase identifier) and `display_name` (rendered
# text used in section headers + agent prose). Cached per-process.
_topic_config_cache = None
_OVERVIEW_PATH = REPO_ROOT / "meta" / "topic" / "overview.md"


def load_topic():
    """Read meta/topic/overview.md frontmatter and return
    ``{topic, display_name}``. Cached per-process. Errors loudly on
    missing file or required fields — overview.md is required and
    validated by ``governance_files``; fork bootstrap goes through
    ``prompts/fork-init.md``.
    """
    global _topic_config_cache
    if _topic_config_cache is not None:
        return _topic_config_cache

    if not _OVERVIEW_PATH.exists():
        raise FileNotFoundError(
            f"meta/topic/overview.md is required for topic-config but is "
            f"missing at {_OVERVIEW_PATH}. If bootstrapping a fresh fork "
            f"target, run prompts/fork-init.md to generate it."
        )

    text = _OVERVIEW_PATH.read_text()
    fm, _ = parse_frontmatter(text)
    if fm is None:
        raise ValueError(
            "meta/topic/overview.md frontmatter could not be parsed."
        )

    for field in ("topic", "display_name"):
        if field not in fm:
            raise KeyError(
                f"meta/topic/overview.md frontmatter missing required "
                f"field {field!r}. The two topic-config fields (topic + "
                f"display_name) drive schema-field-rename + renderer "
                f"section-header substitution. See prompts/fork-init.md."
            )

    _topic_config_cache = {
        "topic": fm["topic"],
        "display_name": fm["display_name"],
    }
    return _topic_config_cache


# ---------------------------------------------------------------------------
# Manifest helpers — Wayback URL detection + manifest I/O.
# Schema's ``manifest_entry`` shape is the contract.
# ---------------------------------------------------------------------------

# A cited URL may already BE a Wayback snapshot (e.g. dead primary source
# whose only surviving copy is a Wayback capture). Auto-set archive_status
# bit 1 and derive wayback_date from the 14-char timestamp.
WAYBACK_URL_RE = re.compile(r"^https?://web\.archive\.org/web/(\d{8,14})/")


def wayback_url_date(url):
    """If URL is itself a Wayback snapshot, return its date (YYYY-MM-DD).
    Otherwise return None."""
    m = WAYBACK_URL_RE.match(url)
    if not m:
        return None
    ts = m.group(1)[:8]  # first 8 chars = YYYYMMDD
    return f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"


def load_manifest():
    """Load sources/manifest.yaml. Returns the entries list, or [] if the
    manifest is absent. Does NOT cache — callers needing repeated access
    should hold the returned list."""
    if not MANIFEST_PATH.exists():
        return []
    with open(MANIFEST_PATH) as f:
        return strict_yaml_load(f) or []


def save_manifest(entries):
    """Write entries back to sources/manifest.yaml. Sorts by URL for
    stable diffs; uses ``allow_unicode=True`` + ``width=9999`` so unicode
    characters survive and YAML doesn't fold long values into multi-line
    blocks."""
    entries.sort(key=lambda e: e.get("url", ""))
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        yaml.dump(entries, f, sort_keys=False, default_flow_style=False,
                  allow_unicode=True, width=9999)


def load_manifest_paths():
    """Return the set of ``path`` strings registered in
    ``sources/manifest.yaml``. Convenience wrapper around
    ``load_manifest()`` for callers that only need path-existence checks
    (validate-research.py + review-coverage.py both use this shape)."""
    return {e.get("path") for e in load_manifest() if e.get("path")}


def resolve_cli_path(arg_path):
    """Resolve a CLI-supplied path argument, error cleanly + exit 1 if
    it's missing or outside ``REPO_ROOT``. Used by validate.py /
    validate-research.py / review-coverage.py to convert raw Python
    ``FileNotFoundError`` / ``ValueError`` tracebacks into a one-line
    contributor-facing error before per-file iteration begins.

    Returns the resolved ``Path``. The orchestrators are CLI tools; a
    bad CLI arg is a user-error condition rather than an Issue the
    per-file iteration should try to report (the iteration can't even
    construct a Context for a path that doesn't exist).
    """
    p = Path(arg_path).resolve()
    if not p.exists():
        sys.exit(f"ERROR: path does not exist: {arg_path}")
    try:
        p.relative_to(REPO_ROOT)
    except ValueError:
        sys.exit(
            f"ERROR: path must be inside the repository "
            f"({REPO_ROOT}); got: {arg_path}"
        )
    return p


# ---------------------------------------------------------------------------
# Date parsing — shared by the chronological-ordering check
# (checks/chronological_tables.py) and the renderer's sort_by_date
# (build-from-research.py).
#
# Returns ``Optional[(year, month, day)]`` — None for unparseable /
# missing / placeholder inputs. Each consumer wraps differently:
#
#   - ``checks/chronological_tables.py`` treats None as "skip ordering
#     check + warn on unparseable cells".
#   - ``build-from-research.py::sort_by_date`` wraps with
#     ``or (9999, 0, 0)`` at the sort-key call site so unparseable rows
#     sort to the end without forcing the parser to invent a sentinel.
# ---------------------------------------------------------------------------

# Range separators between start and end dates in a single cell. Ordered
# longest-first so " — " (em-dash with surrounding spaces) consumes the
# spaces before bare "—" matches inside it.
_DATE_RANGE_SEPARATORS = (" – ", " — ", " to ", " - ", "–", "—", "-to-")

# Placeholder strings recognized as "no date" (case-insensitive). A row
# whose date cell is "TBD" or "ongoing" is intentionally undated; the
# validator skips ordering for it and the renderer sorts it last.
_DATE_PLACEHOLDERS = frozenset({
    "—", "-", "n/a", "undated", "tbd", "present", "ongoing", "",
})


def parse_date_tuple(s):
    """Return ``(year, month, day)`` tuple from a date string suitable
    for sort comparison, or ``None`` for empty / unparseable / placeholder
    inputs.

    Range cells take the leftmost date. Empty-left case (e.g.,
    ``"– 2021"`` — bracketed-end with unknown start) takes the right side
    so the row still sorts by its attested end date. Missing month / day
    default to 0, so ``"2004"`` < ``"2004-11"`` < ``"2004-11-14"`` under
    tuple comparison.
    """
    if not s:
        return None
    s = str(s).strip()
    if s.lower() in _DATE_PLACEHOLDERS:
        return None
    for sep in _DATE_RANGE_SEPARATORS:
        if sep in s:
            left, _, right = s.partition(sep)
            left = left.strip()
            right = right.strip()
            s = left if left else right
            break
    m = re.match(r"^(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?", s)
    if m:
        y = int(m.group(1))
        mo = int(m.group(2)) if m.group(2) else 0
        d = int(m.group(3)) if m.group(3) else 0
        return (y, mo, d)
    return None


# Extension → manifest ``format`` value. Coverage matches the schema's
# ``manifest_entry.format_values`` vocabulary (pdf / html / txt /
# transcript / audio / image / video). Unknown extensions fall back to
# ``html`` — intentional for web scraping where the source's extension
# is often absent or generic.
FORMAT_BY_EXT = {
    ".pdf": "pdf",
    ".html": "html",
    ".htm": "html",
    ".txt": "txt",
    ".md": "transcript",
    # Video extensions — schema format_values supports `video`.
    ".mp4": "video",
    ".m4v": "video",
    ".mov": "video",
    ".webm": "video",
    ".avi": "video",
    ".mkv": "video",
    # Audio extensions — schema format_values supports `audio`.
    ".mp3": "audio",
    ".wav": "audio",
    ".flac": "audio",
    ".aac": "audio",
    ".ogg": "audio",
    ".m4a": "audio",
    # Image extensions — schema format_values supports `image`.
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".tiff": "image",
    ".tif": "image",
    ".webp": "image",
    ".bmp": "image",
    ".heic": "image",
}


def format_from_path(path):
    """Return the manifest ``format`` value for a path's extension, or
    ``html`` for unknown extensions (fallback for web-scraping cases
    where the URL has no informative extension). Returns None for
    empty / falsy paths."""
    if not path:
        return None
    return FORMAT_BY_EXT.get(Path(path).suffix.lower(), "html")


def compute_sha256(file_path):
    """Stream-compute SHA256 of a file. Returns hex digest or None on
    read error. Shared between manifest.py (CLI archival) and the
    manifest_checksums validator check."""
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


# Content-node types the renderer (build-from-research.py) and the
# coverage reviewer (review-coverage.py) both support.
SUPPORTED_TYPES = frozenset({
    "document", "person", "event", "transcript",
    "media", "organization", "location",
    "finding", "investigation",
})


def schema_version_compat_messages(sv, compatible_with, current_version, *, prefix=""):
    """Return list of ``(level, message)`` tuples for schema_version
    compatibility violations. Caller wraps each tuple in its Issue
    class. Empty list when the value is valid, or when it's None
    (absence is the caller's required-field check, not this one).

    ``prefix`` lets template-shaped check sites prepend context (e.g.,
    "Template ") to error messages without forking the helper.
    """
    if sv is None:
        return []
    if not isinstance(sv, int) or isinstance(sv, bool):
        return [(
            "error",
            f"{prefix}schema_version must be an integer; got {sv!r} "
            f"({type(sv).__name__})",
        )]
    if sv not in compatible_with:
        return [(
            "error",
            f"{prefix}schema_version {sv} not in compatible_with "
            f"{compatible_with} (current schema version is {current_version}). "
            f"Migrate per meta/toolkit-notes/schema-migrations/.",
        )]
    return []


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
# Prose-drift tokenizer — used by validate-research.py's prose-drift
# check and by check-vocab.py (contributor pre-flight tool). Both must
# tokenize byte-for-byte the same way.
#
# Scope: ONLY the prose-drift tokenizer. review-coverage.py's
# ``extract_description_drift_tokens`` is a different algorithm
# (proper-noun + designator + quoted-string extraction for the
# description-drift check) and stays there.
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
# WHAT'S DELIBERATELY OUT. Any word that carries evidentiary weight,
# even common ones — investigative verbs (investigate, confirm, attest,
# established), reporting verbs (report, submit, publish, issue, signed),
# institutional / role nouns (intelligence, agency, office, director,
# civilian), testimony language (testify, sworn, witness, hearing),
# provenance / archival vocabulary (document, archive, primary, source).
# Three categories that look stoppable but stay content:
#   - Cardinal numbers ("one", "two", "three") — counting drift is
#     evidentiary drift even when the word is grammatically a determiner
#     ("investigated three cases" vs "investigated one case").
#   - "may" — collides with the month "May" after lowercasing; filtering
#     would mask month-attestation drift.
#   - Generic verbs ("said", "took", "made", "went", "got", "came" and
#     inflections) — paraphrase drift like "Stratton said" for source's
#     "Stratton stated" would pass silently if these were filtered.
# Filtering any of these would silently weaken drift detection for whole
# classes of evidentiary claims. The CONTENT_WORDS set in
# scripts/tests/test_stopwords.py codifies the prohibition.
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
    # Generic verbs ("said", "took", "made", "went", "got", "came" and
    # inflections) are deliberately NOT listed — see the WHAT'S
    # DELIBERATELY OUT block above. Listing them would mask paraphrase
    # drift across reporting-verb substitutions.
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
    # Strip trailing quote characters that the regex captured from
    # source-quoted phrases. The matched class `[a-z0-9\-']+` includes
    # the apostrophe so intra-word forms like "don't" survive — but the
    # same pattern keeps a trailing quote when a source-quoted phrase
    # like 'High' or America's UFO Mythology' decodes through YAML
    # single-quoted-scalar escaping. The trailing quote is grammatical
    # punctuation, never part of a word's identity; drop it.
    words = [w.rstrip("'") for w in words]
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


# ---------------------------------------------------------------------------
# Issue log
# ---------------------------------------------------------------------------
#
# Append-only YAML log of validator-emitted Issues + manual audit findings
# (Claude Web sessions, contributor reviews). One list entry per issue,
# fields on their own lines for readability. Orchestrators call
# append_issue_log() in main() after collecting their issue stream;
# audit by reading the log file directly (a fresh CLI session walks the
# YAML and reports patterns on demand — no aggregation script needed).

ISSUE_LOG_PATH = REPO_ROOT / "meta" / "toolkit-notes" / "issue-log.yaml"

_ISSUE_LOG_HEADER = """\
# Issue log — append-only record of validator-emitted Issues and manual
# audit findings (Claude Web / contributor reviews).
#
# One YAML list entry per issue. Fields:
#   ts         — ISO-8601 UTC timestamp
#   source     — "validator" for orchestrator-emitted, or
#                "web-audit-{node}-{date}" / "manual-{date}" for human-found
#   check      — for validator entries: the check_name. For manual entries:
#                "manual:{semantic-tag}" (free-text; promote frequent tags
#                to a documented list when patterns emerge)
#   phase      — orchestrator that emitted (validate / validate-research /
#                review-coverage), or "semantic" for manual entries
#   node       — repo-relative path of the file the issue concerns
#   node_type  — derived from path (person / organization / document /
#                event / transcript / media / location / finding /
#                research-artifact / governance / manifest)
#   severity   — pulled from Issue.level: "error" | "warn"
#   message    — Issue.message (validator) or contributor's prose
#                description (manual). Multi-line via | literal block.
#   tokens     — (optional) structured payload. Present when the check
#                carries data the human-readable message necessarily
#                truncates — e.g., the prose-drift check previews the
#                first 8 unmatched tokens and lands the full set here.
#                Greppable / consumable for retrospective audits.
#
# Validator entries append automatically (fixture / smoke-test paths
# whose basename starts with "__" are skipped). Manual entries:
# contributors add list items with the same shape after a Web audit /
# manual review. Audit by reading the file directly.

"""

_YAML_QUOTE_CHARS = set(":#[]{},&*!|>'\"%@`")


def _derive_node_type(path):
    """Return the node_type label for the issue log given a repo-
    relative path. Schema content-type name for content nodes;
    coarser bucket label (research-artifact / governance / manifest)
    for non-content paths."""
    s = str(path)
    if s.startswith("meta/research/"):
        return "research-artifact"
    if s.startswith("meta/"):
        return "governance"
    if s.startswith("sources/"):
        return "manifest"
    first = s.split("/", 1)[0]
    rev = {v: k for k, v in content_type_dirs().items()}
    return rev.get(first, "unknown")


def _yaml_quote_simple(val):
    """Single-quote a YAML scalar that contains metacharacters or has
    an ambiguous leading sigil. Returns the value unchanged otherwise.
    Used for the issue-log entry serialization — manual format keeps
    field order and forces | literal-block on the message field."""
    s = str(val)
    if not s:
        return "''"
    if any(c in _YAML_QUOTE_CHARS for c in s):
        return "'" + s.replace("'", "''") + "'"
    if s[0] in "-?":
        return "'" + s + "'"
    return s


def _format_issue_log_entry(entry):
    """Render an issue-log dict as a multi-line YAML list item with
    fixed field order and | literal-block on the message field."""
    out = [f"- ts: {entry['ts']}"]
    for key in ("source", "check", "phase", "node", "node_type"):
        out.append(f"  {key}: {_yaml_quote_simple(entry[key])}")
    out.append(f"  severity: {entry['severity']}")
    out.append("  message: |")
    for line in entry["message"].split("\n"):
        out.append(f"    {line}")
    if "tokens" in entry:
        # Inline-flow YAML list — readable at a glance, greppable.
        token_strs = [_yaml_quote_simple(t) for t in entry["tokens"]]
        out.append(f"  tokens: [{', '.join(token_strs)}]")
    return "\n".join(out)


def append_issue_log(issue, source="validator", phase="validate"):
    """Append one entry to ``meta/toolkit-notes/issue-log.yaml`` for
    the given Issue. Called by validator orchestrators in main() after
    issue collection. ``source`` and ``phase`` are set per call site;
    ``check`` / ``node`` / ``severity`` / ``message`` come from the
    Issue itself.

    Skips fixture / smoke-test paths (any path whose basename starts
    with ``__``) so synthetic test entries don't pollute the real log.
    Convention: fixture nodes use ``__smoke-`` / ``__fixture-`` slugs;
    real content nodes never start with ``__``.

    Creates the log file with the documentation header on first append
    if it doesn't already exist (defensive — fresh forks may not have
    the committed initial file)."""
    path_str = str(issue.path)
    basename = path_str.rsplit("/", 1)[-1]
    if basename.startswith("__"):
        return  # fixture / smoke-test path; not real content

    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "check": issue.check_name or "unknown",
        "phase": phase,
        "node": path_str,
        "node_type": _derive_node_type(issue.path),
        "severity": issue.level,
        "message": issue.message,
    }
    if issue.tokens:
        # Structured payload (e.g., full unmatched-token list on prose-
        # drift warnings); message preview is truncated, full set lands
        # here for retrospective audit + grep.
        entry["tokens"] = list(issue.tokens)
    ISSUE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not ISSUE_LOG_PATH.exists()
    with open(ISSUE_LOG_PATH, "a") as f:
        if new_file:
            f.write(_ISSUE_LOG_HEADER)
        f.write(_format_issue_log_entry(entry))
        f.write("\n\n")
