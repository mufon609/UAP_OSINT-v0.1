"""manifest-checksum check — global BaseContext check.

For every archived entry in sources/manifest.yaml, recompute SHA256
and compare against the stored value. Source-integrity backstop: a
checksum mismatch means downstream verbatim-quote / prose-drift /
description-drift / coverage checks may be validating against altered
source material — all four extract source bytes through
``lib._common.extract_source_text``, so if the bytes silently change
between archival and validation, every source-grounded check would
validate against drifted material without detection.

Global check: runs once per validator invocation, not per node.
Consumes ``ctx.manifest_entries`` so the orchestrator's single
manifest load serves all manifest checks.

Emits ERROR for: missing file on disk; missing sha256 when status is
archived; checksum mismatch (silent corruption / substitution). Emits
no Issues for entries that verify cleanly. Skips non-archived entries
(nothing to verify).

Pairs with ``manifest_archive_status`` to bracket the manifest's two
integrity dimensions: this check covers content-byte integrity;
``manifest_archive_status`` covers composite-indicator state
consistency.

Does NOT verify ``sha256_at_extraction`` (an optional audit-trail
field on ``primary_sources_entry`` separate from the manifest's live
``sha256``).
"""

from checks import Issue
from lib._common import SOURCES_DIR, compute_sha256


CHECK_NAME = "manifest_checksums"
MANIFEST_REL = "sources/manifest.yaml"


def check(ctx):
    """Yield error-level Issue for every archived entry whose stored
    sha256 doesn't match the file on disk (or whose file is missing)."""
    for entry in ctx.manifest_entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "archived":
            continue
        path = entry.get("path")
        if not path:
            continue
        url = entry.get("url", "(no url)")
        full = SOURCES_DIR / path

        if not full.exists():
            yield Issue(
                f"sources/{path}", "error",
                f"Archived source file missing on disk (cited URL: {url})",
                check_name=CHECK_NAME,
            )
            continue

        stored = entry.get("sha256")
        if not stored:
            # Schema marks sha256 as conditionally_required for
            # status=archived. manifest.py verify-checksums backfills on
            # first run; reaching here with status=archived and no sha256
            # means something is structurally wrong — fail loudly.
            yield Issue(
                f"sources/{path}", "error",
                f"Archived manifest entry has no sha256 — run: "
                f"python3 scripts/tools/manifest.py verify-checksums  "
                f"(cited URL: {url})",
                check_name=CHECK_NAME,
            )
            continue

        current = compute_sha256(full)
        if current is None:
            yield Issue(
                f"sources/{path}", "error",
                f"Could not compute sha256 (file read error) — URL: {url}",
                check_name=CHECK_NAME,
            )
            continue

        if current != stored:
            yield Issue(
                f"sources/{path}", "error",
                f"Checksum MISMATCH — stored:{stored[:16]}... vs current:{current[:16]}... "
                f"(URL: {url}) — possible corruption, overwrite, or substitution",
                check_name=CHECK_NAME,
            )
