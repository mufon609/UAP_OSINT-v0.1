"""manifest file-presence check — global BaseContext check.

For every archived artifact in sources/manifest.yaml, confirm the file
exists on disk. A missing git-TRACKED file is an error (a broken manifest
path — the entry points at a file that isn't there).

One absence is NOT an error: a missing file whose path is git-IGNORED.
The large primary-source media (``sources/video/``) is deliberately kept
out of the git remote per ``.gitignore`` (file-size limits) and recorded
in the manifest by URL, so on a fresh clone those files are expected-absent
rather than broken. Those are recorded in ``ctx.missing_sources``
(out-of-band, like the broken-link registry — not an Issue) so the
validator passes on a fresh checkout while the orchestrator still surfaces
what to recover (source URL / Wayback).

Global check: runs once per validator invocation, not per node. Consumes
``ctx.manifest_entries`` so the orchestrator's single manifest load serves
all manifest checks. Verification of source content is the reader's, via
the entry's URL + Wayback snapshot.
"""

import subprocess
from functools import lru_cache

from checks import Issue
from lib._common import REPO_ROOT, SOURCES_DIR, iter_artifacts


CHECK_NAME = "manifest_files_present"


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
    return rel_to_repo.startswith("sources/video/")


def check(ctx):
    """Yield an error-level Issue for every archived artifact whose file
    is missing on disk and not git-ignored."""
    for entry, artifact in iter_artifacts(ctx.manifest_entries):
        path = artifact.get("path")
        if not path:
            continue
        url = entry.get("url", "(no url)")
        full = SOURCES_DIR / path
        if full.exists():
            continue
        rel = f"sources/{path}"
        if _is_gitignored(rel):
            # Expected-absent on a fresh clone (git-ignored large media).
            # Record out-of-band; not an Issue. Recoverable from the
            # source URL / Wayback per the manifest entry.
            ctx.missing_sources[rel] = url
            continue
        yield Issue(
            rel, "error",
            f"Archived source file missing on disk (cited URL: {url})",
            check_name=CHECK_NAME,
        )
