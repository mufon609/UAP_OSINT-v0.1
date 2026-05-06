"""doc-form-archival-status check — per-node NodeContext check.

Document-specific value-vocabulary enforcement, orthogonal to
``conditionally_required`` (which gates required-presence by
condition; this gates value validity whenever the field is set).

  - ``doc_form``         → warn on values outside ``doc_form_values``
                           (extensible vocabulary; warn rather than error
                           so contributors can land new doc_form values
                           without schema friction).
  - ``archival_status``  → error on values outside ``archival_status_values``
                           (enforced whenever set, whether or not
                           ``conditionally_required`` triggers the
                           archival_status-when-book branch).

No-ops when node_type is not ``document``.

Lift from validate.py validate_node (C11 session-3 migration).
"""

from checks import Issue


CHECK_NAME = "doc_form_archival_status"


def check(ctx):
    if ctx.node_type != "document":
        return
    fm = ctx.fm
    type_spec = ctx.type_spec

    valid_forms = type_spec.get("doc_form_values", [])
    df = fm.get("doc_form")
    if df and valid_forms and df not in valid_forms:
        yield Issue(
            ctx.rel, "warn",
            f"Unknown doc_form '{df}' (not in schema list; add if established)",
            check_name=CHECK_NAME,
        )

    if fm.get("archival_status"):
        archival = fm["archival_status"]
        valid_archival = type_spec.get("archival_status_values", [])
        if valid_archival and archival not in valid_archival:
            yield Issue(
                ctx.rel, "error",
                f"Invalid archival_status {archival!r}. Valid: {valid_archival}",
                check_name=CHECK_NAME,
            )
