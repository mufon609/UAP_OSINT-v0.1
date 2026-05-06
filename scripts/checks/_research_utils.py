"""Shared helpers for research-artifact checks.

Every per-section entry check in validate-research.py walks the same
shape: list of entries, each a dict with ``id`` + ``added_date``
lifecycle fields, optional ``source: {path, location}`` dict whose
path must appear in ``sources/manifest.yaml``. The four helpers below
factor that shape so each per-check module isn't a ~50-line copy of
the same scaffolding.

``section_in_scope`` (added 2026-05-05 with C15) reads
``schema.yaml::types.research-artifact.conditional_keys`` and answers
"should this section be present on this artifact?" — schema-driven
gate consumed by every per-section check that previously hard-coded
its target_type / archetype / kind constants. Single source of truth;
schema edits land without touching per-check Python.

Module name carries a leading underscore to signal "private to the
checks/ package — internal scaffolding, not contract surface."
``checks.Issue`` and the Context types are the public contract.
"""

from checks import Issue


def section_in_scope(ctx, section_name):
    """Return True if ``section_name`` should be present on this
    research artifact per ``schema.yaml`` conditional_keys rules.

    Reads ``ctx.schema.types.research-artifact.conditional_keys`` and
    evaluates the section's ``required_when_any_of`` list against
    ``ctx.target_type`` / ``target_archetype`` / ``target_kind``. The
    list is OR-combined; each rule's fields are AND-combined.

    Return values:
      - ``True``  — section is in scope; check should run per-entry validation
      - ``False`` — section is out of scope; check should skip (placement
                    enforced by iff_section)
      - ``None``  — section is not declared in conditional_keys (universal:
                    section is always in scope; caller skips the gate)

    Returns ``False`` when ``ctx.target_type is None`` (target_node
    couldn't be discovered) — downstream checks short-circuit cleanly.
    """
    schema = ctx.schema or {}
    types = schema.get("types") or {}
    research_artifact = types.get("research-artifact") or {}
    conditional_keys = research_artifact.get("conditional_keys") or {}
    rules = conditional_keys.get(section_name)
    if rules is None:
        return None  # not gated by conditional_keys; universal section

    if ctx.target_type is None:
        return False

    return evaluate_required_when(
        rules, ctx.target_type, ctx.target_archetype, ctx.target_kind,
    )


def evaluate_required_when(rules, target_type, target_archetype=None, target_kind=None):
    """Evaluate a section's ``required_when_any_of`` list against the
    artifact's target type / archetype / kind. Returns True if any rule
    matches; False otherwise. Each rule's fields are AND-combined.

    Rule field grammar:
      - ``target_node_type_in: [list]``      — target_type ∈ list
      - ``target_node_archetype_in: [list]`` — target_archetype ∈ list
      - ``target_node_kind_in: [list]``      — target_kind ∈ list
    Absent fields don't constrain (act as wildcard).

    A rule with NO fields would match unconditionally; treated as not-
    matching to avoid silent over-firing on schema typos.

    Takes positional values rather than a ctx so callers without a
    ResearchContext (research-scaffold.py — has node_type / archetype /
    kind as separate variables, not a context) can dispatch
    schema-driven without faking a context object. Shared with
    ``iff_section`` (placement-error emitter) and ``section_in_scope``
    (per-section gate); all three see the same rule logic so the
    scaffolder, validator orchestrator, and per-section checks agree
    on which rules match.
    """
    rule_list = rules.get("required_when_any_of") or []
    if not isinstance(rule_list, list):
        return False
    for rule in rule_list:
        if not isinstance(rule, dict) or not rule:
            continue
        if rule_matches(rule, target_type, target_archetype, target_kind):
            return True
    return False


def rule_matches(rule, target_type, target_archetype, target_kind):
    """AND-combine the rule's fields against the target values."""
    type_in = rule.get("target_node_type_in")
    if type_in is not None and target_type not in type_in:
        return False
    archetype_in = rule.get("target_node_archetype_in")
    if archetype_in is not None and target_archetype not in archetype_in:
        return False
    kind_in = rule.get("target_node_kind_in")
    if kind_in is not None and target_kind not in kind_in:
        return False
    return True


def entries(data, section):
    """Return list of entries for a section, or [] if absent or
    malformed. Always a list — caller can iterate without None
    checks."""
    v = data.get(section)
    return v if isinstance(v, list) else []


def check_unique_ids(rel, items, section_name, check_name):
    """Yield Issues for any entry missing 'id' or duplicating an id
    already seen in this section."""
    seen = set()
    for i, entry in enumerate(items):
        if not isinstance(entry, dict):
            yield Issue(
                rel, "error",
                f"{section_name}[{i}]: entry must be a dict",
                check_name=check_name,
            )
            continue
        eid = entry.get("id")
        if eid is None:
            yield Issue(
                rel, "error",
                f"{section_name}[{i}]: missing required 'id' field",
                check_name=check_name,
            )
            continue
        if eid in seen:
            yield Issue(
                rel, "error",
                f"{section_name}[{i}]: duplicate id {eid!r}",
                check_name=check_name,
            )
        seen.add(eid)


def check_lifecycle_fields(rel, entry, section_name, i, check_name):
    """Every entry requires id + added_date. Yields Issues for any
    missing field."""
    for field in ("id", "added_date"):
        if field not in entry:
            yield Issue(
                rel, "error",
                f"{section_name}[{i}] ({entry.get('id', '?')!r}): "
                f"missing required lifecycle field {field!r}",
                check_name=check_name,
            )


def require_source_dict(rel, entry, section_name, i, manifest_paths, check_name):
    """Verify entry.source is a dict with path + location, and the
    path appears in the manifest. Yields Issues for any violation."""
    src = entry.get("source")
    if not isinstance(src, dict):
        yield Issue(
            rel, "error",
            f"{section_name}[{i}] ({entry.get('id')!r}): "
            f"'source' must be a dict with path + location",
            check_name=check_name,
        )
        return
    if "path" not in src or "location" not in src:
        yield Issue(
            rel, "error",
            f"{section_name}[{i}] ({entry.get('id')!r}): "
            f"source must include 'path' and 'location'",
            check_name=check_name,
        )
    if src.get("path") and src["path"] not in manifest_paths:
        yield Issue(
            rel, "error",
            f"{section_name}[{i}] ({entry.get('id')!r}): "
            f"source.path {src['path']!r} not in sources/manifest.yaml",
            check_name=check_name,
        )
