# Build topology — roles, phases, and per-agent feedback

The canonical map of how a node build decomposes into agents, which
`--phase` bundle gives each agent instant feedback, and how the
orchestrator sequences them. This expands the prior five-agent pipeline
(`prompts/build.md` "The multi-agent pipeline") into seven roles, for two
goals: **instant per-agent feedback** (each agent validates only what it
just produced) and **no monolithic check pass**.

Paste-ready launch prompts for each role live at `prompts/agent-{role}.md`
(see the role table). This file is the shared contract they reference.

---

## The seven roles

| # | Role | Reads sources? | Produces | Feedback phase |
|---|---|---|---|---|
| 0 | **Orchestrator** | no | sequencing + handoff stubs + the single post-investigation scaffold | `archive` (after the scaffold) |
| 1 | **Internal Investigator** | archived only | reuse survey (`reusable_sources[]`, `gaps[]`) + classification | — (manifest tools; no artifact yet) |
| 2 | **External Investigator** | yes (candidate content) | confirmed deep-URL queue | — (`manifest.py add --dry-run` per lead) |
| 3 | **Archive** | yes (downloads bytes) | manifest entries + `primary_sources[]` + scratch | `archive` |
| 4 | **Worker** (`worker_kind`) | yes (one source) | `quotes[]` + advisory `claim_group` + cross-ref candidates | `extract` |
| 5 | **Build Agent** (+ Error Agent) | scratch for judgment only | organized quotes + free-prose + cross-refs + rendered node | `organize` → `link` → `render` |
| 6 | **Audit** | scratch in hand | health report + adjacent-node propagation | full unflagged pass |

Roles 0/1/2 produce no gated artifact state, so they have no `--phase`
bucket — their feedback is preflight plus the manifest tools
(`manifest.py verify-paths`). Role 2 self-checks each lead with
`manifest.py add --dry-run` (validates URL / path / format /
path-uniqueness without writing); the lead is committed when role 3
archives it, and the hard guarantee is role 4's `verbatim_quotes` boundary.

**Naming.** The orchestrator is **never** called "Manager" — that word is
retired from the agent vocabulary. The quote-organization work the old
"Manager" did now lives in the Build Agent (role 5).

---

## Phase vocabulary (the `--phase` tokens)

A `--phase` token is named after the role whose output it validates. The
map from check → phase is `scripts/checks/_phases.py` (the routing source
of truth); `validate.py`, `validate-research.py`, and `review-coverage.py`
all accept `--phase`.

| phase | role | validates |
|---|---|---|
| `preflight` | — (always-on) | parse / structure / version; runs in every phase |
| `archive` | 3 | manifest integrity + `primary_sources[]` + `doc_form_archival_status` |
| `extract` | 4 | `quotes` / `verbatim_quotes` / `speakers` / `speaker_baseline_consistency` |
| `organize` | 5 | free-prose synthesis entry-shape (corroboration, vouching, finding/investigation prose lists) |
| `link` | 5 | cross-reference surfaces + `naming_quirks` / `rumors` / `cross_refs` / `prose_drift` |
| `render` | 5 / 6 | render-time node structure + the cross-layer checks (coverage / boundary / description-drift) |

The older phase names — `scout` / `marker` / `manager` / `meta-linker` /
`builder` — are still accepted on the CLI and resolve to
`archive` / `extract` / `organize` / `link` / `render`.

**`--phase` only ever narrows a run.** An unflagged run is the full pass;
a check absent from the map defaults to `render`, so a newly added check
is always exercised by the full pass and never silently dropped. The
Build Agent's final render run and the Audit role's full pass are the
global consistency check — the only place the cross-cutting checks
(`link_resolution`, `boundary`, `coverage`, `description_token_drift`,
`finding_source_in_entity_node`, `governance_files`) can fire, because
they read state from multiple roles or the whole repo.

`review-coverage.py` accepts `--phase` only for command-shape symmetry:
all its checks are render-phase, so any non-render phase short-circuits it
to zero checks. The Build Agent's render sub-phase calls all three
orchestrators with one `--phase render`.

---

## Source-read-first invariant

The prior pipeline collapsed the investigator and verifier into one agent
because a URL-only investigator violates source-read-first. The 2/3 split
(role 2 finds, role 3 archives) is safe:

