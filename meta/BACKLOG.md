---
id: meta/BACKLOG
type: meta
---

# BACKLOG

Deferred work — real, concrete, and would be lost otherwise; not on the
active roadmap. An item leaves when promoted to a roadmap phase, addressed,
or superseded.

## How this file works

**This file is self-governing** — it is the root authority for how the
BACKLOG is written, identified, and closed. Nothing outside it governs it.

**Sections.** Open items are partitioned by dependency shape:
**A — Priority sequence** (ordering / coupling constraints),
**B — Parallel batch** (renderer-pass items that ship together),
**C — Anytime** (no upstream blockers). **Default focus is C:** no
dependencies, finishable in one pass. Reserve A and B for sessions scoped
to them — starting a constrained item out of order half-bakes it and
clutters the file. Cross-reference entries with `**Blocks:**` /
`**Blocked by:**` lines so the dependency graph stays inline.

**Identifiers** (A1, B1, C1…) are positional working labels, not stable
IDs. A new entry takes the lowest unused number in its section, so numbers
**recycle**; once a section — and ultimately the whole BACKLOG — is cleared,
numbering restarts from 1. Because an ID is transient, **never reference it
outside this file** — not in code, docs, prompts, commit messages, or
`git log` searches. Describe the work; the commit diff + message are the
record.

**Opening an entry.** Write it forward-looking and prescriptive: the work
and why it matters. No "Surfaced from", audit/session label, or commit hash
pinning when the need arose — that history lives in `git log`.

**Closing an entry.** The goal is to REMOVE items, not annotate them.
Delete the block in full — no retirement marker, no placeholder; the
shipping commit's diff + message is the canonical record. Then sweep any
code comments that cited the closed ID (delete them, or rewrite to describe
current behavior) — that sweep is part of closing, not follow-up.

**Externally-blocked items** waiting on an event the repo can't drive (FOIA
resolution, registry access, third-party publication) live, when
topic-specific, in `meta/topic/research-queue.md` "Externally blocked". If a
genuinely toolkit-neutral one ever surfaces (rare), reinstate an "Externally
blocked" heading at the foot of this file.

---

## A. Priority sequence

Items with ordering or coupling constraints.

### A1 — Exercise the pipeline paths the first whole run didn't hit

The six-role pipeline (the `/build` skill + `.claude/agents/`) has been run *whole* on one
real node build — a user-directed, all-internal institutional-actor build:
Internal Investigator → Worker (×N) → Build → Audit, with handoff stubs
captured and friction tightened in place. The **External Investigator
(role 2) and Archive (role 3)** roles have since been exercised standalone on
an existing node — a source-recovery that re-pulled a dead JavaScript-shell
capture from a Wayback snapshot (External Investigator confirmed the snapshot
and captured verbatim spans; Archive re-pulled the file and refreshed the
manifest). Both behaved per contract. Paths still unverified end-to-end:

- **role 2 + role 3 integrated inside a full `/build`** with a genuine
  external-source gap — so far they have run standalone, not as the
  external-gap branch of a fresh orchestration.
- the **`foia` worker kind** — `caption` is now exercised (the all-internal
  `jre-2194-elizondo-2024` transcript build hit it end-to-end: internal-survey →
  caption worker → builder → audit). `pdf` + `html` + `caption` done; only `foia`
  remains, and no load-bearing *unarchived* FOIA source currently exists to build
  (every referenced FOIA doc is already archived) — wait for a genuine FOIA gap
  rather than manufacturing one.
- **error routing** (`route_failure.py`) — no validator failure has needed
  routing on a clean run (the caption build was clean; its audit findings were
  applied via builder re-entry, not a routed check failure; the dird-32 build
  repeated that shape — clean run, one recommend-only locator fix via builder
  re-entry). The dird-32 build did newly exercise the **OCR sibling gate (4b)
  inside a full `/build`** end-to-end (producers → consensus → verifiers →
  registration), so that path no longer needs a dedicated run.

Drive a build that forces these paths (a target with an external-source
gap + a caption/FOIA source); confirm each `--phase X` fires exactly the
checks reading role X's state; tighten friction in place where cheap, file a
new entry where not.

**Deferred follow-on:** split `prose_drift` into `prose_drift_toplevel`
(organize phase) + `prose_drift_notes` (link phase) only if one-phase-late
surfacing of top-level prose drift proves annoying.

**Blocks:** none.
**Blocked by:** a user-directed build with an external-source gap.

---

## B. Parallel batch (renderer pass)

Renderer-touching items that batch into a single polish pass.

_(none)_

---

## C. Anytime (no dependencies)

No upstream blockers; safe to pick up in any session. Default-focus tier.

### C1 — Ingest a book delivered as page images into a verified text transcription

A book (or any long document) delivered as a directory of page images — cover,
back, and each non-blank page — should become a single verified `.txt`
transcription that serves as the citeable primary source. This is far more
content than the repo ingests today (single sources, not multi-hundred-page
collections), so the route must be deliberate, not an afterthought.

