"""primary-sources check — research-artifact ResearchContext check.

Verifies every entry in the ``primary_sources`` list has the required
fields (``path``, ``format``) and that the path appears in
``sources/manifest.yaml``.

Universal — runs on every research artifact regardless of target type.

Origin: foundational from the initial commit (``af5f789``). The
``primary_sources_entry`` schema (``required: [path, format]``,
optional fields ``extracted_text_path / pdf_metadata /
sha256_at_extraction``) and the check function shipped together in
af5f789. Both the schema entry shape and the check have stayed stable
since.

Anchor pattern: stable / stable foundational. Cleanest example of
this shape across the investigated checks — no dispatch, no shared
helpers (this is the only universal entry-list check that doesn't
use ``_research_utils.check_unique_ids`` etc., because
primary_sources entries have no ``id`` lifecycle field), no enum,
no condition, no evolutionary history. Pure shape + cross-reference
enforcement that has been load-bearing from day one.

Layering note: the check does NOT enforce minimum-1 entry. An
artifact authored with ``primary_sources: []`` wouldn't error here;
``artifact_top_level`` enforces key PRESENCE but not minimum
content. Downstream checks catch the empty case indirectly —
``prose_drift`` uses primary_sources to build its source-token pool
and warns on "no source text could be extracted" when the pool is
empty; ``verbatim_quotes`` cross-references each quote's
``source.path`` against the manifest. The foundational discipline
("every artifact cites at least one primary source") is enforced
by the build pipeline + contributor practice, not by this check.
Acceptable layering at current scale; if a real incident surfaces
where an empty primary_sources slips into a committed artifact, a
minimum-1 enforcement could land here.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the lift.
"""

from checks import Issue


CHECK_NAME = "primary_sources"


def check(ctx):
    sources = ctx.data.get("primary_sources") or []
    if not isinstance(sources, list):
        return
    for i, src in enumerate(sources):
        if not isinstance(src, dict):
            yield Issue(
                ctx.rel, "error",
                f"primary_sources[{i}]: must be a dict",
                check_name=CHECK_NAME,
            )
            continue
        if "path" not in src:
            yield Issue(
                ctx.rel, "error",
                f"primary_sources[{i}]: missing required 'path'",
                check_name=CHECK_NAME,
            )
            continue
        if "format" not in src:
            yield Issue(
                ctx.rel, "error",
                f"primary_sources[{i}]: missing required 'format'",
                check_name=CHECK_NAME,
            )
        if src["path"] not in ctx.manifest_paths:
            yield Issue(
                ctx.rel, "error",
                f"primary_sources[{i}]: path {src['path']!r} not registered "
                f"in sources/manifest.yaml",
                check_name=CHECK_NAME,
            )
