"""quote-ocr-corroboration check — ResearchContext check (every artifact
type).

The seam this closes. For a sibling-backed (``ocr-scan`` /
``extraction-lossy``) PDF, the verbatim-quote check guarantees
quote-text ↔ sibling fidelity, but sibling ↔ page-image fidelity rests
on the perception steps of sibling prep — and nothing at the commit
boundary verified that the quoted spans specifically were ever held up
against the OCR engines after extraction. ``ocr-consensus.py
corroborate-quotes`` performs that pass (every load-bearing quoted
token corroborated by an OCR engine; contested tokens and
PaddleOCR-filled-page quotes enumerated as the audit target list) and
stamps its canonical result onto the entry as ``quote_corroboration``.
This check is the stamp's commit-boundary backstop, the quote-level
sibling of ``ocr_sibling_presence``.

Three findings, one invariant (a quoted sibling-backed source carries a
fresh corroboration stamp):

  - **Stamp owed** — quotes cite the source but the entry carries no
    ``quote_corroboration``. The fix is ``ocr-consensus.py
    corroborate-quotes {pdf} --artifact {yaml}`` (seconds on the engine
    cache; never hand-typed). Requires ``content_block`` stamped first.
  - **Sibling drifted** — the sibling's bytes no longer match the hash
    recorded in the stamp (the sibling was edited after corroboration),
    so the stamped verdict no longer describes the text the quotes
    match against. Re-run corroborate-quotes.
  - **Quote set drifted** — the number of quotes citing the source no
    longer matches the stamped count (quotes were added or removed
    after corroboration). Re-run corroborate-quotes.

The stamp's machine anchors (quote count / contested count /
``sha256:`` hash) are written only by ``format_quote_corroboration`` in
``ocr-consensus.py``; this check keys off two of them — the quote count
and the ``sha256:`` hash — so a value missing those was hand-typed and
is flagged as such. Engines never run here: the heavy perception work
happened at corroborate-quotes time; the commit boundary only reads the
stamp, exactly as ``ocr_sibling_presence`` reads ``content_block``.

What this check cannot see — stated so nobody reads more into a green
stamp than it carries: a correlated misread shared by the VLM and both
OCR engines passes corroboration silently; only the audit-phase
page-image read covers that. The stamp's contested/filled lists are
that read's target list.

Scope: PDF sources only, same boundary as ``ocr_sibling_presence``
(``content_block`` / page-image concepts don't apply to non-PDF
formats; no lossy-flagged non-PDF source exists in the manifest today). Fires only when the sibling exists
(``ocr_sibling_presence`` owns the missing-sibling finding) and at
least one quote cites the source (an unquoted source owes nothing).

Phase: extract — corroboration is a property of the extracted quote
set, so it fires once quotes exist, after the ``/build`` 4b gate and
the worker have run.

Severity: error — the documented end state, reached once the legacy
backfill completed: every quoted ocr-scan / extraction-lossy PDF in the
corpus carries a fresh ``quote_corroboration`` stamp with its contested
tokens page-image-settled. An uncorroborated quoted span is
definitionally unfinished prep, and the fix is mechanical
(``corroborate-quotes`` on the engine cache), so nothing legitimate is
blocked.
"""

import hashlib
import re

from checks import Issue
from checks._research_utils import entries
from lib._common import SOURCES_DIR, iter_artifacts


CHECK_NAME = "quote_ocr_corroboration"

_LOSSY = frozenset({"ocr-scan", "extraction-lossy"})

_SHA_RE = re.compile(r"sha256:([0-9a-f]{6,})")
_COUNT_RE = re.compile(r"(\d+) quote\(s\) corroborated")


def check(ctx):
    sources = ctx.data.get("primary_sources") or []
    if not isinstance(sources, list) or not sources:
        return

    cited = {}
    for q in entries(ctx.data, "quotes"):
        if not isinstance(q, dict):
            continue
        src = q.get("source")
        path = src.get("path") if isinstance(src, dict) else None
        if path:
            cited[path] = cited.get(path, 0) + 1

    path_to_artifact = {
        artifact.get("path"): artifact
        for _, artifact in iter_artifacts(ctx.manifest_entries)
    }

    for i, src in enumerate(sources):
        if not isinstance(src, dict):
            continue
        path = src.get("path")
        artifact = path_to_artifact.get(path)
        if artifact is None:
            continue  # unregistered path is primary_sources' finding
        if artifact.get("format") != "pdf":
            continue  # same non-PDF boundary as ocr_sibling_presence
        if artifact.get("extraction_type") not in _LOSSY:
            continue
        sibling = (SOURCES_DIR / path).with_suffix(".txt")
        if not sibling.exists():
            continue  # ocr_sibling_presence owns the missing-sibling finding
        n_cited = cited.get(path, 0)
        if n_cited == 0:
            continue  # an unquoted source owes no corroboration

        val = src.get("quote_corroboration")
        if not val or not isinstance(val, str):
            yield Issue(
                ctx.rel, "error",
                f"primary_sources[{i}]: {n_cited} quote(s) cite {path!r} "
                f"(extraction_type: {artifact.get('extraction_type')}) but the "
                f"entry carries no quote_corroboration — the quoted spans were "
                f"never held up against the OCR engines after extraction. Stamp "
                f"it mechanically: ocr-consensus.py corroborate-quotes {path} "
                f"--artifact {ctx.rel} (seconds on the engine cache; never "
                f"hand-typed)",
                check_name=CHECK_NAME,
            )
            continue

        sha_m = _SHA_RE.search(val)
        count_m = _COUNT_RE.search(val)
        if not sha_m or not count_m:
            yield Issue(
                ctx.rel, "error",
                f"primary_sources[{i}]: quote_corroboration on {path!r} lacks "
                f"the canonical anchors (quote count / sha256) — only "
                f"ocr-consensus.py corroborate-quotes writes this value; "
                f"re-stamp it mechanically",
                check_name=CHECK_NAME,
            )
            continue
        recorded_sha = sha_m.group(1)
        actual_sha = hashlib.sha256(sibling.read_bytes()).hexdigest()
        if not actual_sha.startswith(recorded_sha):
            yield Issue(
                ctx.rel, "error",
                f"primary_sources[{i}]: the sibling for {path!r} was edited "
                f"after its quotes were corroborated (sha256:{recorded_sha} "
                f"recorded, sibling now {actual_sha[:12]}) — the stamped "
                f"verdict is stale. Re-run: ocr-consensus.py "
                f"corroborate-quotes {path} --artifact {ctx.rel}",
                check_name=CHECK_NAME,
            )
            continue
        recorded_count = int(count_m.group(1))
        if recorded_count != n_cited:
            yield Issue(
                ctx.rel, "error",
                f"primary_sources[{i}]: {n_cited} quote(s) now cite {path!r} "
                f"but quote_corroboration recorded {recorded_count} — quotes "
                f"were added or removed after corroboration. Re-run: "
                f"ocr-consensus.py corroborate-quotes {path} --artifact "
                f"{ctx.rel}",
                check_name=CHECK_NAME,
            )
