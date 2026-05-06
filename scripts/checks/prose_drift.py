"""prose-drift check — whole-artifact research-artifact check.

Verifies contributor-prose surfaces source their vocabulary from
primary-source text. Tokenizes each prose field into significant words
(lowercase, ≥3 chars, non-stopword) and verifies each token appears
in the referenced source(s).

Impartial reporter — surface drift; the contributor judges each case:
  - WARN on every unmatched significant token (any field, any count).
  - ERROR only when 100% of a field's significant tokens are absent
    from source. 100% divergence is a mathematical observation
    (no shared vocabulary with the source the field claims to draw on),
    not a stylistic threshold. Below 100%, no classification — just
    report.

Scope is CONTRIBUTOR SYNTHESIS PROSE: top-level free-prose fields
(``description``, ``background``, ``uap_relevance``, ``credibility_notes``)
and per-entry synthesis content notes (``ownership_timeline.note``,
``uap_scope_activity.note``, ``key_personnel.note``, ``contracts.note``,
``media_versioning.note``, ``vouching_chain.attestation``). Applied
across all renderer-supported types.

OUT of scope: compact label cells (role titles, short relationship
descriptors, ``timeline[].event``, ``use_status``, ``activity``,
``contracts.subject``, ``publication_record.beat``) and cross-reference
descriptor notes (``corroboration_items.note``,
``witnesses_testimony.note``, ``org_relationships.note``,
``location_relationships.note``). Token-match misfires on label cells
and meta-descriptors; fabrication in those cells is Phase III
semantic-review territory.

Origin: created in response to the F.1c Fravor pilot audit
(introducing commit ``d9bc684``). The pilot built the first person
node end-to-end under statements-only discipline and committed at i0;
the audit found four contributor-prose drift issues despite all
mechanical gates passing clean. RCA isolated the gap — existing
checks operated on the artifact-to-node axis; the source-to-artifact
axis was unchecked for prose, only for verbatim quotes (the
verbatim_quotes check). The new check (then numbered #16, later
renamed prose-drift per the topic-name migration) closed that gap.

Threshold-tuning history: the initial shape used differentiated 80%
error thresholds calibrated to let synthesis-heavy fields (e.g.
``uap_relevance``, ``credibility_notes``) pass without error.
Contributor feedback flagged that as bias — the validator was
encoding a category judgment about which fields "deserve" more
contributor vocabulary headroom. Revised at commit ``836f96a`` to
the impartial single-rule design above (warn on every unmatched
token, error only at 100% mathematical divergence). That revision
established the broader "validator surfaces drift, doesn't classify
it" principle documented in
``meta/conventions.md`` "Prose-drift discipline on synthesis
surfaces"; reference it before proposing any threshold extension or
field-specific tuning.

Per-entry fields pool against the top-level union (∪ primary_sources)
rather than each entry's own ``source.path``. Synthesis-content notes
legitimately draw vocabulary from cross-source synthesis (a voucher's
claim referenced across multiple attestation venues; a contract
described from both the contract itself and external reporting);
per-entry pooling would over-fire on that legitimate case. The union
pool still surfaces fabrication — vocabulary attested by NO cited
source still produces unmatched tokens.

Migration: ``00a985d`` (C11 session 3 lift to per-module shape);
``a572f77`` (2026-05-05 lockstep refactor — ``extract_significant_tokens``,
``load_source_tokens``, ``STOPWORDS`` moved to ``lib._common.py`` for
cross-script lockstep with check-vocab.py and the validator
orchestrators; the description-drift tokenizer at
``review-coverage.py`` uses a different algorithm and is
deliberately NOT consolidated with this one — see commit ``a572f77``
docstring note). C18 confirmed byte-identity through both moves.
"""

from checks import Issue
from checks._research_utils import entries
from lib._common import extract_significant_tokens, load_source_tokens


CHECK_NAME = "prose_drift"


