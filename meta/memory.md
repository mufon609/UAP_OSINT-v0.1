---
id: meta/memory
type: meta
---

# Contributor memory

Durable behavioral patterns and working knowledge that span sessions
but don't fit a more specific surface (`conventions.md`, `schema.yaml`,
templates, prompts). Keep short. Promote entries to a more specific
home when one emerges.

---

## What goes here

- Cross-cutting working patterns that affect how a contributor
  approaches the repo, not what the repo contains.
- Behavioral discipline around session conduct, audit shape, recovery
  from failure modes that don't map cleanly to a single rule in
  `conventions.md`.
- Pointers to patterns that already live in repo files, when the
  pointer itself is the load-bearing thing a contributor needs to
  carry between sessions.

## What does NOT go here

- Evidentiary discipline or structural rules → `meta/conventions.md`.
- Schema-level field semantics → `meta/schema.yaml` and
  `meta/schema-research-artifact.yaml` comments.
- Session workflows → `.claude/skills/` (invokable as `/build`, `/onboard`,
  `/audit`, …); build design rationale + fallback → `prompts/`.
- Per-script behavior → that script's docstring.
- Past-work narrative, dated incidents, BACKLOG IDs, commit hashes
  → git log only.

## How to add an entry

One H3 per pattern. Lead with the rule. Add a short `Why` paragraph
only when the rationale is non-obvious from the rule. Skip dates,
commit hashes, and incident references — those belong in git log.
When a more specific home for an entry emerges (a conventions
section, a schema comment, a prompt), promote the entry there and
delete the H3 from this file.

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

The `NO BANDAIDS` rule (`conventions.md`) as day-to-day contributor
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

### Check conventions.md before treating an "inconsistency" as open

`meta/conventions.md` usually already settles what looks like an open
design question. Grep it for the governing rule first; if a standard
exists, bring the data into compliance rather than inventing tooling
or a parallel scheme. A check often *silently skips* a non-compliant
form, so a violation can read green and look like "no standard
exists."

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
first. Standard discipline still holds: `pre-commit` green before
committing, and commit only when asked.

### Commit before auditing, in multi-agent batches

When cleaner subagents edit artifacts and auditor subagents verify,
commit the cleaner edits before dispatching the auditors. An
auditor's advisory-scoped Bash can run `git restore` and silently
revert an uncommitted batch; a committed change is immune. A
regression caught after the commit is a cheap follow-up — far cheaper
than lost work.
