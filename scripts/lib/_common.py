"""Cross-script shared helpers.

The verbatim-quote check (validate.py), prose-drift check
(validate-research.py), and description-drift check (review-coverage.py)
must see identical source bytes under identical normalization or the
"confirmation against source" guarantee in `meta/conventions.md` breaks
silently. This module is the single implementation the three import.
"""

import hashlib
import html
import os
import re
import subprocess
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Strict YAML loader — rejects duplicate top-level mapping keys
# ---------------------------------------------------------------------------
#
# PyYAML's default ``SafeLoader`` silently uses the last occurrence of a
# duplicate mapping key. In a repo where YAML is hand-edited, patched via
# string-replace tooling, or merged across branches, a file can land with
# two mappings of the same name; SafeLoader picks the trailing one without
# warning, masking the earlier write. Validators then read the wrong block
# and pass under stale content.
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
RESEARCH_DIR = REPO_ROOT / "meta" / "research"
SCHEMA_PATH = REPO_ROOT / "meta" / "schema.yaml"
SCHEMA_RESEARCH_ARTIFACT_PATH = REPO_ROOT / "meta" / "schema-research-artifact.yaml"


# Per-process caches.
_source_text_cache = {}             # Path -> extracted plain text or None
_extraction_type_cache = None       # rel-path str -> extraction_type str
_manifest_format_cache = None       # rel-path str -> format str
_schema_cache = None                # parsed schema (merged)


def load_schema():
    """Parse the schema once per process and cache. Composes two files:
    ``meta/schema.yaml`` (main spec) and ``meta/schema-research-artifact.yaml``
    (the research-artifact subspec). The latter's top-level keys are
    spliced into ``schema["types"]["research-artifact"]`` so callers
    see a single merged dict. Errors loudly on parse failure or
    missing files (schema is foundational toolkit contract; absence
    is fatal)."""
    global _schema_cache
    if _schema_cache is None:
        with open(SCHEMA_PATH) as f:
            schema = strict_yaml_load(f)
        with open(SCHEMA_RESEARCH_ARTIFACT_PATH) as f:
            schema["types"]["research-artifact"] = strict_yaml_load(f)
        _schema_cache = schema
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


def entity_type_names():
    """Set of entity-layer type names per the three-layer evidentiary
    architecture (see meta/conventions.md). Derived from schema's
    ``architecture_layers.entity`` list — the directional-contract
    checks (entity_no_finding_or_investigation_refs,
    finding_source_in_entity_node) gate on this so adding a new entity
    type is a one-line schema edit."""
    return frozenset(load_schema()["architecture_layers"]["entity"])


def entity_type_dirs():
    """Set of entity-layer directory names (people, organizations,
    documents, events, transcripts, media, locations). Convenience
    for callers that key by directory rather than type name (e.g.,
    ``target_node`` strings parsed from research artifacts)."""
    types = entity_type_names()
    dir_map = content_type_dirs()
    return frozenset(dir_map[t] for t in types if t in dir_map)


def iter_artifacts(entries):
    """Yield ``(entry, artifact)`` pairs across every URL entry's
    ``artifacts`` list. Centralizes the nested-iteration pattern that
    every manifest consumer needs for the URL → artifacts nesting. The
    entry carries URL-level state (url, status, archive_status,
    wayback_date); the artifact carries per-rendering fields (path,
    format, archived_date, extraction_type, transcript_provenance, note).
    """
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for artifact in entry.get("artifacts") or []:
            if isinstance(artifact, dict):
                yield entry, artifact


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
    for _, artifact in iter_artifacts(entries):
        path = artifact.get("path")
        et = artifact.get("extraction_type")
        if path and et:
            _extraction_type_cache[path] = et
    return _extraction_type_cache


# Manifest formats whose sources are binary-by-design — no text layer
# to extract, so the verbatim-quote check / Phase III coverage / etc.
# skip text-extraction paths for these and frame any "missing text"
# observation as expected rather than as a failure.
BINARY_FORMATS = frozenset({"image", "video", "audio"})


