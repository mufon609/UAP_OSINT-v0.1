# Handoff-stub schemas

One stub per role. Each role reads only its own. A stub is a role's **return
value** — the final message it returns to the orchestrator (no file is
written). Every example value is a placeholder — keep this file topic-neutral.

```yaml
# internal-investigator — returned stub
agent: internal-investigator
slug: {slug}
target: {type}/{slug}
linked_nodes: [/{type}/{related-a}, /{type}/{related-b}]   # the context downstream roles judge relevance against
reusable_sources:
  - path: {category}/{file}.pdf
    scratch: /tmp/scratch-{slug}-1.txt
    covers: ["{claim-group label}"]
    extraction_type: text-native   # text-native | ocr-scan | extraction-lossy (from manifest)
    # ocr-scan / extraction-lossy → the artifact's primary_sources entry also carries
    # `content_block`, pasted verbatim from ocr-consensus.py's emitted line at sibling
    # prep (/prepare-ocr-sibling step 5). Renders as a `Content Block` row.
topic_relevance: "<one line: how the subject connects to the topic via linked_nodes>"
gaps: ["{what the record is missing}"]
blocking_prep: []              # source-prep prerequisites the orchestrator must clear before the Worker
                               # (NOT gaps, NOT Worker tasks). e.g. an ocr-scan reused source whose
                               # verified .txt sibling does not yet exist -> /build step 4b must produce it.
all_internal: false            # true => orchestrator skips external + archive (NOT source-prep / 4b)
validator_findings: []
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
    scratch: /tmp/scratch-{slug}-2.txt
primary_sources_registered: [{category}/{file}.pdf]
validator_findings: []         # validate.py --phase archive
```

```yaml
# worker — returned stub (one per source)
# The worker EMITS this fragment; it does NOT merge into the shared
# artifact. The builder serializes the merge of all worker fragments,
# then runs the extract-phase check once on the merged result.
agent: worker
worker_kind: pdf               # pdf | html | caption | foia
slug: {slug}
source: {category}/{file}.pdf
inputs_consumed: [/tmp/scratch-{slug}-2.txt]
outputs_produced:
  quotes:                       # verbatim spans BY the subject; legitimately [] for an about-the-subject / institutional source
    - text: "<verbatim span copied from scratch, never typed from memory>"
      location: "<source-shape anchor>"
  claim_groups_proposed: ["{claim-group label}"]
  cross_ref_candidates:
    - entity: /{type}/{related}
      kind: relationship
      span: "<location anchor>"
  background_material:          # the quotes: [] case — facts ABOUT the subject for the builder's prose
    - fact: "{fact}"
      source_phrasing: "<exact words from source — prose-drift grounding>"
      location: "<location anchor>"
  # cited_works (DOCUMENT sources only — conventions.md "cited_works
  # affirmation"; omit entirely for non-document sources). Pick exactly ONE
  # of three shapes; bare [] is REJECTED.
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
validator_findings: []         # validate-research.py --phase extract, on the merged artifact
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
```

```yaml
# auditor — returned stub
agent: auditor
slug: {slug}
node: {type}/{slug}.md
health: pass
adjacent_needs_update:
  - node: /{type}/{related}
    reason: "<a new source attests something this adjacent node should carry>"
    material_in_hand: /tmp/scratch-{slug}-2.txt
    skip_external: true        # external skipped — material already archived
propagation_loop: [/{type}/{related}]
validator_findings: []
```
