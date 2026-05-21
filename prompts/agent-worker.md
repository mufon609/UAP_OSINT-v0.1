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

## Whose voice does the source record? — the quote-attribution gate

Verbatim is necessary but **not sufficient**. `quotes[]` carries only the
statements the artifact's SUBJECT is responsible for. A verbatim span by the
wrong speaker is a defect the `verbatim_quotes` check **cannot catch** — it
verifies the bytes are in the source, not who said them — so it passes green
and the contamination only surfaces downstream at audit. Apply this gate
before emitting any quote:

- **Person artifacts** — `quotes[]` = statements **BY the subject**, never
  ABOUT them. In a multi-speaker source (a panel, an interview, an article
  quoting several people), extract only the subject's lines; every other
  speaker's quote is a `cross_ref_candidate`, not a Statement. A document the
  subject **authored or signed** counts as their voice (the signer's prose
  IS a BY-statement). A biography, news narration, or institutional document
  **about** the subject yields **zero** `quotes[]` — `quotes: []` is the
  correct, expected output for such a source; route its content to
  `background_material[]` + `cross_ref_candidates[]`. See `meta/conventions.md`
  "Statements speaker-attribution — quotes BY the person, not ABOUT".
- **A reporting-verb paraphrase is not a quote.** "Holly emphasized that…"
  (a narrator's verb, no quotation marks) is not a verbatim utterance — don't
  lift it into `quotes[]` even though copy-pasting it would pass the byte
  check. Capture the fact as a `cross_ref_candidate` instead.
- **Transcript artifacts** carry every speaker, each tagged with `speaker_id`
  — the multi-speaker exclusion above does NOT apply to transcripts.

## Inputs

- `{slug}`, one `{source-path}`, and its `/tmp/scratch-{slug}-N.txt`.
- `worker_kind ∈ {pdf, html, caption, foia}`.

## Reading guide by `worker_kind` (the output schema is identical)

The location form follows the **source's shape, not the file extension** —
`meta/conventions.md` "Quote location refs" carries the authoritative
source-shape table. Common cases + the edges that bite:

| kind | typical anchor | watch for |
|---|---|---|
| `pdf` | `"p. N, ¶M"` (paginated) | a **single-page memo** is unpaginated → `¶N`; page footers stripped at extraction |
| `html` | `"¶N"` | when extraction collapses paragraphs into one large block, a bare `¶N` is uncountable — use the `¶ <leading phrase>` anchor (ctrl-F-able); preserve HTML entities |
| `caption` | `"[MM:SS]"` | `speaker_id` required; preserve auto-caption typos |
| `foia` | `"¶N"` / `"p. N"` / `"Doc N"` | redaction markers + OCR damage are verbatim artifacts |

A load-bearing fact that lives only in **extracted metadata** (e.g. a PDF
Author byline that `extract-source.py` surfaces into the manifest note, not
the body text) is not a body quote — emit it as a `cross_ref_candidate`
whose `span` names the metadata field (`PDF metadata (Author field)`), never
as a `quotes[]` entry.

## What you do

1. Read the scratch file; pull the subject's load-bearing verbatim spans
   (per the voice gate above) into `quotes[]` (`id`, `text`,
   `source.{path,location}`, `significance`, `context` + `observation_type`
   on person artifacts — `direct` | `relayed` per
   `schema-research-artifact.yaml::quote_entry`: `direct` = first-hand
   sensory observation, `relayed` = anything else — `statement_date`,
   `speaker_id` on transcript artifacts). For an about-the-subject or
   institutional source, `quotes[]` is legitimately **empty**.
2. Propose a `claim_group` label per quote (advisory; the Build Agent
   normalizes across sources).
3. Emit `cross_ref_candidates[]` for entities the source names (the Build
   Agent resolves canonical slugs). For an about-the-subject source, also
   emit `background_material[]` — the load-bearing biographical /
   institutional facts with their **exact source phrasing** + location
   anchor — so the Build Agent can write source-grounded prose (the
   prose-drift check tokenizes against this vocabulary) without re-reading
   the source.

## Output — `/tmp/handoff-{slug}-worker-{kind}-{N}.yaml`

Schema in `prompts/topology.md`. `/tmp` only; never committed.

## After you finish

Merge candidates into the artifact and run
`python3 scripts/build/validate-research.py --phase extract meta/research/{slug}.yaml`.
The Build Agent consumes all worker fragments.
