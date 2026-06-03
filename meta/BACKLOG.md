---
id: meta/BACKLOG
type: meta
---

# BACKLOG

Deferred work items — real, concrete, and would be lost otherwise. Not
on the active roadmap. Items leave when (a) promoted to a roadmap phase,
(b) addressed, or (c) superseded.

Open items are partitioned into three sections by dependency shape:
**A — Priority sequence** (ordering / coupling constraints),
**B — Parallel batch** (renderer-pass items that ship together),
and **C — Anytime** (no upstream blockers). Item identifiers within
each section (A1, A2, …, B1, …, C1, C2, …) are positional working
labels, not stable identifiers. A closed item's block is deleted in
full — no marker, no placeholder. A new entry takes the lowest section
number not currently in use, so **numbers recycle**; once a section,
and ultimately the whole BACKLOG, is cleared, numbering restarts from 1.
Because an ID is transient and reused, never reference it from outside
this file — not in code, docs, prompts, commit messages, or `git log`
searches. Describe the work; the commit diff + message are the record.
See `meta/conventions.md` "BACKLOG lifecycle discipline".

**Default focus: Section C.** C items have no upstream dependencies
and can be picked up and finished in a single pass. A and B items
carry ordering or coupling constraints — starting one without its
dependencies risks half-baked implementations and leaves the BACKLOG
cluttered with partial work. For ad-hoc sessions, prefer C work.
Reserve A and B for sessions explicitly scoped to those tracks.

Items waiting on an external event the repo can't drive (FOIA
resolution, registry access, third-party publication) and that are
**topic-specific** to the current investigation live in
`meta/topic/research-queue.md` "Externally blocked" — that's the fork-
boundary-correct home for them. If a genuinely toolkit-neutral
externally-blocked item ever surfaces (rare), reinstate the
"Externally blocked" heading at the bottom of this file.

Cross-references between entries use `**Blocks:**` / `**Blocked by:**`
lines so the dependency graph is visible inline.

---

## A. Priority sequence

Items with ordering or coupling constraints.

### A1 — Exercise the pipeline paths the first whole run didn't hit

The six-role pipeline (`prompts/topology.md`) has been run *whole* on one
real node build — a user-directed, all-internal institutional-actor build:
Internal Investigator → Worker (×N) → Build → Audit, with handoff stubs
captured and friction tightened in place. The **External Investigator
(role 2) and Archive (role 3)** roles have since been exercised standalone on
an existing node — a source-recovery that re-pulled a dead JavaScript-shell
capture from a Wayback snapshot (External Investigator confirmed the snapshot
and captured verbatim spans; Archive re-pulled the file and refreshed the
manifest). Both behaved per contract. Paths still unverified end-to-end:

- **role 2 + role 3 integrated inside a full `/build`** with a genuine
  external-source gap — so far they have run standalone, not as the
  external-gap branch of a fresh orchestration.
- the **`foia` worker kind** — `caption` is now exercised (the all-internal
  `jre-2194-elizondo-2024` transcript build hit it end-to-end: internal-survey →
  caption worker → builder → audit). `pdf` + `html` + `caption` done; only `foia`
  remains, and no load-bearing *unarchived* FOIA source currently exists to build
  (every referenced FOIA doc is already archived) — wait for a genuine FOIA gap
  rather than manufacturing one.
- **error routing** (`route_failure.py`) — no validator failure has needed
  routing on a clean run (the caption build was clean; its audit findings were
  applied via builder re-entry, not a routed check failure).

Drive a build that forces these paths (a target with an external-source
gap + a caption/FOIA source); confirm each `--phase X` fires exactly the
checks reading role X's state; tighten friction in place where cheap, file a
new entry where not.

**Deferred follow-on:** split `prose_drift` into `prose_drift_toplevel`
(organize phase) + `prose_drift_notes` (link phase) only if one-phase-late
surfacing of top-level prose drift proves annoying.

**Blocks:** none.
**Blocked by:** a user-directed build with an external-source gap.

### A3 — DIRD extraction: re-level the corpus against the rubric + extract remaining citations

The DIRD extraction standard now exists — the passage-selection rubric in
`meta/conventions.md` "Document-corpus extraction — the DIRD passage rubric"
(provenance / thesis-and-scope / each section's finding / methods / conclusions /
acknowledgements / references), under the "Comparability standard". The
`cited_works` dimension is modeled (`schema-research-artifact.yaml`
`cited_work_entry`; required-but-emptyable on every document), rendered
(`## References` in `renderers/document.py`), source-fidelity-gated
(`scripts/checks/cited_works.py`), and proven on dird-24 (113 references
extracted, references region image-verified). Remaining work:

