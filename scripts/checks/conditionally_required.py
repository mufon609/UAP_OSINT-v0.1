"""conditionally-required check — per-node NodeContext check.

Schema-driven dispatcher for ``types.{T}.conditionally_required`` rules.
For each (key, condition) pair on the node's type:

  1. Evaluate condition against the frontmatter; skip if false.
  2. If key is a frontmatter-field name (lowercase): require presence,
     and if a ``{key}_values`` vocabulary exists on the type_spec,
     additionally require the value is in that list.
  3. If key is a Title-Case section name: require the H2 section
     exists in the node body.

Supported condition grammar (kept minimal on purpose; extend only when
a new conditional genuinely needs it):

  - ``<field> == <literal>`` — equality check; literal is \\w-separated token
  - ``<field> is set`` — field is present and truthy in frontmatter

Schema-driven dispatch replaces what would otherwise be a hardcoded
per-conditional check per case (e.g., archival_status when doc_form ==
book; Media Versioning section when derivation_of is set), so new
conditionals land as schema edits alone. Malformed condition strings
surface as validator errors — schema drift fails loudly rather than
silently no-op'ing.

Reads ``ctx.h2_sections`` for the section-name route — the lazy
property memoizes H2 extraction so this check shares the work with
required_sections / section_rules / table_cell_word_budget on the
same NodeContext (one extraction, multiple consumers).
"""

import re

from checks import Issue


CHECK_NAME = "conditionally_required"


_CONDITION_IS_SET = re.compile(r"^\s*(\w+)\s+is\s+set\s*$")
_CONDITION_EQ = re.compile(r"^\s*(\w+)\s*==\s*([\w-]+)\s*$")

# Frontmatter field vs section name disambiguated by shape: field names
# are lowercase with underscores / hyphens (no spaces, no capitals);
# section names are human-readable (any space or capital triggers
# section routing). Matches the schema style already in use.
_FIELD_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


def evaluate_condition(condition, fm):
    """Evaluate a condition string against frontmatter ``fm``. Returns
    True/False. Raises ValueError if the expression doesn't match the
    supported grammar — malformed conditions surface loudly to the
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


def check(ctx):
    cr = ctx.type_spec.get("conditionally_required") or {}
    if not cr:
        return

    for key, condition in cr.items():
        try:
            active = evaluate_condition(condition, ctx.fm)
        except ValueError as e:
            yield Issue(
                ctx.rel, "error",
                f"schema conditionally_required[{key!r}]: {e}",
                check_name=CHECK_NAME,
            )
            continue
        if not active:
            continue

        if _FIELD_KEY_RE.match(key):
            # Frontmatter-field route: require presence, then vocabulary.
            if not ctx.fm.get(key):
                yield Issue(
                    ctx.rel, "error",
                    f"Frontmatter missing {key!r} (required when {condition!r})",
                    check_name=CHECK_NAME,
                )
                continue
            values_key = f"{key}_values"
            valid_values = ctx.type_spec.get(values_key) or []
            if valid_values and ctx.fm[key] not in valid_values:
                yield Issue(
                    ctx.rel, "error",
                    f"Invalid {key} {ctx.fm[key]!r}. Valid: {valid_values}",
                    check_name=CHECK_NAME,
                )
        else:
            # Section-name route: require H2 presence (use lazy cache).
            if key not in ctx.h2_sections:
                yield Issue(
                    ctx.rel, "error",
                    f"Required section '## {key}' missing "
                    f"(required when {condition!r})",
                    check_name=CHECK_NAME,
                )
