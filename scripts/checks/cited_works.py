"""cited-works check — type-conditional research-artifact check (load-bearing).

Document artifacts MUST set ``cited_works`` to one of three valid
shapes — the three-state affirmation that resolves the historical
empty-list ambiguity:

  - ``cited_works: NONE`` (string sentinel) — the source carries no
    reference list. Renders a one-line affirmation; no entry
    validation runs here.
  - ``cited_works: IGNORED`` (string sentinel) — the source HAS a
    reference list, deliberately not captured (low-value release
    valve). Renders a one-line affirmation; no entry validation runs.
    The audit surface for ``IGNORED`` is the rendered node + a
    repo-wide grep, NOT this check or the heuristic
    ``cited_works_uncaptured``.
  - ``cited_works: [<entry>, ...]`` — non-empty list of
    ``cited_work_entry``. Entry validation runs as documented below. A
    bare ``cited_works: []`` is REJECTED — the empty list used to be
    ambiguous between "source has no list" and "list not yet
    captured"; the sentinels now carry the affirmation explicitly.

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

  - this check (state machine + entry shape + source-fidelity): the
    three-shape state machine above; on populated lists, required
    fields present, ``source`` is a manifest-known path + location,
    and ``citation_verbatim`` appears verbatim in the cited source.
  - ``cited_works_uncaptured`` (cross-check, WARN): warns when
    ``cited_works == 'NONE'`` but a reference-list signal is detected
    in the source — a likely-false affirmation. Demoted from primary
    gate to cross-check now that the affirmation is explicit.
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

    value = ctx.data.get("cited_works")
    sentinels = ctx.schema["types"]["research-artifact"][
        "cited_works_sentinel_values"]

    # Three-shape state machine — see module docstring.
    if isinstance(value, str):
        if value in sentinels:
            return  # affirmation — no entry validation
        yield Issue(
            ctx.rel, "error",
            f"cited_works string value {value!r} is not a valid sentinel — "
            f"must be one of {sentinels} (or a non-empty list of "
            f"cited_work_entry).",
            check_name=CHECK_NAME,
        )
        return
    if not isinstance(value, list):
        yield Issue(
            ctx.rel, "error",
            f"cited_works must be a string sentinel (one of {sentinels}) "
            f"or a non-empty list of cited_work_entry; got "
            f"{type(value).__name__}.",
            check_name=CHECK_NAME,
        )
        return
    if not value:
        yield Issue(
            ctx.rel, "error",
            f"cited_works is an empty list — bare [] is no longer valid. "
            f"Use one of {sentinels} to affirm the source's reference-list "
            f"state, or populate with cited_work_entry objects.",
            check_name=CHECK_NAME,
        )
        return

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
