"""quotes check — research-artifact ResearchContext check.

Quotes are the universal evidentiary primitive. Each entry: required
``text`` + ``source`` (dict with path + location). Person-artifact
quotes additionally require:

  - ``observation_type`` (direct | relayed) — drives the renderer's
    Direct Observations vs Other Statements subsection split.
  - ``context`` — composed with ``statement_date`` into the
    Attributed-to row of the rendered verification block; both empty
    would omit the row and violate
    ``schema.yaml::quote_verification_fields.required``.

Transcript-artifact quotes additionally require:

  - ``speaker_id`` — references one of the artifact's
    ``speakers[*].id`` values; surfaces in the rendered verification
    block as a Speaker row. Structural attribution; prevents
    contributor-prose drift on who-said-what across re-edits and
    audits.

Universal — runs on every research artifact. ``observation_type``,
``context``, and ``speaker_id`` enforcement varies by target_type.

Layered enforcement around quote integrity:

  - This check (``quotes``): entry-shape (text + source + person-
    archetype-conditional observation_type / context).
  - ``verbatim_quotes`` (NodeContext): the quote text actually appears
    verbatim in the cited source file (load-bearing fabrication
    backstop).
  - ``coverage`` (cross-layer): the artifact's quote text appears in
    the rendered node body.
  - ``prose_drift`` / ``description_token_drift`` (per-prose-field
    surfaces): different axes; not quote-shape concerns.

Render-time ordering / Attributed-to composition uses
``statement_date``, which is optional at the entry layer per schema.
Each layer enforces what it can verify; the split avoids double-firing
on the same defect.
"""

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
)


CHECK_NAME = "quotes"


def check(ctx):
    # Closed enum values for ``observation_type`` and
    # ``attestation_tier`` come from
    # ``schema-research-artifact.yaml::quote_entry``. Direct
    # subscript surfaces a loud KeyError on schema malformation.
    valid_observation_types = ctx.schema["types"]["research-artifact"][
        "quote_entry"]["observation_type_values"]
    valid_attestation_tiers = ctx.schema["types"]["research-artifact"][
        "quote_entry"]["attestation_tier_values"]

    quotes = entries(ctx.data, "quotes")
    yield from check_unique_ids(ctx.rel, quotes, "quotes", CHECK_NAME)

    # Speakers index for transcript-target speaker_id enforcement
    # (see below).
    speakers = entries(ctx.data, "speakers")
    speaker_ids = {s.get("id") for s in speakers if isinstance(s, dict) and s.get("id")}

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

        # speaker_id — required on every quote when target_type is
        # transcript; references speakers[*].id on the same artifact.
        # Structural attribution; renderer surfaces the matched speaker
        # as a Speaker row in the verification block.
        if ctx.target_type == "transcript":
            sid = q.get("speaker_id")
            if not sid:
                yield Issue(
                    ctx.rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): missing required "
                    f"'speaker_id' (required on transcript artifacts; "
                    f"references one of speakers[*].id on this artifact)",
                    check_name=CHECK_NAME,
                )
            elif sid not in speaker_ids:
                yield Issue(
                    ctx.rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): speaker_id {sid!r} "
                    f"not in speakers[].id "
                    f"({sorted(s for s in speaker_ids if s)})",
                    check_name=CHECK_NAME,
                )
        elif ctx.target_type is not None and q.get("speaker_id"):
            yield Issue(
                ctx.rel, "warn",
                f"quotes[{i}] ({q.get('id')!r}): speaker_id set on a "
                f"non-transcript artifact (target_type "
                f"{ctx.target_type!r}) — ignored by renderer; "
                f"consider removing",
                check_name=CHECK_NAME,
            )

        # attestation_tier — optional finding-scoped field. Validate
        # enum membership when present. Warn when set on non-finding
        # artifacts (renderer ignores it).
        tier = q.get("attestation_tier")
        if tier is not None:
            if tier not in valid_attestation_tiers:
                yield Issue(
                    ctx.rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): attestation_tier "
                    f"{tier!r} not in {sorted(valid_attestation_tiers)}",
                    check_name=CHECK_NAME,
                )
            elif ctx.target_type is not None and ctx.target_type != "finding":
                yield Issue(
                    ctx.rel, "warn",
                    f"quotes[{i}] ({q.get('id')!r}): attestation_tier set on "
                    f"a non-finding artifact (target_type {ctx.target_type!r}) "
                    f"— ignored by renderer; consider removing",
                    check_name=CHECK_NAME,
                )