> Every inclusion decision is made against source **content**, never a URL
> or title. Soft-enforced at roles 1 and 2 — each reads the candidate body
> before judging load-bearing-ness. **Hard-enforced mechanically at role
> 4**, where `verbatim_quotes` matches every emitted quote against the
> archived + extracted file. **No agent may introduce a verbatim quote
> outside the `extract` phase**, so the verbatim check fires at exactly one
> boundary. The 2↔3 split moves *who downloads the bytes*, not *whether
> they were read before a quote is trusted*.

`prompts/web-claude-investigator.md` is an optional upstream lead
generator feeding role 2 — a candidate list, never an inclusion decision.

---

## Per-agent feedback — what each role runs the moment it finishes

| role | runs | writes into the stub's `validator_findings` |
|---|---|---|
| 1 Internal Investigator | `manifest.py verify-paths` on the reuse set | manifest health of the reuse set (no artifact exists yet) |
| 2 External Investigator | `manifest.py add --dry-run` per lead | malformed / colliding leads, caught before handoff |
| 3 Archive | `validate.py --phase archive` (manifest health) | manifest family — no artifact until the post-Archive scaffold |
| 0 Orchestrator — scaffold | `validate-research.py --phase archive {artifact}` | the scaffold parses + `primary_sources` registered correctly (the artifact's first validation) |
| 4 Worker | `validate-research.py --phase extract {artifact}` | the verbatim-quote boundary (all worker kinds share it) |
| 5 Build, organize | `validate-research.py --phase organize {artifact}` | synthesis entry-shape |
| 5 Build, link | `validate-research.py --phase link {artifact}` | cross-refs + naming_quirks + rumors + prose-drift |
| 5 Build, render | `build-from-research.py {artifact}` → `validate.py --phase render {node}` + `review-coverage.py --phase render {artifact}` | render structure + cross-layer |
| 6 Audit | `validate.py` + `validate-research.py` + `review-coverage.py --all` (unflagged) | everything, incl. the global-only checks + propagation |

The Build Agent's three sub-phases (organize → link → render) are three
tight checkpoints inside one role, so a defect surfaces before the next
sub-phase builds over it — render is last because the coverage/boundary
checks need the just-rendered node.

---

## Handoff stubs

Ephemeral, at `/tmp/handoff-{slug}-{agent}.yaml`, never committed (the
manifest + artifact + git are the source of truth). Each carries `agent`,
`slug`, `inputs_consumed`, `outputs_produced`, `validator_findings`.

```yaml
# /tmp/handoff-{slug}-internal-investigator.yaml
agent: internal-investigator
slug: {slug}
target: {type}/{slug}
linked_nodes: [/people/foo, /organizations/bar]
reusable_sources:
  - path: government/file.pdf
    scratch: /tmp/scratch-{slug}-1.txt
    covers: ["Crash-Retrieval Program"]
gaps: ["post-2023 testimony on biologics"]
all_internal: false            # true => orchestrator skips roles 2 and 3
validator_findings: []
```
```yaml
# /tmp/handoff-{slug}-external-investigator.yaml
agent: external-investigator
slug: {slug}
consumed_gaps: ["post-2023 testimony on biologics"]
queued_sources:                # may be empty — an exhausted record is a valid result
  - url: https://oversight.house.gov/.../document.pdf
    suggested_path: government/file.pdf
    format: pdf
    tier: primary              # primary | secondary-lead-only
    read_confirmed: true       # content was read, not URL-only
    rationale: <one line: why load-bearing>
unfilled_gaps: []
validator_findings: []
```
```yaml
# /tmp/handoff-{slug}-archive.yaml
agent: archive
slug: {slug}
archived:
  - url: https://oversight.house.gov/.../document.pdf
    path: government/file.pdf
    archive_status: archived   # or pending + wayback_date
    scratch: /tmp/scratch-{slug}-2.txt
primary_sources_registered: [government/file.pdf]
validator_findings: []         # validate.py --phase archive
```
```yaml
# /tmp/handoff-{slug}-worker-{kind}-{N}.yaml
agent: worker
worker_kind: pdf               # pdf | html | caption | foia
slug: {slug}
source: government/file.pdf
inputs_consumed: [/tmp/scratch-{slug}-2.txt]
outputs_produced:
  candidates: 7                 # quotes[] candidates; legitimately 0 for an about-the-subject / institutional source
  claim_groups_proposed: ["Crash-Retrieval Program"]
  cross_ref_candidates:
    - entity: /people/jane-doe
      kind: relationship
      span: "p. 4, ¶2"
  background_material:          # about-the-subject sources (the quotes: [] case): facts for the Build Agent's prose
    - fact: "first Acting Director of the IPMO"
      source_phrasing: "<exact words from source — prose-drift grounding>"
      location: "¶ Biography"
validator_findings: []         # validate-research.py --phase extract
```
```yaml
# /tmp/handoff-{slug}-build.yaml
agent: build
slug: {slug}
node: {type}/{slug}.md
claim_groups: [{label: "Crash-Retrieval Program", primaries: [q7], pointers: [q15], n_sources: 3}]
tested_before_build: true      # organize + link were clean before render
result: pass                   # or fail
routed_to_error_agent: []
validator_findings: []
```
```yaml
# /tmp/handoff-{slug}-error.yaml
agent: error
slug: {slug}
trigger: build                 # build | audit
findings:
  - check_name: prose_drift
    phase: link
    owning_role: build
    field: description
    fix: "token 'Sentinel' ungrounded — capture as naming_quirk or remove"
    target: data               # always data, never the node body
routed_back_to: [build]
```
```yaml
# /tmp/handoff-{slug}-audit.yaml
agent: audit
slug: {slug}
node: {type}/{slug}.md
health: pass
adjacent_needs_update:
  - node: /people/jane-doe
    reason: "new source attests a relationship she should carry"
    material_in_hand: /tmp/scratch-{slug}-2.txt
    skip_external: true        # role 2 skipped — material already archived
propagation_loop: [/people/jane-doe]
validator_findings: []
```

---

## Orchestration + branches

**Happy path.** `0 (scaffold) → 1 → 2 → 3 → 4×N (parallel) → 5
(organize → link → render) → 6`. The orchestrator reads each stub before
launching the next, passing `outputs_produced` to the next agent's
`inputs_consumed`.

**Branch — tightening loop.** Role 6 flags `adjacent_needs_update[]` with
`skip_external: true` → the orchestrator re-enters at **role 4** (extract
the relevant spans from the already-archived scratch) → role 5 (update the
adjacent artifact + rebuild) → role 6 (re-audit). Roles 2/3 are skipped:
no new URL, no new bytes.

**Branch — all-internal.** Role 1 sets `all_internal: true`, `gaps: []` →
the orchestrator skips roles 2 and 3 and jumps to role 4 on the reused
scratch files.

---

## Fix the data, never the node body

The node body is regenerated from the artifact, never hand-edited. When a
check fails, the Error Agent maps `check_name` → its phase (via
`_phases.phase_of`) → the owning role, and recommends a fix to the
**artifact data**; the owning role applies it and the Build Agent rebuilds.

| failing phase | owning role to re-run |
|---|---|
| `archive` | 3 Archive |
| `extract` | 4 Worker (on the offending source) |
| `organize` / `link` | 5 Build (re-cluster / re-draft / re-normalize) |
| `render` | the latest upstream role owning the gap |
| source/investigation gap | 1 / 2 |

---

## Script ownership

| script | owner |
|---|---|
| `new.py` + `research-scaffold.py` | role 0, **once, after roles 1–3** settle the classification + source set (NOT at kickoff): `new.py` creates the node `.md`, then `research-scaffold.py --sources {all paths}` writes the artifact. `research-scaffold` writes fresh and cannot append, so every source goes in this one call. |
| `manifest.py add` | role 3 (roles 1/6 only read the manifest) |
| `extract-source.py` | role 1 (existing sources) + role 3 (new sources) — each source extracted once |
| `build-from-research.py` (+ auto `associate.py` + `validate.py`) | role 5 |
| `review-coverage.py` | role 5 (gate) + role 6 (audit) |
| `associate.py` | auto via `build-from-research.py`; standalone only at role 6 after a propagation edit |

---

## Launch prompts

| role | prompt |
|---|---|
| 0 Orchestrator | `prompts/agent-orchestrator.md` |
| 1 Internal Investigator | `prompts/agent-internal-investigator.md` |
| 2 External Investigator | `prompts/agent-external-investigator.md` |
| 3 Archive | `prompts/agent-archive.md` |
| 4 Worker | `prompts/agent-worker.md` (one prompt, `worker_kind` parameter) |
| 5 Build / Error | `prompts/agent-build.md`, `prompts/agent-error.md` |
| 6 Audit | `prompts/audit.md` (role-6 propagation section) |
