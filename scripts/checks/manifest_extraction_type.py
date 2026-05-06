"""manifest-extraction-type check — global BaseContext check.

``extraction_type`` is an optional manifest field (default
``text-native``) classifying how a source yields text:

  - text-native      — clean text layer; pdftotext / direct read sufficient
  - ocr-scan         — text layer from OCR; character-level corruption risk
  - extraction-lossy — text-native PDF but extraction layer is unreliable
                       (Unicode mapping artifacts, font encoding issues)

The field drives ingestion-pipeline behavior — ``lib._common
.extract_source_text`` prefers a same-stem ``.txt`` sibling over
pdftotext output for any non-text-native source. This check verifies
the field's value, when present, is one of the schema's enum members;
unknown values fail loudly so typos can't silently disable downstream
OCR-handling logic.

Consumes ``BaseContext.manifest_entries`` from the orchestrator's
single manifest load.

Origin: introduced at commit ``978221a`` (BACKLOG #19 Phase A —
"extraction_type metadata on manifest entries"). The field surfaced
reactively from the Grusch v2 audit (2026-04-24) when
``government/grusch-ppd-19-procedural-filing.pdf`` was found to be
an OCR-scanned PDF whose pdftotext extract carried character-level
corruptions (``UAP-telated``, ``compatrtmented``, ``appatently``,
``cottelated``). The convention gap: existing manifest entries had
no metadata distinguishing OCR-scan sources from text-native ones,
so the validator couldn't know when a source needed better
extraction.

Two-stage enum evolution, both reactive:

  - ``978221a`` (Phase A, 2026-04-24): {text-native, ocr-scan}.
    Two values; surfaced from Grusch PPD-19 OCR artifacts.
  - ``4b4d7fb`` (Phase F Tier 1): added ``extraction-lossy`` as a
    third value. Surfaced from the 2023-07-26 House Oversight
    hearing transcript — Grusch's sworn "11½ hours" rendering as
    "11‡ hours" via pdftotext (Unicode mapping artifact at PDF-
    generation layer, NOT OCR-scanned). Acrobat Distiller from
    ``.txt`` source produces this distinct failure shape; same
    operational consequence as ocr-scan (default extraction
    unreliable), so the sibling-lookup logic in
    ``lib._common.extract_source_text`` was generalized from
    ``== "ocr-scan"`` to ``!= "text-native"`` — the mechanism
    extends to any non-default extraction_type.

Three-check manifest family — together with ``manifest_checksums``
(content-byte integrity) and ``manifest_archive_status`` (state-bit
consistency), this check guards a third manifest invariant: enum
discipline on ingestion-pipeline metadata. Each check protects a
different manifest dimension; together they bracket the manifest's
integrity surface.

Migration: ``1c34081`` (C11 session 2 — lifted alongside
manifest_archive_status, closing BACKLOG C14). C18 confirmed byte-
identity through the lift.
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
