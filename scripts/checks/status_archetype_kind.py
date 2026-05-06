"""status-archetype-kind check — per-node NodeContext check.

Three small enum-vocabulary checks bundled together because they share
the same per-type-spec lookup pattern: read a list of valid values from
``type_spec``, error if the frontmatter field's value isn't in the
list. Absent fields are handled by frontmatter_required (when required)
or skipped silently (when optional per type).

  - status     → ``type_spec.status_values``
  - archetype  → ``type_spec.archetypes`` keys
  - kind       → ``type_spec.kinds`` keys

Lift from validate.py validate_node (C11 session-3 migration). Bundled
per design doc §6: substantively independent but mechanically identical.
"""

from checks import Issue


CHECK_NAME = "status_archetype_kind"


def check(ctx):
    fm = ctx.fm
    type_spec = ctx.type_spec

    status_values = type_spec.get("status_values", [])
    if fm.get("status") and status_values and fm["status"] not in status_values:
        yield Issue(
            ctx.rel, "error",
            f"Invalid status '{fm['status']}'. Valid: {status_values}",
            check_name=CHECK_NAME,
        )

    if fm.get("archetype"):
        valid = list(type_spec.get("archetypes", {}).keys())
        if valid and fm["archetype"] not in valid:
            yield Issue(
                ctx.rel, "error",
                f"Invalid archetype '{fm['archetype']}'. Valid: {valid}",
                check_name=CHECK_NAME,
            )

    if fm.get("kind"):
        valid = list(type_spec.get("kinds", {}).keys())
        if valid and fm["kind"] not in valid:
            yield Issue(
                ctx.rel, "error",
                f"Invalid kind '{fm['kind']}'. Valid: {valid}",
                check_name=CHECK_NAME,
            )
