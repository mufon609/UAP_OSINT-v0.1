"""manifest-extraction-type check — global BaseContext check.

``extraction_type`` is an optional manifest field (default
``text-native``) classifying how a source yields text:

  - text-native      — clean text layer; pdftotext / direct read sufficient
  - ocr-scan         — text layer from OCR; character-level corruption risk
  - extraction-lossy — text-native PDF but extraction layer is unreliable
                       (Unicode mapping artifacts, font encoding issues)

The field drives ingestion-pipeline behavior:
``lib._common.extract_source_text`` prefers a same-stem ``.txt`` sibling
over pdftotext output for any non-text-native source. This check verifies
the field's value, when present, is one of the schema's enum members;
unknown values fail loudly so typos can't silently disable downstream
OCR-handling logic.

Together with ``manifest_checksums`` (content-byte integrity) and
``manifest_archive_status`` (state-bit consistency), this check guards
a third manifest invariant — enum discipline on ingestion-pipeline
metadata.

Consumes ``BaseContext.manifest_entries`` from the orchestrator's
single manifest load.
"""

from checks import Issue


CHECK_NAME = "manifest_extraction_type"
MANIFEST_REL = "sources/manifest.yaml"


def check(ctx):
    """Yield error-level Issue for any entry whose extraction_type is
    set to a value outside the schema's enum. Valid values come from
    ``schema.yaml::manifest_entry.extraction_type_values`` — schema is
    the single source of truth, so adding a new extraction_type is one
    schema edit rather than a schema edit + this check edit."""
    valid_values = ctx.schema["manifest_entry"]["extraction_type_values"]
    for entry in ctx.manifest_entries:
        if not isinstance(entry, dict):
            continue
        if "extraction_type" not in entry:
            continue
        et = entry.get("extraction_type")
        if et not in valid_values:
            url = entry.get("url", "(no url)")
            yield Issue(
                MANIFEST_REL, "error",
                f"extraction_type must be one of {list(valid_values)}; "
                f"got {et!r} (URL: {url})",
                check_name=CHECK_NAME,
            )
