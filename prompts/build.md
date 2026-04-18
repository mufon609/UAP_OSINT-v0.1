# Build prompt — layered three-phase process

Paste into a Claude Code session to build **one node** under the layered
Investigation → Build → Review process. **One node per session** is the
hard rule established after the 2026-04-17 pilot failure (see
`meta/toolkit-notes/pilot-failure-2026-04-17.md`).

This prompt documents all three phases: **Phase I (Investigation)**,
**Phase II (Build)**, and **Phase III (Review)**.

Phase II scope (D.3): **document-type nodes only**. Regeneration of
person, organization, event, transcript, news, book, location, and
finding nodes from research artifacts is tracked in `BACKLOG.md`. Until
those ship, build those node types by hand from their populated
research artifact, following the conventions in `meta/conventions.md`.

---

## Hard rules

1. **One node per session.** Do not scaffold a second target while one
   is in-flight. The session ends when the one node has validated,
   been regenerated from its research artifact, passed coverage review,
   and been committed.

2. **Source-read-first.** Every claim and every quote must trace to
   text that was extracted from an archived source **in this session**.
   No claims from memory. No quotes from training knowledge.

3. **Phase discipline.** Phase I produces a populated research
   artifact. Phase II regenerates the node from the artifact.
   Phase III reviews coverage. Do not write node body content during
   Phase I. Do not update the research artifact during Phase II.

4. **Append-only research artifacts.** Never delete entries. Use
   `superseded_by` / `contradicted_by` / `corroborated_by` to preserve
   history. New material arrives via a new iteration entry, not by
   overwriting old entries.

---

## Prerequisites

Before starting, confirm:

- The **target node** is known (path: `{type}/{slug}`, e.g.,
  `documents/written-testimony-fravor-2023`)
- The target node's **narrative file exists** as an empty scaffold
  (via `python3 scripts/new.py …`). Create it first if needed.
- All **primary sources are archived locally** in `sources/{category}/`
  and registered in `sources/manifest.yaml`. If new sources are needed,
  archive them via `python3 scripts/manifest.py add …` before Phase I
  begins.
- The research artifact is either **absent** (will be scaffolded in
  step 1 below) or **exists in initial-scaffold state** with no content
  (will be populated in this session).

If any prerequisite is unmet, stop and fix before proceeding.

---

## Phase I — Investigation workflow

### Step 1. Scaffold the research artifact (if not yet scaffolded)

```
python3 scripts/research-scaffold.py --target {type}/{slug} \
    --sources {comma-separated-source-paths-relative-to-sources/}
```

This creates `research/{slug}.yaml` with empty content sections and an
initial iteration entry (`i0`). A `rumors:` section is included only if
the target node type is `person`, `organization`, `event`, or
`location`.

Validate the scaffold passed its structural checks:
```
python3 scripts/validate-research.py research/{slug}.yaml
```

Should exit 0 (passes, zero content but structurally valid).

### Step 2. Extract every primary source to plaintext

```
python3 scripts/extract-source.py --artifact research/{slug}.yaml
```

This writes `/tmp/scratch-{slug}-0.txt`, `/tmp/scratch-{slug}-1.txt`,
etc. — one per primary source. PDF metadata is printed to stdout for
immediate review (useful for populating `document_intrinsic`).

**Rule:** every subsequent Phase I step references these extracted
files. If a claim or quote is not traceable to text in a scratch file,
it does not belong in the research artifact.

### Step 3. Populate `document_intrinsic`

For each primary source, scan the extracted text for facts the
**document itself states about itself**:

- `internal_title` — title printed in the document
- `internal_date` — date printed inside (often absent; leave null if so)
- `classification` — marking on the document (`unclassified`, etc.)
- `classification_markings_on_document` — what's literally printed
- `authors_per_document` — list of names the document identifies as authors
- Other fields as appropriate per source type

These are **only things readable from the document's own content**.
PDF metadata from Step 2 (author/date from pdfinfo) can inform
`document_intrinsic` but PDF metadata is often set by authoring-software
boilerplate — verify against document content when using.

### Step 4. Populate `context_extrinsic`

Contextual metadata **from outside the document** — e.g., hearing date,
committee name, event node, submitted-to authority. Distinct from
`document_intrinsic` per the Step-A/B/C Flag 1 fix (hearing-date ≠
document-metadata).

Fields used by `build-from-research.py` when rendering document nodes
(add the ones you have; omit the rest):

- `display_title` — node H1 title and Summary-table Title row
- `hearing_date` — Summary-table Hearing Date row
- `primary_source_url` — original upstream URL
- `quote_attribution` — string used as each Key Passage's
  "Attributed to" field (typically `"{Speaker}, {occasion}, {date}"`)
