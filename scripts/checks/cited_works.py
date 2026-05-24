"""cited-works check — type-conditional research-artifact check (load-bearing).

Required-but-emptyable on document artifacts: the formal reference /
citation list the source document carries (e.g. an AAWSAP DIRD's
References section). The KEY is present on every document artifact (empty
list when the document has no reference list, or one not yet captured);
the ``## References`` SECTION renders only when entries exist.

Each entry carries derived bibliographic split fields (``citation_key`` /
``author`` / optional ``year`` / ``title``) for queryability — the
authorship-network dimension, greppable across the corpus for recurring
cited authors — plus a ``citation_verbatim`` line that is the fidelity
anchor: this check substring-matches it against the extracted source
text, the same mechanical backstop ``verbatim_quotes`` applies to
``quotes[]``. OCR corruption in the source reference list is preserved
as-sic in ``citation_verbatim`` (never silently corrected); the split
fields are the contributor's structured read of that verbatim string.

Layered enforcement, parallel to the quote family:

  - this check (entry shape + source-fidelity): required fields present,
    ``source`` is a manifest-known path + location, and
    ``citation_verbatim`` appears verbatim in the cited source file.
  - ``coverage`` (cross-layer): the rendered ``## References`` content
    appears in the node body — source → artifact → node.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors (cited_works on a non-document artifact, or missing on a document
artifact) come from ``iff_section``. Requires ``pdftotext`` for PDF
sources; OCR-scan PDFs prefer a same-stem ``.txt`` sibling per
``sources/manifest.yaml`` (handled inside ``extract_source_text``).
Binary-by-design sources warn rather than error.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
    require_source_dict,
    section_in_scope,
)
from lib._common import (
    BINARY_FORMATS,
    SOURCES_DIR,
    extract_source_text,
    manifest_format,
    normalize_for_compare,
)


CHECK_NAME = "cited_works"


def check(ctx):
    if not section_in_scope(ctx, "cited_works"):
        return  # iff_section handled placement; skip per-entry validation
    if "cited_works" not in ctx.data:
        return  # iff_section emitted "required missing"; nothing to validate

    # Schema-driven required-field list — single source of truth on the
    # entry definition; lifecycle fields (id / added_date) checked separately.
    required_fields = ctx.schema["types"]["research-artifact"][
        "cited_work_entry"]["required"]

    items = entries(ctx.data, "cited_works")
    yield from check_unique_ids(ctx.rel, items, "cited_works", CHECK_NAME)
    for i, cw in enumerate(items):
        if not isinstance(cw, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, cw, "cited_works", i, CHECK_NAME)

        for field in required_fields:
            if field == "source":
                continue  # validated below via require_source_dict
            if not cw.get(field):
                yield Issue(
                    ctx.rel, "error",
                    f"cited_works[{i}] ({cw.get('id')!r}): missing required {field!r}",
                    check_name=CHECK_NAME,
                )
        yield from require_source_dict(
            ctx.rel, cw, "cited_works", i, ctx.manifest_paths, CHECK_NAME)

        # Source-fidelity: citation_verbatim must appear in the source file.
        verbatim = cw.get("citation_verbatim")
        src = cw.get("source")
        if not verbatim or not isinstance(verbatim, str):
            continue  # missing-field error already emitted above
        if not isinstance(src, dict):
            continue  # require_source_dict already emitted the shape error
        rel_source = src.get("path")
        if not rel_source:
            continue  # require_source_dict already emitted

        cid = cw.get("id")
        source_file = SOURCES_DIR / rel_source
        if not source_file.exists():
            yield Issue(
                ctx.rel, "error",
                f"cited_works[{i}] ({cid!r}): cites missing source file: "
                f"sources/{rel_source}",
                check_name=CHECK_NAME,
            )
            continue
        source_text = extract_source_text(source_file)
        if source_text is None:
            fmt = manifest_format(rel_source)
            if fmt in BINARY_FORMATS:
                yield Issue(
                    ctx.rel, "warn",
                    f"cited_works[{i}] ({cid!r}): cites sources/{rel_source} "
                    f"(format: {fmt}) — citation-verbatim check requires manual "
                    f"contributor verification of binary source",
                    check_name=CHECK_NAME,
                )
            else:
                yield Issue(
                    ctx.rel, "warn",
                    f"cited_works[{i}] ({cid!r}): cites sources/{rel_source} but "
                    f"text extraction failed (pdftotext missing or failed)",
                    check_name=CHECK_NAME,
                )
            continue
        if normalize_for_compare(verbatim) not in normalize_for_compare(source_text):
            preview = verbatim[:80] + ("..." if len(verbatim) > 80 else "")
            yield Issue(
                ctx.rel, "error",
                f'cited_works[{i}] ({cid!r}): citation_verbatim NOT FOUND in '
                f'sources/{rel_source}: "{preview}"',
                check_name=CHECK_NAME,
            )
