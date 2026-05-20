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

Emits ERROR for: missing file on disk (when the path is git-TRACKED);
missing sha256 when status is archived; checksum mismatch (silent
corruption / substitution). Emits no Issues for entries that verify
cleanly. Skips non-archived entries (nothing to verify).

One absence is NOT an error: a missing file whose path is git-IGNORED.
The large primary-source media (``sources/video/``) is deliberately kept
out of the git remote per ``.gitignore`` (file-size limits) and recorded
in the manifest by URL + sha256, so on a fresh clone those files are
expected-absent rather than corrupt. Those are recorded in
``ctx.missing_sources`` (out-of-band, like the broken-link registry —
not an Issue) so the validator passes on a fresh checkout while the
orchestrator still surfaces what to recover (source URL / Wayback). A
*present* git-ignored file is still checksum-verified; only absence is
exempted, because re-fetched transcoded media (yt-dlp) is not byte-
reproducible — see meta/sources-access.md "Large primary-source files".

Pairs with ``manifest_archive_status`` to bracket the manifest's two
integrity dimensions: this check covers content-byte integrity;
``manifest_archive_status`` covers composite-indicator state
consistency.

Does NOT verify ``sha256_at_extraction`` (an optional audit-trail
field on ``primary_sources_entry`` separate from the manifest's live
``sha256``).
"""

import subprocess
from functools import lru_cache

from checks import Issue
from lib._common import REPO_ROOT, SOURCES_DIR, compute_sha256, iter_artifacts


CHECK_NAME = "manifest_checksums"
MANIFEST_REL = "sources/manifest.yaml"


@lru_cache(maxsize=None)
def _is_gitignored(rel_to_repo):
    """True if ``rel_to_repo`` (e.g. 'sources/video/x.mp4') is git-ignored.

    Uses ``git check-ignore -q`` — which classifies a path string whether
    or not the file exists on disk, exactly the missing-file case here
    (exit 0 = ignored, 1 = not ignored, 128 = error / not a repo). Falls
    back to a ``sources/video/`` prefix heuristic when git is unavailable
    (tarball checkout) so the exemption still holds. Cached: the same
    paths recur across a validator run."""
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "-q", rel_to_repo],
            cwd=REPO_ROOT, capture_output=True,
        )
        if proc.returncode in (0, 1):
            return proc.returncode == 0
    except OSError:
        pass
    # git absent or errored (returncode 128) — fall back to the known
    # git-ignored media directory.
    return rel_to_repo.startswith("sources/video/")


def check(ctx):
    """Yield error-level Issue for every archived artifact whose stored
    sha256 doesn't match the file on disk (or whose file is missing)."""
    for entry, artifact in iter_artifacts(ctx.manifest_entries):
        path = artifact.get("path")
        if not path:
            continue
        url = entry.get("url", "(no url)")
        full = SOURCES_DIR / path

        if not full.exists():
            rel = f"sources/{path}"
            if _is_gitignored(rel):
                # Expected-absent on a fresh clone (git-ignored large
                # media). Record out-of-band; not an Issue. Recoverable
                # from the source URL / Wayback per the manifest entry.
                ctx.missing_sources[rel] = url
                continue
            yield Issue(
                rel, "error",
                f"Archived source file missing on disk (cited URL: {url})",
                check_name=CHECK_NAME,
            )
            continue

        stored = artifact.get("sha256")
        if not stored:
            # Schema marks sha256 as required on artifact_entry.
            # manifest.py verify-checksums backfills on first run;
            # reaching here with a path-bearing artifact and no sha256
            # means something is structurally wrong — fail loudly.
            yield Issue(
                f"sources/{path}", "error",
                f"Archived artifact has no sha256 — run: "
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
