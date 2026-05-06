"""doc-form-archival-status check — per-node NodeContext check.

Document-specific value-vocabulary enforcement, orthogonal to
``conditionally_required``:

  - ``doc_form``         → warn on values outside ``doc_form_values``
                           (extensible vocabulary; new doc_form values
                           land without schema friction).
  - ``archival_status``  → error on values outside
                           ``archival_status_values`` (enforced whenever
                           set, whether or not ``conditionally_required``
                           triggers the archival_status-when-book
                           branch).

No-ops when node_type is not ``document``.

Why this isn't subsumed by ``conditionally_required``:
``conditionally_required`` gates REQUIRED-PRESENCE under a condition
(``archival_status`` MUST be present when ``doc_form == book``). This
check gates VALUE-VALIDITY whenever the field is set, irrespective of
any conditional. ``doc_form: article + archival_status: bogus-value``
would slip through ``conditionally_required`` because article doesn't
trigger the gate; this check catches the bogus value.
"""

from checks import Issue


CHECK_NAME = "doc_form_archival_status"


def check(ctx):
    if ctx.node_type != "document":
        return
    fm = ctx.fm
    type_spec = ctx.type_spec

    # Direct subscripts: both fields are declared on the document type
    # spec per schema.yaml; this check is gated to ``node_type ==
    # "document"`` so absence at runtime would be schema drift.
    valid_forms = type_spec["doc_form_values"]
    df = fm.get("doc_form")
    if df and df not in valid_forms:
        yield Issue(
            ctx.rel, "warn",
            f"Unknown doc_form '{df}' (not in schema list; add if established)",
            check_name=CHECK_NAME,
        )

    if fm.get("archival_status"):
        archival = fm["archival_status"]
        valid_archival = type_spec["archival_status_values"]
        if archival not in valid_archival:
            yield Issue(
                ctx.rel, "error",
                f"Invalid archival_status {archival!r}. Valid: {valid_archival}",
                check_name=CHECK_NAME,
            )
