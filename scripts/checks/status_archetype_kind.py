"""status-archetype-kind check — per-node NodeContext check.

Three enum-vocabulary checks bundled because they share the same
per-type-spec lookup pattern: read valid values from ``type_spec``,
error if the frontmatter field's value isn't in the list.

  - status     → ``type_spec.status_values``
  - archetype  → ``type_spec.archetypes`` keys
  - kind       → ``type_spec.kinds`` keys

Absent required fields are handled by ``frontmatter_required``;
fields that are optional per type are skipped silently (archetype
is person-only; orgs / docs / events / transcripts / media nodes
have no archetype enum; locations / findings have neither archetype
nor kind).

PRESENCE-GUARD SEMANTICS (not truthy). The check fires whenever the
field key is present, INCLUDING when nullified (``archetype:`` with
no value → None) — None isn't in the valid list, so it errors.
Truthy-guard semantics would skip null values and open a layering
gap with ``frontmatter_required`` (presence-only check; null passes
there). Together:

  - missing field: ``frontmatter_required`` errors
  - field present with null / empty / wrong value: this check errors
"""

from checks import Issue


CHECK_NAME = "status_archetype_kind"


def check(ctx):
    fm = ctx.fm
    type_spec = ctx.type_spec

    # ``status_values`` is universal (every type declares one); direct
    # subscript surfaces a loud KeyError on schema drift. ``archetypes``
    # / ``kinds`` are polymorphic (person has archetypes but no kinds;
    # orgs / docs / events / transcripts / media have kinds but no
    # archetypes; locations / findings have neither) — the .get
    # fallbacks below are meaningful absences, not drift masks.
    status_values = type_spec["status_values"]
    if "status" in fm and fm["status"] not in status_values:
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
