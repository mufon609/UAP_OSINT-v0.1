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

- **C35** — retire `p. N, ¶M` page-anchored location convention?
  *(blocks C33 implementation; not originally an A2 prerequisite
  but transitively in the chain)*
- **C33** — verbatim-quote normalization architecture
  *(implementation waits on C35)*
- **A3** — quote-section redesign

Within Tier 0, A3 is independent; C35 and C33 are sequenced (C35
first, then C33).

**Tier 1 — A2 sub-task (scoped after A2's agent decomposition is
settled; implementation co-lands with A2):**

- **A4** — per-phase validator dispatch

**Tier 2 — A2 implementation:**

- **A2** — multi-agent decomposition of source-prep + Phase I

**Retired or reduced by A2 on landing:**

- **C30** — source-prep orchestrator (fully retired; can ship as
  interim orchestrator if A2 stays roadmap-scoped)
- **C31** — preflight discipline audit (reduced; manual-invocation
  case stays for tools called outside the agent chain)
- **C32** — research-scaffold placeholder shape (narrows to
  non-marker-populated fields)

**Independent of the A2 chain:**

- **A1** — retire mandatory `entities_referenced[]` registration
  (corpus-migration + schema decision, orthogonal to A2)
- **C34** — schema↔CLI parity check (orthogonal mechanism question;
  no known concrete drift instance)

---

## A. Priority sequence

Items with ordering or coupling constraints.

### A1 — Retire mandatory `entities_referenced[]` registration

**Premise verified by corpus measurement.** The field carries 1,254
entries across 58 of 59 research artifacts. 100% of those entries'
`wrap_path` values already appear as `[`/path`]` body wraps in the
rendered node. The duplication is complete: every entity registered
in the field is also wrapped in body prose. AGENT.md does not consume
`entities_referenced[]` — the field has no reader-facing or
query-agent consumer. The structural consumers are:

- `scripts/checks/link_resolution.py` — builds the broken-link
  registry, but reads body wraps directly via the same
  `\[``(/[^``]+)``\]` regex `associate.py` uses. Independent of
  `entities_referenced[]`.
- `scripts/checks/stub_linking.py` — enforces every
  `entities_referenced[].wrap_path` also appears as a body wrap.
  Symmetry-enforcement check; the symmetry is what creates the
  duplication burden.
- `scripts/checks/description_token_drift.py` — uses `name` field
  as approved-token vocabulary for the description-drift gate.
- `scripts/tools/coverage-suggest.py` — pools entity text into the
  missed-entity capitalized-token diagnostic.

`context_summary` is the only sub-field carrying contributor synthesis
not derivable from elsewhere. Corpus measurement: 84% of
`context_summary` content already appears in the rendered body prose;
16% (173 entries across 58 artifacts) carries unique synthesis content
not present in body.

**Direction.** Retire the discipline that every body-wrapped entity
must be registered. `entities_referenced[]` becomes optional and only
carries entries the contributor wants to attach a non-trivial
`context_summary` to. Reduces the field from 1,254 entries to ~173
entries; retires `stub_linking.py`'s symmetry enforcement; preserves
the synthesis surface for the 16% of entries where it's load-bearing.

**Surfaces an investigation has to walk before implementation:**

- `description_token_drift.py` — entity `name` is one input to the
  approved-token vocabulary. Reducing the entity set shrinks the
  vocab. Determine whether the 84% redundant entries' names are
  unique to those entries or are also covered by other vocab sources
  (body prose tokens, `naming_quirks[]`, structured tables). If
  unique-to-redundant-entries, a corresponding migration moves those
  names to a `naming_quirks` or `description_token_overrides` entry
  before deleting the registration.
- `coverage-suggest.py` — pooling reduces by the redundant-entries'
  text. Likely benign (the tool gaps-checks against source content,
  not artifact density), but verify.
- `meta/schema-research-artifact.yaml` — drop `entities_referenced`
  from the universally-required keys list; mark optional in schema.
