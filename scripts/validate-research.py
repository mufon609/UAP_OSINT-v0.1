#!/usr/bin/env python3
"""
Validate research artifacts against meta/schema.yaml.

Structural checks only — does NOT compare against the target node
(that's scripts/review-coverage.py in sub-phase D.4).

Checks (per schema.yaml research-artifact.invariants):
  - Required top-level keys present (id, type, schema_version, target_node,
    status, created, description, primary_sources, document_intrinsic,
    context_extrinsic, quotes, entities_referenced, naming_quirks)
  - id matches file path
  - type == 'research-artifact'
  - schema_version ∈ schema.compatible_with
  - target_node points to an existing content-node .md file
  - status ∈ {active, archived}
  - Per-section entries: required lifecycle fields, unique ids, valid
    enum values
  - primary_sources[].path and sources[].path appear in sources/manifest.yaml
  - entity references[].quote_id points to an existing quote.id
  - Conditional `rumors` section present if target_node type ∈
    {person, organization, event, location}; absent otherwise
  - Conditional `timeline` section present if target_node type ∈
    {person, organization, event, finding}; absent otherwise
  - Per-archetype required section on person artifacts:
      eyewitness          → corroboration_items
      whistleblower       → vouching_chain
      institutional-actor → program_involvement
      reporter            → publication_record
    Each archetype-specific section must be absent on other archetypes.
  - `speakers` section required on every transcript artifact
    (both kinds) — cross-reference surface; entry requires name + source,
    optional role / node_link / note.
  - `observation_type` required on every quote when target_node type is
    person; values ∈ {direct, relayed}. Warned when set on a non-person
    artifact (ignored by renderer).
  - Per-entry enum checks for corroboration_items.observation_type,
    program_involvement.evidentiary_basis / confidence, and
    vouching_chain.evidentiary_basis / confidence.
  - Prose-drift check — extract significant tokens
    (≥3 chars, non-stopword, possessive `'s` stripped) from contributor
    synthesis prose and verify each appears in the referenced primary-
    source text. Impartial reporter: warn on every unmatched token
    regardless of count or field; error only when 100% of a field's
    tokens are absent from source (complete divergence — mathematical,
    not stylistic).

    Scope is CONTRIBUTOR SYNTHESIS PROSE: top-level free-prose fields
    (`description`, `background`, `uap_relevance`, `credibility_notes`)
    and per-entry synthesis content notes (`ownership_timeline.note`,
    `uap_scope_activity.note`, `key_personnel.note`, `contracts.note`,
    `media_versioning.note`, `vouching_chain.attestation`). Applied
    across all renderer-supported types (person, event, transcript,
    media, organization, location). See PROSE_FIELDS_BY_TYPE /
    PROSE_ENTRY_FIELDS_BY_TYPE for exact per-type scope.

    Explicitly OUT of scope: compact label cells (role titles, short
    relationship descriptors, `timeline[].event`, `use_status`,
    `activity`, `contracts.subject`, `publication_record.beat`) and
    cross-reference descriptor notes (`corroboration_items.note`,
    `witnesses_testimony.note`, `org_relationships.note`,
    `location_relationships.note`). Token-match misfires on label
    cells and meta-descriptors; fabrication in those cells is Phase
    III semantic-review territory. Scope narrowed in two passes on
    2026-04-21 (commits 8667590 + df743fe).

Usage:
  validate-research.py                  # validate all research/*.yaml
  validate-research.py PATH             # validate one file
  validate-research.py --quiet          # errors only
"""

import argparse
import subprocess
import re
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
SCHEMA_PATH = REPO_ROOT / "meta" / "schema.yaml"
MANIFEST_PATH = REPO_ROOT / "sources" / "manifest.yaml"
RESEARCH_DIR = REPO_ROOT / "research"
SOURCES_DIR = REPO_ROOT / "sources"

RUMORS_TYPES = {"person", "organization", "event", "location"}
TIMELINE_TYPES = {"person", "organization", "event", "finding"}

# Archetype → required artifact section (only on person artifacts)
ARCHETYPE_REQUIRED_SECTION = {
    "eyewitness":           "corroboration_items",
    "institutional-actor":  "program_involvement",
    "reporter":             "publication_record",
    "whistleblower":        "vouching_chain",
}

# Person-artifact-specific required keys beyond the universal top-level
# list. These carry the prose and structured data for the biographical
# sections the person renderer emits.
PERSON_REQUIRED_KEYS = [
    "background",         # prose; renders as `## Background`
    "uap_relevance",      # prose; renders as `## UAP Relevance`
    "affiliations",       # list of affiliation entries
    "relationships",      # list of relationship entries
    "credibility_notes",  # prose; renders as `## Credibility Notes`
]

# Event-artifact-specific required keys. Event structure differs
# meaningfully by kind (hearing vs encounter); kind-conditional sections
# are layered on top of these universal event requirements.
EVENT_REQUIRED_KEYS = [
    "event_intrinsic",    # dict of kind-conditional metadata; renders
                          # as `## Event Summary` table
    "participants",       # list of participant entries; renders as
                          # `## Participants` (hearings sub-structure;
                          # encounters flat Confirmed/Flagged)
]

# Kind → required artifact section (only on event artifacts).
EVENT_KIND_REQUIRED_SECTION = {
    "hearing":   "witnesses_testimony",
    "encounter": "corroboration_items",
}

# Organization-artifact-specific required keys (universal across the three
# kinds — gov, gov-contractor, private). key_personnel is the cross-
# reference surface (people + sourced roles); org_relationships carries
# org-to-org structured links. Kind-specific sections (contracts for
# gov-contractor) layered on top of these via ORG_KIND_REQUIRED_SECTION.
ORGANIZATION_REQUIRED_KEYS = [
    "key_personnel",
    "org_relationships",
]

# Kind → required artifact section (only on organization artifacts).
# Only gov-contractor carries the contracts list; gov and private have
# no kind-specific sections beyond ORGANIZATION_REQUIRED_KEYS.
ORGANIZATION_KIND_REQUIRED_SECTION = {
    "gov-contractor": "contracts",
}

# Location-artifact-specific required keys. ownership_timeline is the
# chronological ownership-transition record; uap_scope_activity tracks
# institutional UAP-scope activity at the location; location_relationships
# is heterogeneous entity_path links to connected nodes. All three
# required on every location artifact regardless of status.
LOCATION_REQUIRED_KEYS = [
    "ownership_timeline",
    "uap_scope_activity",
    "location_relationships",
]

TYPE_DIRS = {
    "person": "people", "organization": "organizations", "document": "documents",
    "event": "events", "transcript": "transcripts", "media": "media",
    "location": "locations", "finding": "findings",
}

REQUIRED_TOP_LEVEL_KEYS = [
    "id", "type", "schema_version", "target_node", "status", "created",
    "primary_sources", "document_intrinsic",
    "context_extrinsic", "quotes", "entities_referenced",
    "naming_quirks",
]

# `description` is required on all artifact types EXCEPT person. Person
# body renderer (render_body_person) emits Background / UAP Relevance /
# Credibility Notes from dedicated fields and never calls
# render_description, so a populated description on a person artifact
# is unrendered content. Enforced after target_type is read below so
# the requirement is type-conditional; person artifacts may omit
# description entirely.
DESCRIPTION_REQUIRED_TYPES = {
    "document", "transcript", "media", "event",
    "organization", "finding", "location",
}

# All entry-bearing typed sections that participate in lifecycle-field
# and cross-ref checks (check_cross_refs). A section listed here need
# not be present on every artifact — presence is gated elsewhere by
# type / kind / archetype conditional rules. `_entries()` returns an
# empty list for absent sections, so enumerating all sections is safe
# regardless of which ones any given artifact carries.
#
# Update this list when a new typed section is introduced (e.g., new F-
# sub-phase sections). Single source of truth avoids cross-ref gaps
# where new typed sections (timeline / affiliations / key_personnel /
# contracts / etc.) get structurally validated per-section but miss
# the superseded_by / contradicted_by / corroborated_by ref check.
ALL_ENTRY_SECTIONS = [
    # Universal (top-level required on every artifact)
    "quotes",
    "entities_referenced",
    "naming_quirks",
    # Type-conditional
    "rumors",
    "timeline",
    # Person
    "affiliations",
    "relationships",
    "corroboration_items",
    "program_involvement",
    "publication_record",
    "vouching_chain",
    # Event
    "participants",
    "witnesses_testimony",
    # Transcript
    "speakers",
    # Media
    "media_versioning",
    # Organization
    "key_personnel",
    "org_relationships",
    "contracts",
    # Location
    "ownership_timeline",
    "uap_scope_activity",
    "location_relationships",
]

# Per-entry enum values
VALID_NAMING_QUIRK_RESOLUTIONS = {
    "preserve-as-sic-in-quotes", "use-canonical", "disputed", "unresolved"
}
VALID_RUMOR_STATUSES = {
    "not-primary-source-established",
    "primary-source-disputed",
}
VALID_ENTITY_TYPES = {
    "person", "organization", "document", "event", "transcript",
    "media", "location", "finding"
}
VALID_STATUS = {"active", "archived"}
VALID_OBSERVATION_TYPES = {"direct", "relayed"}
VALID_CORROBORATION_OBS_TYPES = {
    "testimonial", "instrumented", "government-statement", "documentary"
}
VALID_EVIDENTIARY_BASIS = {
    "primary-source", "sworn-testimony", "on-record", "self-attested", "secondary"
}
VALID_CONFIDENCE = {"high", "medium", "low"}
VALID_PARTICIPANT_CAPACITY = {
    "witness-eyewitness", "witness-whistleblower", "witness-institutional",
    "committee-member", "observer", "official", "other",
}
VALID_OATH_STATUS = {"sworn", "unsworn", "affirmation", "unknown"}
VALID_MEDIA_VERSIONING_ASPECT = {
    "duration", "encoding", "metadata", "content", "provenance", "other",
}
VALID_LEADERSHIP_CLASS = {
    "director", "deputy", "staff", "advisor", "other",
}
VALID_ORG_RELATIONSHIP_TYPE = {
    "parent", "subsidiary", "predecessor", "successor",
    "contractor", "contracting-agency", "partner", "other",
}


# =============================================================================
# Types and reporting
# =============================================================================

