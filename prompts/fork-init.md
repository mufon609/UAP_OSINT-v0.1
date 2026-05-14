# Fork-init prompt

Paste into a fresh Claude Code session when forking this toolkit for a
different topic. Run before any contributor sessions on the fork.

The toolkit is topic-neutral by design (schema, scripts, conventions,
templates, validators, test suite). What's NOT neutral is the
content layer (`meta/research/`, the content-node directories, `sources/`)
and the topic-identity-of-record file (`meta/topic/overview.md`),
whose `display_name` frontmatter field flows into every UI surface
that names the subject.

This prompt walks the bootstrap.

---

You are bootstrapping a fresh fork of the toolkit for a new topic.
Before doing anything:

1. Read `CLAUDE.md` — session-start checklist (skim; the build-state
   block will be empty after the wipe).
2. Read `README.md` — the "Forking for a different topic" paragraph
   defines the scope of the wipe.
3. Read `meta/conventions.md` — the evidentiary discipline carries
   over to every fork.
4. Read `meta/schema.yaml` — the machine-readable spec is topic-neutral.
5. Read the existing `meta/topic/overview.md` — you'll be replacing
   its content but keeping the structure.

Confirm you understand what stays (toolkit) and what goes (content +
topic-identity) before the wipe.

---

## Step 1 — Confirm topic with the user

Ask the user:

- **Topic short identifier** (lowercase token, used in
  `meta/topic/overview.md` frontmatter `topic` field; e.g. `uap`,
  `chemtrails`, `targeted-individuals`, `mkultra`).
- **Display name** (capitalized form for rendered headers and
  user-facing strings; e.g. `UAP`, `Chemtrails`, `MKULTRA`).
- **One-sentence topic statement** for the overview body.

Do not proceed to wiping content until topic + display_name are
confirmed.

---

## Step 2 — Wipe content

Wipe content layer (preserves directory structure):

```
rm -rf meta/research/* meta/topic/working-notes/* meta/topic/addenda/*
rm -f  meta/topic/overview.md meta/topic/research-queue.md
rm -rf people/* organizations/* documents/* events/* transcripts/* media/* locations/* findings/* investigations/*
rm -rf sources/*/
> sources/manifest.yaml
```

Verify the directories themselves still exist (`ls people/` should
succeed and return nothing); the toolkit's `validate.py` and
`build-state.py` walk these directories and assume they exist.

---

## Step 3 — Regenerate `meta/topic/overview.md`

Create a new `meta/topic/overview.md`. Required frontmatter:

```yaml
---
id: meta/topic/overview
type: meta
schema_version: 1
created: <YYYY-MM-DD>
topic: <topic-short-identifier>
display_name: <Display Name>
---
```

The `topic` and `display_name` fields are validated as required by
`scripts/checks/governance_files.py`; missing either is a hard
error. Both flow into `lib._common.load_topic()` which is read at
render time by:

- `scripts/build-from-research.py::render_top_relevance` (person
  artifacts) — composes `## {display_name} Relevance` headers
- `scripts/build-from-research.py::render_top_scope_activity`
  (location artifacts) — composes `## {display_name}-Scope Activity`
  headers
- `scripts/archive.py::USER_AGENT` — composes
  `{display_name}-Research-Archiver/2.0` for Wayback Machine
  submissions

Body of `overview.md`: write the topic statement, scope boundaries
(in-scope / out-of-scope), and any structural notes specific to
the new topic. Use the wiped UAP version (recoverable via
`git show HEAD:meta/topic/overview.md` if needed) as a structural
reference; replace its content entirely.

---

## Step 4 — Regenerate `meta/topic/research-queue.md`

Create a new `meta/topic/research-queue.md` with the same
frontmatter shape as `overview.md` (drop `topic` / `display_name`;
those live only on `overview.md`). The body re-establishes the
two-backlog structure (Queue + Priority Build Queue) that the
toolkit's contributor prompts reference. Empty bodies are fine on
day 1; the queue grows organically as leads accumulate.

---

## Step 5 — Health check

Run:

```
python3 scripts/validate.py
python3 scripts/build-state.py --check
bash scripts/tests/pre-commit.sh
```

All should exit clean on an empty corpus. The validators walk the
content directories; empty-but-existing directories produce no
errors. `build-state.py --check` updates `CLAUDE.md`'s build-state
block to reflect the wiped state (zero nodes everywhere).

If any validator errors surface, the toolkit-bootstrap is broken;
fix before adding content.

---

## Step 6 — First content commit

Commit the wipe + new `overview.md` + new `research-queue.md` as
the fork's commit-zero. Subsequent sessions follow the standard
`prompts/build.md` Phase I → II → III workflow.

---

## What NOT to change

The following are topic-neutral toolkit and should not be
modified during fork-init:

- `meta/schema.yaml` — node types, archetypes, required sections,
  vocabularies. If you discover the new topic genuinely needs a
  schema extension (a new archetype, a new entry-list shape),
  treat it as a real schema change with the same evidentiary
  discipline — not a fork-customization step.
- `meta/conventions.md` — evidentiary discipline.
- `scripts/` — validators, renderer, scaffolders, source tooling.
- `prompts/` — paste-ready session prompts (this one included).
- `meta/templates/` — node body templates.

If during fork-init you find yourself wanting to edit any of the
above, stop and ask: is this a topic-neutral toolkit improvement
(file as a separate commit, BACKLOG, or roadmap item), or am I
trying to escape the topic-customization mechanism? The mechanism
is `display_name` on `overview.md`; everything else should flow
from that.