- `provenance` — list of custody-chain steps; each step is a dict with
  `step`, `date`, `entity`, `verified` keys. Rendered as the
  Provenance table (gov-doc nodes only). **`date` values use ISO
  format (`YYYY-MM-DD`)** — the renderer passes them through verbatim;
  ISO keeps provenance sortable and unambiguous across documents.

### Step 5. Populate `description`

A 1-3 paragraph prose summary that renders as the node's `##
Description` section. Every factual claim in the description should
be traceable to a specific artifact entry (claim, quote, or
document-intrinsic field). This is the only free-prose field in the
artifact — treat it as a synthesis of the structured fields below,
not as new evidentiary content.

Future plan (tracked in `BACKLOG.md`): move to agent-generated
description so the evidentiary-derivation invariant is enforced
mechanically. For now: hand-write with discipline.

### Step 6. Populate `quotes` (bounded agent task T2)

**Agent task T2:**
- **Input:** extracted plaintext scratch file(s)
- **Output:** YAML fragment of `quotes:` entries, each with:
  - `id` (q1, q2, q3, …)
  - `text` (literal block `|` preserving exact line structure)
  - `source` (`path` + `location`, e.g., `location: "¶2"` or `"line 807"`)
  - `significance` (one-line note on why the quote matters)
  - `context` (optional: "opening statement" vs "Q&A" vs "appendix")
  - Standard lifecycle fields (id, added_date, added_by_iteration: i0,
    audit_cadence_days: 365)

**Discipline:**
- Every quote is copy-pasted from the extracted text — not typed, not
  rephrased, not composited.
- Multi-line quotes use YAML literal block (`|`) so original line
  breaks are preserved character-for-character.
- **Paragraph references are counted from the extracted scratch file,
  not from memory.** The D.5 pilot corrected a ¶7/¶8 error in a
  hand-authored node this way; an extraction-based count is the
  authoritative anchor, not pre-existing prose.
- Quote text must match source exactly except for surrounding
  quotation marks (which are not part of the quoted content).

### Step 7. Populate `claims` (bounded agent task T1)

**Agent task T1:**
- **Input:** extracted plaintext + populated `quotes`
- **Output:** YAML fragment of `claims:` entries, each with:
  - `id` (c1, c2, c3, …)
  - `statement` (one sentence; atomic factual claim the source establishes)
  - `sources` (list — paths + locations; may include `quote_ref` pointing
    to a supporting quote)
  - `evidentiary_type` — one of:
    - `sworn-testimony` (the source is sworn/on-record; the claim-fact is
      "the witness said X," not "X is true")
    - `documented` (primary-source government/institutional document)
    - `cited` (the source references another source; claim rests on the
      cited one)
    - `secondary` (news / book; use cautiously)
  - `independently_verifiable` (optional: free-text note on corroboration
    status)
  - Standard lifecycle fields

**Discipline:**
- A claim is what the source *establishes*. For sworn testimony, the
  claim is the fact of the testimony, not the truth of what's testified.
  Use `sworn-testimony` evidentiary_type and phrase carefully.
- One claim per sentence. Complex claims break into multiple atomic
  entries.
- Every claim cites at least one source. If you can't trace a claim to
  a location, it doesn't belong in this artifact.

### Step 8. Populate `entities_referenced` (bounded agent task T3)

**Agent task T3:**
- **Input:** extracted plaintext + populated `quotes` + `claims`
- **Output:** YAML fragment of `entities_referenced:` — one entry per
  unique named entity (person, organization, document, event, location,
  finding) mentioned anywhere in the source or in the claims/quotes.
  Each entry:
  - `id` (e1, e2, …)
  - `entity_type` (person | organization | document | event | location | finding)
  - `name` (display name)
  - `wrap_path` (canonical repo path, e.g., `/people/jay-stratton`)
  - `context_summary` (one-line note on how this entity appears in the source)
  - `references` (list of `{quote_id: qN}` or `{claim_id: cN}` — every
    quote or claim that mentions this entity)
  - Standard lifecycle fields

**Discipline:**
- Deduplicate: one entry per entity across the whole artifact. If
  Stratton appears in ¶8 and also in a quote from ¶9, one entity entry
  with both references.
- `wrap_path` uses canonical name form even if the source uses a typo
  (the typo goes into `naming_quirks`, not here).

### Step 9. Populate `naming_quirks` (bounded agent task T4)

**Agent task T4:**
- **Input:** extracted plaintext + populated `quotes`
- **Output:** YAML fragment of `naming_quirks:` — one entry per
  observed spelling/naming oddity that differs from canonical form.
  Each entry:
  - `id` (nq1, nq2, …)
  - `observed` (as written in source)
  - `canonical` (corrected form)
  - `location` (where in source)
  - `source_path` (manifest path of the source)
  - `resolution` (one of: `preserve-as-sic-in-quotes`, `use-canonical`,
    `disputed`, `unresolved`)
  - `note` (optional)
  - Standard lifecycle fields

**Discipline:**
- If a typo is found in a passage that appears as a verbatim quote
  in `quotes`, the quote preserves the typo and the naming_quirk
  resolution should be `preserve-as-sic-in-quotes` so rendered node
  prose knows to use canonical form outside the quote.

### Step 10. Populate `research_gaps` (bounded agent task T5)

**Agent task T5:**
- **Input:** everything populated so far + any contextual knowledge
  about what readers might expect vs what's in the source
- **Output:** YAML fragment of `research_gaps:` — concrete
  investigation pathways raised by this source (things it hints at but
  doesn't resolve; references to other sources worth cross-checking;
  unresolved naming questions; etc.)
  Each entry:
  - `id` (rg1, rg2, …)
  - `statement` (the question/gap in one sentence)
  - `methodology` (how to resolve — be specific, not "research more")
  - `resolved: false` (on initial build)
  - Standard lifecycle fields

**Discipline:**
- Every gap is actionable. "Archive the report Fravor mentions as
  'available on the internet'" is actionable; "Investigate UAP further"
  is not.
- Naming quirks with unresolved resolution automatically imply a
  research gap; record separately so the research_gap can be independently
  tracked/closed.
- Keep `methodology` concise (one or two sentences). The renderer
  concatenates `statement — methodology` into a single Open-Questions
  line; long multi-sentence methodologies produce unwieldy lines.
  If the methodology truly needs a paragraph of explanation, capture
  that in a linked finding node or in the target node's Description,
  and leave the research_gap methodology as the actionable pointer.

### Step 11. Populate `rumors` (bounded agent task T6, conditional)

**Only when target node type is `person`, `organization`, `event`, or
`location`.** Document nodes, transcripts, news, books, and findings do
not carry a rumors section.

**Agent task T6:**
- **Input:** everything populated so far + knowledge of
  widely-circulating claims about the entity
- **Output:** YAML fragment of `rumors:` — widely-reported claims that
  circulate in public discourse but lack primary-source backing in this
  artifact. Each entry:
  - `id` (r1, r2, …)
  - `claim` (the circulating claim as prose)
  - `status` (one of: `not-primary-source-established`,
    `primary-source-identified`, `primary-source-disputed`)
  - `observed_sources` (optional: where the rumor circulates)
  - `primary_source_search` (optional: where we've looked, or where to look)
  - `note` (optional)
  - Standard lifecycle fields

**Discipline:**
- A rumor is a claim that WOULD go into `claims` if a primary source
  existed. Its presence here is a fabrication-prevention mechanism:
  "this is a widely-believed claim; don't re-fabricate it into the
  node without finding a source."
- When a primary source eventually surfaces for a rumor, status
  changes to `primary-source-identified`, a new claim entry is added,
  and the rumor entry is kept as audit history.

### Step 12. Validate the research artifact

```
python3 scripts/validate-research.py research/{slug}.yaml
```

Must exit 0 before leaving Phase I. Any errors must be corrected by
going back to the appropriate step above.

### Phase I complete

At this point you have a structurally-valid, content-populated
research artifact. The narrative node is still an empty scaffold. **Do
not populate the node body in Phase I.**

---

## Phase II — Build

Deterministic transformation from research artifact → populated node
body. No creative writing in Phase II. Every node-body claim traces
to a research-artifact entry.

**Scope (D.3):** document-type nodes only. For other node types,
Phase II is still manual — follow `meta/conventions.md`. Extension is
tracked in `BACKLOG.md`.

### Step 1. Regenerate the node from its research artifact

```
python3 scripts/build-from-research.py research/{slug}.yaml
```

This:

1. Pre-flight: re-runs `validate-research.py` on the artifact and
   aborts if the artifact isn't structurally clean.
2. Renders each required H2 section from artifact data:
   - `## Document Summary` — from `document_intrinsic` +
     `context_extrinsic` + `primary_sources[0]`
   - `## Description` — from `description`
   - `## Provenance` (gov-doc only) — from
     `context_extrinsic.provenance`
   - `## What This Establishes` — from `claims`
   - `## Key Passages` — from `quotes` (with verification blocks)
   - `## Associated Nodes` — placeholder (associate.py fills below)
   - `## Open Questions / Research Gaps` — from `research_gaps`
