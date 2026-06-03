"""quote-source-grounding check — per-artifact ResearchContext check.

The per-quote "final independent check" against the primary source, made
mechanical and re-runnable. For every quote whose ``source.path`` points at an
OCR-scan / extraction-lossy PDF, this check binds the quote to a FINALIZED,
hash-matching OCR-consensus verification record (see
``meta/schema-ocr-verification.yaml``).

Why this is the per-quote source check, structurally:

  - ``verbatim_quotes`` already confirms the quote text appears in the `.txt`
    sibling. But the sibling is a transcription — it can itself diverge from the
    page images (that is exactly how DIRD-16's `ITT` / `cammunication` reached a
    committed node: the quote matched a *wrong* sibling).
  - The OCR-consensus pipeline makes the sibling trustworthy: every token is
    either CONSENSUS (≥2 of 3 uncorrelated engine votes agree — independent
    source verification) or ADJUDICATED against the page image (recorded). A
    FINALIZED record certifies that.
  - Therefore, if a quote's sibling has a FINALIZED record AND the sibling bytes
    still hash to what was verified, every token the quote draws is
    independently source-grounded by construction. The sha256 binding is the
    load-bearing per-quote guarantee the source-layer validator can't give: it
    catches a sibling edited *after* verification (which ``verbatim_quotes``
    would happily still match).

Failure modes surfaced (one diagnostic per cited OCR-scan source per artifact):
  - no verification record exists → sibling fidelity unverified;
  - record not finalized (``sibling_sha256`` unset) → run ``assemble``;
  - unresolved contested spans → sibling not yet trustworthy;
  - sibling sha256 ≠ recorded → sibling edited since verification.

Transition: ``SEVERITY = "warn"`` until the OCR-consensus backfill has produced
a record for every existing OCR-scan sibling; flipped to ``"error"`` and wired
into ``validate-research.py::_ARTIFACT_CHECKS`` at the gate-flip step (see the
OCR-consensus plan). Non-OCR-scan sources are skipped entirely, so text-native
sources are unaffected.
"""

import hashlib

import yaml

from checks import Issue
from checks._research_utils import entries
from lib._common import SOURCES_DIR, _load_extraction_types

CHECK_NAME = "quote_source_grounding"

# Transition severity. Flip to "error" when wiring into _ARTIFACT_CHECKS after
# the backfill (every OCR-scan sibling carries a finalized record by then).
SEVERITY = "warn"

_OCR_TYPES = {"ocr-scan", "extraction-lossy"}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check(ctx):
    """Yield Issues for quotes citing an OCR-scan source without a finalized,
    hash-matching consensus verification record. Deduplicated per cited source
    path (one diagnostic per source per artifact — many quotes share one
    source)."""
    quotes = list(entries(ctx.data, "quotes"))
    if not quotes:
        return
    ext_types = _load_extraction_types()
    seen = set()
    for q in quotes:
        if not isinstance(q, dict):
            continue
        src = q.get("source")
        if not isinstance(src, dict):
            continue
        rel = src.get("path")
        if not rel or ext_types.get(rel) not in _OCR_TYPES:
            continue  # text-native (or unflagged) sources are out of scope
        if rel in seen:
            continue
        seen.add(rel)

        src_path = SOURCES_DIR / rel
        sibling = src_path.with_suffix(".txt")
        stem = src_path.with_suffix("").name
        verification = src_path.parent / f"{stem}-ocr-verification.yaml"

        if not verification.exists():
            yield Issue(
                ctx.rel, SEVERITY,
                f"quote(s) cite OCR-scan source sources/{rel}, but no "
                f"OCR-consensus verification record exists "
                f"({verification.name}); the sibling's fidelity to the page "
                f"images is unverified — run /prepare-ocr-sibling "
                f"(ocr-consensus.py).",
                check_name=CHECK_NAME,
            )
            continue
        try:
            rec = yaml.safe_load(verification.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            yield Issue(
                ctx.rel, SEVERITY,
                f"verification record {verification.name} for sources/{rel} "
                f"is unreadable: {e}",
                check_name=CHECK_NAME,
            )
            continue
        if not isinstance(rec, dict):
            yield Issue(
                ctx.rel, SEVERITY,
                f"verification record {verification.name} for sources/{rel} "
                f"is not a mapping",
                check_name=CHECK_NAME,
            )
            continue

        recorded = rec.get("sibling_sha256")
        if not recorded:
            yield Issue(
                ctx.rel, SEVERITY,
                f"verification record for sources/{rel} is not finalized "
                f"(sibling_sha256 unset) — run `ocr-consensus.py assemble`.",
                check_name=CHECK_NAME,
            )
            continue

        unresolved = [
            c.get("id") for c in (rec.get("contested") or [])
            if isinstance(c, dict)
            and (c.get("status") != "adjudicated" or not c.get("resolution"))
        ]
        if unresolved:
            yield Issue(
                ctx.rel, SEVERITY,
                f"verification record for sources/{rel} has unresolved "
                f"contested spans {unresolved}; the sibling is not yet "
                f"trustworthy. Adjudicate + `assemble`.",
                check_name=CHECK_NAME,
            )
            continue

        if not sibling.exists():
            yield Issue(
                ctx.rel, SEVERITY,
                f"verification record exists but the sibling "
                f"sources/{sibling.relative_to(SOURCES_DIR)} is missing.",
                check_name=CHECK_NAME,
            )
            continue
        if _sha256(sibling) != recorded:
            yield Issue(
                ctx.rel, SEVERITY,
                f"sibling sources/{sibling.relative_to(SOURCES_DIR)} has been "
                f"edited since verification (sha256 ≠ recorded) — quotes match "
                f"an unverified sibling. Re-verify via ocr-consensus.py.",
                check_name=CHECK_NAME,
            )
            continue
        # grounded: finalized record + hash match → every quote token is
        # consensus-or-image-adjudicated. No issue.
