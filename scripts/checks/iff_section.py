"""iff-section check — schema-driven research-artifact ResearchContext check.

Walks ``schema-research-artifact.yaml::conditional_keys`` and
emits placement errors:

  - ``required X key missing`` — when a section's
    ``required_when_any_of`` rules match the artifact's target context
    but the section is absent
  - ``X key should not be present`` — when neither the
    ``required_when_any_of`` nor the ``optional_when_any_of`` rules match
    but the section is present anyway

A section may declare ``optional_when_any_of`` (present-allowed-but-not-
required) alongside or instead of ``required_when_any_of`` — mirroring the
schema's rendered-side ``optional_sections`` (finding Apparent
Contradictions; investigation Counter-Evidence / Closure Path / Resolution
History). A matching optional rule suppresses BOTH the missing error and
the should-not-be-present error; only ``required_when_any_of`` forces
presence.

The schema is the single source of truth for which sections belong on
which artifacts: per-section checks call ``section_in_scope`` for the
gate and keep only entry validation. Schema edits to
``conditional_keys`` land without touching per-check Python.

Per-section checks STILL gate on ``section_in_scope`` and skip
per-entry validation when the section is wrongly placed — emitting
N per-entry errors on top of the placement error would be noise
about contents that shouldn't exist. ``iff_section`` carries the
single placement error; per-section checks carry the entry-level
diagnostics.

Schema rule grammar: each section's ``required_when_any_of`` is a
list of rules, each rule a dict whose fields are AND-combined; the
list is OR-combined. AND within a rule, OR across rules — handles
both ``witnesses_testimony``'s ``type=event AND kind=hearing``
conjunction (since ``hearing`` is shared between event and transcript
kinds) and ``corroboration_items``'s "eyewitness-person OR
encounter-event" disjunction.
"""

from checks import Issue
from checks._research_utils import evaluate_optional_when, evaluate_required_when


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

    # Direct schema-config access; loud KeyError on schema breakage
    # rather than silent {} fallback (which would mass over-fire and
    # under-fire on wrong sides of the placement check).
    conditional_keys = ctx.schema["types"]["research-artifact"]["conditional_keys"]

    for section_name, rules in conditional_keys.items():
        required = evaluate_required_when(
            rules, ctx.target_type, ctx.target_archetype, ctx.target_kind,
        )
        optional = evaluate_optional_when(
            rules, ctx.target_type, ctx.target_archetype, ctx.target_kind,
        )
        present = section_name in ctx.data

        if required and not present:
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
        elif present and not (required or optional):
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
