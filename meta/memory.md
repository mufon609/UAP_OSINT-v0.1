---
id: meta/memory
type: meta
---

# Contributor memory

Durable behavioral patterns and working knowledge that span sessions
but don't fit a more specific surface (`schema.yaml`,
templates, prompts). Keep short. Promote entries to a more specific
home when one emerges.

---

## What goes here

- Cross-cutting working patterns that affect how a contributor
  approaches the repo, not what the repo contains.
- Behavioral discipline around session conduct, audit shape, recovery
  from failure modes that don't map cleanly to a single owner doc
  (schema / build-protocol / a check).
- Pointers to patterns that already live in repo files, when the
  pointer itself is the load-bearing thing a contributor needs to
  carry between sessions.

## What does NOT go here

- Evidentiary discipline or structural rules → their owner: the
  enforcing `scripts/checks/` module, `meta/schema.yaml` /
  `meta/schema-research-artifact.yaml`, a `.claude/skills/` + `agents/`
  contract, or `README.md` for the cross-cutting epistemic
  principles.
- Schema-level field semantics → `meta/schema.yaml` and
  `meta/schema-research-artifact.yaml` comments.
- Session workflows → `.claude/skills/` (invokable as `/build`, `/audit`,
  `/augment`, …); the Claude-Web briefs → `prompts/`.
- Per-script behavior → that script's docstring.
- Past-work narrative, dated incidents, BACKLOG IDs, commit hashes
  → git log only.

## How to add an entry

One H3 per pattern. Lead with the rule. Add a short `Why` paragraph
only when the rationale is non-obvious from the rule. Skip dates,
commit hashes, and incident references — those belong in git log.
When a more specific home for an entry emerges (a
schema comment, a skill/agent contract, a prompt), promote the entry
there and delete the H3 from this file.

---

## Entries

### Multi-issue audits split into phases

When an audit surfaces 3+ issues on a single node, work them in
phases. Address each phase in order; pause for confirmation between
phases.

- **Phase 1 — factual correctness.** Wrong attributions,
  misspellings, source-misquotations, mis-linked paths, mixed-speaker
  quotes. Self-contained errors; can ship independently.
- **Phase 2 — completeness.** Missing timeline events, narrative
  gaps, under-attribution. The
  node works but is thinner than the source supports.
- **Phase 3 — convention.** Schema changes, renderer changes,
  taxonomy redefinitions. Can't be fixed at the node level; needs
  consensus and typically becomes a BACKLOG entry rather than an
  in-session change.

Within a phase, log out-of-phase observations rather than mixing
fixes across phases — bundling a Phase 2 completeness item into a
Phase 1 commit produces long diffs that mix self-evident factual
fixes with contested taste calls.

Pre-existing defects discovered during an audit get fixed in the
same pass and reported transparently in the summary — not silently
left because they pre-date the session. The "surface as observation,
don't fix" reflex is reserved for convention-level questions and
larger architectural items, not for mechanical issues already in
scope.

After each phase, do a verification pass — regenerate the node,
re-run validators, re-read the relevant sections. Treat this as
systematic re-review rather than rubber-stamp confirmation; expect
1-2 items to surface on legitimate re-read.

**Why:** Multi-issue audits that try to address every surfaced item
in one pass produce long diffs mixing clear factual corrections with
contested convention changes. Phasing makes each piece independently
reviewable and lets the contributor halt after Phase 1 if Phase 2 or
3 need more discussion.

### Lean over bespoke tooling

Before proposing a new script or system, check whether existing
infrastructure — git, the Wayback Machine, the manifest, an existing
validator or out-of-band registry pattern — already covers the need,
and prefer the smaller change. If a proposal is heavier than the
problem, say so and offer the lean alternative.

### NO BANDAIDS, in practice