# Top-level prose fields by target type. Pooled against the union of
# all primary_sources[].path token pools.
PROSE_FIELDS_BY_TYPE = {
    "person": ["background", "uap_relevance", "credibility_notes"],
    "event": ["description"],
    "media": ["description"],
    "transcript": ["description"],
    "document": ["description"],
    "organization": ["description"],
    "location": ["description"],
}

# Per-entry prose fields by target type. Each tuple: (list_key,
# field_name_within_entry). Pooled against the union of all
# primary_sources (per entry's own source.path no longer scopes the
# pool — see commentary in the lifted check).
PROSE_ENTRY_FIELDS_BY_TYPE = {
    "person": [
        ("vouching_chain", "attestation"),
    ],
    "event": [],
    "transcript": [],
    "media": [
        ("media_versioning", "note"),
    ],
    "organization": [
        ("key_personnel", "note"),
        ("contracts", "note"),
    ],
    "location": [
        ("ownership_timeline", "note"),
        ("uap_scope_activity", "note"),
    ],
}


def _judge_drift(rel, location, prose_tokens, unmatched):
    """Impartial drift reporter. Warns on every unmatched significant
    token; errors only when 100% of the field's significant tokens are
    absent from source (complete vocabulary divergence — mathematical,
    not stylistic). Below 100%, no classification — contributor reviews.
    """
    if not unmatched:
        return
    preview = ", ".join(sorted(unmatched)[:8])
    if len(unmatched) > 8:
        preview += f", … (+{len(unmatched) - 8} more)"
    if prose_tokens and len(unmatched) == len(prose_tokens):
        yield Issue(
            rel, "error",
            f"{location}: 100% of significant tokens "
            f"({len(unmatched)}/{len(prose_tokens)}) absent from source "
            f"— prose has no shared vocabulary with the source it claims "
            f"to draw on. Unmatched: {preview}",
            check_name=CHECK_NAME,
        )
    else:
        yield Issue(
            rel, "warn",
            f"{location}: {len(unmatched)} significant token(s) not in "
            f"source (prose-drift check — contributor review): {preview}",
            check_name=CHECK_NAME,
        )


def check(ctx):
    target_type = ctx.target_type
    if (target_type not in PROSE_FIELDS_BY_TYPE
            and target_type not in PROSE_ENTRY_FIELDS_BY_TYPE):
        return

    # Pool top-level source tokens = ∪ primary_sources[].path
    top_level_pool = set()
    primary_sources = entries(ctx.data, "primary_sources")
    for src in primary_sources:
        if not isinstance(src, dict):
            continue
        path = src.get("path")
        if not path:
            continue
        tokens = load_source_tokens(path)
        if tokens is not None:
            top_level_pool |= tokens

    if not top_level_pool and primary_sources:
        yield Issue(
            ctx.rel, "warn",
            "prose-drift check: no source text could be extracted from "
            "primary_sources — check skipped (pdftotext missing? source "
            "files present on disk?)",
            check_name=CHECK_NAME,
        )
        return

    for field in PROSE_FIELDS_BY_TYPE.get(target_type, []):
        prose = ctx.data.get(field) or ""
        prose_tokens = extract_significant_tokens(prose)
        if not prose_tokens:
            continue
        unmatched = prose_tokens - top_level_pool
        yield from _judge_drift(ctx.rel, field, prose_tokens, unmatched)

    for list_key, entry_field in PROSE_ENTRY_FIELDS_BY_TYPE.get(target_type, []):
        for i, entry in enumerate(entries(ctx.data, list_key)):
            if not isinstance(entry, dict):
                continue
            prose = entry.get(entry_field) or ""
            prose_tokens = extract_significant_tokens(prose)
            if not prose_tokens:
                continue
            unmatched = prose_tokens - top_level_pool
            yield from _judge_drift(
                ctx.rel,
                f"{list_key}[{i}] ({entry.get('id', '?')!r}) {entry_field}",
                prose_tokens, unmatched,
            )
