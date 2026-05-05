#!/usr/bin/env python3
"""
Validate nodes against meta/schema.yaml.

Checks:

  Frontmatter — required fields + valid type/kind/archetype/status

  id-path-match — id frontmatter matches file path

  Required sections — per type + kind/archetype (+ corpus addendum)

  Confirmed/Flagged split — subsection splits (Flagged omitted when empty)

  Quote-verification blocks — in sections that require them

  Background prose-only — person nodes

  Internal-link resolution — body `[`/path`]` links + frontmatter
  node-path pointers (media.derivation_of, transcript.derived_from)
  share one existence-check pass. Missing targets register in the
  broken-link registry as backlog (not errors).

  Table-cell word-budget — soft warning

  Finding cross-ref consistency — entities listed must link back

  Verbatim-quote check — for every '> blockquote' followed by an
  attribution block whose Source row points at an archived file under
  `sources/`, extract the cited source to plaintext and confirm the
  quote appears as a substring (with whitespace/dash/quote-style
  normalization). Errors if the quote is not present, with a failure
  message naming the node, approximate line number of the block-quote,
  the cited source file, and a preview of the unmatched text.

  Runs unconditionally — confirmation against the underlying source
  is a precondition for inclusion in node bodies, not a marker the
  contributor opts into. The check has no rendered counterpart in node
  output (no Verified row) by design; the source link IS the evidence
  for readers, this check is the mechanical backstop against silent
  drift between an artifact's quote text and the source it claims to
  draw on. See meta/conventions.md.

  Requires `pdftotext` for PDF sources (poppler-utils on Linux);
  HTML/TXT sources read directly. PDFs flagged
  `extraction_type: ocr-scan` in sources/manifest.yaml prefer a
  same-stem `.txt` sibling (clean transcription) over pdftotext output.

  Manifest-checksum check — for every archived entry in
  sources/manifest.yaml, recompute SHA256 and compare to stored value.
  Errors on: file missing on disk, missing sha256 field when required,
  checksum mismatch (silent corruption / substitution). Run once per
  validator invocation, before the per-node checks.

  Governance-frontmatter check — every .md file under meta/ must carry
  id / type / schema_version / created; schema_version must be in
  schema.compatible_with; id must match file path. Templates routed
  through a placeholder-aware regex path because their `{{slug}}` /
  `{{today}}` values can't be YAML-parsed cleanly.

  Conditionally-required check — schema-driven enforcement of
  `types.{T}.conditionally_required` entries. Condition grammar:
  `<field> == <literal>`, `<field> is set`. Keys route to frontmatter-
  field presence+vocabulary checks (lowercase names) or section-
  presence checks (Title Case names). Replaces earlier hardcoded
  archival_status / Media Versioning rules.

  Chronological-ordering check — every markdown table with a date-
  bearing column (Date / Date / Time / Period / Start / Date Captured /
  Date Released / Dates) is ordered earliest-first. Range cells take
  the leftmost date; missing month / day default to 0 so
  '2004' < '2004-11' < '2004-11-14'. Rows in disorder error; cells
  with unparseable date strings warn. Universal discipline across
  every node type and section. Upgrades the schema's
  `chronological: true` flag from descriptive-only to enforced.

Usage:
  validate.py                    # all nodes
  validate.py PATH               # single node
  validate.py --quiet            # errors only

Cross-referencing: other docs / scripts refer to these checks by topic
name (e.g., `the verbatim-quote check`, `the prose-drift check` in
validate-research.py). See meta/conventions.md "Check naming".
"""

import argparse
import re
import sys
from pathlib import Path
from collections import defaultdict

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from lib._common import (
    extract_h2_sections,
    extract_section,
    extract_source_text,
    manifest_format,
    normalize_for_compare,
)

# Per-check modules (C11 / C13 / C14 — pilot wiring; sessions 2 and 3
# migrate the remaining checks against the same contract).
from checks import BaseContext
from checks import manifest_archive_status as ck_manifest_archive_status
from checks import manifest_checksums as ck_manifest_checksums
from checks import manifest_extraction_type as ck_manifest_extraction_type

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "meta" / "schema.yaml"
ADDENDA_DIR = REPO_ROOT / "meta" / "topic" / "addenda"
SOURCES_DIR = REPO_ROOT / "sources"
MANIFEST_PATH = SOURCES_DIR / "manifest.yaml"

CONTENT_DIRS = [
    "people", "organizations", "documents", "events",
    "transcripts", "media", "locations", "findings",
]

LINK_PATTERN = re.compile(r"\[`(/[^`]+)`\]")

# Frontmatter fields that carry node-path semantics. When set on a node
# of the listed type, the value is checked for target existence the same
# way body `[`/path`]` links are — missing targets register in the
# broken-link registry (backlog), not as errors. Consistent with how
# body-link stubs are tracked today.
#
# Kept as a module-level constant rather than reading a schema annotation
# at runtime — short and stable enough that the simplicity wins. Promote
# to schema-driven if the list grows past ~5 fields.
NODE_PATH_FRONTMATTER_FIELDS = {
    "media":      ["derivation_of"],   # parent media node
    "transcript": ["derived_from"],    # underlying media or document node
}


# =============================================================================
# Types and reporting
# =============================================================================