Any issue found during an audit either gets fixed immediately (preferred
for mechanical issues, missing checks, hygiene gaps) or filed in
`meta/BACKLOG.md` for later (design questions, convention-level changes,
items needing consensus). A comment parking the issue (`// known issue: X
never fires under condition Y`) is not a third option. The day-to-day
reflexes:

- **Fix the cause, not a backstop.** Fix a failure at its source
  rather than adding a compensating downstream verify/inspect step.
  And don't add — or keep — a check whose only job is to re-confirm
  an issue already fixed at the source; an audit may call it
  "coverage," but it is dead weight.
- **Defer real work to BACKLOG, never verbally.** When a fix is too
  big for the session, add it to `meta/BACKLOG.md` immediately and say
  you filed it — a chat-only "I'm skipping this" loses the work.
  Describe the work, not an ID (BACKLOG IDs recycle).
- **Question whether a derived artifact should exist before patching
  it.** Heavy fix-up on a generated artifact (an OCR `.txt` sibling,
  an extract, a scaffold) is a smell it is wrong-by-construction.
  Judge from the consumer's seat — a researcher — not the checker's:
  machinery that satisfies a check but adds no consumer value is
  overhead to drop. Prefer remove/regenerate over patch.

### Prefer removing a fact to leaving it half-finished

When a piece of content's value or sourcing is uncertain, leave it
out — the git diff is the recovery record — rather than ship
incorrect or half-finished work; record genuinely load-bearing
removals in BACKLOG. An agent with no more context defaults to
hedging, and an unsourced hedge degrades the repo.

### Check the governing docs before treating an "inconsistency" as open

The governing surfaces usually already settle what looks like an open
design question: `README.md` for the epistemic principles,
`meta/schema.yaml` / `meta/schema-research-artifact.yaml` for
field/structure semantics, `.claude/skills/` + `.claude/agents/` for
build discipline, and `scripts/checks/` for what is mechanically
enforced. Grep them for the governing rule first; if a standard exists,
bring the data into compliance rather than inventing tooling or a
parallel scheme. A check often *silently skips* a non-compliant form, so
a violation can read green and look like "no standard exists."

### Drive node builds through the agent topology

Build or rebuild nodes through the `/build` skill's role pipeline
(internal/external investigator → archive → worker → builder →
auditor), not by hand-authoring the research artifact on the main
thread. Hand-authoring bypasses the source-read-first boundary and
the verbatim / prose-drift discipline the roles exist to enforce.

### A schema or check mechanism applies to every instance of its type

If a field or validator mechanism is right for a node type, declare
it for the whole type and migrate all instances (empty lists render
nothing) — never carve out one "optional exception" to dodge a
corpus-wide sweep. Content scope (which nodes get *populated*) must
not leak into the schema-mechanism decision (which nodes *declare*
the field).

### Verify a BACKLOG item against current state before executing it

A `meta/BACKLOG.md` item may already be mostly done by a prior
session whose bookkeeping lagged. Before executing one, reconcile
each sub-bullet against current artifacts, `git log`, and the
manifest; strike what's done, drop what's redundant or unattested,
and route topic-specific remainders to
`meta/topic/research-queue.md`. Most "fix the BACKLOG" work is
triage, not building.

### Commit directly to main

In this repo, commit (and push) straight to `main` — do not branch
first. Standard discipline still holds: the gates must be green to commit —
the commit hook runs the full pre-commit chain at the boundary
(un-bypassable), so don't pay a separate manual chain run first; run it
manually only to diagnose a red gate. Commit only when asked.

### Commit before auditing, in multi-agent batches

When cleaner subagents edit artifacts and auditor subagents verify,
commit the cleaner edits before dispatching the auditors. An
auditor's advisory-scoped Bash can run `git restore` and silently
revert an uncommitted batch; a committed change is immune. A
regression caught after the commit is a cheap follow-up — far cheaper
than lost work.

### An additions-only diff is not a completeness proof