- `meta/conventions.md` "Cross-reference contract for interview-
  derived testimony" — currently requires venue/host/transcript
  registration. Rewrite to require body wraps (still load-bearing for
  the broken-link registry) without requiring `entities_referenced[]`
  registration.
- 58 research artifacts — corpus migration drops 1,081 redundant
  entries; preserves 173 with non-trivial `context_summary`. Migration
  script reads each artifact, keeps only entries whose
  `context_summary` is unique-to-the-entry (not duplicated in body
  prose), drops the rest.

**Blocks:** none.
**Blocked by:** none.

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

**Blocks:** retires C30, absorbs sub-pieces of C5 / C27 / C28 / C31 / C32 on landing.
**Blocked by:** A3, A4, C33.

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

**A2 effect:** fully retired when A2 ships. The verifier + marker
agents absorb the orchestration; slug consistency becomes
agent-internal. Could ship as an interim orchestrator if A2 stays
roadmap-scoped, but the work does not carry forward into A2 — the
agents replace the orchestrator rather than build on it.

### C31 — Standardize preflight discipline across `scripts/tools/`

**Catalog of current state** (one-pass audit; tools with no
prerequisites omitted):

| Tool | Prerequisites | Preflight pattern |
|---|---|---|
| `download-video.py` | yt-dlp, ffmpeg, ffprobe, Firefox cookies | `def preflight()` at `main()` entry |
| `diarize-audio.py` | HF_TOKEN, ffmpeg, ffprobe, pyannote, torch | Inline HF_TOKEN check at `main()` entry; other prereqs deferred until use |
| `transcribe.py` | yt-dlp, Firefox cookies | Deferred (fails at first use) |
| `extract-frames.py` | ffmpeg, ffprobe | Deferred |
| `extract-firefox-cookies.py` | yt-dlp (for cookie format), Firefox profile | Deferred |
| `detect-faces.py` | cv2 (OpenCV), PIL | Deferred (ImportError at top-level) |
| `stitch-transcript.py` | ffmpeg, pyannote outputs | Deferred |
| `archive.py` | Network (Wayback Machine) | Deferred (HTTP error at first call) |

Tools with no prerequisites (no preflight needed): `manifest.py`,
`check-vocab.py`, `coverage-suggest.py`, `normalize-locations.py`,
`migrate-manifest-to-artifacts.py`.

The pattern is non-uniform: 1 of 8 prerequisite-bearing tools has a
formal `preflight()`; 1 has an inline check for the most-likely-
missing prereq (HF_TOKEN); 6 defer entirely. The cluster most exposed
to mid-pipeline failure is the video pipeline
(`download-video` → `extract-frames` → `detect-faces` → optional
`diarize-audio` + `stitch-transcript`) — five tools, four with
deferred-check failure modes, where a contributor may complete one
step's work before the next step fails on a missing binary or model.

**The actual question:** what's the standard for "prerequisite
discoverability" across `scripts/tools/`?

Candidate resolutions (none recommended; listed for completeness):

- **Universal `preflight()` discipline.** Every prerequisite-bearing
  tool grows a `preflight()` function called at `main()` entry that
  checks every env var, binary, library, and external-service
  prerequisite the tool consumes anywhere in its execution. Exit
  non-zero with install hints before any side-effect runs. Most
  explicit; most invasive — adds preflight to seven tools.
- **Shared preflight library.** A `lib/_preflight.py` module tools
  register requirements with declaratively (`require_env("HF_TOKEN")`,
  `require_binary("yt-dlp")`, `require_python_module("pyannote.audio")`).
  Tools call `lib._preflight.check()` at entry. Less per-tool
  boilerplate; centralizes the install-hint vocabulary; assumes
  the cluster grows enough to amortize the abstraction.
- **Smoke-test coverage only.** Add a `scripts/tests/preflight-check.sh`
  that confirms each tool exits cleanly with the prerequisite-missing
  install hint when its prerequisites are absent. Catches regressions
  but doesn't change behavior of any currently-deferred check.
