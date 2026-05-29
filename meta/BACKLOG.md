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

> **⚠ Superseded in part by C3 (markerless strip-all).** The page-for-page
> mirroring claimed in this subsection — siblings carrying `----- PAGE BREAK
> -----` markers so *block count == `pdfinfo` page count* — was reversed by C3's
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

### C1 — ✅ DONE (2026-05-29): dlib face embeddings replaced Haar+pHash

**The problem.** The agent-based speaker-attribution pipeline ships with a
mechanical fourth-layer spot-check at `scripts/tools/spot-check-attribution.py`
— extracts beginning/middle/end frames per turn, runs face-detection +
photo-identity-log baseline matching, surfaces per-turn `confirmed` /
`contested-fold` / `contested-other` / `inconclusive` verdicts. The intent is
contributor peace-of-mind: every turn gets mechanical visual cross-check, and
a fold-up (two speakers folded into one turn) shows up as `contested-fold`.

The current matching stack — Haar-cascade face detection + perceptual-hash
(pHash) baseline matching — has a structurally low ceiling. Test evidence
from the three shipped pilots (2026-05-29):

| Pilot | confirmed | contested-fold | contested-other | inconclusive | useful? |
|---|---:|---:|---:|---:|---|
| jre-2194-elizondo-2024 (3,660 lines, 145 turns) | 23 | 19 | 1 | 97 | yes |
| mysterywire-lacatski-kelleher-knapp-2021 (429 lines, 18 turns) | 1 | 4 | 7 | 3 | marginal |
| 8newsnow-craft-of-unknown-origin-lacatski-2026 (140 lines, 19 turns) | 0 | 0 | 13 | 1 | no |

JRE-2194 works because Rogan + Elizondo have distinctive features and the
JRE camera setup matches existing baselines. The other two pilots show the
fundamental limits: pHash distance distributions for same-person frames vs
different-person frames OVERLAP (same-person ranges 5–25; different-person
ranges 5–30). No single threshold separates them: distance 5 (default for
near-duplicate dedup) misses real matches at distance 15; distance 20
catches real matches but also surfaces false-positives like `david-grusch`
detected in a JRE-Elizondo episode, or `david-fravor` / `luis-elizondo` /
`james-ryder` detected across every 8newsnow news-package frame where
neither is actually present. Haar-cascade also misses 50–75% of faces at
random timestamps because of profile/angled/looking-down shots.

