# AGENT.md — agent first-read

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

| Your task | Read these, in order |
|---|---|
| Answer a factual question from the repo | `meta/topic/overview.md` → relevant `meta/research/*.yaml` → follow `target_node` link for narrative context if needed |
| Investigate a thread not yet in the repo | `meta/topic/research-queue.md` → `meta/conventions.md` → `CLAUDE.md` → `prompts/build.md` |
| Build a new node | `CLAUDE.md` → `prompts/build.md` (one *new* node per session) |
| Audit an existing node | `CLAUDE.md` → `prompts/audit.md` |
| Verify a transcript verbatim | `prompts/verify-transcript.md` |
| Run an archival sweep | `prompts/archive-sweep.md` |
| Fork this toolkit for a different topic | delete `meta/topic/` → restart with your own `meta/topic/overview.md` |

---

## Authoritative references

| What | Where |
|---|---|
| Node structure spec | `meta/schema.yaml` |
| Epistemic standard (why the rules exist) | `meta/conventions.md` |
| Node templates (one per type) | `meta/templates/` |
| Corpus-specific addenda (this topic) | `meta/topic/addenda/` |
| Source archive | `sources/` + `sources/manifest.yaml` |
| Site-specific archival workarounds | `meta/sources-access.md` |
| Toolkit lessons-learned (postmortems, design notes) | `meta/toolkit-notes/` |
| Build-state snapshot | `CLAUDE.md` (auto-generated section) |
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

## Hard rules (summary — see `meta/conventions.md` for the full rationale)

- Every `✅ Confirmed` claim traces to a linked primary source.
- Verbatim quotes must match source character-for-character; `validate.py` checks this mechanically.
- Contradictions are preserved, not reconciled.
- Sworn testimony is a distinct evidentiary fact from the truth of the claim testified to.
- **One *new* node per build session.** Batch *construction* violates the discipline; see `meta/toolkit-notes/pilot-failure-2026-04-17.md` for the case that established this rule. The rule limits new-node scaffolding only — editing, auditing, fixing, or rebuilding existing nodes is unrestricted.
- Source-read-first: every node's content traces to a primary source file extracted and read *in the session the content was written*. Not training knowledge.

---

## File types in this repo — quick legend

| Path pattern | Type | Format |
|---|---|---|
| `AGENT.md`, `CLAUDE.md`, `README.md` | Governance / entry points | Markdown |
| `meta/*.md`, `meta/topic/*.md`, `meta/toolkit-notes/*.md`, `meta/topic/addenda/*.md` | Governance / reference | Markdown with YAML frontmatter |
| `meta/schema.yaml` | Machine-readable spec | YAML |
| `meta/templates/*.md` | Node scaffolding templates | Markdown with placeholder tokens |
| `{type}/*.md` (people, organizations, ...) | Content nodes | Markdown with YAML frontmatter |
| `meta/research/*.yaml` | Research artifacts | YAML |
| `sources/manifest.yaml` | Source archival index | YAML |
| `sources/{category}/*` | Archived primary sources | PDF / HTML / TXT / other |
| `scripts/*.py` | Toolkit scripts | Python |
| `prompts/*.md` | Paste-ready session prompts | Markdown |

---

## Schema versioning

Every schema-governed file declares `schema_version` in its frontmatter.
The current schema version is declared at the top of `meta/schema.yaml`
under the `schema:` block. If you encounter a file whose `schema_version`
is not listed in `schema.compatible_with`, consult
`meta/toolkit-notes/schema-migrations/{from}-to-{to}.md` for migration
instructions.

---

## If you're uncertain about anything

- Default to reading `meta/conventions.md` for the epistemic standard.
- Default to `meta/schema.yaml` for structural rules.
- If a question isn't answered by governance docs, ask the user before
  making assumptions that will enter content.
