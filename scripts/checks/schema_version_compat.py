"""schema-version-compat check — per-node NodeContext check.

Verifies the node's ``schema_version`` is an integer in
``schema.compatible_with``. Errors on type mismatch or version
outside the compatible window (with a pointer to the migration
docs). Absent schema_version is handled by frontmatter_required;
this check no-ops on None.

Lift from validate.py validate_node (C11 session-3 migration).
Same logic as the four other sites that duplicated this check
(governance-files template + governance-files doc + research-artifact
top-level); Issue #8 dedup folds those duplicates into a shared
helper at lib level when the orchestrator rewrite consolidates.
"""

from checks import Issue


CHECK_NAME = "schema_version_compat"


def check(ctx):
    sv = ctx.fm.get("schema_version")
    if sv is None:
        return
    schema_block = ctx.schema.get("schema", {}) or {}
    compatible_with = schema_block.get("compatible_with", [1])
    if not isinstance(sv, int) or isinstance(sv, bool):
        yield Issue(
            ctx.rel, "error",
            f"schema_version must be an integer; got {sv!r} ({type(sv).__name__})",
            check_name=CHECK_NAME,
        )
        return
    if sv not in compatible_with:
        current = schema_block.get("version", "?")
        yield Issue(
            ctx.rel, "error",
            f"schema_version {sv} not in compatible_with {compatible_with} "
            f"(current schema version is {current}). "
            f"Migrate per meta/toolkit-notes/schema-migrations/.",
            check_name=CHECK_NAME,
        )
