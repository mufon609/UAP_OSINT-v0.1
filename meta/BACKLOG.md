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

Cross-references between entries use `**Blocks:**` /
`**Blocked by:**` / `**A2 effect:**` lines so the dependency graph
is visible inline. The "Roadmap forward" section below traces the
full graph for items in the A2 chain.

---

## Roadmap forward

Section A is a dependency chain: **A2** (multi-agent decomposition of
source-prep + Phase I) shipped, and **A5** now expands its topology
(agent topology + per-agent check bundles). What remains is A5's own
staged implementation (see the A5 entry).

- **Tier 0 — A3** (quote-section redesign): **shipped** (A2 increment 1)
  — `claim_group` grouping + rendered `corroborated_by` pointers, proven
  on Grusch. (C35 was reframed to an accuracy-check investigation, so it
  does not sit in the A2 chain.)
- **Tier 1 — A4** (per-phase validator dispatch): **shipped** (A2
  increment 3) — central phase map + `--phase` on validate.py /
  validate-research.py.
- **Tier 2 — A2** (the decomposition itself): all five increments
  shipped — A3 (1), agent docs (2), A4 `--phase` (3), Marker+Manager
  prompts (4), Scout/Meta-linker/Builder prompts (5). The pipeline is
  complete as launchable prompts + per-phase validation.
- **Tier 3 — A5** (agent topology): supersedes A2's five-agent chain
  with a seven-role topology + per-agent check bundles. inc-1 (`_phases.py`
  re-map, resolved/retired C42), inc-2 (topology doc), and inc-3 (new
  prompts; the five A2 prompts deleted) are shipped; inc-4 (first live run
  on a user-directed build) remains.

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
exercise it on the next user-directed node build (now A5-inc-4, since A5
supersedes this topology). All 15 person nodes are now migrated to
`claim_group` (C40 — done 2026-05-20).
**A5 effect:** A5 supersedes this topology (seven roles + per-agent check
bundles) while inheriting its invariants (handoff stubs, agent-boundary
invariant, A3 shape). See A5.

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

**Migration complete (2026-05-20):** all 15 person nodes are migrated to
`claim_group` (C40, done). The renderer's flat-fallback path stays for
any future person node that hasn't yet been grouped — a person artifact
with no `claim_group` renders the legacy Direct/Other split unchanged.

**Blocks:** A2 — RESOLVED. The Manager agent's contract (how it
organizes quotes into the node) now has a concrete shape to target.
**Blocked by:** none.

---

### A5 — Agent topology (expanded pipeline + per-phase/per-agent check bundles)

**Supersedes A2's topology; inherits its invariants.** A2 settled a
five-agent chain (Scout → Marker → Manager → Meta-linker → Builder) with
per-phase validation. A5 expands it to a seven-role topology for two goals
A2 left coarse: (a) **instant per-agent feedback** — each agent validates
only what it just produced — and (b) **no monolithic check pass**. Design
home: `prompts/topology.md` (inc-2).

**The seven roles (the user-directed workflow).**

0. **Orchestrator** — kicks off + sequences agents, passes handoff stubs,
   takes the user's scope/target. New; A2's session was the orchestrator.
   NB: NOT A2's "Manager" — that word is retired from the agent vocabulary
   to kill the clash; A2-Manager's quote-organization work moves into role 5.
1. **Internal Investigator** — surveys in-repo nodes/sources linked to the
   build; re-extracts already-archived sources the build can reuse. New —
   A2's Scout only looked outward.
2. **External Investigator** — fills gaps: finds missing load-bearing
   content, reads candidate CONTENT to confirm load-bearing (not URL-only),
   queues exact deep URLs for archiving. ≈ A2 Scout's investigator half +
   `prompts/web-claude-investigator.md` as upstream leads.
3. **Archive** — archives the queued sources (`manifest.py add` + Wayback),
   extracts new sources, keeps the manifest healthy. ≈ A2 Scout's
   verifier/archival half.
4. **Worker** — grabs verbatim quotes + advisory `claim_group` + cross-ref
   candidates; one generic prompt parameterized by `worker_kind`
   (paginated-PDF / HTML / caption-transcript / FOIA-`.txt`), all sharing
   the `extract` phase. ≈ A2 Marker, generalized.
5. **Build Agent (+ Error Agent)** — organizes quotes (`claim_group` +
   `corroborated_by`), writes free-prose, normalizes
   cross-refs/naming_quirks/rumors, tests, then renders only if error-free;
   routes any failure to an Error Agent that maps the failing check → owning
   role via the `--phase` table and recommends a DATA fix (never a node-body
   edit). ≈ A2 Manager + Meta-linker + Builder + a new error-triage role.
6. **Audit** — global health pass + adjacent-node propagation: finds linked
   nodes that should carry the new material; that path SKIPS role 2 (material
   already in hand — the tightening loop). ≈ `prompts/audit.md` + the
   cross-layer review checks + propagation that has no home today.

**Source-read-first under the 2↔3 split.** A2 collapsed
investigator+verifier into Scout because a URL-only investigator violates
source-read-first. The 2/3 split is safe: role 2 reads source CONTENT before
judging load-bearing-ness (soft enforcement), and the hard mechanical
guarantee never moved — `verbatim_quotes` matches every quote against the
archived/extracted file at the single `extract` boundary, and no agent may
introduce a quote outside it.

