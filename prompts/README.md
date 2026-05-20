# Prompts

Paste-ready session prompts for common workflows. Not loaded automatically —
copy the relevant prompt into a fresh Claude Code session.

| File | Use for |
|---|---|
| `onboard.md` | First-time session or any fresh session start |
| `fork-init.md` | Bootstrap the toolkit for a different topic (run once on a fresh fork) |
| `build.md` | Build a new node (Phase I → II → III) |
| `agent-scout.md` | Scout agent (build pipeline, stage 1) — find / confirm / archive primary sources + scaffold + extract; produces the scratch files the Marker reads |
| `agent-marker.md` | Marker agent (build pipeline) — per-source verbatim quote extraction (launchable form of task T2); one subagent invocation per source, feeds the Manager |
| `agent-manager.md` | Manager agent (build pipeline) — cross-source quote organization (A3: `claim_group` grouping + `corroborated_by` de-dup) + free-prose synthesis; one invocation per node |
| `agent-meta-linker.md` | Meta-linker agent (build pipeline) — cross-reference surfaces (relationships / affiliations / timeline / …) + `[`/path`]` prose wraps + naming_quirks (T4) + rumors (T5) |
| `agent-builder.md` | Builder agent (build pipeline, final stage) — render the node + full-pass validate + Phase III review; routes failures back to the owning agent, never edits the node body |
| `design-expanded-pipeline.md` | Design/plan session — investigate the repo, then design the expanded agent topology (orchestrator + internal/external investigators + archive + type-specialized workers + build/error + audit) and the per-phase decomposition of the checks/scripts for instant per-agent feedback. Extends A2 + `--phase`; resolves C42 |
| `audit.md` | Audit an existing node for evidentiary integrity (includes the audit-correction pattern for applying changes to an existing artifact) |
| `quote-relevance-audit.md` | Audit `quotes[]` on an existing artifact for load-bearing relevance to the node's subject — the content-relevance layer that mechanical checks cannot evaluate. Run after Phase I rebuilds, after 5+ incremental quote additions, or periodically across built nodes. Especially relevant on PA-spokesperson institutional-actor nodes. |
| `web-claude-investigator.md` | Brief for Claude Web acting as investigator — find primary sources for a target, produce a handoff stub for Claude CLI to build from |
| `web-claude-node-audit.md` | Audit an existing node against a Claude Web report — verifies Web's findings against repo schema and conventions before applying any changes |
| `verify-transcript.md` | Verify transcript quotes verbatim against archived source |
| `archive-sweep.md` | Archival health check + Wayback submission pass |

Prompts assume the agent has read `README.md`, `meta/conventions.md`,
and `meta/schema.yaml` at session start (the `onboard.md` prompt
handles this).