The transcription machinery already exists and is reusable: the VLM page-image
read + dual-OCR consensus (`scripts/tools/ocr-consensus.py`) and the
`ocr-page-producer` / `ocr-page-verifier` agents, which already read page
IMAGES one at a time and settle divergences against them. What is missing is
image-directory input: `ocr-consensus.py` is bound to PDF (`pdfinfo` for page
count, `pdftoppm` to rasterize). Generalize it to accept a directory/list of
page images (skip rasterization; page count from the file list), and generalize
the `/prepare-ocr-sibling` skill (or add a sibling skill) to dispatch the
producers across image-file ranges the way it fans out over PDF page ranges.
`extract_source_text` already reads a committed `.txt` sibling for an image
source, and such a transcription earns real verification (a quote that does not
match the sibling errors), so the quote-citation rail is already in place.

Open design considerations to settle before building:
- **Assembly target.** After transcribing, consider combining the pages into a
  text-layer (searchable) PDF, which would then ingest through the existing
  text-native PDF route and sidestep any image-collection manifest schema.
  Weigh this against registering the `.txt` as the primary source with the
  page-image directory as archived provenance.
- **Manifest convention.** No "collection" entry exists today (the manifest
  registers single artifacts). Decide: txt-as-primary + image-dir provenance, a
  new image-collection entry, or the text-PDF above.
- **Scale.** OCR cost is per-page; a multi-hundred-page book is a long consensus
  run with content-filter blocks handled per page — confirm the scratch layout,
  caching, and single-sibling assumptions hold at that size before committing to
  a real book.
- **Location grammar.** The transcription is flat text (no synthetic page
  markers), so book quotes anchor via the `¶ "<leading phrase>"` descriptive
  form that resolves against the sibling.

**Blocks:** none.
**Blocked by:** none.

### C2 — Investigate whether the Description "no-duplication" convention should relax

The maintainer wants `## Description` to read as a well-defined summary that may
surface select salient items also living in a structured section (a key
relationship, timeline event, contract, finding). The current convention pushes
the other way — the builder's date-grade discipline (`.claude/agents/builder.md`,
"Date grade + period fields") states *don't restate in prose a field-precise date
the table already carries* because *that duplication is a drift surface*. That
anti-drift rationale is load-bearing, so a relaxation could easily go bad; it is
deferred for investigation, not changed in place.

Avenues to weigh before any edit: (a) survey how built nodes actually use
Description today — is the overlap pressure real or rare?; (b) whether the
carve-out should stay field-precise-only (exact dates / dollar amounts / control
numbers single-sourced in their table; orientation-grade overlap allowed); (c)
whether the `description_token_drift` check needs any change (it checks grounding,
not overlap, so likely none). Produce a recommended wording, then edit the
convention and record the rationale.

**Blocks:** none.
**Blocked by:** none.

### C3 — Reconcile the duplicate-stub clusters `stub-reconcile.py` surfaces

The mechanism is shipped. An initial people pass reconciled the
initials-vs-full-name duplicates (`/people/v-teofilo` → `vincent-teofilo`, plus
the cited-physicist pairs Fermi / Feynman / Forward / Hawking / Sakharov /
Shannon / Davies). The standing tool + pipeline integration then followed:
`scripts/tools/stub-reconcile.py` computes the complete coined-stub set (built
∪ every artifact's references) and surfaces candidate duplicate clusters
(NER-free; *initials* rule for people, generic-word-guarded *subset* rule for
orgs); it is wired into the internal-investigator reuse survey, the builder's
slug-coinage step, and the auditor's cold re-read. The root cause — the reuse
survey seeing only *built* nodes — is closed to the extent it can be: the tool
surfaces an existing unbuilt stub at coinage, but it is a judgment aid, not a
gate (same-surname-different-person is legitimate).

What remains is **running the sweep and applying per-cluster judgment** — the
work the tool can't do itself:

- **Candidate clusters the sweep surfaces — source-confirm each before
  merging; slug-shape confidence is NOT entity confidence.** A spot check
  already disproved several "obvious" merges: `aircraft-nuclear-propulsion` and
  `nuclear-energy-for-propulsion-of-aircraft` are the *distinct* predecessor
  (NEPA) and successor (ANP) programs, not one entity; `/people/morris` (a
  biology-DIRD reference) is almost certainly not the wormhole physicist
  `michael-morris`; `/people/einstein` and `newton` appear in eponym
  constructions ("Einstein's field theory"), so the eponym carve-out may apply
  rather than a merge. Candidates that still look clean but need the same
  per-source confirmation: `/people/carter` → `jimmy-carter`, `ratcliffe` →
  `john-ratcliffe`; `/organizations/mitre` → `mitre-corporation`, `oak-ridge` →
  `oak-ridge-national-laboratory`, `house-of-representatives` →
  `united-states-house-of-representatives`, the two `institute-for-advanced-
  studies-(at-)austin` slugs. Canonicalize a confirmed-same-entity cluster to
  the fullest source-attested form and re-render; leave the rest.
- **Genuinely ambiguous / part-whole clusters** that must be ruled on, not
  merged: distinct people sharing a surname (`gerald-ford` / `l-ford` [physicist
  L. H. Ford] / `lonye-ford`; `d-brown` / `dean-brown`; the bare `smith` /
  `johnson` / `sherman` hubs); and org part-whole pairs that are *not*
  duplicates (`boeing` / `boeing-phantom-works`; the NASA centers; `us-air-force`
  / `us-air-force-academy`; `university-of-alabama` / `…-huntsville`).

**Blocks:** none.
**Blocked by:** none.
**Related:** the [[link-all-load-bearing-references]] working-memory note;
`scripts/tools/stub-reconcile.py` is the tool; the `link_resolution` broken-link
registry is the data it reads.
