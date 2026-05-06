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

Origin: foundational from the initial commit (``af5f789``) — value-
vocabulary enforcement on ``doc_form`` and ``archival_status`` was
inline in validate.py from day one.

Anchor pattern: foundational orthogonal guard. Despite surface
similarity to ``conditionally_required``, the two checks cover
distinct cases:

  - ``conditionally_required``: gates REQUIRED-PRESENCE under a
    condition (e.g., archival_status MUST be present when
    doc_form == book). When the condition fires, errors on missing
    OR on invalid value — covers both presence and vocabulary
    on the conditional path.
  - ``doc_form_archival_status`` (this check): gates VALUE-VALIDITY
    whenever the field is set, IRRESPECTIVE of any conditional
    gate. Two distinct fields:
      • doc_form's extensible vocabulary (WARN-on-unknown so new
        values land without schema friction; no other check covers
        this — conditionally_required doesn't apply because doc_form
        isn't a conditional field)
      • archival_status's closed enum (ERROR whenever an invalid
        value is set, even when the conditional gate doesn't fire —
        e.g., ``doc_form: article + archival_status: bogus-value``
        would be silently accepted by conditionally_required since
        the article-doc_form doesn't trigger the archival_status-
        required gate; this check catches the bogus value).

The orthogonal-concern coexistence is the design point; not a
subsumption candidate.

Migration: ``60bb88d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the migration.
"""

from checks import Issue


CHECK_NAME = "doc_form_archival_status"


def check(ctx):
    if ctx.node_type != "document":
        return
    fm = ctx.fm
    type_spec = ctx.type_spec

    # Direct subscripts: both ``doc_form_values`` and
    # ``archival_status_values`` are declared on the document type spec
    # per schema.yaml; this check is gated to ``node_type == "document"``
    # so absence at runtime would be schema drift. Loud KeyError per
    # the C21 no-silent-fallbacks principle.
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
