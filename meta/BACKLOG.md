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

### C4 — Move verbatim-quote check from rendered Markdown to research artifact

The verbatim-quote check (`scripts/checks/verbatim_quotes.py`, dispatched
per-node by `validate.py` via `_NODE_CHECKS`) parses the rendered node
body to locate quotes: a blockquote regex finds `> ...` blocks, then a
2500-character window scan finds the following `| Source | ... |` row,
then a markdown-link regex extracts `(../sources/{path})`, then the
quote is substring-checked against the extracted source text.

The check then has a defensive `continue` branch for any Source row that
doesn't match the `(../sources/...)` pattern — a "soft case" silent-skip
on malformed Source rows. Across the current corpus this branch never
fires (1205 rendered Source rows + 2256 artifact `quotes[].source.path`
values all canonical), but a hand-edited node body or a renderer
regression would slip through silently — exactly the silent-drift class
of failure the check exists to catch.

The structural fix: dispatch the check from the artifact layer, not the
rendered layer. The artifact's `quotes[]` carry `text` + `source.path`
as structured fields; substring-check `text` against the source extracted
at `source.path`. Concrete changes:

- New per-artifact check, `scripts/checks/verbatim_quotes_artifact.py`
  (or rename the existing module and re-purpose it), dispatched from
  `validate-research.py::_ARTIFACT_CHECKS`.
- Retire the per-node markdown-parsing implementation in
  `scripts/build/validate.py::_NODE_CHECKS`.
- Drop the markdown-link regex, the blockquote regex, and the 2500-char
  search window — all artifacts of parsing rendered output that the
  artifact-side check doesn't need.
- Update `validate.py`'s `__doc__` block + `meta/conventions.md`
  "Statements as the universal evidentiary primitive" / "Confirmation
  is a precondition for inclusion" to reflect that verification is
  artifact-side, with the rendered node faithful to the artifact by
  construction.

Side benefits:
- Faster (no per-node markdown regex pass).
- The 2500-char magic number disappears with the markdown-side check.
- Architecturally consistent with the rest of the validator chain:
  drift / coverage / prose-drift checks all already run against the
  artifact, not the rendered node.

Why it matters: the current per-node check reaches 0 errors because
everything is renderer-emitted, but the architecture inverts the
source-of-truth direction (verifies generated output, not the
structured source). Moving to artifact-side is the principled fix —
the rendered node stays faithful to the artifact by construction
rather than by happenstance.

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

