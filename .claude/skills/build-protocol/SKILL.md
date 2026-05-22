---
name: build-protocol
description: Shared contract for the node-build pipeline — phase vocabulary, the source-read-first invariant, the fix-the-data rule, handoff-stub transport, and the orchestration branches. Background knowledge preloaded into every build subagent; not a standalone action.
user-invocable: false
---

# Build protocol — the shared contract

This is the contract every build role shares. It is preloaded into each
build subagent so no role restates it. It defines *how* a node is built;
the *what* (this instance's subject) is never named here — keep this file
topic-neutral (placeholders only).

## The non-negotiable invariant — gates read disk, not memory

The verbatim-quote check and the prose-drift check derive truth from
**disk**: they re-read the extracted source file and the artifact on every
run. They never trust an agent's memory or a handoff value. This is why a
fresh-context subagent is safe — it cannot fabricate a quote, because the
gate re-derives from the file. **Never let a gate trust a returned value in
place of re-reading the source.** Any confirmation an agent reports
(e.g. "I read this source") must be backed by a verbatim span the next role
can re-check against disk — not a bare boolean.

## Source-read-first

Every inclusion decision is made against source **content**, never a URL or
title. Soft-enforced where sources are surveyed/fetched; **hard-enforced at
the `extract` phase**, where the verbatim check matches every emitted quote
against the archived + extracted file. No role may introduce a verbatim
quote outside `extract`.

Load-bearing-ness is judged **in context, not isolation**: an entity's
relevance often lives in its relationships, not its own source. The
`linked_nodes` set + topic-relevance framing the internal survey assembles
must be **threaded forward** to every downstream role; no role judges
relevance from a source alone.

**OCR-scanned sources need a verified sibling before the Worker.** A primary
source flagged `extraction_type: ocr-scan` / `extraction-lossy` (manifest) is
**not worker-ready**: its `pdftotext` layer is corrupt, so quotes pulled from it
would be garbage or fail the verbatim gate. Its canonical text is a same-stem
`.txt` sibling, produced by VLM page-image read and **independently verified by
a different agent** — the producer cannot self-verify a hallucination, which is
invisible to its author (`meta/conventions.md` "Producing the `.txt` sibling").
Producing + verifying + registering the sibling is the **orchestrator's
sibling-readiness step** (`/build` step 4b), run before the Worker — never the
Worker's job: the Worker has no Write tool and emits a fragment, not a file.
This keeps source-read-first honest for scanned documents instead of letting a
corrupt extract masquerade as source text.

**Exemplars give shape, not facts.** A built node handed to you as a structural
model (a sibling document, an archetype peer) supplies SHAPE only — section set,
field layout, quote-density feel. Every fact, every cross-reference link, and
every quote is confirmed against THIS node's own source, never carried over from
the exemplar. Copying a fact or link from an exemplar is a fabrication-class
error (a build once inherited a sibling's wrong cross-link by mirroring it);
the exemplar may be wrong, and the gate that catches it is your re-read of the
source, not the exemplar's apparent authority.

## Tier linking contract — references run downward (check before you link)

Four tiers; a node references only *lower* tiers, never a greater one. The
sole same-tier exception is entity ↔ entity (the navigational fabric).

- **Tier 1 — sources** (`sources/`): referenced *by* nodes; references nothing.
- **Tier 2 — entity** (person / organization / document / event / transcript /
  media / location): reference sources + other entity nodes; **never** a
  finding or investigation.
- **Tier 3 — findings**: reference sources + entity nodes; **never** another
  finding or an investigation.
- **Tier 4 — investigations**: reference findings + entity nodes + sources;
  **never** another investigation. Nothing references an investigation.

A reference *up* a tier — or a finding/investigation referencing its own tier —
is a defect **even in prose**, not only as a `/findings/` or `/investigations/`
path link (a bare-slug mention like "the {slug} finding" inside an entity node
is the same violation). When you add or carry a cross-reference, check its
direction before emitting it. Full matrix: `meta/conventions.md` "Tier model
and linking contract".

## Build phases

The phase vocabulary is generated from the routing source of truth
(`scripts/checks/_phases.py`) — run it rather than memorizing a list:

```!
python3 scripts/checks/_phases.py --list-phases
```

`--phase` only ever **narrows** a run; an unflagged run is the full pass. A
check absent from the map defaults to `render`, so a new check is always
exercised. To see the phase (and owning role) of one check:
`python3 scripts/checks/_phases.py --check-phase <check_name>`.

## Fix the data, never the node body

The node body under `{type}/{slug}.md` is **regenerated** from the artifact,
never hand-edited. A node-body edit is blocked by a hook. When a check
fails, route it — don't patch the symptom:

```
python3 scripts/tools/route_failure.py <failing_check_name> [<more> ...]
```

This maps each check → its phase → the owning role (via `_phases.py`) and
prints the fix `target: data`. The owning role applies the fix to the
artifact; the builder rebuilds. The fix target is always artifact data.

## Handoff stubs

Your output is your **return value**: return your role's stub (per the schema
in [stub-schemas.md](stub-schemas.md)) as your final message. That return value
is the handoff the orchestrator reads to drive the next role — you write no file
for it. The durable record is the manifest + artifact + git. Read only the stub
schema for your own role.

## Orchestration branches

- **all-internal** — the internal survey sets `all_internal: true`,
  `gaps: []` → external + archive roles are skipped; the build proceeds from
  the reused, already-archived sources.
- **tightening loop** — the audit flags `adjacent_needs_update[]` with
  `skip_external: true` → re-enter at the `extract` phase for the adjacent
  node (its material is already archived; no new URL, no new bytes), then
  rebuild and re-audit until no adjacent node flags.

## One new synthesis-heavy node per session

A new **person** or **organization** node is a large free-prose surface
(the drift-prone types). Only one new such node may be scaffolded per
session; lighter types (document / event / transcript / media / location /
finding / investigation) may batch. This is enforced by a hook on the
scaffolder — do not work around it.