class Issue:
    def __init__(self, path, level, message):
        self.path = str(path)
        self.level = level  # "error" or "warn"
        self.message = message


# =============================================================================
# Loading
# =============================================================================

def load_schema():
    with open(SCHEMA_PATH) as f:
        return yaml.safe_load(f)


def load_manifest_paths():
    """Return set of path strings registered in sources/manifest.yaml."""
    if not MANIFEST_PATH.exists():
        return set()
    with open(MANIFEST_PATH) as f:
        entries = yaml.safe_load(f) or []
    return {e.get("path") for e in entries if e.get("path")}


def load_artifact(path):
    """Load a research artifact. Returns (data, error_msg_or_None)."""
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return None, f"YAML parse failure: {e}"
    if not isinstance(data, dict):
        return None, "Research artifact root must be a YAML mapping (dict)"
    return data, None


# Pattern for lines that look like `key: value # more content` where the
# `#` is preceded by whitespace and followed by non-whitespace, inside an
# UNQUOTED scalar value — which YAML silently treats as a comment,
# truncating everything after `#`. Contributors hit this when they type
# prose with embedded "#N" references (like "Issue #3", "channel #23").
# Heuristic: the value portion starts with a non-quote, non-block-scalar
# character, and contains `\s#\S` somewhere. Two common false-positives
# (intentional comments) are explicitly permitted:
#   - Lines where everything before the `#` is a YAML list marker /
#     whitespace only (pure comment line)
#   - Lines where the `#` appears at the very start of the value
#     (e.g., `foo: # just a comment on empty value`) — those don't
#     truncate meaningful content.
_YAML_HASH_COMMENT_PATTERN = re.compile(
    r"^(\s*-?\s*[A-Za-z_][\w-]*:\s+)"      # group 1: key + colon + first whitespace
    r"([^'\"|>#\s].+?)"                      # group 2: unquoted value (non-trivial)
    r"(\s+#\S.*)$"                           # group 3: whitespace + # + non-ws + rest
)


def check_yaml_hash_truncation(path, rel):
    """Pre-parse scan for unquoted scalar values that contain `space+#`
    and get silently truncated by YAML's comment handling. Surfaces as
    warn (not error) — the YAML is technically valid; the validator is
    flagging what's likely a contributor mistake. Zero false-positives
    on deliberate trailing comments is impossible to guarantee with a
    regex alone; the check tolerates one-line comments where the post-`#`
    content is plausibly a contributor note (few characters) and warns
    only when the post-`#` content looks substantive (>= 3 words or
    ends mid-sentence).
    """
    issues = []
    try:
        with open(path) as f:
            raw_lines = f.readlines()
    except OSError:
        return issues
    for lineno, line in enumerate(raw_lines, start=1):
        # Skip block-scalar content (inside | or > blocks we don't track
        # perfectly here, but the regex's value-start-character guard
        # also excludes those). Also skip lines where the key looks like
        # a date field that might legitimately carry a # annotation.
        m = _YAML_HASH_COMMENT_PATTERN.match(line.rstrip("\n"))
        if not m:
            continue
        comment_part = m.group(3).strip()
        # comment_part starts with the `#`; drop it
        post_hash = comment_part[1:].strip()
        # Heuristic: post-# content >= 3 words suggests accidental
        # truncation of prose. Fewer words = plausibly a deliberate
        # terse annotation; don't warn.
        word_count = len(post_hash.split())
        if word_count < 3:
            continue
        issues.append(Issue(rel, "warn",
            f"line {lineno}: value contains ` #` followed by substantive content "
            f"— YAML will silently treat everything after `#` as a comment and "
            f"truncate the scalar. If the `#` is intentional content (e.g., "
            f"\"Issue #3\", \"channel #23\"), quote the entire value "
            f"(single or double quotes) or use a YAML literal block (`|`). "
            f"Post-`#` content that will be truncated: {post_hash[:80]!r}"))
    return issues


# Pattern for unquoted YAML scalar values that contain an inner `: `
# (colon-space) sequence. YAML's block-mapping parser may treat the
# inner `: ` as a nested key/value separator, either parse-erroring or
# silently mis-parsing the scalar. Contributors hit this with prose
# titles that contain a colon ("We are not alone: The UFO whistleblower
# speaks"), descriptions / notes with sub-clauses, and anywhere
# a natural-language subtitle appears in an unquoted scalar.
#
# Heuristic: match the structural shape; skip the two most common
# legitimate cases — URL schemes (http://, https://, mailto:, etc.) and
# digit-preceded colons (line numbers, timestamps) — by inspecting the
# word that precedes the inner colon.
_YAML_COLON_SPACE_PATTERN = re.compile(
    r"^(\s*-?\s*[A-Za-z_][\w-]*:\s+)"      # group 1: outer key + colon + first whitespace
    r"([^'\"|>#\s].*?)"                      # group 2: unquoted value start (non-quote opener)
    r"(\w+):\s+"                             # group 3: word-preceding-inner-colon
    r"(\S.+)$"                               # group 4: substantive post-colon content
)

_URL_SCHEMES_FOR_COLON_SKIP = frozenset({
    "http", "https", "ftp", "ftps", "mailto", "ssh", "file", "git",
    "svn", "ws", "wss", "sftp", "rsync",
})


def check_yaml_colon_space(path, rel):
    """Pre-parse scan for unquoted scalar values containing an inner
    `: ` (colon followed by space). YAML's block-mapping parser may
    treat the inner `: ` as a nested key/value separator, either
    parse-erroring or silently mis-parsing the scalar. Surfaces as
    warn — contributor can quote the value OR replace the inner
    colon with an em-dash `—` / semicolon `;` if typographically
    appropriate.

    Skips URL schemes (word preceding inner colon ∈ known scheme set
    like http, https, mailto) and digit-preceded colons (line numbers,
    timestamps, ordinals). Warns only when the post-colon content is
    ≥2 words, reducing false positives on single-word sub-keys.

    Surfaced during the 2026-04-20 Cluster B hearing-event pilot — a
    NewsNation submission title broke the `publication_record` entry;
    fixed by single-quoting + replacing the inner `:` with an em-dash.
    Parallel pre-parse mechanism to check_yaml_hash_truncation above.
    """
    issues = []
    try:
        with open(path) as f:
            raw_lines = f.readlines()
    except OSError:
        return issues
    for lineno, line in enumerate(raw_lines, start=1):
        m = _YAML_COLON_SPACE_PATTERN.match(line.rstrip("\n"))
        if not m:
            continue
        preceding_word = m.group(3)
        post = m.group(4)
        # Skip URL schemes (http://, https://, mailto:, etc.)
        if preceding_word.lower() in _URL_SCHEMES_FOR_COLON_SKIP:
            continue
        # Skip digit-preceded colons (line numbers, timestamps, ordinals)
        if preceding_word.isdigit():
            continue
        # Require ≥2 post-colon words — single-word sub-keys are
        # rarely prose
        post_words = post.split()
        if len(post_words) < 2:
            continue
        issues.append(Issue(rel, "warn",
            f"line {lineno}: value contains `{preceding_word}: ` (word followed "
            f"by colon + space) inside an unquoted scalar — YAML's block-mapping "
            f"parser may treat the inner `: ` as a key/value separator, either "
            f"causing a parse error or silently truncating the scalar. Fix: "
            f"quote the entire value (single or double quotes), OR replace the "
            f"inner colon with an em-dash `—` / semicolon `;` if typographically "
            f"appropriate. Post-colon content: {post[:60]!r}"))
    return issues


# =============================================================================
# Per-artifact validation
# =============================================================================

