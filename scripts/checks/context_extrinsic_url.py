"""context-extrinsic primary-source URL check — per-research-artifact.

Enforces that ``context_extrinsic.primary_source_url``, when present,
matches the parent ``url`` of the manifest entry that registers
``primary_sources[0].path``.

Rationale: ``primary_source_url`` records the public URL the primary
source was archived from. The single source of truth for that URL is
``sources/manifest.yaml`` — specifically, the parent ``url`` of the
entry that registers the local artifact path. A mismatch indicates the
URL was constructed, typed from memory, or copied from a stale
reference — the failure mode that motivated this check: a Worker pass
emitted a fabricated URL that no validator caught (the Builder
happened to correct it during merge that time, but nothing
mechanically required the correction).

Mechanical backstop parallel to ``verbatim_quotes`` (quote text vs.
source file) and ``cited_works`` (citation_verbatim vs. source file):
each check pins a field whose value is constructible-by-inference
against the artifact's only authoritative external state.

Skips silently when:
  - the artifact has no ``context_extrinsic`` block (non-document /
    non-media types that don't carry the field)
  - ``primary_source_url`` is unset
  - ``primary_sources`` is empty or shape-malformed (other checks own
    those diagnostics)
  - the manifest has no entry registering ``primary_sources[0].path``
    (``manifest_files_present`` / ``primary_sources`` own that case)

A fragment suffix on the declared URL (e.g.
``#clean-text-transcription``) is stripped before comparison: the
parent manifest entry for a primary PDF carries a bare URL, never a
fragment. Fragments are used on derived-artifact entries (the
``.txt`` sibling that pairs to the PDF) and have no place on the
primary-source URL.
"""

from checks import Issue


CHECK_NAME = "context_extrinsic_url"


def check(ctx):
    data = ctx.data or {}
    ctx_extrinsic = data.get("context_extrinsic")
    if not isinstance(ctx_extrinsic, dict):
        return
    declared_url = ctx_extrinsic.get("primary_source_url")
    if not declared_url:
        return

    primary_sources = data.get("primary_sources")
    if not isinstance(primary_sources, list) or not primary_sources:
        return  # primary_sources check owns shape diagnostics
    first = primary_sources[0]
    if not isinstance(first, dict):
        return
    source_path = first.get("path")
    if not source_path:
        return

    # Find the manifest entry that registers this primary-source path.
    registered_url = None
    for entry in ctx.manifest_entries:
        if not isinstance(entry, dict):
            continue
        for art in entry.get("artifacts") or []:
            if isinstance(art, dict) and art.get("path") == source_path:
                registered_url = entry.get("url")
                break
        if registered_url is not None:
            break

    if registered_url is None:
        # manifest_files_present + primary_sources own this case
        return

    declared_base = str(declared_url).split("#", 1)[0]
    registered_base = str(registered_url).split("#", 1)[0]

    if declared_base != registered_base:
        yield Issue(
            ctx.rel, "error",
            f"context_extrinsic.primary_source_url does not match the "
            f"manifest URL for primary_sources[0].path "
            f"({source_path}). Declared: {declared_url!r}; manifest: "
            f"{registered_url!r}. The manifest entry is the single "
            f"source of truth for source URLs — read it from "
            f"sources/manifest.yaml; never construct or infer.",
            check_name=CHECK_NAME,
        )
