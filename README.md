# Primary-Source Investigation Toolkit

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
- Source data is never overwritten; updates are added alongside
  originals with `Superseded By` or `Contradicted By` pointers
- Evidentiary categories (eyewitness, whistleblower, institutional-actor,
  reporter; government, contractor, private; hearing, encounter;
  gov-doc, non-gov-doc) are separated structurally so a reader sees the
  evidentiary distinction before reading the content

See `meta/conventions.md` for the full philosophy.

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
AGENT.md                    first-read for AI agents querying the repo
CLAUDE.md                   session-start checklist for contributors
CONTRIBUTING.md             how to build a node
BACKLOG.md                  deferred work items (not on active roadmap)

meta/
  schema.yaml               machine-readable spec (source of truth)
  conventions.md            evidentiary philosophy (why the rules exist)
  sources-access.md         site-specific archival workarounds
  templates/                scaffolding templates (9 files)
  topic/                    THIS INSTANCE'S topic-specific content
    overview.md             topic statement, scope, corpora
    research-queue.md       priority investigation queue
    addenda/                corpus-specific rules (e.g., aawsap-dird)
  toolkit-notes/            toolkit lessons-learned (topic-neutral)
    pilot-failure-*.md      postmortems
    schema-migrations/      version-migration docs (populated as schema evolves)

scripts/
  new.py                    scaffolder — produces empty node from template
  validate.py               schema + structural + source-integrity validation
  manifest.py               manifest CLI (add, verify-paths, verify-checksums, …)
  archive.py                Wayback Machine submission
  transcribe.py             YouTube caption download
  associate.py              auto-generate Associated Nodes sections
  build-state.py            refresh CLAUDE.md build state
  audit-schedule.py         staleness tracker for research artifacts (Phase D)

sources/
  manifest.yaml             source-archival index (YAML; sha256-checksummed)
  government/               government primary sources (PDFs, HTML)
  news/                     news article HTML snapshots
  social/                   social media post snapshots
  transcripts/              downloaded YouTube / broadcast transcripts
  video/                    video-adjacent content

people/ organizations/ documents/ events/ transcripts/
news/ books/ locations/ findings/
                            content nodes (human-readable narrative)

research/                   research artifacts (machine-readable atomic
                            facts backing each node) — populated in Phase D

prompts/                    paste-ready session prompts
```

**Forking for a different topic.** Delete `meta/topic/` and everything
under `/people/`, `/organizations/`, `/documents/`, `/events/`,
`/transcripts/`, `/news/`, `/books/`, `/locations/`, `/findings/`,
`/research/`, and empty `sources/manifest.yaml`. Everything else is
topic-neutral toolkit. See `AGENT.md` for fork procedure details.

---

## Node types

- **person** — named individuals (4 archetypes: eyewitness,
  whistleblower, institutional-actor, reporter)
- **organization** — institutions (3 kinds: gov, gov-contractor, private)
- **document** — primary-source documents (2 kinds: gov-doc,
  non-gov-doc; plus `doc_form` metadata)
- **event** — discrete events (2 kinds: hearing, encounter)
- **transcript** — testimony or interview transcripts (2 kinds:
  hearing, interview)
- **news** — news articles as publication records
- **book** — published books as publication records (never evidence
  of claims)
- **location** — non-institutional physical sites
- **finding** — cross-entity patterns that span 3+ nodes

Full specification in `meta/schema.yaml`.

---

## Status markers

Four status markers document evidentiary state throughout the repository:

| Marker | Meaning |
|---|---|
| `✅ Confirmed` | Verified against a linked primary source |
| `⏳ Pending` | Claimed or cited; not yet verified |
| `⚠ Flagged` | Secondary-source only; requires primary-source confirmation |
| `⚠ Disputed — unknown` | Both sides assert; neither has primary-source evidence |
| `❌ Contradiction` | Positions contradict and at least one side is backed by primary-source evidence |

Relationship tables, affiliations, and evidence sections split into
`### Confirmed` and `### Flagged` subsections. Flagged subsections are
omitted when empty.

---

## How to start

### New contributor

Paste `prompts/onboard.md` into a fresh Claude Code session. It reads
the governance docs, runs the validator, and shows current state.

If you'd rather read directly, start with `CONTRIBUTING.md`.

### Returning contributor

`CLAUDE.md` is the session-start checklist. Run the health check:

```
python3 scripts/validate.py
python3 scripts/build-state.py --check
```

Then pick work from `meta/topic/research-queue.md`.

---

## Source preservation

Every external URL cited in any node is preserved through two
independent mechanisms:

1. **Local archive** — downloaded file in `/sources/{category}/` and
   registered in `sources/manifest.yaml`
2. **Wayback Machine** — submitted via `scripts/archive.py`

The local archive is the integrity guarantee; Wayback is insurance.

See `meta/sources-access.md` for site-specific workarounds when a
source blocks automated retrieval (SEC, defense.gov, Twitter/X, etc).

---

## Origin

This toolkit originated from the need to separate documented UAP
public-record material from secondary-source claims repeated so often
they are mistaken for established fact. The structure is deliberately
topic-neutral — any investigation grounded in primary sources can use it.
