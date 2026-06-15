"""quotes check — research-artifact ResearchContext check.

Quotes are the universal evidentiary primitive. Each entry: required
``text`` + ``source`` (dict with path + location). Person-artifact
quotes additionally require:

  - ``observation_type`` (direct | relayed) — drives the renderer's
    Direct Observations vs Other Statements subsection split.
  - ``context`` — composed with ``statement_date`` into the
    Attributed-to row of the rendered verification block; both empty
    would omit a row the verification block requires.

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

import re

from checks import Issue
from checks._research_utils import (
    check_lifecycle_fields,
    check_unique_ids,
    entries,
)

# source.location must be source-anchored (stable across extract
# regeneration), not extraction-anchored line numbers. Bare ``lines N-M`` /
# ``line N`` shift when the source is re-extracted; ``lines N-M of the
# extract`` is allowed (the extract itself is the cited object).
_EXTRACTION_ANCHORED_LOCATION = re.compile(r"\s*lines?\s+\d", re.IGNORECASE)


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

    # Quote-id index + claim_group map for the person-quote grouping
    # checks (claim_group / corroborated_by; see quote_entry.claim_group).
    quote_ids = {q.get("id") for q in quotes if isinstance(q, dict) and q.get("id")}
    claim_group_of = {
        q.get("id"): q.get("claim_group")
        for q in quotes if isinstance(q, dict) and q.get("id")
    }
    # Quotes pointed at by some other quote's corroborated_by — these
    # render as compact pointers, not full blocks. Used to forbid
    # corroboration chains (a pointer that itself carries corroborated_by).
    pointer_ids = {
        cid for q in quotes if isinstance(q, dict)
        for cid in (q.get("corroborated_by") or [])
    }

    # Sources this artifact declares it draws on. Every quote's source.path
    # must be one of them: a quote IS the artifact drawing on a source
    # (schema: primary_sources = "sources this artifact draws on"), so a
    # quoted path absent from primary_sources[] is an undeclared source.
    # Beyond the consistency defect, an undeclared path routes the source
    # around the primary_sources-keyed sibling gate (ocr_sibling_presence /
    # transcript_sibling_presence iterate primary_sources[], NOT quotes[]) —
    # a degraded source quoted but not declared never gets its mandatory
    # sibling, so verbatim_quotes falls back to the corrupt text layer and
    # the quote matches itself. Empty set => primary_sources is missing /
    # malformed; primary_sources.py owns that diagnostic, so the membership
    # test below is skipped in that case (guarded inline) rather than piling
    # a per-quote error onto a single top-level defect.
    primary_source_paths = {
        s.get("path") for s in entries(ctx.data, "primary_sources")
        if isinstance(s, dict) and s.get("path")
    }

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
        path = src.get("path")
        if path:
            if path not in ctx.manifest_paths:
                yield Issue(
                    ctx.rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): source.path "
                    f"{path!r} not in sources/manifest.yaml",
                    check_name=CHECK_NAME,
                )
            elif primary_source_paths and path not in primary_source_paths:
                # Registered source, but not declared in THIS artifact's
                # primary_sources[]. if/elif (not a second independent if)
                # so a path absent from the manifest fires once, not twice —
                # the manifest miss is the more fundamental defect and wins.
                yield Issue(
                    ctx.rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): source.path {path!r} is "
                    f"not in this artifact's primary_sources[] — a quote may "
                    f"only draw on a declared primary source. Add it to "
                    f"primary_sources[] (which also subjects a degraded "
                    f"source to the sibling gate), or correct the path.",
                    check_name=CHECK_NAME,
                )

        # Reject extraction-anchored location forms. Canonical forms are
        # source-anchored: ``p. N, ¶M``, ``¶N``, ``[MM:SS]``, ``p. N``.
        loc = src.get("location")
        if (isinstance(loc, str)
                and _EXTRACTION_ANCHORED_LOCATION.match(loc)
                and "of the extract" not in loc.lower()):
            yield Issue(
                ctx.rel, "error",
                f"quotes[{i}] ({q.get('id')!r}): source.location {loc!r} is "
                f"extraction-anchored — line numbers shift when the source is "
                f"re-extracted. Use a source-anchored form (p. N, ¶M / ¶N / "
                f"[MM:SS] / p. N), or 'lines N-M of the extract' when the "
                f"extract itself is the cited object.",
                check_name=CHECK_NAME,
            )

        # observation_type + context — required on every quote when
        # target_type is person; ignored otherwise. The person renderer
        # composes the Attributed-to row from `context` + `statement_date`;
        # a quote missing context renders without the Attributed-to row the
        # verification block requires.
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
        # A single id string attributes the quote to one speaker (the
        # common case); a list of 2+ ids attributes a MIXED EXCHANGE to
        # all involved speakers (a passage carrying more than one
        # speaker's words, or a genuinely unresolvable speaker boundary
        # in a label-less source). The list value is itself the mixed
        # marker — the renderer surfaces it as a "Speakers — mixed
        # exchange" row. Structural attribution either way.
        if ctx.target_type == "transcript":
            sid = q.get("speaker_id")
            if not sid:
                yield Issue(
                    ctx.rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): missing required "
                    f"'speaker_id' (required on transcript artifacts; a "
                    f"speakers[*].id string for one speaker, or a list of "
                    f"2+ ids for a mixed exchange)",
                    check_name=CHECK_NAME,
                )
            else:
                sid_list = sid if isinstance(sid, list) else [sid]
                ids_seen = [str(x) for x in sid_list]
                if isinstance(sid, list) and len(sid_list) < 2:
                    yield Issue(
                        ctx.rel, "error",
                        f"quotes[{i}] ({q.get('id')!r}): speaker_id is a "
                        f"list of fewer than 2 ids — use a bare string for "
                        f"a single-speaker quote; a list is only for a "
                        f"mixed exchange (2+ speakers)",
                        check_name=CHECK_NAME,
                    )
                if len(ids_seen) != len(set(ids_seen)):
                    yield Issue(
                        ctx.rel, "error",
                        f"quotes[{i}] ({q.get('id')!r}): speaker_id list "
                        f"has duplicate ids {sid!r}",
                        check_name=CHECK_NAME,
                    )
                for one in sid_list:
                    if one not in speaker_ids:
                        yield Issue(
                            ctx.rel, "error",
                            f"quotes[{i}] ({q.get('id')!r}): speaker_id "
                            f"{one!r} not in speakers[].id "
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

        # claim_group / corroborated_by — person-quote grouping (see
        # quote_entry.claim_group). claim_group must be a non-empty string
        # when present. On person artifacts, where corroborated_by renders
        # as the canonical's "Also attested" pointer list, each
        # corroborated_by id that resolves to a local quote must share the
        # referencing quote's claim_group (else the pointer would land in a
        # different group); an id that resolves to no local quote warns
        # (an external ref does not render in the claim-group view).
        cg = q.get("claim_group")
        if cg is not None and not str(cg).strip():
            yield Issue(
                ctx.rel, "error",
                f"quotes[{i}] ({q.get('id')!r}): claim_group is set but "
                f"empty — omit the key or give it a non-empty label",
                check_name=CHECK_NAME,
            )
        if ctx.target_type == "person":
            if q.get("corroborated_by") and not cg:
                # An ungrouped quote is rendered in its own singleton group, so
                # its corroborated_by can never demote a target to a pointer —
                # the reference is inert in the renderer yet still suppresses
                # the target's coverage check. Reject it at the source.
                yield Issue(
                    ctx.rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): corroborated_by is set but "
                    f"the quote has no claim_group — a corroboration pointer "
                    f"only renders within a claim_group",
                    check_name=CHECK_NAME,
                )
            for cid in (q.get("corroborated_by") or []):
                if cid not in quote_ids:
                    yield Issue(
                        ctx.rel, "warn",
                        f"quotes[{i}] ({q.get('id')!r}): corroborated_by "
                        f"{cid!r} resolves to no quote in this artifact — "
                        f"it will not render in the claim-group view "
                        f"(typo, or an external ref that belongs elsewhere)",
                        check_name=CHECK_NAME,
                    )
                elif cg and claim_group_of.get(cid) != cg:
                    yield Issue(
                        ctx.rel, "error",
                        f"quotes[{i}] ({q.get('id')!r}): corroborated_by "
                        f"{cid!r} is in claim_group "
                        f"{claim_group_of.get(cid)!r}, not {cg!r} — a "
                        f"corroboration pointer must share its primary's "
                        f"claim_group",
                        check_name=CHECK_NAME,
                    )
            # No corroboration chains: a quote pointed at by another's
            # corroborated_by is a pointer (renders as a source link, not a
            # full block), so it must not itself carry corroborated_by —
            # those nested pointers would never render.
            if q.get("corroborated_by") and q.get("id") in pointer_ids:
                yield Issue(
                    ctx.rel, "error",
                    f"quotes[{i}] ({q.get('id')!r}): is itself a corroboration "
                    f"pointer (listed in another quote's corroborated_by) yet "
                    f"carries its own corroborated_by — chains don't render. "
                    f"Point every same-claim quote at one primary instead.",
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
