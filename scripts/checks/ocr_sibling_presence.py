"""ocr-sibling-presence check — ResearchContext check (every artifact
type).

The seam this closes. The ``/build`` 4b gate produces + verifies a
clean-text ``.txt`` sibling for an ``ocr-scan`` / ``extraction-lossy``
PDF before any quote derives from it, and ``ocr-consensus.py
--stamp-artifact`` lands the ``content_block`` value on the artifact's
``primary_sources[]`` entry at the same moment. But the gate runs only
inside an orchestration: an artifact built before the gate existed — or
a fresh build that *reuses* an already-verified sibling and so never
runs the consensus tool — reaches the commit boundary with no mechanical
backstop. This check is that backstop, the 4b twin of
``transcript_sibling_presence`` (the 4c gate's backstop).

Two findings, one invariant (a sibling-backed source is fully prepped):

  - **Sibling owed** — the manifest flags the PDF ``ocr-scan`` /
    ``extraction-lossy`` but no same-stem ``.txt`` sibling exists on
    disk. Quotes citing this source derive from a corrupt text layer;
    the fix is ``/prepare-ocr-sibling``.
  - **Entry unstamped** — the sibling exists but the artifact's entry
    carries no ``content_block``. The node renders without its
    ``Content Block`` row; the fix is
    ``ocr-consensus.py verify {pdf} --stamp-artifact {yaml}`` (seconds
    on the engine cache; never hand-typed).

Scope: PDF sources only. ``content_block`` is a page-image concept
(which pages the VLM read was content-filter-blocked on, schema
``primary_sources_entry``). No lossy-flagged non-PDF source exists in
the manifest today; if one ever appears, decide its sibling story
before extending this check rather than half-checking it.

Phase: extract — sibling presence is a precondition of verbatim quote
derivation. It fires once the artifact exists with its source set,
after the ``/build`` 4b gate has had its chance to produce the sibling;
the archive phase would fire at scaffold time, before 4b runs.

Severity: error — the documented end state, reached once the legacy
backfill completed: every quoted ocr-scan / extraction-lossy PDF in the
corpus carries a verified sibling and a stamped ``content_block``. A
missing sibling or stamp is definitionally a defect (quotes deriving
from a corrupt text layer, or production facts unrecorded), and the fix
is mechanical (``/prepare-ocr-sibling``; ``verify --stamp-artifact``),
so nothing legitimate is blocked.
"""

from checks import Issue
from lib._common import SOURCES_DIR, iter_artifacts


CHECK_NAME = "ocr_sibling_presence"

_LOSSY = frozenset({"ocr-scan", "extraction-lossy"})


def check(ctx):
    sources = ctx.data.get("primary_sources") or []
    if not isinstance(sources, list) or not sources:
        return

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
            continue  # content_block is a page-image concept; no lossy
            # non-PDF source exists today — decide its sibling story before
            # extending this check
        if artifact.get("extraction_type") not in _LOSSY:
            continue

        sibling = (SOURCES_DIR / path).with_suffix(".txt")
        if not sibling.exists():
            yield Issue(
                ctx.rel, "error",
                f"primary_sources[{i}]: source {path!r} is "
                f"extraction_type: {artifact.get('extraction_type')} with no "
                f"verified .txt sibling on disk — quotes citing it derive "
                f"from a corrupt text layer. Produce + confirm + register a "
                f"sibling via /prepare-ocr-sibling",
                check_name=CHECK_NAME,
            )
        elif "content_block" not in src:
            yield Issue(
                ctx.rel, "error",
                f"primary_sources[{i}]: source {path!r} has a verified "
                f"sibling but the entry carries no content_block — the node "
                f"renders without its Content Block row. Stamp it "
                f"mechanically: ocr-consensus.py verify {path} "
                f"--stamp-artifact {ctx.rel} (seconds on the engine cache; "
                f"never hand-typed)",
                check_name=CHECK_NAME,
            )
