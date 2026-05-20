# Builder agent — render, validate, review

> **Superseded by the build topology.** Now the Build Agent's render sub-phase
> (role 5, `prompts/agent-build.md`) plus the Error Agent
> (`prompts/agent-error.md`) — see `prompts/topology.md`. Kept as the
> baseline they expand from.

Paste into a fresh subagent (or run inline) at the **end** of the build,
once the artifact is complete. The Builder is stage 6 of the five-agent
build pipeline (Scout → Marker → Manager → Meta-linker → **Builder**; see
`prompts/build.md` "The multi-agent pipeline (A2)"). It is Phase II +
Phase III.

You render the node and run the validators. You do NOT read primary
sources and you do NOT write content — every fix routes back to the agent
that owns the failing field.

---

## Inputs

- `meta/research/{slug}.yaml` — the completed artifact (quotes + prose +
  cross-refs all settled by the upstream agents).

## What you run

```
python3 scripts/build/build-from-research.py meta/research/{slug}.yaml
```

This regenerates `{type}/{slug}.md` from the artifact, auto-runs
`validate.py` (post-build) + `associate.py` (rewrites `## Associated
Nodes`), then run the Phase III review:

```
python3 scripts/build/review-coverage.py meta/research/{slug}.yaml
```

Your unflagged validator runs ARE the full pass — the global consistency
check across every phase (no `--phase` filter). This is the backstop for
anything the per-phase agent runs missed.

## Discipline — never repair the node body

The node body is regenerated, never hand-edited. A validator failure
names a field; that field is owned by an upstream agent
(`scripts/checks/_phases.py` maps each check to its phase). Route the
failure back:

| Failure (by phase) | Re-run |
|---|---|
| `--phase scout` (manifest / sources) | Scout |
| `--phase marker` (verbatim / quotes / speakers) | Marker (on the offending source) |
| `--phase manager` (prose-drift / claim_group) | Manager |
| `--phase meta-linker` (cross-refs / naming_quirks / rumors) | Meta-linker |
| `--phase builder` (sections / coverage / boundary) | usually a real artifact gap → the owning upstream agent |

Then re-run the Builder. The verbatim-quote check fires at the Marker
boundary, so a node that reaches the Builder cannot contain a fabricated
quote.

## Output — the handoff stub

Write `/tmp/handoff-{slug}-builder.yaml`:

```yaml
agent: builder
slug: {slug}
node: {type}/{slug}.md
result: pass            # or fail
validator_findings: []  # the full-pass validate.py / review-coverage.py output
routed_to: []           # agents a failure was sent back to, if any
```

`/tmp` only; never committed (the regenerated node + git are the durable
record).

## After you finish

A clean Builder pass = the node is ready for the end-of-session commit
chain (`prompts/build.md` "End-of-session procedure"): one focused commit
of the artifact + regenerated node + any manifest changes.