def validate_artifact(path, schema, manifest_paths):
    issues = []
    rel = path.relative_to(REPO_ROOT)

    # Pre-parse check: scan for unquoted scalar values truncated by
    # YAML's # comment handling. Runs before yaml.safe_load so the
    # warning fires on contributor-written YAML even when the file
    # parses cleanly.
    issues.extend(check_yaml_hash_truncation(path, rel))

    # Pre-parse check: scan for unquoted scalar values containing an
    # inner `: ` (colon-space) sequence that YAML's block-mapping
    # parser may treat as a nested key/value separator. Same pre-parse
    # philosophy as the hash-truncation check above.
    issues.extend(check_yaml_colon_space(path, rel))

    data, err = load_artifact(path)
    if err:
        issues.append(Issue(rel, "error", err))
        return issues

    # --- Top-level required keys ---
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            issues.append(Issue(rel, "error", f"Missing required top-level key: {key!r}"))

    # Abort further checks if fatal top-level keys are missing
    if "target_node" not in data or "id" not in data or "type" not in data:
        return issues

    # --- id matches file path ---
    expected_id = f"research/{path.stem}"
    if data.get("id") != expected_id:
        issues.append(Issue(rel, "error",
            f"id {data.get('id')!r} does not match file path ({expected_id!r})"))

    # --- type must be research-artifact ---
    if data.get("type") != "research-artifact":
        issues.append(Issue(rel, "error",
            f"type must be 'research-artifact'; got {data.get('type')!r}"))

    # --- schema_version in compatible_with ---
    sv = data.get("schema_version")
    compatible_with = schema.get("schema", {}).get("compatible_with", [1])
    if sv is not None:
        if not isinstance(sv, int) or isinstance(sv, bool):
            issues.append(Issue(rel, "error",
                f"schema_version must be an integer; got {sv!r}"))
        elif sv not in compatible_with:
            current = schema.get("schema", {}).get("version", "?")
            issues.append(Issue(rel, "error",
                f"schema_version {sv} not in compatible_with {compatible_with} "
                f"(current schema version is {current}). "
                f"Migrate per meta/toolkit-notes/schema-migrations/."))

    # --- status value ---
    if data.get("status") not in VALID_STATUS:
        issues.append(Issue(rel, "error",
            f"status must be one of {sorted(VALID_STATUS)}; got {data.get('status')!r}"))

    # --- target_node points to existing .md ---
    target_node = data.get("target_node")
    if target_node:
        target_path = REPO_ROOT / f"{target_node}.md"
        if not target_path.exists():
            issues.append(Issue(rel, "error",
                f"target_node {target_node!r} does not point to an existing file "
                f"({target_path.relative_to(REPO_ROOT)})"))

    # --- Determine target-node type + (for person) archetype + (for event) kind ---
    target_type = None
    target_archetype = None
    target_kind = None
    target_derivation_of = None
    if target_node and "/" in target_node:
        content_dir_name = target_node.split("/", 1)[0]
        reverse_map = {v: k for k, v in TYPE_DIRS.items()}
        target_type = reverse_map.get(content_dir_name)
        if target_node:
            target_path = REPO_ROOT / f"{target_node}.md"
            if target_path.exists():
                fm_of_target = _read_target_frontmatter(target_path)
                if target_type == "person":
                    target_archetype = fm_of_target.get("archetype")
                if target_type in ("event", "transcript", "organization"):
                    target_kind = fm_of_target.get("kind")
                if target_type == "media":
                    target_derivation_of = fm_of_target.get("derivation_of")

    # --- description required on non-person artifacts ---
    # Person body renderer doesn't emit ## Description; other types do.
    # Check placed here so target_type is known.
    if target_type in DESCRIPTION_REQUIRED_TYPES and "description" not in data:
        issues.append(Issue(rel, "error",
            f"Missing required top-level key: 'description' "
            f"(target_node type {target_type!r} renders ## Description "
            f"from this field)"))

    # --- rumors section present iff target type in RUMORS_TYPES ---
    if target_type in RUMORS_TYPES:
        if "rumors" not in data:
            issues.append(Issue(rel, "error",
                f"Required 'rumors' section missing "
                f"(target_node type is {target_type!r}, which requires rumors)"))
    elif target_type is not None:
        if "rumors" in data:
            issues.append(Issue(rel, "error",
                f"'rumors' section should not be present "
                f"(target_node type {target_type!r} does not carry rumors)"))

    # --- timeline section present iff target type in TIMELINE_TYPES ---
    if target_type in TIMELINE_TYPES:
        if "timeline" not in data:
            issues.append(Issue(rel, "error",
                f"Required 'timeline' section missing "
                f"(target_node type is {target_type!r}, which requires timeline)"))
    elif target_type is not None:
        if "timeline" in data:
            issues.append(Issue(rel, "error",
                f"'timeline' section should not be present "
                f"(target_node type {target_type!r} does not carry timeline)"))

    # --- Archetype-specific sections (person artifacts only) ---
    # ARCHETYPE_REQUIRED_SECTION maps {archetype -> required section}.
    # For the artifact's target archetype, the matching section must be
    # present; the other three must be absent. This enforces the 1-to-1
    # rule: each person node carries exactly one archetype-specific
    # artifact section, determined by its archetype.
    #
    # `corroboration_items` is shared between eyewitness person artifacts
    # and encounter event artifacts — the absent-on-other-archetypes
    # check is relaxed for that section specifically so encounter events
    # can carry it without triggering a false positive.
    if target_type == "person" and target_archetype:
        for arch_name, section in ARCHETYPE_REQUIRED_SECTION.items():
            if arch_name == target_archetype:
                if section not in data:
                    issues.append(Issue(rel, "error",
                        f"Required {section!r} section missing "
                        f"(target archetype is {target_archetype!r}, "
                        f"which requires {section!r})"))
            else:
                if section in data:
                    issues.append(Issue(rel, "error",
                        f"{section!r} section should not be present "
                        f"(target archetype {target_archetype!r} does not carry it — "
                        f"that section belongs to {arch_name!r})"))

    # --- Person-artifact biographical sections (type-conditional) ---
    # background / uap_relevance / affiliations / relationships /
    # credibility_notes are required on every person artifact regardless
    # of archetype. The renderer consumes these to populate the
    # corresponding node sections; missing means the renderer emits
    # TODO stubs. Enforced as required so artifacts are always
    # renderer-ready.
    if target_type == "person":
        for key in PERSON_REQUIRED_KEYS:
            if key not in data:
                issues.append(Issue(rel, "error",
                    f"Required {key!r} key missing "
                    f"(person artifacts require {', '.join(PERSON_REQUIRED_KEYS)})"))
    elif target_type is not None:
        # On non-person artifacts, these keys shouldn't be set (the
        # renderer won't know what to do with them)
        for key in PERSON_REQUIRED_KEYS:
            if key in data:
                issues.append(Issue(rel, "error",
                    f"{key!r} key should not be present "
                    f"(target_node type {target_type!r} is not person)"))

    # --- Event-artifact universal sections (type-conditional) ---
    # event_intrinsic + participants required on every event artifact
    # regardless of kind. Kind-specific sections (witnesses_testimony
    # for hearing; corroboration_items for encounter) layered below.
    if target_type == "event":
        for key in EVENT_REQUIRED_KEYS:
            if key not in data:
                issues.append(Issue(rel, "error",
                    f"Required {key!r} key missing "
                    f"(event artifacts require {', '.join(EVENT_REQUIRED_KEYS)})"))
    elif target_type is not None:
        for key in EVENT_REQUIRED_KEYS:
            if key in data:
                issues.append(Issue(rel, "error",
                    f"{key!r} key should not be present "
                    f"(target_node type {target_type!r} is not event)"))

    # --- Event-kind-specific sections (kind-conditional on event) ---
    # Exactly one of witnesses_testimony (hearing) / corroboration_items
    # (encounter) on an event artifact. Note: corroboration_items is
    # also valid on eyewitness person artifacts — its absence-check is
    # only enforced between the two event kinds, not on person-scoped
    # artifacts.
    if target_type == "event" and target_kind:
        required_kind_section = EVENT_KIND_REQUIRED_SECTION.get(target_kind)
        for kind_name, section in EVENT_KIND_REQUIRED_SECTION.items():
            if kind_name == target_kind:
                if section not in data:
                    issues.append(Issue(rel, "error",
                        f"Required {section!r} section missing "
                        f"(target event kind is {target_kind!r}, "
                        f"which requires {section!r})"))
            else:
                if section in data:
                    issues.append(Issue(rel, "error",
                        f"{section!r} section should not be present "
                        f"(target event kind {target_kind!r} does not carry it — "
                        f"that section belongs to kind {kind_name!r})"))

    # --- Transcript-universal sections (type-conditional on transcript) ---
    # `speakers` required on every transcript artifact regardless of kind.
    # Cross-reference surface; renders as `## Speakers` section.
    if target_type == "transcript":
        if "speakers" not in data:
            issues.append(Issue(rel, "error",
                "Required 'speakers' section missing "
                "(transcript artifacts require speakers)"))
    elif target_type is not None:
        if "speakers" in data:
            issues.append(Issue(rel, "error",
                "'speakers' section should not be present "
                f"(target_node type {target_type!r} is not transcript)"))

    # --- Media-universal sections (type-conditional on media) ---
    # `media_versioning` required on every media artifact regardless of
    # kind. Empty list permitted (canonical / original media with no
    # derivation); populated when the node's frontmatter has
    # derivation_of set and the derivative differs from its parent
    # across one or more aspects. Renderer emits the `## Media
    # Versioning` section only when entries exist.
    if target_type == "media":
        if "media_versioning" not in data:
            issues.append(Issue(rel, "error",
                "Required 'media_versioning' section missing "
                "(media artifacts require media_versioning — empty list "
                "permitted for canonical / original media)"))
        else:
            # Empty list is permitted, but if the target node frontmatter
            # has derivation_of set, an empty media_versioning is likely
            # a contributor-forgot-to-populate signal. Warn (not error)
            # per the impartial-validator policy — contributor reviews
            # and decides if the derivative has no material differences
            # worth recording, or if the artifact needs population.
            mv = data.get("media_versioning") or []
            if target_derivation_of and not mv:
                issues.append(Issue(rel, "warn",
                    f"media_versioning is empty but target node has "
                    f"derivation_of={target_derivation_of!r} set — "
                    f"derivative media nodes typically document at least "
                    f"one parent/derivative difference (duration, encoding, "
                    f"metadata, content, provenance). Populate media_versioning "
                    f"or confirm the derivative is byte-identical to the "
                    f"parent (in which case derivation_of itself may not be "
                    f"warranted)."))
    elif target_type is not None:
        if "media_versioning" in data:
            issues.append(Issue(rel, "error",
                "'media_versioning' section should not be present "
                f"(target_node type {target_type!r} is not media)"))

    # --- Organization-universal sections (type-conditional on organization) ---
    # key_personnel + org_relationships required on every organization
    # artifact regardless of kind. Kind-specific section (contracts for
    # gov-contractor) layered below via ORGANIZATION_KIND_REQUIRED_SECTION.
    if target_type == "organization":
        for key in ORGANIZATION_REQUIRED_KEYS:
            if key not in data:
                issues.append(Issue(rel, "error",
                    f"Required {key!r} key missing "
                    f"(organization artifacts require "
                    f"{', '.join(ORGANIZATION_REQUIRED_KEYS)})"))
    elif target_type is not None:
        for key in ORGANIZATION_REQUIRED_KEYS:
            if key in data:
                issues.append(Issue(rel, "error",
                    f"{key!r} key should not be present "
                    f"(target_node type {target_type!r} is not organization)"))

    # --- Organization-kind-specific sections (kind-conditional on organization) ---
    # Only gov-contractor carries contracts. gov and private kinds must
    # NOT carry it; gov-contractor MUST carry it (empty list permitted
    # for contracts not yet archived).
    if target_type == "organization" and target_kind:
        for kind_name, section in ORGANIZATION_KIND_REQUIRED_SECTION.items():
            if kind_name == target_kind:
                if section not in data:
                    issues.append(Issue(rel, "error",
                        f"Required {section!r} section missing "
                        f"(target organization kind is {target_kind!r}, "
                        f"which requires {section!r})"))
            else:
                if section in data:
                    issues.append(Issue(rel, "error",
                        f"{section!r} section should not be present "
                        f"(target organization kind {target_kind!r} does "
                        f"not carry it — that section belongs to kind "
                        f"{kind_name!r})"))

    # --- Location-universal sections (type-conditional on location) ---
    # ownership_timeline + uap_scope_activity + location_relationships
    # required on every location artifact. Empty lists permitted at
    # scaffold time; populated during Phase I. Location has no kinds,
    # so no kind-conditional sections layer on top.
    if target_type == "location":
        for key in LOCATION_REQUIRED_KEYS:
            if key not in data:
                issues.append(Issue(rel, "error",
                    f"Required {key!r} key missing "
                    f"(location artifacts require "
                    f"{', '.join(LOCATION_REQUIRED_KEYS)})"))
    elif target_type is not None:
        for key in LOCATION_REQUIRED_KEYS:
            if key in data:
                issues.append(Issue(rel, "error",
                    f"{key!r} key should not be present "
                    f"(target_node type {target_type!r} is not location)"))

    # --- primary_sources: path must exist in manifest ---
    issues.extend(check_primary_sources(rel, data, manifest_paths))

    # --- Per-section entry checks ---
    issues.extend(check_quotes(rel, data, manifest_paths, target_type))
    issues.extend(check_entities(rel, data))
    issues.extend(check_naming_quirks(rel, data, manifest_paths))
    if "rumors" in data:
        issues.extend(check_rumors(rel, data))
    if "timeline" in data:
        issues.extend(check_timeline(rel, data, manifest_paths))
    if "corroboration_items" in data:
        issues.extend(check_corroboration_items(rel, data, manifest_paths))
    if "program_involvement" in data:
        issues.extend(check_program_involvement(rel, data, manifest_paths))
    if "publication_record" in data:
        issues.extend(check_publication_record(rel, data, manifest_paths))
    if "vouching_chain" in data:
        issues.extend(check_vouching_chain(rel, data, manifest_paths))
    if "affiliations" in data:
        issues.extend(check_affiliations(rel, data, manifest_paths))
    if "relationships" in data:
        issues.extend(check_relationships(rel, data, manifest_paths))
    if "participants" in data:
        issues.extend(check_participants(rel, data, manifest_paths))
    if "witnesses_testimony" in data:
        issues.extend(check_witnesses_testimony(rel, data, manifest_paths))
    if "speakers" in data:
        issues.extend(check_speakers(rel, data, manifest_paths))
    if "media_versioning" in data:
        issues.extend(check_media_versioning(rel, data, manifest_paths))
    if "key_personnel" in data:
        issues.extend(check_key_personnel(rel, data, manifest_paths))
    if "org_relationships" in data:
        issues.extend(check_org_relationships(rel, data, manifest_paths))
    if "contracts" in data:
        issues.extend(check_contracts(rel, data, manifest_paths))
    if "ownership_timeline" in data:
        issues.extend(check_ownership_timeline(rel, data, manifest_paths))
    if "uap_scope_activity" in data:
        issues.extend(check_uap_scope_activity(rel, data, manifest_paths))
    if "location_relationships" in data:
        issues.extend(check_location_relationships(rel, data, manifest_paths))

    # --- Cross-ref integrity (entity references, supersedes/etc) ---
    issues.extend(check_cross_refs(rel, data))

    # --- Prose-drift check ---
    # Contributor-prose surfaces that aren't covered by the verbatim-
    # quote check. Scoped per-type; no-ops on types without registered
    # prose fields (documents carry no contributor-prose layer; their
    # evidentiary content is verbatim Key Passages).
    issues.extend(check_prose_drift(rel, data, target_type))

    return issues


