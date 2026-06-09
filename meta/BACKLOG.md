---
id: meta/BACKLOG
type: meta
---

# BACKLOG

Deferred work items — real, concrete, and would be lost otherwise. Not
on the active roadmap. Items leave when (a) promoted to a roadmap phase,
(b) addressed, or (c) superseded.

**This file is self-governing.** The rules in this header and in the
**§ Lifecycle** section at the foot are the root, authoritative definition
of how the BACKLOG is written, identified, and closed — nothing outside
this file governs it.

Open items are partitioned into three sections by dependency shape:
**A — Priority sequence** (ordering / coupling constraints),
**B — Parallel batch** (renderer-pass items that ship together),
and **C — Anytime** (no upstream blockers). Item identifiers within
each section (A1, A2, …, B1, …, C1, C2, …) are positional working
labels, not stable identifiers. A closed item's block is deleted in
full — no marker, no placeholder. A new entry takes the lowest section
number not currently in use, so **numbers recycle**; once a section,
and ultimately the whole BACKLOG, is cleared, numbering restarts from 1.
Because an ID is transient and reused, never reference it from outside
this file — not in code, docs, prompts, commit messages, or `git log`
searches. Describe the work; the commit diff + message are the record.
(Full close-and-open discipline: **§ Lifecycle** at the foot.)

**Default focus: Section C.** C items have no upstream dependencies
and can be picked up and finished in a single pass. A and B items
carry ordering or coupling constraints — starting one without its
dependencies risks half-baked implementations and leaves the BACKLOG
cluttered with partial work. For ad-hoc sessions, prefer C work.
Reserve A and B for sessions explicitly scoped to those tracks.

Items waiting on an external event the repo can't drive (FOIA
resolution, registry access, third-party publication) and that are
**topic-specific** to the current investigation live in
`meta/topic/research-queue.md` "Externally blocked" — that's the fork-
boundary-correct home for them. If a genuinely toolkit-neutral
externally-blocked item ever surfaces (rare), reinstate the
"Externally blocked" heading at the bottom of this file.

Cross-references between entries use `**Blocks:**` / `**Blocked by:**`
lines so the dependency graph is visible inline.

---

## A. Priority sequence

Items with ordering or coupling constraints.

### A1 — Exercise the pipeline paths the first whole run didn't hit

The six-role pipeline (`prompts/topology.md`) has been run *whole* on one
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
  applied via builder re-entry, not a routed check failure).

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

### C2 — Investigate whether the Description "no-duplication" convention should relax

The maintainer wants `## Description` to read as a well-defined summary that may
surface select salient items also living in a structured section (a key
relationship, timeline event, contract, finding). The current convention pushes
the other way — `meta/conventions.md` "Date precision: orientation-grade in prose,
field-precise in tables" states *Description should not duplicate field-precise
dates from a structured surface* and *eliminating duplication removes a drift
surface*. That anti-drift rationale is load-bearing, so a relaxation could easily
go bad; it is deferred for investigation, not changed in place.

Avenues to weigh before any edit: (a) survey how built nodes actually use
Description today — is the overlap pressure real or rare?; (b) whether the
carve-out should stay field-precise-only (exact dates / dollar amounts / control
numbers single-sourced in their table; orientation-grade overlap allowed); (c)
whether the `description_token_drift` check needs any change (it checks grounding,
not overlap, so likely none). Produce a recommended wording, then edit the
convention and record the rationale.

**Blocks:** none.
**Blocked by:** none.

### C3 — Correct the Kress-footnote date (OCR misread "June 17" → "June 27, 1972")

A cold-context audit of `organizations/stanford-research-institute` rendered the
Kress source PDF **page image** (the source is `extraction_type: ocr-scan` with
**no verified `.txt` sibling** — the `pdftotext` layer is corrupt) and read the
footnote date unambiguously as **"June 27, 1972"**. The quote was extracted from
the corrupt text layer as "June '1:7," and carried as **"June 17"**, then
propagated. A zero-tolerance verbatim defect, deferred here per the maintainer
for a clean session (needs the OCR-sibling workflow, not a quick edit).

Source: `sources/government/cia-kress-parapsychology-in-intelligence-studies-intelligence-1977-declassified-1996.pdf`
(PDF page 7 / printed page 8, footnote 6).

Steps:
1. Produce + confirm the verified `.txt` sibling via `/prepare-ocr-sibling`
   (this source feeds multiple quotes, so the sibling is owed regardless).
2. Re-extract the footnote quote text — `stanford-research-institute` q36 and
   `kit-green` q1 — from the verified sibling / page image: `…June 27, 1972.`
3. Drop the now-pointless naming_quirks — SRI `nq14` and kit-green `nq1` (they
   "preserve" a garble that lived only in the discarded text layer, never on the
   page → correction-to-nothing).
4. Retarget every derived `1972-06-17` field in `kit-green` (q1 `statement_date`,
   `background`, `top_relevance`, timeline entry, affiliation `period_start`) to
   `1972-06-27`.
5. Rebuild both nodes; re-audit.

Also verify while there: `uaptf` q22 shares the exact location string that q18
carried ("UAPTF Charter, p.4, UAP Task Force Director responsibilities section");
q18 was corrected to p.7 this session after a page-image check, but q22 was left
unverified — confirm q22's page ref against the charter PDF (likely also p.7,
same section) and correct if needed.

**Blocks:** none.
**Blocked by:** none.

---

## Lifecycle

The goal is to REMOVE items, not accumulate annotations referencing them.

**Closing an entry:**

- Delete the entry's block in full. No retirement marker, no placeholder.
  The commit that ships the closure carries the implementation diff and a
  message describing what shipped — that is the canonical record.
- IDs are positional working labels, NOT stable identifiers. A new entry
  takes the lowest section number not currently in use, so numbers
  **recycle**; when a section — and ultimately the whole BACKLOG — is
  cleared, numbering restarts from 1. An ID therefore must never appear
  outside this file: not in code, docs, prompts, commit messages, or
  `git log` searches. Reference the work, never the ticket.
- Sweep code comments that referenced the closed entry's identifier —
  either delete the comment (if its resolution is now reflected in the
  code itself) or rewrite to describe current behavior without the
  BACKLOG anchor. This sweep is part of closing the entry, not follow-up
  work.

**Open entries** describe the work to be done and why it matters —
forward-looking, prescriptive. An entry does NOT carry "Surfaced from",
"introduced by audit X on date Y", commit hashes pinning when the need
was identified, or other past-work narrative. Where the audit / session /
commit that surfaced the work lives is in git log, retrievable via
`git log --grep <ID>` once the entry is named in any commit message. The
entry itself describes only the work.
