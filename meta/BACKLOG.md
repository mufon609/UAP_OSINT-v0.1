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
Shannon / Davies); a later source-confirmed pass canonicalized `ratcliffe` →
`john-ratcliffe`, `mitre` → `mitre-corporation`, `oak-ridge` →
`oak-ridge-national-laboratory`, `house-of-representatives` →
`united-states-house-of-representatives`, the two
`institute-for-advanced-studies-(at-)austin` slugs, `skunk-works` →
`lockheed-martin-skunk-works`, and `hathaway-consulting` →
`hathaway-consulting-services`. The standing tool + pipeline
integration then followed:
`scripts/tools/stub-reconcile.py` computes the complete coined-stub set (built
∪ every artifact's references) and surfaces candidate duplicate clusters
(NER-free; *initials* rule for people, generic-word-guarded *subset* rule for
orgs); it is wired into the internal-investigator reuse survey, the builder's
slug-coinage step, and the auditor's cold re-read. The root cause — the reuse
survey seeing only *built* nodes — is closed to the extent it can be: the tool
surfaces an existing unbuilt stub at coinage, but it is a judgment aid, not a
gate (same-surname-different-person is legitimate).

The current sweep is now fully adjudicated. Beyond the canonicalizations above,
the source+web pass ruled every remaining candidate cluster DISTINCT — including
two slug-shape traps this rule exists to catch: `/people/carter` ≠ `jimmy-carter`
(the JRE "carter" is Howard Carter the archaeologist, in a King-Tut analogy) and
`/people/b-miller` ≠ `bruce-miller` (the dird-24 "Miller, B." is Berndt Müller,
theoretical-physics co-author of *The Structured Vacuum*, not the Sandia
pulsed-power engineer Bruce Miller). **Standing rule for future sweeps:
source-confirm each candidate before merging — slug-shape confidence is NOT
entity confidence — and where the person or context is not obvious from the
artifact alone, confirm it BOTH at the source document AND on the web before
ruling.**

Ruled DISTINCT / part-whole / eponym — left as expected sweep noise:

- distinct people sharing a surname or initial: `carter` [Howard Carter,
  archaeologist] ≠ `jimmy-carter`; `b-miller` [Berndt Müller] ≠ `bruce-miller`;
  `a-robinson` [A. L. Robinson, Science writer] ≠ `art-robinson`; `c-anderson`
  [positron-physics citation] ≠ `charles-a-anderson` [SRI president]; `h-j-kim`
  [IEC-fusion physicist] ≠ `h-kim`; `d-brown` [1948 FBI agent D. K. Brown] ≠
  `dean-brown` [SRI parapsychology associate]; `daniel` [Uri Geller's son] ≠
  `daniel-kimmage` [State Dept GEC]; `/people/morris` [biology-DIRD] ≠
  `michael-morris` [wormhole physicist]; `gerald-ford` / `l-ford` [physicist
  L. H. Ford] / `lonye-ford`; the bare `smith` / `johnson` / `sherman` hubs.
- eponym constructions: `einstein`, `newton` in "Einstein's field theory".
- distinct institutions the subset rule false-positives:
  `university-of-washington` [Seattle] ≠ `washington-university` [St. Louis];
  `general-electric` ≠ `pacific-general-electric-company` [1948 Bakersfield
  utility]; `aircraft-nuclear-propulsion` [ANP] ≠
  `nuclear-energy-for-propulsion-of-aircraft` [NEPA].
- org part-whole pairs that are *not* duplicates: `boeing` /
  `boeing-phantom-works`; the NASA centers; `us-air-force` /
  `us-air-force-academy`; `lockheed-martin` / `lockheed-martin-skunk-works` /
  `…-space-systems-company`; `university-of-alabama` / `…-huntsville`;
  `lucis-trust` / `lucis-trust-arcane-school`; `ousd-is` / `ousd-is-exdir` /
  `ousd-is-sasp`.

One item remains before this closes: decide whether to add an adjudicated-distinct
ledger so the sweep stops re-surfacing the ruled clusters above to the
internal-investigator and auditor on every run (the alternative is to accept the
recurring noise).

**Blocks:** none.
**Blocked by:** none.
**Related:** the [[link-all-load-bearing-references]] working-memory note;
`scripts/tools/stub-reconcile.py` is the tool — it independently reconstructs the
complete reference set from the research artifacts + built nodes (it does NOT read
the `link_resolution` broken-link registry, which is computed separately at
validation time).

### C4 — Harden the Worker extraction step against large-source timeouts and over-exploration

The Worker role (one invocation per source, the verbatim-extraction boundary)
showed two robustness gaps on a large OCR-scan source (a 37-page DIRD yielding 38
quotes + 20 `cited_works`):

- **The monolithic fragment Write is stall-prone.** The Worker emits its entire
  fragment (all quotes + `cited_works`) in a single `Write` tool-call. On a large
  source that payload runs tens of KB, and generating it in one shot after a heavy
  read context can stall the model long enough to trip the stream-idle-timeout —
  losing the whole extraction, because no incremental progress is saved. The same
  source extracted cleanly on one Worker run and stalled mid-final-Write on a
  second (idle-aborted after the work was effectively done). Investigate an
  incremental / checkpointed fragment write (append per page or per section, so a
  stall costs one chunk, not the run), a larger agent timeout for large sources, or
  an explicit size threshold above which the source is chunked — weigh against the
  byte-exact `merge-fragments.py` transport contract, which assumes one fragment
  file per source.
- **The Worker over-explores beyond its assigned source.** Despite the
  build-protocol "No built node is an example" rule, a Worker read a sibling
  node's full research artifact (the Part I DIRD) unprompted, plus ran several
  greps/globs — inflating its context (worsening the stall above) and crossing the
  no-example boundary. The Worker's job is to extract from its ONE assigned source
  + scratch; the reuse/precedent survey is the internal-investigator's, threaded
  forward via `linked_nodes`. Decide whether to tighten the Worker contract and/or
  add a guard so it reads only its assigned source + scratch. (Per-command Bash /
  Read scoping is advisory — see `build-protocol` "Mechanical enforcement vs. role
  discipline" — so a hard guard may not be mechanizable; a contract tightening may
  be the realistic lever.)

**Related:** the two-scratch footgun — `extract-source.py --source`
(internal-investigator survey aid) and `--artifact` (Worker scratch) leave a
corrupt extract and the clean sibling-backed extract side-by-side in `/tmp`; the
orchestrator must relay the `--artifact` (`-0.txt`, sibling-backed) path, never the
corrupt survey aid.

**Blocks:** none.
**Blocked by:** none.

### C5 — Close the Wayback-submission gap on the all-internal build branch

The `/build` all-internal branch (every load-bearing source already archived
in-repo, `gaps: []`) skips the External Investigator and **Archive** roles. The
Archive role is the only step that submits a source to the Wayback Machine
(`archive.py --submit`), so a node built entirely from reused in-repo sources is
**never Wayback-submitted** — its manifest entry stays `archive_status: 1` (local
copy only). The build pipeline alone never closes this; the only closer today is a
manual `/archive-sweep` at session end, which is easy to forget — so the gap
accumulates silently across every all-internal build (the DIRD set, built from the
in-repo Black Vault mirror, sits this way).

The local `/sources/` copy is the integrity guarantee, so this is not data loss —
but Wayback submission is the insurance the archival discipline promises, and the
all-internal branch silently skips it.

Decide where the pipeline closes it — a `/build` finalize step that submits any
`archive_status: 1` source the build touched, an archive-readiness gate that flags
unsubmitted sources before finalize, or making the end-of-session `/archive-sweep`
mechanical rather than discipline — then run one sweep to submit the backlog of
all-internal-built sources already sitting at `archive_status: 1`.

**Blocks:** none.
**Blocked by:** none.

### C6 — Ingest the parked OUSD(I&S) contractor job-posting evidence into `sources/` and the org nodes

Two scratch drafts hold primary-source material on OUSD(I&S) support
contractors that no node cites yet. Job postings are perishable, and several
of these are already gone from the live web:

- `.scratch/drafts/contractor-postings-20260925/` contains:
  - Sancorp's ADP Workforce Now postings, including the "Staff Officer III" that names AARO;
  - Premier's Indeed postings (Indeed blocks Wayback, so this text is the only capture);
  - 177 Wayback captures of Arlo's removed Greenhouse postings, with `summary.csv`;
  - USAspending and FPDS responses for Sancorp's BPA HQ003425A0001 call orders and for HQ003424C0096's modifications.
  
  `SHA256SUMS` covers every file.
- `.scratch/drafts/arlo-greenhouse-20260924/` holds working copies of the Arlo
  board snapshots, now committed as incident evidence under
  `meta/topic/incidents/2026-09-24-wayback-capture-loss/`. It also holds the frozen
  session log, whose SHA-256 that incident record cites. The log stays out of git
  because it contains account details.

The work:

1. Run the archive role to register the load-bearing postings in `sources/`:
   - Sancorp's Staff Officer III and Field Operations & Sensor Support SME IV;
   - Arlo's AARO postings, requisitions 617 and 619;
   - Arlo's C&PE posting, requisition 469;
   - a representative set of the SASP-batch postings.
2. Run `/augment` on `sancorp-consulting`, `aaro` and `arlo-solutions` to add:
   - call order HQ003426FE050: OUSD(I)-funded, awarded 2026-01-28, four offers, and its description appears verbatim in Sancorp's AARO-naming posting;
   - call order HQ003425FE174;
   - HQ003424C0096's AARO-labelled modifications and its final deobligation;
   - the four BPA numbers (A0001 Sancorp, A0002 Comprehensive Approach, A0003 Premier, A0004 Arlo);
   - Arlo's Dec 2025 – Jan 2026 AARO key-personnel postings;
   - the OUSD(I&S) Commonwealth & Partnership Engagement branch.
3. Keep "FE050 is the AARO follow-on" flagged as an inference until a federal
   record names AARO on it. The FE050 performance work statement, obtainable by
   FOIA from WHS, would settle it.

Before closing, decide where the frozen session log lives durably. Then sweep both
drafts; the committed incident evidence remains the record.

**Blocks:** none.
**Blocked by:** none.

### C7 — Separate the requiring (customer) office from the contracting agency in `org_relationships`

`org_relationship_entry.relationship_type_values` (`meta/schema-research-artifact.yaml`)
has one value for the government side of a contract: `contracting-agency`, defined
as "the other org is this org's contracting agency". The corpus uses it for two
different things. On contractor nodes it tags the **office the work is for** (AARO,
IPMO, USSOUTHCOM, CDAO, …) and, separately, the **office that awarded the
contract** (WHS). Its mirror value `contractor` has the same conflation on the
customer side: AARO's node lists Sancorp as `contractor`, although WHS awarded the
contract. A reader of the Relationships table cannot tell which office contracted
and which office was served — and the distinction matters, because the requiring
office is often the evidentiary question (the award record names only the
contracting and funding offices).

Add a value for the requiring office (e.g. `customer` or `requiring-office`, with
a mirror such as `supplier-to` if needed), define both it and `contracting-agency`
precisely in the schema comment block, and update the `org_relationships` check's
closed enum. Then migrate every affected row corpus-wide — list them with
`grep -n "relationship_type: contracting-agency\|relationship_type: contractor" meta/research/*.yaml`
— deciding each from its cited source: keep `contracting-agency` only where the
source names the awarding office, and move customer offices to the new value.
Flagged rows migrate the same way. Re-render the affected organization nodes.

**Blocks:** none.
**Blocked by:** none.
