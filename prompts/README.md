# Prompts

The operational build workflow now lives in the toolkit as **skills and
subagents** under `.claude/` — invoke them (e.g. `/build`, `/onboard`,
`/audit`), don't paste them. What remains here is the **design rationale** and
the **Claude-Web briefs** (a separate surface that has no `.claude/` skill).

| File | Use for |
|---|---|
| `topology.md` | Design rationale for the multi-agent build — why the roles are cut where they are, the phase vocabulary, the branches, the dissolved roles. The live system is the `/build` skill + `.claude/agents/`. |
| `web-claude-investigator.md` | Brief for Claude Web acting as investigator — find primary sources for a target, produce a handoff stub for the CLI build to consume. |
| `web-claude-node-audit.md` | Audit an existing node against a Claude Web report before applying any changes. |

The shared contract the role subagents preload is `.claude/skills/build-protocol/`.
