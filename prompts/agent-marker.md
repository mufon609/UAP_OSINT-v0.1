# Marker agent — per-source quote extraction

Paste into a fresh subagent, one invocation **per archived source**. The
Marker is stage 3 of the five-agent build pipeline (Scout → **Marker** →
Manager → Meta-linker → Builder; see `prompts/build.md` "The multi-agent
pipeline (A2)"). It is the extended form of bounded task **T2**.

You read **one** primary source and emit verbatim quote candidates. You
do NOT cluster across sources, write prose, or build the node — later
agents do that. Your output is consumed by the Manager.

---

## Inputs

- `{slug}` — the target node slug (e.g. `david-grusch`).
- `{source-path}` — the source's manifest path (e.g.
  `government/oversight-house-gov-grusch-written-testimony-20230726.pdf`).
- The extracted plaintext at `/tmp/scratch-{slug}-N.txt` for that source
  (produced by the Scout via `scripts/build/extract-source.py`). If it is
  not present, extract it first:
  `python3 scripts/build/extract-source.py --artifact meta/research/{slug}.yaml`.

## Source-read-first — hard rule

Every candidate's `text` is **copy-pasted verbatim** from the scratch
file — not typed from memory, not rephrased, not composited. Multi-line
quotes preserve original line breaks (YAML literal block `|`). Preserve
source artifacts exactly (HTML entities, OCR damage, auto-caption typos);
log oddities for the Meta-linker's `naming_quirks`, never "correct" them
in the quote. Paragraph / page / timestamp anchors are counted from the
scratch file, not from memory. If a claim isn't in the scratch text, it
does not belong in your output.

## Output 1 — a `quotes:` YAML fragment

One entry per load-bearing passage, each with the T2 fields:

- `id` (local to this source's batch — the Manager renumbers on merge)
- `text` (verbatim literal block)
- `source`: `{path: {source-path}, location: …}` (e.g. `"p. 12, ¶3"`,
  `"[14:22]"`, `"¶4"` — anchored to the source's own structure, per
  `meta/conventions.md` "Quote location refs")
- `significance` — one line on why it matters
- `context` — venue / circumstance (required on person artifacts)
- `observation_type` — `direct` | `relayed` (required on person artifacts)
- `statement_date` (when the source attests one)
- `speaker_id` (required on transcript artifacts)
- **`claim_group`** — your **proposed** short topic label for what this
  statement is *about* (e.g. `"Crash-Retrieval Program"`). This is
  ADVISORY: you have read only this one source, so you cannot see that
  another source says the same thing. The Manager normalizes labels
  across sources and owns the final grouping. Propose a clear, consistent
  label; reuse the same string for candidates about the same claim within
  this source.

Only extract distinctive evidentiary passages — skip procedural
scaffolding. On person artifacts apply the speaker-attribution rule
(quotes BY the subject, not ABOUT — see `prompts/build.md` Step 6).

## Output 2 — the handoff stub

Write `/tmp/handoff-{slug}-marker-{N}.yaml` (N = the source index):

```yaml
agent: marker
slug: {slug}
source: {source-path}
inputs_consumed: [/tmp/scratch-{slug}-N.txt]
outputs_produced:
  candidates: <count>
  claim_groups_proposed: [<label>, …]
validator_findings: []   # filled by: validate-research.py --phase marker
```

The stub is a debugging surface, not load-bearing data — `/tmp` only,
never committed (the research artifact is the source of truth).

## After you finish

The candidates are verbatim-checked by
`validate-research.py --phase marker` once merged. Do not introduce a
quote that isn't in the scratch text — that is the one invariant the
whole pipeline rests on (the verbatim-quote check fires here).