**(a) Re-level DIRD density against the rubric.** Audit each built DIRD's quote
set against the rubric — the target is each major section's finding captured, NOT
a quote-count (`### Density is source-driven`). **dird-24 DONE** (2026-05-24,
9 → 19 quotes): captured §II Cole-Puthoff thermodynamics / Forward's
no-continuous-extraction limit / "no practicable technique demonstrated", §III
QED + SED origin of the ZPF, §IV Koch et al. corroboration, the §V/Summary
ZPF-modes-placeholder + new-boundary-conditions findings, and §VI SED-inadequate
/ QED-vacuum-degradable conclusions; quotes renumbered to document order; the
equation/superscript energy-density passages intentionally left unquoted. Each
re-level requires image-verifying the relevant OCR-sibling body regions against
the PDF first (the built DIRDs verified only their already-quoted regions — see
the dird-24 sibling note for the precedent). Use `coverage-suggest.py` + the
rubric. Remaining: dird-04 (55) and dird-05 (50) — the density outliers —
audited for whether each quote is a distinct subsection finding (likely over the
bar, not under); dird-01/02/03/06/07/15/18/26 audited for any skipped section
findings (dird-05/06/07/18 were built after this item was opened and are not yet
rubric-audited). Re-level the set for consistency.

| DIRD | pages | quotes | quotes/page |
|---|---|---|---|
| dird-06 space-access | 57 | 16 | 0.28 |
| dird-24 quantum-vacuum-energy-extraction (re-leveled) | 58 | 19 | 0.33 |
| dird-26 field-effects | 39 | 21 | 0.54 |
| dird-01 metallic-glasses | 31 | 17 | 0.55 |
| dird-07 invisibility-cloaking | 30 | 17 | 0.57 |
| dird-03 pulsed-hpm | 38 | 23 | 0.61 |
| dird-15 advanced-space-propulsion | 17 | 13 | 0.76 |
| dird-02 programmable-matter | 21 | 17 | 0.81 |
| dird-18 traversable-wormholes | 42 | 43 | 1.02 |
| dird-04 biomaterials | 33 | 55 | 1.67 |
| dird-05 aerospace-platforms-materials | 28 | 50 | 1.79 |

**(b) Extract `cited_works` — all 14 BUILT DIRDs are DONE.** Each built DIRD's
reference list is extracted and source-fidelity-gated, with the citation marker
style preserved per source (`[N]` brackets, `(N)` parenthetical, `^N` endnotes,
`N.` numbered list, dird-09's `N.N` dotted chapter.ref, and dird-26's sub-lettered
`[5-a/b/c]` UFO-relevant entries — Schuessler, Sturrock, Vallee, Cash-Landrum).
dird-03 (Pulsed HPM) and dird-04 (Biomaterials) were assessed and **carry no
formal reference list** (end at Conclusion / Summary; sibling marker-scan = 0;
PDF last page confirmed) — their `cited_works: []` is correct, not missing.
Remaining: the UNBUILT DIRDs (11/12/13/14/16/17/19 through 37 — 23 archived, none
built) get their citations when each is built — same per-DIRD flow (locate region
→ image-verify sibling vs PDF → worker extract → integrate). (dird-08/09
cited_works were extracted at build time; **dird-10** was built in a later session
and shipped with `cited_works: []` — the omission was caught only on review, which
prompted the `cited_works_uncaptured` enforcement gate, and its 97 references were
then backfilled — see C6.) The recurring-author network is the payoff (Puthoff
across dird-24 + dird-15; E. W. Davis / C. Maccone cross-DIRD; M. Tsoi within
dird-10).

*Illegible references (deferred — design on first real case).* dird-24's
references were all recoverable by image-verifying the PDF page. If a remaining
DIRD has a reference that is **visibly present but genuinely unreadable** (scan
too degraded to make out, not recoverable from the page), the current mechanism
has no answer (the `cited_works` verbatim check errors). At that point add: an
optional `cited_work_entry.legibility: illegible` flag → `cited_works.py` WARNS
instead of erroring (mirrors the binary-source warn path) and still verifies any
legible fragment provided; the renderer emits a standardized, searchable `[sic]`
label — `**[N]** *[illegible in source — p.N; preserved [sic], flagged for
re-OCR/re-verification]*` — greppable later via `legibility: illegible`
(artifacts) and `[illegible in source` (nodes). Capture the marker + legible
fragment; never fabricate the unreadable span, never skip the entry (skipping
loses the fact a reference exists at [N]).

