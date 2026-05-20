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

Section A is a dependency chain anchored by **A2** (multi-agent
decomposition of source-prep + Phase I). The prerequisites have landed;
what remains is A2's own staged implementation (see the A2 entry).

- **Tier 0 — A3** (quote-section redesign): **shipped** (A2 increment 1)
  — `claim_group` grouping + rendered `corroborated_by` pointers, proven
  on Grusch. (C35 was reframed to an accuracy-check investigation, so it
  does not sit in the A2 chain.)
- **Tier 1 — A4** (per-phase validator dispatch): **shipped** (A2
  increment 3) — central phase map + `--phase` on validate.py /
  validate-research.py.
- **Tier 2 — A2** (the decomposition itself): in progress — increments
  1–3 done (A3, agent docs, A4); increments 4–5 (Marker+Manager, then
  Scout/Meta-linker/Builder as real agent invocations) remain.

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
- **3 — A4 per-phase validator dispatch (DONE 2026-05-20).** A central
  phase map (`scripts/checks/_phases.py`) classifies all 67 checks into
  preflight / scout / marker / manager / meta-linker / builder; `--phase`
  on `validate.py` + `validate-research.py` filters their dispatch
  (preflight always runs; unlisted → builder; unflagged = full pass, so
  `--phase` only ever narrows). Chose the central map over a per-module
  `PHASE` constant — routing is the orchestrator layer's concern per
  `checks/__init__.py` ("the dispatch lists are the routing source of
  truth"), and one reviewable map beats 67 scattered constants.
  review-coverage stays the unflagged builder pass (its checks are all
  builder/cross-layer).
- **4 — Marker + Manager as launchable agent invocations (DONE
  2026-05-20).** Shipped paste-ready subagent prompts
  `prompts/agent-marker.md` (per-source verbatim quote extraction +
  proposed `claim_group`) and `prompts/agent-manager.md` (cross-source
  `claim_group` clustering + `corroborated_by` de-dup + free-prose), each
  specifying its `/tmp/handoff-{slug}-{agent}.yaml` stub I/O and pinned to
  `--phase {marker,manager}` for scoped validation. The Manager was
  dogfooded in increment 1 (the Grusch clustering). Registered in
  `prompts/README.md`; build.md A2 section cross-refs them. Real runtime
  invocation happens on the next node build / `claim_group` migration.
- **5 — Scout + Meta-linker + Builder as launchable agents + full-
  pipeline orchestration doc (DONE 2026-05-20).** Shipped
  `prompts/agent-scout.md` (find / confirm / archive / scaffold /
  extract), `prompts/agent-meta-linker.md` (cross-refs + naming_quirks
  T4 + rumors T5), `prompts/agent-builder.md` (render + full-pass
  validate + Phase III; routes failures to the owning agent by `--phase`).
  build.md A2 section gained a "Running the full pipeline" recipe
  chaining all five agents with per-stage `--phase` checkpoints; all five
  registered in `prompts/README.md`. **The first live end-to-end run is a
  user-directed node build** — per `CLAUDE.md`, target + scope come from
  the user and sources must be real + archived, so the pipeline is not
  exercised on a fabricated target here.

**Blocks:** none.
**Blocked by:** none. The A2 decomposition is **complete as a launchable,
documented pipeline** (all five agents + A3 quote shape + `--phase`
per-stage validation). What remains is operational, not structural:
exercise it on the next user-directed node build, and migrate the
remaining 14 person nodes to `claim_group` one per session.

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

### C40 — Migrate the remaining person nodes to `claim_group`

A3 (claim-group quote organization) shipped 2026-05-20 with the machinery
+ Grusch as the proof. The other person nodes still render the legacy
flat `## Statements → Direct / Other` stream (the renderer's
backward-compatible fallback when no quote carries `claim_group`).
Migrate them a few per session: launch the Manager
(`prompts/agent-manager.md`) to cluster a node's existing quotes into
`claim_group`s and wire `corroborated_by` cross-source de-dup pointers,
apply by field-only insertion (never touch quote `text` / `source`),
regenerate, validate. Eyewitness nodes are safe (the grouped renderer
marks first-hand observations inline since `1f3669a`).

**Progress (15 person nodes):** done (4) — `david-grusch`,
`david-fravor`, `luis-elizondo`, `james-ryder` (the latter three migrated
via the Manager subagent per `prompts/agent-manager.md` — first real
exercise of that prompt on existing nodes; `david-fravor` confirmed the
inline `_Direct observation._` marker renders on a real eyewitness).
Remaining (11): alex-dietrich, hal-puthoff, james-lacatski, karl-nell,
kit-green, ronald-moultrie, russell-targ, ryan-graves, sean-kirkpatrick,
sue-gough, uri-geller.

**Blocks:** none.
**Blocked by:** none (A3 machinery shipped).

### C41 — Exercise the A2 pipeline end-to-end on a real node build

The five-agent build pipeline (Scout → Marker → Manager → Meta-linker →
Builder) is complete as launchable prompts + per-phase validation (A2
increments 1–5), but has never been run *whole* on one node — each stage
is validated piecewise, not the chain. The first live run is a
**user-directed** node build (per `CLAUDE.md`, target + scope come from
the user and sources must be real + archived; the pipeline is not
exercised on a fabricated target). On the next directed build, launch
each agent in order with a human checkpoint + `--phase` validation
between stages (`prompts/build.md` "Running the full pipeline"), capture
the `/tmp/handoff-{slug}-{agent}.yaml` stubs, and surface any
handoff-boundary friction the piecewise validation missed.

**Blocks:** none.
**Blocked by:** a user-directed build target (scope + real, archivable
sources) — opportunistic, taken on the next node build.

### C42 — Validate the per-phase check classifications

A2 increment 3 (`--phase`) classifies all 67 checks into
preflight / scout / marker / manager / meta-linker / builder in
`scripts/checks/_phases.py`. The map is best-fit, not exhaustively
litigated — low-stakes today because the full pass is unaffected and
`--phase` only narrows (unlisted checks default to `builder`). But once
agents consume `--phase` for real (C41), a mis-classified check gives an
agent wrong scoped feedback (a missed check, or an irrelevant fire).
Validate the map against real agent runs: for each phase confirm
`--phase X` runs exactly the checks that read the artifact state agent X
produced, and re-home any check whose inputs come from a later phase.

**Blocks:** none.
**Blocked by:** none (best validated alongside C41's first live run).