class Issue:
    def __init__(self, path, level, message):
        self.path = str(path)
        self.level = level
        self.message = message


# =============================================================================
# Schema loading
# =============================================================================


def load_schema():
    with open(SCHEMA_PATH) as f:
        return yaml.safe_load(f)


# =============================================================================
# Parsing utilities — frontmatter, sections, links, tables
# =============================================================================


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None, None
    end = text.find("\n---", 3)
    if end < 0:
        return None, None
    try:
        fm = yaml.safe_load(text[3:end])
        return fm, text[end + 4:]
    except yaml.YAMLError:
        return None, None


# extract_h2_sections + extract_section moved to scripts/lib/_common.py
# in the C11 session-2 migration (2026-05-05) so per-check modules in
# scripts/checks/ can import them directly without the layering inversion
# that would result from importing from the orchestrator (validate.py).
# Both functions are pure (text in, structure out); no shared state.


def extract_h3_subsections(section_text):
    return re.findall(r"^### (.+?)\s*$", section_text, re.MULTILINE)


def extract_links(text):
    return set(LINK_PATTERN.findall(text))


def section_has_table(section_text):
    return bool(
        re.search(r"^\|[^\n]*\|\s*\n\|[\s:|-]+\|", section_text, re.MULTILINE)
    )


def count_quote_blocks_and_attributions(section_text):
    """Count `> blockquote` lines and `| Source | …` attribution rows in
    a section. Used to enforce the structural rule that a section flagged
    `requires_quote_attribution` either has no quotes (empty section is
    fine) or has a Source row for each quote — the renderer always pairs
    a block-quote with an attribution table whose Source row points at
    the cited archived file."""
    quotes = sum(1 for line in section_text.splitlines() if line.strip().startswith(">"))
    attributions = sum(1 for line in section_text.splitlines() if line.strip().startswith("| Source |"))
    return quotes, attributions


# =============================================================================
# Chronological-ordering check
#
# Universal discipline: any table with a date-bearing column is ordered
# earliest-first. Applies across every node type and every section.
# The check:
#   1. Scans each H2 section for markdown tables (header + separator +
#      data rows).
#   2. For each table, identifies the date column by header name
#      (case-insensitive match against DATE_HEADERS).
#   3. Parses the date cell on each data row (ISO YYYY-MM-DD and
#      prefix-truncated YYYY-MM / YYYY; range cells take the leftmost
#      date; empty cells skip).
#   4. Errors if rows are not in ascending date order.
#   5. Warns on unparseable dates (natural-language dates, non-ISO
#      formats — promoted to error-level later if warranted).
#
# Upgrades the `chronological: true` schema flag from descriptive-only
# to enforced — closing part of BACKLOG #9.
# =============================================================================

DATE_HEADERS = {
    "date", "date / time", "date/time",
    "period", "start", "start date", "dates",
    "date captured", "date released",
}

# Range separators between start and end dates in a single cell. Ordered
# longest-first so "—" doesn't match inside " – ".
_DATE_RANGE_SEPARATORS = (" – ", " — ", " to ", " - ", "–", "—", "-to-")


def parse_date_token(s):
    """Return (year, month, day) tuple suitable for sort comparison, or
    None if unparseable. Range cells take the leftmost date. Missing
    month / day default to 0, so '2004' < '2004-11' < '2004-11-14'
    under tuple comparison.
    """
    if not s:
        return None
    s = s.strip()
    # Strip typical non-date tokens
    if s.lower() in {"—", "-", "n/a", "undated", "tbd", "present", "ongoing", ""}:
        return None
    # Range: take the left side. If the left side is empty (end-only
    # period rendered as "– 2021" — signals bracketed end with unknown
    # start, e.g., "former X" attestation without a specific start date),
    # take the right side instead so the row still sorts by its attested
    # end date.
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


_TABLE_RE = re.compile(
    r"(?P<header_line>^\|(?P<header>[^\n]+)\|\s*)\n"
    r"(?P<sep_line>^\|(?P<sep>[\s:|-]+)\|\s*)\n"
    r"(?P<rows>(?:^\|[^\n]+\|\s*\n?)+)",
    re.MULTILINE,
)


def _parse_table_row(row_line):
    """Split a `| a | b | c |` row into trimmed cell strings."""
    inner = row_line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip() for c in inner.split("|")]


def check_chronological_tables(text, rel):
    """Enforce chronological (earliest-first) ordering on every date-
    bearing table across all H2 sections. Returns a list of Issue.
    """
    issues = []
    h2_sections = extract_h2_sections(text)
    for section_name in h2_sections:
        section_text = extract_section(text, section_name)
        if section_text is None:
            continue

        for m in _TABLE_RE.finditer(section_text):
            headers = [h.strip().lower() for h in m.group("header").split("|")]
            date_col = None
            for i, h in enumerate(headers):
                if h in DATE_HEADERS:
                    date_col = i
                    break
            if date_col is None:
                continue

            # Parse each data row's date cell (skip empty-placeholder rows)
            rows = m.group("rows").strip().splitlines()
            parsed_dates = []
            for row_line in rows:
                cells = _parse_table_row(row_line)
                if date_col >= len(cells):
                    continue
                if all(c == "" for c in cells):
                    continue  # template placeholder row
                cell = cells[date_col]
                d = parse_date_token(cell)
                if d is None and cell:
                    issues.append(Issue(rel, "warn",
                        f"Section '{section_name}': unparseable date "
                        f"{cell!r} in '{headers[date_col] or '?'}' column"))
                parsed_dates.append((cell, d))

            # Verify ascending order across parseable entries
            previous_cell, previous = None, None
            for cell, d in parsed_dates:
                if d is None:
                    continue
                if previous is not None and d < previous:
                    issues.append(Issue(rel, "error",
                        f"Section '{section_name}': table rows not in "
                        f"chronological order (saw {cell!r} after "
                        f"{previous_cell!r} in "
                        f"'{headers[date_col] or '?'}' column; "
                        f"earliest first)"))
                    break
                previous, previous_cell = d, cell

    return issues