A clean diff — additions-only, verbatim/prose-drift/coverage gates green —
proves a change *broke nothing*. It says nothing about *completeness*: a
missed entity is an absence, invisible to the diff and to every mechanical
gate. So the independent verifier (the cold second read the build and
`/re-associate` skills mandate as producer→verifier) is not optional, and
"this pass is mechanical / the diff is provably additions-only" is not an
exemption from it — that rationalization is exactly how a completeness miss
ships. The under-linking miss the sweep exists to catch is invisible until
an independent reader re-enumerates from the source; run the verifier even
when the change feels trivial. A follow-up verify pass is cheap; a silently
dropped entity in a committed node is not.

### No speculative estimates — name the work, not its size

Work plans, BACKLOG entries, and status reports state what needs to
get done, not how much of it there is or how long it will take. Do
not invent: per-task percentage gains, accuracy projections, hour
estimates, session counts, line-count estimates, or probability
claims about whether something will succeed. Algorithm- or library-
level facts (a published benchmark number, a documented distance
metric, a measured throughput) are properties of the tool itself and
belong in artifacts. The line: anything specific to THIS project's
outcome where there is no measurement is speculation.

Where uncertainty matters, state directional shape only ("this
should help format X more than format Y, magnitudes unknown") and
prefer naming what would resolve the uncertainty (run a real test)
over inventing the number.

**Why:** Speculative percentages and hours read as precision but
contain no information — the reader cannot tell what was measured
from what was guessed, and the artifact decays as more sessions
accumulate fake-precise predictions that nothing tests.

### Working notes are a report, not a residue

An agent's — or contributor's — analysis, intermediate reasoning, and
findings are a **deliverable**: handed to the user, or returned up the
build pipeline as a handoff. They are never persisted into the
repository's durable surfaces. The repo records *what the sources say*
and *what the code does*, not the working process that produced either.

Three durable surfaces, three places working notes must not land:

- **Node bodies** — renderer output, regenerated from the
  `meta/research/` artifact; source-anchored content, not commentary
  about how it was assembled. The `block_node_body_edit.sh` hook enforces
  this; bodies are not hand-edited at all.
- **Code comments** — what the code does and the non-obvious why, not who
  changed it or what an audit found (see "Comments describe code, not
  refactor history" below).
- **Stray files** — no scratch notes, status logs, or "summary of this
  session" files committed to the tree.

The record lives in **git history** (commit messages, PR descriptions).
For build work this is the mechanism the role pipeline already runs on —
each role returns a handoff stub rather than writing shared state
(build-protocol "Handoff stubs"); see "Drive node builds through the
agent topology" above.

### Comments describe code, not refactor history

Code comments describe what a function or script does and any non-obvious
why — invariants, layering rules, surprising behavior — not refactor
history. Forbidden in comments: BACKLOG identifiers (`per BACKLOG C21`),
commit hashes (`migrated at af5f789`), dated audit notes
(`2026-05-05 audit surfaced …`), phase/cluster markers (F.5b, D.4),
`Origin:` / `Migration:` / `Anchor pattern:` blocks, "previously X, now
Z" reframings, and "mirror X exactly" sync reminders for code since
centralized. The commit message carries *why we changed it*; the comment
carries *why it is the way it is*, and only when non-obvious. This
describe-current-state rule extends to every governance file — retiring a
check, removing a schema field, deleting a template: the file
describes current state and pending work, not past evolution. Git log
carries the evolution.

**What TO keep:** functional descriptions, plus non-obvious why notes
anchored on still-live concepts — a durable governance anchor (a
`meta/schema.yaml` /
`meta/schema-research-artifact.yaml` field path, a `.claude/skills/` or
`.claude/agents/` contract name), a `meta/roadmap.md` mention when scoping
a "not yet implemented" check, or a layering invariant (e.g.
"presence-guard, not truthy — opens a gap with `frontmatter_required` if
loosened"). Anchor on durable concepts, never transient ones (specific
commits, dated audits, phase markers).
