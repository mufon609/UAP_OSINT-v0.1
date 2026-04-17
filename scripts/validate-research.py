#!/usr/bin/env python3
"""
Validate research artifacts against meta/schema.yaml.

Structural checks only — does NOT compare against the target node
(that's scripts/review-coverage.py in sub-phase D.4).

Checks (per schema.yaml research-artifact.invariants):
  - Required top-level keys present (id, type, schema_version, target_node,
    status, created, last_iteration, description, primary_sources,
    document_intrinsic, context_extrinsic, quotes, claims,
    entities_referenced, naming_quirks, research_gaps, iterations)
  - id matches file path
  - type == 'research-artifact'
  - schema_version ∈ schema.compatible_with
  - target_node points to an existing content-node .md file
  - status ∈ {active, archived}
  - Per-section entries: required lifecycle fields, unique ids, valid
    enum values
  - primary_sources[].path and sources[].path appear in sources/manifest.yaml
  - quote_ref and entity references point to existing entry ids
  - iterations log is sequential (i0, i1, i2, ...)
  - Every added_by_iteration value refers to an existing iteration id
  - Conditional `rumors` section present if target_node type ∈
    {person, organization, event, location}; absent otherwise

Usage:
  validate-research.py                  # validate all research/*.yaml
  validate-research.py PATH             # validate one file
  validate-research.py --quiet          # errors only
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


# =============================================================================
# Constants
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "meta" / "schema.yaml"
MANIFEST_PATH = REPO_ROOT / "sources" / "manifest.yaml"
RESEARCH_DIR = REPO_ROOT / "research"

RUMORS_TYPES = {"person", "organization", "event", "location"}
TYPE_DIRS = {
    "person": "people", "organization": "organizations", "document": "documents",
    "event": "events", "transcript": "transcripts", "news": "news",
    "book": "books", "location": "locations", "finding": "findings",
}

REQUIRED_TOP_LEVEL_KEYS = [
    "id", "type", "schema_version", "target_node", "status", "created",
    "last_iteration", "description", "primary_sources", "document_intrinsic",
    "context_extrinsic", "quotes", "claims", "entities_referenced",
    "naming_quirks", "research_gaps", "iterations",
]

# Per-entry enum values
VALID_EVIDENTIARY_TYPES = {"sworn-testimony", "documented", "cited", "secondary"}
VALID_NAMING_QUIRK_RESOLUTIONS = {
    "preserve-as-sic-in-quotes", "use-canonical", "disputed", "unresolved"
}
VALID_AUDIT_STATUSES = {
    "verified", "flagged", "superseded", "contradicted", "needs-reaudit"
}
VALID_RUMOR_STATUSES = {
    "not-primary-source-established", "primary-source-identified",
    "primary-source-disputed"
}
VALID_ENTITY_TYPES = {
    "person", "organization", "document", "event", "location", "finding"
}
VALID_STATUS = {"active", "archived"}
VALID_ITERATION_TRIGGERS = {
    "initial-build", "new-source", "oq-resolution", "cross-node-update",
    "audit-correction", "other",
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


# =============================================================================
# Per-artifact validation
# =============================================================================

def validate_artifact(path, schema, manifest_paths):
    issues = []
    rel = path.relative_to(REPO_ROOT)

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

    # --- Determine target-node type for conditional rumors section ---
    target_type = None
    if target_node and "/" in target_node:
        content_dir_name = target_node.split("/", 1)[0]
        reverse_map = {v: k for k, v in TYPE_DIRS.items()}
        target_type = reverse_map.get(content_dir_name)

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

    # --- primary_sources: path must exist in manifest ---
    issues.extend(check_primary_sources(rel, data, manifest_paths))

    # --- Per-section entry checks ---
    issues.extend(check_quotes(rel, data, manifest_paths))
    issues.extend(check_claims(rel, data, manifest_paths))
    issues.extend(check_entities(rel, data))
    issues.extend(check_naming_quirks(rel, data, manifest_paths))
    issues.extend(check_research_gaps(rel, data, manifest_paths))
    if "rumors" in data:
        issues.extend(check_rumors(rel, data))

    # --- Iteration log ---
    issues.extend(check_iterations(rel, data))

    # --- added_by_iteration cross-ref ---
    issues.extend(check_added_by_iteration(rel, data))

    # --- Cross-ref integrity (quote_ref, entity references, supersedes/etc) ---
    issues.extend(check_cross_refs(rel, data))

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
    """Every entry requires id, added_date, added_by_iteration."""
    issues = []
    required = ["id", "added_date", "added_by_iteration"]
    for field in required:
        if field not in entry:
            issues.append(Issue(rel, "error",
                f"{section_name}[{i}] ({entry.get('id', '?')!r}): "
                f"missing required lifecycle field {field!r}"))
    # audit_status enum (optional field)
    if "audit_status" in entry and entry["audit_status"] not in VALID_AUDIT_STATUSES:
        issues.append(Issue(rel, "error",
            f"{section_name}[{i}] ({entry.get('id')!r}): "
            f"audit_status {entry['audit_status']!r} not in {sorted(VALID_AUDIT_STATUSES)}"))
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


def check_quotes(rel, data, manifest_paths):
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
    return issues


def check_claims(rel, data, manifest_paths):
    issues = []
    claims = _entries(data, "claims")
    issues.extend(_check_unique_ids(rel, claims, "claims"))
    # Collect quote ids for quote_ref validation
    quote_ids = {q.get("id") for q in _entries(data, "quotes") if isinstance(q, dict)}
    for i, c in enumerate(claims):
        if not isinstance(c, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, c, "claims", i))
        # Required: statement, sources (list), evidentiary_type
        if "statement" not in c:
            issues.append(Issue(rel, "error",
                f"claims[{i}] ({c.get('id')!r}): missing required 'statement'"))
        sources = c.get("sources")
        if not isinstance(sources, list) or not sources:
            issues.append(Issue(rel, "error",
                f"claims[{i}] ({c.get('id')!r}): 'sources' must be a non-empty list"))
        else:
            for si, src in enumerate(sources):
                if not isinstance(src, dict):
                    issues.append(Issue(rel, "error",
                        f"claims[{i}] sources[{si}]: must be a dict"))
                    continue
                if "path" not in src or "location" not in src:
                    issues.append(Issue(rel, "error",
                        f"claims[{i}] ({c.get('id')!r}) sources[{si}]: must include path + location"))
                if src.get("path") and src["path"] not in manifest_paths:
                    issues.append(Issue(rel, "error",
                        f"claims[{i}] ({c.get('id')!r}) sources[{si}]: "
                        f"path {src['path']!r} not in sources/manifest.yaml"))
                if "quote_ref" in src and src["quote_ref"] not in quote_ids:
                    issues.append(Issue(rel, "error",
                        f"claims[{i}] ({c.get('id')!r}) sources[{si}]: "
                        f"quote_ref {src['quote_ref']!r} does not match any quote.id"))
        # evidentiary_type enum
        et = c.get("evidentiary_type")
        if et is None:
            issues.append(Issue(rel, "error",
                f"claims[{i}] ({c.get('id')!r}): missing required 'evidentiary_type'"))
        elif et not in VALID_EVIDENTIARY_TYPES:
            issues.append(Issue(rel, "error",
                f"claims[{i}] ({c.get('id')!r}): evidentiary_type {et!r} "
                f"not in {sorted(VALID_EVIDENTIARY_TYPES)}"))
    return issues


def check_entities(rel, data):
    issues = []
    entities = _entries(data, "entities_referenced")
    issues.extend(_check_unique_ids(rel, entities, "entities_referenced"))
    quote_ids = {q.get("id") for q in _entries(data, "quotes") if isinstance(q, dict)}
    claim_ids = {c.get("id") for c in _entries(data, "claims") if isinstance(c, dict)}
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
                if "claim_id" in ref and ref["claim_id"] not in claim_ids:
                    issues.append(Issue(rel, "error",
                        f"entities_referenced[{i}] ({e.get('id')!r}) references[{ri}]: "
                        f"claim_id {ref['claim_id']!r} does not match any claim.id"))
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


def check_research_gaps(rel, data, manifest_paths):
    issues = []
    gaps = _entries(data, "research_gaps")
    issues.extend(_check_unique_ids(rel, gaps, "research_gaps"))
    for i, g in enumerate(gaps):
        if not isinstance(g, dict):
            continue
        issues.extend(_check_lifecycle_fields(rel, g, "research_gaps", i))
        if "statement" not in g:
            issues.append(Issue(rel, "error",
                f"research_gaps[{i}] ({g.get('id')!r}): missing required 'statement'"))
        if "resolved" not in g:
            issues.append(Issue(rel, "error",
                f"research_gaps[{i}] ({g.get('id')!r}): missing required 'resolved' (bool)"))
        # When resolved=True, require resolution fields
        if g.get("resolved") is True:
            for field in ["resolved_date", "resolving_source", "resolution_summary"]:
                if not g.get(field):
                    issues.append(Issue(rel, "error",
                        f"research_gaps[{i}] ({g.get('id')!r}): resolved=true requires {field!r}"))
            rs = g.get("resolving_source")
            if isinstance(rs, dict) and rs.get("path") and rs["path"] not in manifest_paths:
                issues.append(Issue(rel, "error",
                    f"research_gaps[{i}] ({g.get('id')!r}): resolving_source.path "
                    f"{rs['path']!r} not in sources/manifest.yaml"))
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


def check_iterations(rel, data):
    issues = []
    its = _entries(data, "iterations")
    if not its:
        issues.append(Issue(rel, "error", "iterations list must contain at least i0 (initial build)"))
        return issues
    # IDs must be i0, i1, i2, ... sequential
    seen = []
    for i, it in enumerate(its):
        if not isinstance(it, dict):
            issues.append(Issue(rel, "error", f"iterations[{i}]: must be a dict"))
            continue
        iid = it.get("id")
        expected = f"i{i}"
        if iid != expected:
            issues.append(Issue(rel, "error",
                f"iterations[{i}]: id {iid!r} must be {expected!r} (sequential, no gaps)"))
        for field in ["id", "date", "trigger", "summary"]:
            if field not in it:
                issues.append(Issue(rel, "error",
                    f"iterations[{i}]: missing required {field!r}"))
        trig = it.get("trigger")
        if trig is not None and trig not in VALID_ITERATION_TRIGGERS:
            issues.append(Issue(rel, "error",
                f"iterations[{i}]: trigger {trig!r} not in {sorted(VALID_ITERATION_TRIGGERS)}"))
        if iid:
            seen.append(iid)
    return issues


def check_added_by_iteration(rel, data):
    issues = []
    iteration_ids = {
        it.get("id") for it in _entries(data, "iterations")
        if isinstance(it, dict)
    }
    for section in ["quotes", "claims", "entities_referenced", "naming_quirks",
                    "research_gaps", "rumors"]:
        for i, entry in enumerate(_entries(data, section)):
            if not isinstance(entry, dict):
                continue
            abi = entry.get("added_by_iteration")
            if abi is None:
                continue  # caught by lifecycle check
            if abi not in iteration_ids:
                issues.append(Issue(rel, "error",
                    f"{section}[{i}] ({entry.get('id')!r}): "
                    f"added_by_iteration {abi!r} does not match any iteration.id"))
    return issues


def check_cross_refs(rel, data):
    """Verify superseded_by / contradicted_by / corroborated_by refs point to
    existing entry ids within this artifact (or are structured external refs)."""
    issues = []
    all_ids = set()
    for section in ["quotes", "claims", "entities_referenced", "naming_quirks",
                    "research_gaps", "rumors"]:
        for entry in _entries(data, section):
            if isinstance(entry, dict) and entry.get("id"):
                all_ids.add(entry["id"])

    for section in ["quotes", "claims", "entities_referenced", "naming_quirks",
                    "research_gaps", "rumors"]:
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
