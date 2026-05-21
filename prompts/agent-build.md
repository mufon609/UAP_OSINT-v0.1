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
   fabricate a source claim. **Document `description` provenance trap:** a
   document's `description` is prose-drift-checked against the source *body*,
   which never describes its own publication date / outlet / paywall — so
   keep that provenance in the structured Document Summary fields
   (`document_intrinsic.internal_date`, `context_extrinsic.primary_source_url`,
   the manifest note) and describe the document's *content* in source
   vocabulary; don't fight the drift check to cram provenance into the prose. →
   `python3 scripts/build/validate-research.py --phase organize meta/research/{slug}.yaml`
2. **Link.** Normalize worker cross-ref candidates into
   `relationships` / `affiliations` / `timeline` / … with canonical
   `[`/path`]` links; populate `naming_quirks` + `rumors`. Keep each
   entry's optional `.note` to context the row's own columns and the node's
   other sections (Timeline / Key Passages / Description) don't already
   carry — never restate Role / Period / Source or repeat a Timeline fact;
   an empty note is correct when there's no residue (see `meta/conventions.md`
   "Per-entry notes"). The prose-drift check verifies a note is *sourced*,
   not that it's *non-redundant* — that judgment is yours. →
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
- **Single-quote any artifact scalar containing an apostrophe.** In YAML an
  apostrophe is escaped as `''` only *inside* a single-quoted scalar. Writing
  `''` in an UNQUOTED scalar (`context: …Knapp''s…`) — or over-escaping to
  `''''` inside a single-quoted one — parses cleanly but renders the `''`
  literally into the node, and these label/attribution/note cells aren't
  verbatim- or drift-checked, so a mistake ships silently. Either
  single-quote the scalar and escape as `''`, or leave it unquoted with a
  single `'`.
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