- **Cluster-only `preflight()`.** Apply universal preflight to the
  video pipeline cluster (where mid-pipeline failure is most costly)
  and accept deferred-check on the rest. Trades partial coverage for
  smaller invasive surface — five new `preflight()` functions instead
  of seven.

**Surfaces an investigation has to walk:** the seven prerequisite-
bearing tools above; `lib/_common.py` for shared preflight helpers;
`scripts/tests/` for the smoke / help-check patterns the preflight
standard would integrate with.

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
normalizations: curly-quote → straight (U+201C/U+201D, U+2018/U+2019),
em/en dash → hyphen → strip, `[MM:SS]` / `[H:MM:SS]` caption-timestamp
stripping (YouTube auto-caption sources), Markdown blockquote-prefix
stripping, HTML-entity decoding, whitespace collapsing. Form-feed
characters collapse via the whitespace rule. Each rule was added
reactively when a failure mode surfaced.

**One known class of failure mode is not currently normalized:**

- **PDF page-number footers.** A multi-page-spanning quote whose
  source extract carries a bare digit ("3") between the body-text
  lines (page-3 footer + form feed + next-page content) fails the
  substring match. The validator collapses the form feed to a
  space but the digit stays. Contributors work around this by
  splitting quotes at page breaks; the workaround is functional but
  reader-hostile (one logical passage becomes two artificial quotes).

**The original BACKLOG framing also named a curly-quote failure
mode; investigation determined this claim was stale.** Lines 796–797
of `normalize_for_compare` already map U+201C/U+201D and U+2018/U+2019
to straight quotes on both sides. Corpus census confirms standard
curly variants are handled. Exotic variants (U+201E low-9, U+00AB/BB
guillemets, U+2032/U+2033 primes) occur in <250 total positions
across 333 text-extractable source files and have not surfaced as
failure modes; no current action required for them.

