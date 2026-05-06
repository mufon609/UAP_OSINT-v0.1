"""manifest-checksum check — global BaseContext check.

For every archived entry in sources/manifest.yaml, recompute SHA256 and
compare against the stored value. Source-integrity backstop: a checksum
mismatch means downstream verbatim-quote checks may be validating
against altered source material.

Global check: runs once per validator invocation, not per node.
Consumes ``ctx.manifest_entries`` so the orchestrator's single
manifest load serves all manifest checks.

Emits ERROR for: missing file on disk; missing sha256 when status is
archived; checksum mismatch (silent corruption / substitution).
Emits no Issues for entries that verify cleanly. Skips non-archived
entries (nothing to verify).

Origin: foundational from the initial commit (``af5f789``). SHA256
integrity was called out as a toolkit core feature in the initial
commit message: "mechanical verbatim quote verification against
archived sources, SHA256 integrity on every archived file." The
check is the source-integrity backstop that downstream source-using
checks rely on — ``verbatim_quotes``, ``prose_drift``,
``description_token_drift``, and ``coverage`` all extract source
bytes via ``lib._common.extract_source_text``; if those bytes
silently change between archival and validation, every source-
grounded check would validate against drifted material without
detection.

Pairs with ``manifest_archive_status`` to bracket the manifest's two
integrity dimensions:

  - manifest_checksums (this check): content-byte integrity — file
    bytes haven't been corrupted, overwritten, or substituted since
    archival. Catches silent-modification scenarios.
  - manifest_archive_status: composite-indicator state consistency
    — the 2-bit archive_status flag matches status / path /
    wayback_date. Catches state-drift scenarios.

Migration: ``472e547`` (C11 cluster PILOT — "checks: pilot two
checks against C11/C13/C14 contract"). manifest_checksums was the
first per-module lift in the cluster, chosen for the pilot because
it's stand-alone (no per-node iteration), has few helpers, and is
easy to test. Tightening at ``af0c1b2`` (pilot doc/impl alignment).
``1c34081`` retired BACKLOG C14 by lifting the remaining manifest
checks alongside this one. C18 confirmed byte-identity through the
migration.

What this check does NOT verify: ``sha256_at_extraction`` (an
optional audit-trail field on ``primary_sources_entry`` separate
from the manifest's live ``sha256`` — captured at extraction time
rather than current state). Different concern, different field.
"""

import hashlib

from checks import Issue
from lib._common import SOURCES_DIR


CHECK_NAME = "manifest_checksums"
MANIFEST_REL = "sources/manifest.yaml"


def _compute_sha256(file_path):
    """Stream-compute SHA256 of a file. Returns hex digest or None on
    read error. Same algorithm as scripts/manifest.py (kept duplicated
    so each validator script remains self-contained)."""
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


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
                f"python3 scripts/manifest.py verify-checksums  "
                f"(cited URL: {url})",
                check_name=CHECK_NAME,
            )
            continue

        current = _compute_sha256(full)
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
