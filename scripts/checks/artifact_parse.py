"""artifact-parse check — preflight for research-artifact loading.

Validates that a research artifact YAML file exists, parses cleanly,
and has a dict root. Three fatal cases:

  - Artifact file missing on disk.
  - ``yaml.safe_load`` raises YAMLError.
  - Root value is not a mapping (dict).

Runs as a preflight in both ``validate-research.py`` (after the
pre-parse text checks; before the main ``_ARTIFACT_CHECKS`` chain)
and ``review-coverage.py`` (before the ``_REVIEW_CHECKS`` chain).
Downstream checks rely on ``ctx.data`` being a dict.

Per-artifact parse failures yield fatal Issues without short-
circuiting the iteration, so an ``--all`` run continues over the
rest of the corpus.
"""

import yaml

from checks import Issue


CHECK_NAME = "artifact_parse"


def check(ctx):
    """Yield fatal Issues if ``ctx.path`` is missing, unparseable, or
    has a non-dict root. Reads the file directly (does not depend on
    ``ctx.data`` being prepopulated)."""
    if not ctx.path.exists():
        yield Issue(
            ctx.rel, "error",
            "Artifact file does not exist",
            check_name=CHECK_NAME, fatal=True,
        )
        return

    try:
        with open(ctx.path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        yield Issue(
            ctx.rel, "error",
            f"YAML parse failure: {e}",
            check_name=CHECK_NAME, fatal=True,
        )
        return

    if not isinstance(data, dict):
        yield Issue(
            ctx.rel, "error",
            "Research artifact root must be a YAML mapping (dict)",
            check_name=CHECK_NAME, fatal=True,
        )
