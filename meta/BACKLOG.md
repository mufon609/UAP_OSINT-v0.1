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
each section (A1, A2, ..., B1, B2, ..., C1, C2, ...) are positional
and assigned at write time. When an item is retired, its block is
deleted in full; no marker, no placeholder, no renumber. The next
new entry in the section takes the next previously-unused ID — IDs
are not reused, so commit-message and git-log references to a
historical ID stay unambiguous when grepped. See `meta/conventions.md`
"BACKLOG lifecycle discipline" for the rule of record.

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

Cross-references between entries use `**Blocks:**` /
`**Blocked by:**` / `**A2 effect:**` lines so the dependency graph
is visible inline. The "Roadmap forward" section below traces the
full graph for items in the A2 chain.

---

## Roadmap forward

Section A items participate in a dependency chain anchored by
**A2** (multi-agent decomposition of source-prep + Phase I). The
graph below shows what blocks what, and what A2 retires or absorbs
on landing. Cross-reference lines on individual items name their
position in the graph.

**Tier 0 — A2 prerequisites (must resolve first):**

- **A3** — quote-section redesign

A3 is the sole remaining Tier-0 prerequisite. (C35 was reframed to an
accuracy-check investigation — page-anchored locations stay — so it does
not sit in the A2 chain.)

**Tier 1 — A2 sub-task (scoped after A2's agent decomposition is
settled; implementation co-lands with A2):**

- **A4** — per-phase validator dispatch

**Tier 2 — A2 implementation:**

- **A2** — multi-agent decomposition of source-prep + Phase I

---

## A. Priority sequence

Items with ordering or coupling constraints.

### A2 — Multi-agent decomposition of source-prep + Phase I

**Proposal framing.** Today the contributor is the synchronization
layer between every stage of node construction — source URL →
archived file → extracted text → quote candidates → artifact prose
→ node body → cross-references → validation. Slug consistency is
contributor-enforced across multiple tools, load-bearing-ness is
contributor-judged against primary sources, quote organization and
cross-reference completeness and build-step ordering all flow
through the same single contributor mind. This proposal decomposes
that work into specialized agent stages with mechanical handoff
between them.

**Proposed pipeline.**

1. **Investigator agent** — given a target node, produces a list of
   candidate primary sources and a per-source one-line summary of
   what each source contains. No archival yet; the output is the
   source plan.
2. **Verifier agent** — reads each candidate source, confirms it is
   genuinely load-bearing to the target node's investigation (not
   incidental, not duplicate), runs `scripts/tools/manifest.py add`
   to archive the confirmed sources, and emits a handoff stub
   recording its decision.
3. **Marker agent** — runs once per archived source, identifies the
   load-bearing spans inside each, and emits structured
   quote-candidate stubs (text + source location + significance) for
   the manager stage to consume.
4. **Manager agent** — consumes per-source marker output, decides
   which quote candidates land in the node and how they're
   organized. The quote-section structure itself may need redesign
   as part of this work (see Quote-section sub-question below).
5. **Meta-linker agent** — populates remaining cross-reference
   surfaces (`relationships`, `affiliations`, `timeline` cross-refs)
   once the quote layer is settled.
6. **Builder agent** — runs `build-from-research.py` +
   `validate.py` + `review-coverage.py`, resolves or logs
   validation findings.

Each agent emits a **handoff stub** — a small temp artifact
recording who-did-what-why and what the next agent inherits. Stubs
are debugging surfaces, not load-bearing data; they exist so a
failure mid-pipeline can be traced back to the agent that produced
the upstream artifact.

**Quote-section sub-question.** The current node-body quote section
may need to be reorganized to be less clunky — *without* losing
verbatim quotes (see **A3**, which reframes this as grouping quotes by
load-bearing statement with confirm/contradict cross-refs, not
compressing them to source-node pointers). Separable structural
decision, tracked in its own BACKLOG entry (A3).

**Surfaces an investigation has to walk.**

- `prompts/build.md` — the canonical Phase I/II/III walkthrough the
  multi-agent decomposition replaces or extends.
