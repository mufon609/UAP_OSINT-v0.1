"""schema-version-compat check — per-node NodeContext check.

Verifies the node's ``schema_version`` is an integer in
``schema.compatible_with``. Errors on type mismatch or version
outside the compatible window (with a pointer to the migration
docs). Absent schema_version is handled by frontmatter_required;
this check no-ops on None.

Origin: foundational from the initial commit (``af5f789``); the
schema_version compat check was inline in validate.py from day one
as part of the basic frontmatter discipline. Migration trail:

  - ``60bb88d`` (C11 session 3 lift to per-module shape)
  - ``2f3effb`` (BACKLOG #8 close — "lib: consolidate schema_version
    compat helper") consolidated the version-compat logic into
    ``lib._common.schema_version_compat_messages``. Same helper now
    serves four sites: this per-node check, ``artifact_top_level``
    (research-artifact top-level), ``governance_files`` template
    route, ``governance_files`` governance-doc route. Single source
    of truth for the version-compat error wording + migration-
    pointer message.

Anchor pattern: foundational thin-wrapper on shared helper. Stable
check shape since af5f789; the check delegates the operative
logic to ``lib._common``. Same shape as the helper-using paths in
``artifact_top_level`` and ``governance_files``. The four consumer
sites converged on a single helper rather than maintaining four
parallel implementations of the version-compat-message logic —
consistent with the broader lockstep pattern for source-extraction
helpers (BACKLOG-tracked refactors that pulled extract_source_text,
normalize_for_compare, parse_frontmatter, the prose-drift tokenizer
into lib).

C18 confirmed byte-identity through both the C11 lift and the
helper consolidation.
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
