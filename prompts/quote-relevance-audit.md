# Quote-relevance audit prompt

Paste into a Claude Code session to audit `quotes[]` on an existing
research artifact for **load-bearing relevance to the node's subject**
— a complement to `validate.py`'s mechanical verbatim-quote check
(which confirms each quote matches its source) and `validate-research.py`'s
prose-drift check (which confirms each significant token in synthesis
prose appears in source).

This audit is the **content-relevance** check that those two don't cover:
*does each verbatim quote actually advance understanding of the node's
subject, or has the node accumulated quotes whose subject is some other
entity?*

---

## When to run

- After a Phase I rebuild that added many new quotes
- After multiple incremental edits added 5+ quotes
- Periodically across all built nodes (e.g., once per node-cluster ring closes)
- When a reader spot-check surfaces "this quote doesn't seem to be about
  this node's subject"
- Before promoting a node from `in-progress` to `active`

Especially relevant on **PA-spokesperson institutional-actor nodes**,
where the speaker's role is structurally to speak FOR the institution
ABOUT other people / programs / events. See
`feedback_quote_relevance_load_bearing.md`.

---

## Hard rules

1. **Speaker attribution is necessary but not sufficient.** A quote
   correctly attributed to the node's subject CAN still be the wrong
   home if its content is heavily about another entity. The
   audit asks the second question: *what is the quote ABOUT?*

2. **Default to keep when uncertain.** Per `feedback_no_count_targets.md`,
   source drives density. The load-bearing test is contributor judgment,
   not a mechanical check. Drop only when over-extraction is visible
   (multiple long quote blocks about an entity that has its own node
   or stub).

3. **Move detail, don't lose it.** When a quote belongs better on
   another entity's node:
   - If that other entity is built — surface the quote for transfer
     to that artifact (do not silently delete).
   - If that other entity is not yet built — register it in
     `entities_referenced` (with wrap_path) so the Stub-linking check
     surfaces it as a build candidate; capture the institutional moment
     in the speaker's `timeline[]` so the contextual fact is not lost;
     the verbatim quote can be added on the other entity's node when
     that node is built.

---

## Procedure

### Step 1. Run the onboarding steps

If you haven't already this session, paste `prompts/onboard.md`. The
audit assumes you've read `meta/conventions.md`, `meta/schema.yaml`,
and the relevant memory files.

### Step 2. Identify the audit target

Ask the user for the target artifact path
(`meta/research/{slug}.yaml`) if not already specified.

### Step 3. Confirm baseline pre-commit cleanliness

Before opening the load-bearing question, the artifact must already
pass:

```
python3 scripts/validate-research.py meta/research/{slug}.yaml
python3 scripts/build-from-research.py meta/research/{slug}.yaml
python3 scripts/review-coverage.py meta/research/{slug}.yaml
```

A failing baseline means the audit candidates may be confounded by
mechanical defects. Fix the baseline first.

### Step 4. Walk each quote against the load-bearing test

For each entry in `quotes[]`, fill out a per-quote assessment:

| Field | Test |
|---|---|
| `id` | quote identifier |
| `attributed_speaker` | who the source attributes the quote to (should = node's subject for person artifacts) |
| `content_subject` | what entity / topic the quote text is primarily ABOUT |
| `length_bytes` | rough length indicator (text-only, excluding YAML escapes) |
| `unique_evidentiary_signal` | what does this quote uniquely add to understanding the NODE'S subject? |
| `decision` | KEEP / CONSOLIDATE-WITH-{id} / DROP-AND-MOVE / DROP-AND-REPLACE-WITH-TIMELINE / SURFACE-FOR-NODE-{path} |
| `rationale` | one sentence explaining the decision |

### Step 5. Apply the decision matrix

| Speaker | Content subject | Decision | When to apply |
|---|---|---|---|
| node subject | node subject | KEEP | always — this is the canonical case |
| node subject | other entity | KEEP ONE per institutional moment + surface others | when source has multiple quotes about the same other-entity moment (consolidate to the substantive one; surface the rest for the other entity's node) |
| node subject | other entity | DROP, replace with `timeline[]` entry | when quote adds no unique signal beyond what a timeline event would record (short, ceremonial, or repeated PA-pattern statements) |
| node subject | other entity | DROP-AND-MOVE | when the other entity has a built node and the quote belongs there |
| node subject | other entity | KEEP for now, file move-when-built | when the other entity is in the broken-link registry as an unbuilt stub |
| not node subject | anything | NEVER on this node | quote belongs on the actual speaker's node; this is a misattribution to fix |

### Step 6. Multi-quote consolidation rule

When multiple quotes from the same source cover one institutional
moment (a single Q&A statement, a single press conference, a single
email thread, a single hearing exchange), prefer ONE anchoring quote
that captures the moment's substance unless every quote uniquely
contributes a distinct evidentiary signal.

Heuristic: if you can summarize multiple quotes as "the [speaker]
said [topic] in the [date] [event]" without losing meaningful nuance,
they're consolidation candidates.

### Step 7. Report findings BEFORE applying changes

Surface the assessment as a table with all decisions per quote.
**Do not auto-apply drops or moves.** Content decisions need
contributor approval, especially for ambiguous cases. Present:

- The full per-quote assessment table
- A summary count: how many KEEP / CONSOLIDATE / DROP-AND-MOVE / etc.
- Specific recommended changes with concrete edits
- Any cases where the speaker-vs-content-subject distinction is
  genuinely ambiguous (so the user can adjudicate)

### Step 8. Apply approved changes

Once contributor approves the recommendation set:

1. Edit the artifact (drop selected quotes, update `timeline[]` if
   needed, update `entities_referenced` if surfacing for a future node).
2. If consolidating, update `significance` / `context` on the
   surviving quote to capture what was in the dropped siblings.
3. Re-render: `python3 scripts/build-from-research.py meta/research/{slug}.yaml`
4. Re-run Phase III: `python3 scripts/review-coverage.py meta/research/{slug}.yaml`
5. Verify the rendered Statements section reads cleanly — the
   subject-as-protagonist test should pass at a glance.
6. Pre-commit chain: `bash scripts/tests/pre-commit.sh`

### Step 9. Surface broader patterns

If the audit pass identifies the same shape of over-extraction across
multiple nodes (e.g., "every PA-spokesperson node carries Q&A blocks
about other people"), surface the pattern as a candidate for a
broader convention or BACKLOG entry.

---

## What this audit does NOT cover

- **Verbatim accuracy** — `validate.py` already mechanically verifies
  every quote's text matches the source byte-for-byte (after
  normalize-for-compare).
- **Prose-drift in synthesis fields** — `validate-research.py` covers
  this on scoped fields.
- **Stub-linking / coverage / boundary / description-drift** —
  `review-coverage.py` covers all four.
- **Source archival integrity** — `manifest_checksums` check + the
  general `audit.md` prompt cover this.

This audit is exclusively the **content-relevance** layer that
mechanical checks cannot evaluate.

---

## Related memories and prompts

- `feedback_quote_relevance_load_bearing.md` — the durable policy this
  prompt operationalizes
- `feedback_no_count_targets.md` — source drives density (no quantitative
  target — but also no over-extraction)
- `feedback_source_priority_hierarchy.md` — subject's own words rank
  highest when sources disagree (related but distinct: this prompt
  asks WHICH SUBJECT the quote serves)
- `feedback_audit_methodology.md` — multi-issue audits split into
  phases; this audit is a Phase 2 (completeness / quality)
  shape, not Phase 1 (factual correctness)
- `prompts/audit.md` — general node-audit prompt; this prompt is a
  more specialized lens
