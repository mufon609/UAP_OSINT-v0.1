# CLAUDE.md — Session-start checklist

*Contributor session checklist for Claude Code — read order, health
check, build state, session rules, enforcement warnings — then the
contributor reference: a repository-layout map, the end-to-end pipeline,
and the skills/agents map. Deep reference tables still live with their
owners (`scripts/README.md`, the `.claude/` SKILLs, `meta/schema.yaml`);
the maps below are navigational and point to them.*

Read this file at the start of every Claude Code session that involves
**building, auditing, or iterating** on repository content.

**If you are instead *querying* the repo to answer a user's question** —
not modifying content — read `AGENTS.md` at the repo root first: the
consumer-agent entry point (query protocol, research-artifact layer,
task routing). CLAUDE.md below assumes a contributor session.

---

## 1. Read the governing docs

In order:

1. `README.md` — what this repository is / is not (the epistemic standard + Status markers)
2. `meta/schema.yaml` — machine-readable node spec (types, kinds, archetypes, required sections, vocabularies); `meta/schema-research-artifact.yaml` — the research-artifact spec (drives `validate-research.py`)
3. `meta/memory.md` — cross-cutting contributor working knowledge (behavioral patterns that don't fit a more specific surface)
4. `meta/topic/research-queue.md` — current priority build queue
5. `meta/roadmap.md` + `meta/BACKLOG.md` — active work + deferred items; note anything relevant to this session

Don't skip. Governance docs change between sessions.

---

## 2. Health check

Before building anything:

```
python3 scripts/build/validate.py            # node structure + verbatim quotes
python3 scripts/build/validate-research.py    # artifact structure + prose-drift
python3 scripts/build/review-coverage.py --all  # cross-layer coverage/boundary/description-drift
python3 scripts/build/build-state.py --check  # meta/build-state.md snapshot in sync
bash scripts/tests/pre-commit.sh             # full gate chain (subsumes the four above + more); ALSO runs inside `git commit` via .githooks/pre-commit (auto-armed; bypass routes denied — un-bypassable by --no-verify)
```

Exit 0 on all = repo healthy. Any errors → fix first. Don't stop at
`validate.py`: the artifact validator carries the prose-drift family and
the coverage review carries the cross-layer checks, and `pre-commit.sh`
adds the `renderer-coverage.py` and `phase_routing_parity.py` gates a
node-only pass never runs — so a node-only pass can read clean while
artifact-level warnings stand.

---

## 3. Current build state

The corpus snapshot — every node with its status and archetype/kind —
lives at `meta/build-state.md` (auto-generated; do not hand-edit).
Regenerate after any node add / remove / status change:

```
python3 scripts/build/build-state.py --update
```

The pre-commit chain runs `--check` to keep the snapshot in sync.

---

## 4. Ask the user what to build

Do not scaffold nodes without direction from the user. The priority queue
at `meta/topic/research-queue.md` is a suggestion, not a mandate. Confirm
scope, archetype/kind selection, and primary-source availability before
starting.

**One *new* person/organization node per build session.** Do not
scaffold a second until the first is fully populated, passes
`validate.py`, and is committed; lighter node types may scaffold in
batches, and edits/audits/rebuilds/sweeps are unrestricted for any
type. Rule owner — rationale and the synthesis-heavy/lighter split:
`.claude/skills/build-protocol/SKILL.md` ("One new synthesis-heavy
node per session"); hook-enforced at the scaffolder.

**Source-read-first — hard rule.** Every `✅ Confirmed — verified verbatim`
quote rests on text extracted from the archived source file *in this
session* — never training knowledge. The verbatim-quote check in
`scripts/build/validate.py` verifies this mechanically. Rule owner:
`.claude/skills/build-protocol/SKILL.md` ("Source-read-first").

---

## 5. Build path and toolkit

**The default build path is the `/build` skill** — the orchestrator runs
on the main thread and dispatches the role subagents in
`.claude/agents/` (internal-investigator · external-investigator ·
archive · worker · builder · auditor); never hand-author a node. The
standalone skills: `/audit`, `/augment`, `/verify-transcript`,
`/quote-relevance-audit`, `/archive-sweep`, `/prepare-ocr-sibling`,
`/prepare-transcript-sibling`, `/fork-init`.

The owners of the operational detail:

- Pipeline map — steps, stages, branches: `.claude/skills/build/SKILL.md`
  ("The shape")
- Shared build contract — invariants, phases, handoff stubs:
  `.claude/skills/build-protocol/SKILL.md`
- Per-script reference — every script in all six subdirectories, with
  flags and design notes: `scripts/README.md`

---

## 6. Hand-edits to node bodies are blocked

Rendered node bodies (`/people/`, `/organizations/`, `/documents/`, …)
are regenerated from their research artifacts — never hand-edited. A
committed `settings.json` deny rule plus a PreToolUse hook block the
Edit/Write path. To change a node: fix the artifact under
`meta/research/` and re-render with `build-from-research.py`, or run
`/augment` for a targeted maintenance change. `git commit` runs the full
pre-commit chain at commit execution time (`.githooks/pre-commit`,
auto-armed by the commit guard, which denies `--no-verify` and the other
bypass routes — so a compound fix-then-commit is gated on its post-fix
state); scaffolding a second uncommitted new
person/organization node is also hook-blocked (the
one-new-synthesis-node rule, §4).

---

## Repository layout

```
README.md                   public-facing what-and-why overview
AGENTS.md                   consumer entry point — how to query the repo
CLAUDE.md                   this file — contributor session checklist + reference

meta/
  README.md                 friendly-face index of the directory
  BACKLOG.md                deferred work items (not on active roadmap)
  roadmap.md                active work + design decisions that shaped the codebase
  schema.yaml               machine-readable spec (source of truth)
  sources-access.md         site-specific archival workarounds
  templates/                scaffolding templates (one per node type)
  research/                 YAML research artifacts backing each node
                            (structured facts; one per content node)
  topic/                    THIS INSTANCE'S topic-specific content
    overview.md             topic statement, scope, corpora
    research-queue.md       priority investigation queue
    working-notes/          in-progress synthesis docs awaiting integration into content nodes

scripts/
  README.md                 canonical per-script reference (all six subdirectories)
  build/                    scaffold → render → validate pipeline + the per-phase validators
  tools/                    standalone utilities + diagnostics (manifest, archival,
                            transcription, video/OCR pipelines)
  checks/                   per-check modules — every named validator check,
                            dispatched by the build/ validators
  tests/                    pre-commit gate chain + its regression tests
  lib/                      shared cross-script helpers
  scratch/                  gitignored landing zone for exploratory queries

sources/
  manifest.yaml             source-archival index (YAML)
  government/               government primary sources (PDFs, HTML)
  news/                     news article HTML snapshots (news articles
                            are stored here as source material; content
                            nodes live under /documents/)
  social/                   social media post snapshots
  transcripts/              downloaded YouTube / broadcast transcripts
  video/                    video-adjacent content

people/ organizations/ documents/ events/ transcripts/
media/ locations/ findings/ investigations/
                            content nodes (human-readable narrative)

.claude/
  skills/                   invokable workflows — /build, /audit,
                            /augment, /verify-transcript, /quote-relevance-audit,
                            /archive-sweep, /prepare-ocr-sibling,
                            /prepare-transcript-sibling, /fork-init — plus the
                            build-protocol contract preloaded into the role
                            subagents
  agents/                   the six build role subagents (internal-investigator,
                            external-investigator, archive, worker, builder, auditor)
                            + the two OCR page agents (ocr-page-producer,
                            ocr-page-verifier) dispatched by /prepare-ocr-sibling
                            + the two attribution agents (attribution-producer,
                            attribution-verifier) dispatched by
                            /prepare-transcript-sibling
  hooks/                    PreToolUse guards — commit anti-bypass guard (arms
                            .githooks/pre-commit, which runs pre-commit.sh at
                            commit time), node-body-edit block,
                            one-new-synthesis-node cap
  settings.json             hook wiring (committed; topic-neutral)

.githooks/
  pre-commit                runs the full gate chain inside `git commit`
                            (armed via core.hooksPath by the commit guard)

prompts/                    Claude-Web briefs — see prompts/README.md
                            for the index
```

**Three organizing principles, one per tier.** Investigator-facing
content (`/people/`, `/organizations/`, … and `/sources/`) is **flat by
design** — `/{type}/{slug}.md`, found one click in, with no
archetype/sub-category nesting; the frontmatter (archetype, kind,
status) carries the categorization hierarchy would otherwise impose.
Backend tooling (`/scripts/`) is organized for **engineering hygiene**,
and governance + structured-data backing (`/meta/`) is organized **by
role** (templates / topic / research). The flatness rule is about
content the investigator reads — don't extrapolate it onto the tooling
or governance layer, and don't extrapolate organized-by-role onto the
content layer.

**Forking for a different topic.** Delete `meta/topic/`,
`meta/research/`, and the contents of `/people/`, `/organizations/`,
`/documents/`, `/events/`, `/transcripts/`, `/media/`, `/locations/`,
`/findings/`, and `/investigations/`, and `sources/{category}/` (keep the
directories themselves); empty `sources/manifest.yaml`. Create your own
`meta/topic/overview.md` — its frontmatter `topic` and `display_name`
fields drive every UI surface that names the subject (rendered section
headers like `## {topic_display_name} Relevance`, archiver User-Agent,
etc.); the toolkit reads them via `load_topic()`. Run `/fork-init` for
the bootstrap walk-through. Everything not deleted by those steps — the
rest of `meta/` (schema, memory, templates, …), all of `scripts/` and
`prompts/`, the `.claude/` skills + subagents + hooks + `settings.json`,
and root-level governance (`CLAUDE.md`, `AGENTS.md`, `README.md`) — is
topic-neutral toolkit and survives the fork.

---

## The pipeline, end to end

How a primary source becomes a quotable, queryable node — the data
lifecycle a new contributor should be able to follow start to finish.
Tier 1 (sources) flows down into Tier 2/3/4 (nodes); references run
downward only.

1. **Fetch** — a source URL or file lands under `sources/{category}/`
   and is registered in `sources/manifest.yaml`. Tools: `manifest.py`
   (register), `browser-fetch.py` (bot-walled hosts), `download-video.py`
   (YouTube), `transcribe.py` (captions). The `archive` role is the only
   writer of the manifest.
2. **Archive** — the URL is submitted to the Wayback Machine
   (`archive.py`). The local copy under `/sources/` is the integrity
   guarantee; Wayback is insurance.
3. **Extract** — the source is rendered to plaintext for reading
   (`extract-source.py`): text-native PDF via `pdftotext -layout`, HTML
   stripped to text. The extracted scratch text — never training
   knowledge — is what every quote is read from.
4. **Sibling (conditional)** — a degraded source gets a verified
   companion file before any quote is drawn from it:
   - OCR-scanned PDF (`extraction_type: ocr-scan` / `extraction-lossy`)
     → clean-text `.txt` sibling via `/prepare-ocr-sibling` (VLM
     page-image read, confirmed against PaddleOCR, a different OCR
     modality).
   - Label-less transcript (`transcript_provenance: auto-caption` /
     `human-corrected-caption`) → speaker-attribution `.yaml` sibling via
     `/prepare-transcript-sibling` (semantic parse → independent verify →
     video active-speaker fold-gate).
5. **Research artifact** — a contributor populates
   `meta/research/{slug}.yaml`: verbatim `quotes[]` extracted from the
   source text, plus structured facts (`document_intrinsic`,
   `context_extrinsic`, cross-refs). This YAML is the machine-readable
   fact layer the consumer query protocol reads.
6. **Render** — `build-from-research.py` regenerates the node body
   (`{type}/{slug}.md`) from the artifact via the per-type renderer
   (`scripts/build/renderers/{type}.py`), then runs `associate.py`
   (Associated-Nodes back-links) and `validate.py`. Node bodies are
   never hand-edited (§6); a fix means editing the artifact and
   re-rendering.
7. **Query** — an investigator reads and composes the rendered nodes, or
   drops to the research artifacts for exact quote provenance. The
   consumer workflow is `AGENTS.md` ("The investigator workflow").

The verbatim-quote check (`validate.py`) and prose-drift check
(`validate-research.py`) both re-read the source file from disk on every
run — no gate trusts a remembered value. The build phases (`archive ·
extract · organize · link · render · preflight`) and the role that owns
each are in `.claude/skills/build-protocol/SKILL.md`; the full
step/stage/branch map is `.claude/skills/build/SKILL.md` ("The shape").

---

## Skills and agents — the map

Work runs through **skills** (invokable `/name` workflows that run on the
main thread and may dispatch subagents) and the **role subagents** they
dispatch (capability-bounded workers whose tool set *is* their
discipline). This is the navigational map; the operational depth lives
with each owner.

| Skill | What it does | Pipeline position |
|---|---|---|
| `/build` | Build or rebuild a node through the six-role pipeline | The orchestrator |
| `/prepare-ocr-sibling` | Produce + verify a clean-text sibling for an OCR-scanned source | `/build` step-4b gate; also standalone |
| `/prepare-transcript-sibling` | Produce + verify a speaker-attribution sibling for a label-less transcript | `/build` step-4c gate; also standalone |
| `/audit` | Health-check a built node for evidentiary integrity and consistency | Standalone maintenance (reactive) |
| `/augment` | Targeted maintenance change without re-scaffolding | Standalone maintenance (proactive; partial re-entry) |
| `/verify-transcript` | Verify a transcript node's quotes word-for-word against the source | Standalone maintenance |
| `/quote-relevance-audit` | Check each quote is load-bearing for the node's subject | Standalone maintenance |
| `/archive-sweep` | Verify local archives; recover dead URLs; submit missing to Wayback | Periodic / end-of-session health pass |
| `/fork-init` | Bootstrap the toolkit for a different topic | One-time, destructive |
| `build-protocol` | Shared contract preloaded into every build role | Not invokable |

The `/build` orchestrator dispatches the six role subagents in sequence —
**internal-investigator** (survey reuse + name gaps; read-only) →
**external-investigator** (find + read missing sources; web-enabled, no
manifest write) → **archive** (download, register, classify; the *only*
manifest writer) → **worker** ×N parallel (extract verbatim quotes from
one source into a fragment file; the *only* role that introduces quotes)
→ **builder** (merge fragments → organize → link → render; edits the
artifact, *never* the node body) → **auditor** (fresh-context cold
re-read; recommend-only as a build role). The boundaries are mechanical —
each role's tool set enforces them, not convention.

`/prepare-ocr-sibling` dispatches **ocr-page-producer** (VLM page-image
transcription) + **ocr-page-verifier** (settle flagged divergences against
the page image). `/prepare-transcript-sibling` dispatches
**attribution-producer** (semantic parse → draft sibling) +
**attribution-verifier** (independent re-check, separate session).

The role-boundary rationale and the shared contract are
`.claude/skills/build-protocol/`; the step/stage/branch map is
`.claude/skills/build/SKILL.md`; per-script flags and design notes are
`scripts/README.md`.

`.claude/hooks/` enforce the discipline at the tool level: an
un-bypassable commit gate, a block on hand-editing rendered node bodies,
and the one-new-synthesis-node-per-session cap (§4, §6).
