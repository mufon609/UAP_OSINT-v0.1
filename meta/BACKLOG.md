---
id: meta/BACKLOG
type: meta
schema_version: 1
created: 2026-04-17
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

The seven-role pipeline (`prompts/topology.md`) has now been run *whole* on
one real node build — a user-directed, all-internal institutional-actor
build: Orchestrator → Internal Investigator → Worker (×N) → Build → Audit,
with handoff stubs captured and friction tightened in place. Three paths
were NOT exercised by that run and remain unverified end-to-end:

- the **External Investigator (role 2) + Archive (role 3)** roles — skipped
  by the all-internal branch (every source was already archived). Needs a
  build with a genuine external-source gap.
- the **`caption` and `foia` worker kinds** — only `pdf` + `html` were hit.
- **Error-Agent routing** — no validator failure needed routing on the clean
  run.

Drive a build that forces these paths (a target with an external-source
gap + a caption/FOIA source); confirm each `--phase X` fires exactly the
checks reading role X's state; tighten friction in place where cheap, file a
new entry where not.

**Deferred follow-on:** split `prose_drift` into `prose_drift_toplevel`
(organize phase) + `prose_drift_notes` (link phase) only if one-phase-late
surfacing of top-level prose drift proves annoying.

**Blocks:** none.
**Blocked by:** a user-directed build with an external-source gap.

### A3 — Recover the facts removed when the `.note` field was eliminated

The per-entry `.note` field — an unchecked, reader-facing catch-all that had
accumulated fact-store paraphrase, opinion, future-work pointers, cross-node
bookkeeping, and duplicates — was **eliminated repo-wide**: stripped from every
research artifact (≈640 notes across 50 files), removed from the schema and the
prose-drift scope, dropped from the renderers, and retired from `conventions.md`.
The corroboration "what it confirms" content (the one note that was load-bearing,
not residue) was preserved under a new `confirms` field; `naming_quirks`
structured mappings and `vouching_chain.attestation` survive. This item tracks
what removal left to recover, plus the non-note data debt the audit surfaced.

**Load-bearing facts removed from notes — re-investigate and promote to verbatim
quotes (with `source.location`):**
- **SRI remote-viewing program lineage** (was narrated in
  stanford-research-institute or4/or5, carried in no quote): per the 1993 DIA
  STAR GATE Project Overview — CIA funding discontinued 1975, subsequent funding
  by DIA; an HQDA/INSCOM small unit established late 1970s, transferred to DIA in
  1986 as the SUN STREAK Special Access Program; FY1991 Congressional direction
  established successor research at SAIC, Menlo Park. Plus the 9 November 1973
  K. Green (CIA OSI/LSD) "Verification of Remote Viewing" Memorandum for the
  Record (Kress 1977 footnote, ~source line 410). Promote the load-bearing
  pieces to quotes on SRI.
- **DoDD 5143.01 authority basis** (was ousd-is or1): "pursuant to the authority
  vested in the Secretary of Defense (SecDef) by sections 113 and 137 of Title
  10, United States Code" — verbatim-promotable (DoDD 5143.01, ~l.17-18).
- **hal-puthoff TTSA / AATIP attestations narrated into relationship/program
  notes**: the 2017-12-16 NYT TTSA-venture sentence; the TTSA SEC Form 1-A
  stock-grant sentence (Gravity Holdings, LLC / JimSemI, LLC / Harold Puthoff);
  the 2018 TTSA ADAM "former Senior Advisor and Subcontractor to … AATIP" line.
  Promote whichever are load-bearing to quotes; otherwise they stay out.
- **sancorp facts that survive nowhere else once their restatement-notes are
  gone**: JAIC DRAID BOA + AI-Eng BPA (c3); the GSA vehicles MAS (July 2022),
  8(a) STARS III GWAC, OASIS+ #47QRCA25DA398 (or13) as `contracts[]` rows;
  `number_of_offers_received: 1` (c14) as a column; the MDA SHIELD IDIQ award
  (q49 / USAspending). Note: c17's citation to a non-existent "Sancorp Featured
  News January 2026" was deleted, so the SHIELD award needs a real archived
  source; and the strings stripped as unattested this pass — STARS III
  "47QTCB22D0104" and the "AI Talent 2.0" BOA label — must be re-verified before
  any reuse (neither appears in any archived source).
- **aaro PWS facts** on `blackvault-sancorp-23-f-1114-aaro-pws.pdf` (SF-33
  issuing-office block + task-area enumeration) are OCR-corrupt with no
  clean-text sibling — not promotable to quotes until `/prepare-ocr-sibling`
  produces one.

**Future-work (was narrated inside rendered notes; the node is not its home):**
- Archive the Puthoff–Targ "The Record" SRI daily log → resolves the
  five-week-vs-nine-day Geller SRI-engagement discrepancy (uri-geller rumor r1).
- Archive a primary source for the Uri Geller Museum opening date → graduate
  uri-geller rumor r4 to a quote and populate affiliations a9 `period_start`
  (currently secondary-only "2021").
- Decide where the "known start, unknown end (but not ongoing)" period
  convention lives (a conventions.md decision) — hal-puthoff a2/p1 (and
  russell-targ) cited a now-emptied research-queue.md entry for it; the dead
  citation was stripped.

**Finding to create — AARO → AIC budget rebrand:** FY2024 OSD OP-5 named AARO;
FY2025 OP-5 was the first to substitute "AIC"; FY2026 retains AIC; no public DoD
announcement of an AARO renaming, and aaro.mil remains active. This
multi-budget-year cross-source pattern was narrated in ousd-is entity notes
or7/or15 (the entity layer must not carry patterns) — route it to a new finding
citing the OP-5 sources directly.

