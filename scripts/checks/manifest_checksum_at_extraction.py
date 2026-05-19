"""manifest-checksum-at-extraction check — per-artifact ResearchContext check.

For every ``primary_sources_entry`` carrying ``sha256_at_extraction``,
compare it against the manifest's live ``sha256``. Mismatch errors
loudly — the source bytes the contributor extracted from differ from
the bytes the manifest currently attests.

Defense-in-depth backstop to ``manifest_checksums`` (the source-side
integrity check): manifest_checksums catches "manifest claims X but
the file on disk hashes Y" (silent local corruption or substitution).
This check catches "contributor extracted from bytes X, but manifest
+ disk now both attest Y" (source was re-archived under the same URL
with different bytes between extraction and commit-time validation).
The two checks bracket the source-bytes-integrity window from extraction
through validation.

No-ops on entries lacking ``sha256_at_extraction`` — the field is
optional, contributor-populated at scaffold time via
``research-scaffold.py``. Existing artifacts pre-dating C6 won't carry
the field and won't trip this check.

Also no-ops when:
  - the source path isn't in the manifest (``primary_sources`` check
    already errors on that case);
  - the manifest entry has no live ``sha256`` (``manifest_checksums``
    check already errors when ``status: archived`` lacks one).
"""

from checks import Issue
from lib._common import iter_artifacts


CHECK_NAME = "manifest_checksum_at_extraction"


def check(ctx):
    sources = ctx.data.get("primary_sources") or []
    if not isinstance(sources, list):
        return
    # Build a path → artifact index across every URL entry's artifacts.
    artifact_by_path = {
        a["path"]: a for _, a in iter_artifacts(ctx.manifest_entries)
        if a.get("path")
    }
    for i, src in enumerate(sources):
        if not isinstance(src, dict):
            continue
        captured = src.get("sha256_at_extraction")
        if not captured:
            continue
        path = src.get("path")
        if not path:
            continue
        artifact = artifact_by_path.get(path)
        if artifact is None:
            continue
        live = artifact.get("sha256")
        if not live:
            continue
        if captured != live:
            yield Issue(
                ctx.rel, "error",
                f"primary_sources[{i}]: sha256_at_extraction "
                f"({captured[:16]}…) does not match manifest sha256 "
                f"({live[:16]}…) for sources/{path} — source bytes "
                f"have changed since extraction; re-extract and "
                f"re-verify quotes before committing",
                check_name=CHECK_NAME,
            )
