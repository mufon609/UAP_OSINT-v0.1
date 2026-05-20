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

- **C33** — verbatim-quote normalization architecture
- **A3** — quote-section redesign

Within Tier 0, A3 and C33 are independent. (C35 was reframed to an
accuracy-check investigation — page-anchored locations stay — so it no
longer gates C33 or sits in the A2 chain.)

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
  decompose the contributor-as-glue friction via a single
  slug-threaded source-prep orchestrator + tighter preflight
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

**Blocks:** none currently open.
**Blocked by:** A3, A4, C33.

---

### A3 — Quote-section redesign (organize by load-bearing statement)

**Open structural question — purely about ORGANIZATION.** The node
**must keep its proper verbatim quotes** — the repo's evidentiary
primitive is verbatim text on the node where the claim is asserted,
not a compressed pointer to the source node "one click away."
Compressing quotes to references breaks that and is explicitly NOT
the goal. The real question is how to *organize* the quotes so the
surface isn't a dense, repetitive per-quote stream (a person node
citing many statements today renders one verification block per
quote).

**Direction (framing, not a chosen design).** Reorganize the surface
around **load-bearing statements** rather than a flat per-quote list,
complementing the existing `timeline` (the chronological view):

- Each load-bearing statement carries its verbatim quote(s) once.
- Other sources that bear on the statement **reference** it instead
  of re-stating it — "source X confirms this statement", "source Y
  contradicts it" — so cross-source corroboration adds no duplicate
  quote text.
- **Contradictions get their own section, adjacent to the statement
  they contradict** — the disagreement sits next to the claim, not
  buried in a flat stream or only on a separate node.

Net: no verbatim loss, far less duplication / clutter, and the
investigation stays current — a new corroborating or contradicting
source attaches to the relevant statement instead of appending
another block.

**The design question to settle — best for BOTH:**
- the reader / investigator (each load-bearing claim shown with its
  verbatim support + adjacent confirm/contradict cross-refs), and
- backend maintenance (how a "statement" + its quote(s) + the
  cross-source confirm/contradict links are modeled in the research
  artifact and rendered, without a fragile new layer).

**Architecture boundary to reconcile.** Cross-source contradiction is
today a **finding** (the three-layer architecture: entity nodes carry
single-source facts; findings carry multi-source patterns). A
statement-adjacent "contradicts" section on the entity node must be
squared with that — e.g., the node carries the pointer + marker
(`❌` / `⚠`) adjacent to the statement while the cross-source analysis
still lives on a finding, or the boundary moves. Resolve this as part
of the design; it is the load-bearing tension.

**Corpus measurement (person nodes) — the duplication the redesign
targets.** 15 person nodes; mean 30 quotes / median 16 / max 165:

| Person node | Total quotes | Max same-source repetition |
|---|---|---|
| `/people/david-grusch` | 165 | 79 |
| `/people/james-lacatski` | 41 | 14 |
| `/people/david-fravor` | 16 | 10 |
| `/people/sean-kirkpatrick` | 43 | 10 |
| `/people/luis-elizondo` | 23 | 9 |

The Grusch node (165 quotes, 79 to one source — his July 2023 House
testimony) is the worst case the statement-grouping must handle
gracefully: those 79 collapse under the statements they support, with
no loss of verbatim text.

**Surfaces an investigation has to walk.**

- `scripts/build/renderers/{person,document,event,transcript}.py` —
  current quote rendering across types.
- `meta/schema-research-artifact.yaml` — `quote_entry` shape; whether
  a statement grouping + confirm/contradict cross-refs need new fields.
- `meta/conventions.md` "Statements as the universal evidentiary
  primitive" (keep verbatim) + "Contradictions" (the `❌` / `⚠`
  markers and where contradictions are documented).
- The finding-node layer — the boundary above.
- A representative read of `/people/david-grusch` (165-quote surface).

**Blocks:** A2 (the manager agent's contract — how it organizes
quotes into the node — depends on the quote section's shape).
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
reachable is partly answered by the convergence. (C35 was once
expected to retire page-anchored locations — which would have made
page-spanning quotes rare and narrowed this further — but C35 has been
reframed to an accuracy check; page-anchored locations stay, so the
page-footer failure mode stands on its own merits here.)

**The actual question:** what is the right separation between
"source content" (the substring the check should match against)
and "source presentation noise" (the page footers, fonts, glyph
substitutions, layout artifacts that mechanically appear in
extracted text but shouldn't gate verbatim verification)?

**2026-05-20 — second presentation-noise class found and fixed at the
extraction layer (HTML element-boundary concatenation).** While driving
`meta/research/luis-elizondo.yaml` to zero prose-drift findings, the NYT
2017 source surfaced the token `KEANDEC`: the byline surname "Leslie
Kean" (`<span>`) glued to the dateline "Dec. 16, 2017" (`<time>`) because
`clean_html_for_text` empty-stripped `<time>` — it sat in
`_HTML_INLINE_TAGS` alongside true mid-word formatters. Standalone-datum
phrasing elements (`time`, `data`, `meter`, `progress`, `output`,
`picture`) carry a discrete datum, never a mid-word continuation, so
empty-stripping concatenates them onto adjacent text. Fix: moved those
six out of `_HTML_INLINE_TAGS` so they hit the whitespace branch
(word-boundary preserved). This is the HTML analog of the
`extract_source_text` candidate below — presentation noise removed once
at the extraction layer, so all three consumers (verbatim-quote,
prose-drift, description-drift) benefit with no per-check change.
Full 58-node re-validation clean (no verbatim-quote regressions;
broken-link registry unchanged at 510). It settles the "actual question"
above for the HTML case — the extraction layer is the right home — and
narrows C33 to the remaining PDF page-footer-digit mode, which keeps the
entry open.

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
**Blocked by:** none. (C35 was reframed to an accuracy check — it no
longer retires page-anchored locations — so C33 no longer waits on it;
the page-footer failure mode stands on its own.)

### C35 — Verify page-anchored location refs are accurate

**Investigation (accuracy check — not a convention change).** Every
quote in `meta/research/*.yaml` carries a `source.location` the
renderer surfaces so a reader can navigate to the quoted passage.
~507 of these are page-anchored (`p. N, ¶M` or `p. N`), almost all
from PDF / paginated-HTML sources. The verbatim-quote check confirms
the quote TEXT appears somewhere in the source — it does NOT confirm
the location ref points to the right place. The open question: are
the page-anchored refs accurate, or have some drifted (wrong page,
off-by-one paragraph, stale after a re-extraction)?

**What to do.** Sweep (or sample) the page-anchored locations and
check each against its archived source — does following the ref land
on the quoted passage? Report (and correct) any inaccurate refs. The
page-anchored convention stays; the goal is confirming the refs are
correct. `scripts/tools/normalize-locations.py` (the read-only
diagnostic that flags extraction-version-dependent refs) is the
natural starting point; the source files in `sources/` are the ground
truth.

**Blocks:** none.
**Blocked by:** none.