**Non-note data debt surfaced by the audit (pre-existing; not note-related):**
- **deprecated `lines N-M` source.location forms** — ~12 artifacts still use the
  extraction-anchored `lines N-M` form instead of the source-anchored form
  (`p. N, ¶M` / `[MM:SS]` / section descriptor): mostly older event / transcript
  / Nimitz-eyewitness nodes (`2004-nimitz-encounter`, the 2023 hearing
  transcripts, `david-fravor`, `david-grusch`, `sean-kirkpatrick`). Run
  `normalize-locations.py` + a contributor pass. Also tighten alex-dietrich's
  imprecise Debrief `line 66` refs (a1/a10/a11 point at a `<script>` tag; content
  is at lines 96/1275).
- **ronald-moultrie a29 BlueVoyant mis-dating** — the affiliation row's
  `period_start`/`period_end` (`2021-06`), role text, and timeline `t25`
  contradict the cited source (`datePublished` 2020-09-02; `2021-06` traces to
  `dateModified` + the manifest filename suffix). Re-verify + re-date; may also
  touch the a-Mitre / a-Pallas rows if they rest on the same source.
- **ronald-moultrie a11 C5 source re-pull** — the cited
  `mondovisione-c5-partners-moultrie-nsa-20170306.html` is a JS-shell / cookie-
  wall capture with no extractable body (backs the "March 2017 Strategic Partner"
  fact + timeline `t21`). Re-pull a usable capture.
- **uri-geller sourcing reconciliation** — the `program_involvement`
  "CIA-sponsored SRI investigation" row references a contract 1471(S)73 progress
  report and the 1974 Nature paper absent from `primary_sources`; the explicit
  CIA-funding statement (CIA-RDP96-00791R000100030062-7) lives only in an
  image-only TIF with no text layer (needs `/prepare-ocr-sibling`). Reconcile the
  source list and verify the sponsorship basis.
- **research-queue / lockheed-investigation reference reconciliation** — the
  `lockheed-martin-uap-materials` investigation's `what_would_resolve` cites
  research-queue.md "Externally blocked" (FOIA appeal 24-F-0266); give that
  external-blocked acquisition item a tracking home.

**Blocks:** none.
**Blocked by:** nothing — execution.

---

## B. Parallel batch (renderer pass)

Renderer-touching items that batch into a single polish pass.

_(none)_

---

## C. Anytime (no dependencies)

No upstream blockers; safe to pick up in any session. Default-focus tier.

### C5 — Streamline prose-drift iteration WITHOUT weakening it (critical; handle carefully)

The prose-drift gate is correct and the resulting nodes are worth the
energy — but source-grounding a synthesis `description` took 3–6 rewrite
passes per node this session (`check-vocab.py` pre-flight roughly halves
it). Two rough edges: token-passing can yield stilted non-English ("is
acknowledging by") that no grammar check catches; and contributors burn
passes guessing source morphology. This is CRITICAL repo discipline —
any streamlining must NOT relax the zero-ungrounded-token floor.
Candidate directions that preserve the floor: tighter `check-vocab.py`
integration into the authoring loop, a morphology-aware suggestion
surface (source has `gives`, not `give`), or surfacing the source token
pool inline. Implement extremely carefully; the gate's rigor is the point.

### C6 — prose-drift grounds `description` against source text only, not `document_intrinsic` / `naming_quirks` (handle carefully)

The Phase-I prose-drift check grounds `description` tokens against the
primary-source TEXT only — it does not credit `document_intrinsic` values
or `naming_quirks.canonical`. Consequence (seen on `dird-01`): describing
a fact that lives only in structured metadata — e.g. a FOIA redaction,
whose vocabulary (`redacted`, `withheld`, `exemption`) is absent from the
source prose — is impossible in the description, and must be surfaced via
Key Passages + `naming_quirks` instead. This may be intended (description
= strictly source-grounded synthesis); decide deliberately whether the
check should credit canonical-form `naming_quirks` / `document_intrinsic`
vocabulary. Same check family as C5; handle with the same care.

### C8 — Phase-I prose-drift and Phase-III description-drift treat adjacent punctuation differently

On `dird-15`, a comma fused inside a closing quote (`apparent "cloaking,"`)
PASSED the Phase-I prose-drift check (the bare token appears in the source
elsewhere) but FAILED the Phase-III description-drift check (which
tokenizes the rendered section and caught the fused punctuation). Two
checks in the same family with different adjacent-punctuation exposure —
a contributor can clear one and trip the other on the same text.
Reconcile their tokenization (shared adjacency handling) so the same text
passes/fails both consistently. Same check family as C5/C6.

### C9 — verbatim-quote check doesn't normalize page-footer/header boilerplate

On `dird-15` (q12/q13), a Discussion passage spanning a printed-page
boundary carries the page footnote + page number + classification
footer/header wedged mid-sentence; that boilerplate isn't in the quote,
so a single verbatim quote across the boundary fails the verbatim-quote
check, forcing a split into two adjacent Key Passages. `normalize_for_compare`
already strips `[MM:SS]` caption timestamps but does NOT strip recognized
page-footer/header/page-number boilerplate. Consider normalizing
recognized page boilerplate in the verbatim check (carefully — it must
not mask real mismatches), or document the split-at-page-boundary
expectation prominently. Recurs on every page-spanning quote in paginated
sources.