# =============================================================================
# Section-level check helpers
# =============================================================================

def _entries(data, section):
    """Return list of entries in named section, or []. Always a list."""
    v = data.get(section)
    return v if isinstance(v, list) else []


def _check_unique_ids(rel, entries, section_name):
    issues = []
    seen = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            issues.append(Issue(rel, "error",
                f"{section_name}[{i}]: entry must be a dict"))
            continue
        eid = entry.get("id")
        if eid is None:
            issues.append(Issue(rel, "error",
                f"{section_name}[{i}]: missing required 'id' field"))
            continue
        if eid in seen:
            issues.append(Issue(rel, "error",
                f"{section_name}[{i}]: duplicate id {eid!r}"))
        seen.add(eid)
    return issues


def _check_lifecycle_fields(rel, entry, section_name, i):
    """Every entry requires id, added_date."""
    issues = []
    required = ["id", "added_date"]
    for field in required:
        if field not in entry:
            issues.append(Issue(rel, "error",
                f"{section_name}[{i}] ({entry.get('id', '?')!r}): "
                f"missing required lifecycle field {field!r}"))
    return issues


def check_primary_sources(rel, data, manifest_paths):
    issues = []
    sources = _entries(data, "primary_sources")
    for i, src in enumerate(sources):
        if not isinstance(src, dict):
            issues.append(Issue(rel, "error", f"primary_sources[{i}]: must be a dict"))
            continue
        if "path" not in src:
            issues.append(Issue(rel, "error", f"primary_sources[{i}]: missing required 'path'"))
            continue
        if "format" not in src:
            issues.append(Issue(rel, "error", f"primary_sources[{i}]: missing required 'format'"))
        if src["path"] not in manifest_paths:
            issues.append(Issue(rel, "error",
                f"primary_sources[{i}]: path {src['path']!r} not registered in sources/manifest.yaml"))
    return issues


def _read_target_frontmatter(target_path):
    """Read a target-node file's frontmatter and return it as a dict
    (archetype / kind / etc.), or {} on any failure. Used by
    validate_artifact to route archetype-specific and kind-specific
    section requirements.
    """
    try:
        text = target_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return {}


def check_quotes(rel, data, manifest_paths, target_type=None):
    issues = []
    quotes = _entries(data, "quotes")
    issues.extend(_check_unique_ids(rel, quotes, "quotes"))
    for i, q in enumerate(quotes):
        if not isinstance(q, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, q, "quotes", i))
        # Required: text, source
        if "text" not in q:
            issues.append(Issue(rel, "error",
                f"quotes[{i}] ({q.get('id')!r}): missing required 'text'"))
        src = q.get("source")
        if not isinstance(src, dict):
            issues.append(Issue(rel, "error",
                f"quotes[{i}] ({q.get('id')!r}): 'source' must be a dict with path + location"))
            continue
        if "path" not in src or "location" not in src:
            issues.append(Issue(rel, "error",
                f"quotes[{i}] ({q.get('id')!r}): source must include 'path' and 'location'"))
        if src.get("path") and src["path"] not in manifest_paths:
            issues.append(Issue(rel, "error",
                f"quotes[{i}] ({q.get('id')!r}): source.path {src['path']!r} not in sources/manifest.yaml"))
        # observation_type — required on every quote when target_type is
        # person; ignored otherwise. Enum {direct, relayed}.
        # context — required on every quote when target_type is person;
        # optional on non-person artifacts (document / transcript / media
        # carry context at the artifact level). The person renderer
        # composes the Attributed-to row from `context` + `statement_date`;
        # a quote missing context renders without an Attributed-to row,
        # violating the schema's quote_verification_fields requirement.
        if target_type == "person":
            obs = q.get("observation_type")
            if not obs:
                issues.append(Issue(rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): missing required "
                    f"'observation_type' (required on person artifacts; "
                    f"value in {sorted(VALID_OBSERVATION_TYPES)})"))
            elif obs not in VALID_OBSERVATION_TYPES:
                issues.append(Issue(rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): observation_type "
                    f"{obs!r} not in {sorted(VALID_OBSERVATION_TYPES)}"))
            ctx = q.get("context")
            if not ctx or not str(ctx).strip():
                issues.append(Issue(rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): missing required "
                    f"'context' (required on person artifacts so the "
                    f"renderer produces a complete Attributed-to row; "
                    f"describes where / when / under what circumstances "
                    f"the speaker made the statement)"))
        # observation_type on non-person artifacts: unused but tolerated;
        # warn if set since it signals possible confusion.
        elif target_type is not None and q.get("observation_type"):
            issues.append(Issue(rel, "warn",
                f"quotes[{i}] ({q.get('id')!r}): observation_type set on "
                f"a non-person artifact (target_type {target_type!r}) — "
                f"ignored by renderer; consider removing"))
    return issues


def check_entities(rel, data):
    issues = []
    entities = _entries(data, "entities_referenced")
    issues.extend(_check_unique_ids(rel, entities, "entities_referenced"))
    quote_ids = {q.get("id") for q in _entries(data, "quotes") if isinstance(q, dict)}
    for i, e in enumerate(entities):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "entities_referenced", i))
        # Required: entity_type, name, wrap_path
        et = e.get("entity_type")
        if et is None:
            issues.append(Issue(rel, "error",
                f"entities_referenced[{i}] ({e.get('id')!r}): missing 'entity_type'"))
        elif et not in VALID_ENTITY_TYPES:
            issues.append(Issue(rel, "error",
                f"entities_referenced[{i}] ({e.get('id')!r}): entity_type {et!r} "
                f"not in {sorted(VALID_ENTITY_TYPES)}"))
        if not e.get("name"):
            issues.append(Issue(rel, "error",
                f"entities_referenced[{i}] ({e.get('id')!r}): missing 'name'"))
        wp = e.get("wrap_path")
        if not wp:
            issues.append(Issue(rel, "error",
                f"entities_referenced[{i}] ({e.get('id')!r}): missing 'wrap_path'"))
        elif not wp.startswith("/"):
            issues.append(Issue(rel, "error",
                f"entities_referenced[{i}] ({e.get('id')!r}): wrap_path {wp!r} "
                f"must start with '/'"))
        # references are optional; if present, cross-check
        refs = e.get("references", [])
        if isinstance(refs, list):
            for ri, ref in enumerate(refs):
                if not isinstance(ref, dict):
                    continue
                if "quote_id" in ref and ref["quote_id"] not in quote_ids:
                    issues.append(Issue(rel, "error",
                        f"entities_referenced[{i}] ({e.get('id')!r}) references[{ri}]: "
                        f"quote_id {ref['quote_id']!r} does not match any quote.id"))
    return issues


def check_naming_quirks(rel, data, manifest_paths):
    issues = []
    nqs = _entries(data, "naming_quirks")
    issues.extend(_check_unique_ids(rel, nqs, "naming_quirks"))
    for i, nq in enumerate(nqs):
        if not isinstance(nq, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, nq, "naming_quirks", i))
        for field in ["observed", "canonical", "location", "source_path", "resolution"]:
            if field not in nq:
                issues.append(Issue(rel, "error",
                    f"naming_quirks[{i}] ({nq.get('id')!r}): missing required {field!r}"))
        res = nq.get("resolution")
        if res is not None and res not in VALID_NAMING_QUIRK_RESOLUTIONS:
            issues.append(Issue(rel, "error",
                f"naming_quirks[{i}] ({nq.get('id')!r}): resolution {res!r} "
                f"not in {sorted(VALID_NAMING_QUIRK_RESOLUTIONS)}"))
        sp = nq.get("source_path")
        if sp and sp not in manifest_paths:
            issues.append(Issue(rel, "error",
                f"naming_quirks[{i}] ({nq.get('id')!r}): source_path {sp!r} "
                f"not in sources/manifest.yaml"))
    return issues


