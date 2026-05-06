"""iff-section check — schema-driven research-artifact ResearchContext check.

Walks ``schema.yaml::types.research-artifact.conditional_keys`` and
emits placement errors:

  - ``required X key missing`` — when a section's
    ``required_when_target_node_<dimension>_in`` rules match the
    artifact's target context but the section is absent
  - ``X key should not be present`` — when no rule matches but the
    section is present anyway

Replaces ~22 inline iff-walker blocks that previously lived in
``validate_artifact``: the per-section checks each duplicated the
target_type / target_archetype / target_kind gate logic. This module
reads the rules from ``schema.yaml`` once per artifact and dispatches.
The schema becomes the single source of truth; per-section checks
keep only entry validation and call ``section_in_scope`` for the
gate.

Closes BACKLOG C15. Schema edits to ``conditional_keys`` land without
touching per-check Python.

Per-section checks STILL gate on ``section_in_scope`` and skip
per-entry validation when the section is wrongly placed — emitting
N per-entry errors on top of the placement error would be noise
about contents that shouldn't exist. ``iff_section`` carries the
single placement error; per-section checks carry the entry-level
diagnostics.
"""

from checks import Issue
from checks._research_utils import evaluate_required_when


CHECK_NAME = "iff_section"


def _format_condition(rules):
    """Render the section's ``required_when_any_of`` list as a human-
    readable condition string for error messages."""
    rule_list = rules.get("required_when_any_of") or []
    parts = []
    for rule in rule_list:
        if not isinstance(rule, dict):
            continue
        rule_parts = []
        for key, label in (
            ("target_node_type_in", "target_type"),
            ("target_node_archetype_in", "target_archetype"),
            ("target_node_kind_in", "target_kind"),
        ):
            values = rule.get(key)
            if values is not None:
                rule_parts.append(f"{label} ∈ {sorted(values)}")
        if rule_parts:
            parts.append(" AND ".join(rule_parts))
    if not parts:
        return "(no rule)"
    return " OR ".join(f"({p})" if " AND " in p else p for p in parts)


def check(ctx):
    if ctx.target_type is None:
        return

    schema = ctx.schema or {}
    types = schema.get("types") or {}
    research_artifact = types.get("research-artifact") or {}
    conditional_keys = research_artifact.get("conditional_keys") or {}

    for section_name, rules in conditional_keys.items():
        in_scope = evaluate_required_when(rules, ctx)
        present = section_name in ctx.data

        if in_scope and not present:
            condition = _format_condition(rules)
            yield Issue(
                ctx.rel, "error",
                f"Required {section_name!r} key missing — schema "
                f"conditional_keys requires it when {condition}; "
                f"target context: target_type={ctx.target_type!r}, "
                f"target_archetype={ctx.target_archetype!r}, "
                f"target_kind={ctx.target_kind!r}",
                check_name=CHECK_NAME,
            )
        elif not in_scope and present:
            yield Issue(
                ctx.rel, "error",
                f"{section_name!r} key should not be present — schema "
                f"conditional_keys gates it on target_type / archetype / "
                f"kind that don't match this artifact "
                f"(target_type={ctx.target_type!r}, "
                f"target_archetype={ctx.target_archetype!r}, "
                f"target_kind={ctx.target_kind!r})",
                check_name=CHECK_NAME,
            )
