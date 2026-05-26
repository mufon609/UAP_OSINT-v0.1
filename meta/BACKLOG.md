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

### A2 — Audit the label-less transcript corpus against the speaker-attribution discipline

**The problem.** A transcript whose source is *label-less* — a machine caption or
speech-to-text that records the words but not who spoke them — cannot have its
speakers *determined* by a text reader; they can only be *inferred* from textual
cues (second-person address, one participant naming another in the third person,
question-then-answer structure). Those cues are frequently absent or ambiguous in a
fast two-party exchange, and inferring from them is the very process that produces
misattributions: a line delivered by one participant gets assigned to the other, and
a back-and-forth collapses onto a single speaker. The ground truth for
who-is-speaking lives only in the audio. A pilot audit of one label-less
multi-speaker transcript found exactly this pattern in already-shipped content (a
passage attributed to the wrong participant; another single-attribution that was
really a two-party exchange; a summary line crediting the wrong speaker) — the
discipline gap is real, not hypothetical.

**The discipline (defined + codified).** Speaker attribution on a label-less source is
**confirm-against-source** — the audio/video analog of source-read-first. Where video
exists, confirm by *image* (frames at the quote timestamp matched to a face baseline,
human-verified — stronger than telling similar voices apart by ear); audio-only sources
use diarization for turn boundaries plus an anchor; a genuinely unresolvable boundary
takes the mixed-exchange `speaker_id` list (the honest marker, not a license to skip
attribution work). The decision tree, the per-method dependency gating, and the
issue-routing live in `meta/conventions.md` "Speaker attribution: source format selects
the method" and `scripts/tools/VIDEO-PIPELINE.md` Step 0. Shipped: the mixed-exchange
mechanism (`speaker_id` as a 2+ id list, rendered `Speakers — mixed exchange`); the
diarize venv-missing fail-fast; the pilot (`lucistrust-rending-veils-ryder-2017`)
proven by image-verification and committed.

**Latent features assessed (keep both).** `derived_from` (transcript frontmatter) is
wired + rendered but has 0 uses — its case is a transcript that is a text rendering
*of* a media/document node; latent, correct, keep. The audio-diarization sub-branch
(`diarize-audio.py` + `setup-diarize-audio.sh`) was built and debugged historically
but is unexercised in this checkout; optional, keep, note the setup cost.

**Tooling-adequacy gaps — do NOT file fixes until each is proven needed (the
test-before-BACKLOG rule).** The is-the-pipeline-enough answer for label-less
multi-speaker sources is *no*, but each specific fix must be demonstrated against a
real failing test before it becomes a work item: a label-less speech-to-text source
is not a first-class tool path (`transcribe.py` is YouTube-caption-only); there is no
mechanical speaker aid for label-less transcripts (attribution falls to manual
inference); the speaker-ID pipeline's intermediate outputs are `/tmp`-ephemeral;
`stitch-transcript.py` loads the face-detector by file-path `importlib` hack rather
than a shared module; there is no end-to-end integration test of the
download→diarize→stitch path; Haar-cascade face detection misses frequently (manual
crop fallback); and several thresholds are hardcoded (pHash distance, min face size,
segment-snap tolerance).

**Remaining work.**
1. **Audit the remaining transcript nodes**, one at a time, against the discipline:
   stenographic / published hearing transcripts are speaker-labeled in source
   (mechanically verifiable, low-risk); auto-caption / Whisper interview transcripts are
   label-less (image path where video exists, else audio path + mixed tag). Candidates:
   the `other`-kind nodes — jre-2194, 8newsnow, mysterywire, and the weaponized-*
   set (038/096/097/114). Still open: the generic conversation template in
   `conventions.md` (narration as a `speakers[]` Narrator entry; non-speech captured
   only when verbatim-in-source AND load-bearing; same-speaker-different-recording via
   `statement_date` + `context`) — fold in as the corpus audit surfaces the cases.
2. **Re-assess the tooling gaps above** with test evidence (test-before-BACKLOG rule):
   file a specific fix only once a real failing test demonstrates the need.

**Blocks:** none.
**Blocked by:** nothing — incremental, one transcript at a time.

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