# =============================================================================
# Source-integrity checks — manifest-checksum check
# =============================================================================

# manifest_checksums check moved to scripts/checks/manifest_checksums.py
# as part of the C11 / C13 / C14 pilot migration (2026-05-05). It consumes
# BaseContext.manifest_entries instead of re-loading the manifest itself,
# so the orchestrator's single load can serve all manifest checks once
# they migrate (sessions 2 and 3).
#
# Manifest parse-failure handling moved to the orchestrator (load_manifest
# in main()) so the migrated check can assume a clean entry list.


# manifest_archive_status + manifest_extraction_type checks moved to
# scripts/checks/manifest_archive_status.py and
# scripts/checks/manifest_extraction_type.py during the C11 session-2
# migration (2026-05-05). Both consume BaseContext.manifest_entries from
# the orchestrator's single manifest load; the load-3x duplication that
# affected the legacy manifest checks is now fully closed (C14 retires).


# =============================================================================
# Verbatim-quote check — against archived source files
# =============================================================================

BLOCKQUOTE_BLOCK = re.compile(
    r"(^>[ \t].+(?:\n>[ \t].*)*)",
    re.MULTILINE,
)


# extract_source_text + normalize_for_compare moved to scripts/lib/_common.py
# (centralized 2026-05-01) to keep validate.py / validate-research.py /
# review-coverage.py in mechanical lockstep on source extraction and quote
# normalization. See _common.py for the full implementation and rationale.


def find_quote_source_pairs(text):
    """Yield (quote_text, source_ref, line_no) for each block-quote followed
    by an attribution table containing a Source row.

    line_no is the 1-indexed line number of the block-quote's first line in
    the original text \u2014 surfaced in failure messages so contributors can
    locate the quote in the rendered node directly.
    """
    for bq_match in BLOCKQUOTE_BLOCK.finditer(text):
        raw = bq_match.group(1)
        # Strip leading "> " from each line, join with spaces
        quote_lines = [re.sub(r"^>[ \t]?", "", line) for line in raw.splitlines()]
        quote_text = " ".join(line for line in quote_lines if line.strip())
        # Strip surrounding quote marks
        quote_text = re.sub(r'^["\u201c\u201d\u2018\u2019]+', "", quote_text)
        quote_text = re.sub(r'["\u201c\u201d\u2018\u2019]+$', "", quote_text)
        quote_text = quote_text.strip()
        if not quote_text:
            continue
        # Look for Source row within ~2500 chars after the quote
        after = text[bq_match.end():bq_match.end() + 2500]
        src_match = re.search(
            r"^\|\s*Source\s*\|\s*([^|]+?)\s*\|",
            after, re.MULTILINE,
        )
        if not src_match:
            continue
        source_ref = src_match.group(1).strip()
        line_no = text.count("\n", 0, bq_match.start()) + 1
        yield quote_text, source_ref, line_no


def check_verbatim_quotes(node_path, text, rel_path):
    """For every block-quote with an attribution Source pointing at an archived
    file under `sources/`, confirm the quote appears as a substring of the
    extracted source text.

    Runs unconditionally — no marker gate. Confirmation against the source
    is a precondition for inclusion; this check enforces it mechanically.
    Failure messages name the node, the line number of the block-quote,
    the cited source file, and a preview of the unmatched text — enough
    for a contributor to navigate and fix without further detective work.
    """
    issues = []
    for quote_text, source_ref, line_no in find_quote_source_pairs(text):
        # Extract local source path from markdown link (../sources/foo.pdf)
        path_match = re.search(r"\(\.\./sources/([^)]+)\)", source_ref)
        if not path_match:
            # Source refers to a node link (e.g. [`/transcripts/...`]) rather
            # than a file. Can't mechanically verify — skip (soft case).
            continue
        rel_source = path_match.group(1)
        source_file = SOURCES_DIR / rel_source
        if not source_file.exists():
            issues.append(Issue(rel_path, "error",
                f"Quote at line {line_no} cites missing source file: sources/{rel_source}"))
            continue
        source_text = extract_source_text(source_file)
        if source_text is None:
            # Distinguish binary-by-design (image/video/audio per manifest
            # format) from extraction-infrastructure failure. pdftotext
            # didn't fail on a .mp4; it was never going to run. Binary-
            # source-citing quotes require manual contributor verification —
            # the validator can't substring-match against bytes that aren't
            # text. Frame the warning accordingly.
            fmt = manifest_format(rel_source)
            if fmt in ("image", "video", "audio"):
                issues.append(Issue(rel_path, "warn",
                    f"Quote at line {line_no} cites sources/{rel_source} "
                    f"(format: {fmt}) — verbatim-quote check requires manual "
                    f"contributor verification of binary source"))
            else:
                issues.append(Issue(rel_path, "warn",
                    f"Quote at line {line_no} cites sources/{rel_source} but text extraction failed (pdftotext missing or failed)"))
            continue
        norm_quote = normalize_for_compare(quote_text)
        norm_source = normalize_for_compare(source_text)
        if norm_quote not in norm_source:
            preview = quote_text[:80] + ("..." if len(quote_text) > 80 else "")
            issues.append(Issue(rel_path, "error",
                f'Quote at line {line_no} NOT FOUND in sources/{rel_source}: "{preview}"'))
    return issues