**✅ RESOLVED (2026-05-29).** The matching stack was replaced in place with
dlib's HOG detector + ResNet 128-d face embeddings via `face_recognition`
(no dual-backend — clean cut, pHash recoverable from git). dlib built from
source in a project-local `.venv-face/` (`setup-face-embeddings.sh`); the
tools auto-relaunch under it. Distance metric is **Euclidean** (the library's
native metric; the "cosine ~0.4" note above was imprecise), default
`--embed-threshold 0.50` (tighter than dlib's 0.6 to favour precision).
Baselines are encoded once into a sha256-fingerprinted `baseline-encodings.npz`
cache.

**Measured result — same three pilots, embed @ 0.50 vs the saved pHash run:**

| Pilot | confirmed | contested-fold | contested-other | inconclusive |
|---|---|---|---|---|
| jre-2194 | 23 → **27** | 19 → 22 | 1 → **0** | 97 → 91 |
| mysterywire | 1 → **6** | 4 → 7 | 7 → **0** | 3 → 2 |
| 8newsnow | 0 → **5** | 0 → 4 | 13 → **0** | 1 → 5 |

Every prediction held: **`contested-other` look-alike false positives → 0 on
all three pilots** (the JRE `david-grusch`-in-an-Elizondo-episode and the
13 phantom 8newsnow matches are gone); confirm rate rose on every pilot;
previously-`inconclusive` Haar-missed angled shots now resolve. The
false-positives that existed reclassified to *correct* verdicts (real
same-panel detections → confirmed/fold), not to new errors. Threshold sweep
0.45/0.50/0.55 on JRE: all hold contested-other at 0; 0.50 ties 0.55 for
peak confirms — a wide clean band, confirming the same/different distance
gap pHash lacked.

**Baseline expansion — done, but the honest finding:** core identities grown
to 5–10 refs (lacatski 1→7, kelleher 1→5, rogan 2→5, elizondo 2→5, spanning
angle/year/setting; knapp stayed at 1 — he is the off-camera interviewer in
our sources, no on-camera single-face frames to harvest). Re-running all
three pilots with the expanded 43-vector baseline set changed **0 verdicts**
and only 2/145 match-lists: embeddings were already at ceiling on these
pilots with single baselines. The extra references are insurance for harder
*future* inputs (profile, cross-lighting, cross-year), not a measurable lift
on the current corpus — recorded so the next contributor doesn't expect one.

Shipped: `detect-faces.py` engine swap (HOG detect + embedding dedup/identity
+ `encode-baselines` subcommand), `spot-check-attribution.py` wiring +
`--embed-threshold`, `setup-face-embeddings.sh`, docs (CLAUDE.md,
VIDEO-PIPELINE.md, SKILL.md, setup-photo-identity.sh — Haar/opencv dependency
retired). Comparison CSVs preserved under
`sources/photo-identity-log/.compare/` (gitignored). (The interim step that
updated `stitch-transcript.py` to the embedding API was mooted by the
follow-up removal below.)

**Follow-up — DONE (2026-05-29):** the superseded diarize+stitch path
(`stitch-transcript.py` + `diarize-audio.py` + `setup-diarize-audio.sh` +
`.venv-diarize`) was removed; the agent-based `/prepare-transcript-sibling`
is the sole speaker-attribution spine, with `detect-faces.py` /
`spot-check-attribution.py` as the visual backstop. Docs (CLAUDE.md, README,
VIDEO-PIPELINE.md now four-step, conventions.md, sources-access.md, SKILL.md)
updated; the audio-only source path now routes to the agent text-pass +
manual anchoring instead of pyannote diarization.

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

### C3 — Speaker-attribution pipeline: prevent attribution errors at the source

The pipeline's *verbatim* guarantee is sound, but **attribution correctness
rests on fallible agent judgment plus hand-keying**, caught only by
after-the-fact checks. Two opposite-polarity misattributions were found in one
transcript this session: a worker hand-keyed a `speaker_id` that contradicted
the sibling, and a producer boundary call was passed by the independent
verifier at HIGH confidence yet was wrong (image evidence overturned it). The
shipped `speaker_attribution_consistency` check catches the first class but
only at quoted spans, and the second class never reached the image backstop
because that backstop is gated by producer self-doubt.

**The shift: make the sibling a verified single-source-of-truth, then DERIVE
everything downstream from it.** No human re-keys attribution; the consistency
check becomes defense-in-depth that should never fire. Because derivation
trusts the sibling, sibling correctness (W3+W4) must land with or before
derivation (W1).

- **W1 — Derive `speaker_id`, don't author it.** New `scripts/build/stamp-speaker-id.py`
  resolves each transcript quote's `[MM:SS]` → sibling turn → speaker and
  stamps `speaker_id`; it also generates the artifact's `speakers[]` from the
  sibling (so ids/names/node_links are copied, not independently re-authored —
  killing the id-divergence hazard). The Worker stops hand-typing `speaker_id`
  (emits text + location only); the Builder runs the stamp step. For
  person/org artifacts, the same tool runs in confirm-mode (warns if the
  sibling attributes a quoted span to someone other than the node subject).
  Reuses the resolution helpers in `scripts/checks/speaker_attribution_consistency.py`
  (`_load_siblings`, `_range_seconds`, `_resolve_line`, `_build_line_map`,
  `_build_source_index`, `_norm_link`/`_norm_name`) and the timestamp map in
  `scripts/tools/spot-check-attribution.py` (`build_line_timestamp_map`).
  Touches `.claude/agents/worker.md` + `.claude/skills/build-protocol/`.

- **W3 — Systematic video verification as an always-on hard gate.** Wire
  `scripts/tools/spot-check-attribution.py` (already samples beg/mid/end frames
  per turn across ALL turns and emits confirmed / contested-fold /
  contested-other / inconclusive / no-baseline / n/a-foreign) into
  `/prepare-transcript-sibling` as a mandatory pre-finalize step. A
  `contested-fold` verdict BLOCKS finalize and routes back to producer/verifier.
  **No graceful skip:** a sibling for a video source cannot be finalized unless
  the video + `.venv-face` are present and the spot-check runs (`no-baseline`
  speakers such as moderators are recorded as honestly unverified, not a pass).
  This de-gates the backstop from producer self-doubt; it would have caught the
  4-line boundary fold found this session. Note: `needs_image_verification` is
  now draft-only/stripped on finalize, so the producer flag is no longer the
  gate — the systematic spot-check is.

- **W4 — `node_link` as the identity join key.** New check in
  `scripts/build/validate-speaker-attribution.py`: every live (non-`foreign-*`)
  speaker in a *verified* sibling must carry a `node_link`. Makes the sibling
  the authoritative identity map and kills the honorific/name-matching
  fragility (e.g. "Dr. Colm Kelleher" vs "Colm Kelleher"). Backfill the
  existing siblings whose live speakers lack links.

- **W2 — Harden the sibling format (follow-on).** Add deterministic per-turn
  `start_ts`/`end_ts` and a top-level source content hash, computed by
  `scripts/build/finalize-attribution.py` (timestamp derivation already exists
  in spot-check). Exact timestamp resolution replaces the nearest-preceding
  heuristic; the content hash replaces line-count-only drift detection.
  `validate-speaker-attribution.py` gains hash + timestamp-consistency checks.

- **W5 — Document the residual.** Sub-line speaker transitions (turn-end +
  turn-start packed on one `[MM:SS]` line) cannot be represented by the
  line-range schema and cannot be fully eliminated; keep the
  dominant-speaker + `medium`-confidence convention and rely on W3 to catch the
  worst cases. Document honestly in the SKILL + conventions as a known limit.

**Issue → mitigation:** (1) confident-wrong verification / self-gated backstop
→ W3. (2) errors across worker/producer/verifier, worker ignored the sibling →
W1. (3) consistency check covers only quoted, transcript-side spans →
dissolved by W3 (all turns verified at production) + W1 (universal derivation,
incl. person/org confirm-mode). (4) coordinate-mismatch heuristic +
source-stability pinning → W2; sub-line granularity → W5 (residual). (5) id
divergence + missing node_links + honorific name-matching → W4 + W1.

**Sequencing:** W3 + W4 (harden the sibling) → W1 (derive from it) → W2
(format hardening); W5 is doc-only, anytime. Migration: re-finalize the
existing siblings (backfill node_links, timestamps, hash) and re-stamp the
existing transcript artifacts to confirm.

**Residual to clear at W3 migration:** before `needs_image_verification` was
de-gated (commit 992006d), 9 turns the producer had flagged for image
verification across 3 verified siblings — jre-2194-elizondo-2024 (7),
8newsnow-craft-of-unknown-origin-lacatski-2026 (1),
mysterywire-lacatski-kelleher-knapp-2021 (1) — shipped without ever being
visually confirmed. The flags are now stripped and the durable
`confidence: low|medium` markers carry the uncertainty (lucistrust's one
flagged turn already has an `image_verification[]` resolution). These turns are
not a correctness gap, but they are the concrete set of "never visually
verified" turns that W3's always-on spot-check should retroactively cover when
it re-finalizes the existing siblings. Until then they remain honestly
unverified.

**Blocks:** none.
**Blocked by:** none. W1 is internally blocked by W3+W4.

### C4 — Skills↔conventions sharing: the layer is already cite-don't-restate; resolve the one orphan

**Finding.** The skill layer already implements "per-skill + a common helper,
cited not restated," and the design splits correctly by *where a skill runs*:

- **Build agents (fresh-context subagents).** The six role agents under
  `.claude/agents/` share one common helper — `.claude/skills/build-protocol/SKILL.md` —
  preloaded via `skills: build-protocol` in each agent's frontmatter and **cited**
  with the `(build-protocol → section)` arrow pattern, never restated. `build-protocol`
  is topic-neutral and itself cites `meta/conventions.md` for the long-form disciplines
  ("Producing the `.txt` sibling"; "Tier model and linking contract") and
  `scripts/checks/_phases.py` for phase vocabulary. This is exactly the common-helper
  shape; it earns its keep because a fresh-context subagent cannot see
  CLAUDE.md/conventions.md by default.
- **Standalone (main-thread) skills.** `onboard` / `audit` / `augment` /
  `verify-transcript` / `prepare-ocr-sibling` / `archive-sweep` / `fork-init` cite
  `meta/conventions.md` directly — the correct common source on the main thread, where
  the skill text + CLAUDE.md + conventions.md are all reachable. No preloaded helper
  is needed.

**Decision recorded (so it is not re-opened): do NOT add a new shared-helper skill
for the standalone family.** It would duplicate what `meta/conventions.md` already is
for main-thread skills, and the inline restatements that exist are *audience-specific
slices*, not flat duplication — e.g. the OCR-sibling discipline is canonical in
conventions.md ("Producing the `.txt` sibling"), summarized in `build-protocol`, and
each consumer restates only its slice (`build` step 4b = the orchestrator's
sibling-readiness slice; `prepare-ocr-sibling` = the producer/verifier slice).
Factoring those into a fourth shared file would add indirection without removing a
real drift surface.

**The one genuine orphan — `quote-relevance-audit`.** Its discipline (the
keep/consolidate/move decision matrix; "attribution ≠ relevance"; "move detail, don't
lose it") lives only in the skill, with no anchor in `meta/conventions.md` — the
existing "Relevance can be relational" section is about *entity* inclusion, not
*per-quote* content-relevance. This is currently by-design: the skill's own closing
line defers centralization until "the same over-extraction shape recurs across many
nodes." Gated action (test-before-BACKLOG): once that over-extraction shape has
recurred across multiple node audits, promote the matrix to a named
`meta/conventions.md` section (sibling to "Comparability standard") and have the skill
cite it; until then leave it skill-local. Do not pre-emptively centralize a
one-consumer discipline.

**Minor, optional (low value).** Citation hygiene across the standalone skills is
slightly uneven — most name the cited section (`conventions.md "Comparability
standard"`), a few cite the doc without the section anchor. Always-name-the-section
would aid navigation but fixes no defect; fold into any future skill edit rather than
a dedicated pass.

**Blocks:** none.
**Blocked by:** nothing; the quote-relevance promotion is gated on observed
recurrence, not a dependency.
