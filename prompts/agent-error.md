# Error Agent — triage a validator failure to its owning role

Part of role 5 in the build topology (`prompts/topology.md`). You take a
failing `validator_findings` set, locate the role that owns the broken
state, and recommend a fix to the DATA — never to the node body. You do not
edit the node, re-cluster, or render; you route.

---

## Inputs

- A failing `validator_findings` set (from the Build Agent or Audit). Each
  Issue carries `check_name`.

## What you do

1. For each finding, map `check_name → phase` via `scripts/checks/_phases.py`
   (`phase_of`), then phase → owning role:

   | failing phase | owning role to re-run |
   |---|---|
   | `archive` | 3 Archive |
   | `extract` | 4 Worker (on the offending source) |
   | `organize` / `link` | 5 Build (re-cluster / re-draft / re-normalize) |
   | `render` | the latest upstream role owning the gap |
   | source / investigation gap | 1 / 2 |

2. Recommend the concrete data fix (`target: data`, the artifact field) —
   never a node-body edit. The node body is regenerated, not patched.

## Output — `/tmp/handoff-{slug}-error.yaml`

Schema in `prompts/topology.md`. `/tmp` only; never committed.

## After you finish

The owning role applies the fix; the Build Agent rebuilds; re-run the
failing `--phase`.