# =============================================================================
# Structural-check utilities — table cell word budget, addendum loading,
# required-sections computation
# =============================================================================


def table_cell_overages(section_text, budget):
    """Return list of (cell_preview, word_count) for cells exceeding budget."""
    out = []
    for line in section_text.splitlines():
        if not (line.strip().startswith("|") and line.count("|") >= 2):
            continue
        if re.match(r"^\s*\|[\s:|-]+\|\s*$", line):
            continue  # separator row
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        for cell in cells:
            # Strip markdown link syntax before counting words
            stripped = re.sub(r"\[`[^`]+`\]", "", cell)
            stripped = re.sub(r"[*_`]", "", stripped)
            words = stripped.split()
            if len(words) > budget:
                preview = cell[:60] + ("..." if len(cell) > 60 else "")
                out.append((preview, len(words)))
    return out


def load_addendum_sections(corpus):
    """Parse an addendum file for required sections."""
    path = ADDENDA_DIR / f"{corpus}.md"
    if not path.exists():
        return []
    text = path.read_text()
    # Look for "## Additional required sections" block; then ### `## SectionName`
    m = re.search(
        r"##\s+Additional required sections\s*\n(.*?)(?=\n---|\n##\s|\Z)",
        text, re.DOTALL,
    )
    if not m:
        return []
    block = m.group(1)
    return re.findall(r"`##\s+([^`]+)`", block)


def compute_required_sections(fm, type_spec):
    sections = []
    arch = fm.get("archetype")
    kind = fm.get("kind")
    if arch and "archetypes" in type_spec:
        sections = list(type_spec["archetypes"].get(arch, {}).get("required_sections", []))
    elif kind and "kinds" in type_spec:
        sections = list(type_spec["kinds"].get(kind, {}).get("required_sections", []))
    else:
        sections = list(type_spec.get("required_sections", []))
    corpus = fm.get("corpus")
    if corpus:
        sections.extend(load_addendum_sections(corpus))
    return sections


# =============================================================================
# conditionally_required dispatcher
#
# Reads `types.{T}.conditionally_required` from schema.yaml as a dict of
# {key: condition-expression}. When the condition is true against the
# node's frontmatter, the key is enforced. Key routing:
#   - lowercase_with_underscores → frontmatter field (required presence;
#     value validated against `{key}_values` on type_spec when present)
#   - Title Case With Spaces     → H2 section name (required presence)
#
# Supported condition grammar (kept minimal on purpose; extend only when
# a new conditional genuinely needs it):
#   <field> == <literal>      equality check; literal is \w-separated token
#   <field> is set            field is present and truthy in frontmatter
#
# The dispatcher replaces two earlier hardcoded checks (archival_status
# when doc_form is book; Media Versioning section when derivation_of is
# set) so future conditionals can land as schema edits alone. Malformed
# condition strings surface as validator errors so schema drift is loud.
# =============================================================================


_CONDITION_IS_SET = re.compile(r"^\s*(\w+)\s+is\s+set\s*$")
_CONDITION_EQ = re.compile(r"^\s*(\w+)\s*==\s*([\w-]+)\s*$")

# Frontmatter field vs section name is disambiguated by shape: field names
# are lowercase with underscores / hyphens (no spaces, no capitals);
# section names are human-readable (any space or capital triggers section
# routing). Matches the schema style already in use.
_FIELD_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


def evaluate_condition(condition, fm):
    """Evaluate a condition string from schema conditionally_required
    against frontmatter `fm`. Returns True/False.

    Raises ValueError if the expression doesn't match the supported
    grammar — malformed conditions should surface loudly to the
    validator, not silently pass.
    """
    if not isinstance(condition, str):
        raise ValueError(f"condition must be a string; got {type(condition).__name__}")

    m = _CONDITION_IS_SET.match(condition)
    if m:
        field = m.group(1)
        return bool(fm.get(field))

    m = _CONDITION_EQ.match(condition)
    if m:
        field, value = m.group(1), m.group(2)
        return fm.get(field) == value

    raise ValueError(
        f"unsupported condition expression {condition!r} — "
        f"grammar: '<field> == <literal>' | '<field> is set'"
    )


