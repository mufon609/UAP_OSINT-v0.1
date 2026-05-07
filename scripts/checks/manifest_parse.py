"""manifest-parse check — preflight for the manifest-integrity check family.

Validates ``sources/manifest.yaml`` parses cleanly and the root is a list
of entries. Two fatal cases:

  - ``strict_yaml_load`` raises YAMLError.
  - Root value is not a list.

Missing manifest is silent (manifest is optional in toolkit shape; a
fresh fork-target may not have one yet). The three manifest-integrity
checks (``manifest_checksums``, ``manifest_archive_status``,
``manifest_extraction_type``) no-op on an empty ``manifest_entries``,
so silent absence is correct behavior.

Runs as a preflight in ``validate.py`` before the manifest-integrity
checks. On fatal Issue, the orchestrator skips the family (the three
checks would silently no-op on the empty fallback anyway, but the
explicit gate keeps the dependency obvious).
"""

import yaml

from checks import Issue
from lib._common import MANIFEST_PATH, strict_yaml_load


CHECK_NAME = "manifest_parse"
MANIFEST_REL = "sources/manifest.yaml"


def check(ctx):
    """Yield fatal Issues for manifest YAML parse failure or non-list
    root. Reads ``MANIFEST_PATH`` directly (does not depend on
    ``ctx.manifest_entries`` being prepopulated)."""
    if not MANIFEST_PATH.exists():
        return  # manifest is optional; absence silent by design

    try:
        with open(MANIFEST_PATH) as f:
            data = strict_yaml_load(f)
    except yaml.YAMLError as e:
        yield Issue(
            MANIFEST_REL, "error",
            f"Manifest parse failure: {e}",
            check_name=CHECK_NAME, fatal=True,
        )
        return

    if data is not None and not isinstance(data, list):
        yield Issue(
            MANIFEST_REL, "error",
            "Manifest root must be a list of entries",
            check_name=CHECK_NAME, fatal=True,
        )
