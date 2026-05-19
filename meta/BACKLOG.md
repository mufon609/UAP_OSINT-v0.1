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
and **C — Anytime** (no upstream blockers). Item identifiers are
A1, A2, ..., B1, B2, ..., C1, C2, ... — within each section,
retired items leave a gap rather than shifting remaining IDs, so
git-log and commit-message references stay valid. The same
gap-stable policy in `meta/conventions.md` applies to validator
check names.

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

*No priority-sequence items currently open.*

---

## B. Parallel batch (renderer pass)

Items that touch the renderer and naturally batch into a single
polish pass — bundling reduces churn vs. shipping each as a
separate touch.

*No parallel-batch items currently open.*

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

Surfaced: 2026-05-19 design-element audit. The current per-node check
gets the corpus to 0 errors because everything is renderer-emitted, but
the architecture inverts the source-of-truth direction (verifies
generated output, not the structured source). Moving to artifact-side
is the principled fix.

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

Surfaced: 2026-05-19 design-element audit. Complementary to C4's
artifact-side verbatim-quote move; both reduce duplication between
governance docs and source-of-truth layers (schema / artifact). Not
strictly correctness-required after the schema+validator topic-
substitution fix landed in `5148b2e` — but closes the
documentation-drift surface for forks and schema evolution.

C1 retired 2026-05-17 — shipped as `scripts/tools/extract-firefox-cookies.py`;
ID held open per the gap-stable retirement rule.

C2 retired 2026-05-19 — issue-log mechanism removed entirely (function +
helpers in `scripts/lib/_common.py`, orchestrator call sites, and the
file itself). Followed C2's "remove" path: log accumulated balloon
during a single session of validator-heavy work, confirming the
audit-value-vs-carrying-cost imbalance the 2026-05-17 audit flagged.
ID held open per the gap-stable retirement rule.

C3 retired 2026-05-19 — WEAPONIZED-038 video pipeline registered baselines
for corbell / lacatski / kelleher / knapp, closing all 17 direction-1
warnings; ID held open per the gap-stable retirement rule.

