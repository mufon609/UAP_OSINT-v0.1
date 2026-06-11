# Handoff-stub schemas

One stub per role. Each role reads only its own. A stub is a role's **return
value** — the final message it returns to the orchestrator (you write no file
for it). Every example value is a placeholder — keep this file topic-neutral.

**Advisory notes.** Every stub MAY end with an optional `notes:` block — free
prose recording what the emitting role *saw, did, and judged*: source facts,
anomalies encountered, edge cases resolved and why. It is **non-normative**
(subordinate to every contract; it creates no obligation for any role) and it
must **never** contain instructions or policy for another role — that is
relay-rule-2 policy injection by proxy, since a role weights its just-issued
prompt above its standing contract. Notes travel with the stub only when the
**whole stub is the relayed unit** (a worker fragment handed to the builder);
they are never extracted into another step's named-field `Pass:` set — a
survey stub's notes inform the orchestrator's own gate decisions and stop
there.

```yaml
# internal-investigator — returned stub
agent: internal-investigator
slug: {slug}
target: {type}/{slug}
linked_nodes: [/{type}/{related-a}, /{type}/{related-b}]   # the context downstream roles judge relevance against
reusable_sources:
  - path: {category}/{file}.pdf
    covers: ["{claim-group label}"]
    extraction_type: text-native   # text-native | ocr-scan | extraction-lossy (from manifest)
    # No scratch path here: survey extracts are this role's own reading aids
    # (corrupt for ocr-scan sources). The canonical worker scratches come from
    # the orchestrator's step-4b `extract-source.py --artifact` run and are
    # relayed to workers at step 5 — never through this stub.
    # ocr-scan / extraction-lossy → the artifact's primary_sources entry also carries
    # `content_block`, stamped mechanically by ocr-consensus.py --stamp-artifact at
    # sibling prep (/prepare-ocr-sibling step 5). Renders as a `Content Block` row.
topic_relevance: "<one line: how the subject connects to the topic via linked_nodes>"
gaps: ["{what the record is missing}"]
blocking_prep: []              # source-prep prerequisites the orchestrator must clear before the Worker
                               # (NOT gaps, NOT Worker tasks). e.g. an ocr-scan reused source whose
                               # verified .txt sibling does not yet exist -> /build step 4b must produce it.
all_internal: false            # true => orchestrator skips external + archive (NOT source-prep / 4b)
validator_findings: []
notes: |                       # optional, non-normative — "Advisory notes" above
```

```yaml
# external-investigator — returned stub
agent: external-investigator
slug: {slug}
consumed_gaps: ["{gap this fills}"]
queued_sources:                # may be empty — an exhausted record is a valid result
  - url: https://{host}/.../{document}.pdf
    suggested_path: {category}/{file}.pdf
    format: pdf
    tier: primary              # primary | secondary-lead-only
    confirming_span: "<a verbatim excerpt copied from the fetched body>"   # REQUIRED — proves the read; the next role re-checks it against disk
    span_location: "<page / paragraph / timestamp anchor of the span>"
    rationale: <one line: why load-bearing, judged against linked_nodes>
unfilled_gaps: []
validator_findings: []
notes: |                       # optional, non-normative — "Advisory notes" above
```
A queued source with no `confirming_span` is rejected — a bare
"I read it" boolean is not accepted (the read must be re-checkable).

```yaml
# archive — returned stub
agent: archive
slug: {slug}
archived:
  - url: https://{host}/.../{document}.pdf
    path: {category}/{file}.pdf
    status: archived           # or pending + wayback_date
    # No scratch path here: the archive role's extracts serve its own
    # extraction-fidelity flagging. The canonical worker scratches come from
    # the orchestrator's step-4b `extract-source.py --artifact` run and are
    # relayed to workers at step 5 — never through this stub.
primary_sources_registered: [{category}/{file}.pdf]
validator_findings: []         # validate.py --phase archive
notes: |                       # optional, non-normative — "Advisory notes" above
```

