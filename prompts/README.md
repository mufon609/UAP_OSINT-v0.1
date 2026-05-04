# Prompts

Paste-ready session prompts for common workflows. Not loaded automatically —
copy the relevant prompt into a fresh Claude Code session.

| File | Use for |
|---|---|
| `onboard.md` | First-time session or any fresh session start |
| `build.md` | Build a new node (Phase I → II → III) |
| `audit.md` | Audit an existing node for evidentiary integrity (includes the audit-correction pattern for applying changes to an existing artifact) |
| `Web-Claude-Node_Audit.md` | Audit an existing node against a Claude Web report — verifies Web's findings against repo schema and conventions before applying any changes |
| `verify-transcript.md` | Verify transcript quotes verbatim against archived source |
| `archive-sweep.md` | Archival health check + Wayback submission pass |

Prompts assume the agent has read `README.md`, `meta/conventions.md`,
and `meta/schema.yaml` at session start (the `onboard.md` prompt
handles this).
