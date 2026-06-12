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

### A2 — Make the active-speaker fold gate trustworthy on grid-layout remote-guest video

The fold gate (`finalize-attribution.py` → `spot-check-attribution.py` +
`active-speaker.py`) returned 14 contested-fold verdicts on a
verifier-PASSED draft whose labels frame-level reads confirm are mostly
correct — engine false-positives, with at most one likely genuine label
error among them. Reproduced on the `weaponized-114` video (persistent
three-tile grid, remote guest in a low-quality middle tile); evidence
preserved at `.scratch/handoff/` (`finalize-114.log`,
`spot-check-114.csv`; probe crops registered in
`sources/photo-identity-log/`). A dedicated session should investigate
ONLY this, before any further attribution finalize.

The settlement path is in place: the gate honors `image_verification[]`
adjudications (`--resolve-turn` writes them; a contested-fold turn whose
entry still matches its `speaker_id` is reported as settled, not
blocking; stale entries re-block), so the one likely genuine label error
can settle durably once frame-read. Do NOT bulk-adjudicate the ~13
engine false-positives through that path — entries record frame-settled
judgments, not engine noise; the engine itself is what this entry fixes.
Failure mechanics:

- **Detection/identification recall on small tiles.** The assigned
  speaker (Lacatski, middle tile) matched in 0–3 of 7 frames per turn
  while clearly present — `detect-faces.py` standalone identified him
  correctly on probe frames at the same timestamps. Compare the two
  paths' detection parameters (HOG upsampling, extracted frame size);
  consider upsampling or the CNN model for sub-100px faces.
- **MAR "active speaker" false positives over long windows.** The
  active-speaker signal is the MAR range (max−min) across burst frames
  sampled seconds apart; over a 30–60 s window a listener's smile or
  laugh crosses the 0.06 `mar_talk_range` default, so a visibly static
  listener reads as the talker (Corbell: MAR range 0.10–0.31 while
  motionless in the bursts). Lip motion is only meaningful across
  adjacent frames (~100 ms); range-across-a-sparse-burst is structurally
  noisy — rethink the sampling (adjacent-frame pairs per sample point)
  or the metric.
- Validate any fix against BOTH the 114 grid layout and the clean 097
  run (same trio, 0 contested across 226 turns) so the gate keeps its
  discriminative power, and design for the 038 case (one speaker
  genuinely audio-only, `on_camera_role: off-camera`). Then re-run the
  114 finalize as the acceptance test.

**Blocks:** A3 (every remaining attribution finalize runs this gate).
**Blocked by:** none.

### A3 — Finish the transcript-sibling backfill, then promote transcript_sibling_presence to error

One of the four sibling-less transcript nodes is done
(`weaponized-097-lacatski-part2-2025`: verified sibling registered +
rendered, node speaker ids stamped). The remaining three have completed
or near-completed text-side pipelines; every finalize is gated on A2.
Drafts live at their durable pipeline paths
(`.scratch/attribution-{slug}/{stem}-attribution.yaml`); fold-gate
evidence and the 096 correction list are under `.scratch/handoff/`. All
source videos are on disk under `sources/video/` (038 at its
manifest-registered suffixed filename).

- `weaponized-114-lacatski-future-visions-2026` — draft verifier-PASSED
  (independent session `claude-fable-5-verifier-2026-06-11-weaponized-114`;
  structural validator clean). Remaining: the fold gate (BLOCKED by A2 —
  its run returned the 14 contested-fold verdicts A2 investigates), then
  register + render + `stamp-speaker-id.py` confirm (the 097 shape).
  When re-gating, adjudicate `2336-2343` specifically — the one
  contested turn whose frame read (Lacatski mid-speech on a
  Knapp-assigned turn) suggests a genuine label error.
- `weaponized-096-lacatski-part1-2025` — structurally-valid draft;
  independent verifier REJECTED with two cold-open boundary corrections
  (full list: `.scratch/handoff/096-verifier-corrections.md`). Route
  to a producer, re-validate, fresh verification; then gate → register
  → stamp.
- `weaponized-038-lacatski-kelleher-2023` — structurally-valid draft
  (200 turns, produced via the contract's incremental emission; Knapp is
  audio-only this episode, `on_camera_role: off-camera`). Needs its
  independent verification; then gate → register → stamp.

For each: after registration, confirm the node's existing `speaker_id`
values against the verified sibling (`stamp-speaker-id.py`) and correct
any divergence — hand-keyed attribution is exactly the divergence hazard
the sibling exists to remove.

When all four are verified, promote `scripts/checks/
transcript_sibling_presence.py` from `warn` to `error` (its documented
end state) and update its docstring's severity paragraph.

**Blocks:** none.
**Blocked by:** A2 (every remaining finalize runs the fold gate).

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
