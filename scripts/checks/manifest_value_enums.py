"""manifest-value-enums check — global BaseContext check.

Validates closed-enum fields on every manifest entry against the
schema's ``manifest_entry`` enum lists:

  - ``status``  → ``manifest_entry.status_values``
                  (archived | 403-blocked | 402-blocked | pending)
  - ``format``  → ``manifest_entry.format_values``
                  (pdf | html | txt | audio | image | video | transcript)

Errors on any entry whose ``status`` or ``format`` value is outside the
declared enum. ``extraction_type`` is optional and validated by the
sibling ``manifest_extraction_type`` check; ``archive_status`` enum +
bit-consistency is validated by ``manifest_archive_status``. Together
the three manifest checks cover the four closed enums on
``manifest_entry``.

Coverage gap closed by this check: prior to it, contributor typos in
``status`` or ``format`` (e.g. ``"Archived"`` with capital A,
``"PDF"`` upper-case, ``"vid"`` truncation) would silently slip through
the validator. ``status`` is load-bearing — ``manifest_archive_status``
routes on ``status == "archived"`` and a typoed status value would
produce a wrong bit-0 calculation; the validator wouldn't catch the
underlying typo, only the resulting bit inconsistency.

Origin: filed during the post-bundle audit pass when the schema's
``status_values`` and ``format_values`` enums were found to be
declared but unenforced — same coverage shape as
``extraction_type_values`` (covered) and ``archive_status_values``
(covered). This check closes the analogous gap for the remaining two.
"""

from checks import Issue


CHECK_NAME = "manifest_value_enums"
MANIFEST_REL = "sources/manifest.yaml"


def check(ctx):
    """Yield error-level Issue for any entry whose ``status`` or
    ``format`` is outside the schema's enum. Direct subscripts on the
    schema-declared enum lists per the C21 no-silent-fallbacks
    principle."""
    manifest_spec = ctx.schema["manifest_entry"]
    valid_status = manifest_spec["status_values"]
    valid_format = manifest_spec["format_values"]

    for entry in ctx.manifest_entries:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url", "(no url)")

        status = entry.get("status")
        if status is not None and status not in valid_status:
            yield Issue(
                MANIFEST_REL, "error",
                f"status must be one of {list(valid_status)}; "
                f"got {status!r} (URL: {url})",
                check_name=CHECK_NAME,
            )

        fmt = entry.get("format")
        if fmt is not None and fmt not in valid_format:
            yield Issue(
                MANIFEST_REL, "error",
                f"format must be one of {list(valid_format)}; "
                f"got {fmt!r} (URL: {url})",
                check_name=CHECK_NAME,
            )
