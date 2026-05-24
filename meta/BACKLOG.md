---
id: meta/BACKLOG
type: meta
schema_version: 1
created: 2026-04-17
---

# BACKLOG

Deferred work items — real, concrete, and would be lost otherwise. Not
on the active roadmap. Items leave when (a) promoted to a roadmap phase,
(b) addressed, or (c) superseded.

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
See `meta/conventions.md` "BACKLOG lifecycle discipline".

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

### C1 — Cross-node structural-consistency audit

Comparable nodes diverge in load-bearing, **source-anchored** optional sections,
with no standing check that surfaces the divergence. Observed:

- An organization with publicly contested claims (`/organizations/aaro`) lacks the
  **Primary-Source Contradictions** / **Public-Record Claims Without Primary Source**
  sections a peer org (`/organizations/ipmo`) carries — the same source-anchored
  treatment of contested public-record material applied to one node and not the other.
- **Associated Nodes** is an unlabeled list while **Relationships** (person nodes)
  labels the tie — the navigational surface drops the relation type.

Convergence candidates **only** where the section is source-anchored (verbatim /
contradiction material), never synthesis prose. **Out of scope:** the deliberate
lighter-surface design — document / transcript / event / media / location nodes
intentionally omit synthesis-heavy sections (Credibility Notes, free-prose Timeline)
to minimize prose-drift surface; that asymmetry is correct and must not be "fixed."

Mechanism to evaluate: a dedicated cross-node consistency pass — a new skill/agent run
as a final audit over a built set, possibly section-specialized agents (one per
recurring section family). Decide skill-vs-agent and whether it folds into `/audit`'s
adjacent-node propagation before building.

**Blocks:** none.
**Blocked by:** none.

### C2 — Extend quote_location_page to OCR-scan / extraction-lossy sources

The `quote_location_page` check verifies a quote's `p. N` against the physical
page by splitting the `pdftotext` extract on form feeds. It **skips**
`ocr-scan` / `extraction-lossy` sources because those are served from a
contributor-produced `.txt` sibling whose pagination is not form-feed-faithful
to the original PDF (a sibling may carry one stray form feed or none) — so
their `p. N` labels currently go unverified. Known skipped sources with page
refs include the SASC AARO hearing transcript and FOIA-released PDFs.

Forever-fix: give siblings a page-marker convention (preserve `\f` at the
original PDF's physical-page boundaries, or `--- page N ---` markers aligned to
them) produced by `/prepare-ocr-sibling`, then teach the check to split a
sibling on those markers. Re-run the gate over the previously-skipped sources
and migrate any mislabeled `p. N` refs. Until then those labels rest on
contributor care, not a gate.

Same scope gap on a second axis: the check covers `quotes[]` only. `p. N` refs
in `timeline[]` and `naming_quirks[]` are ungated and were not migrated — two
stale timeline labels (`aaro-denial-action-mismatch` t2, `pax-river` t2) were
found and fixed by hand during the findings audit. `naming_quirks[]` carry a
verbatim `observed` token and could be gated the same way (token on page N);
`timeline[]` entries carry a paraphrased `event`, not verbatim text, so they
have no anchor to verify against — for those the `p. N` rests on contributor
care regardless.

**Blocks:** none.
**Blocked by:** none.
