"""primary-sources check — research-artifact ResearchContext check.

Verifies every entry in the ``primary_sources`` list has the required
fields (``path``, ``format``) and that the path appears in
``sources/manifest.yaml``.

Universal — runs on every research artifact regardless of target type.
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
