---
id: meta/BACKLOG
type: meta
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

### A3 — DIRD extraction process: consistency standard (open) + capture citations (decided)

Two facets of one question — *how should an AAWSAP DIRD document node be
extracted?* — surfaced when a relevance audit of `dird-04-biomaterials` (55
quotes) found it a ~3× outlier against its siblings. The size gap is a symptom;
the underlying issue is that there is **no shared extraction standard** for DIRD
document nodes, so each was built to whatever its worker session judged
"load-bearing" under "density source-driven, no count target."

**(a) Extraction-density consistency — OPEN QUESTION (a fresh session decides;
no recommendation is recorded here on purpose).** The seven built DIRDs span a
~10× density range with no principled reason:

| DIRD | pages | quotes | quotes/page |
|---|---|---|---|
| dird-24 quantum-vacuum-energy-extraction | 58 | 9 | 0.16 |
| dird-26 field-effects | 39 | 21 | 0.54 |
| dird-01 metallic-glasses | 31 | 17 | 0.55 |
| dird-03 pulsed-hpm | 38 | 23 | 0.61 |
| dird-15 advanced-space-propulsion | 17 | 13 | 0.76 |
| dird-02 programmable-matter | 21 | 17 | 0.81 |
| dird-04 biomaterials | 33 | 55 | 1.67 |

The longest DIRD (dird-24, 58pp) has the fewest quotes (9) — a candidate for
*under*-extraction; dird-04 (1.67/pg) is the high end. The investigation must
decide: is dird-04 over-extracted, are the others (esp. dird-24) under-extracted,
or both — and what is the consistent rule (a quote-density target, or, better, a
selection rubric naming which categories of DIRD passage must be captured:
provenance / thesis-and-scope / each section's finding / methods / conclusions /
…) so density falls out of consistent selection rather than worker judgment?
Context for the deciding session: not every passage needs explicit UAP content —
a DIRD is an AAWSAP product, so its substance is relevant by program proxy, which
argues against aggressive trimming; under-extraction risks losing material whose
relevance only surfaces later. **Do not trim dird-04 in isolation** — resolve the
standard, then re-level the whole DIRD set against it.

**(b) Capture DIRD citations — DECIDED (implement; not an open question).** The
DIRDs carry formal reference lists that the repo captures nowhere: dird-24 alone
has a `References` section with ~206 citation markers, and **no document
research-artifact has any citations/references field** — the schema doesn't model
it. The AAWSAP-commissioned authors' citations are an investigative dimension
(who they relied on; recurring cited authors; cross-DIRD / known-figure networks).
The decision is to capture them as a new dimension. Implementation (for the same
fresh session, since it is part of redefining DIRD extraction): design the schema
representation on the document artifact type (a `cited_works` / `references`
section), render it, and extract across the DIRD corpus (dird-24's reference list
first). Decide granularity (full bibliographic entries vs. author+year+title).

**Blocks:** none.
**Blocked by:** none. Reserve for a session explicitly scoped to the DIRD
extraction process (the density re-level + the citations schema/extraction are
coupled — both redefine how a DIRD is extracted).

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