def manifest_format(rel_path):
    """Return the manifest's `format` value for a source path (relative to
    sources/), or None if the path or the field is absent. Lazy + cached.

    Used to distinguish binary-by-design sources (per BINARY_FORMATS)
    from text-extractable formats when the verbatim-quote check needs
    to frame its warning accurately — pdftotext didn't fail on a .mp4;
    it was never going to run.
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
    for _, artifact in iter_artifacts(entries):
        path = artifact.get("path")
        fmt = artifact.get("format")
        if path and fmt:
            _manifest_format_cache[path] = fmt
    return _manifest_format_cache.get(rel_path)


# HTML inline tags — replaced with empty string during cleaning so mid-word
# interleave (e.g., `Army<span dir="RTL">'</span>s liaison`) collapses back
# to the intended word. Block-level and unknown tags are replaced with
# whitespace to preserve word boundaries across paragraph / heading / list
# breaks.
#
# Only true text-formatting inline elements belong here. Standalone-datum
# phrasing elements — `time` (datelines/timestamps), `data`, `meter`,
# `progress`, `output`, `picture` — are deliberately EXCLUDED: their content
# is a discrete datum, never a mid-word continuation, and HTML routinely sets
# them flush against adjacent text (e.g. a byline `<span>` immediately
# followed by a dateline `<time>`). Empty-stripping them concatenates the two
# ("LESLIE KEAN" + "DEC. 16, 2017" -> "KEANDEC"); the whitespace branch keeps
# the word boundary. This (HTML) and `_strip_pdf_page_number_lines` (PDF) both
# remove source-presentation noise once at the extraction layer, so the three
# source-grounded checks (verbatim-quote, prose-drift, description-drift) see
# clean bytes with no per-check normalization.
_HTML_INLINE_TAGS = (
    r"span|b|i|em|strong|u|a|small|code|sub|sup|cite|q|mark|del|ins|"
    r"abbr|dfn|samp|kbd|var|bdi|bdo|s|wbr|ruby|rt|rp|tt|font"
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
    ``the /fork-init skill``.
    """
    global _topic_config_cache
    if _topic_config_cache is not None:
        return _topic_config_cache

    if not _OVERVIEW_PATH.exists():
        raise FileNotFoundError(
            f"meta/topic/overview.md is required for topic-config but is "
            f"missing at {_OVERVIEW_PATH}. If bootstrapping a fresh fork "
            f"target, run the /fork-init skill to generate it."
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
                f"section-header substitution. See the /fork-init skill."
            )

    _topic_config_cache = {
        "topic": fm["topic"],
        "display_name": fm["display_name"],
    }
    return _topic_config_cache


def topic_substitute(s):
    """Substitute the ``{topic_display_name}`` placeholder in ``s`` with
    the current topic's ``display_name`` from ``meta/topic/overview.md``.
    Symmetric to the renderer's runtime composition of section headers
    via ``load_topic()`` — consumers reading schema strings that carry
    topic-bound section names (``required_sections``, header templates)
    route through this helper so schema stays topic-neutral and the
    substitution happens at validation/render time. Non-string inputs
    pass through unchanged."""
    if not isinstance(s, str) or "{topic_display_name}" not in s:
        return s
    return s.replace("{topic_display_name}", load_topic()["display_name"])


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
    """Write entries back to sources/manifest.yaml in their current order.

    Does NOT globally re-sort. Re-sorting on every write churned unrelated
    entries — a one-entry add produced a multi-entry diff whenever the file
    had drifted from sorted order. ``manifest.py`` ``cmd_add`` instead inserts
    a new URL at its URL-sorted position (the only operation that adds an
    entry), so the canonical URL order is maintained with a single-entry diff
    and existing entries never move. ``allow_unicode=True`` + ``width=9999``
    keep unicode intact and stop YAML folding long values into multi-line
    blocks.

    Atomic write: serialize to a same-directory temp file then
    ``os.replace`` onto the destination. A crash or interrupted write
    leaves the previous manifest intact; the rename is atomic on POSIX
    so concurrent readers never see a half-written file.
    """
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST_PATH.with_suffix(MANIFEST_PATH.suffix + ".tmp")
    try:
        with open(tmp, "w") as f:
            yaml.dump(entries, f, sort_keys=False, default_flow_style=False,
                      allow_unicode=True, width=9999)
        os.replace(tmp, MANIFEST_PATH)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def load_manifest_paths():
    """Return the set of ``path`` strings registered in
    ``sources/manifest.yaml`` — across every URL's ``artifacts`` list.
    Convenience wrapper for callers that only need path-existence
    checks (validate-research.py + review-coverage.py both use this
    shape)."""
    return {
        a.get("path") for _, a in iter_artifacts(load_manifest())
        if a.get("path")
    }


