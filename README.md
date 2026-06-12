# Primary-Source Investigation Toolkit

*The human entry point: what this repository is and why it exists. How to
use it once it holds nodes — and how to read a node's evidentiary state —
is `INVESTIGATOR.md`; the consumer query protocol is `AGENTS.md`;
contributor mechanics (repository layout, the build pipeline, the
skills/agents map) are `CLAUDE.md`.*

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

## Node types — the investigator's working set

The repository's content is a set of **nodes**: human-readable narrative
files an investigator reads directly and composes in queries. Each type
separates an evidentiary category structurally, so a reader sees the
distinction before reading the content.

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
fact / finding / investigation bright line.

**Nodes are a composable working set.** The fastest way to use the corpus
is to point the CLI at one or more node files and ask a synthesis question
— `@people/{a} @people/{b} — what do they share in common?`, or
`@events/{e} @transcripts/{t} — does the testimony match the event
record?` Each node carries an `## Associated Nodes` section linking the
related people, organizations, documents, and events, so one node fans out
to its neighbours. The full consumer workflow — node composition vs. the
structured research-artifact query — is `AGENTS.md` ("The investigator
workflow").

---

## Where the mechanics live

This README is the what-and-why. The how lives alongside it:

- **`INVESTIGATOR.md`** — how to use the repo once it holds nodes: why
  primary-source grounding beats an untrained model, how to wield it, and
  how to read a node's evidentiary state (`### Confirmed` vs `### Flagged`).
- **`AGENTS.md`** — the consumer query reference: how an investigator
  queries the corpus (node composition + the structured research-artifact
  protocol).
- **`CLAUDE.md`** — the contributor reference: repository layout, the
  end-to-end build pipeline (source → node), and the skills/agents map.
- **`scripts/README.md`** · **`meta/schema.yaml`** · the `.claude/` SKILLs
  — per-script, per-field, and per-role depth.

**Source preservation.** Every cited URL is preserved two independent
ways: a local archive under `/sources/` registered in
`sources/manifest.yaml` (the integrity guarantee) and a Wayback Machine
snapshot (insurance). See `meta/sources-access.md` for site-specific
workarounds when a source blocks automated retrieval.

---

## Forking for a different topic

The structure is deliberately topic-neutral — any investigation grounded
in primary sources can use it. Forking to a new topic deletes the content
layer and this instance's topic files (`meta/topic/`, `meta/research/`,
and the node directories), keeping the toolkit (`scripts/`, `.claude/`,
the schema, templates, and the root governance docs), then declares a new
subject in `meta/topic/overview.md`. Run `/fork-init` for the bootstrap
walk-through; the exact delete-list and the layout it operates on are in
`CLAUDE.md` ("Repository layout").

---

## Origin

This toolkit originated from the need to separate documented UAP
public-record material from secondary-source claims repeated so often
they are mistaken for established fact. The structure is deliberately
topic-neutral — any investigation grounded in primary sources can use it.