- `scripts/build/` — the existing scaffold / extract /
  build-from-research / validate / review-coverage tools each
  proposed agent invokes.
- `scripts/tools/manifest.py` — the archival entry point; its dedup
  semantics shape the verifier-agent contract.
- `meta/schema.yaml` and `meta/schema-research-artifact.yaml` — the
  data contracts each agent reads or writes.
- `meta/conventions.md` — the source-read-first rule, the
  synthesis-confirmation invariant, the speaker-attribution rule,
  the quotes-by-not-about discipline.

**Settled decomposition (2026-05-20).** Five agents, extending the
existing `prompts/build.md` bounded-task pattern (T2/T4/T5):

1. **Scout** (investigator + verifier, COLLAPSED — a URL-only
   investigator violates source-read-first, so the read lives with the
   archival). Reads candidate sources directly, confirms load-bearing /
   non-duplicate, archives (`manifest.py add` → scaffold →
   `extract-source.py`).
2. **Marker** — per source, reads directly; emits verbatim quote
   candidates + a proposed `claim_group` label per candidate (advisory).
3. **Manager** — consumes Marker output across all sources; clusters by
   claim, derives the canonical/pointer split via `corroborated_by`
   (this is where **A3** lives — its shape is now shipped), writes
   free-prose. May read sources for judgment but MUST NOT introduce a
   quote outside the Marker phase.
4. **Meta-linker** — cross-ref surfaces (relationships / affiliations /
   timeline / program_involvement; naming_quirks / rumors).
5. **Builder** — `build-from-research.py` → `validate.py` /
   `associate.py` → `review-coverage.py`; its full pass is the global
   consistency check.

**Resolved design decisions.** (1) Investigator+verifier collapse into
Scout. (2) Handoff stubs live at `/tmp/handoff-{slug}-{agent}.yaml`,
mirroring the `/tmp/scratch-{slug}-N.txt` convention — debugging
surfaces, not git-tracked. (3) Quote-section redesign = A3, shipped
(`claim_group` grouping + rendered `corroborated_by` pointers). (4)
Agent-boundary invariant: *no agent may introduce a verbatim quote
outside the Marker phase*, so the verbatim check always fires at one
known boundary; a defect surfaces at the phase that produced it and is
re-driven by re-running that agent (never by editing the node body).

**Staged implementation.**
- **1 — A3 data-model + person renderer (DONE 2026-05-20, proven on
  Grusch).** A2's Tier-0 unblocker; see the A3 entry.
- **2 — formalize the 5 agents as bounded tasks in `prompts/build.md`
  (DONE 2026-05-20).** Added "The multi-agent pipeline (A2)" section
  documenting Scout/Marker/Manager/Meta-linker/Builder (I/O, source-read
  discipline, phase mapping), the `/tmp/handoff-{slug}-{agent}.yaml`
  stub format, and the agent-boundary invariant; `claim_group` added to
  the T2 field list. No new code.
- **3** — A4 per-phase validator dispatch: a `PHASE` constant per check
  module + `validate.py --phase {scout|marker|manager|meta-linker|
  builder}` filtering the existing `_ARTIFACT_CHECKS`/`_NODE_CHECKS`;
  Builder's flagless run = full pass.
- **4** — Marker+Manager as real agent invocations producing `/tmp`
  stubs.
- **5** — Scout + Meta-linker + Builder; full pipeline.

**Blocks:** none currently open.
**Blocked by:** A4 (increment 3) for the full agent-boundary mechanics;
A3 (increment 1) is shipped.

---

### A3 — Quote-section redesign (group person Statements by claim)

**Design settled + machinery shipped 2026-05-20 (proven on Grusch).**
Scope was narrowed during design: this is purely ORGANIZATION of a
person's own statements, with NO contradiction subsystem. Group a
person node's quotes by **claim/topic** (what the statement is *about*)
instead of the flat chronological `## Statements → Direct/Other` stream;
where the same claim is attested across multiple of that person's own
sources, render **one verbatim quote + compact "Also attested" pointers**
to the other attestations. Self-contradictions ("I did" / "I didn't")
sit in the same group as separate full statements — no marker.
Cross-entity contradictions stay on finding nodes (the entity↔finding
directional contract is untouched — A3 introduces no `/findings/` links
and no `❌`/`⚠`).

