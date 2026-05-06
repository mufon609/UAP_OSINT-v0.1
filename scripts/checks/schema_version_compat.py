"""schema-version-compat check — per-node NodeContext check.

Verifies the node's ``schema_version`` is an integer in
``schema.compatible_with``. Errors on type mismatch or version
outside the compatible window (with a pointer to the migration
docs). Absent schema_version is handled by frontmatter_required;
this check no-ops on None.

Lift from validate.py validate_node (C11 session-3 migration).
Shares ``schema_version_compat_messages`` from ``lib/_common.py`` with
the equivalent checks on research artifacts (artifact_top_level) and
governance-doc / template frontmatter (governance_files). Same logic;
one source — closes BACKLOG Issue #8.
"""

from checks import Issue
from lib._common import schema_version_compat_messages


CHECK_NAME = "schema_version_compat"


def check(ctx):
    schema_block = ctx.schema.get("schema", {}) or {}
    compatible_with = schema_block.get("compatible_with", [1])
    current = schema_block.get("version", "?")
    for level, msg in schema_version_compat_messages(
        ctx.fm.get("schema_version"), compatible_with, current,
    ):
        yield Issue(ctx.rel, level, msg, check_name=CHECK_NAME)
