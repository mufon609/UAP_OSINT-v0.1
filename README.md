# Primary-Source Investigation Toolkit

*The human entry point: what this repository is and why, plus the catalog
of the skills and agents that operate it.*

A structured, versioned knowledge base where every claim is anchored to a
verifiable primary source. Topic-neutral; the current instance documents
UAP public-record material, but the same structure works for any
investigation grounded in primary sources.

---

## What this is

- Every claim is either confirmed from a linked primary source or
  explicitly flagged as unverified
- Primary-source URLs are archived locally so the record survives if the
  source site dies
- Contradictions are preserved, not reconciled — the repository
  documents what each side says and links to both
- Source data is never overwritten — or silently cleaned: the repository
  records sources verbatim, preserving their artifacts (OCR errors, typos)
  and flagging them rather than correcting them. Updates are added
  alongside originals with `Superseded By` or `Contradicted By` pointers
- Evidentiary categories (eyewitness, whistleblower, institutional-actor,
  reporter; gov, gov-contractor, private; hearing, encounter;
  gov-doc, non-gov-doc) are separated structurally so a reader sees the
  evidentiary distinction before reading the content

The rules are enforced by `meta/schema.yaml` + the validators in `scripts/build/` (dispatching the per-check modules in `scripts/checks/`); the build discipline lives in `.claude/skills/build-protocol/`.

---

## What this is not

- Not a place for speculation or anonymous sourcing
- Not secondary-source summaries presented as fact
- Not advocacy for any conclusion
- Not a debunking resource
- Does not adjudicate between conflicting primary sources

---

## Repository layout

```
README.md                   this file — public-facing overview
AGENTS.md                   first-read for AI agents querying the repo
CLAUDE.md                   session-start checklist for contributors

meta/
  README.md                 friendly-face index of the directory
  BACKLOG.md                deferred work items (not on active roadmap)
  roadmap.md                active work + design decisions that shaped the codebase
  schema.yaml               machine-readable spec (source of truth)
  sources-access.md         site-specific archival workarounds
  templates/                scaffolding templates (9 files, one per node type)
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

**Forking for a different topic.** Delete `meta/topic/`,
`meta/research/`, and the contents of `/people/`, `/organizations/`,
`/documents/`, `/events/`, `/transcripts/`, `/media/`, `/locations/`,
`/findings/`, `/investigations/`, and `sources/{category}/` (keep the
directories themselves); empty `sources/manifest.yaml`. Create your own
`meta/topic/overview.md` — its frontmatter `topic` and `display_name`
fields drive every UI surface that names the subject (rendered
section headers like `## {topic_display_name} Relevance`, archiver
User-Agent, etc.); the toolkit reads them via
`load_topic()`. Run `/fork-init` for the bootstrap walk-through.
Everything not deleted by the steps above — the rest of
`meta/` (schema, memory, templates, …), all of
`scripts/` and `prompts/`, the `.claude/` skills + subagents + hooks +
`settings.json`, and root-level governance (`CLAUDE.md`, `AGENTS.md`,
this `README.md`) — is topic-neutral toolkit and survives the fork.

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

---

## Node types

- **person** — named individuals (4 archetypes: eyewitness,
  whistleblower, institutional-actor, reporter)
- **organization** — institutions (3 kinds: gov, gov-contractor, private)
- **document** — text-native primary-source documents (2 kinds:
  gov-doc, non-gov-doc; plus `doc_form` metadata — article, book,
  testimony, memo, letter, contract, social-post, etc.). News
  articles and books live here, distinguished by `doc_form`.
- **event** — discrete events (2 kinds: hearing, encounter)
- **transcript** — verbatim text records of speech sources (2 kinds:
  hearing, other — `other` covers interview, podcast, broadcast,
  documentary, press conference, conference talk, deposition, etc.).
  Each transcript optionally points to an underlying media or
  document node via `derived_from`.
- **media** — non-text-native primary sources (4 kinds: photo, video,
  audio, imagery-other). Source files (UAP footage, photographs,
  satellite imagery, document scans pre-OCR) with metadata,
  provenance, and optional verbatim Key Passages for legible text or
  audible speech.
- **location** — non-institutional physical sites
- **finding** — multi-source primary-source patterns that become visible
  only by reading multiple sources together (convergence or divergence
  on a single question)
- **investigation** — open-ended hypothesis evaluation that consumes
  findings + entity-node facts. Speculation-tolerant; per-hypothesis
  status verdicts; cited findings + per-hypothesis sources rollups

Full specification in `meta/schema.yaml` (`architecture_layers`) for the
fact / finding /
investigation bright line.

**From schema to rendered node.** `meta/schema.yaml` defines each type's
required and optional sections; `meta/templates/{type}.md` scaffolds them
(via `scripts/build/new.py`); `scripts/build/renderers/{type}.py`
regenerates the node body from its research artifact (via
`build-from-research.py`). `scripts/build/renderer-coverage.py` gates the
chain at every commit: every schema section must be renderer-producible.

