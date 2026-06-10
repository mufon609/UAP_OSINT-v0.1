---
name: augment
description: Orchestrate a maintenance change to an existing node — add a recovered quote, re-source a dead citation, or correct a data field — without re-scaffolding. The proactive counterpart to reactive /audit; runs on the main thread and dispatches the minimal role subset. Use to maintain a built node, not to build a new one.
argument-hint: {type}/{slug} "<what to change>"
allowed-tools:
  - Agent(external-investigator, archive, worker, auditor)
  - Skill(prepare-ocr-sibling)
  - Skill(prepare-transcript-sibling)
  - Read
  - Grep
  - Glob
  - Edit
  - Bash(python3 scripts/build/extract-source.py *)
  - Bash(python3 scripts/build/merge-fragments.py *)
  - Bash(python3 scripts/build/build-from-research.py *)
  - Bash(python3 scripts/build/validate.py *)
  - Bash(python3 scripts/build/validate-research.py *)
  - Bash(python3 scripts/build/review-coverage.py *)
  - Bash(python3 scripts/build/stamp-speaker-id.py *)
  - Bash(python3 scripts/build/associate.py *)
  - Bash(python3 scripts/build/build-state.py *)
  - Bash(python3 scripts/tools/coverage-suggest.py *)
  - Bash(python3 scripts/tools/route_failure.py *)
---

# Augment an existing node

Target + change: **$ARGUMENTS** (ask the user if empty). You are the orchestrator on the main
thread — the **proactive** counterpart to reactive `/audit`. You maintain an **existing** node: add
a recovered quote, re-source a dead citation, or correct a data field. You **never scaffold** (the
node and its artifact exist — `new.py` / `research-scaffold.py` are not yours and cannot append)
and **never hand-edit the node body** (it regenerates from the artifact; a body edit is hook-
blocked). You follow the shared **Partial re-entry** contract in `build-protocol` — skip scaffold,
dispatch only the roles a change needs, route a failing check to its owning role, preserve
contradictions via pointers. The subagents you dispatch get that contract preloaded; thread the
node's `linked_nodes` / relevance context forward to each.

## 1. Classify each change, and state it back before acting

Real maintenance bundles changes (one request can be several shapes across one or more nodes).
Decompose it; for each fact:

- **Q1 — does it need a NEW verbatim quote?** No → **Shape A**.
- **Q2 (yes) — are the bytes already on disk** — source archived in `sources/` + registered in
  `sources/manifest.yaml`, and (if `ocr-scan` / `extraction-lossy`) carrying a verified same-stem
  `.txt` sibling? Yes → **Shape B**; No → **Shape C**.

Present the per-fact classification + the planned artifact edits to the user **before changing
anything** (mirrors `/audit`). The shape is never chosen silently.

## 2. Run each fact's minimal path

- **Shape A — data-correctness fix** (re-date, correct a field, fix a relationship descriptor,
  remove an *unattested* string): **no role**. Edit the **artifact** (`meta/research/{slug}.yaml`)
  directly, exactly as `/audit` step 4 does. See §3 for what may and may not be removed.
- **Shape B — quote from an already-archived source**: §4 OCR gate → `Agent(worker)` on that one
  source (`worker_kind` per its format) → the worker writes its fragment file and returns the slim
  stub → merge it with `python3 scripts/build/merge-fragments.py --append meta/research/{slug}.yaml
  {fragment_path}` (`--append` is the maintenance mode: it allows the populated artifact and
  continues qN/cwN numbering — never hand-copy the verbatim payload) →
  `validate-research.py --phase extract` (the verbatim boundary; re-reads disk).
- **Shape C — needs a new or re-pulled source**: `Agent(external-investigator)` with the gap +
  `linked_nodes` (**reject any queued source lacking a `confirming_span`** — the non-negotiable
  invariant) → `Agent(archive)` (downloads, writes the manifest, submits to Wayback, extracts the
  scratch — the only manifest writer) → §4 OCR gate → `Agent(worker)` → you merge → `validate-
  research.py --phase extract`.

On a **transcript artifact** (Shape B or C), derive the merged quote's `speaker_id` after the merge
and before validating: `python3 scripts/build/stamp-speaker-id.py meta/research/{slug}.yaml` (dry
run, then `--write`) — the verified attribution sibling is the source of truth; never hand-key it.

On any failing check, `python3 scripts/tools/route_failure.py {check}` names the owning role; apply
the fix to the artifact and re-validate. The fix target is always artifact data.

## 3. Removal + contradiction discipline

- **Removing a string** — ask "does it trace to any archived source?" If **no** (unattested — e.g.
  a label that appears in no source), deleting it is a legitimate Shape-A fix. If **yes** (source-
  backed), you may **not** delete it: a source-backed Flagged item can only be **superseded** by a
  *new contradicting primary source* (escalates to Shape C).
- **Correction vs. contradiction** — a *correction* (the old value was simply wrong, e.g. a date
  taken from `dateModified` instead of `datePublished`) edits in place. A *contradiction* (a new
  source genuinely disagrees with an existing sourced claim) **preserves both** via `superseded_by`
  / `contradicted_by` / `corroborated_by` — never overwrite. Declare which case applies before
  editing; the mechanics are opposite.

## 4. Sibling-readiness gate — before any worker

Read the manifest entry for the source (the why + the
produce→independently-verify→register contract: build-protocol → "Some primary sources need
a verified sibling"). Two flavors:

- **OCR-scan / extraction-lossy without a verified `.txt` sibling** → extract is corrupt and **not
  worker-ready**. Invoke `/prepare-ocr-sibling {source}` via the Skill tool; if that invocation
  fails, **HALT** and direct the user to run it. Resume once the verified sibling is registered —
  `extract-source.py --artifact` then prefers it.
- **Label-less transcript without a verified `-attribution.yaml` sibling** — any
  `transcript_provenance` other than `stenographic` / `published-transcript`, including an explicit
  `unknown` or an absent flag (classify it in the manifest while here) → `speaker_id` is not
  derivable from the caption alone. Invoke
  `/prepare-transcript-sibling {slug}` via the Skill tool; same HALT-on-failure rule. Resume once
  registered; the verbatim source is unchanged (the sibling adds the attribution layer indexed by
  line range — see `meta/schema-speaker-attribution.yaml` — that `validate-research.py` matches
  `speaker_id` against).

## 5. Rebuild, audit, close out

For **each affected node, once** (not per-fact):

1. `python3 scripts/build/build-from-research.py meta/research/{slug}.yaml` — regenerates the body,
   runs `associate.py` (cross-refs), and validates.
2. Confirm the change **renders** — grep the regenerated body (an edit that lands only in an
   artifact-only field never surfaces; move it to a rendered surface).
3. `python3 scripts/build/review-coverage.py --all` clean.
4. **Audit** — `Agent(auditor)` for a fresh-context cold read: **required** for Shape B / C (new
   evidentiary material warrants the independent re-read), **optional** for a pure Shape A
   fix (the reader-grep + validators suffice). The auditor is **recommend-only**; you apply any
   user-approved fix (a Shape-A edit) and re-validate.
5. If a node's **status or type changed**, refresh build-state: `python3 scripts/build/build-state.py --update`.

The user commits (the full pre-commit chain runs at the boundary, un-bypassable). In a **multi-node
batch**, commit each node's result **before** dispatching the next node's auditor — an auditor's
effective Bash can `git restore` uncommitted work.

Do not: scaffold (use `/build` for a new node); hand-edit the node body; introduce a quote outside a
worker / the `extract` phase; remove a source-backed item without a contradicting source; or
overwrite a contradicted claim instead of preserving both.
