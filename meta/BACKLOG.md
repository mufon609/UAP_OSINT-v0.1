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

### C1 — Distribute conventions.md to its consumers (in progress)

**Why.** `meta/conventions.md` became the repo's ad-hoc hub — ~200 references
across ~55 files pointed *into* it as the authority. A rule everything cites from
a central rationale file is not co-located with the tool that applies it. Goal:
each rule lives with the consumer that uses it (skill / agent / check / schema /
README / memory); nothing needs to point at conventions.md, which shrinks toward
zero.

**Cautions — verify, don't trust (this is the point of the item).**
- Prove a section's true owner with line-level evidence *before* touching it. A
  section is delete-already-owned ONLY when the owner already states it; a
  genuinely-unique claim is moved to its owner; redundant rationale is dropped.
- Prefer defining a rule into the PRODUCING role (worker / producer / skill), not
  an after-the-fact check — front-load, don't backstop.
- De-reference every inbound pointer to a removed section atomically (no dangling
  "see conventions.md X"). Nothing mechanical reads conventions.md (every ref is
  prose; `governance_files` needs only frontmatter), so moves can't break the
  pipeline at runtime — but the pointers must still be fixed.
- **Sweep INTERNAL conventions.md cross-refs too** — `above` / `below` / `see "X"`
  — after every delete, not just external files. Phase C found six latent
  dangling refs earlier external-only sweeps had missed (inside conventions.md
  itself + `coverage-suggest.py`); a deleted section's in-file "see X below" is as
  dangling as an external pointer.
- Show before→after per move, gate (`scripts/tests/pre-commit.sh` green), commit
  per owner-cluster.

**Start here, next session — investigate before continuing.** Read the commit
series first (`git log --oneline --grep='docs(conventions)'`) to see what was
moved where, then INVESTIGATE IT FOR FLAWS: re-verify each move landed in the
right home, that nothing load-bearing was lost or mis-housed, and that no pointer
dangles (`grep -rn 'conventions' --include='*.py' --include='*.md' --include='*.yaml'`).
Do not resume on trust — find the mistakes first, then continue; everything is
investigated before it is altered.

**Done (Phases A–C).** Phase A (checks): prose-drift, cited_works, location-refs,
check-naming + validator-design, source-form + off-node. Phase B (schema):
manifest-shape, type-views, news-articles, key-passages-ordering, date-precision
(BACKLOG C2 redirected). Phase C (skills/agents): OCR-fidelity,
transcript-provenance + label-less, hearing-as-venue + key-testimony,
primary-sources-archival, cross-references + interview-contract, paired-siblings,
comparability + passage-rubric, confirmation-precondition. conventions.md
1841 → 794 lines; all commits pushed (`git log --grep='docs(conventions)'`).

**Next.** Phase D (repo-layout / scripts-six-tiers / meta-root-vs-subdirs / scope /
versioning → README / meta-README / CLAUDE); Phase E (NO-BANDAIDS /
comments-describe-code / what-to-keep / working-notes / density → meta/memory.md);
Phase F (~67 manifest `note:` re-citations + templates → cite the new owner or
drop). Then Phase G — a **DECISION for the maintainer**, not a mechanical move:
the residue is the cross-cutting epistemic axioms with no single code owner
(core-principle, relevance-relational, structure-reflects-evidence,
confirmed/flagged, sworn-testimony, source-priority, contradictions, neutrality),
plus statements-as-primitive and the Part IV three-layer / tier block. Decide:
keep a slim unreferenced essay, fold into README, or fold into meta/memory.md.

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
