"""quotes check — research-artifact ResearchContext check.

The universal evidentiary primitive. Each entry: required ``text`` +
``source`` (dict with path + location). Person-artifact quotes
additionally require ``observation_type`` (direct | relayed) and
``context`` for the renderer's Attributed-to row.

Universal — runs on every research artifact. ``observation_type``
enforcement varies by target_type.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
)


CHECK_NAME = "quotes"

VALID_OBSERVATION_TYPES = {"direct", "relayed"}


def check(ctx):
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
                    f"value in {sorted(VALID_OBSERVATION_TYPES)})",
                    check_name=CHECK_NAME,
                )
            elif obs not in VALID_OBSERVATION_TYPES:
                yield Issue(
                    ctx.rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): observation_type "
                    f"{obs!r} not in {sorted(VALID_OBSERVATION_TYPES)}",
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