**(c) DIRD page-ref convention — DONE (all 13 DIRDs) + ENFORCED.**

> **⚠ Superseded in part by the markerless strip-all pass.** The page-for-page
> mirroring claimed in this subsection — siblings carrying `----- PAGE BREAK
> -----` markers so *block count == `pdfinfo` page count* — was reversed by the
> strip-all uniformity pass (commits `fb31764` / `466a28c`), which stripped every
> synthetic page marker from the DIRD siblings that carried them. The siblings are
> now **markerless**, so no block-count↔`pdfinfo` correspondence exists. What
> still holds: the `p. N` = PDF-viewer-page *semantic* convention and its
> mechanical enforcement (`location_format`, `pdf_page_count`); for a
> sibling-backed source `p. N` is a verbatim-anchored navigation hint, and new
> builds (dird-11 / dird-12, via `/prepare-ocr-sibling`) use **descriptive content
> anchors** instead of `p. N`. The narrative below is retained as the record of
> the page-ref work — read it in that light.

Settled rule
(`meta/conventions.md` "`p. N` is the physical page"): `p. N` = the PDF viewer's
page N (the Nth physical page of the file), so a reader opening the source PDF
to page N lands on the quote. The OCR sibling therefore preserves **every**
physical page verbatim — including the third-party Black Vault distribution page
the PDFs carry at physical page 2 (preserved as-is, never summarized, never
dropped). All 13 built DIRD siblings now mirror their PDFs page-for-page (block
count == pdfinfo page count) and every quote / naming-quirk / cited-work ref is a
PDF-viewer page, verified against the corrected sibling: dird-01/03/04/05/07/18
had the dropped insert restored + refs shifted +1; dird-06 had the insert
restored + a merged front-matter page split + a piecewise shift; dird-02/26 had a
contributor *summary* of the insert replaced with the verbatim page, bespoke
`--- page N ---` markers normalized to `----- PAGE BREAK -----`, and refs
renumbered from the document's printed labels to PDF-viewer pages; dird-24 already
complied; dird-15 (non-Black-Vault) has no insert. (This superseded an earlier
omit-the-insert / physical-sheet attempt — counting the document's own pages and
dropping the insert made `p. N` source-dependent, the opposite of findable.)

