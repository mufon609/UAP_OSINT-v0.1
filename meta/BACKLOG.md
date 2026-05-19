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

**Tier 0 — A2 prerequisites (must resolve first; can land
independently in any order):**

- **C29** — manifest URL ↔ artifacts model
- **C33** — verbatim-quote normalization architecture
- **A3** — quote-section redesign

**Tier 1 — A2 sub-task (scoped after A2's agent decomposition is
settled; implementation co-lands with A2):**

- **A4** — per-phase validator dispatch

**Tier 2 — A2 implementation:**

- **A2** — multi-agent decomposition of source-prep + Phase I

**Retired or reduced by A2 on landing:**

- **C30** — source-prep orchestrator (fully retired; can ship as
  interim orchestrator if A2 stays roadmap-scoped)
- **C5** — auto-generate per-type section list in prompts/build.md
  (retired if A2 replaces the monolithic narrative with per-agent
  prompts)
- **C27** — reader-visibility discipline (workflow half absorbed by
  builder agent; schema-comment half stays independent)
- **C28** — interview-node entities_referenced discipline
  (mechanically absorbed by meta-linker; convention text in
  meta/conventions.md still needed as the agent's source)
- **C31** — preflight discipline audit (reduced; manual-invocation
  case stays for tools called outside the agent chain)
- **C32** — research-scaffold placeholder shape (narrows to
  non-marker-populated fields)

**Independent of the A2 chain:**

- **A1** — entities_referenced[] body rendering (orthogonal
  renderer decision)
- **C34** — schema↔CLI parity check (orthogonal mechanism question;
  blocked by C29 for its only known concrete drift instance)

---

## A. Priority sequence

Items with ordering or coupling constraints.

### A1 — Investigation: should `entities_referenced[]` render in the body?

**Open design question, not a tractable fix.** Every other structured
artifact field renders to the body (`description`, `background`,
`timeline`, `key_personnel`, `relationships`, `affiliations`,
`corroboration_items`, `quotes`), but `entities_referenced[]` is the
lone exception. That break in the pattern means cross-references
declared there are invisible to the broken-link signal and to human
readers, and contributors have to duplicate references across body
wraps and `entities_referenced[]` to make new build candidates
discoverable.

**What the investigation needs to answer before any change:**

1. **What's the design history?** Why was `entities_referenced[]`
   built as a YAML-only declaration when every other structured
   field renders? Was the design intent agent-layer-only? Was it
   "supplementary to body wraps, never primary"? Reading
   `meta/conventions.md`, the renderer modules under
   `scripts/build/renderers/`, and `AGENT.md` for original framing
   is the first step.

2. **What's the actual scope?** How many `entities_referenced[]`
   entries exist across the corpus? What fraction already have
   a matching body wrap (would be no-op to render)? What fraction
   is unique to `entities_referenced[]` (would surface for the
   first time)? Mechanical answer via a one-pass script over
   `meta/research/*.yaml`.

3. **What does each entry look like?** Are they uniform "real
   cross-references worth surfacing," or is there a mix —
   load-bearing references, incidental-mentions-in-quoted-source,
   placeholder declarations that haven't earned a body wrap?
   Render-everything risks surfacing the incidental-mentions
   class to readers without editorial framing.

4. **What does AGENT.md / the query layer consume?** If a query
   agent walks `entities_referenced[]` today, does it depend on
   the field being structured-only? Would rendering also into
   the body create a duplication the query layer would have to
   reconcile?

5. **What's the body-size impact?** Some artifacts have 40+
   `entities_referenced[]` entries. If all unique-to-the-field
   entries render in `## Associated Nodes`, what does the rendered
   page length look like? Is there a reader-experience cost?

**Candidate approaches the investigation may surface** (none
recommended; listed for completeness):

- Render in `## Associated Nodes` — extend `scripts/build/associate.py`
  to also include `wrap_path` values from `entities_referenced[]`
  not already covered by a body wrap
- Validator-only crawl — make `validate.py`'s broken-link detector
  consume `entities_referenced[]` directly from artifacts; no
  renderer / reader-visible change
- Schema retire — if entries are mostly redundant with body wraps,
  retire `entities_referenced[]` entirely and document the body-wrap
  convention as canonical
- Hybrid — render only entries whose `context_summary` indicates
  load-bearing cross-reference; keep "incidental mention" entries
  YAML-only (would require classifying entries)

The investigation may conclude that the current design is
load-bearing (and the bandaid is the right cost), or that one
of these approaches retires the duplication. Either way, the
investigation has to happen before any code change.

**Out of scope for the investigation:** retiring
`entities_referenced[]` without preserving the `context_summary`
+ quote-backlinks metadata. That metadata is consumed by the
agent / query layer per `AGENT.md`; any structural change has to
preserve or relocate it.

**Bandaid in effect:** wraps are currently placed inside timeline-
entry `event` fields alongside `entities_referenced[]` entries to
force broken-link discovery. That duplication is the workaround the
investigation exists to retire.

**Blocks:** none.
**Blocked by:** none (independent renderer decision; in Section A
because the investigation has coupling constraints across renderer,
schema, validator, and AGENT.md query-layer surfaces).

---

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
   surfaces (`entities_referenced`, `relationships`, `affiliations`,
   `timeline` cross-refs) once the quote layer is settled.
6. **Builder agent** — runs `build-from-research.py` +
   `validate.py` + `review-coverage.py`, resolves or logs
   validation findings.

Each agent emits a **handoff stub** — a small temp artifact
recording who-did-what-why and what the next agent inherits. Stubs
are debugging surfaces, not load-bearing data; they exist so a
failure mid-pipeline can be traced back to the agent that produced
the upstream artifact.

**Quote-section sub-question.** The current node-body quote section
may need to be redesigned to be less clunky. The constraints are no
info loss and no duplicate noise. A person node always points to
the source nodes anyway, so verbatim quote content remains
recoverable from the source layer even if the person-node surface
itself is leaner. This is a separable structural decision and likely
wants its own BACKLOG entry once the multi-agent decomposition is
scoped.

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

**Open design questions before implementation.**

1. **Load-bearing determination without source-read is a regression.**
   The investigator agent listing "what each source contains" cannot
   summarize from training knowledge or from the URL alone — the
   source-read-first rule applies. Either the investigator agent
   also reads each source (collapsing investigator + verifier into
   one source-read-then-archive stage), or it produces only a
   candidate list that the verifier reads and prunes against the
   archived text.
2. **Handoff-stub home.** Temp file under `/tmp/`? Sidecar YAML next
   to the research artifact? Frontmatter block on the artifact?
   Comment region inside the artifact? Each has different
   post-mortem-debuggability properties — temp files vanish on
   reboot; sidecars live with the artifact in git; in-artifact
   comments mix data with provenance.
3. **Quote-section redesign scope.** Per-quote verification blocks
   today carry source link, attribution, context, observation type,
   significance. Which fields move, which compress, and what the
   node-body rendering looks like vs. the artifact layer — open.
4. **Agent boundary discipline.** Phase II/III rebuild loops surface
   failures invisible until validation. More agents create more
   synchronization points; the proposal needs to be explicit about
   which agents read primary sources directly vs. consume upstream
   agent output, and how a defect attributable to a stage three
   agents upstream is handled when validation surfaces it.

**Out of scope until upstream structural items resolve.**

- **C29** — manifest URL ↔ artifacts model. The verifier-agent /
  `manifest.py add` contract depends on whether one URL maps to one
  entry or one URL maps to many entries.
- **C33** — verbatim-quote normalization architecture. The marker
  agent's extraction primitive depends on what counts as a
  verbatim match.
- **A3** — quote-section redesign. The manager-agent's contract
  (how it organizes quotes into the node) depends on what the
  rendered quote section looks like.
- **A4** — per-phase validator dispatch. The agent-chain handoff
  stubs ARE the per-phase validator outputs. A4 is scoped after
  A2's agent list is settled, but A2's implementation depends on
  A4 mechanics being in place.

**Candidate alternative resolutions** (listed for the decision space,
not as recommendations):

- **Status quo + tooling polish** — keep Phase I/II/III monolithic;
  retire contributor-as-glue via the C30 orchestrator (single
  slug-threaded command), C32 scaffold placeholders, C31 preflight
  discipline. Decomposes the friction without introducing agent
  boundaries.
- **Two-phase decomposition** — split source-prep from
  artifact-construction; keep artifact construction monolithic.
  Investigator + verifier + marker handle pre-Phase-I; Phase I
  onwards stays one-agent.
- **Phase-internal sub-tasks, not agents** — keep Phase I
  monolithic but formalize the investigator → verifier → marker →
  manager → meta-linker steps as a checklist with mechanical
  handoff inside `prompts/build.md`, not as separate agent
  invocations.

**Surfaced from.** Contributor observation that the same contributor
mind currently carries every coordination decision across
source-prep + Phase I + Phase II + Phase III, with no mechanical
handoff at stage boundaries.

**Blocks:** retires C30, absorbs sub-pieces of C5 / C27 / C28 / C31 / C32 on landing.
**Blocked by:** A3, A4, C29, C33.

---

### A3 — Quote-section redesign

**Open structural question.** The current node-body quote section
carries per-quote verification blocks with source link,
attribution, context, observation type, and significance. Across
the corpus this produces dense, repetitive surfaces — a person
node citing many statements becomes a long quote-block stream. The
constraint is load-bearing: every claim must trace to a verbatim
source. The question is whether the rendered surface can be leaner
without losing the evidentiary trace.

**Constraints.**

1. **No info loss.** Every quote that supports a claim must remain
   recoverable, with verbatim text + source link + attribution.
2. **No duplicate noise.** A person node citing the same source for
   five quotes shouldn't repeat the source attribution five times
   in the body. The artifact layer carries the data; the rendered
   surface is the presentation.
3. **The source node carries the canonical quote text.** A person
   node always points to the source node (document / transcript /
   media); the verbatim quote already lives there. The person node
   could carry compressed references rather than full verbatim
   repetition, since the source node is one click away.

**Candidate approaches** (listed for the decision space; none
recommended):

- **Compressed reference layout.** Person node renders a short
  attribution + significance + link to the source node's quote.
  Full verbatim text lives only in the source node. Smallest body
  surface; highest navigation cost for a reader who wants the
  quoted text inline.
- **Source-grouped layout.** Multiple quotes from the same source
  render under one attribution heading, not one per quote.
  Eliminates repetition without losing inline verbatim text.
- **Collapsible blocks.** Body renders full quote in a
  collapsible HTML detail/summary structure. Compact by default,
  expandable on demand. Breaks pure-Markdown discipline (renderer
  would need to emit raw HTML).
- **Status quo + tighter discipline.** Keep per-quote blocks;
  retire the duplicative attribution / context / observation-type
  fields where the source layer already carries them. Smallest
  structural change.

**Surfaces an investigation has to walk.**

- `scripts/build/renderers/{person,document,event,transcript}.py` —
  current quote rendering across types.
- `meta/schema-research-artifact.yaml` — per-quote required fields.
- `meta/conventions.md` "Statements as the universal evidentiary
  primitive" — the principle the section enforces.
- A representative sample of dense person nodes (e.g.,
  `karl-nell`, `david-grusch`) to see how the current surface
  reads against each candidate layout.

**Blocks:** A2 (the manager agent's contract — how it organizes
quotes into the node — depends on what the rendered quote section
looks like).
**Blocked by:** none.

**Surfaced from:** A2 proposal flagged this as a sibling
structural question. Quote-section structure is independent of the
agent-decomposition question but blocks A2 implementation.

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
  `manifest_extraction_type`.
- **After marker** (quote extraction): `verbatim_quotes`
  (artifact-side post-C4), `quotes`, `speakers`,
  `speaker_baseline_consistency`.
- **After manager** (free-prose synthesis): `prose_drift`,
  `description_token_drift`, `top_scope_activity`,
  `corroboration_items`, `vouching_chain`, `hypotheses`,
  `open_questions`, `naming_quirks`.
- **After meta-linker** (cross-references): `entities_referenced`,
  `stub_linking`, `relationships`, `affiliations`,
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

**Surfaced from:** A2 proposal — the contributor question "can
the check scripts be broken into different phases instead of a
massive last-minute call" pointed at this as the
architecturally-natural mechanism for agent handoff verification.

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

### C5 — Auto-generate the per-type section list in `prompts/build.md`

`prompts/build.md` Phase II Step 1 enumerates the per-type rendered
section list (~148 lines, `prompts/build.md:594-741`) as `## SectionName
— from artifact_field` entries — Identity, Background, `{topic_display_name}`
Relevance, Affiliations, Statements, Timeline, Relationships,
Corroboration, Credibility Notes, Associated Nodes for person/eyewitness,
and so on across every type + archetype/kind. This duplicates information
that already lives in two places:

- `meta/schema.yaml::types.{T}.required_sections` (and per-archetype /
  per-kind sub-blocks) — the canonical section list
- `scripts/build/renderers/{T}.py` — the canonical section → artifact-
  field dispatch

The duplication means the prompt drifts whenever a section is added or
renamed at the source-of-truth layers. It also still carries the literal
"UAP Relevance" / "UAP-Scope Activity" examples — accurate documentation
of *this instance's* rendered output, but a fork would need to edit the
prompt as a separate step from `prompts/fork-init.md`'s `display_name`
swap.

Fix shape: wrap the per-type section enumeration in `<!-- BUILD-SPEC-START -->`
/ `<!-- BUILD-SPEC-END -->` markers (analogous to CLAUDE.md's build-state
auto-block), and add a generator that walks schema's `required_sections`
+ per-renderer source-field mapping and emits the enumeration. The
generator routes section names through `topic_substitute()` so the
prompt's example headers always reflect the current `display_name`.
Add `build-md-spec.py --check` as a new pre-commit gate (parallel to
`build-state.py --check`).

The narrative + discipline portions of `prompts/build.md` stay hand-
written. Only the dispatch-table enumeration auto-generates.

Complementary to C4's artifact-side verbatim-quote move; both reduce
duplication between governance docs and source-of-truth layers
(schema / artifact). Not strictly correctness-required as a one-time
fix, but closes the documentation-drift surface for forks and schema
evolution.

**A2 effect:** retired in full when A2 replaces the monolithic
`prompts/build.md` narrative with per-agent prompts. Until A2
ships, this remains a tractable standalone fix.

### C27 — Split reader-visibility discipline into audit prompt + schema comments

The rule "verify a fix actually surfaces in the rendered node before
marking it done" mixes three concerns that need different homes:

- **Workflow discipline** — "regenerate the node and grep for the fix"
  is a step every audit/build session needs. Land it in
  `prompts/audit.md` (new file) as a numbered step in the post-fix
  verification pass. Workflow guidance belongs in prompts, not in
  free-floating memory.
- **Per-field render catalog** — which artifact fields render to the
  node body vs. stay artifact-internal. The renderer code is the
  source of truth; `meta/schema-research-artifact.yaml` is where
  per-field semantics already live. For each field that doesn't
  render, add a one-line "not rendered (artifact-only)" comment to
  that field's entry in the schema. The catalog co-locates with the
  field; no standalone prose catalog accumulates.
- **Specific incident references and dated snapshots** — git log only.
  Anywhere they accrue in repo files, delete them.

Concrete work:

1. Grep current renderer code (`scripts/build/renderers/*.py`) to
   determine which fields render and which don't, against the present
   codebase. Specifically verify `timeline[].note` and
   `quote.significance` — they were reportedly artifact-only as of an
   older snapshot; status today needs confirming.
2. For each artifact-only field, add a `# not rendered (artifact-only)`
   comment in `schema-research-artifact.yaml`.
3. Create `prompts/audit.md` (or extend an existing audit prompt) with
   the "regenerate + grep" verification step.
4. If a contributor encounters this rule's substance elsewhere
   (memory, code comment, BACKLOG note), delete it; the new homes are
   canonical.

**A2 effect:** workflow-discipline half ("regenerate + grep"
verification) absorbed by the builder agent's contract. The
schema-comment half (per-field render catalog in
`schema-research-artifact.yaml`) stays independent of A2.

### C28 — Promote interview-node entities_referenced discipline; optional audit aid

Two related pieces:

**(a) Promote the discipline into `meta/conventions.md`.** When a
person node cites long-form media appearances as primary-source
evidence (podcasts, broadcasts, panels, conference talks), each
**venue** (organization), **host / interviewer / moderator** (person),
and **transcript-to-be** (transcript node) must be registered as an
`entities_referenced[]` entry with `wrap_path` AND must appear as a
`[`/path`]` body wrap somewhere in the node (typically inside the
corresponding `timeline[].event` text). The validator's
`stub_linking` check enforces the registered→linked direction; the
inverse (named-in-prose-but-not-registered) is contributor
discipline.

Add as a new "Cross-reference contract" subsection in
`conventions.md`, near "Associated Nodes" or under the entity-layer
discussion in "Three-layer evidentiary architecture". Update the
`stub_linking.py` docstring's "see feedback memory" cross-reference
to point at the new conventions section.

**(b) Optional audit aid — `coverage-suggest`-style entity scanner.**
Build a read-only diagnostic that scans node-body prose for
capitalized terms not in `entities_referenced[]` and surfaces them at
audit time. Parallel to `scripts/tools/coverage-suggest.py` (which
catches the analogous gap on source coverage). Read-only; contributor
judges per-case. Don't promote to a validator error — capitalized-
word heuristics false-positive on "Pentagon" / "April" / proper
nouns inside quoted source / etc. Premature enforcement reintroduces
the category-tuned-threshold failure mode.

(b) is optional follow-up; (a) is the load-bearing work.

**A2 effect:** (a) the discipline is mechanically encoded by the
meta-linker agent's contract. (b) the optional audit aid retires —
the meta-linker's own check is the audit. The convention text in
`meta/conventions.md` still needs to exist as the agent's source.

### C29 — One source URL ↔ many archived artifacts: no schema model

The manifest models `(url, path, format, sha256, …)` as a flat list of
entries. Conceptually each entry is "this URL is archived at this
path." The shape doesn't acknowledge that a single source URL can
yield MULTIPLE archived artifacts of different formats — most
commonly a video file plus a transcript derived from that file's
audio (auto-caption pull, whisper transcription, contributor-
transcribed clean text). Same source, multiple archived renderings,
all needing manifest registration with their own paths and sha256s.

The current state has three uncoordinated pieces of behavior:

- **Schema** (`meta/schema.yaml::manifest_entry`) does not declare
  URL uniqueness. Each entry is independent; the list shape permits
  duplicates.
- **`scripts/tools/manifest.py::cmd_add`** enforces URL uniqueness:
  if any existing entry shares the URL, the call is a silent no-op
  regardless of whether the supplied path differs. The CLI is
  stricter than the schema.
- **`scripts/tools/manifest.py::cmd_status`** returns the first match
  on URL. If multiple entries share a URL, only the first surfaces;
  the others are invisible to status / lookup workflows.

The mismatch surfaces concretely in the video pipeline: a
`transcribe.py` run registers `(url, format=transcript)`; the
subsequent `download-video.py` run for the same URL tries to
register `(url, format=video)` and is silently rejected by
`cmd_add`. The video file lands on disk unregistered. No validator
flags this — manifest integrity checks key on `path`, not on
which-files-on-disk-have-no-entry.

A workaround pattern would be tempting (allow duplicate URLs as long
as paths differ) but ages poorly: dual-URL rows accumulate without
a schema concept of "primary artifact vs. derivation," and
downstream tooling (`cmd_status`, `cmd_usage`, `save_manifest`
ordering, the verbatim-quote check's path → URL resolution) has no
principled way to disambiguate.

**The actual decision the investigation needs to make.** Where does
the derivation relationship between artifacts live?

1. **Inside one entry.** Make URL the key and let each entry carry
   multiple archived artifacts — e.g., `artifacts: [{path, format,
   sha256, derivation_note}, …]`. One URL → one entry. The schema
   acknowledges that "the cited URL" is distinct from "the archived
   renderings of what's at that URL." Citation resolution is by URL;
   verification picks the right artifact by format.

2. **Across entries with a derivation pointer.** Permit duplicate
   URLs and add a per-entry `derived_from_path` field naming the
   parent archived artifact. The transcript entry points at its
   parent video entry; readers and tools can walk the derivation
   chain. Schema gains a new optional field; URL uniqueness is
   explicitly retired.

3. **Outside the manifest entirely.** Treat the transcript as a
   derived artifact whose "source URL" is the local video file path,
   not the original YouTube URL. The transcript's manifest entry
   carries a synthesized URL (or no URL). The original YouTube URL
   appears only on the video entry. Asymmetric but mechanically
   simple; the cost is that node citations of "the YouTube URL" no
   longer resolve to the transcript file directly.

4. **Forbid the dual-artifact pattern.** One archived artifact per
   URL, full stop. Re-derive transcripts on demand from the video
   file; never register the transcript in the manifest. Loses the
   verbatim-quote-check substring property against the registered
   transcript path.

Each option has different implications for the verbatim-quote check
(which resolves `source.path` on a quote to either a registered file
or its `.txt` sibling), for `cmd_status` / `cmd_usage` semantics, for
how nodes cite the underlying source, and for the
`transcript_provenance` field's home (per-artifact vs. per-entry).

**Investigation owes a decision on each surface before any
implementation:** the schema definition of `manifest_entry`, the
`manifest.py` commands (add / status / usage / orphans / missing),
the build-pipeline tools that call `manifest.py add` (currently
`download-video.py` and `transcribe.py`'s manual post-step), the
verbatim-quote check's path resolution, and `meta/conventions.md`
"Source preservation."

**Out of scope for the investigation.** Picking one option without
walking the other surfaces. The temptation is to soften `cmd_add`
to permit duplicate URLs (option 2 lite, without the
`derived_from_path` field) and call it a day — the BACKLOG entry
exists explicitly to prevent that path, because the cluttered-
manifest failure mode it produces would only become visible after
several more dual-artifact sources accumulate.

**Surfaced from:** the JRE #2194 Elizondo source-prep walkthrough.
`transcribe.py` ran first (auto-caption pull) and registered the URL
as `format: transcript`; the subsequent `download-video.py` run
landed the 480p mp4 on disk but `cmd_add` no-op'd the registration
attempt — visible only as a one-line `Already in manifest:` message
in tool output, easy to miss. Pipeline B continues to work because
the visual tools (`extract-frames.py`, `detect-faces.py`,
`diarize-audio.py`, `stitch-transcript.py`) read the video from
disk by path and never consult the manifest for it; the unregistered
state surfaces only when a node tries to cite the video URL.

**Blocks:** A2 (verifier-agent / `manifest.py add` contract), C34
(the only concrete schema↔CLI drift instance is the manifest
URL-uniqueness gap C29 hasn't decided).
**Blocked by:** none.

### C30 — Source-prep orchestrator: single command for the full caption + video chain

Preparing one YouTube source for a person node currently chains four
to seven discrete tool invocations across two documented workflows:

- **Caption pull** (`meta/sources-access.md` "YouTube"):
  `extract-firefox-cookies.py` → `transcribe.py --cookies -` →
  `manifest.py add ... --format transcript --transcript-provenance auto-caption`
- **Video + speaker identity** (`scripts/tools/VIDEO-PIPELINE.md`):
  `download-video.py` → `extract-frames.py anchor` →
  `detect-faces.py detect` → contributor review → `detect-faces.py register`
  (per identity, per baseline) → optional `diarize-audio.py` +
  `stitch-transcript.py`

The two workflows share three contributor-supplied parameters that
MUST agree: the source URL, the kebab-case slug used for the
transcript file (`{slug}-downloaded.md`), and the kebab-case slug
used for the video file (`{slug}.mp4`). When the slugs drift, the
slug-discovery downstream in `stitch-transcript.py` silently fails
(it looks for `sources/transcripts/{slug}-downloaded.md` and
`/tmp/diarize-{slug}/segments.csv` against the video stem). Cross-
tool slug consistency is currently contributor discipline with no
mechanical enforcement.

An orchestrator script would take a URL and an output slug and
invoke the right subset of tools in order, threading the same slug
through each, surfacing the consent gate once, and emitting a single
contributor-readable summary at the end. The investigation has to
decide:

- **Scope of the orchestrator.** Whole-pipeline (caption + video +
  diarize + frames + detect + stitch) or caption-only-with-optional-
  video-flag? The visual-baseline registration step is interactive
  (contributor identifies which crop is which person); a pure
  orchestrator can't auto-register baselines, only stop and prompt.
- **Cookies surface.** Caption pull needs Firefox cookies via
  `extract-firefox-cookies.py`; `download-video.py` uses
  `--cookies-from-browser firefox` directly. The orchestrator
  inherits both paths or unifies them.
- **Failure-mode propagation.** Each step has its own non-zero exit
  semantics. Orchestrator decides whether to abort on first failure
  or attempt the rest of the pipeline and report a per-step status
  summary.
- **Where it lives.** A new `scripts/tools/prep-source.py` is the
  most obvious home; alternatively the orchestration logic moves
  into one of the existing tools (e.g., `download-video.py` gains
  a `--with-captions` flag). The first preserves single-purpose-
  per-tool; the second avoids a new entry point.

**Surfaced from:** the JRE #2194 Elizondo source-prep walkthrough.
The walkthrough ran each step manually to evaluate the pipeline; the
slug-consistency requirement and the multi-tool consent gates
emerged as the two friction points an orchestrator would close.

**A2 effect:** fully retired when A2 ships. The verifier + marker
agents absorb the orchestration; slug consistency becomes
agent-internal. Could ship as an interim orchestrator if A2 stays
roadmap-scoped, but the work does not carry forward into A2 — the
agents replace the orchestrator rather than build on it.

### C31 — Preflight discipline audit across `scripts/tools/`

Tools that depend on environmental prerequisites (env vars, gated
model auth, browser session state, JS runtimes, network access)
currently surface those prerequisite failures at the point the tool
*uses* the prerequisite, not at the point the tool *starts*. The
gap means contributors do meaningful work (audio extraction, video
download, manifest scan, frame-extraction setup) before the
tool exits with the install hint.

The pattern isn't uniform across `scripts/tools/`. Some tools
preflight cleanly (`download-video.py`'s `preflight()` checks
yt-dlp + ffmpeg + JS runtime before the yt-dlp invocation); others
defer the check until the prerequisite is consumed; the cookie-
extraction path has its own non-uniform pattern (the canonical
multi-video shell-variable workflow prompts once per session, but
the per-tool failure modes vary).

**The actual question:** what's the standard for "prerequisite
discoverability" across `scripts/tools/`?

Candidate resolutions (none recommended; listed for completeness):

- **Universal `preflight()` discipline.** Every tool grows a
  `preflight()` function called at `main()` entry that checks
  every env var, binary, library, and external-service prerequisite
  the tool consumes anywhere in its execution. Exit non-zero with
  install hints before any side-effect runs. Most explicit; most
  invasive.
- **Shared preflight library.** A `lib/_preflight.py` module that
  tools register requirements with declaratively (`require_env(
  "HF_TOKEN")`, `require_binary("yt-dlp")`, `require_python_module(
  "pyannote.audio")`). Tools call `lib._preflight.check()` at entry.
  Less per-tool boilerplate; centralizes the install-hint vocabulary.
- **Status-quo + audit-only.** Accept that some prerequisites only
  surface deep in the call graph; the audit produces a manifest of
  "known mid-pipeline failure points" so contributors are warned at
  documentation time rather than at script-runtime time.
- **Smoke-test coverage.** Add a `scripts/tests/preflight-check.sh`
  that confirms each tool exits cleanly with the prerequisite-missing
  install hint when its prerequisites are absent. Catches regressions
  but doesn't change the architecture.

**Surfaces an investigation has to walk:** every script under
`scripts/tools/` and `scripts/build/`; `lib/_common.py` for any
shared preflight helpers; `meta/conventions.md` "Inside /scripts/"
for the landing rules; `scripts/tests/` for the smoke / help-check
patterns the preflight standard would integrate with.

**A2 effect:** agent-invocation case reduced — agents preflight on
their own behalf before invoking tools. Manual-invocation case
stays: tools called directly by contributors outside the agent
chain still want preflight discipline.

### C32 — `research-scaffold.py` should emit placeholder entries showing required shape

The current scaffold emits empty content sections (`quotes: []`,
`affiliations: []`, `entities_referenced: []`, `naming_quirks: []`,
etc.). Contributors learn the required entry shape by reading an
existing exemplar artifact (e.g., `karl-nell.yaml`) or by hitting
validation errors and inferring the shape from the error messages.

The required-entry shape is non-trivial: every list entry needs
lifecycle fields (`id`, `added_date`) plus type-specific required
fields (e.g., affiliation_entry needs `organization_path`, `role`,
`source`; quote_entry needs `text`, `source` with sub-fields;
naming_quirks_entry needs `observed`, `canonical`, `location`,
`source_path`, `resolution`). Discovering these by validation
error is high-friction: a contributor populating a fresh artifact
from-scratch can hit 100+ "missing required field" errors on
first validate, organized by entry rather than by category.

**The actual question:** how should the scaffold teach the required-
entry shape to the contributor?

Candidate resolutions:

- **Commented-out placeholder per section.** Scaffold emits one
  fully-formed placeholder entry per list field, prefixed with
  `# placeholder — replace or delete`. Contributor learns shape by
  replacing or deleting; copying-and-extending is the natural path.
  Lowest friction; small risk that contributors forget to delete
  unused placeholders.
- **Schema-driven `--help` doc.** A new `research-scaffold.py
  --explain {field}` mode that prints the required entry shape for
  any artifact field, derived from `schema-research-artifact.yaml`.
  Doesn't change the scaffold; adds discoverability surface.
- **Pre-populated from sources.** Scaffold runs against the primary
  sources passed in `--sources` and pre-extracts candidate
  entries (e.g., detected named entities → `entities_referenced[]`
  placeholders; detected dates → `timeline[]` placeholders).
  Highest value but highest implementation cost; risks bad defaults
  becoming load-bearing.
- **Status-quo + improve error grouping.** Keep the empty scaffold;
  refactor `validate-research.py`'s missing-required-field reporting
  to group by category (e.g., "12 list entries need `added_date`")
  rather than per-entry. Reduces the cognitive load of the error
  cascade without changing the scaffold.

**Surfaces an investigation has to walk:** `scripts/build/research-
scaffold.py`; `meta/schema-research-artifact.yaml` (the
per-entry shape specs); `scripts/checks/` (the validators that
detect missing fields); `prompts/build.md` Phase I Step 1
(how the scaffold integrates with the build prompt).

**A2 effect:** narrows to non-marker-populated fields. The marker
agent fills `quotes[]` (and possibly `timeline[]`) from sources;
those fields no longer need placeholder teaching. Free-prose
fields (`description`, `background`, `top_relevance`,
`credibility_notes`) and structured-data lists not auto-populated
(`affiliations`, `relationships`) still want scaffold placeholders.

### C33 — Verbatim-quote normalization: principled refactor vs. reactive patches

The `normalize_for_compare` helper in `scripts/lib/_common.py`
(consumed by the verbatim-quote check) accumulates per-symptom
normalizations: form-feed character stripping (PDF page-break
artifacts), `[MM:SS]` / `[H:MM:SS]` caption-timestamp stripping
(YouTube auto-caption sources), whitespace collapsing. Each was
added reactively when a failure mode surfaced.

Two known classes of failure mode are not currently normalized:

- **PDF page-number footers.** A multi-page-spanning quote whose
  source extract carries a bare digit ("3") between the body-text
  lines (page-3 footer + form feed + next-page content) fails the
  substring match. The validator strips the form feed but not the
  digit. Contributors work around this by splitting quotes at page
  breaks; the workaround is functional but reader-hostile (one
  logical passage becomes two artificial quotes).
- **Curly-quote vs. straight-quote drift.** PDF sources that
  contain typographically-correct `“` / `”` characters (U+201C /
  U+201D) fail substring match when the artifact text was authored
  with straight `"`. Contributors work around this by using the
  source's curly-quote form verbatim; the workaround is functional
  but propagates a presentation-layer choice into the artifact-
  layer text.

The reactive-patch trajectory continues — each new failure mode
adds a new normalization rule. The question is whether a more
principled abstraction is reachable.

**The actual question:** what is the right separation between
"source content" (the substring the check should match against)
and "source presentation noise" (the page footers, fonts, glyph
substitutions, layout artifacts that mechanically appear in
extracted text but shouldn't gate verbatim verification)?

Candidate resolutions:

- **Targeted addition.** Add normalizations for the two known
  classes (page-footer digits, curly-quote → straight-quote)
  without changing the architecture. Closes the immediate cases
  at the cost of one more reactive patch on the pile.
- **PDF-layer abstraction.** Make `extract_source_text` produce a
  more aggressively-cleaned text layer (drop page-footer digits,
  unify quote characters, normalize ligatures) before substring
  comparison even happens; the normalization moves from check-time
  to extraction-time. Pre-validates a known-clean comparison
  surface; risks losing fidelity for legitimate digit / quote
  content in source body text.
- **Per-quote whitelist for known artifacts.** Each quote that
  spans a known-noise pattern declares the pattern explicitly via
  a new artifact field (e.g., `source.spans_page_break: true`).
  Validator suppresses substring check around the declared
  artifact location. Most explicit; most contributor-burden.
- **Question whether substring is the right primitive.** Move from
  substring match to a token-sequence match (tokenize quote +
  source, compare sequences after both have presentation noise
  stripped). Most architecturally invasive; closes the door on
  multiple classes of presentation drift simultaneously.

**Surfaces an investigation has to walk:** `scripts/lib/_common.py`
(the `normalize_for_compare` and `extract_source_text` helpers);
`scripts/checks/verbatim_quotes.py` (the check itself);
`meta/conventions.md` "Statements as the universal evidentiary
primitive" (the principle the check enforces); the existing
`naming_quirks` machinery (which handles a parallel class of
drift via contributor declaration rather than mechanical
normalization).

**Blocks:** A2 (marker-agent extraction primitive).
**Blocked by:** none.

### C34 — Schema↔CLI parity check

The schema (`meta/schema.yaml::manifest_entry`) and the CLI
(`scripts/tools/manifest.py`'s commands) drift independently. The
JRE #2194 walkthrough surfaced a concrete case (cf. C29): the
schema's `manifest_entry` declares no URL-uniqueness constraint,
but `cmd_add` enforces URL-uniqueness via a silent early-return;
`cmd_status` returns the first URL match by similar implicit
assumption. The schema permits a model the CLI silently forbids.

The pattern is general. CLI commands carry implicit assumptions
about uniqueness, ordering, dedup keys, and matching semantics
that aren't declared in the schema and aren't checked against the
schema. The gap is invisible until contributor workflow exercises
a permitted-by-schema-but-forbidden-by-CLI case.

**The actual question:** what mechanism asserts that CLI commands
implement the same data model the schema declares?

Candidate resolutions:

- **Docstring assertion.** Convention that every CLI subcommand's
  docstring names the schema rules it enforces (e.g., `cmd_add`
  docstring says "Asserts (url, path) tuple uniqueness per
  schema.yaml manifest_entry — see compatibility note"). Reviewer-
  visible discipline; no mechanical enforcement.
- **Parity check.** A meta-test (`scripts/tests/schema-cli-
  parity.sh`) that asserts dedup semantics, match semantics, and
  required-field handling in CLI commands match the schema's
  declarations. Higher implementation cost; closes the gap
  mechanically.
- **Schema-as-CLI-spec.** The CLI consults the schema at runtime
  to determine dedup keys, required fields, etc. Most architecturally
  invasive; eliminates the drift surface entirely at the cost of
  CLI-side complexity.
- **Per-command audit + accept drift.** One-pass audit cataloging
  every implicit assumption in CLI commands; document the gaps in
  `meta/conventions.md`; rely on contributor discipline going
  forward. Lowest-cost; doesn't prevent future drift.

**Surfaces an investigation has to walk:** every CLI in
`scripts/tools/` (especially `manifest.py`'s commands —
add / status / pending / usage / orphans / missing / summary
/ verify-paths / verify-checksums); `meta/schema.yaml` (the
manifest_entry, person, organization, etc. blocks); `meta/schema-
research-artifact.yaml` (the entry-shape specs CLI scaffolders
need to honor); `scripts/build/research-scaffold.py`,
`scripts/build/new.py`, `scripts/build/build-state.py` (other
CLI tools whose behavior implicitly assumes schema semantics).

**Blocks:** none.
**Blocked by:** C29 (the only known concrete drift instance is the
manifest URL-uniqueness gap, which is precisely what C29 hasn't
decided). The parity-mechanism question itself is unblocked, but
has no second drift instance to design against until C29 resolves
or the corpus surfaces another mismatch.

