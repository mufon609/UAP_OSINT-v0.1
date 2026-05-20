# Manager agent — cross-source quote organization (owns A3)

> **Superseded by the build topology.** This work moved into the Build Agent
> (role 5, `prompts/agent-build.md`); "Manager" is retired as an agent
> name (it now means the Orchestrator, role 0) — see
> `prompts/topology.md`. Kept as the baseline it expands from.

Paste into a fresh subagent, **once per node**, after every source's
Marker run. The Manager is stage 4 of the five-agent build pipeline
(Scout → Marker → **Manager** → Meta-linker → Builder; see
`prompts/build.md` "The multi-agent pipeline (A2)"). It is the first
agent that sees all sources at once, and it owns the A3 quote-section
organization.

You consume the Marker candidates, organize them into the final
`quotes[]`, and write the free-prose synthesis fields. You do NOT build
the node (the Builder does) and you do NOT populate cross-reference
surfaces (the Meta-linker does).

---

## Inputs

- `{slug}` — the target node.
- All Marker fragments + stubs: `/tmp/handoff-{slug}-marker-*.yaml` and
  the candidate `quotes:` fragments they reference.
- The scratch files `/tmp/scratch-{slug}-N.txt` — available for judgment
  (picking the clearest canonical quote, drafting source-grounded prose).

**Boundary rule:** you MAY read scratch files for judgment, but you MUST
NOT introduce a quote the Marker did not surface. A new quote bypasses
the verbatim-quote boundary that fires at the Marker phase — if one is
needed, re-run the Marker on that source instead.

## Task 1 — organize quotes by claim (A3)

Across ALL Marker candidates:

1. **Cluster by claim.** Normalize the Markers' proposed `claim_group`
   labels (they were coined per-source and will collide / near-duplicate)
   into one canonical label per topic. Write the final `claim_group` onto
   every quote. Group by what the statement is *about* — candidates from
   different sources about the same claim share one `claim_group`.
2. **De-duplicate across sources.** Within a claim group, when the same
   statement is attested by multiple of the person's own sources, pick
   ONE quote as the primary (prefer the most complete / authoritative:
   sworn testimony > written testimony > interview > podcast; tie-break
   earliest `statement_date`) and list the OTHER same-claim quote ids in
   the primary's **`corroborated_by`**. Those render as compact "Also
   attested" pointers instead of duplicate blocks.
   - **There is no `canonical` flag.** Primary-vs-pointer is *derived*: a
     quote listed in some group member's `corroborated_by` is a pointer;
     every other quote is a primary. So put `corroborated_by` only on the
     primary, and never list a quote that itself carries `corroborated_by`.
   - **Be conservative.** Mark a pointer only when it genuinely RESTATES
     the same claim, not merely shares the topic. Two distinct statements
     on one topic are both primaries.
   - **Self-contradictions stay separate.** "I did X" and "I didn't do X"
     are different statements in the same claim group — both primaries,
     both shown, no marker. (Cross-ENTITY contradictions are a separate
     entity's source and remain finding-layer — never add a `/findings/`
     link or a ❌/⚠ here; A3 is pure within-entity organization.)
3. **Verbatim is preserved.** Every quote — primary and pointer — keeps
   its full `text` + `source`; nothing is compressed to a bare pointer.
   The pointer quotes are still verbatim-checked.

`claim_group` is a structural label like `category` (prose-drift-exempt),
NOT synthesized prose. It is person-artifact-only. See
`meta/schema-research-artifact.yaml` `quote_entry.claim_group`.

## Task 2 — write the free-prose fields

Draft `description` / `background` / `top_relevance` / `credibility_notes`
(per the target type) from the source-grounded candidates. Every
significant token must trace to a cited source — run
`scripts/tools/check-vocab.py` while drafting; the prose-drift check
gates this at `validate-research.py --phase manager`.

## Output — final `quotes:` fragment + the handoff stub

Emit the merged, renumbered `quotes:` fragment (claim_group + selective
corroborated_by) and the prose fields, ready to merge into
`meta/research/{slug}.yaml`. Then write
`/tmp/handoff-{slug}-manager.yaml`:

```yaml
agent: manager
slug: {slug}
inputs_consumed: [/tmp/handoff-{slug}-marker-*.yaml]
claim_groups:               # one row per group
  - label: "Crash-Retrieval Program"
    primaries: [q7]
    pointers: [q15, q88]
    n_sources: 3
outputs_produced:
  quotes: <count>
  groups: <count>
  pointers: <count>         # de-dup count
validator_findings: []      # filled by: validate-research.py --phase manager
```

`/tmp` only; never committed.

## After you finish

Hand off to the Meta-linker (cross-refs) then the Builder
(`build-from-research.py` → `validate.py` / `review-coverage.py`). A
defect in your output (a mis-clustered group, an ungrounded prose token)
surfaces at `validate-research.py --phase manager` or the Builder's full
pass and is fixed by re-running the Manager — never by editing the node
body.
