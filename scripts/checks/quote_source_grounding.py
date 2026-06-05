"""quote-source-grounding check — per-artifact ResearchContext check.

The per-quote "final independent check" against the primary source, made
mechanical and re-runnable — **quote-scoped** (BACKLOG C1). For every quote AND
cited_work whose ``source.path`` points at an OCR-scan / extraction-lossy PDF,
this binds the load-bearing span to a ``{stem}-quote-grounding.yaml`` record
produced by ``scripts/tools/ocr-consensus.py ground`` (spec:
``meta/schema-quote-grounding.yaml``).

Why quote-scoped (and not whole-document):

  - ``verbatim_quotes`` already confirms the quote text appears in the `.txt`
    sibling. But the sibling is a transcription — it can itself diverge from the
    page images (that is exactly how DIRD-16's `ITT` / `cammunication` reached a
    committed node: the quote matched a *wrong* sibling).
  - Whole-document token-by-token consensus on a banner/figure-heavy government
    PDF produces ~1000 CONTESTED spans, ~99% of them non-prose furniture (running
    classification banners, figure interiors, TOC dot-leaders) that no quote ever
    draws from. The DIRD-16 pilot: 1067 contested, **0 of them inside any of the
    21 node quotes**. That noise is un-adjudicatable and not load-bearing.
  - The guarantee that matters is per-LOAD-BEARING-SPAN: the sibling is the
    authoritative grab (ideally a VLM page read — a modality uncorrelated with
    OCR); Tesseract + PaddleOCR confirm ONLY the WORDS and NUMBERS of the spans
    the node quotes/cites (structure is not compared). Each load-bearing contested
    token is resolved by an automated arbiter (majority, then trust precedence
    VLM > PaddleOCR > Tesseract) — no human step. cited_works are in scope — they
    are load-bearing verbatim citations and inherited the same OCR garble (DIRD-16
    cw2/cw5/.../cw24).

Failure modes surfaced:
  - no grounding record for a cited OCR-scan source → run ``ground``;
  - record not finalized for the sibling (``sibling_sha256`` != sibling bytes)
    → the sibling changed since grounding; re-run ``ground``;
  - the quote/cited_work is absent from the record, or was not located in the
    sibling → re-run ``ground`` / re-check the citation;
  - an OCR-override token (resolution != grab): two engines agree the grab misread
    a word/number → correct the quote to the OCR reading, then re-run ``ground``.

Transition: ``SEVERITY = "warn"`` until every OCR-scan sibling that a node quotes
has a grounding record (the build→backfill→gate discipline); flipped to
``"error"`` and wired into ``validate-research.py::_ARTIFACT_CHECKS`` at the
gate-flip step. Non-OCR-scan sources are skipped entirely.
"""

import hashlib
from pathlib import Path

import yaml

from checks import Issue
from checks._research_utils import entries
from lib._common import SOURCES_DIR, _load_extraction_types

CHECK_NAME = "quote_source_grounding"

# Transition severity. Flip to "error" when wiring into _ARTIFACT_CHECKS after
# every node's OCR-scan quotes carry a grounding record.
SEVERITY = "warn"

_OCR_TYPES = {"ocr-scan", "extraction-lossy"}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_record(rel):
    """Load + validate the grounding record for an OCR-scan source path.

    Returns ``(spans_by_ref, source_error)`` — exactly one is non-empty.
    ``source_error`` is a single per-source diagnostic string (missing /
    unreadable / stale record); when set, the source's spans are not checked
    individually."""
    src_path = SOURCES_DIR / rel
    sibling = src_path.with_suffix(".txt")
    stem = src_path.with_suffix("").name
    record_path = src_path.parent / f"{stem}-quote-grounding.yaml"

    if not record_path.exists():
        return None, (
            f"quote(s)/cited_work(s) cite OCR-scan source sources/{rel}, but no "
            f"quote-grounding record exists ({record_path.name}); the spans the "
            f"node draws are not confirmed against the page images — run "
            f"`ocr-consensus.py ground` on the artifact.")
    try:
        rec = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        return None, f"quote-grounding record {record_path.name} for sources/{rel} is unreadable: {e}"
    if not isinstance(rec, dict):
        return None, f"quote-grounding record {record_path.name} for sources/{rel} is not a mapping"
    if rec.get("schema") != "quote-grounding/v2":
        return None, (f"quote-grounding record {record_path.name} for sources/{rel} "
                      f"has unexpected schema {rec.get('schema')!r} (want "
                      f"'quote-grounding/v2') — regenerate with `ocr-consensus.py ground`.")

    recorded = rec.get("sibling_sha256")
    if not recorded:
        return None, (f"quote-grounding record for sources/{rel} is not finalized "
                      f"(sibling_sha256 unset) — re-run `ocr-consensus.py ground`.")
    if not sibling.exists():
        return None, (f"quote-grounding record exists but the sibling "
                      f"sources/{sibling.relative_to(SOURCES_DIR)} is missing.")
    if _sha256(sibling) != recorded:
        return None, (f"sibling sources/{sibling.relative_to(SOURCES_DIR)} has changed "
                      f"since grounding (sha256 != recorded) — the confirmed spans no "
                      f"longer match the sibling; re-run `ocr-consensus.py ground`.")

    # Namespaced by (node, ref): one record aggregates every node citing this
    # source, and two nodes' identically-numbered ids (both "q4") are distinct
    # keys — so a node's quote can never be silently confirmed against a
    # different node's span.
    spans_by_key = {(gs.get("node"), gs.get("ref")): gs
                    for gs in (rec.get("grounded_spans") or [])
                    if isinstance(gs, dict)}
    return spans_by_key, None