---

## Status markers

The repository records evidentiary state structurally, not with inline
emoji on every row. Two mechanisms carry it.

**Confirmed vs. Flagged splits.** Any section that mixes
primary-source-supported entries with secondary-source-only ones —
affiliations, relationships, organization key-personnel, event
participants — splits into `### Confirmed` and `### Flagged`
subsections:

| Subsection | Meaning |
|---|---|
| `### Confirmed` | Established from a primary source linked in the row |
| `### Flagged` | Cited in secondary sources only; awaiting primary-source confirmation |

`### Flagged` is omitted entirely when empty (a present-but-empty
Flagged subsection is a schema violation). The split records source
quality, not truth: a Flagged item may well be true — it just hasn't
been verified against a primary source yet. On finding nodes, each
evidence row's weight comes from a structured `attestation_tier` field
(`sworn-oath`, `dopsr-cleared`, `on-record`, `self-attested`, …) rather
than a marker.

**Cross-source disagreement.** Where sources conflict, the disagreement
is documented on the synthesis/finding node where it gains analytical
meaning, under `## Apparent Contradictions`. Two doctrinal labels
distinguish the cases by evidence quality:

| Label | Meaning |
|---|---|
| `⚠ Disputed — unknown` | Both sides assert; neither has primary-source evidence beyond its own authority to speak |
| `❌ Contradiction` | Positions conflict and at least one side is backed by primary-source evidence |

These frame how a finding is written; the repository documents both
sides and does not adjudicate.

---

## Skills and agents

Work in this repository runs through **skills** and **role subagents**,
defined under `.claude/`. A **skill** is an invokable workflow you start
with `/name`; it runs on the main thread and may dispatch subagents. A
**role subagent** is a capability-bounded worker a skill dispatches; its
tool set *is* its discipline — the boundaries are mechanical, not
conventional.

| Skill | What it does | Pipeline position |
|---|---|---|
| `/build` | Build or rebuild a node through the six-role pipeline | The pipeline orchestrator |
| `/prepare-ocr-sibling` | Produce + verify a clean-text sibling for an OCR-scanned source | `/build` step-4b sibling gate; also standalone |
| `/prepare-transcript-sibling` | Produce + verify a speaker-attribution sibling for a label-less transcript (auto-caption / Whisper) | `/build` step-4c sibling gate; also standalone |
| `/audit` | Health-check a built node for evidentiary integrity and consistency | Standalone maintenance on built nodes (reactive) |
| `/augment` | Targeted maintenance change without re-scaffolding | Standalone maintenance on built nodes (proactive; partial re-entry) |
| `/verify-transcript` | Verify a transcript node's quotes word-for-word against the archived source | Standalone maintenance on built nodes |
| `/quote-relevance-audit` | Check each quote is load-bearing for the node's subject | Standalone maintenance on built nodes |
| `/archive-sweep` | Verify local archives; recover dead URLs; submit missing to Wayback | Periodic / end-of-session health pass |
| `/fork-init` | Bootstrap the toolkit for a different topic | One-time, destructive |
| `build-protocol` | Shared contract preloaded into every build role | Not invokable |

The `/build` orchestrator dispatches the six role subagents in sequence —
internal-investigator → external-investigator → archive → worker (×N) →
builder → auditor: only `archive` writes the source manifest, only `worker`
introduces verbatim quotes, and the builder edits the research artifact,
never the rendered node. `/prepare-ocr-sibling` dispatches the two OCR page
agents (ocr-page-producer, ocr-page-verifier); `/prepare-transcript-sibling`
dispatches the two attribution agents (attribution-producer,
attribution-verifier). The pipeline map — steps,
stages, branches — is `.claude/skills/build/SKILL.md` ("The shape"); the
role-boundary rationale and the shared contract are
`.claude/skills/build-protocol/`.

`.claude/hooks/` enforce the discipline at the tool level: an un-bypassable
commit gate (`.githooks/pre-commit` runs `pre-commit.sh` inside `git commit`;
the PreToolUse guard arms it and denies the bypass routes), a block on
hand-editing rendered node bodies, and a one-new-synthesis-node-per-session
cap.

---

## Source preservation

Every external URL cited in any node is preserved through two
independent mechanisms:

1. **Local archive** — downloaded file in `/sources/{category}/` and
   registered in `sources/manifest.yaml`
2. **Wayback Machine** — submitted via `scripts/tools/archive.py`

The local archive is the integrity guarantee; Wayback is insurance.

See `meta/sources-access.md` for site-specific workarounds when a
source blocks automated retrieval (SEC, defense.gov, Twitter/X, etc).

---

## Origin

This toolkit originated from the need to separate documented UAP
public-record material from secondary-source claims repeated so often
they are mistaken for established fact. The structure is deliberately
topic-neutral — any investigation grounded in primary sources can use it.
