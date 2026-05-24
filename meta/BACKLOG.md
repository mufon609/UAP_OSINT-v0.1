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

### A2 — Assess removing bookkeeping/versioning metadata from node frontmatter

The changelog belongs in git. BACKLOG, comments, and node bodies do not hold a
history of changes or book-keeping — git is the centralized history. Several
node-frontmatter fields are bookkeeping or versioning metadata that costs the
investigator token-window space and adds stale-reference risk without pushing
the repo's evidentiary philosophy forward. Assess removing them; the first
deliverable is the assessment (why is each here, is it dead-with-a-simple-
removal or load-bearing, what breaks beyond template + schema), then a go/no-go
plus a coupled implementation plan if approved.

In scope for removal (examples from `people/hal-puthoff.md`):
- `schema_version` (line 4) — **not** obviously dead: it backs a forward-compat
  mechanism (`scripts/checks/schema_version_compat.py`, `meta/schema.yaml`
  `compatible_with`, the AGENT.md "Schema versioning" migration protocol). The
  assessment must weigh whether that mechanism earns its keep (has it ever
  fired?) against its clutter cost — removal means retiring the compat check and
  the AGENT.md protocol, not just deleting a line.
- `created` (line 7) and `updated` — the clearest git-owned case: pure
  bookkeeping dates that `git log` already holds authoritatively.
- **Finding** `status` (`in-progress` / `documented` / `superseded`) and
  `updated` — remove. Findings are append-only evidentiary records; their
  lifecycle status is bookkeeping. This **resolves the finding status-transition
  gap** (there is currently no sanctioned way to advance a finding's status —
  node frontmatter is `Edit`/`Write`-denied, status isn't artifact-driven, and
  no tool exists; removing the field dissolves the problem).

Explicitly **out of scope (keep):** **investigation** `status`
(`open` / `paused` / `closed`) is a meaningful lifecycle, not bookkeeping, and
`scripts/checks/investigation_closure_path_when_paused` gates on it.

Consumer map to verify against (starting point — every one must be checked
before a field is removed):
- `meta/schema.yaml` — `frontmatter.required` lists name `schema_version`,
  `status`, `created` for every node type; the per-type lists drive
  `scripts/checks/frontmatter_required`.
- `scripts/checks/` — `schema_version_compat`, `status_archetype_kind`,
  `artifact_top_level`, `governance_files`, `frontmatter_required`.
- `scripts/build/build-state.py` — renders finding `status` into the CLAUDE.md
  build-state table; reads `created`/`updated`.
- `scripts/build/build-from-research.py` + `renderers/` — compose the node as
  `existing-frontmatter + body`, so frontmatter is preserved, not regenerated;
  removing fields means the renderer (or a one-time migration) must rewrite
  frontmatter. Node files are `Edit`/`Write`-denied, so migration across the
  ~68 existing nodes runs via a script using Python file I/O, not the Edit tool.
- `scripts/build/new.py` + `meta/templates/` — emit the fields at scaffold.
- `AGENT.md`, `meta/conventions.md` — document `schema_version` + status
  lifecycle; update in lockstep.

**Blocks:** none.
**Blocked by:** none (assessment is read-only; the implementation, if approved,
is coupled across schema + checks + renderers + all nodes + build-state + docs
and would move to a roadmap phase).

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

### C2 — Extend quote_location_page beyond `quotes[]` (timeline / naming_quirks)

The `quote_location_page` check covers `quotes[]` only. `p. N` refs in
`timeline[]` and `naming_quirks[]` are ungated and were not migrated — two
stale timeline labels (`aaro-denial-action-mismatch` t2, `pax-river` t2) were
found and fixed by hand during the findings audit.

`naming_quirks[]` carry a verbatim `observed` token and could be gated the same
way (token on page N). `timeline[]` entries carry a paraphrased `event`, not
verbatim text, so they have no anchor to verify against — for those the `p. N`
rests on contributor care regardless; the realistic scope here is
`naming_quirks[]` plus a sweep of the existing `timeline[]` page refs against
the now-paginated extracts.

(The OCR-sibling axis of this gap is closed: siblings carry
`----- PAGE BREAK -----` per document page, `extract_source_text` normalizes it
to a form feed, and the gate now verifies OCR `p. N` refs the same as
text-native — see `meta/conventions.md` "Quote location refs".)

**Blocks:** none.
**Blocked by:** none.
