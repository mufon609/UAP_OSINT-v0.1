# Prompts

The operational build workflow lives in the toolkit as **skills and
subagents** under `.claude/` — invoke them (e.g. `/build`, `/audit`),
don't paste them. What remains here is the **Claude-Web briefs**
(a separate surface that has no `.claude/` skill). The pipeline map lives in
`.claude/skills/build/SKILL.md` ("The shape"); the shared role contract is
`.claude/skills/build-protocol/`.

| File | Use for |
|---|---|
| `web-claude-investigator.md` | Brief for Claude Web acting as investigator — find primary sources for a target, produce a handoff stub for the CLI build to consume. |
| `web-claude-node-audit.md` | Audit an existing node against a Claude Web report before applying any changes. |
