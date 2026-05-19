---
id: meta/memory
type: meta
schema_version: 1
created: 2026-05-19
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
- Paste-ready session prompts → `prompts/`.
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
- **Phase 2 — completeness.** Missing timeline events, gaps in
  `entities_referenced[]`, narrative gaps, under-attribution. The
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
