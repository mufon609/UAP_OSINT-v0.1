"""artifact-parse check — preflight for research-artifact loading.

Validates the orchestrator's load + parse step succeeded. Three fatal
cases:

  - Artifact file missing on disk.
  - YAML parse failure (orchestrator captured the YAMLError into
    ``ctx.parse_error``).
  - Root value is not a mapping (dict).

Pure inspection — does NOT read the file. The orchestrator owns the
load + parse and populates ``ctx.data`` on success, ``ctx.parse_error``
on YAML failure. This check reads that state and yields fatal Issues;
downstream Context construction reuses ``ctx.data`` so no second parse
runs.

Runs as a preflight in both ``validate-research.py`` (after the
pre-parse text checks; before the main ``_ARTIFACT_CHECKS`` chain)
and ``review-coverage.py`` (before the ``_REVIEW_CHECKS`` chain).
Per-artifact parse failures yield fatal Issues without short-
circuiting the iteration, so an ``--all`` run continues over the
rest of the corpus.
"""

from checks import Issue


CHECK_NAME = "artifact_parse"


def check(ctx):
    """Yield fatal Issues for missing file, parse error, or non-dict
    root. Reads only ``ctx.path`` (existence) and ``ctx.parse_error`` /
    ``ctx.data`` (populated by orchestrator)."""
    if not ctx.path.exists():
        yield Issue(
            ctx.rel, "error",
            "Artifact file does not exist",
            check_name=CHECK_NAME, fatal=True,
        )
        return

    if ctx.parse_error is not None:
        yield Issue(
            ctx.rel, "error",
            f"YAML parse failure: {ctx.parse_error}",
            check_name=CHECK_NAME, fatal=True,
        )
        return

    if not isinstance(ctx.data, dict):
        yield Issue(
            ctx.rel, "error",
            "Research artifact root must be a YAML mapping (dict)",
            check_name=CHECK_NAME, fatal=True,
        )
