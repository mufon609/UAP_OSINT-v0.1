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

### C1 — Backfill the four sibling-less weaponized attribution siblings, then promote transcript_sibling_presence to error

Four transcript nodes carry hand-attributed `speaker_id` quotes on
auto-caption sources with no verified attribution sibling — built before
the sibling gate existed, so the one mechanical attribution check
(`speaker_attribution_consistency`) silently skips them. Per-slug state
(drafts preserved at `~/Desktop/claude/UAP_OSINT-c1-handoff/` — /tmp is
periodically cleaned and has already eaten one scratch file; copy a draft
back to its `/tmp/attribution-{slug}/` path before resuming its pipeline):

- `weaponized-097-lacatski-part2-2025` — FURTHEST. Draft r3 (216 turns)
  passed the structural validator and an independent verification
  (verifier session `attribution-verifier-2026-06-11-weaponized-097-r3`;
  two content corrections from the r1 rejection applied and re-checked).
  Video on disk at `sources/video/weaponized-097-lacatski-part2-2025.mp4`.
  Remaining: the mandatory active-speaker fold gate
  (`finalize-attribution.py --verifier-session
  attribution-verifier-2026-06-11-weaponized-097-r3 --video …`) was started
  and stopped mid-run (clean: it writes nothing until it passes) — re-run
  it, settle any `contested-fold`, then register + render (skill §6) and
  `stamp-speaker-id.py` dry-run-confirm the node's hand-keyed values.
- `weaponized-114-lacatski-future-visions-2026` — draft written (213
  turns, full coverage) but FATALs the structural validator: YAML parse
  error at draft line 114 col 5 (unquoted scalar class). Route to a
  producer for the repair, then validator → verifier → gate → register.
- `weaponized-038-lacatski-kelleher-2023` (2373 lines) and
  `weaponized-096-lacatski-part1-2025` (1476 lines) — no draft yet. Two
  producer attempts failed on harness limits: one request timeout
  (~69 min), two hit the 64k single-response output cap mid-draft (the
  successful 097/114 producers emitted their YAML across multiple
  writes). If the cap recurs, that is producer-contract friction —
  consider directing incremental section-by-section Write/Edit emission
  in the contract rather than one full-file emission.
- Videos for 038/096/114 are not yet on disk — fetch with
  `download-video.py {manifest url} --slug {slug} --skip-manifest`
  before each finalize (the gate refuses to run without the recording;
  `.venv-face` is installed and working).

For each: finish the `/prepare-transcript-sibling` pipeline as above, then
confirm each node's existing `speaker_id` values against the verified
sibling (`stamp-speaker-id.py` dry run) and correct any divergence —
hand-keyed attribution is exactly the divergence hazard the sibling
exists to remove.

When all four are verified, promote `scripts/checks/
transcript_sibling_presence.py` from `warn` to `error` (its documented
end state) and update its docstring's severity paragraph.

**Blocks:** C3 (its recorded resume state pins the `/tmp` draft paths).
**Blocked by:** none.

### C3 — Move expensive agent-draft scratch out of /tmp to a durable workspace

The sibling pipelines direct their agent producers to emit drafts under
`/tmp` (`/tmp/attribution-{slug}/…` for transcript attribution,
`/tmp/{stem}/` page files for OCR). `/tmp` is periodically cleaned, and a
multi-hour semantic parse is the most expensive artifact these pipelines
produce — losing a draft to cleanup forces a full producer re-run, and the
interim mitigation (hand-copying drafts to an out-of-repo handoff
directory) is contributor discipline, not pipeline design. Establish a
durable git-ignored scratch root inside the repo (e.g. `.scratch/`), route
the draft/page-file output paths there in the
`prepare-transcript-sibling` + `prepare-ocr-sibling` SKILL.md files and
the `attribution-producer` / `ocr-page-producer` contracts, and sweep
every other doc reference to the old paths (grep `/tmp/attribution-`,
`/tmp/{stem}`). Cheap regenerable scratch (`extract-source.py` plaintext,
worker fragments) may stay in `/tmp` — the boundary is regeneration cost,
not uniformity. The gate scripts already take paths as arguments, so this
is a docs/contract retarget, not a code change. Retire the ad-hoc handoff
directory once the retarget lands.

**Blocks:** none.
**Blocked by:** the in-flight transcript-sibling backfill above (don't
retarget paths under a mid-flight run that resumes from them).

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
