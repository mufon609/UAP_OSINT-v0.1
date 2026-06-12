# AGENTS.md — agent first-read

*Query protocol for any AI agent — route by task, and answer factual
questions from the repo's two queryable layers.*

This file is the entry point for any AI agent querying or contributing
to this repository. Read this file first.

---

## What this repo is

A structured primary-source investigation toolkit. Every claim is
anchored to a verifiable primary source. The repo has two queryable
layers:

1. **Node layer** (human-readable narrative) — `/people/`,
   `/organizations/`, `/documents/`, `/events/`, `/transcripts/`,
   `/media/`, `/locations/`, `/findings/`, `/investigations/`
2. **Research-artifact layer** (machine-readable structured facts) —
   `/meta/research/*.yaml`, one per node; the atomic-claim record backing
   each narrative node

The toolkit itself is topic-neutral. The current instance investigates
a specific topic — see `meta/topic/overview.md` for scope.

The fastest way to query these two layers is **node composition** — see
"The investigator workflow" below.

---

## The investigator workflow — composing nodes

The repository's content is a set of **nodes** — human-readable narrative
files (`/people/`, `/organizations/`, `/documents/`, `/events/`,
`/transcripts/`, `/media/`, `/locations/`, `/findings/`,
`/investigations/`). They are a **composable working set**: the fastest
way to use the corpus is to point the CLI at one or more node files and
ask a synthesis question.

- `@people/{a} @people/{b} — what do they share in common?`
- `@events/{e} @transcripts/{t} — does the testimony match the event record?`
- `@findings/{f} — which primary sources back each side of the dispute?`
- `@organizations/{o} — who are its confirmed personnel, and where else in the corpus do they appear?`

Each node carries an `## Associated Nodes` section linking the related
people, organizations, documents, and events — so a single @-mentioned
node fans out to its neighbours, and you can pull those in too.

**Two modes, two precisions:**

| Mode | Use when | What you get |
|---|---|---|
| **Node composition** (@-mention node files) | cross-entity synthesis, comparison, "what connects these?" | a narrative answer grounded in the rendered nodes + their Associated-Nodes links |
| **Research-artifact query** (search `meta/research/*.yaml`) | exact fact lookup, quote provenance, uncertainty flags | a per-quote answer with quote ID, `target_node`, and `source.path` to the primary source (the protocol below) |

The rendered node is the readable narrative; the research artifact behind
it (`meta/research/{slug}.yaml`) is the structured fact layer. Compose
nodes to see the picture; drop to the artifact when you need the exact
quote and its primary-source path. Both honour the same evidentiary
framing (Confirmed / Flagged / Disputed / Contradicted) — surface it in
any answer, and cite the primary source so the user can verify.

---

## What this instance covers

See `meta/topic/overview.md` for the specific investigation:

- Topic statement
- Scope boundaries (what's in, what's out)
- Time period
- Primary corpora
- Agent orientation for this specific topic

If you're doing anything related to this instance's topic, read
`meta/topic/overview.md` after this file.

---

## How to use this repo — route by task

| Your task | How |
|---|---|
| Start a contributor session | read `CLAUDE.md` (auto-loaded for Claude Code) — the session-start checklist |
| Answer a factual question from the repo | `meta/topic/overview.md` → relevant `meta/research/*.yaml` → follow `target_node` link for narrative context if needed |
| Compare or synthesize across nodes | @-mention the node files and ask — `@people/{a} @events/{e} what do they share?` — see *The investigator workflow* above |
| Investigate a thread not yet in the repo | `meta/topic/research-queue.md` → `CLAUDE.md` → run `/build` |
| Build a new node | run `/build {type}/{slug}` (the multi-agent pipeline). One *new* person/org node per session. |
| Prepare a clean-text sibling for an OCR source | run `/prepare-ocr-sibling {category}/{filename}.pdf` (before quoting an OCR-scanned source) |
| Prepare a speaker-attributed sibling for a label-less transcript | run `/prepare-transcript-sibling {slug}` (before quoting an auto-caption / Whisper / human-corrected-caption source) |
| Audit an existing node | run `/audit {type}/{slug}` |
| Maintain a built node without re-scaffolding | run `/augment {type}/{slug} "<what to change>"` (add a recovered quote, re-source a dead citation, correct a field) |
| Verify a transcript verbatim | run `/verify-transcript {type}/{slug}` |
| Audit quote relevance | run `/quote-relevance-audit meta/research/{slug}.yaml` |
| Run an archival sweep | run `/archive-sweep` |
| Fork this toolkit for a different topic | run `/fork-init` (deletes `meta/topic/` + content, keeps the `.claude/` toolkit) |

