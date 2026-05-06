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
  reporter; gov, gov-contractor, private; hearing, encounter;
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

meta/
  BACKLOG.md                deferred work items (not on active roadmap)
  schema.yaml               machine-readable spec (source of truth)
  conventions.md            evidentiary philosophy (why the rules exist)
  sources-access.md         site-specific archival workarounds
  templates/                scaffolding templates (8 files, one per node type)
  research/                 YAML research artifacts backing each node
                            (structured facts; one per content node)
  topic/                    THIS INSTANCE'S topic-specific content
    overview.md             topic statement, scope, corpora
    research-queue.md       priority investigation queue
    addenda/                corpus-specific rules (e.g., aawsap-dird)
    working-notes/          in-progress synthesis docs awaiting integration into content nodes
  toolkit-notes/            toolkit lessons-learned (topic-neutral)

scripts/
  new.py                    scaffolder — produces empty node from template
  research-scaffold.py      scaffold the research artifact backing a node
  extract-source.py         extract primary sources to plaintext (Phase I)
  build-from-research.py    regenerate node body from its research artifact (Phase II)
  review-coverage.py        Phase III coverage / boundary / stub-linking / description-drift review
  validate.py               node structural + verbatim-quote + source-integrity validation
  validate-research.py      research-artifact structural validation
  manifest.py               manifest CLI (add, verify-paths, verify-checksums, …)
  archive.py                Wayback Machine submission
  transcribe.py             YouTube caption download
  associate.py              auto-generate Associated Nodes sections
  build-state.py            refresh CLAUDE.md build state
  checks/                   per-check modules — every named validator check
                            lives here as its own file; validate.py /
                            validate-research.py / review-coverage.py are
                            thin orchestrators that import and dispatch
                            them via explicit step lists
  lib/                      shared cross-script helpers (source extraction,
                            HTML cleanup, quote normalization, frontmatter
                            parse, schema_version compat) — imported by
                            both the orchestrators and the per-check
                            modules; keeps mechanical lockstep across them

scripts/tests/
  pre-commit.sh             canonical all-gates health check (chains 7 gates:
                            help-check / test_stopwords / smoke / validate.py /
                            validate-research.py / review-coverage.py /
                            build-state.py --check)
  help-check.sh             confirms every scripts/*.py --help exits 0
  test_stopwords.py         STOPWORDS shape + content-word regression test
  smoke.sh                  fixture-based new.py + validator smoke tests

sources/
  manifest.yaml             source-archival index (YAML; sha256-checksummed)
  government/               government primary sources (PDFs, HTML)
  news/                     news article HTML snapshots (news articles
                            are stored here as source material; content
                            nodes live under /documents/)
  social/                   social media post snapshots
  transcripts/              downloaded YouTube / broadcast transcripts
  video/                    video-adjacent content

people/ organizations/ documents/ events/ transcripts/
media/ locations/ findings/
                            content nodes (human-readable narrative)

prompts/                    paste-ready session prompts — see prompts/README.md for the index
```

**Forking for a different topic.** Delete `meta/topic/`,
`meta/research/`, and the contents of `/people/`, `/organizations/`,
`/documents/`, `/events/`, `/transcripts/`, `/media/`, `/locations/`,
`/findings/`, and `sources/{category}/` (keep the directories
themselves); empty `sources/manifest.yaml`. Create your own
`meta/topic/overview.md` — its frontmatter `topic` and `display_name`
fields drive every UI surface that names the subject (rendered
section headers like `## {display_name} Relevance`, archiver
User-Agent, etc.); the toolkit reads them via
`load_topic()`. See `prompts/fork-init.md` for the bootstrap walk-
through. Everything else — schema, conventions, scripts, templates,
prompts, validators, test suite — is topic-neutral toolkit.

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
- **finding** — cross-entity patterns that span 3+ nodes

Full specification in `meta/schema.yaml`.

---

## Status markers

Five status markers document evidentiary state throughout the repository:

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

If you'd rather read directly, start with `meta/conventions.md` (the
evidentiary standard) and `meta/schema.yaml` (the structural spec),
then paste `prompts/build.md` when you're ready to build a node.

### Returning contributor

`CLAUDE.md` is the session-start checklist. Run the canonical all-gates
health check:

```
bash scripts/tests/pre-commit.sh
```

This chains 7 gates: help-check / test_stopwords / smoke /
`validate.py` / `validate-research.py` / `review-coverage.py` /
`build-state.py --check`. Then pick work from
`meta/topic/research-queue.md`.

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
