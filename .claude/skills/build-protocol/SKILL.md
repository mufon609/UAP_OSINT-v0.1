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
can re-check against disk — not a bare boolean. This disk-truth property is
the keystone the whole role decomposition rests on: nothing commits red, so
a rogue web-pull or manifest-write cannot yield a passing quote — the gate
re-derives truth from disk regardless of which role touched what.

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

**Some primary sources need a verified sibling before the Worker.** Two flavors
carry a built-in deficiency the verbatim / attribution gates cannot catch by
themselves; both are made worker-ready by an orchestrator-produced,
**independently-verified** sibling — the producer cannot self-verify the
failure mode (it is invisible to its author).

- **OCR-scanned documents** (`extraction_type: ocr-scan` / `extraction-lossy`):
  the `pdftotext` layer is corrupt, so quotes pulled from it would be garbage
  or fail the verbatim gate. Its canonical text is a same-stem `.txt` sibling,
  produced by VLM page-image read (see `/prepare-ocr-sibling`).
  Sibling-readiness step: **`/build` step 4b** via
  `/prepare-ocr-sibling`. *The sibling replaces the corrupt text layer.*
- **Label-less transcripts** (any `transcript_provenance` other than
  `stenographic` / `published-transcript` — `auto-caption`,
  `human-corrected-caption`, an explicit `unknown`, or an absent flag; only
  the two human-attested labeled classes skip): the caption text is fine
  but speaker labels are absent — `speaker_id` cannot be derived from the
  caption file alone, only against the recording. Its canonical
  attribution is a same-stem stitched sibling, produced by the video pipeline.
  Sibling-readiness step: **`/build` step 4c** via
  `/prepare-transcript-sibling`. *The sibling adds an attribution layer
  alongside the unchanged verbatim source.*

Producing + verifying + registering each sibling is the **orchestrator's** job,
never the Worker's: the Worker's only Write surface is its own fragment file —
it never produces siblings or sources. This keeps source-read-first + attribution-against-source honest instead
of letting a corrupt extract or label-less caption masquerade as worker-ready.
The orchestrator dispatches the prep skill via the Skill tool; if that
invocation fails, it **HALTs** and directs the user to run the skill — it
never hands the Worker an unprepared source.

**No built node is an example.** Shape comes from the contracts, never from a
peer: `meta/schema.yaml` + `meta/templates/` define the section set and field
layout, `research-scaffold.py` scaffolds it, and the render-phase checks
(`required_sections`, `section_rules`) enforce it. Do not open another built
node or artifact as a structural model — peer-derived shape varies with
whichever peer a session picks, so builds stop being reproducible across
sessions and forks, and a peer's error propagates by mirroring (a build once
inherited a sibling document's wrong cross-link exactly this way — a
fabrication-class error). Every fact, link, and quote on this node comes from
this node's own archived sources.

## Document-corpus extraction — the passage rubric

A commissioned-program / serially-released document is extracted against a
category checklist, so density falls out of consistent selection rather than
each worker re-judging "load-bearing" afresh. Capture, where the source contains
it: **provenance / front matter** (title, authors, preparing org, date, contract
markings); **thesis and scope**; **each major section's finding** (the
load-bearing result of every numbered section — the category most often
dropped); **methods / approach**; **conclusions / recommendations**;
**acknowledgements** (named contributors / institutions — an authorship-network
signal); and **references** (the citation list, captured as `cited_works[]`, not
`quotes[]`). The rubric names what to *consider*; the source decides what is
*present* — it is not a quote-count target. `scripts/tools/coverage-suggest.py`
surfaces uncovered source paragraphs to read against this rubric.

A node in a serially-released set is slugged `{corpus}-{release#}-{short-title}`
with NO date (siblings then sort + cross-reference by release number; the date
lives in `internal_date` / the manifest).

## Density is source-driven — no count targets

The passage rubric above is the document-corpus case of a repo-wide rule:
templates, prompts, and audits do not impose count targets on artifact
content. This applies uniformly to two surfaces:

- **Entry lists** — `quotes`, `naming_quirks`, `affiliations`,
  `relationships`, `corroboration_items`, `program_involvement`,
  `publication_record`, `vouching_chain`, `participants`,
  `witnesses_testimony`, `timeline`, `key_personnel`, `org_relationships`,
  `contracts`, `media_versioning`, and any other entry-list section the
  schema defines.
- **Free-prose fields** — `description`, `background`, `top_relevance`,
  `credibility_notes`.

Populate each surface with what archived primary sources support — no
more, no less. The source produces the count: one entry is correct if the
source supports one, fifty if it supports fifty. Validators check each
entry's traceability to source, never counts.

