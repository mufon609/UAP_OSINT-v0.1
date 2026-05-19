"""prose-drift check — whole-artifact research-artifact check.

Verifies contributor-prose surfaces source their vocabulary from
primary-source text. Tokenizes each prose field into significant
words (lowercase, ≥3 chars, non-stopword) and verifies each token
appears in the referenced source(s).

Impartial reporter — surfaces drift; the contributor judges each
case:
  - WARN on every unmatched significant token (any field, any count).
  - ERROR only when 100% of a field's significant tokens are absent
    from source. 100% divergence is a mathematical observation (no
    shared vocabulary with the source the field claims to draw on),
    not a stylistic threshold. Below 100%, no classification — just
    report.

Scope is CONTRIBUTOR SYNTHESIS PROSE: top-level free-prose fields
(``description``, ``background``, ``top_relevance``, ``credibility_notes``)
and per-entry synthesis content notes (``ownership_timeline.note``,
``top_scope_activity.note``, ``key_personnel.note``, ``contracts.note``,
``media_versioning.note``, ``vouching_chain.attestation``,
``contradictions.note``). Applied to renderer-supported types EXCEPT
investigation — see below. See ``meta/conventions.md`` "Prose-drift
discipline on synthesis surfaces" for the principle of record before
proposing any field-specific threshold tuning.

OUT of scope: compact label cells (role titles, short relationship
descriptors, ``timeline[].event``, ``use_status``, ``activity``,
``contracts.subject``, ``publication_record.beat``) and cross-reference
descriptor notes (``corroboration_items.note``,
``witnesses_testimony.note``, ``org_relationships.note``,
``location_relationships.note``). Token-match misfires on label cells
and meta-descriptors; fabrication in those cells is semantic-review
territory.

ALSO OUT of scope: every prose surface on investigation artifacts.
Investigations are speculation-tolerant by design — the
``hypothesis_evaluation`` / ``best_current_answer`` /
``counter_evidence`` / ``open_questions`` / ``closure_path`` /
``resolution_history`` surfaces (and the investigation's umbrella
``description``) carry analytical prose that intentionally goes
beyond what any single primary source attests. Token-match drift on
those surfaces would force investigations into source-vocabulary-only
prose and defeat the layer. The ``investigation_hypothesis_citation``
check enforces non-empty Sources rollups in lieu of token-match drift
on those surfaces.

Per-entry fields pool against the top-level union (∪ primary_sources)
rather than each entry's own ``source.path``. Synthesis-content notes
legitimately draw vocabulary from cross-source synthesis (a voucher's
claim referenced across multiple attestation venues; a contract
described from both the contract itself and external reporting);
per-entry pooling would over-fire on that legitimate case. The union
pool still surfaces fabrication — vocabulary attested by NO cited
source still produces unmatched tokens.
"""

from checks import Issue
from checks._research_utils import entries
from lib._common import extract_significant_tokens, load_source_tokens


CHECK_NAME = "prose_drift"


# Per-type drift scope is declared in ``meta/schema.yaml`` as each
# content type's ``prose_drift_fields:`` block:
#
#   prose_drift_fields:
#     top_level: [field_name, ...]       # synthesis prose fields on the artifact root
#     per_entry:                          # synthesis prose inside list entries
#       - [list_key, field_name_in_entry]
#
# Finding ``description`` is in scope because finding synthesis prose is
# anchored to the convergent multi-source pool — the description
# explains the pattern visible across those sources and should use
# their vocabulary.
#
# Investigation has NO ``prose_drift_fields`` block in schema by design.
# Investigations are speculation-tolerant: description /
# hypothesis_evaluation.text / hypothesis_evaluation.status /
# best_current_answer.text / counter_evidence.text /
# open_questions.question / closure_path entries / resolution_history
# entries all carry contributor analytical prose that goes beyond what
# any single source attests. The investigation_hypothesis_citation
# check enforces source-rollup discipline in lieu of token-match drift.
# Adding prose_drift_fields to investigation's schema block would
# mis-fire against the design and force investigations to use only
# source-vocabulary, which defeats the speculation-tolerant layer.


def _drift_scope(schema, target_type):
    """Return (top_level_fields, per_entry_fields) for the target type,
    read from schema's per-type ``prose_drift_fields`` block. Returns
    ([], []) when the type opts out (no block declared) — e.g.,
    investigation. ``per_entry_fields`` is a list of (list_key,
    entry_field) tuples; the schema stores them as 2-element lists,
    coerced to tuples here for stable downstream unpacking.
    """
    type_spec = schema.get("types", {}).get(target_type) or {}
    block = type_spec.get("prose_drift_fields") or {}
    top_level = list(block.get("top_level") or [])
    per_entry = [
        (pair[0], pair[1])
        for pair in (block.get("per_entry") or [])
        if isinstance(pair, (list, tuple)) and len(pair) == 2
    ]
    return top_level, per_entry


def _judge_drift(rel, location, prose_tokens, unmatched):
    """Impartial drift reporter. Warns on every unmatched significant
    token; errors only when 100% of the field's significant tokens are
    absent from source (complete vocabulary divergence — mathematical,
    not stylistic). Below 100%, no classification — contributor reviews.
    """
    if not unmatched:
        return
    full_tokens = sorted(unmatched)
    preview = ", ".join(full_tokens[:8])
    if len(unmatched) > 8:
        preview += f", … (+{len(unmatched) - 8} more — pass --verbose for full list)"
    if prose_tokens and len(unmatched) == len(prose_tokens):
        yield Issue(
            rel, "error",
            f"{location}: 100% of significant tokens "
            f"({len(unmatched)}/{len(prose_tokens)}) absent from source "
            f"— prose has no shared vocabulary with the source it claims "
            f"to draw on. Unmatched: {preview}",
            check_name=CHECK_NAME,
            tokens=full_tokens,
        )
    else:
        yield Issue(
            rel, "warn",
            f"{location}: {len(unmatched)} significant token(s) not in "
            f"source (prose-drift check — contributor review): {preview}",
            check_name=CHECK_NAME,
            tokens=full_tokens,
        )


def check(ctx):
    target_type = ctx.target_type
    top_fields, entry_fields = _drift_scope(ctx.schema, target_type)
    if not top_fields and not entry_fields:
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

    for field in top_fields:
        prose = ctx.data.get(field) or ""
        prose_tokens = extract_significant_tokens(prose)
        if not prose_tokens:
            continue
        unmatched = prose_tokens - top_level_pool
        yield from _judge_drift(ctx.rel, field, prose_tokens, unmatched)

    for list_key, entry_field in entry_fields:
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
