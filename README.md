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
- Source data is never overwritten — or silently cleaned: the repository
  records sources verbatim, preserving their artifacts (OCR errors, typos)
  and flagging them rather than correcting them. Updates are added
  alongside originals with `Superseded By` or `Contradicted By` pointers
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
  README.md                 friendly-face index of the directory
  BACKLOG.md                deferred work items (not on active roadmap)
  roadmap.md                active work + design decisions that shaped the codebase
  schema.yaml               machine-readable spec (source of truth)
  conventions.md            evidentiary philosophy (why the rules exist)
  sources-access.md         site-specific archival workarounds
  templates/                scaffolding templates (9 files, one per node type)
  research/                 YAML research artifacts backing each node
                            (structured facts; one per content node)
  topic/                    THIS INSTANCE'S topic-specific content
    overview.md             topic statement, scope, corpora
    research-queue.md       priority investigation queue
    working-notes/          in-progress synthesis docs awaiting integration into content nodes

scripts/
  build/                    build pipeline + validators (contributor-facing)
    new.py                  scaffolder — produces empty node from template
    research-scaffold.py    scaffold the research artifact backing a node
    extract-source.py       extract primary sources to plaintext (Phase I)
    build-from-research.py  orchestrator — regenerates node body from artifact (Phase II)
    renderers/              per-type renderer modules dispatched by
                            build-from-research.py — _common.py, _universal.py,
                            and one module per node type
                            (document / person / event / transcript / media /
                            organization / location / finding / investigation)
    review-coverage.py      Phase III coverage / boundary / stub-linking / description-drift review
    validate.py             node structural + verbatim-quote + source-integrity validation
    validate-research.py    research-artifact structural validation
    associate.py            auto-generate Associated Nodes sections
    build-state.py          refresh CLAUDE.md build state
  tools/                    standalone utilities + diagnostics
    manifest.py             manifest CLI (add, verify-paths, …)
    archive.py              Wayback Machine submission
    transcribe.py           YouTube caption download (auto-fallback to yt-dlp; --cookies - reads from stdin)
    extract-firefox-cookies.py  Firefox cookies → stdout (memory-only; pipe into transcribe.py --cookies -)
    check-vocab.py          pre-flight prose-drift token check (contributor diagnostic)
    coverage-suggest.py     source-coverage audit aid (read-only; surfaces under-extraction candidates)
    normalize-locations.py  quote `source.location` ref diagnostic (read-only)
    download-video.py       canonical video archival (yt-dlp wrapper; 480p mp4 default; manifest registration)
    extract-frames.py       ffmpeg frame extraction — anchor / burst / sweep / transcript modes
    detect-faces.py         Haar-cascade face detection + pHash dedup + persistent baselines/manifest
    diarize-audio.py        pyannote.audio speaker diarization (identity-blind SPEAKER_NN; project-local venv)
    stitch-transcript.py    merges video + diarize segments + identity baselines → speaker-labeled transcript (/tmp/ contributor diagnostic)
    setup-photo-identity.sh one-time installer for the visual-side video pipeline (cv2, yt-dlp, ffmpeg, JS runtime)
    setup-diarize-audio.sh  one-time installer for the audio-side diarize step (pyannote, torch, HF_TOKEN walk-through)
    VIDEO-PIPELINE.md       five-step workflow doc (download → diarize → extract → detect → stitch)
  checks/                   per-check modules — every named validator check
                            lives here as its own file; build/validate.py /
                            build/validate-research.py / build/review-coverage.py
                            are thin orchestrators that import and dispatch
                            them via explicit step lists
  lib/                      shared cross-script helpers (source extraction,
                            HTML cleanup, quote normalization, frontmatter
                            parse) — imported by both the orchestrators and
                            the per-check modules; keeps mechanical lockstep
                            across them

scripts/tests/
  pre-commit.sh             canonical all-gates health check (chains every gate:
                            help-check / test_stopwords / smoke / build/validate.py /
                            build/validate-research.py / build/review-coverage.py /
                            build/build-state.py --check / build/renderer-coverage.py /
                            phase-routing-parity / skills-check / file-size-check /
                            cookies-check)
  help-check.sh             confirms every scripts/{build,tools}/*.py --help exits 0
  test_stopwords.py         STOPWORDS shape + content-word regression test
  smoke.py                  fixture-based new.py + validator smoke tests
                            (single-process; ProcessPoolExecutor over fork)
  file-size-check.sh        warn 50MB / error 100MB on git-tracked files
                            (per meta/sources-access.md large-file discipline)
  cookies-check.sh          block commits containing Netscape cookies content
                            or Google session cookies in Netscape-shape rows
                            (defensive backstop to .gitignore patterns)

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
  skills/                   invokable workflows — /build, /onboard, /audit,
                            /verify-transcript, /quote-relevance-audit,
                            /archive-sweep, /fork-init — plus the build-protocol
                            contract preloaded into the role subagents
  agents/                   the six build role subagents (internal-investigator,
                            external-investigator, archive, worker, builder, auditor)
  hooks/                    PreToolUse guards — commit gate (runs pre-commit.sh),
                            node-body-edit block, one-new-synthesis-node cap
  settings.json             hook wiring (committed; topic-neutral)

prompts/                    design docs (topology.md) + Claude-Web
                            briefs — see prompts/README.md for the index
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
`meta/` (schema, conventions, memory, templates, …), all of
`scripts/` and `prompts/`, the `.claude/` skills + subagents + hooks +
`settings.json`, and root-level governance (`CLAUDE.md`, `AGENT.md`,
this `README.md`) — is topic-neutral toolkit and survives the fork.

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

Full specification in `meta/schema.yaml`. See `meta/conventions.md`
"Three-layer evidentiary architecture" for the fact / finding /
investigation bright line.

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
sides and does not adjudicate. See `meta/conventions.md`
("Confirmed vs Flagged", "Contradictions") for the full discipline.

---

## Skills and agents

Work in this repository runs through **skills** and **role subagents**,
defined under `.claude/`.

A **skill** is an invokable workflow you start with `/name`; it runs on the
main thread and may dispatch subagents. The user-facing skills:

- `/onboard` — orient at session start (read governing docs, health-check, report state)
- `/build` — build or rebuild a node through the full multi-agent pipeline
- `/audit` — health-check a built node for evidentiary integrity and consistency
- `/augment` — make a targeted maintenance change to a built node without re-scaffolding
- `/verify-transcript` — verify a transcript node's quotes against the archived source, word-for-word
- `/quote-relevance-audit` — check that each quote is load-bearing for the node's subject
- `/archive-sweep` — verify every cited URL is archived locally and recover/submit what's missing
- `/prepare-ocr-sibling` — produce and verify a clean-text sibling for an OCR-scanned source before quoting it
- `/fork-init` — bootstrap the toolkit for a different topic

A **role subagent** is a capability-bounded worker the `/build` orchestrator
dispatches in sequence — internal-investigator → external-investigator →
archive → worker → builder → auditor. The boundaries are mechanical, not
conventional: only `archive` writes the source manifest, only `worker`
introduces verbatim quotes, and the builder edits the research artifact
rather than the rendered node. `build-protocol` is the shared contract
preloaded into each role; it is not a skill you invoke.

`.claude/hooks/` enforce the discipline at the tool level: an un-bypassable
commit gate (runs `pre-commit.sh`), a block on hand-editing rendered node
bodies, and a one-new-synthesis-node-per-session cap.

Deeper detail: `AGENT.md` ("Route by task") maps a goal to the right skill;
`prompts/topology.md` is the design rationale for the role decomposition; the
contract itself lives in `.claude/skills/build-protocol/`.

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
