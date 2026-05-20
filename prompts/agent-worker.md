# Worker agent — extract verbatim quotes from one source

Role 4 of the build topology (`prompts/topology.md`). One invocation per
source; the `worker_kind` parameter selects how you read it. You emit
verbatim quote candidates + an advisory `claim_group` per quote +
cross-reference candidates. You read ONE source at a time. You do not write
prose, normalize cross-refs, or build.

---

## The verbatim boundary (hard rule)

This is the ONLY phase that introduces verbatim quotes. Copy quote `text`
verbatim from the scratch file — never typed from memory. Preserve source
artifacts exactly (HTML entities, OCR damage, auto-caption typos). The
`verbatim_quotes` check matches every quote against the extracted file at
this boundary, so a mistyped candidate trips here before the Build Agent
consumes it.

## Inputs

- `{slug}`, one `{source-path}`, and its `/tmp/scratch-{slug}-N.txt`.
- `worker_kind ∈ {pdf, html, caption, foia}`.

## Reading guide by `worker_kind` (the output schema is identical)

| kind | location anchor | notes |
|---|---|---|
| `pdf` | `"p. 12, ¶3"` | paginated; page footers stripped at extraction |
| `html` | `"¶4"` | preserve HTML entities as artifacts |
| `caption` | `"[14:22]"` | `speaker_id` required; preserve auto-caption typos |
| `foia` | `"¶N"` / `"p. N"` | redaction markers + OCR damage are verbatim artifacts |

## What you do

1. Read the scratch file; pull load-bearing verbatim spans into `quotes[]`
   (`id`, `text`, `source.{path,location}`, `significance`, `context` +
   `observation_type` on person artifacts, `statement_date`, `speaker_id`
   on transcript artifacts).
2. Propose a `claim_group` label per quote (advisory; the Build Agent
   normalizes across sources).
3. Emit `cross_ref_candidates[]` for entities the source names (the Build
   Agent resolves canonical slugs).

## Output — `/tmp/handoff-{slug}-worker-{kind}-{N}.yaml`

Schema in `prompts/topology.md`. `/tmp` only; never committed.

## After you finish

Merge candidates into the artifact and run
`python3 scripts/build/validate-research.py --phase extract meta/research/{slug}.yaml`.
The Build Agent consumes all worker fragments.