def check_conditionally_required(fm, type_spec, text, rel):
    """Enforce `type_spec.conditionally_required`. Returns list of Issue.

    For each (key, condition) pair:
      1. Evaluate condition; if false, skip.
      2. If key is a frontmatter-field name (lowercase): require the
         field is set. If a `{key}_values` vocabulary exists on the
         type_spec, additionally require the value is in that list.
      3. If key is an H2 section name: require the section exists in the
         node body.
    """
    issues = []
    cr = type_spec.get("conditionally_required") or {}
    h2_sections = None  # lazy — only extract when first section check fires

    for key, condition in cr.items():
        try:
            active = evaluate_condition(condition, fm)
        except ValueError as e:
            issues.append(Issue(rel, "error",
                f"schema conditionally_required[{key!r}]: {e}"))
            continue
        if not active:
            continue

        if _FIELD_KEY_RE.match(key):
            # Frontmatter-field route: require presence, then vocabulary.
            if not fm.get(key):
                issues.append(Issue(rel, "error",
                    f"Frontmatter missing {key!r} (required when {condition!r})"))
                continue
            values_key = f"{key}_values"
            valid_values = type_spec.get(values_key) or []
            if valid_values and fm[key] not in valid_values:
                issues.append(Issue(rel, "error",
                    f"Invalid {key} {fm[key]!r}. Valid: {valid_values}"))
        else:
            # Section-name route: require H2 presence.
            if h2_sections is None:
                h2_sections = extract_h2_sections(text)
            if key not in h2_sections:
                issues.append(Issue(rel, "error",
                    f"Required section '## {key}' missing "
                    f"(required when {condition!r})"))

    return issues


# =============================================================================
# Per-node validation orchestration
# =============================================================================