**(b) Extract `cited_works` — all 11 BUILT DIRDs are DONE.** Each built DIRD's
reference list is extracted and source-fidelity-gated, with the citation marker
style preserved per source (`[N]` brackets, `^N` endnotes, `N.` numbered list,
and dird-26's sub-lettered `[5-a/b/c]` UFO-relevant entries — Schuessler,
Sturrock, Vallee, Cash-Landrum). dird-03 (Pulsed HPM) and dird-04 (Biomaterials)
were assessed and **carry no formal reference list** (end at Conclusion / Summary;
sibling marker-scan = 0; PDF last page confirmed) — their `cited_works: []` is
correct, not missing. Remaining: the UNBUILT DIRDs (08/09/10/11/12/13/14/16/17/19
through 37 — 26 archived, none built) get their citations when each is built —
same per-DIRD flow (locate region → image-verify sibling vs PDF → worker extract →
integrate). The recurring-author network is the payoff (Puthoff across dird-24 +
dird-15; E. W. Davis / C. Maccone cross-DIRD).

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

**(c) DIRD page-ref convention — DONE (all 11 DIRDs).** Settled rule
(`meta/conventions.md` "`p. N` is the physical page"): `p. N` = the PDF viewer's
page N (the Nth physical page of the file), so a reader opening the source PDF
to page N lands on the quote. The OCR sibling therefore preserves **every**
physical page verbatim — including the third-party Black Vault distribution page
the PDFs carry at physical page 2 (preserved as-is, never summarized, never
dropped). All 11 built DIRD siblings now mirror their PDFs page-for-page (block
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

### C1 — Apply the family-comparability audit to AARO's contested claims

The cross-node comparability mechanism now exists — the "Comparability standard"
in `meta/conventions.md` plus the recommend-only family-comparability goal in the
auditor (`.claude/agents/auditor.md` goal 8, surfaced in `/audit`). Remaining is
the one concrete observed asymmetry: `/organizations/aaro` carries no
`## Primary-Source Contradictions` section while peer `gov` org
`/organizations/ipmo` does. Run `/audit` on `aaro` and apply goal 8 — does AARO
have a circulating public claim that an archived primary source actively refutes
(warranting a `rumors[].status: primary-source-disputed` entry)?
`/findings/aaro-denial-action-mismatch` is a lead. A **source re-check, not a
count match**: add an entry only if a source attests it; if none does, the
absence is correct.

(The Associated-Nodes-vs-Relationships observation was resolved as **by-design** —
Associated Nodes is an unlabeled post-build navigation surface; relation type
lives on the source entity's Relationships row. Duplicating it onto every
backlink is redundancy, not discipline. No change.)

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

### C3 — Make the non-DIRD `p. N` refs verifiable (silent-skip remediation)

`quote_location_page` only verifies `p. N` when the source extract is
page-structured (canonical `----- PAGE BREAK -----` → `\f`, or pdftotext form
feeds). A repo-wide audit found the non-DIRD paginated sources cite `p. N`
against extracts that aren't page-structured, so those refs are **silently
skipped** — text still verbatim-verified, page unchecked.

**Already DONE (do not redo):**
- **Form-feed-eating bug fixed** (`scripts/lib/_common.py`, commit `24be516`).
  `extract_source_text`'s hyphen-merge (`-\s+`→`-`) was swallowing the `\f`
  after any page-final hyphen (footer page numbers like `- 1 -`), silently
  fusing pages and shifting every downstream split. This corrupted the page
  check for *any* paginated source — the checker is only a reliable oracle
  after this fix. Restricted to whitespace-minus-form-feed.
- **`cia-rdp79`** sibling normalized to canonical breaks (commit `199b11a`);
  its 24 refs now actively verified and pass. This is the proof-of-method.
- **Sibling rule refined** in `meta/conventions.md` + `schema.yaml`: a sibling
  is warranted only for `ocr-scan` (OCR-producer metadata) or *pervasively*
  corrupt `extraction-lossy` (stenographic line-number noise). A clean,
  natively-paginated text layer with only a *sparse* glyph artifact stays
  `text-native` — no sibling.

**Decisions (locked with the maintainer):** (1) page anchor = **physical
PDF-viewer page**, uniform with the DIRDs (refs that cite a printed/stenographic
page must be re-derived to physical). (2) HTML `p. N` claims are removed (HTML
has no pages) — anchor to a section heading or `¶N`. (3) **Remove + regenerate
over fix** a needless or broken sibling.

**Work — A. Remove the House transcript sibling (it should not exist).**
`congress-gov-house-hearing-transcript-20230726` is text-native (Acrobat
Distiller from a `.txt` source; pristine, natively-paginated `pdftotext`). Its
54-page hand sibling existed only to repair one `11½`→`‡` glyph and its
hand-pagination diverged from the PDF (marked 3 front-matter pages; the PDF has
4 — printed `p. N` = physical `p. N+4`). Reclassify `text-native`, delete the
sibling, and regenerate the refs against `pdftotext`. **Coupled** (do as one
unit — removal activates both checks): (i) the verbatim check — the 2 `11½ hours`
quotes (`2023-07-26-house-grusch`, `david-grusch`) fail vs pdftotext's `11‡`:
re-derive them or add the `½`/`‡` confusable to `normalize_for_compare`; (ii) the
physical-page check — re-derive the bare-leading `p. N` refs (house-fravor /
-grusch / -graves / -uap-hearing, ryan-graves) and, for consistency, the
descriptive-prefix refs too (`…, p. N`), printed→physical (+4, confirm constant
via the pdftotext printed-number-per-page map). ~212 refs across 6 artifacts.

**Work — B. Page-faithful the genuine siblings** (ocr-scan / pervasive-lossy;
their `p. N` refs are silently skipped today). Per source: paginate to canonical
`----- PAGE BREAK -----` (block N = physical page N), run
`validate-research.py`, re-derive each flagged ref to the physical page the
checker reports (it is now a reliable oracle), verify block-count == `pdfinfo`,
commit.
- *image-only (read page images, dird-06 method):* `cia-rdp96-…100180001-3`
  (extend its `[Page N]` markers 21→29), `cia-rdp96-…100220001-8` (Nature, 19pp),
  `foia-23-f-0905-doc-1` (34pp; normalize its `PAGE N of 34` markers),
  `docs-house-…go12-…-sd004` (21pp; refs all `p. 1`).
- *OCR with a usable text layer (pdftotext-map align, spot-verify):*
  `foia-23-f-0906-sancorp-ipmo-pws`, `blackvault-aaro-invitations-to-grusch`
  (FOIA correspondence release — confirm `p. N` vs `Doc N` per its nature).
- *stenographic text-native-noisy (pdftotext form-feed map):* SASC
  `-20230419` (56 refs) and `-20241119` (7 refs; also re-anchor its
  `p. N, lines X-Y` refs — the line numbers are stripped from the sibling).
- `foia-23-f-0905-doc-2` is a **single physical page** → legitimately no `\f`,
  `p. 1` skipped by convention. **No work.**

**Work — C. Downgrade HTML `p. N`** (page-less): `sec-ttsa-1a-partii-20170710`
(~24 refs in `ttsa.yaml`, plus `hal-puthoff`) → section heading / `¶N`;
`opg.optica.org` Targ articles in `russell-targ` **per-ref** (keep `p. N` where
the ref points to a CIA *PDF*, downgrade where it points to the optica HTML).
The `optica` hits in DIRD artifacts are `cited_works` bibliography, not
`source.location` — leave them.

**Work — D. Add the gates** (after A–C land; lean):
- `sibling_parent_extraction_type` — a same-stem `.txt` sibling may exist only
  when its PDF parent's `extraction_type` is non-text-native (enforces the
  proportionality rule; once House is removed there are 0 violations).
- `sibling_page_faithful` — any sibling carrying `----- PAGE BREAK -----` must
  have block-count == `pdfinfo` pages (fires only on marker-carrying siblings,
  so `Doc N` email-release siblings are untouched). All DIRD + cia-rdp79
  siblings already satisfy it.
Wire both into `validate.py`; register phases via `_phases.py` parity gate.

**Blocks:** none.
**Blocked by:** none — each source is independent; A is self-contained.
