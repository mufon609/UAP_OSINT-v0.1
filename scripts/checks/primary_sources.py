"""primary-sources check — research-artifact ResearchContext check.

Verifies every entry in the ``primary_sources`` list has the required
fields (``path``, ``format``) and that the path appears in
``sources/manifest.yaml``.

Universal — runs on every research artifact. Distinct from the other
universal entry-list checks in not using ``_research_utils`` helpers,
because primary_sources entries have no ``id`` lifecycle field.

Layering note: this check does NOT enforce minimum-1 entry. An
artifact authored with ``primary_sources: []`` wouldn't error here;
``artifact_top_level`` enforces key presence but not minimum content.
Downstream checks catch empty primary_sources indirectly — prose_drift
warns when the source-token pool is empty; verbatim_quotes
cross-references each quote's source.path against the manifest.
Minimum-1 enforcement could land here if downstream coverage proves
insufficient.
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