def check_rumors(rel, data):
    issues = []
    rumors = _entries(data, "rumors")
    issues.extend(_check_unique_ids(rel, rumors, "rumors"))
    for i, r in enumerate(rumors):
        if not isinstance(r, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, r, "rumors", i))
        if "claim" not in r:
            issues.append(Issue(rel, "error",
                f"rumors[{i}] ({r.get('id')!r}): missing required 'claim'"))
        status = r.get("status")
        if status is None:
            issues.append(Issue(rel, "error",
                f"rumors[{i}] ({r.get('id')!r}): missing required 'status'"))
        elif status not in VALID_RUMOR_STATUSES:
            issues.append(Issue(rel, "error",
                f"rumors[{i}] ({r.get('id')!r}): status {status!r} "
                f"not in {sorted(VALID_RUMOR_STATUSES)}"))
    return issues


def _require_source_dict(rel, entry, section_name, i, manifest_paths):
    """Shared per-entry source dict check (path + location; manifest ref).
    Returns a list of Issue; empty when source is valid."""
    issues = []
    src = entry.get("source")
    if not isinstance(src, dict):
        issues.append(Issue(rel, "error",
            f"{section_name}[{i}] ({entry.get('id')!r}): "
            f"'source' must be a dict with path + location"))
        return issues
    if "path" not in src or "location" not in src:
        issues.append(Issue(rel, "error",
            f"{section_name}[{i}] ({entry.get('id')!r}): "
            f"source must include 'path' and 'location'"))
    if src.get("path") and src["path"] not in manifest_paths:
        issues.append(Issue(rel, "error",
            f"{section_name}[{i}] ({entry.get('id')!r}): "
            f"source.path {src['path']!r} not in sources/manifest.yaml"))
    return issues


def check_timeline(rel, data, manifest_paths):
    """timeline[] — aggregated chronological dated facts. Required on
    person / organization / event / finding artifacts. Each entry:
    required {date, event, source}, optional {category, node_link, end_date}.
    """
    issues = []
    tl = _entries(data, "timeline")
    issues.extend(_check_unique_ids(rel, tl, "timeline"))
    for i, e in enumerate(tl):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "timeline", i))
        for field in ["date", "event"]:
            if field not in e:
                issues.append(Issue(rel, "error",
                    f"timeline[{i}] ({e.get('id')!r}): missing required {field!r}"))
        issues.extend(_require_source_dict(rel, e, "timeline", i, manifest_paths))
    return issues


def check_corroboration_items(rel, data, manifest_paths):
    """corroboration_items[] — present on eyewitness person artifacts.
    Each entry: required {observer_path, observation_type, source},
    optional {observed_event_ref, note}.
    """
    issues = []
    items = _entries(data, "corroboration_items")
    issues.extend(_check_unique_ids(rel, items, "corroboration_items"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "corroboration_items", i))
        for field in ["observer_path", "observation_type"]:
            if field not in e:
                issues.append(Issue(rel, "error",
                    f"corroboration_items[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}"))
        ot = e.get("observation_type")
        if ot and ot not in VALID_CORROBORATION_OBS_TYPES:
            issues.append(Issue(rel, "error",
                f"corroboration_items[{i}] ({e.get('id')!r}): "
                f"observation_type {ot!r} not in "
                f"{sorted(VALID_CORROBORATION_OBS_TYPES)}"))
        # observer_path leading-slash check (cross-node ref)
        op = e.get("observer_path")
        if op and not op.startswith("/"):
            issues.append(Issue(rel, "error",
                f"corroboration_items[{i}] ({e.get('id')!r}): "
                f"observer_path {op!r} must start with '/'"))
        issues.extend(_require_source_dict(rel, e, "corroboration_items", i, manifest_paths))
    return issues


def check_program_involvement(rel, data, manifest_paths):
    """program_involvement[] — present on institutional-actor person
    artifacts. Each entry: required {program, role, evidentiary_basis,
    confidence, source}, optional {start_date, end_date, note}.
    """
    issues = []
    items = _entries(data, "program_involvement")
    issues.extend(_check_unique_ids(rel, items, "program_involvement"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "program_involvement", i))
        for field in ["program", "role", "evidentiary_basis", "confidence"]:
            if field not in e:
                issues.append(Issue(rel, "error",
                    f"program_involvement[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}"))
        eb = e.get("evidentiary_basis")
        if eb and eb not in VALID_EVIDENTIARY_BASIS:
            issues.append(Issue(rel, "error",
                f"program_involvement[{i}] ({e.get('id')!r}): "
                f"evidentiary_basis {eb!r} not in "
                f"{sorted(VALID_EVIDENTIARY_BASIS)}"))
        conf = e.get("confidence")
        if conf and conf not in VALID_CONFIDENCE:
            issues.append(Issue(rel, "error",
                f"program_involvement[{i}] ({e.get('id')!r}): "
                f"confidence {conf!r} not in {sorted(VALID_CONFIDENCE)}"))
        issues.extend(_require_source_dict(rel, e, "program_involvement", i, manifest_paths))
    return issues


def check_publication_record(rel, data, manifest_paths):
    """publication_record[] — present on reporter person artifacts.
    Each entry: required {publication, outlet, date, source},
    optional {node_link, beat, note}.
    """
    issues = []
    items = _entries(data, "publication_record")
    issues.extend(_check_unique_ids(rel, items, "publication_record"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "publication_record", i))
        for field in ["publication", "outlet", "date"]:
            if field not in e:
                issues.append(Issue(rel, "error",
                    f"publication_record[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}"))
        issues.extend(_require_source_dict(rel, e, "publication_record", i, manifest_paths))
    return issues


def check_affiliations(rel, data, manifest_paths):
    """affiliations[] — present on person artifacts. Each entry:
    required {organization_path, role, source}, optional
    {period_start, period_end, flagged, note}.
    """
    issues = []
    items = _entries(data, "affiliations")
    issues.extend(_check_unique_ids(rel, items, "affiliations"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "affiliations", i))
        for field in ["organization_path", "role"]:
            if field not in e:
                issues.append(Issue(rel, "error",
                    f"affiliations[{i}] ({e.get('id')!r}): missing required {field!r}"))
        op = e.get("organization_path")
        if op and not op.startswith("/"):
            issues.append(Issue(rel, "error",
                f"affiliations[{i}] ({e.get('id')!r}): "
                f"organization_path {op!r} must start with '/'"))
        issues.extend(_require_source_dict(rel, e, "affiliations", i, manifest_paths))
    return issues


def check_relationships(rel, data, manifest_paths):
    """relationships[] — present on person artifacts. Each entry:
    required {person_path, relationship, source}, optional
    {flagged, note}.
    """
    issues = []
    items = _entries(data, "relationships")
    issues.extend(_check_unique_ids(rel, items, "relationships"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "relationships", i))
        for field in ["person_path", "relationship"]:
            if field not in e:
                issues.append(Issue(rel, "error",
                    f"relationships[{i}] ({e.get('id')!r}): missing required {field!r}"))
        pp = e.get("person_path")
        if pp and not pp.startswith("/"):
            issues.append(Issue(rel, "error",
                f"relationships[{i}] ({e.get('id')!r}): "
                f"person_path {pp!r} must start with '/'"))
        issues.extend(_require_source_dict(rel, e, "relationships", i, manifest_paths))
    return issues


def check_participants(rel, data, manifest_paths):
    """participants[] — present on event artifacts. Each entry:
    required {participant_path, capacity, source}, optional
    {role, flagged, note}. capacity ∈ VALID_PARTICIPANT_CAPACITY.
    """
    issues = []
    items = _entries(data, "participants")
    issues.extend(_check_unique_ids(rel, items, "participants"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "participants", i))
        for field in ["participant_path", "capacity"]:
            if field not in e:
                issues.append(Issue(rel, "error",
                    f"participants[{i}] ({e.get('id')!r}): missing required {field!r}"))
        pp = e.get("participant_path")
        if pp and not pp.startswith("/"):
            issues.append(Issue(rel, "error",
                f"participants[{i}] ({e.get('id')!r}): "
                f"participant_path {pp!r} must start with '/'"))
        cap = e.get("capacity")
        if cap and cap not in VALID_PARTICIPANT_CAPACITY:
            issues.append(Issue(rel, "error",
                f"participants[{i}] ({e.get('id')!r}): "
                f"capacity {cap!r} not in {sorted(VALID_PARTICIPANT_CAPACITY)}"))
        issues.extend(_require_source_dict(rel, e, "participants", i, manifest_paths))
    return issues


def check_witnesses_testimony(rel, data, manifest_paths):
    """witnesses_testimony[] — present on hearing-kind event artifacts.
    Each entry: required {witness_path, oath_status, source}, optional
    {transcript_node, written_testimony_node, note}.
    """
    issues = []
    items = _entries(data, "witnesses_testimony")
    issues.extend(_check_unique_ids(rel, items, "witnesses_testimony"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "witnesses_testimony", i))
        for field in ["witness_path", "oath_status"]:
            if field not in e:
                issues.append(Issue(rel, "error",
                    f"witnesses_testimony[{i}] ({e.get('id')!r}): missing required {field!r}"))
        wp = e.get("witness_path")
        if wp and not wp.startswith("/"):
            issues.append(Issue(rel, "error",
                f"witnesses_testimony[{i}] ({e.get('id')!r}): "
                f"witness_path {wp!r} must start with '/'"))
        oath = e.get("oath_status")
        if oath and oath not in VALID_OATH_STATUS:
            issues.append(Issue(rel, "error",
                f"witnesses_testimony[{i}] ({e.get('id')!r}): "
                f"oath_status {oath!r} not in {sorted(VALID_OATH_STATUS)}"))
        # Optional cross-references: check leading slash if set
        for optional_path_field in ("transcript_node", "written_testimony_node"):
            v = e.get(optional_path_field)
            if v and not v.startswith("/"):
                issues.append(Issue(rel, "error",
                    f"witnesses_testimony[{i}] ({e.get('id')!r}): "
                    f"{optional_path_field} {v!r} must start with '/'"))
        issues.extend(_require_source_dict(rel, e, "witnesses_testimony", i, manifest_paths))
    return issues