3. Preserves the node's existing frontmatter verbatim.
4. Writes the regenerated body to `{type}/{slug}.md`, overwriting the
   previous body.
5. Invokes `scripts/associate.py {node}` to rewrite Associated Nodes.
6. Post-build: re-runs `validate.py` on the regenerated node (quote
   verbatim check, section structure, etc.). Exits non-zero if
   validation fails.

Use `--dry-run` to render to stdout without writing. Use
`--no-validate` to skip pre-flight and post-build validators (for
debugging only — never when committing).

### Step 2. Read the regenerated node

After regeneration, open the node file and read it top-to-bottom.
The validators check structure; they do not check that a human would
read the node and find it coherent. If anything looks wrong
(misrendered field, bad table alignment, missing content the artifact
should have produced), the fix goes into the **artifact**, not the
node. Re-run `build-from-research.py` and re-read.

### Phase II complete

The node passes `validate.py` (including mechanical quote-verbatim
verification against the archived source). No hand-edits to the node
body have been made. Every line traces to a research-artifact entry
or to the frontmatter.

---

## Phase III — Review

Mechanical consistency checks between the regenerated node and its
research artifact. Runs last — assumes Phase I and Phase II have passed.

### Step 1. Run the coverage checker

```
python3 scripts/review-coverage.py research/{slug}.yaml
```