**Per-phase/per-agent check bundles (the load-bearing surface; resolves
C42).** `scripts/checks/_phases.py` is re-mapped so each `--phase` token is
named for the role whose output it validates: `archive` (3) / `extract` (4) /
`organize` (5) / `link` (5) / `render` (5/6); preflight always-on; roles
0/1/2 produce no gated state. The pre-A5 names (scout / marker / manager /
meta-linker / builder) remain accepted as aliases. C42's substance is
resolved by re-homing four mis-classified checks to the LATEST phase that
supplies their inputs: `chronological_tables`, `iff_section`,
`finding_source_in_entity_node` → `render` (they read the rendered node / the
full section set / the global cross-artifact index); `prose_drift` → `link`
(it also scans link-phase synthesis `.note`/`.attestation` fields). Confirmed
in passing: the two `*_no_*_refs` directional checks are single-artifact
recursive walks, NOT global — they stay at `link`. The genuinely
full-pass-only checks (`link_resolution`, `boundary`, `coverage`,
`description_token_drift`, `finding_source_in_entity_node`,
`governance_files`) keep the global consistency guarantee at role 5's final
render run + role 6's audit.

**Staged implementation.**
- **1 — `_phases.py` re-map + validator `--phase` plumbing (DONE
  2026-05-20).** Renamed phases + back-compat aliases
  (`PHASE_CHOICES`/`canonical_phase`); the four C42 re-homes; `--phase` on
  `review-coverage.py` (render-only short-circuit). Full pass unchanged
  (`--phase` only narrows); all gates green.
- **2 — Topology doc + naming.** `prompts/topology.md` (vocabulary,
  A2→role reconciliation, source-read-first invariant, stub schemas, branch
  flows); cross-ref from `prompts/build.md`; retire "Manager" from the agent
  vocabulary.
- **3 — New launch prompts.** `agent-{orchestrator,internal-investigator,
  external-investigator,archive,worker,build,error}.md`; extend `audit.md`
  with role-6 propagation; register in `prompts/README.md`; delete the five
  superseded A2 `agent-*.md` (they strand no scripts — every script they
  named is also named in a new role prompt).
- **4 — Exercise end-to-end (first live run).** The seven-role pipeline is
  complete as launchable prompts + per-phase validation but has never been
  run *whole* on one node. The first run is a user-directed build (per
  `CLAUDE.md`, target + scope from the user, sources real + archived — not a
  fabricated target); launch each role in order with a human checkpoint +
  `--phase` validation between stages (`prompts/topology.md`), capture the
  `/tmp/handoff-{slug}-*.yaml` stubs, and prove the worker variants, the
  tightening loop, and Error-Agent routing; confirm each `--phase X` fires
  exactly the checks reading state role X produced.
- **5 (deferred) — `prose_drift` two-phase split** (`prose_drift_toplevel` @
  organize + `prose_drift_notes` @ link) if one-phase-late surfacing of
  top-level drift proves annoying in practice.

**Blocks:** none.
**Blocked by:** inc-4 needs a user-directed build target — opportunistic,
taken on the next node build.
**Inherits from A2:** the handoff-stub convention
(`/tmp/handoff-{slug}-{agent}.yaml`), the agent-boundary invariant, and the
A3 `claim_group`/`corroborated_by` shape (shipped across all 15 person nodes)
— A5 must not regress these.

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

### C43 — Mechanical check for source-anchored quote location forms

`quotes.py` validates that a quote's `source.location` is *present*, but
nothing validates its *form* — so extraction-anchored refs (`lines N-M`,
`line N`), which go stale when an extract is regenerated, can still slip in.
`scripts/tools/normalize-locations.py` is the only guard today, and it is a
manual diagnostic nobody is scheduled to run (the same bandaid pattern the
A5 audit flagged). Convert the guard to a mechanical check: flag a
`source.location` that begins with `line`/`lines` + a number (allowing the
explicit `lines N-M of the extract` form) per `meta/conventions.md` "Quote
location refs: source-anchored, not extraction-anchored". Map it to the
`extract` phase (role 4 produces the quotes). The corpus is currently clean
(C35 sweep), so the check passes on arrival and prevents regression;
`normalize-locations.py` then reduces to a fix-aid (it reports where a
flagged quote's text lives in the extract).

**Blocks:** none.
**Blocked by:** none.

### C44 — `manifest.py add --dry-run` for role-2 lead self-check

Role 2 (External Investigator) produces a URL queue but has no self-check;
its leads are validated only when role 3 archives them (`manifest.py add`).
Add `--dry-run` to `manifest.py add`: run the URL / path / format /
uniqueness validation and report what *would* change without writing the
manifest, so role 2 can validate a lead before handoff — the per-agent
feedback every other role in `prompts/topology.md` already has. Reuses the
one authoritative archival tool (no second validation surface). Then point
role 2's feedback line in `prompts/topology.md` at it.

**Blocks:** none.
**Blocked by:** none.
