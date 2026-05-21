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

### B1 — Quote blockquotes render broken at source line-wrapping (multi-line `>`)

Quotes authored as YAML `|` literal blocks preserve the source's physical
line-wrapping (PDF/HTML extraction wraps at ~80 cols), and the statement
renderer (`_render_statement_block`, `renderers/_common.py`) splits quote
text on every `\n` and prefixes each with `> ` — so a prose quote renders as
a blockquote broken mid-sentence at the wrap points (`> …and Under` /
`> …and Perception` / `> …tasked with`). Pervasive: 617 `|`-block quotes
across ~39 artifacts; 20 rendered nodes carry multi-line blockquotes (sancorp
110, aaro 77, elizondo-qfr 70, luis-elizondo 51, ousd-is 45, ipmo 31, …).

Why no check caught it: the quote-text checks normalize whitespace by design
(`verbatim_quotes` + `coverage` collapse newlines before comparing — they're
line-structure-blind), the `boundary` check compares the node to a fresh
render so a consistent-but-ugly output passes, and there is no blockquote
format-structure check. The single-line-quote convention exists only for
caption sources (`conventions.md` "Caption-tick timestamps") and was never
generalized to PDF/HTML prose quotes; the `ronald-moultrie` template uses
`|` blocks, so the pattern propagated.

Non-bandaid fix — all four parts:
1. **Renderer reflow.** `_render_statement_block` reflows intra-paragraph
   soft-wrap newlines to one `> ` line (space-join) while PRESERVING
   intentional structure — blank-line-separated paragraphs stay separate
   blockquote paragraphs; bulleted/indented list lines stay broken (e.g.
   ronald-moultrie q3 "Big Plays"). Needs a wrap-vs-structure heuristic + tests
   so structured quotes aren't flattened.
2. **Convention.** Generalize the single-line / no-`|`-for-prose rule from
   captions to all prose quotes; state that extraction line-wrapping is
   collapsed at render.
3. **A check** to close the gap so it can't regress — flag a rendered
   blockquote that breaks mid-sentence (or quote text carrying mid-prose
   soft-wrap newlines). Mirrors the existing `yaml_colon_space` format-hygiene
   check. This is the direct remedy for "no check caught it."
4. **Corpus rebuild.** Renderer-touching → rebuild all quote-bearing nodes
   (the boundary check forces it); the diff reflows ~617 quotes across 20
   nodes.

Surfaced by the james-holly node review.

### B2 — `''` escaping artifacts leak into rendered label / attribution cells

A YAML scalar that is **unquoted** but contains a doubled apostrophe
(`America''s`, `AARO''s`) — or a title wrapped in `''…''` — renders the `''`
literally in the node body, because the parser only collapses `''`→`'` inside
a *single-quoted* scalar. This hits structural-label / attribution / note
fields (`significance`, `context`, `.note`, key_personnel / contract notes)
which are **neither verbatim-quote-checked nor prose-drift-scanned** — so the
defect passes validate.py + validate-research.py + review-coverage.py green,
and only a manual read catches it. Surfaced when the WSJ document-node build
leaked `article''s` into an H3 (fixed in that node); a corpus grep finds
existing instances in `people/sean-kirkpatrick` (L78), `organizations/aaro`
(L921, L1182), and ~6 other nodes.

Nuance: `''` **inside** a `>` blockquote can be legitimate source-verbatim
quote text (e.g. `transcripts/2023-07-26-house-fravor` L146 — stenographic
quote marks), so the fix must scope to `''` *outside* blockquote lines.

Fix (batches with B1 — renderer / format-hygiene pass):
1. **A check** (NodeContext, mirrors `yaml_colon_space`) flagging `''` on a
   rendered body's non-blockquote lines — a clean presence/absence floor
   there (a literal `''` in a label/attribution cell is always an escaping
   bug). Closes the "no check caught it" gap.
2. **Corpus cleanup** — triage each existing `''`: fix the unquoted-scalar
   escaping in the artifact + rebuild; leave source-verbatim blockquote `''`.

Surfaced by the WSJ document-node build.

---

## C. Anytime (no dependencies)

No upstream blockers; safe to pick up in any session. Default-focus tier.

_(none)_
