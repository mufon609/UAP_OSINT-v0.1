# Prompts

Paste-ready session prompts for common workflows. Not loaded automatically —
copy the relevant prompt into a fresh Claude Code session.

| File | Use for |
|---|---|
| `onboard.md` | First-time session or any fresh session start |
| `fork-init.md` | Bootstrap the toolkit for a different topic (run once on a fresh fork) |
| `build.md` | Build a new node (Phase I → II → III) |
| `audit.md` | Audit an existing node for evidentiary integrity (includes the audit-correction pattern for applying changes to an existing artifact) |
| `quote-relevance-audit.md` | Audit `quotes[]` on an existing artifact for load-bearing relevance to the node's subject — the content-relevance layer that mechanical checks cannot evaluate. Run after Phase I rebuilds, after 5+ incremental quote additions, or periodically across built nodes. Especially relevant on PA-spokesperson institutional-actor nodes. |
| `web-claude-investigator.md` | Brief for Claude Web acting as investigator — find primary sources for a target, produce a handoff stub for Claude CLI to build from |
| `web-claude-node-audit.md` | Audit an existing node against a Claude Web report — verifies Web's findings against repo schema and conventions before applying any changes |
| `verify-transcript.md` | Verify transcript quotes verbatim against archived source |
| `archive-sweep.md` | Archival health check + Wayback submission pass |

Prompts assume the agent has read `README.md`, `meta/conventions.md`,
and `meta/schema.yaml` at session start (the `onboard.md` prompt
handles this).
