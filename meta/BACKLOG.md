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

The seven-role pipeline (`prompts/topology.md`) has now been run *whole* on
one real node build — a user-directed, all-internal institutional-actor
build: Orchestrator → Internal Investigator → Worker (×N) → Build → Audit,
with handoff stubs captured and friction tightened in place. Three paths
were NOT exercised by that run and remain unverified end-to-end:

- the **External Investigator (role 2) + Archive (role 3)** roles — skipped
  by the all-internal branch (every source was already archived). Needs a
  build with a genuine external-source gap.
- the **`caption` and `foia` worker kinds** — only `pdf` + `html` were hit.
- **Error-Agent routing** — no validator failure needed routing on the clean
  run.

Drive a build that forces these paths (a target with an external-source
gap + a caption/FOIA source); confirm each `--phase X` fires exactly the
checks reading role X's state; tighten friction in place where cheap, file a
new entry where not.

**Deferred follow-on:** split `prose_drift` into `prose_drift_toplevel`
(organize phase) + `prose_drift_notes` (link phase) only if one-phase-late
surfacing of top-level prose drift proves annoying.

**Blocks:** none.
**Blocked by:** a user-directed build with an external-source gap.

### A2 — Decide whether the per-entry `.note` field stays, is redefined, or is removed

`.note` (on `key_personnel`, `affiliations`, `relationships`,
`program_involvement`, `contracts`, `ownership_timeline`, …) is classified as
**synthesis** — `meta/conventions.md` lists it among "per-entry
synthesis-content notes" and the prose-drift check scans it; facts live
elsewhere (structured columns + verbatim `quotes[]`). But the field has no
*positive* definition of its job — only a vocabulary constraint (sourced
tokens) — so it drifts into the two things it must not be: restating the
row's own columns (duplication), or stating a new fact (which belongs in a
column or a quote with its own source). The james-holly / ipmo build
surfaced both modes.

Open question for the user — does the field earn its place? Three directions:
- **Keep + define positively** — note = per-entry interpretive residue
  (caveat / source-limitation / disambiguation / sequencing) the columns and
  quotes structurally can't carry; empty by default. (A first, negative-framed
  cut of this discipline is already in `conventions.md` / `agent-build.md` /
  `audit.md` — "don't restate columns, don't duplicate the Timeline".)
- **Narrow** — restrict notes to one enumerated purpose (e.g. source-quality
  caveats only); everything else moves to columns / quotes.
- **Remove** — drop the field; force all content into structured columns +
  verbatim quotes.

Resolution couples: audit what existing `.note` fields actually carry across
the corpus → pick a direction → update `conventions.md` (+ schema field
comments, + the renderers if removed) → rebuild affected nodes. No mechanical
redundancy check — redundancy here is semantic; a token-overlap scan both
false-positives on legitimate notes and misses real cases.

**Blocks:** none.
**Blocked by:** a user decision on the field's purpose.

---

## B. Parallel batch (renderer pass)

Renderer-touching items that batch into a single polish pass.

_(none)_

---

## C. Anytime (no dependencies)

No upstream blockers; safe to pick up in any session. Default-focus tier.

### C1 — `manifest.py` has no update/remove path and no structured-metadata flags

`manifest.py` only `add` mutates the YAML; correcting a registered
entry's note (or any field) has no CLI surface, forcing a hand-`Edit`
(which the build rules otherwise discourage). Also: no `--archived-date`
flag — `add` auto-stamps today, conflating archival-date with
registration-date for files that were downloaded in a prior session;
and no `--classification` / `--date` / `--pages` structured flags (all
such metadata goes into the freeform `--note`). Add an `edit`/`set`
subcommand (target an artifact by path; set a field or rewrite the note)
plus an `--archived-date` flag. Surfaced during the AAWSAP DIRD bulk
registration (36 entries; one note needed a post-add hand-fix).

### C2 — `dia-mil-reid-aatip-letter-2009.pdf` is misnamed

Page-1 read shows the file is the James R. Clapper Jr. / OUSD(I)
memorandum to the Deputy Secretary of Defense recommending against a
Special Access Program for AATIP — i.e. the memo *responding to* Reid,
not Reid's own letter (that is `reid-letter-to-depsecdef-sap-request-20090624.pdf`).
Rename the file + update its manifest path/note so a future builder
doesn't mis-cite it as Reid's letter. (A separate 3-page
`OUSDI_IM_on_AATIP_Final.pdf` on The Black Vault is a DIFFERENT, shorter
document — the 18-page packet on disk here is distinct.)

### C3 — Three AAWSAP source URLs recorded as landing-page fallback

`dird-22-…-diamil-…` (dia.mil FileId/161870 → 403), `fas-org-aatip-list-20210808.pdf`
(irp.fas.org/dia/aatip-list.pdf → 202 empty, Cloudflare), and
`dia-mil-reid-aatip-letter-2009.pdf` (dia.mil FileId/170015 → 403) are
registered with the Black Vault AAWSAP landing page as the URL plus
"direct-PDF URL unverified" in the note, because their canonical hosts
bot-block both curl and WebFetch. Revisit via the Wayback fuzzy-timestamp
pull (per `meta/sources-access.md`) or a manual browser save to record
verified direct URLs.