**Data model (shipped):**
- `claim_group` — NEW free-text grouping key on `quote_entry`
  (structurally like `category`; prose-drift-exempt; person-only). One
  `### {claim_group}` heading per group.
- `corroborated_by` — EXISTING lifecycle field, now *rendered* on person
  claim-grouped quotes: a quote pointed at by another group member's
  `corroborated_by` renders as a compact source+location pointer, not a
  full duplicate block. The `canonical` flag from the design draft was
  dropped as redundant — primary-vs-pointer is *derived* (a quote in
  some group-member's `corroborated_by` is the pointer; everything else
  is a primary).
- Verbatim integrity preserved: every quote (primary and pointer) keeps
  full `text` + `source` and is still verbatim-checked. No compression
  to bare pointers.

**Shipped surfaces:** `quote_entry.claim_group` + the rendered
`corroborated_by` (`meta/schema-research-artifact.yaml`); the grouped
`render_statements` path with a backward-compatible flat fallback
(`scripts/build/renderers/person.py`); `claim_group`/`corroborated_by`
integrity checks (`scripts/checks/quotes.py`); pointer-quote coverage
exemption (`scripts/checks/coverage.py`); `grouped_split_ok` on the
person Statements section rule (`meta/schema.yaml` + `section_rules.py`).
Grusch: 165 quotes → 26 claim groups, 19 cross-source duplicates
collapsed to pointers.

**Remaining (incremental, one node per session):** migrate the other
14 person nodes to `claim_group`. They render unchanged until migrated —
a person artifact with no `claim_group` renders the legacy flat
Direct/Other split (the fallback is the backward-compat guarantee).

**Blocks:** A2 — RESOLVED. The Manager agent's contract (how it
organizes quotes into the node) now has a concrete shape to target.
**Blocked by:** none.

---

### A4 — Per-phase validator dispatch (sub-task of A2)

**Proposal framing.** Today `scripts/build/validate.py` runs ~60
check modules in `scripts/checks/` as a single end-of-build pass.
Under A2's multi-agent decomposition, each agent emits a phase
boundary where a defined subset of checks reads the artifact
state that agent just wrote. Per-phase dispatch makes the
validator clustering match the agent boundaries — and the
per-phase validation output IS each agent's handoff stub.

**Natural clustering** (mapped to A2 agent boundaries):

- **Always at the top** (pre-flight on every phase invocation):
  `frontmatter_parse`, `frontmatter_required`, `artifact_parse`,
  `artifact_top_level`, `schema_version_compat`,
  `yaml_colon_space`, `yaml_hash_truncation`, `id_path_match`.
- **After verifier** (source archival): `manifest_parse`,
  `manifest_value_enums`, `manifest_archive_status`,
  `manifest_checksums`, `manifest_checksum_at_extraction`,
  `manifest_extraction_type`, `manifest_artifact_shape`.
- **After marker** (quote extraction): `verbatim_quotes`,
  `quotes`, `speakers`, `speaker_baseline_consistency`.
- **After manager** (free-prose synthesis): `prose_drift`,
  `description_token_drift`, `top_scope_activity`,
  `corroboration_items`, `vouching_chain`, `hypotheses`,
  `open_questions`, `naming_quirks`.
- **After meta-linker** (cross-references): `relationships`,
  `affiliations`,
  `key_personnel`, `timeline`, `chronological_tables`,
  `org_relationships`, `location_relationships`,
  `program_involvement`, `ownership_timeline`, `participants`,
  `cross_refs`, `closure_path`, `iff_section`.
- **After builder** (render-time): `link_resolution`,
  `required_sections`, `section_rules`, `cited_findings`,
  `contracts`, `contradictions`, `coverage`,
  `table_cell_word_budget`, `boundary`, `phase_iii_inputs`,
  `does_not_establish`, `establishes`.

