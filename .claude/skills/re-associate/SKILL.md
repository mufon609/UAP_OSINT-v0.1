---
name: re-associate
description: Sweep ONE already-built node's link layer to the "ingest is the relevance decision" rule — re-read its primary source(s), populate `associated_entities` with the COMPLETE set of every load-bearing entity the source names, and re-render so every source-named entity reaches `## Associated Nodes`. Changes nothing else (no quotes, no facts, no prose). Use to bring a pre-rule node up to standard, or to keep a fresh ingest honest.
argument-hint: {type}/{slug}  (or meta/research/{slug}.yaml)
allowed-tools:
  - Agent(re-associate-producer, re-associate-verifier)
  - Read
  - Grep
  - Glob
  - Edit
  - Bash(python3 scripts/build/extract-source.py *)
  - Bash(python3 scripts/build/build-from-research.py *)
  - Bash(python3 scripts/build/validate.py *)
  - Bash(python3 scripts/build/validate-research.py *)
  - Bash(python3 scripts/build/review-coverage.py *)
  - Bash(python3 scripts/build/associate.py *)
  - Bash(python3 scripts/build/build-state.py *)
  - Bash(python3 scripts/tools/coverage-suggest.py *)
---

# Re-associate a node's link layer

Target: **$ARGUMENTS** (a `{type}/{slug}` node or its `meta/research/{slug}.yaml`
artifact; ask the user if empty). You are the orchestrator on the main thread.
This is the **link-layer-only** maintenance pass: you bring the node's
`associated_entities` field — and therefore its `## Associated Nodes` section —
up to the build-protocol **"Linking — ingest is the relevance decision"**
contract, where EVERY load-bearing entity the source names is linked, with no
"node-worthy / topically relevant" filter.

**The narrow guarantee.** You change ONLY the link layer: the artifact's
`associated_entities` field (and, optionally, an inline `[`/path`]` wrap added
around an entity the `description` already *names* but doesn't wrap — prose-drift
safe, the wrap is stripped before tokenizing). You introduce **no** quotes, **no**
facts, **no** prose rewording, and you **never** hand-edit the node body (it
regenerates from the artifact; a body edit is hook-blocked). The verbatim and
prose-drift gates must read clean before and after — the diff is the field plus
the derived `## Associated Nodes` section, nothing else.

## 1. Resolve target + confirm a green baseline

Resolve the artifact (`meta/research/{slug}.yaml`) and node from `$ARGUMENTS`.
Confirm the node already builds clean — a failing baseline confounds a
link-only pass:

```
python3 scripts/build/validate-research.py meta/research/{slug}.yaml
python3 scripts/build/build-from-research.py meta/research/{slug}.yaml
python3 scripts/build/review-coverage.py --all
```

If red, stop and report — this skill maintains a healthy node, it does not repair
one (use `/audit` or `/augment`).

## 2. Extract the source(s) — source-read-first

```
python3 scripts/build/extract-source.py --artifact meta/research/{slug}.yaml
```

Note the scratch path(s). For an `ocr-scan` / `extraction-lossy` source, the
canonical text is its verified `.txt` sibling — `--artifact` already prefers it;
if the source carries no verified sibling, **HALT** and direct the user to
`/prepare-ocr-sibling` first (you cannot enumerate entities from a corrupt
extract).

## 3. Produce → independently verify the complete entity set

Dispatch the two role agents (separate sessions — the independence is the
completeness guarantee a self-checking single read cannot give):

1. `Agent(re-associate-producer)` — relay the artifact path, the scratch
   path(s), and the current `associated_entities` (if any). It returns the
   proposed COMPLETE `associated_entities` list (deduped, grouped, with a
   source-phrase note per non-obvious entry) plus its judgment calls.
2. `Agent(re-associate-verifier)` — relay the artifact path, the scratch
   path(s), and the producer's proposed list. It returns `PASS`, or `REJECT`
   with an ADD / REMOVE / slug-FIX correction list.

On `REJECT`: if the corrections are **purely mechanical** — slug FIXes only, no
ADD / REMOVE and no judgment call the verifier flags for the user — apply them
yourself directly (the verifier already named the exact fix; a producer
round-trip for a deterministic one-token slug change is wasted spawns across a
corpus sweep). If the corrections include an **ADD / REMOVE or a judgment call**,
re-dispatch the producer with the verifier's correction list verbatim, then
re-verify. Loop until `PASS` (or a genuinely ambiguous case the verifier flags
for the user). `coverage-suggest.py meta/research/{slug}.yaml` (capitalized-terms
output) is an extra mechanical net you may consult to double-check completeness —
judge each (boilerplate / generic terms are noise).

## 4. Report before applying

Present, before changing anything (mirrors `/audit` and `/quote-relevance-audit`):
the reconciled `associated_entities` list as a diff against the current state
(entities ADDED, any REMOVED, any slug changed), with the source phrase backing
each addition, and any ambiguous calls for the user to adjudicate. Do not
auto-apply.

## 5. Apply + re-render

On approval:

1. **Edit the artifact** — write the complete `associated_entities` list (sorted
   within type for human scanning; `associate.py` sorts the rendered output
   regardless). Use the `Edit` tool surgically — do not reflow the file. If the
   `description` *names* an entity it doesn't wrap, optionally add the inline
   `Name ([`/people/slug`])` wrap (source token left verbatim).
2. **Re-render** — `python3 scripts/build/build-from-research.py
   meta/research/{slug}.yaml` (regenerates the body, runs `associate.py` to fold
   `associated_entities` ∪ body-wraps into `## Associated Nodes`, then
   `validate.py` + the `associated_entities` shape/superset check).
3. `python3 scripts/build/review-coverage.py --all` clean.
4. Confirm `## Associated Nodes` now lists the full set, and that nothing else in
   the body changed (the diff is the field + that section only). If the node's
   status or type changed (it won't, for a link-only pass), refresh
   `build-state.py --update`.

The user commits — the full pre-commit chain runs at the commit boundary,
un-bypassable. In a **multi-node sweep**, commit each node's result **before**
dispatching the next node's agents (an agent's effective Bash can `git restore`
uncommitted work).

## Scope notes

- **References stay alone.** Do not explode the `cited_works` / `## References`
  list into per-citation links — only a cited author/work the narrative
  *discusses* becomes an entity (the producer/verifier enforce this carve-out).
- **Redacted / externally-attested author + attributed institution** — the
  author and the institution named in `context_extrinsic.extrinsic_authorship`
  (carried from the products-list attribution) ARE associated entities and go in
  the field; ingesting the attribution is the relevance decision. There is no
  "redacted author stays out" carve-out.
- This is the corpus-sweep tool for BACKLOG C4 (bring every pre-rule node up to
  standard) and the standing pass for keeping new ingests — including the
  government-document releases — honest from the start. Run it against one node
  at a time.