def check_speakers(rel, data, manifest_paths):
    """speakers[] — present on every transcript artifact. Each entry:
    required {name, source}, optional {role, node_link, note}.
    """
    issues = []
    items = _entries(data, "speakers")
    issues.extend(_check_unique_ids(rel, items, "speakers"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "speakers", i))
        if "name" not in e or not str(e.get("name") or "").strip():
            issues.append(Issue(rel, "error",
                f"speakers[{i}] ({e.get('id')!r}): missing required 'name'"))
        nl = e.get("node_link")
        if nl and not str(nl).startswith("/"):
            issues.append(Issue(rel, "error",
                f"speakers[{i}] ({e.get('id')!r}): "
                f"node_link {nl!r} must start with '/'"))
        issues.extend(_require_source_dict(rel, e, "speakers", i, manifest_paths))
    return issues


def check_media_versioning(rel, data, manifest_paths):
    """media_versioning[] — present on every media artifact. Empty list
    permitted for canonical / original media; populated when the node's
    frontmatter has derivation_of set and the derivative differs from
    its parent across one or more aspects. Each entry: required
    {id, aspect, parent_form, this_form, source}, optional {note}.
    aspect ∈ VALID_MEDIA_VERSIONING_ASPECT (warn on unknown; `other`
    permitted as an extensibility escape).
    """
    issues = []
    items = _entries(data, "media_versioning")
    issues.extend(_check_unique_ids(rel, items, "media_versioning"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "media_versioning", i))
        # Required fields
        for field in ["aspect", "parent_form", "this_form"]:
            if field not in e or not str(e.get(field) or "").strip():
                issues.append(Issue(rel, "error",
                    f"media_versioning[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}"))
        # aspect enum — warn on unknown (parallels doc_form extensibility)
        aspect = e.get("aspect")
        if aspect is not None and aspect not in VALID_MEDIA_VERSIONING_ASPECT:
            issues.append(Issue(rel, "warn",
                f"media_versioning[{i}] ({e.get('id')!r}): "
                f"aspect {aspect!r} not in "
                f"{sorted(VALID_MEDIA_VERSIONING_ASPECT)} — "
                f"extensible vocabulary, but unexpected values may indicate "
                f"a missing enum entry worth schema discussion."))
        # source required
        issues.extend(_require_source_dict(rel, e, "media_versioning", i, manifest_paths))
    return issues


def check_vouching_chain(rel, data, manifest_paths):
    """vouching_chain[] — present on whistleblower person artifacts.
    Each entry: required {voucher_path, attestation, source},
    optional {evidentiary_basis, confidence, note}.
    """
    issues = []
    items = _entries(data, "vouching_chain")
    issues.extend(_check_unique_ids(rel, items, "vouching_chain"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "vouching_chain", i))
        for field in ["voucher_path", "attestation"]:
            if field not in e:
                issues.append(Issue(rel, "error",
                    f"vouching_chain[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}"))
        vp = e.get("voucher_path")
        if vp and not vp.startswith("/"):
            issues.append(Issue(rel, "error",
                f"vouching_chain[{i}] ({e.get('id')!r}): "
                f"voucher_path {vp!r} must start with '/'"))
        eb = e.get("evidentiary_basis")
        if eb and eb not in VALID_EVIDENTIARY_BASIS:
            issues.append(Issue(rel, "error",
                f"vouching_chain[{i}] ({e.get('id')!r}): "
                f"evidentiary_basis {eb!r} not in "
                f"{sorted(VALID_EVIDENTIARY_BASIS)}"))
        conf = e.get("confidence")
        if conf and conf not in VALID_CONFIDENCE:
            issues.append(Issue(rel, "error",
                f"vouching_chain[{i}] ({e.get('id')!r}): "
                f"confidence {conf!r} not in {sorted(VALID_CONFIDENCE)}"))
        issues.extend(_require_source_dict(rel, e, "vouching_chain", i, manifest_paths))
    return issues


def check_key_personnel(rel, data, manifest_paths):
    """key_personnel[] — present on organization artifacts. Each entry:
    required {person_path, role, source}, optional
    {period_start, period_end, leadership_class, flagged, note}.
    leadership_class (when set) ∈ VALID_LEADERSHIP_CLASS.
    """
    issues = []
    items = _entries(data, "key_personnel")
    issues.extend(_check_unique_ids(rel, items, "key_personnel"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "key_personnel", i))
        for field in ["person_path", "role"]:
            if field not in e:
                issues.append(Issue(rel, "error",
                    f"key_personnel[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}"))
        pp = e.get("person_path")
        if pp and not pp.startswith("/"):
            issues.append(Issue(rel, "error",
                f"key_personnel[{i}] ({e.get('id')!r}): "
                f"person_path {pp!r} must start with '/'"))
        lc = e.get("leadership_class")
        if lc is not None and lc not in VALID_LEADERSHIP_CLASS:
            issues.append(Issue(rel, "error",
                f"key_personnel[{i}] ({e.get('id')!r}): "
                f"leadership_class {lc!r} not in "
                f"{sorted(VALID_LEADERSHIP_CLASS)}"))
        issues.extend(_require_source_dict(rel, e, "key_personnel", i, manifest_paths))
    return issues


def check_org_relationships(rel, data, manifest_paths):
    """org_relationships[] — present on organization artifacts. Each entry:
    required {organization_path, relationship_type, source}, optional
    {flagged, note}. relationship_type ∈ VALID_ORG_RELATIONSHIP_TYPE.
    """
    issues = []
    items = _entries(data, "org_relationships")
    issues.extend(_check_unique_ids(rel, items, "org_relationships"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "org_relationships", i))
        for field in ["organization_path", "relationship_type"]:
            if field not in e:
                issues.append(Issue(rel, "error",
                    f"org_relationships[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}"))
        op = e.get("organization_path")
        if op and not op.startswith("/"):
            issues.append(Issue(rel, "error",
                f"org_relationships[{i}] ({e.get('id')!r}): "
                f"organization_path {op!r} must start with '/'"))
        rt = e.get("relationship_type")
        if rt is not None and rt not in VALID_ORG_RELATIONSHIP_TYPE:
            issues.append(Issue(rel, "error",
                f"org_relationships[{i}] ({e.get('id')!r}): "
                f"relationship_type {rt!r} not in "
                f"{sorted(VALID_ORG_RELATIONSHIP_TYPE)}"))
        issues.extend(_require_source_dict(rel, e, "org_relationships", i, manifest_paths))
    return issues


def check_contracts(rel, data, manifest_paths):
    """contracts[] — present on gov-contractor organization artifacts.
    Each entry: required {contract_number, contracting_agency,
    period_start, source}, optional {period_end, primary_counterparty_path,
    subject, value, deliverables, note}.
    """
    issues = []
    items = _entries(data, "contracts")
    issues.extend(_check_unique_ids(rel, items, "contracts"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "contracts", i))
        for field in ["contract_number", "contracting_agency", "period_start"]:
            if field not in e or not str(e.get(field) or "").strip():
                issues.append(Issue(rel, "error",
                    f"contracts[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}"))
        pcp = e.get("primary_counterparty_path")
        if pcp and not pcp.startswith("/"):
            issues.append(Issue(rel, "error",
                f"contracts[{i}] ({e.get('id')!r}): "
                f"primary_counterparty_path {pcp!r} must start with '/'"))
        # deliverables: optional list of /documents/... paths
        deliverables = e.get("deliverables") or []
        if deliverables and not isinstance(deliverables, list):
            issues.append(Issue(rel, "error",
                f"contracts[{i}] ({e.get('id')!r}): "
                f"deliverables must be a list (got {type(deliverables).__name__})"))
        elif isinstance(deliverables, list):
            for j, d in enumerate(deliverables):
                if not isinstance(d, str) or not d.startswith("/"):
                    issues.append(Issue(rel, "error",
                        f"contracts[{i}] ({e.get('id')!r}): "
                        f"deliverables[{j}] must be a repo path starting with '/' "
                        f"(got {d!r})"))
        issues.extend(_require_source_dict(rel, e, "contracts", i, manifest_paths))
    return issues


def check_ownership_timeline(rel, data, manifest_paths):
    """ownership_timeline[] — present on location artifacts. Each entry:
    required {period_start, owner, use_status, source}, optional
    {period_end, owner_path, note}. Chronological ordering enforced at
    node-render time by validate.py's chronological-ordering check against the rendered
    `## Ownership Timeline` table.
    """
    issues = []
    items = _entries(data, "ownership_timeline")
    issues.extend(_check_unique_ids(rel, items, "ownership_timeline"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "ownership_timeline", i))
        for field in ["period_start", "owner", "use_status"]:
            if field not in e or not str(e.get(field) or "").strip():
                issues.append(Issue(rel, "error",
                    f"ownership_timeline[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}"))
        op = e.get("owner_path")
        if op and not str(op).startswith("/"):
            issues.append(Issue(rel, "error",
                f"ownership_timeline[{i}] ({e.get('id')!r}): "
                f"owner_path {op!r} must start with '/'"))
        issues.extend(_require_source_dict(rel, e, "ownership_timeline", i, manifest_paths))
    return issues


