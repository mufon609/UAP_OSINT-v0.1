"""manifest-checksum check — global BaseContext pilot (C11).

For every archived entry in sources/manifest.yaml, recompute SHA256 and
compare against the stored value. Source-integrity backstop: a checksum
mismatch means downstream verbatim-quote checks may be validating
against altered source material.

Global check: runs once per validator invocation, not per node.
Consumes ``ctx.manifest_entries`` so the orchestrator's single
manifest load serves all manifest checks (resolves the legacy
load-3x duplication).

Emits ERROR for: missing file on disk; missing sha256 when status is
archived; checksum mismatch (silent corruption / substitution).
Emits no Issues for entries that verify cleanly. Skips non-archived
entries (nothing to verify).
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