The script runs four mechanical checks:

1. **Coverage** — every artifact `claims[].statement` and `quotes[].text`
   appears in the node body (whitespace/punctuation normalized).
2. **Boundary** — the node body (outside `## Associated Nodes`) matches
   what `build-from-research.py --dry-run` would regenerate from the
   current artifact. Divergence means the artifact drifted from the
   node, or the node was hand-edited.
3. **Stub-linking** — every `entities_referenced[].wrap_path` appears
   as a `[`/path`]` link in the node body.
4. **OQ deduplication** — items in `## Open Questions / Research Gaps`
   map 1:1 to unresolved research_gaps (plus any `retain_as_done: true`
   resolved gaps).

Must exit 0. Fix failures by updating the **artifact** (add the missing
claim/quote/entity/gap, or remove orphan node content) and re-running
`build-from-research.py` to resync. Never hand-edit the node to silence
a coverage error.

### Step 2. Semantic review (agent-assisted)

Mechanical checks catch structural drift but not narrative coherence —
whether the Description reads cleanly, whether the What This
Establishes table tells a coherent evidentiary story, whether Open
Questions are genuinely actionable.

After `review-coverage.py` passes, read the regenerated node
top-to-bottom. For any issue: fix the **artifact**, not the node.
Re-run `build-from-research.py` and `review-coverage.py`.

No dedicated prompt for this pass yet — planned as a bounded agent
task (T7) in a later increment.

### Phase III complete

All four mechanical checks pass, and a human read of the regenerated
node surfaces no semantic issues. Ready to commit.

---

## End-of-session procedure (document nodes)

1. `python3 scripts/validate-research.py research/{slug}.yaml` — must pass
2. `python3 scripts/build-from-research.py research/{slug}.yaml` — must
   complete cleanly (includes post-build `validate.py`)
3. `python3 scripts/review-coverage.py research/{slug}.yaml` — must pass
4. Read the regenerated node top-to-bottom; fix any issues in the
   **artifact** (not the node) and re-run steps 2–3
5. Commit the research artifact + regenerated node + any manifest
   changes in one focused commit (one node per session — hard rule)

For non-document node types (Phase II renderer not yet implemented —
tracked in `BACKLOG.md`):

1. `validate-research.py` passes
2. Hand-author the node body per `meta/conventions.md`, drawing
   exclusively from artifact entries
3. `validate.py` passes; commit when clean

`review-coverage.py` currently skips non-document artifacts with a
notice; full coverage review unlocks for each type as its Phase II
renderer lands.

---

## Bounded-agent-task summary

Each task has clear I/O and can be run as a focused agent invocation:

| Task | Input | Output |
|---|---|---|
| T1 — Extract claims | Plaintext + quotes | YAML `claims:` fragment |
| T2 — Extract quotes | Plaintext | YAML `quotes:` fragment |
| T3 — Identify entities | Plaintext + quotes + claims | YAML `entities_referenced:` fragment |
| T4 — Naming quirks | Plaintext + quotes | YAML `naming_quirks:` fragment |
| T5 — Research gaps | Everything above | YAML `research_gaps:` fragment |
| T6 — Rumors (conditional) | Everything above + external context | YAML `rumors:` fragment |

Tasks are **composable** (T3 can use T1 + T2's output). They are
**validated by humans** before being merged into the research artifact.
They are **bounded** — each task produces a specific YAML fragment, not
free-form content.

---

## What NOT to do

- Do not populate node body content during Phase I.
- Do not write quotes from memory — extract from scratch file.
- Do not rephrase source text in quotes (only paraphrase in
  `significance` or `context_summary` fields).
- Do not create a research artifact for a node that doesn't exist yet.
- Do not hand-edit `entities_referenced[].references` after agents
  populate — let the references field reflect what the quotes/claims
  actually contain.
- Do not skip the validator. `validate-research.py` errors are
  commit-blocking.
