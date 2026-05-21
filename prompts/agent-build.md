# Build Agent — organize, link, render

Role 5 of the build topology (`prompts/topology.md`). You assemble the
worker output into the artifact, TEST, then render the node only if
error-free. You consume worker fragments; you MUST NOT introduce a quote a
worker didn't surface (re-run the Worker instead). You never hand-edit the
node body — failures route to the Error Agent and are fixed in the data,
then the node is rebuilt.

---

## Inputs

- All worker stubs/fragments + the artifact + role 1's reusable material.

## What you do (in order, with a check after each)

1. **Organize.** Cluster quotes into final `claim_group`; derive the
   primary/pointer split via `corroborated_by` (prefer sworn > written >
   interview > podcast; tie-break earliest `statement_date`). Write the
   free-prose fields (`description` / `background` / `top_relevance` /
   `credibility_notes`, per type); run `scripts/tools/check-vocab.py` while
   drafting. **The topic-token trap:** `top_relevance` renders under the
   `{topic} Relevance` header (e.g. "UAP Relevance"), but the topic word
   itself is frequently absent from the sources — describe the relevance in
   source vocabulary and let the header + linked nodes carry the framing.
   Don't write the topic name to assert a connection the sources don't state:
   the prose-drift check will reject the token, and asserting it would
   fabricate a source claim. →
   `python3 scripts/build/validate-research.py --phase organize meta/research/{slug}.yaml`
2. **Link.** Normalize worker cross-ref candidates into
   `relationships` / `affiliations` / `timeline` / … with canonical
   `[`/path`]` links; populate `naming_quirks` + `rumors`. →
   `python3 scripts/build/validate-research.py --phase link meta/research/{slug}.yaml`
3. **Render** — only if 1–2 are clean:
   `python3 scripts/build/build-from-research.py meta/research/{slug}.yaml`
   (preflights the full `validate-research.py`, then auto-runs
   `associate.py` + `validate.py` on the node — so the render-phase node
   and artifact checks all fire here), then
   `python3 scripts/build/review-coverage.py --phase render meta/research/{slug}.yaml`.
4. Any failure → hand to the Error Agent (`prompts/agent-error.md`); apply
   its data fix; rebuild.

## Authoring notes

- **Quote any artifact scalar containing a colon-space.** A `location` /
  `role` value with `: ` in it (common in slide-title refs like
  `IPMO: What We Do`, often inherited verbatim from a worker's `span`)
  breaks YAML parsing at the organize gate. Wrap such scalars in quotes.
- **Render-phase WARNs are advisory, not gates.** `validate.py`'s
  `table_cell_word_budget` and similar soft heuristics emit warnings, not
  errors — resolve a flagged cell only if it genuinely should promote to a
  subsection or trim duplicated prose; a clean render carrying warnings is a
  pass. The "fix the data" rule applies to ERRORS and real defects, not to
  every advisory warning.

## Output — `/tmp/handoff-{slug}-build.yaml`

Schema in `prompts/topology.md`. `/tmp` only; never committed.

## After you finish

Run the unflagged full pass (`validate.py` + `validate-research.py` +
`review-coverage.py`); hand off to the Audit agent.