def validate_node(path, schema):
    issues = []
    text = path.read_text()
    rel = path.relative_to(REPO_ROOT)

    fm, _ = parse_frontmatter(text)
    if fm is None:
        issues.append(Issue(rel, "error", "Missing or malformed YAML frontmatter"))
        return issues, set()

    node_type = fm.get("type")
    if not node_type:
        issues.append(Issue(rel, "error", "Missing 'type' in frontmatter"))
        return issues, set()

    type_spec = schema["types"].get(node_type)
    if not type_spec:
        issues.append(Issue(rel, "error", f"Unknown type '{node_type}'"))
        return issues, set()

    # Required frontmatter fields
    required_fm = type_spec.get("frontmatter", {}).get("required", [])
    for field in required_fm:
        if field not in fm:
            issues.append(Issue(rel, "error", f"Missing required frontmatter field '{field}'"))

    # schema_version value check — must be in schema.compatible_with
    # (content-node scope only per the B2 design decision)
    sv = fm.get("schema_version")
    if sv is not None:
        schema_block = schema.get("schema", {}) or {}
        compatible_with = schema_block.get("compatible_with", [1])
        if not isinstance(sv, int) or isinstance(sv, bool):
            issues.append(Issue(rel, "error",
                f"schema_version must be an integer; got {sv!r} ({type(sv).__name__})"))
        elif sv not in compatible_with:
            current = schema_block.get("version", "?")
            issues.append(Issue(rel, "error",
                f"schema_version {sv} not in compatible_with {compatible_with} "
                f"(current schema version is {current}). "
                f"Migrate per meta/toolkit-notes/schema-migrations/."))

    # id matches path
    expected_id = str(rel).removesuffix(".md")
    if fm.get("id") and fm["id"] != expected_id:
        issues.append(Issue(rel, "error",
            f"Frontmatter id '{fm['id']}' does not match path '{expected_id}'"))

    # Valid status
    status_values = type_spec.get("status_values", [])
    if fm.get("status") and status_values and fm["status"] not in status_values:
        issues.append(Issue(rel, "error",
            f"Invalid status '{fm['status']}'. Valid: {status_values}"))

    # Valid archetype / kind
    if fm.get("archetype"):
        valid = list(type_spec.get("archetypes", {}).keys())
        if valid and fm["archetype"] not in valid:
            issues.append(Issue(rel, "error",
                f"Invalid archetype '{fm['archetype']}'. Valid: {valid}"))
    if fm.get("kind"):
        valid = list(type_spec.get("kinds", {}).keys())
        if valid and fm["kind"] not in valid:
            issues.append(Issue(rel, "error",
                f"Invalid kind '{fm['kind']}'. Valid: {valid}"))

    # Document form — value-vocabulary check (unconditional; orthogonal to
    # the conditionally_required dispatch below which handles required-
    # presence by condition).
    if node_type == "document":
        valid_forms = type_spec.get("doc_form_values", [])
        df = fm.get("doc_form")
        if df and valid_forms and df not in valid_forms:
            issues.append(Issue(rel, "warn",
                f"Unknown doc_form '{df}' (not in schema list; add if established)"))
        # archival_status value vocabulary — enforced whenever set, whether
        # or not doc_form triggers the conditionally_required branch below.
        # Covers the case where archival_status is set on a non-book
        # doc_form (uncommon but not forbidden).
        if fm.get("archival_status"):
            archival = fm["archival_status"]
            valid_archival = type_spec.get("archival_status_values", [])
            if valid_archival and archival not in valid_archival:
                issues.append(Issue(rel, "error",
                    f"Invalid archival_status {archival!r}. "
                    f"Valid: {valid_archival}"))

    # conditionally_required dispatch — schema-driven; handles
    # archival_status-when-book (document) and Media Versioning section-
    # when-derivation_of-set (media) from schema.yaml. Future
    # conditionals land as schema edits only.
    issues.extend(check_conditionally_required(fm, type_spec, text, rel))

    # Required sections
    required_sections = compute_required_sections(fm, type_spec)
    h2_sections = extract_h2_sections(text)
    for req in required_sections:
        found = any(s == req or s.startswith(req + " (") or s.startswith(req + " —")
                    for s in h2_sections)
        if not found:
            issues.append(Issue(rel, "error", f"Missing required section '## {req}'"))

    # Section rules
    section_rules = type_spec.get("section_rules", {})
    for section_name, rules in section_rules.items():
        if section_name not in h2_sections:
            continue
        section_text = extract_section(text, section_name)
        if section_text is None:
            continue

        if rules.get("prose_only") and section_has_table(section_text):
            issues.append(Issue(rel, "error",
                f"Section '{section_name}' must be prose only (no tables)"))

        if "split" in rules:
            h3s = extract_h3_subsections(section_text)
            for sub in rules["split"]:
                if sub == "Flagged":
                    continue  # omitted when empty by convention
                if sub not in h3s:
                    issues.append(Issue(rel, "error",
                        f"Section '{section_name}' missing '### {sub}' subsection"))

        if rules.get("requires_quote_attribution"):
            quotes, attributions = count_quote_blocks_and_attributions(section_text)
            if quotes > 0 and attributions == 0:
                issues.append(Issue(rel, "error",
                    f"Section '{section_name}' has quotes but no attribution blocks (each block-quote needs a `| Source | … |` row pointing at the cited archived file)"))

    # Verbatim quote verification — critical check (fix from 2026-04-17 pilot failure)
    issues.extend(check_verbatim_quotes(path, text, rel))

    # Chronological-ordering check on date-bearing tables
    issues.extend(check_chronological_tables(text, rel))

    # Internal link resolution — body links + frontmatter node-path
    # pointers share one existence-check pass and one broken-link
    # registry. Missing targets are backlog, not errors (matches existing
    # body-link behavior for unbuilt stubs).
    links = extract_links(text)
    for field in NODE_PATH_FRONTMATTER_FIELDS.get(node_type, []):
        value = fm.get(field)
        if value:
            # Normalize to leading-slash form so the broken-link registry
            # key shape matches body-link entries. Accept both "/type/slug"
            # and "type/slug" on input.
            links.add("/" + str(value).lstrip("/"))
    broken = set()
    for link in links:
        target = REPO_ROOT / link.lstrip("/")
        target_md = target.with_suffix(".md") if not target.suffix else target
        if not target_md.exists() and not target.exists():
            broken.add(link)

    # Table cell word budget
    budget = schema.get("limits", {}).get("table_cell_words_soft", 50)
    for section_name in h2_sections:
        section_text = extract_section(text, section_name)
        if section_text is None:
            continue
        for preview, count in table_cell_overages(section_text, budget):
            issues.append(Issue(rel, "warn",
                f"Table cell in '{section_name}' exceeds word budget ({count}>{budget}): {preview}"))

    # Finding cross-reference consistency
    if node_type == "finding":
        entities = fm.get("entities") or []
        if isinstance(entities, list):
            for entity in entities:
                ep = REPO_ROOT / entity.lstrip("/")
                ep_md = ep.with_suffix(".md") if not ep.suffix else ep
                if ep_md.exists():
                    entity_text = ep_md.read_text()
                    fid = fm.get("id", "")
                    if fid and f"/{fid}" not in entity_text:
                        issues.append(Issue(rel, "warn",
                            f"Entity {entity} does not link back to this finding"))

    return issues, broken


# =============================================================================
# Governance-file validation — frontmatter discipline for meta/ files
# =============================================================================

META_DIR = REPO_ROOT / "meta"

# Type → content-directory mapping used to derive a template's expected
# placeholder id (person.md → id: people/{{slug}}). Same small static map
# appears in new.py and validate-research.py; centralization deferred —
# the map is short, stable, and rarely changes (one entry added when a
# new node type ships). If drift surfaces or the map grows, promote to
# scripts/lib/_common.py alongside the source-extraction helpers.
_TEMPLATE_TYPE_DIRS = {
    "person": "people", "organization": "organizations",
    "document": "documents", "event": "events",
    "transcript": "transcripts", "media": "media",
    "location": "locations", "finding": "findings",
}

_REQUIRED_META_FIELDS = ("id", "type", "schema_version", "created")

# meta/topic/working-notes/ is the holding pen for in-progress contributor
# synthesis (handoff drafts, audit scratch, investigation notes). Per
# meta/topic/working-notes/README.md, files there sit outside the validated
# content layer and the schema-frontmatter contract — they're transient
# scratch material, deleted on integration. Skip the directory entirely so
# untracked drafts don't block the validator. The directory's own README.md
# is also under this prefix; the README is hand-written with valid
# frontmatter but doesn't need to be validated either.
_WORKING_NOTES_PREFIX = "meta/topic/working-notes/"


