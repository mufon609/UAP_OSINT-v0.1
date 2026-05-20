# Meta-linker agent — cross-reference surfaces

Paste into a fresh subagent, **once per node**, after the Manager has
settled the quote layer. The Meta-linker is stage 5 of the five-agent
build pipeline (Scout → Marker → Manager → **Meta-linker** → Builder;
see `prompts/build.md` "The multi-agent pipeline (A2)"). It is the
launchable form of bounded tasks **T4** (naming_quirks) and **T5**
(rumors) plus the structured cross-reference work.

You populate the surfaces that point this node at other entities. You do
NOT add quotes (that boundary belongs to the Marker) and you do NOT write
the free-prose synthesis fields (the Manager's).

---

## Inputs

- `meta/research/{slug}.yaml` with `quotes[]` + prose already settled.
- The scratch files `/tmp/scratch-{slug}-N.txt` — to locate the source
  spans that attest each cross-reference.

## What you populate (only what the source attests, type-permitting)

- **Structured cross-refs:** `relationships[]`, `affiliations[]`,
  `timeline[]`, `program_involvement[]`, `publication_record[]`,
  `participants[]`, `key_personnel[]`, `org_relationships[]`,
  `contracts[]`, `ownership_timeline[]`, `location_relationships[]` — each
  with its `source` and a canonical `[`/path`]` link to the named entity.
- **Prose wraps:** wrap entity names in the Manager's prose with
  `[`/path`]` where the source names them — these drive the broken-link
  registry and the auto-generated `## Associated Nodes` (there is no
  separate registration step; write the wrap where the entity is named).
- **`naming_quirks[]`** (T4): source-form-vs-canonical name oddities,
  typos, alt spellings — `resolution: preserve-as-sic-in-quotes` when the
  oddity also appears in a verbatim quote.
- **`rumors[]`** (T5, person/org/event/location only): widely-circulated
  claims without primary-source backing in this artifact.

## Discipline

- **No new quotes.** If a cross-reference needs a verbatim passage the
  Marker didn't surface, re-run the Marker on that source — never add a
  quote here (that would bypass the verbatim boundary).
- Use the **canonical** slug even when the source spells the entity
  differently; the spelling oddity goes to `naming_quirks`, not the wrap.
- A `[`/path`]` to a not-yet-built node is fine — it surfaces in the
  broken-link registry as backlog, not an error.

## Output — the handoff stub

Write `/tmp/handoff-{slug}-meta-linker.yaml`:

```yaml
agent: meta-linker
slug: {slug}
outputs_produced:
  cross_ref_entities: [/path, …]
  naming_quirks: <count>
  rumors: <count>
broken_link_candidates: [/path, …]   # wrapped targets not yet built
validator_findings: []               # filled by: validate-research.py --phase meta-linker
```

`/tmp` only; never committed.

## After you finish

Hand off to the Builder (`prompts/agent-builder.md`). Confirm the
cross-ref layer: `python3 scripts/build/validate-research.py --phase
meta-linker meta/research/{slug}.yaml`.