```yaml
# worker — returned stub (one per source)
# The worker WRITES its fragment to /tmp/fragments-{slug}/{stem}.yaml
# (shape below) and returns this slim stub. The builder runs
# scripts/build/merge-fragments.py on the fragment files — a byte-exact
# mechanical copy of the verbatim payload, no LLM retyping — then reads
# them for the judgment payload and runs the extract-phase check once.
agent: worker
worker_kind: pdf               # pdf | html | caption | foia
slug: {slug}
source: {category}/{file}.pdf
inputs_consumed: [/tmp/scratch-{slug}-2.txt]
fragment_path: /tmp/fragments-{slug}/{stem}.yaml
counts:                        # what the fragment carries — the orchestrator's sanity surface
  quotes: 0
  cited_works: NONE            # NONE | IGNORED | <entry count>
  cross_ref_candidates: 0
  background_material: 0
  naming_quirks_flagged: 0
validator_findings: []
notes: |                       # optional, non-normative — "Advisory notes" above; rides
                               # with this stub, which is the relayed unit
```

```yaml
# worker — fragment FILE (/tmp/fragments-{slug}/{stem}.yaml, one per source)
# Two payloads, two consumers:
#   verbatim payload (quotes, cited_works) — transported into the artifact by
#     merge-fragments.py, byte-exact, SCHEMA FIELDS ONLY (anything else in the
#     file is mechanically ignored — prose cannot ride the transport);
#   judgment payload (claim_groups_proposed, cross_ref_candidates,
#     background_material, naming_quirks_flagged, notes) — Read by the builder,
#     never merged by the script.
slug: {slug}
worker_kind: pdf
source: {category}/{file}.pdf
quotes:                        # verbatim spans BY the subject; legitimately [] for an about-the-subject / institutional source
  - text: "<verbatim span copied from scratch, never typed from memory>"
    location: "<source-shape anchor>"
    # optional: significance, context, claim_group, statement_date,
    #           observation_type, category — copied through when present
claim_groups_proposed: ["{claim-group label}"]
cross_ref_candidates:
  - entity: /{type}/{related}
    kind: relationship
    span: "<location anchor>"
background_material:           # the quotes: [] case — facts ABOUT the subject for the builder's prose
  - fact: "{fact}"
    source_phrasing: "<exact words from source — prose-drift grounding>"
    location: "<location anchor>"
naming_quirks_flagged:
  - observed: "<source form>"
    canonical: "<source-attested form, or null when unresolvable>"
    note: "<grounding>"
# cited_works (DOCUMENT sources only — the three-state cited_works
# affirmation; omit entirely for non-document sources). Pick exactly ONE
# of three shapes; bare [] is REJECTED (merge-fragments.py enforces, and a
# cross-fragment shape mismatch exits with cited_works_shape_conflict).
#
# Shape A — source has no reference list (EOs, news items, hearing
# transcripts, short docs):
cited_works: NONE
# Shape B — source HAS a reference list, deliberately not captured
# (rare low-value release valve, observable on the rendered node):
cited_works: IGNORED
# Shape C — source carries a reference list and it is captured below.
# Each entry is a distinct extract-phase dimension PARALLEL to quotes[]
# (never a quotes[] entry), source form preserved sic:
cited_works:
  - citation_key: "<bare in-source marker, e.g. 1 for [1] / ^1 / 1.>"
    author: "<author / originating body, source form preserved (sic)>"
    citation_verbatim: "<full reference line copied verbatim from scratch, incl. its [N] marker + OCR sic>"
    location: "<source-shape anchor, e.g. p. N, References>"   # optional: year, title
notes: |                       # optional, non-normative — "Advisory notes" above
```

```yaml
# builder — returned stub
agent: builder
slug: {slug}
node: {type}/{slug}.md
inputs_consumed:
  worker_fragments: [<each worker's returned stub>]
  linked_nodes: [/{type}/{related-a}]   # REQUIRED — relevance is judged against this, not the source alone
claim_groups: [{label: "{claim-group label}", primaries: [q1], pointers: [q2], n_sources: 2}]
tested_before_build: true      # organize + link were clean before render
result: pass                   # or fail
routed: []                     # route_failure.py output when result: fail
validator_findings: []
notes: |                       # optional, non-normative — "Advisory notes" above
```

```yaml
# auditor — returned stub
agent: auditor
slug: {slug}
node: {type}/{slug}.md
health: pass
validator_findings: []
notes: |                       # optional, non-normative — "Advisory notes" above
```