*Later brought into compliance + enforced.* **dird-08/09** (built after this item
was first closed, and regressed to the document's printed page numbers) were
remapped to PDF-viewer pages (offset +6 / +8, derived from each PDF's clean OCR
folio sequence). The **cited_works (References) page refs on dird-01/07/15/24** were
still the document's printed folios — the body quotes had been converted but the
reference lists were missed — and were corrected to the PDF-viewer page where each
reference list physically sits (dird-01 refs p.24/25 → p.30/31; dird-07 → p.29/30;
dird-15 → p.17; dird-24 +7). The convention is now **mechanically enforced** so it
cannot regress: `location_format` errors on any roman (`p. ii`) or `printed p.`
location ref — and runs on OCR-scan sources too, where `quote_location_page` (which
skips sibling-backed sources) cannot reach; `pdf_page_count` errors when
`document_intrinsic.pages` ≠ the PDF's `pdfinfo` page count. The document renderer
also emits a one-line physical-page convention note on every multi-page PDF node.
(`pdfinfo` on the archived file is ground truth for the count — the external audit's
third-party page-listing numbers were all wrong.)

**(d) Image-verify each OCR sibling against the PDF page images — dird-08/09 DONE.**
For an OCR-scan DIRD the verbatim-quote check compares artifact ↔ `.txt` sibling
only; it is structurally blind both to (i) drift between the hand-made sibling and
the PDF, and (ii) page-citation errors (the `quote_location_page` check skips
sibling-backed sources). The only ground truth is the PDF page image.

**What the dird-08/09 pass found (reframes the concern).** The external audit's
verbatim-drift claims were **all false positives** — read against the page images,
every flagged span matched the node: dird-08 "globe-encircling UAV flight" (p.33,
not "turbojet"), "interactions with the walls" (p.34, not "on"), "Sänger" with the
umlaut throughout; dird-09 "Tokomak" consistently (no dual spelling), "...television,
as an approach" (comma, not semicolon), "Central Spot" + "(Figure 1.4). As verified"
(as the node has), "Robert Hirsh ... shown if Figure 2.1" genuinely printed thus. The
siblings are **faithful**; the auditor evidently read the garbled OCR text layer, not
the page images. The non-canonical source forms were already preserved verbatim and
mostly flagged (dird-09 nq4 Tokomak, nq5 Hirsh; added nq6 "shown if"→"shown in").

**The real defect is page-citation accuracy.** The page-ref convention pass (item (c))
converted printed→physical by a fixed offset, which faithfully carried **pre-existing
off-by-one errors** in the original citations — a quote/reference on a section's
*continuation* page had been cited at the section-start page. Only image/content
verification catches these. Fixed: **dird-08** 6 (commit ef400c1), **dird-09** 21
(16 quotes + 5 references; commit 6fdf357).

**Remaining: the other 11 built OCR DIRDs** (01/02/03/04/05/06/07/15/18/24/26). Each
needs the same per-DIRD image pass — primarily to catch the off-by-one page-citation
errors the offset conversion propagated (the method: a token-vote page resolver over
the PDF's `pdftotext` pages flags candidates, then confirm each against the page image
— references especially, where the resolver is unreliable because reference text
overlaps body in-text citations). Verbatim is likely faithful (08/09 were) but confirm
the audit-flagged spans where they exist. **Caveat from dird-11 (built later via
the Tesseract route):** its sibling carried a real verbatim glyph-mangle inside a
quote — the document's superscript He³ rendered as `He?` — caught only by a
page-image check, fixed, and initially mis-logged as a `preserve-as-sic`
naming_quirk. Verbatim-faithfulness is therefore NOT safely assumed for
Tesseract-route siblings; the per-DIRD image pass must check special-glyph
fidelity (superscripts / subscripts / Greek / math), not only page-citations.
**Shares the per-DIRD image pass with (a)** —
do the coverage re-level and the page/fidelity check in one sweep per DIRD.

**Blocks:** none.
**Blocked by:** none. Each DIRD's re-level / extraction is gated on OCR-sibling
verification of the relevant region.

---

## B. Parallel batch (renderer pass)

Renderer-touching items that batch into a single polish pass.

_(none)_

---

## C. Anytime (no dependencies)

No upstream blockers; safe to pick up in any session. Default-focus tier.

### C1 — OCR-scan sibling fidelity: consensus pipeline built but unwired; 32 siblings unverified; DIRD-16 backfill stalled on adjudication noise

**The defect that started this.** OCR-scan PDFs are quoted against a clean-text
`.txt` sibling, not the corrupt pdftotext layer. The existing siblings were
produced by a now-retired process: one agent transcribed the page images, a
second agent "verified" by re-reading — same modality, correlated failure mode,
no durable record, and no mechanical sibling↔source check anywhere in the gate
chain (the verbatim-quote check compares quote↔sibling, never sibling↔document).
It failed silently: `documents/dird-16-quantum-entanglement-nonlocality`'s
committed sibling carries four image-divergent errors that reached the committed
node, each confirmed against the PDF page images — `Section ITT` (image reads
III), `cammunication` (communication), the Tittel/Gisin reference volume `82`
(81), and `Kiyshko` (Klyshko). They propagated into node quotes (q4, q12), two
Source-Form Notes (nq1, nq2) that describe artifacts NOT present in the primary
source, and cited_works (cw9, cw16). nq3 (`demonstration on` for `of`) IS a
genuine document typo present in the PDF.

**What now exists (committed, not yet active).** A replacement pipeline was
built and committed: `scripts/tools/ocr-consensus.py` (multi-engine consensus +
`assemble` + `--selftest`), `scripts/tools/setup-ocr-consensus.sh` (PaddleOCR →
`.venv-ocr`), `meta/schema-ocr-verification.yaml`,
`scripts/build/validate-ocr-sibling.py`, `scripts/checks/quote_source_grounding.py`,
and rewrites of the `/prepare-ocr-sibling` skill + the `meta/conventions.md`
"Producing the `.txt` sibling" section. It cross-checks three votes with
uncorrelated failure modes — Tesseract, PaddleOCR (`.venv-ocr`, v3.6: requires
oneDNN disabled + mobile det/rec models + a capped detection side-length, all
handled in the committed adapter after the server model tried to allocate ~43 GB
on a 300-dpi page), and a VLM page-image read — accepting a token only on
≥2-of-3 agreement and flagging the rest CONTESTED for image adjudication recorded
in a `{stem}-ocr-verification.yaml`.

**Problem 1 — the new machinery is not wired into the gate chain.**
`validate-ocr-sibling.py` is not in `scripts/tests/pre-commit.sh`;
`quote_source_grounding.py` is not in `validate-research.py`'s `_ARTIFACT_CHECKS`
and carries `SEVERITY = "warn"`. By design (build→backfill→gate) they activate
only after every existing sibling has a verification record. Until then nothing
mechanically enforces sibling fidelity.

**Problem 2 — 32 OCR-scan siblings are unverified.** `validate-ocr-sibling.py`
discovers 32 OCR-scan / extraction-lossy sources that have a `.txt` sibling
(every DIRD, plus Grusch PPD-19, the FOIA docs, SD004); none has a verification
record. All were produced by the retired process. The DIRD-16 pilot confirmed
the old siblings are Tesseract-correlated (fresh Tesseract reproduces the same
`cammunication`/`82`/`Kiyshko` errors), so the error class is not unique to
DIRD-16. The per-sibling error rate across the corpus is unmeasured.

**Problem 3 — the DIRD-16 pilot stalled on adjudication noise.** DIRD-16's VLM
vote was rejected by the model's output content-filter on the full-document
transcription, forcing the 2-engine fallback (Tesseract base + PaddleOCR
cross-check, `--vlm-skipped`). The consensus correctly flagged all four known
errors as CONTESTED (Tesseract wrong, PaddleOCR right) — the core mechanism
works. But the run produced 14,405/15,641 consensus and **1,236 CONTESTED**
spans, of which roughly 1,230 are non-prose noise: the 2-engine fallback uses
raw Tesseract output as the sibling base, which transcribes every glyph on the
page including the Black Vault logo, the DIA seal, all ~12 figure diagrams, and
TOC dot-leaders. Hand-adjudicating 1,236 spans is impractical and would recur on
every figure-heavy DIRD. The noisiest band is the front matter (~5.7 contested
per line) — which also contains the quotable Administrative Note (source of q1).
A clean VLM base would not contain the non-prose tokens at all.

**Problem 4 — the content-filter block is uncharacterized.** It is unknown
whether the filter blocked one specific passage or the whole document; the
producer agent died on output after reading the pages, before writing anything.
No chunked / per-page-range production was attempted, so the recoverable
fraction of a VLM base for DIRD-16 is unknown.

**Problem 5 — the original DIRD-16 node fix is still unapplied.** The audit that
opened this thread identified the node corrections (restore `III` /
`communication`, drop nq1 / nq2, keep nq3, set the Tittel/Gisin volume to 81,
correct the Strekalov/Klyshko author). They are blocked behind producing a
trustworthy DIRD-16 sibling, so the committed node still carries the errors.

**Session state.** DIRD-16's sibling was restored to its committed
(still-erroneous) state after the pilot; the pilot's verification YAML was
ephemeral (`/tmp`). `.venv-ocr/` is present and gitignored. The consensus tooling
is verified working on the deterministic path (selftest + assemble) and on real
OCR (the 33-page DIRD-16 run completed end-to-end).

**No approach is proposed here, intentionally** — the maintainer asked that a
fresh session evaluate the noise / VLM-block / backfill problems with clear eyes.
Candidate directions were discussed in the originating session and are
deliberately omitted.

**Blocks:** none.
**Blocked by:** none.

### C2 — Investigate whether the Description "no-duplication" convention should relax

The maintainer wants `## Description` to read as a well-defined summary that may
surface select salient items also living in a structured section (a key
relationship, timeline event, contract, finding). The current convention pushes
the other way — `meta/conventions.md` "Date precision: orientation-grade in prose,
field-precise in tables" states *Description should not duplicate field-precise
dates from a structured surface* and *eliminating duplication removes a drift
surface*. That anti-drift rationale is load-bearing, so a relaxation could easily
go bad; it is deferred for investigation, not changed in place.

Avenues to weigh before any edit: (a) survey how built nodes actually use
Description today — is the overlap pressure real or rare?; (b) whether the
carve-out should stay field-precise-only (exact dates / dollar amounts / control
numbers single-sourced in their table; orientation-grade overlap allowed); (c)
whether the `description_token_drift` check needs any change (it checks grounding,
not overlap, so likely none). Produce a recommended wording, then edit the
convention and record the rationale.

**Blocks:** none.
**Blocked by:** none.
