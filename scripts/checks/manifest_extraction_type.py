"""manifest-extraction-type check — global BaseContext check.

``extraction_type`` is an optional manifest field (default
``text-native``) classifying how a source yields text:

  - text-native      — clean text layer; pdftotext / direct read sufficient
  - ocr-scan         — text layer from OCR; character-level corruption risk
  - extraction-lossy — text-native PDF but extraction layer is unreliable
                       (Unicode mapping artifacts, font encoding issues)

The field drives ingestion-pipeline behavior (the validator prefers a
same-stem ``.txt`` sibling over pdftotext output for non-text-native
sources). This check verifies the field's value, when present, is one
of the schema's enum members; unknown values fail loudly so typos
can't silently disable downstream OCR-handling logic.

Consumes ``BaseContext.manifest_entries`` from the orchestrator's
single manifest load.
"""

from checks import Issue


CHECK_NAME = "manifest_extraction_type"
MANIFEST_REL = "sources/manifest.yaml"

_VALID_VALUES = ("text-native", "ocr-scan", "extraction-lossy")


def check(ctx):
    """Yield error-level Issue for any entry whose extraction_type is
    set to a value outside the schema's enum."""
    for entry in ctx.manifest_entries:
        if not isinstance(entry, dict):
            continue
        if "extraction_type" not in entry:
            continue
        et = entry.get("extraction_type")
        if et not in _VALID_VALUES:
            url = entry.get("url", "(no url)")
            yield Issue(
                MANIFEST_REL, "error",
                f"extraction_type must be one of {list(_VALID_VALUES)}; "
                f"got {et!r} (URL: {url})",
                check_name=CHECK_NAME,
            )
