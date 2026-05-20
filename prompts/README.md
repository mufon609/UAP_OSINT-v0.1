# Prompts

Paste-ready session prompts for common workflows. Not loaded automatically —
copy the relevant prompt into a fresh Claude Code session.

| File | Use for |
|---|---|
| `onboard.md` | First-time session or any fresh session start |
| `fork-init.md` | Bootstrap the toolkit for a different topic (run once on a fresh fork) |
| `build.md` | Build a new node (Phase I → II → III) |
| `topology.md` | Build topology — the canonical map of roles, `--phase` check bundles, handoff stubs, and orchestration that the agent prompts below share |
| `agent-orchestrator.md` | Orchestrator (role 0) — sequence the build, scaffold, pass the handoff stubs; takes the user's scope/target |
| `agent-internal-investigator.md` | Internal Investigator (role 1) — survey in-repo nodes/sources the build can reuse; name the gaps |
| `agent-external-investigator.md` | External Investigator (role 2) — find + read missing load-bearing content; queue exact deep URLs for archiving |
| `agent-archive.md` | Archive (role 3) — archive queued sources (`manifest.py add` + Wayback), extract, register on the artifact |
| `agent-worker.md` | Worker (role 4) — per-source verbatim quote extraction, parameterized by `worker_kind` (pdf / html / caption / foia) |
| `agent-build.md` | Build Agent (role 5) — organize quotes + free-prose + cross-refs, then render; routes failures to the Error Agent, never edits the node body |
| `agent-error.md` | Error Agent (role 5) — triage a validator failure to its owning role; recommend a data fix, never a node-body edit |
| `audit.md` | Audit an existing node for evidentiary integrity (includes the audit-correction pattern); also role 6 of the build topology — the health pass + adjacent-node propagation |
| `quote-relevance-audit.md` | Audit `quotes[]` on an existing artifact for load-bearing relevance to the node's subject — the content-relevance layer that mechanical checks cannot evaluate. Run after Phase I rebuilds, after 5+ incremental quote additions, or periodically across built nodes. Especially relevant on PA-spokesperson institutional-actor nodes. |
| `web-claude-investigator.md` | Brief for Claude Web acting as investigator — find primary sources for a target, produce a handoff stub for Claude CLI to build from |
| `web-claude-node-audit.md` | Audit an existing node against a Claude Web report — verifies Web's findings against repo schema and conventions before applying any changes |
| `verify-transcript.md` | Verify transcript quotes verbatim against archived source |
| `archive-sweep.md` | Archival health check + Wayback submission pass |

Prompts assume the agent has read `README.md`, `meta/conventions.md`,
and `meta/schema.yaml` at session start (the `onboard.md` prompt
handles this).