Count targets ("aim for ~10 quotes", "1-2 paragraphs", "~6-10 entries",
"2-4 sentences", "~50 words per paragraph") create pressure that splits
two ways under real source variance: filler entries when the source
doesn't support the count, or hallucinated content when the model fills
the gap from training knowledge. The surface that introduces a count
target is where these failure modes originate — the rule applies
prospectively to template authoring, prompt drafting, and
scope-at-session-start. Comparison framings count as targets too ("this
section seems sparse"; "comparable nodes have N entries, this has fewer —
anything to add?"): flag specific entries that look unsupported by source,
never aggregate counts.

**Density governs count, not capture.** The rule bars count *targets*; it
does not license declining to capture a class of source material the
source actually carries. Whether the source has a reference list for
`cited_works`, whether a passage is load-bearing, whether a contradiction
is attested are source-*presence* questions answered by reading the
source, not density questions. The misread to refuse is "these references
aren't load-bearing, so leave `cited_works` empty": a source-attested
reference list is captured *because the source carries it* (the passage
rubric above names References as a capture category), and the three-state
`cited_works` affirmation (`NONE | IGNORED | non-empty list`) rejects a
bare `[]` outright. Density governs only how many entries a captured list
then yields. The same holds for every required-but-emptyable
source-anchored section: an empty list is correct only when the source
genuinely lacks that material, never as a discretionary skip.

## Tier linking contract — references run downward (check before you link)

Four tiers; a node references only *lower* tiers, never a greater one. The
sole same-tier exception is entity ↔ entity (the navigational fabric).

- **Tier 1 — sources** (`sources/`): referenced *by* nodes; references nothing.
- **Tier 2 — entity** (person / organization / document / event / transcript /
  media / location): reference sources + other entity nodes; **never** a
  finding or investigation. Entity nodes carry single-source FACTS that may
  name other entities — but a prose or cross-link reference to another entity is
  made only **where the primary source attests the connection**; topical
  similarity (same subject, same program) is not a reference.
- **Tier 3 — findings**: reference sources + entity nodes; **never** another
  finding or an investigation.
- **Tier 4 — investigations**: reference findings + entity nodes + sources;
  **never** another investigation. Nothing references an investigation.

A reference *up* a tier — or a finding/investigation referencing its own tier —
is a defect **even in prose**, not only as a `/findings/` or `/investigations/`
path link (a bare-slug mention like "the {slug} finding" inside an entity node
is the same violation). When you add or carry a cross-reference, check its
direction before emitting it.

**Linking — name it, wrap it.** Every entity a node names in its own authored
prose — person, organization, program, event, document, location, finding — is
wrapped as a `[`/{type}/{slug}`]` link, stub even when that node doesn't exist
yet (the unbuilt-node stub is what populates `## Associated Nodes` and the
broken-link / Priority-Build registry). No "load-bearing vs. incidental"
judgment — if the prose names it, wrap it. A forward-link to an unbuilt node is
the correct value, never null and never bare narration, in a structured path
field (`affiliations[].organization_path`, `relationships[].person_path`, a
program/event path) exactly as in an inline prose wrap. A named theory /
equation / referenced work the prose *discusses* (vs. merely listing it in
`## References`) is itself a document node → `[`/documents/{slug}`]`. **Two
carve-outs only:** (1) verbatim `quote.text` is never wrapped — an entity
appearing only inside a quote is carried by wrapping the canonical form in the
surrounding prose (the form the prose-drift check matches); (2) a bare
`## References` / `cited_works` entry is not wrapped — the bibliography is an
authorship-network dimension, not navigation — unless that work is *also*
discussed in argument prose. `## Associated Nodes` is auto-generated from the
wraps by `associate.py` (never hand-edited); `prose_entity_link` (blocking
check) catches an unwrapped entity already in the repo.

**Interview-derived testimony** — when a node cites a long-form media appearance
(podcast, broadcast, panel, conference talk, streamed interview) as evidence,
three classes must appear as `[`/path`]` wraps (usually inside the
`timeline[].event` text): the **venue** (host/distributor org →
`/organizations/{slug}`), the **host / interviewer / moderator**
(→ `/people/{slug}`, structurally distinct from the appearance's subject), and
the **transcript-to-be** (the `/transcripts/{slug}` where the verbatim evidence
will live, forward-linked before it is built). Called out because a media
appearance is where they are most often missed.

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

Each `--phase` token names the role whose output it validates. The canonical
phase tokens are enumerated here (so `phase_routing_parity.py` can confirm
none ships undocumented), but their descriptions are **not** restated — read
them from `--list-phases`:

- `archive` · `extract` · `organize` · `link` · `render`

`preflight` (parse / structure) runs in every phase.

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

**How the block actually holds.** A hand-edit to a node body is blocked two
ways. The mechanical gate is a committed `settings.json` `permissions.deny`
rule on the node-type directories — it binds for the main thread *and*
subagents (the builder is the one role holding `Edit`), and the renderer is
unaffected because it writes the body via Python file I/O, not the
Edit/Write tool. A `PreToolUse` hook
(`.claude/hooks/block_node_body_edit.sh`) is the main-thread backstop,
carrying the fix-pointing message. (The hook alone is insufficient: a
`settings.json` `PreToolUse` hook does **not** fire for a *subagent's* tool
call, so the deny rule is what actually gates the builder.) Two more hooks
back the discipline — and these gate main-thread actions, so the hook
mechanism is sufficient: a `git commit` runs the full pre-commit chain **at
commit execution time** and blocks on any red gate — the repo githook
`.githooks/pre-commit` runs the chain after any chained fix in a compound
`fix && git commit` has run, and the `block_commit_if_red.sh` PreToolUse
guard keeps that floor un-droppable (arms `core.hooksPath` on every commit
attempt, denies the bypass routes — `--no-verify` and abbreviations, `-n`
short-flag clusters, `core.hooksPath` manipulation — with heredoc-stripped
token scanning so commit-message prose never trips it, and falls back to
running the chain at PreToolUse time if the githook is ever missing). And
scaffolding a second uncommitted new person/organization node is blocked
(the one-new-synthesis-node-per-session rule).

## Handoff stubs

Your output is your **return value**: return your role's stub (per the schema
in [stub-schemas.md](stub-schemas.md)) as your final message. That return value
is the handoff the orchestrator reads to drive the next role — you write no file
for it, with one exception: the **worker writes its fragment file**
(`/tmp/fragments-{slug}/{stem}.yaml`, stub-schemas.md) and its stub
carries the path; `merge-fragments.py` transports the verbatim payload from
that file into the artifact byte-exactly. The durable record is the manifest +
artifact + git. Read only the stub schema for your own role.

## Orchestration branches

- **all-internal** — the internal survey sets `all_internal: true`,
  `gaps: []` → external + archive roles are skipped; the build proceeds from
  the reused, already-archived sources.

### Partial re-entry — skip scaffold, run a minimal role subset

When the artifact already exists, a change runs through only the roles it
needs — never a fresh scaffold (a change re-enters at the phase its material
demands; the cheapest correct path). The shared rules:

1. **Skip scaffold** — the node + artifact exist (`new.py` /
   `research-scaffold.py` do not run; the latter cannot append anyway).
2. **Dispatch only the roles the change needs** — a data-correctness fix needs
   no worker; a quote from an already-archived source needs the worker but no
   external/archive; a new or re-pulled source needs external → archive →
   worker. No role introduces a quote outside `extract`.
3. **Route failures** — a failing check goes through `route_failure.py` to its
   owning role; the fix target is always artifact data.
4. **Preserve contradictions** — material that disagrees with a sourced claim
   is added alongside via `superseded_by` / `contradicted_by` /
   `corroborated_by`, never overwritten.

The entry point sharing this contract:

- **`/augment`** (user-triggered, primary node) — a maintenance change to an
  existing node (add a recovered quote, re-source a dead citation, correct a
  data field), classified into the role subset above; the proactive counterpart
  to reactive `/audit`. See the `augment` skill.

## One new synthesis-heavy node per session

A new **person** or **organization** node is a large free-prose surface
(the drift-prone types). Only one new such node may be scaffolded per
session; lighter types (document / event / transcript / media / location /
finding / investigation) may batch. This is enforced by a hook on the
scaffolder — do not work around it.

## Why these roles — capability boundaries, not feedback granularity

Each role is a distinct **capability boundary** that makes the discipline
mechanical — the separation *is* the enforcement:

| Role (subagent) | Capability boundary it enforces |
|---|---|
| `internal-investigator` | read-only; no web tools, no manifest-write → an "archived-only" reuse survey that can't quietly pull from the web |
| `external-investigator` | web-enabled, but no manifest commit; its read is re-checkable (returns a verbatim `confirming_span`, not a bare "I read it") |
| `archive` | the only role that writes the manifest |
| `worker` | the single phase that introduces verbatim quotes; writes its own fragment file + slim stub, never the shared artifact (one file per worker, so parallel workers can't race) |
| `builder` | the synthesis / prose-drift surface; edits only the artifact, never the node body; owns the fragment merge (mechanical, via merge-fragments.py) |
| `auditor` | a fresh-context cold re-read — the independent verifier the producing role can't be |

Two former roles **dissolved**: the Orchestrator (a control loop, now the
`/build` skill) and the Error agent (a `check → phase → role` lookup, now
`scripts/tools/route_failure.py` driven by `scripts/checks/_phases.py`).

### Mechanical enforcement vs. role discipline

(Verified.) Whole-tool *absence* from a role's `tools:` binds hard — the
worker genuinely has no Write/Bash; the investigators have no
WebFetch/WebSearch. But **per-command scoping inside `tools:` is advisory**
in the current Claude Code environment: a role carrying any `Bash(...)`
entry effectively gets full Bash, so the "no manifest-write" /
"no web-via-curl" lines above rest on **role discipline**, not a hard gate
(empirically, roles asked to cross those lines could). The mechanical floor
is therefore *not* the per-command `tools:` scoping but: (1) committed
`settings.json` `permissions.deny` rules, which **do** bind for subagents
and hot-reload; and (2) the disk-truth gate (verbatim + prose-drift)
enforced un-bypassably at the commit boundary (the non-negotiable
invariant above).
