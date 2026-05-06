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
``media_versioning.note``, ``vouching_chain.attestation``). Applied
across all renderer-supported types. See ``meta/conventions.md``
"Prose-drift discipline on synthesis surfaces" for the principle of
record before proposing any field-specific threshold tuning.

OUT of scope: compact label cells (role titles, short relationship
descriptors, ``timeline[].event``, ``use_status``, ``activity``,
``contracts.subject``, ``publication_record.beat``) and cross-reference
descriptor notes (``corroboration_items.note``,
``witnesses_testimony.note``, ``org_relationships.note``,
``location_relationships.note``). Token-match misfires on label cells
and meta-descriptors; fabrication in those cells is semantic-review
territory.

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


# Top-level prose fields by target type. Pooled against the union of
# all primary_sources[].path token pools.
PROSE_FIELDS_BY_TYPE = {
    "person": ["background", "top_relevance", "credibility_notes"],
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
        ("top_scope_activity", "note"),
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
