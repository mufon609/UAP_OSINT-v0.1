---
name: fork-init
description: Bootstrap a fresh fork of this toolkit for a different topic — wipe the content layer, regenerate the topic-identity files, and confirm the empty corpus is healthy. Destructive; user-invoked only.
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(rm *)
  - Bash(python3 scripts/build/validate.py *)
  - Bash(python3 scripts/build/build-state.py *)
  - Bash(bash scripts/tests/pre-commit.sh)
---

# Fork-init

Bootstrap a fresh fork for a new topic. The toolkit is topic-neutral by design
(schema, scripts, conventions, templates, validators, test suite, **and the
`.claude/` skills + subagents + settings**). What's NOT neutral is the content
layer (`meta/research/`, the content-node directories, `sources/`) and the
topic-identity file (`meta/topic/overview.md`), whose `display_name` flows into
every UI surface that names the subject.

First read `CLAUDE.md`, `README.md` (the "Forking" paragraph), `meta/conventions.md`,
`meta/schema.yaml`, and the existing `meta/topic/overview.md`. Confirm what
stays (toolkit) vs. goes (content + topic-identity) before the wipe.

## Step 1 — Confirm topic with the user

Ask for: the **topic short identifier** (lowercase token for the `topic`
frontmatter field), the **display name** (capitalized form for rendered
headers / user-facing strings), and a **one-sentence topic statement**. Do not
wipe until these are confirmed.

## Step 2 — Wipe content (preserves directory structure; never touches `.claude/`)

```
rm -rf meta/research/* meta/topic/working-notes/*
rm -f  meta/topic/overview.md meta/topic/research-queue.md
rm -rf people/* organizations/* documents/* events/* transcripts/* media/* locations/* findings/* investigations/*
rm -rf sources/*/
> sources/manifest.yaml
```

Verify the directories themselves still exist (`ls people/` succeeds, returns
nothing) — the validators walk them and assume they exist. Confirm `.claude/`
is untouched (the skills, subagents, and `settings.json` are toolkit).

## Step 3 — Regenerate `meta/topic/overview.md`

Required frontmatter: `id`, `type: meta`,
`topic: <identifier>`, `display_name: <Display Name>`. Both `topic` and
`display_name` are validated as required by
`scripts/checks/governance_files.py`; both feed `lib._common.load_topic()`,
read at render time by the `## {display_name} Relevance` /
`## {display_name}-Scope Activity` headers and the archiver User-Agent. Write
the topic statement + scope boundaries in the body; use the prior version as a
structural reference (`git show HEAD:meta/topic/overview.md`) and replace its
content entirely.

## Step 4 — Regenerate `meta/topic/research-queue.md`

Same frontmatter shape (no `topic` / `display_name` — those live only on
`overview.md`). Re-establish the two-backlog structure (Queue + Priority Build
Queue). An empty body is fine on day 1.

## Step 5 — Health check

`python3 scripts/build/validate.py`, `python3 scripts/build/build-state.py --check`,
`bash scripts/tests/pre-commit.sh` — all should exit clean on an empty corpus.
If any validator errors, the bootstrap is broken; fix before adding content.

## Step 6 — First commit

Commit the wipe + new `overview.md` + new `research-queue.md` as commit-zero.
Subsequent sessions use `/build` (the multi-agent pipeline; `prompts/build.md`
is the single-session fallback).

## What NOT to change

Topic-neutral toolkit — do not modify during fork-init:

- `meta/schema.yaml`, `meta/conventions.md`, `meta/templates/` — spec, discipline, templates.
- `scripts/` — validators, renderer, scaffolders, source tooling, hook guards.
- `prompts/` — the kept design docs (`topology.md`, `build.md`, `web-claude-*`).
- **`.claude/skills/`, `.claude/agents/`, `.claude/settings.json`** — the
  skills, role subagents, and hook wiring. These encode *how to build any
  node*, not *what this instance investigates*; keep them placeholder-only.

If you find yourself wanting to edit any of the above, stop: is this a
topic-neutral toolkit improvement (separate commit / BACKLOG / roadmap), or are
you trying to escape the topic-customization mechanism? The mechanism is
`display_name` on `overview.md`; everything else flows from that.
