"""phase-iii-inputs check — preflight for review-coverage.py.

Validates the cross-layer inputs the four review checks (boundary,
coverage, stub_linking, description_token_drift) require:

  - ``target_node`` frontmatter points to a real ``/{type}/{slug}.md``
    file (FATAL — boundary / coverage / stub_linking all read
    ``ctx.node_text``; without a target file the chain can't run).
  - Every ``primary_sources[].path`` is locally available + text-
    extractable. Missing files error; binary-by-design (image /
    video / audio per manifest format) silently skip per the
    extraction contract.

Runs after ``artifact_parse`` cleared the file / YAML-shape preflight.
Source-extraction warnings are non-fatal — only
``description_token_drift`` consumes ``ctx.source_text``, and it
short-circuits internally on empty / missing source. Errors here are
about source-archival integrity (a registered manifest path that's
gone missing on disk), not pipeline blockers.
"""

from checks import Issue
from lib._common import SOURCES_DIR, extract_source_text


CHECK_NAME = "phase_iii_inputs"


def check(ctx):
    """Yield Issues for cross-layer input failures. Fatal on missing
    target_node; non-fatal on source-extraction failures (boundary /
    coverage / stub_linking don't need source_text)."""
    target_node = ctx.data.get("target_node") if ctx.data else None

    if ctx.node_path is None or not ctx.node_path.exists():
        yield Issue(
            ctx.rel, "error",
            f"target_node {target_node!r} does not point to an existing file",
            check_name=CHECK_NAME, fatal=True,
        )
        return

    for ps in (ctx.data.get("primary_sources") or []):
        if not isinstance(ps, dict):
            continue
        rel_path = ps.get("path")
        if not rel_path:
            continue
        # Binary primary sources (image/video/audio) are not text-
        # extractable by design — silent skip rather than warn (matches
        # the manifest extraction contract).
        if ps.get("format") in ("image", "video", "audio"):
            continue
        full = SOURCES_DIR / rel_path
        if not full.exists():
            yield Issue(
                ctx.rel, "error",
                f"primary source {rel_path!r} missing — file not present "
                f"on disk under sources/. Source-archival integrity issue; "
                f"verify the manifest entry and re-archive if needed.",
                check_name=CHECK_NAME,
            )
            continue
        text = extract_source_text(full)
        if text is None:
            yield Issue(
                ctx.rel, "warn",
                f"primary source {rel_path!r} not text-extractable "
                f"(extraction returned no text). Tokens from this source "
                f"won't reach Phase III drift checks; verbatim quote "
                f"verification from this source requires manual contributor "
                f"review.",
                check_name=CHECK_NAME,
            )
