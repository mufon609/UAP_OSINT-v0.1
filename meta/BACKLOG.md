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

### C3 — Decide whether the document renderer should surface `extrinsic_authorship`

A document research artifact can carry author attribution — and `[[wraps]]` to the
person/source that attests it — in `context_extrinsic.extrinsic_authorship`, used
when the author is redacted in the document body and known only from an external
index (the redacted-author convention in `scripts/checks/prose_drift.py`). But
`scripts/build/renderers/document.py` does not consume that field, so any node link
wrapped there never reaches the rendered body or `## Associated Nodes`. On a
redacted-author DIRD the `[/people/...]` author wrap and sibling-document wrap placed
in `extrinsic_authorship` are silently dropped; the authorship stays reachable
navigationally via the rendered attesting-document link, so the node is not wrong —
but the wraps are dead weight that reads as a working link.

Decide one of: (a) teach `document.py` to surface `extrinsic_authorship` so its wraps
feed `associate.py` corpus-wide — weighed against the redacted-author convention's
intent that such an author is *carried by the link*, not asserted on the node; or
(b) confirm the field is structured-metadata-only and add a guard/lint so
contributors don't wrap links there expecting them to render.

**Blocks:** none.
**Blocked by:** none.

### C4 — Finish the `associated_entities` rollout across the corpus

**Shipped already (the rule + mechanism).** The black-and-white linking rule —
*the decision to ingest a source IS the relevance decision; every load-bearing
entity the source names reaches `## Associated Nodes`, no "node-worthy /
topically relevant" filter* — is codified in build-protocol ("Linking — ingest
is the relevance decision") and the worker / builder / auditor roles. The
mechanism is the `associated_entities` artifact field (the complete, deduped
list of every source-named entity), unioned into `## Associated Nodes` by
`associate.py` and validated by `scripts/checks/associated_entities.py`. It
exists because an entity named only inside a verbatim quote can't be wrapped
(the verbatim check rejects a link in `quote.text`), so a thin `description`
used to silently drop it. DIRD-33/34/35 are re-swept, and the **`/re-associate`
skill + `re-associate-producer` / `re-associate-verifier` agents are built** —
the link-layer-only pass (re-read source → producer enumerates the complete
source-named-entity set → independent verifier challenges completeness/correctness
→ apply to `associated_entities` → re-render). **Two things remain, both
corpus-scale:**

**1. Run the sweep across the corpus.** Every node built before the field
under-links — the gap is corpus-wide and homogeneous (the DIRD series alone ran
0–14 people-links across documents of the same kind). Run `/re-associate` against
each pre-rule node, one at a time, committing each before the next (an agent's
effective Bash can `git restore` uncommitted work). The skill changes nothing but
the link layer: no quotes, no facts, no prose rewording; it edits only the
artifact's `associated_entities` field (plus an inline wrap for any entity the
`description` already names), never the node body and never the `## Associated
Nodes` section directly; verbatim + prose-drift gates read clean before and after.
The same skill is the standing pass for keeping new ingests honest — including the
recent government-document releases (same name-dense-PDF shape; ingest under this
rule from the start).

**2. Flip the field to required.** Once the corpus is swept, make
`associated_entities` REQUIRED on document / transcript / media target types
(error on absence in `associated_entities.py` / `artifact_top_level.py`) — the
final mechanical lock that turns "mandatory by build discipline" into "mandatory
by gate." Until then the field stays optional so un-swept nodes hold the
0-warning clean baseline.

**Blocks:** none.
**Blocked by:** none (rule + mechanism shipped).
**Related:** C3 — the `extrinsic_authorship`-not-rendered gap a re-associate pass
would surface on redacted-author nodes; the existing `/augment` skill, which the
re-associate agent narrows to the link layer alone. The principle is the
[[link-all-load-bearing-references]] working-memory note.

### C5 — Dedupe stub slugs that name the same entity across artifacts

**The issue.** Two artifacts can mint *different* stub slugs for the same
not-yet-built entity, because the only reuse check (in the worker and the
`re-associate-producer`) matches against *built* nodes — an unbuilt stub another
artifact already coined is invisible. Surfaced by the dird-30 re-associate run:
`/people/v-teofilo` (dird-30 `extrinsic_authorship`) vs `/people/vincent-teofilo`
(dird-24) name the same person (V. Teofilo / Vincent Teofilo, Lockheed Martin).
The broken-link / Priority-Build registry then carries two entries for one
person; whichever node is built first orphans the other reference.

**The work.** A reconcile pass over the broken-link registry / all artifacts that
groups stub paths likely naming one entity (surname + initials match, alias
overlap) and canonicalizes each cluster to a single slug — preferring the fullest
source-attested form (`vincent-teofilo` over `v-teofilo` when a source attests
"Vincent"). Mechanically: a diagnostic that lists candidate duplicate-stub
clusters for contributor judgment (NER-free, like `prose_entity_link`'s
whole-phrase matching), then edit the losing artifacts' wraps/fields to the
canonical slug and re-render. Could fold into the `/re-associate` corpus sweep
(the producer gains an "existing stubs across artifacts" index) or stand alone.

**Blocks:** none.
**Blocked by:** none.
**Related:** C4 (the re-associate sweep that surfaces these); the
`link_resolution` broken-link registry is the natural input.

### C6 — Sweep named places into `/locations/` nodes (corpus-wide)

The `associated_entities` sweep (C4) links people / organizations / programs /
events / documents but **defers places**. The black-and-white linking rule covers
a named place as much as any other entity — a place has a host node-type
(`/locations/`) — but the corpus today holds essentially one location node
(`skinwalker-ranch`), and the sweep is being run with places held out, so applying
it mid-sweep would leave the corpus half-converted. Run a dedicated places pass
once the entity sweep is complete: settle the line between a **substantive named
place** (a discussed site → `/locations/` node) and a **bare locative qualifier**
(merely situating an org/event — "the institute in St. Petersburg", "efforts in
Japan"), then apply it uniformly across ALL nodes, including every node the entity
sweep already touched (`dird-01..05`, `30`, `33`, `34`, `35`, and the rest). The
re-associate producer/verifier definitions already state "a named place →
`/locations/`"; this pass is where that clause is exercised and the
place/locative boundary is settled.

**Blocks:** none.
**Blocked by:** the C4 entity sweep (run places after it, for uniformity).
**Related:** C4 (the entity sweep that defers places).
