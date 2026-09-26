"""records-sought check — type-conditional research-artifact check (foia).

Present on foia artifacts. Each entry: required {description, source},
optional {identifiers, date_range, item_label}, plus the universal
lifecycle fields.

``identifiers`` is a list of ``{scheme, value}``: ``scheme`` is closed
vocabulary (``records_sought_entry.identifier_scheme_values``); ``value``
is the identifier exactly as the entry's cited source prints it. The
value is the load-bearing fidelity anchor of the item — a contract PIID
mistyped by one character points an investigator at the wrong contract —
so it is matched against the extracted ``source.path`` text with the same
``normalize_for_compare`` substring match ``cited_works`` applies to
``citation_verbatim``. A binary / unextractable source degrades to a warn
(manual verification), mirroring cited_works.

``description`` is contributor prose, scanned by the prose-drift check
(``types.foia.prose_drift_fields.per_entry``), not here.

Gating delegated to ``section_in_scope`` (schema-driven); placement
errors come from ``iff_section``.
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


CHECK_NAME = "records_sought"


def _check_identifier_values(ctx, i, e, idents, src_path):
    """Match every identifier value against the entry's cited source."""
    source_file = SOURCES_DIR / src_path
    if not source_file.exists():
        return  # manifest_files_present owns a missing archived file
    source_text = extract_source_text(source_file)
    if source_text is None:
        fmt = manifest_format(src_path)
        if fmt == "image":
            return  # archived image: a sibling would have been extracted above
        yield Issue(
            ctx.rel, "warn",
            f"records_sought[{i}] ({e.get('id')!r}): cites sources/{src_path}"
            + (f" (format: {fmt})" if fmt in BINARY_FORMATS else "")
            + " but no text could be extracted — identifier values need "
              "manual verification",
            check_name=CHECK_NAME,
        )
        return
    norm_source = normalize_for_compare(source_text)
    for j, ident in enumerate(idents):
        value = str(ident.get("value") or "")
        if value.strip() and normalize_for_compare(value) not in norm_source:
            yield Issue(
                ctx.rel, "error",
                f"records_sought[{i}] ({e.get('id')!r}): identifiers[{j}] "
                f"value {value!r} NOT FOUND in sources/{src_path} — record "
                f"the identifier exactly as the source prints it",
                check_name=CHECK_NAME,
            )


def check(ctx):
    if not section_in_scope(ctx, "records_sought"):
        return
    if "records_sought" not in ctx.data:
        return

    valid_schemes = ctx.schema["types"]["research-artifact"][
        "records_sought_entry"]["identifier_scheme_values"]
    items = entries(ctx.data, "records_sought")
    yield from check_unique_ids(ctx.rel, items, "records_sought", CHECK_NAME)
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, e, "records_sought", i, CHECK_NAME)
        if not str(e.get("description") or "").strip():
            yield Issue(
                ctx.rel, "error",
                f"records_sought[{i}] ({e.get('id')!r}): missing required 'description'",
                check_name=CHECK_NAME,
            )
        yield from require_source_dict(
            ctx.rel, e, "records_sought", i, ctx.manifest_paths, CHECK_NAME,
        )

        idents = e.get("identifiers")
        if idents is None:
            continue
        if not isinstance(idents, list):
            yield Issue(
                ctx.rel, "error",
                f"records_sought[{i}] ({e.get('id')!r}): identifiers must be "
                f"a list of {{scheme, value}} (got {type(idents).__name__})",
                check_name=CHECK_NAME,
            )
            continue
        well_formed = []
        for j, ident in enumerate(idents):
            if not isinstance(ident, dict) or not str(ident.get("value") or "").strip():
                yield Issue(
                    ctx.rel, "error",
                    f"records_sought[{i}] ({e.get('id')!r}): identifiers[{j}] "
                    f"must be a dict with a non-empty 'value'",
                    check_name=CHECK_NAME,
                )
                continue
            if ident.get("scheme") not in valid_schemes:
                yield Issue(
                    ctx.rel, "error",
                    f"records_sought[{i}] ({e.get('id')!r}): identifiers[{j}] "
                    f"scheme {ident.get('scheme')!r} not in {valid_schemes}",
                    check_name=CHECK_NAME,
                )
            well_formed.append(ident)

        src = e.get("source")
        src_path = src.get("path") if isinstance(src, dict) else None
        if well_formed and src_path and src_path in ctx.manifest_paths:
            yield from _check_identifier_values(ctx, i, e, well_formed, src_path)
