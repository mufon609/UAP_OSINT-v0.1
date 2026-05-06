"""status-archetype-kind check — per-node NodeContext check.

Three small enum-vocabulary checks bundled together because they share
the same per-type-spec lookup pattern: read a list of valid values from
``type_spec``, error if the frontmatter field's value isn't in the
list. Absent fields are handled by frontmatter_required (when required)
or skipped silently (when optional per type — e.g., archetype is
person-only; document / event / transcript / media / location nodes
have no archetype enum to validate against).

  - status     → ``type_spec.status_values``
  - archetype  → ``type_spec.archetypes`` keys
  - kind       → ``type_spec.kinds`` keys

Origin: foundational from the initial commit (``af5f789``) — the
status / archetype / kind enum-validation logic was inline in
validate.py from day one. Migration: ``60bb88d`` (C11 session 3
lift to per-module shape). Bundled per the C11 design doc §6
("Inline validate_node logic disposition"): the three sub-checks
are substantively independent but mechanically identical (same
type_spec lookup pattern + same Issue shape). Splitting fragments
shared structure without buying isolation.

Presence-guard semantics (NOT truthy). The check fires whenever the
field key is present in frontmatter, INCLUDING when the value is
nullified (``archetype:`` with no value → ``None``) — None isn't
in the valid list, so it errors. Distinct from a truthy-guard
that would skip null values, which would create a layering gap with
``frontmatter_required`` (presence-only check; key-present-with-null
passes there). Together the two checks cover:

  - missing field: frontmatter_required errors
  - field present with null/empty/wrong value: this check errors

C17 investigation history: an earlier docstring iteration of this
check, plus the frontmatter_required + id_path_match docstrings,
described the layering as if this check used truthy-guard semantics.
That was wrong on closer read — the original code did use truthy
guards (``if fm.get("archetype"):``), creating the very layering
gap the docstrings claimed didn't exist. The C17 audit corrected
the guards to presence-based + corrected the cross-referenced
claims in the frontmatter_required and id_path_match docstrings.
The corpus had no null fields when the fix landed, so the
correction was zero-impact; the layering invariant now holds.

C18 confirmed byte-identity through the C11 migration; the C17
truthy → presence guard correction is a deliberate behavior
change documented here and in the corresponding commit message.
"""

from checks import Issue


CHECK_NAME = "status_archetype_kind"


def check(ctx):
    fm = ctx.fm
    type_spec = ctx.type_spec

    # Presence-guard, not truthy: a field key with a null value
    # (e.g., ``archetype:`` with no value → ``None``) reaches the
    # enum check and errors because None is not a valid enum value.
    # Truthy-guard semantics here would skip null values and create
    # a layering gap with frontmatter_required's presence-only check.
    status_values = type_spec.get("status_values", [])
    if "status" in fm and status_values and fm["status"] not in status_values:
        yield Issue(
            ctx.rel, "error",
            f"Invalid status {fm['status']!r}. Valid: {status_values}",
            check_name=CHECK_NAME,
        )

    if "archetype" in fm:
        valid = list(type_spec.get("archetypes", {}).keys())
        if valid and fm["archetype"] not in valid:
            yield Issue(
                ctx.rel, "error",
                f"Invalid archetype {fm['archetype']!r}. Valid: {valid}",
                check_name=CHECK_NAME,
            )

    if "kind" in fm:
        valid = list(type_spec.get("kinds", {}).keys())
        if valid and fm["kind"] not in valid:
            yield Issue(
                ctx.rel, "error",
                f"Invalid kind {fm['kind']!r}. Valid: {valid}",
                check_name=CHECK_NAME,
            )