def load_source_to_artifacts_index():
    """Return ``{source_path: [target_node, ...]}`` mapping every source
    path cited in an ENTITY-type research artifact's ``primary_sources[]``
    to the list of target nodes that cite it.

    Entity types only — finding / investigation / meta artifacts are
    excluded since they're the consumers, not the canonical-fact homes.
    Per ``meta/conventions.md`` "Three-layer evidentiary architecture",
    findings DUPLICATE primary-source content from entity nodes; the
    entity node is updated first. The
    ``finding_source_in_entity_node`` check uses this index to enforce
    that contract mechanically.

    Loaded once at orchestrator entry (in ``main()``) and passed via
    ``BaseContext.source_to_artifacts``; fork-propagated to every worker.
    One sequential YAML parse pass over ``meta/research/*.yaml`` —
    ``~100ms`` total at current corpus size, amortized across the full
    validate-research.py run.
    """
    index = defaultdict(list)
    if not RESEARCH_DIR.is_dir():
        return dict(index)
    entity_dirs = entity_type_dirs()
    for path in sorted(RESEARCH_DIR.glob("*.yaml")):
        try:
            with open(path) as f:
                data = strict_yaml_load(f)
        except (yaml.YAMLError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        target_node = data.get("target_node") or ""
        if not isinstance(target_node, str) or "/" not in target_node:
            continue
        type_dir = target_node.split("/", 1)[0]
        # Positive entity-layer gate per schema's architecture_layers.
        # Synthesis layer (findings, investigations) consumes facts;
        # governance (meta) is not evidentiary.
        if type_dir not in entity_dirs:
            continue
        for ps in (data.get("primary_sources") or []):
            if isinstance(ps, dict):
                src = ps.get("path")
                if isinstance(src, str) and src:
                    index[src].append(target_node)
    return dict(index)


def load_synthesis_slugs():
    """Return ``{'finding': frozenset(slugs), 'investigation': frozenset(slugs)}``
    — the slugs of every finding / investigation node, parsed from research
    artifacts' ``target_node`` (``findings/<slug>`` / ``investigations/<slug>``).

    Mirrors ``load_source_to_artifacts_index()`` (one sequential pass over
    ``meta/research/*.yaml`` at orchestrator entry, exposed via
    ``BaseContext.synthesis_slugs``). Consumed by the directional checks to
    catch a *bare-slug* prose reference to a finding / investigation node
    ("the <slug> finding") — the violation the ``/findings/`` //
    ``/investigations/`` path needles miss.
    """
    slugs = {"finding": set(), "investigation": set()}
    if not RESEARCH_DIR.is_dir():
        return {k: frozenset(v) for k, v in slugs.items()}
    for path in sorted(RESEARCH_DIR.glob("*.yaml")):
        try:
            with open(path) as f:
                data = strict_yaml_load(f)
        except (yaml.YAMLError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        target_node = data.get("target_node") or ""
        if not isinstance(target_node, str) or "/" not in target_node:
            continue
        type_dir, _, slug = target_node.partition("/")
        if type_dir == "findings" and slug:
            slugs["finding"].add(slug)
        elif type_dir == "investigations" and slug:
            slugs["investigation"].add(slug)
    return {k: frozenset(v) for k, v in slugs.items()}


def normalize_source_rel_path(arg_path):
    """Normalize a contributor-supplied source path to manifest-canonical
    form (relative to ``sources/``). Accepts both ``news/foo.html``
    (already canonical) and ``sources/news/foo.html`` (repo-root form
    that contributors often copy from grep / find output) and returns
    the canonical form. Also strips a leading slash. Use this at every
    CLI boundary that takes a source path (``extract-source.py
    --source``, ``research-scaffold.py --sources``, ``manifest.py add
    --path``) so the same input works regardless of which root the
    contributor pasted.
    """
    p = (arg_path or "").lstrip("/")
    if p.startswith("sources/"):
        p = p[len("sources/"):]
    return p


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
    read error. Used by the photo-identity baseline pipeline
    (detect-faces.py) to fingerprint baseline crops."""
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


@lru_cache(maxsize=None)
def is_gitignored(rel_to_repo):
    """True if ``rel_to_repo`` (e.g. 'sources/video/x.mp4') is git-ignored.

    Uses ``git check-ignore -q`` — which classifies a path string whether
    or not the file exists on disk (exit 0 = ignored, 1 = not ignored,
    128 = error / not a repo). Falls back to a ``sources/video/`` prefix
    heuristic when git is unavailable (tarball checkout) so the exemption
    still holds. Cached: the same paths recur across a run.

    The large primary-source media (``sources/video/``) is deliberately
    kept out of the git remote per ``.gitignore`` (file-size limits), so a
    missing git-ignored file is expected-absent on a fresh clone, not a
    broken manifest path. Source content is recoverable from the manifest
    URL + Wayback. Shared by manifest.py verify-paths and the
    manifest_files_present validator check."""
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "-q", rel_to_repo],
            cwd=REPO_ROOT, capture_output=True,
        )
        if proc.returncode in (0, 1):
            return proc.returncode == 0
    except OSError:
        pass
    return rel_to_repo.startswith("sources/video/")


# Content-node types the renderer (build-from-research.py) and the
# coverage reviewer (review-coverage.py) both support — derived from
# schema's content-node-type declarations via content_node_types().
# Every schema-declared content-node type has a corresponding renderer
# dispatch branch in build-from-research.py::render_body(); a fork that
# adds a schema type without a renderer dispatch branch surfaces as a
# loud fall-through error at render time.
def supported_types():
    """Frozenset of content-node types the renderer + coverage
    reviewer support. Lazy schema lookup; cached by load_schema()."""
    return content_node_types()


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


def _strip_pdf_page_number_lines(text):
    r"""Remove bare page-number lines that pdftotext emits adjacent to its
    form-feed page separators — a footer digit on its own line at the
    bottom of a page, or a header digit at the top of the next one. These
    are presentation noise: a quote spanning a page break carries the page
    number wedged between the two halves of the sentence, breaking the
    verbatim substring match (and polluting the prose-drift /
    description-drift token pools). Before this strip the workaround was
    to split such quotes at the page break — functional but reader-hostile,
    turning one logical passage into two artificial quotes.

    Conservative: only a line consisting solely of whitespace + digits,
    sitting immediately adjacent (across blank lines only) to a ``\f``, is
    removed. Digits inside body text, numbered-list items, and
    court-reporter line numbers (which carry following text on the same
    line) never match. Form feeds themselves are preserved and the ``\f``
    count is unchanged, so ``normalize-locations.py`` page-number
    computation is unaffected. This is the PDF analog of the HTML
    standalone-datum handling above — presentation noise removed once at
    the extraction layer, so all three source-grounded consumers
    (verbatim-quote, prose-drift, description-drift) benefit with no
    per-check change.
    """
    if "\f" not in text:
        return text
    digit_only = re.compile(r"^[ \t]*\d+[ \t]*$")
    pages = text.split("\f")
    last = len(pages) - 1
    for i, page in enumerate(pages):
        lines = page.split("\n")
        # Footer: trailing digit-only line (past any trailing blanks) on a
        # page that precedes a form feed. Deleted before the header below so
        # the header index (near the start) is not shifted.
        if i < last:
            j = len(lines) - 1
            while j >= 0 and lines[j].strip() == "":
                j -= 1
            if j >= 0 and digit_only.match(lines[j]):
                del lines[j]
        # Header: leading digit-only line (before any leading blanks) on a
        # page that follows a form feed.
        if i > 0:
            k = 0
            while k < len(lines) and lines[k].strip() == "":
                k += 1
            if k < len(lines) and digit_only.match(lines[k]):
                del lines[k]
        pages[i] = "\n".join(lines)
    return "\f".join(pages)


def _strip_sibling_form_feeds(text):
    r"""A `.txt` sibling is a clean transcription that carries **no synthetic
    page markers** — never manufacture page structure in a sibling (see
    ``meta/conventions.md``). Strip any stray form feed so a sibling-backed
    source has no `\f` page structure: ``quote_location_page`` then skips it by
    design — its `p. N` refs are verbatim-anchored navigation hints, not
    machine-checked against a fabricated page split. Text-native PDFs keep the
    form feeds ``pdftotext`` emits natively and stay page-checked.
    """
    return text.replace("\f", "")


def pdf_physical_page_count(source_path):
    r"""Physical page count of a PDF — what a PDF viewer's page counter shows.

    Read from the PDF's page tree via ``pdfinfo`` (poppler, same toolchain as
    ``pdftotext``), so it is the true file page count independent of the text
    layer: correct for image-only / pure-scan PDFs (where ``pdftotext`` would
    collapse to a single block) as well as text-native and OCR-scan files. For
    a text-bearing PDF this equals the ``pdftotext`` form-feed page count — the
    same physical-page model the ``--- page N ---`` extract markers and the
    ``quote_location_page`` check use. Never reads a ``.txt`` sibling, so it
    reports the file's own page count even for OCR-scan sources whose canonical
    text extract is a sibling — exactly where declared counts and ``p. N`` refs
    drifted onto printed folios. Returns None when the file is absent, isn't a
    PDF, or ``pdfinfo`` is unavailable / fails (caller treats None as "can't
    check", never as a violation).
    """
    if source_path.suffix.lower() != ".pdf" or not source_path.exists():
        return None
    try:
        proc = subprocess.run(
            ["pdfinfo", str(source_path)],
            capture_output=True, text=True, timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    m = re.search(r"^Pages:\s*(\d+)", proc.stdout, re.MULTILINE)
    return int(m.group(1)) if m else None


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

    PDF-only normalization: bare page-number lines that pdftotext emits
    adjacent to its form-feed page separators (a footer digit, or a
    top-of-page header digit) are stripped via
    ``_strip_pdf_page_number_lines`` so a quote spanning a page break is
    not broken by the page number wedged between its halves. Form feeds
    are preserved.

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
                    result = _strip_sibling_form_feeds(result)
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
                    result = _strip_pdf_page_number_lines(proc.stdout)
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
        # Merge line-wrap hyphenation (`Geospatial-\nIntelligence`) — but only
        # when a line break actually separates the two halves, and NEVER across
        # a form feed. Two failure modes this guards:
        #   1. Form feed: `\s` includes `\f`, so a bare `-\s+` swallowed the page
        #      separator after a page-final hyphen — a footer page number
        #      (`- 1 -`) or a word hyphenated at the very bottom of a page —
        #      silently merging that page into the next and shifting every
        #      downstream `p. N` split.
        #   2. Suspended hyphen: `-\s+` (and the form-feed-excluding
        #      `-[ \t\r\n\v]+`) also ate the space in a same-line suspended
        #      compound — "ground/sea- or airborne-launched" (= "sea-launched or
        #      airborne-launched") collapsed to "sea-or", corrupting the scratch
        #      and the prose-drift token pool while the hyphen-agnostic verbatim
        #      matcher stayed silent (only an image re-read catches it).
        # A real line-wrap hyphen is always followed by a newline; a suspended
        # or compound hyphen mid-line is followed by a space. Gate the merge on
        # an embedded line break (`[\r\n\v]`, never `\f`) so the wrap still joins
        # but the same-line space survives.
        result = re.sub(r"-[ \t]*[\r\n\v]+[ \t]*", "-", result)
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
    # PDF font-CMap confusable: in some text-native PDFs (Acrobat Distiller
    # from a .txt source) the \u00bd glyph (U+00BD) is encoded so that pdftotext
    # extracts it as \u2021 (U+2021). Fold the extracted \u2021 back to \u00bd so a true
    # "11\u00bd" quote matches the source bytes without hand-transcribing the
    # document (a sibling must be proportionate to the damage \u2014 see the
    # extraction_type doc in schema.yaml). Both quote and source pass through here, so a genuine \u2021
    # still matches a genuine \u2021 (both fold to \u00bd).
    text = text.replace("\u2021", "\u00bd")
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


# The naming_quirks-derived catalog tables. None is "quoted text the
# reader meets," so none counts as grounding for a
# preserve-as-sic-in-quotes entry — body_outside_quirk_tables excises
# all three before the grounding test.
_QUIRK_TABLE_HEADINGS = (
    "## Source-Form Notes",
    "## Preserved Disagreements",
    "## Name Variants",
)


def body_outside_quirk_tables(md_text):
    """Return a rendered node body with every naming_quirks-derived
    catalog table (``## Source-Form Notes`` / ``## Preserved
    Disagreements`` / ``## Name Variants``) excised, so a quirk's own
    catalog row never counts as grounding for itself.

    Shared by the ``source_form_grounding`` review-coverage gate and the
    ``coverage-suggest.py`` diagnostic so both apply the identical
    grounding definition: a ``preserve-as-sic-in-quotes`` entry is
    grounded only when its ``observed`` form appears in quoted text (or
    the heading / locator framing a quote) on the node — NOT merely in
    one of these catalog tables. An entry that surfaces only in a
    catalog row is an orphan."""
    out, skip = [], False
    for line in (md_text or "").splitlines():
        if line.startswith("## "):
            skip = any(line.startswith(h) for h in _QUIRK_TABLE_HEADINGS)
        if not skip:
            out.append(line)
    return "\n".join(out)


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
# capture the variance as evidentiary data (naming_quirks /
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
    (so `smith's` → `smith`) — possessive forms are noise against
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
    # Strip trailing possessive `'s` to collapse "smith" ↔ "smith's".
    # (Leaves intra-word apostrophes alone: "don't" stays "don't".)
    words = [re.sub(r"'s$", "", w) for w in words]
    # Strip trailing quote characters that the regex captured from
    # source-quoted phrases. The matched class `[a-z0-9\-']+` includes
    # the apostrophe so intra-word forms like "don't" survive — but the
    # same pattern keeps a trailing quote when a source-quoted phrase
    # like 'High' or Halverson's Quarterly Report' decodes through YAML
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