The reactive-patch trajectory was forward-looking when the entry
was written. The pile has converged: one remaining concrete failure
mode (page-footer digits) plus exotic-quote variants that may never
fail. The question of whether a more principled abstraction is
reachable is partly answered by the convergence — but page-footer-
digit handling specifically intersects with the open structural
question in **C35** (retire `p. N, ¶M` page-anchored locations in
favor of grep-based navigation). If C35 retires the convention,
the page-footer failure mode's contributor cost drops sharply
(quotes spanning page boundaries are less common when locations
aren't page-anchored), and C33 narrows further.

**The actual question:** what is the right separation between
"source content" (the substring the check should match against)
and "source presentation noise" (the page footers, fonts, glyph
substitutions, layout artifacts that mechanically appear in
extracted text but shouldn't gate verbatim verification)?

Candidate resolutions (for the one remaining failure mode,
page-footer digits):

- **Targeted addition in `normalize_for_compare`.** Add a regex
  stripping bare-digit-only lines adjacent to form feeds in the
  comparison primitive. Wrong layer architecturally (page footers
  aren't a comparison concern; they're an extraction artifact)
  but lowest implementation cost.
- **PDF-layer abstraction in `extract_source_text`.** Strip the
  bare-digit footer lines at extraction time — `\n\s*\d+\s*\n(?=\f)`
  applied to PDF output before downstream consumers see it. All
  three consumers (verbatim-quote, prose-drift, description-drift)
  benefit with no per-check change. Form feed itself stays —
  consumed by `scripts/tools/normalize-locations.py` for page-
  number computation. Conservative: only strips lines that are
  *exclusively* whitespace + digits adjacent to form feeds; random
  content digits stay.
- **Per-quote whitelist for known artifacts.** Each quote that
  spans a known-noise pattern declares the pattern explicitly via
  a new artifact field (e.g., `source.spans_page_break: true`).
  Validator suppresses substring check around the declared
  artifact location. Most explicit; most contributor-burden;
  doesn't scale.
- **Question whether substring is the right primitive.** Move from
  substring match to a token-sequence match. Most architecturally
  invasive; closes the door on multiple classes of presentation
  drift simultaneously, but trades substring's clear failure
  semantics for tokenization edge cases (split-column reflow,
  list-item interleaving). Over-engineered for the converged pile.

**Surfaces an investigation has to walk:** `scripts/lib/_common.py`
(the `normalize_for_compare` and `extract_source_text` helpers);
`scripts/checks/verbatim_quotes.py` (the check itself);
`meta/conventions.md` "Statements as the universal evidentiary
primitive" (the principle the check enforces); the existing
`naming_quirks` machinery (which handles a parallel class of
drift via contributor declaration rather than mechanical
normalization).

**Blocks:** A2 (marker-agent extraction primitive).
**Blocked by:** none directly. Outcome shape depends on C35 — if
C35 retires page-anchored locations, the page-footer failure mode
becomes rare enough that targeted addition or even status-quo
may be acceptable. C33 should not implement until C35 resolves.

### C34 — Schema↔CLI parity check

The schema (`meta/schema.yaml`) and the CLIs in `scripts/tools/`
can drift independently. CLI commands carry implicit assumptions
about uniqueness, ordering, dedup keys, and matching semantics
that aren't declared in the schema and aren't checked against the
schema. The gap is invisible until contributor workflow exercises
a permitted-by-schema-but-forbidden-by-CLI case.

No known concrete drift instance currently exists in the corpus.
The entry stays open as a mechanism question worth designing
against once a second drift case surfaces; until then, there's
nothing to design against.

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
**Blocked by:** none. The parity-mechanism question is unblocked
but has no known concrete drift instance to design against. Await
a corpus-surfaced mismatch before implementing.

### C35 — Retire `p. N, ¶M` page-anchored location convention?

**Open structural question.** Every quote in `meta/research/*.yaml`
carries a `source.location` field anchoring the quoted passage
within the cited source. `meta/conventions.md` "Quote location
refs" enforces a canonical form per source-shape: `p. N, ¶M` for
paginated PDFs, `¶N` for unpaginated short documents, `[MM:SS]`
for caption / audio / video, `Doc N` for FOIA email-release
siblings, etc. The location is reader-facing — the renderer emits
a `| Location | ... |` row in every quote's verification block so
a reader can navigate to the passage within the cited source.

**The proposal under investigation.** Retire the page-anchored
location forms (`p. N, ¶M`, `p. N`) in favor of grep-based
navigation: the source is archived locally, the quote text is
verbatim, a reader finds the passage by searching the source for
the quote text. Implication: `source.location` either drops or
narrows to forms that grep can't replace (timestamps for audio /
video, document-block markers for FOIA email releases).

**What the reader actually does.** For most sources in the
corpus (short documents, news articles, single-page memos), the
reader opens the archived source and locates the quote by
ctrl-F / `grep` on its text. The `p. N, ¶M` ref provides no
information beyond what grep produces. For long-form sources
(200-page hearing transcripts, multi-document FOIA releases,
government reports with section structure), the page ref is a
shortcut — without it, the reader greps a 200-page PDF and
maybe finds multiple matches.

**What the contributor pays today.** Maintaining `p. N, ¶M`
discipline carries real costs:

- Extraction-version dependence: `pdftotext` page numbers shift
  when the extract is regenerated against a clean-text sibling
  (the OCR-scan / extraction-lossy recovery path produces
  different page boundaries than the underlying PDF). The
  `meta/conventions.md` "source-anchored, not extraction-
  anchored" rule documents this fragility.
- Page-footer normalization pain (parent of **C33**'s remaining
  failure mode): substring matching breaks at page boundaries
  because pdftotext emits page-number digits in extracted text.
- `scripts/tools/normalize-locations.py` is one of the more
  complex contributor tools — exists to detect / report
  extraction-version-dependent location refs and propose
  canonical forms. If page-anchored refs retire, this tool
  retires with them.

**What grep-based navigation costs.**

- Long-form sources: reader doesn't get the page-shortcut.
  Mitigation: many PDF viewers' search produces results-with-
  context that approximates a page ref. Acceptable for most
  readers; potentially worse for citation discipline (academic-
  style references that quote "p. 47" carry institutional
  weight grep doesn't).
- Sources where the quote text appears multiple times: grep
  alone is ambiguous. Mitigation: `context` field (already
  populated on most quotes) disambiguates which occurrence is
  meant.
- Sources that don't grep at all: video / audio / scanned PDFs
  without text layers. These keep their timestamp / document-
  block / `lines N-M of the extract` locations regardless —
  the proposal is about retiring page-anchored forms, not all
  location forms.

**Source-shape category walk** (the investigation has to do this
properly before any retirement):

| Source shape | Current location form | Grep-navigable? | Retire ref? |
|---|---|---|---|
| Short PDF / news article (1–5 pages) | `p. N, ¶M` or `¶N` | Yes | Likely yes |
| Long PDF (hearing, report, study) | `p. N, ¶M` | Mostly yes; long-form is the edge case | Investigate per-document |
| HTML article | `¶N` | Yes | Likely yes |
| TXT / Markdown source | `¶N` or line-based | Yes | Likely yes |
| Caption / auto-caption transcript | `[MM:SS]` | Sort of (no easy ctrl-F on bare timestamps) | No — timestamps are content-anchored |
| Audio / video source | `[MM:SS]` | No | No |
| Scanned PDF (`ocr-scan` flag) | `p. N, ¶M` against `.txt` sibling | Yes against sibling | Likely yes |
| FOIA email release with `DOCUMENT N` markers | `Doc N, Sender YYYY-MM-DD HH:MM` | Yes via `Doc N` marker | No — markers ARE content-anchored, not page-anchored |
| Image / photo (visual text) | spatial anchor (e.g., `HUD bottom-right`) | No | No |

**Candidate resolutions:**

- **Full retire.** Drop `p. N, ¶M` entirely. `source.location` becomes
  optional (timestamp / Doc-N / spatial-anchor / `¶N` only). Renderer
  omits Location row when location is empty. Existing quotes' `p. N`
  refs migrate to `¶N`-only or drop. Most aggressive simplification.
- **Retire for short sources only.** Documents under N pages drop
  `p. N`; long-form sources keep it as a navigation aid. Per-source
  judgment via a new manifest field or a page-count threshold. Less
  aggressive; preserves the long-form reader experience.
- **Retire the page component; keep `¶N`.** `p. N, ¶M` becomes `¶M`
  globally — paragraph-anchored, not page-anchored. Eliminates
  extraction-version dependence (paragraph markers are content-
  derived, not page-layout-derived). Renderer still shows a Location
  row; reader uses paragraph-counting instead of page-jumping.
- **Status quo + better tooling.** Keep page-anchored convention;
  add a `scripts/tools/locate-quote.py` helper that takes a quote
  + source and emits the canonical `p. N, ¶M` ref by grep. Eases
  contributor friction without retiring the convention.

**Surfaces an investigation has to walk:** `meta/conventions.md`
"Quote location refs" section; `meta/schema-research-artifact.yaml`
`quote_source.location` field semantics; `scripts/build/renderers/*.py`
(every renderer that emits a Location row); `scripts/tools/normalize-
locations.py` (the diagnostic that would retire); every existing
`meta/research/*.yaml` quote's location form (corpus-wide count by
shape, current distribution); reader-experience evaluation on a
representative dense long-form source (e.g., the 2024-11-19 SASC
hearing transcript).

**Effect on C33.** If C35 lands as "full retire" or "retire page
component," C33's page-footer failure mode loses most of its
contributor cost — quotes spanning page boundaries are rare when
locations aren't page-anchored. The two BACKLOG entries should
land in dependency order: C35 first (decision on locations), C33
follows (decision on remaining normalization gap).

**Out of scope for the investigation.** Picking a candidate without
walking the source-shape category table. Some categories must keep
their location form (audio / video / image / FOIA); the question
is exclusively about page-anchored forms for paginated text
sources. Bundling unrelated location-form changes (timestamp
syntax, paragraph-anchor enforcement, etc.) into this
investigation would scope-creep it.

**Blocks:** C33 (C33's outcome depends on C35's decision).
**Blocked by:** none.