def check_uap_scope_activity(rel, data, manifest_paths):
    """uap_scope_activity[] — present on location artifacts. Each entry:
    required {period_start, activity, source}, optional
    {period_end, actor_paths (list), note}. Tracks institutional UAP-
    scope activity at the location; popular paranormal lore without
    primary-source backing belongs in `rumors`, not here.
    """
    issues = []
    items = _entries(data, "uap_scope_activity")
    issues.extend(_check_unique_ids(rel, items, "uap_scope_activity"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "uap_scope_activity", i))
        for field in ["period_start", "activity"]:
            if field not in e or not str(e.get(field) or "").strip():
                issues.append(Issue(rel, "error",
                    f"uap_scope_activity[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}"))
        paths = e.get("actor_paths") or []
        if paths and not isinstance(paths, list):
            issues.append(Issue(rel, "error",
                f"uap_scope_activity[{i}] ({e.get('id')!r}): "
                f"actor_paths must be a list "
                f"(got {type(paths).__name__})"))
        elif isinstance(paths, list):
            for j, p in enumerate(paths):
                if not isinstance(p, str) or not p.startswith("/"):
                    issues.append(Issue(rel, "error",
                        f"uap_scope_activity[{i}] ({e.get('id')!r}): "
                        f"actor_paths[{j}] must be a repo path starting "
                        f"with '/' (got {p!r})"))
        issues.extend(_require_source_dict(rel, e, "uap_scope_activity", i, manifest_paths))
    return issues


def check_location_relationships(rel, data, manifest_paths):
    """location_relationships[] — present on location artifacts. Each
    entry: required {entity_path, relationship, source}, optional
    {flagged, note}. Unlike person.relationships (person-to-person) and
    org_relationships (org-to-org), location_relationships accepts
    heterogeneous entity_path targets — locations connect to anything
    the primary source attests (owners, investigators, events, media,
    adjacent locations, findings).
    """
    issues = []
    items = _entries(data, "location_relationships")
    issues.extend(_check_unique_ids(rel, items, "location_relationships"))
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, e, "location_relationships", i))
        for field in ["entity_path", "relationship"]:
            if field not in e:
                issues.append(Issue(rel, "error",
                    f"location_relationships[{i}] ({e.get('id')!r}): "
                    f"missing required {field!r}"))
        ep = e.get("entity_path")
        if ep and not str(ep).startswith("/"):
            issues.append(Issue(rel, "error",
                f"location_relationships[{i}] ({e.get('id')!r}): "
                f"entity_path {ep!r} must start with '/'"))
        issues.extend(_require_source_dict(rel, e, "location_relationships", i, manifest_paths))
    return issues


# =============================================================================
# Prose-drift check (F.1c RCA follow-up)
#
# Every contributor-authored prose field on an artifact should draw its
# vocabulary from the primary-source text it references. This check
# tokenizes each prose field into significant words (lowercase, ≥3
# chars, non-stopword) and verifies each token appears in the
# referenced source file.
#
# Impartial reporter — the validator surfaces drift; the contributor
# judges each case:
#   - WARN on every unmatched significant token, any field, any count.
#   - ERROR only when 100% of a field's significant tokens are absent
#     from source. 100% divergence is a mathematical observation (no
#     shared vocabulary with the referenced source), not a stylistic
#     threshold.
#
# The validator makes no categorical judgment about which fields are
# "allowed" to have more contributor vocabulary. Synthesis-heavy
# sections and fact-dense sections go through the same rule.
#
# Known limitations:
#   - Membership-only; doesn't catch phrase-restructuring where all
#     words exist in source (e.g., "ground operations" when source has
#     "operations supporting... ground forces" — F.1c drift #1).
#   - No stemming / lemmatization; "prepare" / "preparing" counts as
#     distinct tokens.
#   - No whitelist; repo vocabulary ("disclosure chain", etc.) warns.
#
# Scope is set by PROSE_FIELDS_BY_TYPE and PROSE_ENTRY_FIELDS_BY_TYPE
# below — free-prose synthesis fields and synthesis-content notes
# across all renderer-supported types (person / event / transcript /
# media / organization / location). Narrowed from the pre-2026-04-21
# scope that also covered structural label cells and cross-reference
# descriptor notes; those fire too many false positives for
# token-match to be the right instrument.
# =============================================================================

# Common English stopwords dropped from token-comparison. About 110
# entries; calibrated from the D-era token-drift check plus light
# pruning based on the Fravor i1 audit signal.
STOPWORDS = {
    # Articles
    "a", "an", "the",
    # Pronouns
    "he", "she", "it", "they", "we", "you", "his", "her", "their",
    "its", "our", "my", "your", "this", "that", "these", "those", "who",
    "whom", "whose", "which", "what",
    # Auxiliaries
    "is", "was", "are", "were", "be", "been", "being", "am",
    "have", "has", "had", "do", "does", "did", "done",
    "will", "would", "can", "could", "should", "may", "might", "must",
    "shall",
    # Prepositions
    "of", "in", "on", "at", "to", "from", "for", "with", "by", "as",
    "into", "onto", "upon", "off", "out", "over", "under", "above",
    "below", "between", "among", "through", "during", "within",
    "without", "against", "about", "across", "after", "before", "behind",
    # Conjunctions
    "and", "or", "but", "so", "if", "because", "since", "until",
    "unless", "when", "where", "while", "although", "though", "than",
    "yet", "whether",
    # Negations / degree
    "not", "no", "never", "also", "then", "now", "just", "only", "even",
    "else", "still", "already", "yet", "ever", "again", "very", "too",
    "quite", "rather", "much", "more", "most", "less", "least",
    # Determiners / quantifiers
    "some", "any", "all", "each", "every", "both", "either", "neither",
    "one", "two", "three", "other", "another", "same", "such", "own",
    "here", "there",
    # Common verbs that carry little specific content
    "says", "said", "say", "saying", "went", "goes", "gone", "come",
    "came", "coming", "get", "got", "getting", "make", "made", "making",
    "take", "took", "taking", "taken",
}

# Fields to check, keyed by target_node type.
#
# Scoping principle: the prose-drift check is built for CONTRIBUTOR SYNTHESIS PROSE —
# paragraph-length or sentence-length fields where a contributor is
# narrating from one or more primary sources and can introduce drift
# (dropped qualifiers, synonym rephrase, unstated premise, fabricated
# fact). The check tokenizes the prose and warns on any significant
# token not present in the cited source.
#
# The check is NOT built for STRUCTURAL LABEL CELLS — compact
# navigational metadata like role titles, short relationship
# descriptors, or timeline event cells that aggregate multi-source
# repo understanding into 3–10-word labels. Those cells routinely
# use repo-canonical naming, cross-reference tokens, and dates that
# appear in no single cited source; the token-match premise fails
# and warnings become noise. Fabrication in label cells is Phase III
# semantic-review territory, not token-matching territory.
#
# Top-level prose fields are pooled against the union of all
# primary_sources. Per-entry prose fields use each entry's own
# source.path.
PROSE_FIELDS_BY_TYPE = {
    "person": [
        "background",
        "uap_relevance",
        "credibility_notes",
    ],
    "event": [
        # event-artifact top-level prose is `description` only (shared
        # with the universal artifact schema). Event-specific synthesis
        # fields like Event Summary derive from event_intrinsic dict,
        # not a prose field.
        "description",
    ],
    "media": [
        # Media top-level prose: `description` renders as the
        # `## Description` section — explicitly labeled contributor-
        # authored synthesis per the media template (describe what the
        # source depicts; verbatim extractable content lives in Key
        # Passages). The prose-drift check scans against the union of
        # primary_sources[].path token pools.
        "description",
    ],
    "transcript": [
        # Transcript top-level prose: `description` renders as the
        # `## Summary` section via the F.3b render-time field→section
        # rename (Q1-A decision). Keeps `description` as the universal
        # top-level required field while the rendered section name fits
        # transcript semantics. Closes BACKLOG entry "Transcript top-
        # level description — prose-drift scoping blocked on F.3b
        # renderer" (entered in F.3a, resolved in F.3b).
        "description",
    ],
    "organization": [
        # Organization top-level prose: `description` renders as the
        # `## Description` section — labeled contributor synthesis.
        # Overview section renders from organization-kind keys in
        # document_intrinsic (fact-table dispatch), not from prose, so
        # only `description` is scanned as free-prose.
        "description",
    ],
    "location": [
        # Location top-level prose: `description` renders as the
        # `## Description` section — labeled contributor synthesis.
        # Overview section renders from document_intrinsic location
        # keys (fact-table dispatch, parallel to organization); only
        # `description` is scanned as free-prose.
        "description",
    ],
    # F.7 extension:
    # "finding": ["what_this_establishes", ...],
}

# Per-entry prose fields. Shape: (list_key, field_name_within_entry).
# Each entry's source.path provides the token pool.
#
# Scope limited to SYNTHESIS CONTENT notes — multi-sentence narrative
# or analytical prose about an event / transaction / role / derivation
# (ownership_timeline, uap_scope_activity, contracts, media_versioning,
# key_personnel, vouching_chain.attestation). These describe what
# happened and what it means; drift signal is real and catchable by
# token-matching.
#
# Explicitly NOT in scope: STRUCTURAL DESCRIPTOR NOTES on cross-
# reference entries — corroboration_items.note, witnesses_testimony.note,
# org_relationships.note, location_relationships.note. Those describe
# *why/how a cross-reference exists* (compact meta-descriptors of a
# relationship) rather than narrative synthesis of content. Examples:
#   corroboration_items.note → "Other F/A-18F pilot in Fravor's
#     2-plane flight; testimony confirms wingman also lost visual at
#     intercept" — explains why this observer corroborates (label-like)
#   ownership_timeline.note → "Kenneth John Myers and wife Edith owned
#     the ranch for approximately sixty years. Kenneth died April 1987;
#     Edith lived there alone until 1992 and died March 3, 1994..."
#     — narrates the ownership transition itself (synthesis prose)
# Token-match fits synthesis prose; it routinely misfires on label
# cells. Fabrication in cross-reference label notes is Phase III
# semantic-review territory.
PROSE_ENTRY_FIELDS_BY_TYPE = {
    "person": [
        # vouching_chain[].attestation — paraphrased (or verbatim)
        # statement of a voucher's attestation. Actual attestation
        # content, scanned against source.path.
        ("vouching_chain", "attestation"),
    ],
    "event": [
        # No per-entry synthesis content fields currently in scope.
        # corroboration_items[].note and witnesses_testimony[].note are
        # structural descriptors on cross-reference entries — excluded.
    ],
    "transcript": [
        # No per-entry synthesis content fields currently in scope.
        # speakers[].role is a structural label.
    ],
    "media": [
        # media_versioning[].note — contributor synthesis on the
        # analytical significance of a parent/derivative aspect
        # difference. Multi-sentence content analysis; scanned against
        # the entry's own source.path.
        ("media_versioning", "note"),
    ],
    "organization": [
        # key_personnel[].note — contributor synthesis assessing the
        # evidentiary context of the personnel entry (attestation
        # strength, corroboration, period-date sourcing). Scanned
        # against source.path.
        ("key_personnel", "note"),
        # contracts[].note — contributor synthesis on the contract.
        # Scanned against source.path.
        ("contracts",     "note"),
        # org_relationships[].note EXCLUDED — structural descriptor of
        # the org-to-org relationship (e.g., "AOIMSG established Nov
        # 23, 2021 as the successor to..."), not synthesis prose.
    ],
    "location": [
        # ownership_timeline[].note — multi-sentence narrative about
        # the ownership transition. Scanned against source.path.
        ("ownership_timeline", "note"),
        # uap_scope_activity[].note — multi-sentence narrative about
        # the institutional UAP-scope activity. Scanned against
        # source.path.
        ("uap_scope_activity", "note"),
        # location_relationships[].note EXCLUDED — structural
        # descriptor of the relationship, not synthesis prose.
    ],
}