def check(ctx):
    """Yield Issues for quotes / cited_works citing an OCR-scan source whose
    load-bearing span is not grounded (every word/number confirmed by an OCR
    engine or auto-arbitrated) in a hash-matching quote-grounding record."""
    items = []
    for q in entries(ctx.data, "quotes"):
        if isinstance(q, dict):
            items.append((q, "quote"))
    for cw in entries(ctx.data, "cited_works"):
        if isinstance(cw, dict):
            items.append((cw, "cited_work"))
    if not items:
        return

    ext_types = _load_extraction_types()
    cache = {}        # rel -> (spans_by_key, source_error)
    reported_source = set()
    # This artifact's node slug — the namespace its spans live under in the
    # per-source record (matches ocr-consensus.py's `artifact.stem`).
    node_slug = Path(str(ctx.rel)).stem

    for obj, kind in items:
        src = obj.get("source")
        if not isinstance(src, dict):
            continue
        rel = src.get("path")
        if not rel or ext_types.get(rel) not in _OCR_TYPES:
            continue  # text-native (or unflagged) sources are out of scope

        if rel not in cache:
            cache[rel] = _load_record(rel)
        spans_by_key, source_error = cache[rel]
        if source_error:
            if rel not in reported_source:    # one per source
                reported_source.add(rel)
                yield Issue(ctx.rel, SEVERITY, source_error, check_name=CHECK_NAME)
            continue

        ref = obj.get("id")
        gs = spans_by_key.get((node_slug, ref))
        if gs is None:
            yield Issue(
                ctx.rel, SEVERITY,
                f"{kind} {ref!r} cites OCR-scan source sources/{rel} but is not "
                f"grounded for node {node_slug!r} in the quote-grounding record — "
                f"re-run `ocr-consensus.py ground` on this artifact.",
                check_name=CHECK_NAME)
            continue
        if not gs.get("located"):
            yield Issue(
                ctx.rel, SEVERITY,
                f"{kind} {ref!r}: verbatim text was not located in the sibling "
                f"during grounding ({gs.get('note', '')}) — re-check the "
                f"quote/citation, then re-run `ocr-consensus.py ground`.",
                check_name=CHECK_NAME)
            continue
        for c in (gs.get("contested") or []):
            res = c.get("resolution")
            sib = c.get("sibling")
            line = c.get("line")
            if res in (None, ""):
                # The arbiter always fills a resolution; a null here means a
                # stale/hand-edited record. Safety-net warn.
                yield Issue(
                    ctx.rel, SEVERITY,
                    f"{kind} {ref!r}: load-bearing token at sibling line {line} "
                    f"({sib!r}) has no arbiter resolution — re-run "
                    f"`ocr-consensus.py ground`.",
                    check_name=CHECK_NAME)
            elif res != sib:
                # OCR-override: two uncorrelated engines agree the grab misread a
                # word/number. The quote still shows the grab's reading — correct it.
                yield Issue(
                    ctx.rel, SEVERITY,
                    f"{kind} {ref!r}: two OCR engines override the grab at line "
                    f"{line} (grab={sib!r}, OCR={res!r}) — the grab misread a "
                    f"word/number; correct the quote/citation to {res!r}, then "
                    f"re-run `ocr-consensus.py ground`.",
                    check_name=CHECK_NAME)
        # else: every load-bearing token confirmed, disclosed, or override-clean
        # (resolution == grab) → grounded.