def iter_governance_files():
    """Yield every .md file under meta/ except working-notes drafts,
    ordered by path for stable reports."""
    if not META_DIR.is_dir():
        return
    for p in sorted(META_DIR.rglob("*.md")):
        rel = p.relative_to(REPO_ROOT).as_posix()
        if rel.startswith(_WORKING_NOTES_PREFIX):
            continue
        yield p


def _check_template_frontmatter(path, rel, text, compatible_with, schema_block):
    """Template-specific frontmatter check. YAML can't cleanly parse
    template placeholders like `{{slug}}` and `{{today}}` — they
    conflict with YAML's flow-mapping syntax (`{...}`). Use line-based
    regex checks against the raw frontmatter block instead."""
    issues = []

    if not text.startswith("---"):
        issues.append(Issue(rel, "error",
            "Template missing frontmatter opener '---'"))
        return issues
    end = text.find("\n---", 3)
    if end < 0:
        issues.append(Issue(rel, "error",
            "Template frontmatter not closed with '---'"))
        return issues
    block = text[3:end]
    stem = path.stem

    # id: must match the placeholder pattern "{content-dir}/{{slug}}"
    id_match = re.search(r"^id:\s*(\S.*?)\s*$", block, re.MULTILINE)
    if not id_match:
        issues.append(Issue(rel, "error",
            "Template missing required 'id:' line in frontmatter"))
    else:
        expected_dir = _TEMPLATE_TYPE_DIRS.get(stem, stem)
        expected_id = f"{expected_dir}/{{{{slug}}}}"
        if id_match.group(1) != expected_id:
            issues.append(Issue(rel, "error",
                f"Template id {id_match.group(1)!r} does not match "
                f"expected placeholder pattern {expected_id!r} "
                f"(derived from filename stem {stem!r})"))

    # type: must match the filename stem
    type_match = re.search(r"^type:\s*(\S.*?)\s*$", block, re.MULTILINE)
    if not type_match:
        issues.append(Issue(rel, "error",
            "Template missing required 'type:' line in frontmatter"))
    elif type_match.group(1) != stem:
        issues.append(Issue(rel, "error",
            f"Template type {type_match.group(1)!r} does not match "
            f"filename stem {stem!r}"))

    # schema_version: must be integer in compatible_with. Templates
    # hard-code a version (not a placeholder) because scaffolded nodes
    # inherit the value verbatim.
    sv_match = re.search(r"^schema_version:\s*(\d+)\s*$", block, re.MULTILINE)
    if not sv_match:
        issues.append(Issue(rel, "error",
            "Template missing required 'schema_version:' line "
            "(must be an integer, not a placeholder)"))
    else:
        sv = int(sv_match.group(1))
        if sv not in compatible_with:
            current = schema_block.get("version", "?")
            issues.append(Issue(rel, "error",
                f"Template schema_version {sv} not in compatible_with "
                f"{compatible_with} (current schema version is "
                f"{current})"))

    # created: required; value is always `{{today}}` placeholder, not
    # validated as a date (the scaffolder substitutes).
    if not re.search(r"^created:\s*\S", block, re.MULTILINE):
        issues.append(Issue(rel, "error",
            "Template missing required 'created:' line in frontmatter"))

    return issues


def _check_governance_doc_frontmatter(path, rel, text, compatible_with, schema_block):
    """Standard governance-doc frontmatter check via YAML parse."""
    issues = []
    fm, _ = parse_frontmatter(text)

    if fm is None:
        issues.append(Issue(rel, "error",
            "Missing or malformed YAML frontmatter (meta/ files require "
            "id / type / schema_version / created)"))
        return issues

    # Required fields
    for field in _REQUIRED_META_FIELDS:
        if field not in fm:
            issues.append(Issue(rel, "error",
                f"Missing required frontmatter field {field!r} "
                f"(meta/ files require "
                f"{' / '.join(_REQUIRED_META_FIELDS)})"))

    # schema_version value check
    sv = fm.get("schema_version")
    if sv is not None:
        if not isinstance(sv, int) or isinstance(sv, bool):
            issues.append(Issue(rel, "error",
                f"schema_version must be an integer; got {sv!r} "
                f"({type(sv).__name__})"))
        elif sv not in compatible_with:
            current = schema_block.get("version", "?")
            issues.append(Issue(rel, "error",
                f"schema_version {sv} not in compatible_with "
                f"{compatible_with} (current schema version is "
                f"{current}). Migrate per "
                f"meta/toolkit-notes/schema-migrations/."))

    # id matches path
    if "id" in fm:
        expected_id = str(rel).removesuffix(".md")
        if fm["id"] != expected_id:
            issues.append(Issue(rel, "error",
                f"Frontmatter id {fm['id']!r} does not match path "
                f"{expected_id!r}"))

    return issues