# Single impartial rule — no field-class differentiation, no percentage
# threshold tuning. The original implementation split errors by field-
# type with a tuned 80% threshold, which encoded a validator-side
# judgment about which fields are "allowed" to carry more contributor-
# synthesis vocabulary (uap_relevance / credibility_notes tolerated
# higher unmatched rates than timeline events). That was bias — the
# validator's role is to surface drift impartially; the contributor
# reviews every warning and decides per-case.
#
# Revised rule:
#   - WARN on every unmatched significant token (any field, any count).
#   - ERROR only when 100% of a field's significant tokens are absent
#     from source. 100% divergence is a mathematical observation
#     (no shared vocabulary with the source the field claims to draw
#     on), not a stylistic threshold. Below 100%, the validator makes
#     no classification — just reports.

# Cache source-file tokens per validator run so a multi-artifact or
# multi-entry run doesn't re-extract the same file N times.
_source_token_cache = {}


def _extract_source_text(source_path_abs):
    """Extract plaintext from a source file. Mirrors the pattern from
    scripts/validate.py's extract_source_text() and scripts/extract-source.py's
    extract() — flat-scripts-pattern duplication rather than a shared lib.
    Returns None on failure (missing pdftotext; unsupported extension;
    read error).
    """
    suffix = source_path_abs.suffix.lower()
    if suffix == ".pdf":
        try:
            proc = subprocess.run(
                ["pdftotext", "-layout", str(source_path_abs), "-"],
                capture_output=True, text=True, timeout=60,
            )
            if proc.returncode == 0:
                return proc.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        return None
    if suffix in (".html", ".htm", ".txt", ".md"):
        try:
            return source_path_abs.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    return None


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
    text = re.sub(r"\[`/[^`]+`\]", "", str(text))
    text = re.sub(r"[*_`]", "", text)
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
    text = text.replace("\u2014", " ").replace("\u2013", "-")
    text = text.lower()
    words = re.findall(r"[a-z0-9][a-z0-9\-']+", text)
    # Strip trailing possessive `'s` to collapse "fravor" ↔ "fravor's".
    # (Leaves intra-word apostrophes alone: "don't" stays "don't".)
    words = [re.sub(r"'s$", "", w) for w in words]
    return {w for w in words if len(w) >= 3 and w not in STOPWORDS}


def load_source_tokens(source_rel_path):
    """Load and tokenize a source file. source_rel_path is relative to
    sources/ (matches the manifest.yaml and artifact source.path shape).
    Cached per-run. Returns a set of significant tokens, or None if the
    source is missing / unextractable.
    """
    if source_rel_path in _source_token_cache:
        return _source_token_cache[source_rel_path]
    source_abs = SOURCES_DIR / source_rel_path
    if not source_abs.exists():
        _source_token_cache[source_rel_path] = None
        return None
    text = _extract_source_text(source_abs)
    if text is None:
        _source_token_cache[source_rel_path] = None
        return None
    tokens = extract_significant_tokens(text)
    _source_token_cache[source_rel_path] = tokens
    return tokens


def _judge_drift(rel, location, prose_tokens, unmatched):
    """Impartial drift reporter. Warns on every unmatched significant
    token; errors only when 100% of the field's significant tokens are
    absent from source (complete vocabulary divergence — mathematical,
    not stylistic). The validator makes no category judgment below
    100% — contributor reviews each warning.
    """
    if not unmatched:
        return []
    preview = ", ".join(sorted(unmatched)[:8])
    if len(unmatched) > 8:
        preview += f", … (+{len(unmatched) - 8} more)"
    if prose_tokens and len(unmatched) == len(prose_tokens):
        return [Issue(rel, "error",
            f"{location}: 100% of significant tokens "
            f"({len(unmatched)}/{len(prose_tokens)}) absent from source "
            f"— prose has no shared vocabulary with the source it "
            f"claims to draw on. Unmatched: {preview}")]
    return [Issue(rel, "warn",
        f"{location}: {len(unmatched)} significant token(s) not in "
        f"source (prose-drift check — contributor review): {preview}")]


def check_prose_drift(rel, data, target_type):
    """Prose-drift check — verify contributor-prose fields on the
    artifact source their vocabulary from the primary-source text.
    Scoped to types in PROSE_FIELDS_BY_TYPE / PROSE_ENTRY_FIELDS_BY_TYPE;
    no-ops on other types.
    """
    issues = []
    if target_type not in PROSE_FIELDS_BY_TYPE \
       and target_type not in PROSE_ENTRY_FIELDS_BY_TYPE:
        return issues

    # Pool top-level source tokens = ∪ primary_sources[].path
    top_level_pool = set()
    primary_sources = _entries(data, "primary_sources")
    for src in primary_sources:
        if not isinstance(src, dict):
            continue
        path = src.get("path")
        if not path:
            continue
        tokens = load_source_tokens(path)
        if tokens is not None:
            top_level_pool |= tokens
    # If we couldn't load any source, short-circuit with one warn (not
    # error — source extraction failure is infrastructural, not content drift)
    if not top_level_pool and primary_sources:
        issues.append(Issue(rel, "warn",
            "prose-drift check: no source text could be extracted from "
            "primary_sources — check skipped (pdftotext missing? source "
            "files present on disk?)"))
        return issues

    # --- Top-level prose fields ---
    for field in PROSE_FIELDS_BY_TYPE.get(target_type, []):
        prose = data.get(field) or ""
        prose_tokens = extract_significant_tokens(prose)
        if not prose_tokens:
            continue
        unmatched = prose_tokens - top_level_pool
        issues.extend(_judge_drift(rel, field, prose_tokens, unmatched))

    # --- Per-entry prose fields ---
    for list_key, entry_field in PROSE_ENTRY_FIELDS_BY_TYPE.get(target_type, []):
        for i, entry in enumerate(_entries(data, list_key)):
            if not isinstance(entry, dict):
                continue
            prose = entry.get(entry_field) or ""
            prose_tokens = extract_significant_tokens(prose)
            if not prose_tokens:
                continue
            # Source-pool resolution differs by section. Most per-entry
            # prose fields use the entry's own `source.path` (timeline
            # events, affiliation roles, witnesses_testimony notes, etc.).
            src = entry.get("source") or {}
            src_path = src.get("path")
            if not src_path:
                continue
            source_tokens = load_source_tokens(src_path)
            if source_tokens is None:
                continue  # source-extraction failure already warned at top
            unmatched = prose_tokens - source_tokens
            issues.extend(_judge_drift(
                rel,
                f"{list_key}[{i}] ({entry.get('id', '?')!r}) {entry_field}",
                prose_tokens, unmatched,
            ))

    return issues


def check_cross_refs(rel, data):
    """Verify superseded_by / contradicted_by / corroborated_by refs
    point to existing entry ids within this artifact (or are structured
    external refs).

    Enumerates over ALL_ENTRY_SECTIONS so newer typed sections are
    cross-validated. Refs that don't match any id in the artifact warn
    (may be external refs — contributor verifies); no error so
    legitimate cross-artifact refs aren't false-positive'd.
    """
    issues = []
    all_ids = set()
    for section in ALL_ENTRY_SECTIONS:
        for entry in _entries(data, section):
            if isinstance(entry, dict) and entry.get("id"):
                all_ids.add(entry["id"])

    for section in ALL_ENTRY_SECTIONS:
        for i, entry in enumerate(_entries(data, section)):
            if not isinstance(entry, dict):
                continue
            eid = entry.get("id", "?")
            for field in ["superseded_by", "contradicted_by"]:
                val = entry.get(field)
                if val and isinstance(val, str) and val not in all_ids:
                    issues.append(Issue(rel, "warn",
                        f"{section}[{i}] ({eid!r}): {field} {val!r} does not match any "
                        f"entry id in this artifact (may be external ref — verify)"))
            corrob = entry.get("corroborated_by", [])
            if isinstance(corrob, list):
                for ref in corrob:
                    if isinstance(ref, str) and ref not in all_ids:
                        issues.append(Issue(rel, "warn",
                            f"{section}[{i}] ({eid!r}): corroborated_by ref {ref!r} "
                            f"does not match any entry id (may be external ref — verify)"))
    return issues


# =============================================================================
# Main
# =============================================================================

def collect_artifacts():
    if not RESEARCH_DIR.is_dir():
        return []
    return sorted(RESEARCH_DIR.glob("*.yaml"))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", help="Single artifact path (optional)")
    parser.add_argument("--quiet", action="store_true", help="Errors only")
    args = parser.parse_args()

    schema = load_schema()
    manifest_paths = load_manifest_paths()

    if args.path:
        artifacts = [Path(args.path).resolve()]
    else:
        artifacts = collect_artifacts()

    all_issues = []
    for p in artifacts:
        all_issues.extend(validate_artifact(p, schema, manifest_paths))

    errors = [i for i in all_issues if i.level == "error"]
    warnings = [i for i in all_issues if i.level == "warn"]

    print("=" * 64)
    print(" Research-Artifact Validation Report")
    print("=" * 64)
    print(f"\n  Artifacts scanned: {len(artifacts)}")
    print(f"  Errors:            {len(errors)}")
    if not args.quiet:
        print(f"  Warnings:          {len(warnings)}")

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
