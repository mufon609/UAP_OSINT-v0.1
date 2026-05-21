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

### A2 — Decide whether the per-entry `.note` field stays, is redefined, or is removed

`.note` (on `key_personnel`, `affiliations`, `relationships`,
`program_involvement`, `contracts`, `ownership_timeline`, …) is classified as
**synthesis** — `meta/conventions.md` lists it among "per-entry
synthesis-content notes" and the prose-drift check scans it; facts live
elsewhere (structured columns + verbatim `quotes[]`). But the field has no
*positive* definition of its job — only a vocabulary constraint (sourced
tokens) — so it drifts into the two things it must not be: restating the
row's own columns (duplication), or stating a new fact (which belongs in a
column or a quote with its own source). The james-holly / ipmo build
surfaced both modes.

Open question for the user — does the field earn its place? Three directions:
- **Keep + define positively** — note = per-entry interpretive residue
  (caveat / source-limitation / disambiguation / sequencing) the columns and
  quotes structurally can't carry; empty by default. (A first, negative-framed
  cut of this discipline is already in `conventions.md` / `agent-build.md` /
  `audit.md` — "don't restate columns, don't duplicate the Timeline".)
- **Narrow** — restrict notes to one enumerated purpose (e.g. source-quality
  caveats only); everything else moves to columns / quotes.
- **Remove** — drop the field; force all content into structured columns +
  verbatim quotes.

Resolution couples: audit what existing `.note` fields actually carry across
the corpus → pick a direction → update `conventions.md` (+ schema field
comments, + the renderers if removed) → rebuild affected nodes. No mechanical
redundancy check — redundancy here is semantic; a token-overlap scan both
false-positives on legitimate notes and misses real cases.

**Blocks:** none.
**Blocked by:** a user decision on the field's purpose.

---

## B. Parallel batch (renderer pass)

Renderer-touching items that batch into a single polish pass.

_(none)_

---

## C. Anytime (no dependencies)

No upstream blockers; safe to pick up in any session. Default-focus tier.

### C1 — `manifest.py` has no update/remove path and no structured-metadata flags

`manifest.py` only `add` mutates the YAML; correcting a registered
entry's note (or any field) has no CLI surface, forcing a hand-`Edit`
(which the build rules otherwise discourage). Also: no `--archived-date`
flag — `add` auto-stamps today, conflating archival-date with
registration-date for files that were downloaded in a prior session;
and no `--classification` / `--date` / `--pages` structured flags (all
such metadata goes into the freeform `--note`). Add an `edit`/`set`
subcommand (target an artifact by path; set a field or rewrite the note)
plus an `--archived-date` flag. Surfaced during the AAWSAP DIRD bulk
registration (36 entries; one note needed a post-add hand-fix).

### C2 — `dia-mil-reid-aatip-letter-2009.pdf` is misnamed

Page-1 read shows the file is the James R. Clapper Jr. / OUSD(I)
memorandum to the Deputy Secretary of Defense recommending against a
Special Access Program for AATIP — i.e. the memo *responding to* Reid,
not Reid's own letter (that is `reid-letter-to-depsecdef-sap-request-20090624.pdf`).
Rename the file + update its manifest path/note so a future builder
doesn't mis-cite it as Reid's letter. (A separate 3-page
`OUSDI_IM_on_AATIP_Final.pdf` on The Black Vault is a DIFFERENT, shorter
document — the 18-page packet on disk here is distinct.)

### C3 — Three AAWSAP source URLs recorded as landing-page fallback

`dird-22-…-diamil-…` (dia.mil FileId/161870 → 403), `fas-org-aatip-list-20210808.pdf`
(irp.fas.org/dia/aatip-list.pdf → 202 empty, Cloudflare), and
`dia-mil-reid-aatip-letter-2009.pdf` (dia.mil FileId/170015 → 403) are now
registered under their canonical-origin URLs (provenance-correct, per the
manifest-shape split), but those origins are bot-blocked and could not be
verified to return 200. Revisit via the Wayback fuzzy-timestamp pull (per
`meta/sources-access.md`) or a manual browser save to record verified /
Wayback-archived copies.

### C4 — No check that a type's required sections are renderer-producible

The corpus-addendum feature (now removed) exposed a class gap:
`scripts/checks/required_sections.py` can demand a section that the
type's renderer cannot emit, and nothing flags the contradiction — the
validator requires it, the build can't produce it, and the mismatch is
invisible until traced by hand. Add a "renderer-coverage" check: for each
type / kind, assert every required section is one its renderer actually
emits (cross-check `schema.yaml` required_sections against the renderer's
section list). Preventive — closes the gap that let the orphaned corpus
requirement sit in the repo undetected.

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

### C7 — Codify the document-build patterns this session demonstrated but never wrote down

Three patterns were worked out across the DIRD pilot but live only in the
built nodes, not in `prompts/build.md`'s document-build guidance — so the
next session re-derives or gets them wrong:

- **Canonical DIRD slug convention** — `dird-{BlackVault#}-{short-title}`
  (no date); reconcile inbound stub refs to it.
- **Redacted-author pattern** — when a document FOIA-redacts its own
  author, preserve that redaction as the document's own fact
  (`authors_per_document: ['[redacted per FOIA (b)(6)]']`) and STOP. Do
  NOT inject the author from an external source. Where the author is
  attested elsewhere (e.g. the DIA→Congress products list), that
  attestation lives on the *attesting* document's OWN node — build that
  node and link to it. NEVER embed the attesting document's content as a
  Key Passage on the redacted document's node: a node's Key Passages come
  only from that node's own source (now enforced by the
  `document_quote_source` check). Embedding a foreign-source quote made a
  rendered DIRD node cite itself for words it doesn't contain — a
  fabrication-class error caught only by manual review.
- **Document-node load-bearing capture** — wrap-link the author, the
  acknowledged / cited load-bearing entities (correct canonical stubs),
  and catch notable cross-topic quotes (named programs / people / orgs,
  e.g. Project Paperclip). The general "Relevance can be relational"
  principle is in `conventions.md`; its document-build application is not.

Plus the cross-cutting rule that prevents the exemplar-mirroring bug
class: **a node's facts and links are confirmed against ITS OWN source,
never copied from another node — exemplars provide structure/shape only.**
(The `dird-01` build copied `dird-15`'s DIA→AARO mislink by mirroring the
exemplar.) Codify in `prompts/build.md` and reinforce in the worker /
build agent prompts.

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
