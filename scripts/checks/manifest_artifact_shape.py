"""manifest-artifact-shape check — global BaseContext check.

Enforces the four C29 invariants on ``sources/manifest.yaml``:

  1. Every URL is unique (one entry per source URL).
  2. Every artifact path is unique across the entire manifest (a given
     file can't be registered as a rendering of two different URLs).
  3. ``artifacts`` is non-empty when ``status == archived`` (an archived
     URL must have at least one archived rendering on disk).
  4. ``artifacts`` is empty when ``status != archived`` (pending /
     blocked URLs have nothing archived yet).

The check is structural — it does NOT verify file integrity (that's
``manifest_checksums``), state-bit consistency (``manifest_archive_status``),
or enum membership (``manifest_value_enums`` / ``manifest_extraction_type``).
This check covers the C29 invariants that those four pre-existing
checks didn't enforce: the new schema's primary/derived discipline.

Errors loudly on any violation. The manifest is a foundational
toolkit contract — silent drift in the URL ↔ artifacts model
propagates to every downstream consumer (verbatim-quote check, the
verifier-agent in A2, manifest.py CLI commands).

Consumes ``BaseContext.manifest_entries`` from the orchestrator's
single manifest load. Dispatched from validate.py's manifest-
integrity preflight family.
"""

from collections import Counter

from checks import Issue
from lib._common import iter_artifacts


CHECK_NAME = "manifest_artifact_shape"
MANIFEST_REL = "sources/manifest.yaml"


def check(ctx):
    """Yield error-level Issue for any URL collision, artifact-path
    collision, or status / artifacts misalignment."""
    # Invariant 1 — URL uniqueness.
    url_counts = Counter()
    for entry in ctx.manifest_entries:
        if isinstance(entry, dict) and entry.get("url"):
            url_counts[entry["url"]] += 1
    for url, n in url_counts.items():
        if n > 1:
            yield Issue(
                MANIFEST_REL, "error",
                f"URL appears in {n} manifest entries (must be unique): {url}",
                check_name=CHECK_NAME,
            )

    # Invariant 2 — artifact path uniqueness across the whole manifest.
    path_to_urls = {}
    for entry, artifact in iter_artifacts(ctx.manifest_entries):
        path = artifact.get("path")
        if not path:
            continue
        path_to_urls.setdefault(path, []).append(entry.get("url"))
    for path, urls in path_to_urls.items():
        if len(urls) > 1:
            yield Issue(
                f"sources/{path}", "error",
                f"Artifact path registered under {len(urls)} different URLs "
                f"(must be unique across manifest): {urls}",
                check_name=CHECK_NAME,
            )

    # Invariants 3 & 4 — status / artifacts alignment.
    for entry in ctx.manifest_entries:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url", "(no url)")
        status = entry.get("status")
        artifacts = entry.get("artifacts") or []
        if status == "archived" and not artifacts:
            yield Issue(
                MANIFEST_REL, "error",
                f"URL has status: archived but no artifacts list — an "
                f"archived URL must have at least one archived rendering "
                f"(URL: {url})",
                check_name=CHECK_NAME,
            )
        elif status != "archived" and artifacts:
            yield Issue(
                MANIFEST_REL, "error",
                f"URL has status: {status!r} but artifacts is non-empty — "
                f"only archived URLs should have artifacts; promote status "
                f"to archived or remove the artifacts (URL: {url})",
                check_name=CHECK_NAME,
            )
