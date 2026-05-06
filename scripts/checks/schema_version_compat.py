"""schema-version-compat check — per-node NodeContext check.

Verifies the node's ``schema_version`` is an integer in
``schema.compatible_with``. Errors on type mismatch or version
outside the compatible window (with a pointer to the migration
docs). Absent ``schema_version`` is handled by
``frontmatter_required``; this check no-ops on None.

Thin wrapper on ``lib._common.schema_version_compat_messages``,
which is shared with ``artifact_top_level`` (research-artifact
top-level) and the two ``governance_files`` routes (template +
governance-doc). One source of truth for the version-compat error
wording and migration-pointer message.
"""

from checks import Issue
from lib._common import schema_version_compat_messages


CHECK_NAME = "schema_version_compat"


def check(ctx):
    # Direct subscript on the ``schema:`` block — schema malformation
    # surfaces loudly rather than masking drift.
    schema_block = ctx.schema["schema"]
    compatible_with = schema_block["compatible_with"]
    current = schema_block["version"]
    for level, msg in schema_version_compat_messages(
        ctx.fm.get("schema_version"), compatible_with, current,
    ):
        yield Issue(ctx.rel, level, msg, check_name=CHECK_NAME)
