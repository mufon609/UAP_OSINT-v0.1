"""quotes check — research-artifact ResearchContext check.

The universal evidentiary primitive. Each entry: required ``text`` +
``source`` (dict with path + location). Person-artifact quotes
additionally require ``observation_type`` (direct | relayed) and
``context`` for the renderer's Attributed-to row.

Universal — runs on every research artifact. ``observation_type``
enforcement varies by target_type.

Origin: foundational from the initial commit (``af5f789``); the
basic shape (text + source + manifest membership + id uniqueness +
lifecycle) was the original check_quotes in the first
validate-research.py. The check accumulated rules across three
later commits as the schema tightened:

  - ``8007ef1`` (F.1a — person schema under statements-only
    discipline) added ``observation_type`` required on person
    artifacts with enum {direct, relayed}; warn when set on non-
    person. The direct/relayed distinction enables the person
    renderer to split Statements into Direct Observations vs Other
    Statements subsections.

  - ``83b19c6`` ("Pre-F.1c hardening: require ``context`` on person
    quotes") was a reactive fix: the F.1b audit found that the
    renderer's verification-block Attributed-to row is composed
    from ``context + statement_date``, and if both are empty the
    row is omitted entirely — violating
    ``schema.yaml::quote_verification_fields.required``. Rather
    than enforce the output shape in validate.py (which would
    catch missing rows post-render), the fix enforced the input
    on the artifact: every person-artifact quote must carry
    ``context``. The renderer can then rely on producing a
    complete Attributed-to row.

  - ``cde69cf`` (claims[] layer elimination, 2026-04-21) didn't
    change check_quotes itself but elevated quotes[] to the
    universal evidentiary primitive across all node types. Every
    "claim-like" rendered surface (Statements, Key Testimony, Key
    Passages, Claim Inventory) is now a filtered view of quotes[];
    the check correspondingly bears the load for every artifact's
    primary evidentiary content.

Layered enforcement around quote integrity:

  - This check (``quotes``): entry-shape (text + source + person-
    archetype-conditional observation_type / context).
  - ``verbatim_quotes`` (NodeContext): the quote text actually
    appears verbatim in the cited source file (the load-bearing
    backstop from the pilot-failure-2026-04-17 postmortem).
  - ``coverage`` (Phase III): the artifact's quote text appears in
    the rendered node body (artifact↔node consistency).
  - ``prose_drift`` / ``description_token_drift`` (per-prose-field
    surfaces): different axes; not quote-shape concerns.

Render-time ordering / Attributed-to composition uses
``statement_date`` which is optional at the entry layer per schema
(conditional on renderer's ordering needs). Each layer enforces
what it can verify; layered design avoids double-firing on the
same defect.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape).
C18 confirmed byte-identity through the lift.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
)


CHECK_NAME = "quotes"


def check(ctx):
    # Schema-driven enum: closed values for ``observation_type`` come
    # from ``schema.yaml::types.research-artifact.quote_entry
    # .observation_type_values``. Direct subscript surfaces a loud
    # KeyError on schema malformation per the C21 no-silent-fallbacks
    # principle.
    valid_observation_types = ctx.schema["types"]["research-artifact"][
        "quote_entry"]["observation_type_values"]

    quotes = entries(ctx.data, "quotes")
    yield from check_unique_ids(ctx.rel, quotes, "quotes", CHECK_NAME)
    for i, q in enumerate(quotes):
        if not isinstance(q, dict):
            continue
        yield from check_lifecycle_fields(ctx.rel, q, "quotes", i, CHECK_NAME)
        if "text" not in q:
            yield Issue(
                ctx.rel, "error",
                f"quotes[{i}] ({q.get('id')!r}): missing required 'text'",
                check_name=CHECK_NAME,
            )
        src = q.get("source")
        if not isinstance(src, dict):
            yield Issue(
                ctx.rel, "error",
                f"quotes[{i}] ({q.get('id')!r}): 'source' must be a dict "
                f"with path + location",
                check_name=CHECK_NAME,
            )
            continue
        if "path" not in src or "location" not in src:
            yield Issue(
                ctx.rel, "error",
                f"quotes[{i}] ({q.get('id')!r}): source must include "
                f"'path' and 'location'",
                check_name=CHECK_NAME,
            )
        if src.get("path") and src["path"] not in ctx.manifest_paths:
            yield Issue(
                ctx.rel, "error",
                f"quotes[{i}] ({q.get('id')!r}): source.path "
                f"{src['path']!r} not in sources/manifest.yaml",
                check_name=CHECK_NAME,
            )

        # observation_type + context — required on every quote when
        # target_type is person; ignored otherwise. The person renderer
        # composes the Attributed-to row from `context` + `statement_date`;
        # a quote missing context renders without an Attributed-to row,
        # violating the schema's quote_verification_fields requirement.
        if ctx.target_type == "person":
            obs = q.get("observation_type")
            if not obs:
                yield Issue(
                    ctx.rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): missing required "
                    f"'observation_type' (required on person artifacts; "
                    f"value in {sorted(valid_observation_types)})",
                    check_name=CHECK_NAME,
                )
            elif obs not in valid_observation_types:
                yield Issue(
                    ctx.rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): observation_type "
                    f"{obs!r} not in {sorted(valid_observation_types)}",
                    check_name=CHECK_NAME,
                )
            ctx_field = q.get("context")
            if not ctx_field or not str(ctx_field).strip():
                yield Issue(
                    ctx.rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): missing required "
                    f"'context' (required on person artifacts so the "
                    f"renderer produces a complete Attributed-to row; "
                    f"describes where / when / under what circumstances "
                    f"the speaker made the statement)",
                    check_name=CHECK_NAME,
                )
        elif ctx.target_type is not None and q.get("observation_type"):
            yield Issue(
                ctx.rel, "warn",
                f"quotes[{i}] ({q.get('id')!r}): observation_type set on "
                f"a non-person artifact (target_type {ctx.target_type!r}) — "
                f"ignored by renderer; consider removing",
                check_name=CHECK_NAME,
            )