The clustering above is illustrative; the implementation has to
classify every check module by which artifact field it reads,
which may surface checks that don't cleanly belong to one phase.

**Open design questions before implementation.**

1. **CLI surface.** `validate.py --phase {verifier|marker|manager|
   meta-linker|builder}` flags, or per-phase invocations stay
   full-pass with each agent filtering by its own checklist?
2. **Phase-not-yet-reached handling.** If marker has run but
   manager hasn't, and `--phase manager` is invoked, does it skip
   silently (agent isn't there yet) or error (you ran it out of
   sequence)?
3. **Final-pass guarantee.** Even with per-phase dispatch, a final
   full-pass remains valuable as the global consistency check.
   Does the builder agent's final run BE the full pass, or is
   full-pass a separate contributor-invoked step?
4. **Re-run discipline.** When an upstream agent re-runs (e.g.,
   manager edits prose after meta-linker has already populated
   cross-refs), do downstream phases auto-invalidate or does the
   contributor manually re-trigger them?

**Surfaces an investigation has to walk.**

- `scripts/build/validate.py` — current `_NODE_CHECKS` dispatch.
- `scripts/build/validate-research.py` — current
  `_ARTIFACT_CHECKS` dispatch.
- `scripts/checks/` — every per-check module (each needs
  classification by which artifact field it reads).

**Blocks:** A2 (the agent-chain handoff stubs ARE the per-phase
validator outputs; without per-phase dispatch, A2's agent
boundaries have no mechanical verification).
**Blocked by:** A2's agent list needs to be settled before the
check-to-agent mapping can be finalized. Not blocked by A2
implementation.

---

## B. Parallel batch (renderer pass)

Items that touch the renderer and naturally batch into a single
polish pass — bundling reduces churn vs. shipping each as a
separate touch.

---

## C. Anytime (no dependencies)

Items with no upstream blockers; safe to pick up at any point in
any session. Per the preamble, this is the default-focus tier:
C work doesn't risk half-baked implementations.

### C35 — Verify page-anchored location refs are accurate

**Swept 2026-05-20.** All 502 PDF-sourced page-anchored
`source.location` refs across `meta/research/*.yaml` were checked
against their archived source: locate the quote in the `pdftotext`
extract, map its `\f`-delimited physical page to the document's PRINTED
page number, compare to the stated `p. N`. Finding: refs anchor to the
**printed document page number** (confirmed — e.g. 203 sit at a constant
front-matter offset where the printed footer/header digit equals the
stated page), and they are accurate corpus-wide. Four errors found and
corrected:

- `ryan-graves` q12 / `2023-07-26-house-graves` q22: `p. 9-24` → `p. 24`
  (over-range; the Vandenberg quote sits solely on printed p. 24).
- `aaro` q35: `p. 5` → `p. 12` (the GTRI/GREMLIN sentence is on printed
  p. 12, not 5).
- `uaptf` q18 + relationship or9: `p.2` → `p.4`.
- `uaptf` q6: `p.3` → `p.2`.

**Residual (3 refs) — page component not mechanically verifiable; the
§/¶ anchor is authoritative and keeps each navigable:**

- `pentagon-uapda-revisions-2023-11` q4 (`p. 5, §9003(13)`) and q11
  (`p. 25, §9010(a)`): the redlined-bill draft carries no page numbers
  in its text layer, so `pdftotext` physical pages don't map to the
  contributor's page frame. Content verified present at the cited
  sections.
- `stanford-research-institute` q13 (`p. 22`): the CIA "SRI Studies in
  Remote Viewing" page is marked `B-2` (appendix numbering); whether
  `p. 22` (compilation-sequential) or `p. B-2` is the right form needs a
  convention call.

**Learnings for any future sweep / tooling:** an `N-M` page can be a
chapter-page form (`3-12` = ch. 3 p. 12 — `stanford-research-institute`
q21, confirmed correct), not always a range; appendix pages use the
`B-2` form; range refs must be parsed as `[start, end]` (the quote may
sit on the end page).

**Blocks:** none.
**Blocked by:** none (residual needs the original rendering / a
convention call on appendix + chapter page forms).