def check_governance_files(schema):
    """Validate every .md under meta/ carries the required frontmatter
    discipline: id / type / schema_version / created; schema_version in
    compatible_with; id matches file path.

    Routes templates (under meta/templates/) through a placeholder-aware
    regex path because their `{{slug}}` / `{{today}}` values can't be
    YAML-parsed cleanly. Governance docs (everything else under meta/)
    use standard YAML frontmatter parsing.

    Closes the BACKLOG gap: meta files carried schema_version but had no
    validation pass. Template drift is the highest-blast-radius scenario
    — a drifted schema_version in a template propagates to every node
    scaffolded afterward, and was previously undetectable until someone
    tried to validate one of those downstream nodes.
    """
    issues = []
    schema_block = schema.get("schema", {}) or {}
    compatible_with = schema_block.get("compatible_with", [1])

    for path in iter_governance_files():
        rel = path.relative_to(REPO_ROOT)
        rel_str = str(rel)
        is_template = rel_str.startswith("meta/templates/")

        text = path.read_text(encoding="utf-8", errors="replace")

        if is_template:
            issues.extend(_check_template_frontmatter(
                path, rel, text, compatible_with, schema_block))
        else:
            issues.extend(_check_governance_doc_frontmatter(
                path, rel, text, compatible_with, schema_block))

    return issues


# =============================================================================
# Node collection
# =============================================================================


def collect_nodes():
    nodes = []
    for d in CONTENT_DIRS:
        cd = REPO_ROOT / d
        if cd.is_dir():
            nodes.extend(sorted(cd.glob("*.md")))
    return nodes


# =============================================================================
# Main — CLI, orchestration, and report formatting
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", help="Single node path (optional)")
    parser.add_argument("--quiet", action="store_true", help="Errors only")
    args = parser.parse_args()

    schema = load_schema()
    nodes = [Path(args.path).resolve()] if args.path else collect_nodes()

    all_issues = []
    broken_links = defaultdict(set)

    # Load the manifest once for shared global state. The migrated
    # manifest-checksum check consumes BaseContext.manifest_entries;
    # legacy manifest checks below still reload independently until
    # they migrate (sessions 2 and 3). Parse-failure handling moved
    # here from the per-check function so the migrated check can
    # assume a clean entry list.
    manifest_entries = []
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH) as f:
                manifest_entries = yaml.safe_load(f) or []
        except yaml.YAMLError as e:
            all_issues.append(Issue("sources/manifest.yaml", "error",
                f"Manifest parse failure: {e}"))
            manifest_entries = []
        if not isinstance(manifest_entries, list):
            all_issues.append(Issue("sources/manifest.yaml", "error",
                "Manifest root must be a list of entries"))
            manifest_entries = []

    base_ctx = BaseContext(schema=schema, manifest_entries=manifest_entries)

    # Source-integrity backstop. Runs once per invocation, before per-node
    # checks. "Do I trust my sources?" is a precondition for interpreting
    # node content; a checksum mismatch means downstream quote verifications
    # may be validating against altered source material.
    #
    # All three manifest checks consume BaseContext.manifest_entries — the
    # orchestrator loads the manifest once (above) and shares. C14 retired
    # at session-2 close (2026-05-05).
    all_issues.extend(ck_manifest_checksums.check(base_ctx))
    all_issues.extend(ck_manifest_archive_status.check(base_ctx))
    all_issues.extend(ck_manifest_extraction_type.check(base_ctx))

    # Governance-file validation (governance-frontmatter check). Every .md under meta/ carries
    # id / type / schema_version / created frontmatter; templates also have
    # a placeholder-shape id. Runs regardless of --path argument because
    # governance files apply to all nodes, not a specific target. Template
    # drift is high-blast-radius (propagates to every node scaffolded
    # afterward) — catching it here prevents silent downstream corruption.
    all_issues.extend(check_governance_files(schema))

    # Required-instance-file check: every toolkit instance must declare its
    # topic scope in meta/topic/overview.md. Catches fork scenarios where
    # meta/topic/ was emptied without recreating overview.md.
    overview_path = REPO_ROOT / "meta" / "topic" / "overview.md"
    if not overview_path.exists():
        all_issues.append(Issue("meta/topic/overview.md", "error",
            "Required file missing — every toolkit instance must declare its "
            "topic scope in meta/topic/overview.md. See README.md for fork "
            "procedure."))

    for node in nodes:
        issues, broken = validate_node(node, schema)
        all_issues.extend(issues)
        for link in broken:
            broken_links[link].add(str(node.relative_to(REPO_ROOT)))

    errors = [i for i in all_issues if i.level == "error"]
    warnings = [i for i in all_issues if i.level == "warn"]

    print("=" * 64)
    print(" Validation Report")
    print("=" * 64)
    print(f"\n  Nodes scanned: {len(nodes)}")
    print(f"  Errors:        {len(errors)}")
    if not args.quiet:
        print(f"  Warnings:      {len(warnings)}")
    print(f"  Broken links:  {len(broken_links)} unbuilt-stub targets (backlog)")

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

    if broken_links and not args.quiet:
        print("\n" + "-" * 64)
        print(" Broken Link Registry")
        print("-" * 64)
        for link in sorted(broken_links.keys()):
            refs = sorted(broken_links[link])
            print(f"\n  {link} ({len(refs)} ref{'s' if len(refs) != 1 else ''})")
            for r in refs:
                print(f"    <- {r}")

    print("\n" + "=" * 64)
    if errors:
        print(f"  FAILED — {len(errors)} error(s)")
        sys.exit(1)
    print(f"  PASSED — {len(warnings)} warning(s)")
    sys.exit(0)


if __name__ == "__main__":
    main()
