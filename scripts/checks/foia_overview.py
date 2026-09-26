"""foia-overview check — type-conditional research-artifact check (foia).

Validates the foia ``document_intrinsic`` keys that render as the
``## Overview`` fact table (key conventions:
``schema-research-artifact.yaml::required_keys`` document_intrinsic
comment):

  - ``fee_category`` → ERROR outside ``foia_fee_category_values`` when set.
  - ``requester_path`` / ``agency_path`` / ``component_path`` → must start
    with ``/`` when set (they render as wrapped node links).
  - ``submitted_date`` → ISO ``YYYY-MM-DD`` / ``YYYY-MM`` when set.
  - ``request_state`` → must NOT be set here: the request's state is the
    node's frontmatter ``request_state`` (the renderer mirrors it into the
    Overview); a second copy in the artifact would drift.

No-ops unless the artifact's target type is ``foia``.
"""

import re

from checks import Issue


CHECK_NAME = "foia_overview"

_ISO_DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def check(ctx):
    if ctx.target_type != "foia":
        return
    di = ctx.data.get("document_intrinsic")
    if not isinstance(di, dict):
        return  # artifact_top_level owns the shape of the required key

    valid_fees = ctx.schema["types"]["research-artifact"]["foia_fee_category_values"]
    fee = di.get("fee_category")
    if fee is not None and fee not in valid_fees:
        yield Issue(
            ctx.rel, "error",
            f"document_intrinsic.fee_category {fee!r} not in {valid_fees}",
            check_name=CHECK_NAME,
        )

    for key in ("requester_path", "agency_path", "component_path"):
        v = di.get(key)
        if v and (not isinstance(v, str) or not v.startswith("/")):
            yield Issue(
                ctx.rel, "error",
                f"document_intrinsic.{key} {v!r} must start with '/'",
                check_name=CHECK_NAME,
            )

    sd = di.get("submitted_date")
    if sd is not None and not _ISO_DATE.match(str(sd).strip()):
        yield Issue(
            ctx.rel, "error",
            f"document_intrinsic.submitted_date {sd!r} must be YYYY-MM-DD (or YYYY-MM)",
            check_name=CHECK_NAME,
        )

    if "request_state" in di:
        yield Issue(
            ctx.rel, "error",
            "document_intrinsic.request_state must not be set — the request's "
            "state is the foia node's frontmatter `request_state` (mirrored "
            "into the Overview by the renderer)",
            check_name=CHECK_NAME,
        )