---

## Authoritative references

| What | Where |
|---|---|
| Node structure spec | `meta/schema.yaml` (nodes) · `meta/schema-research-artifact.yaml` (research artifacts) |
| Epistemic standard (why the rules exist) | `README.md` ("What this is" / "Status markers"), `meta/schema.yaml`, `.claude/skills/build-protocol/` |
| Node templates (one per type) | `meta/templates/` |
| Source archive | `sources/` + `sources/manifest.yaml` |
| Build-state snapshot | `meta/build-state.md` (auto-generated) |
| This instance's topic scope | `meta/topic/overview.md` |

---

## Query protocol — answering a user's factual question

1. **Identify entities** in the question (people, events, documents, organizations by name).
2. **Confirm scope**: read `meta/topic/overview.md` — is the question within this instance's coverage?
3. **For each entity**, search `meta/research/*.yaml` for the entity name. Research artifacts are the structured fact layer; prefer them over prose nodes.
4. **Assemble answer** from research-artifact `quotes[]` (the universal evidentiary primitive). For each quote you cite, include:
   - the quote ID
   - the `target_node` (so the user can read narrative context)
   - the `source.path` (so the user can verify against primary source)
5. **Surface uncertainty explicitly**:
   - If `superseded_by` is set — use the successor and note supersession.
   - If `contradicted_by` is set — cite both sides per the `❌ Contradiction` convention.
   - If a quote rests on a single sworn-testimony source — use the "sworn testimony, claim not independently verified" framing.
6. **If information is not in the repo** — say so. Do not guess. Suggest adding the investigation thread to `meta/topic/research-queue.md`.

---

## Hard rules (summary — the rationale lives with each rule's owner: `README.md`, `meta/schema.yaml`, `.claude/skills/build-protocol/`)

- Every `✅ Confirmed` claim traces to a linked primary source.
- Verbatim quotes must match source character-for-character; `validate.py` checks this mechanically.
- Contradictions are preserved, not reconciled.
- Sworn testimony is a distinct evidentiary fact from the truth of the claim testified to.
- **One *new* person/organization node per build session** — the synthesis-heavy (large free-prose) types; lighter types (document/event/transcript/media/location/finding/investigation) may scaffold in batches. Limits new-node scaffolding only; edits/audits/rebuilds are unrestricted for any type.
- Source-read-first: every node's content traces to a primary source file extracted and read *in the session the content was written*. Not training knowledge.

---

## File types in this repo — quick legend

| Path pattern | Type | Format |
|---|---|---|
| `AGENTS.md`, `CLAUDE.md`, `README.md` | Governance / entry points | Markdown |
| `meta/*.md`, `meta/topic/*.md` | Governance / reference | Markdown with YAML frontmatter |
| `meta/schema.yaml`, `meta/schema-research-artifact.yaml` | Machine-readable specs (node / research-artifact) | YAML |
| `meta/templates/*.md` | Node scaffolding templates | Markdown with placeholder tokens |
| `{type}/*.md` (people, organizations, ...) | Content nodes | Markdown with YAML frontmatter |
| `meta/research/*.yaml` | Research artifacts | YAML |
| `sources/manifest.yaml` | Source archival index | YAML |
| `sources/{category}/*` | Archived primary sources | PDF / HTML / TXT / other |
| `scripts/{build,tools}/*.py` | Toolkit scripts (build pipeline + utilities; reference: `scripts/README.md`) | Python |
| `prompts/*.md` | Paste-ready Claude-Web briefs | Markdown |

---

## If you're uncertain about anything

- Default to reading `README.md` ("What this is" / "Status markers") + `meta/schema.yaml` for the epistemic standard.
- Default to `meta/schema.yaml` for structural rules.
- If a question isn't answered by governance docs, ask the user before
  making assumptions that will enter content.
