"""manifest-value-enums check — global BaseContext check.

Validates closed-enum fields against the schema:

  - URL-level ``status``    → ``manifest_entry.status_values``
                              (archived | 403-blocked | 402-blocked | pending)
  - Artifact-level ``format`` → ``artifact_entry.format_values``
                              (pdf | html | txt | audio | image | video | transcript)

Errors on any URL entry whose ``status`` is outside the declared
enum, or any artifact whose ``format`` is outside the declared enum.
``extraction_type`` is validated by ``manifest_extraction_type``;
``archive_status`` enum + bit-consistency is validated by
``manifest_archive_status``.

``status`` is load-bearing for ``manifest_archive_status``, which
routes on ``status == "archived"``. A typoed status value (e.g.
``"Archived"`` with capital A) would produce a wrong bit-0
calculation downstream; this check catches the underlying typo at
the source.
"""

from checks import Issue
from lib._common import iter_artifacts


CHECK_NAME = "manifest_value_enums"
MANIFEST_REL = "sources/manifest.yaml"


def check(ctx):
    """Yield error-level Issue for any URL entry whose ``status`` or
    artifact whose ``format`` is outside the schema's enum."""
    valid_status = ctx.schema["manifest_entry"]["status_values"]
    valid_format = ctx.schema["artifact_entry"]["format_values"]

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

    for entry, artifact in iter_artifacts(ctx.manifest_entries):
        fmt = artifact.get("format")
        if fmt is not None and fmt not in valid_format:
            url = entry.get("url", "(no url)")
            path = artifact.get("path", "(no path)")
            yield Issue(
                MANIFEST_REL, "error",
                f"format must be one of {list(valid_format)}; "
                f"got {fmt!r} (artifact sources/{path} on URL: {url})",
                check_name=CHECK_NAME,
            )
