---
id: meta/conventions
type: meta
schema_version: 1
created: 2026-04-17
---

# Conventions

Human-readable rationale for the repository's evidentiary discipline and
structural decisions. The machine-readable specification — required
fields, valid vocabularies, required sections per node type — lives in
`schema.yaml`. This file explains *why* those rules exist.

---

## Core principle

Every claim is anchored to a primary source or explicitly flagged as
unverified. Contradictions are preserved, not reconciled. Testimony under
oath is documented separately from independent verification of the claim.
Primary-source URLs are archived locally so the record survives if the
source site dies.

The repository does not adjudicate between conflicting primary sources.
It documents what each source says and links to both. The reader draws
their own conclusions from the preserved evidence.

---

## Structure reflects evidence type

Evidentiary categories are separated structurally, not hidden in cells.

- A pilot who observed an object is an **eyewitness** — requires
  `Corroboration` (instrumented, testimonial, government statement).
- Someone who filed a formal complaint about claims made by others is a
  **whistleblower** — requires `Claim Inventory` (claim → document →
  status) and `Vouching Chain` (named attestations).
- Someone whose significance is institutional access is an
  **institutional-actor** — requires `Program Involvement` (program,
  role, evidentiary basis).
- A journalist whose significance is published reporting is a
  **reporter** — requires `Publication Record` (outlet, beat, notable
  coverage).

These distinctions are not cosmetic. An eyewitness account rests on direct
sensory observation; a whistleblower's account rests on the credibility of
sources they have not themselves observed; an institutional actor's
significance rests on what they had access to; a reporter's significance
rests on what they published. Structural separation makes the evidentiary
category visible before the reader reads the content.

The same principle applies to organizations (government vs.
government-contractor vs. private), events (proceeding vs. observed
incident), and documents (government vs. non-government).

---

## Statements as the universal evidentiary primitive

The evidentiary content of every node rests on `quotes[]` in the
research artifact — verbatim passages from primary sources with
per-quote mechanical verification (`validate.py` check #11 extracts
the cited source and substring-checks every passage marked
`✅ Confirmed — verified verbatim`). No contributor-synthesized claim
layer sits between source and reader, on any node type.

The rationale is failure-mode specific: contributor-prose summaries
introduce fine drift (dropped qualifiers, synonym rephrases,
word-level condensations) that mechanical checks catch poorly.
Eliminating the prose claim layer eliminates the drift surface. Other
nodes that cite facts from a source link to the source-bearing node
(document / transcript / media) and reference the specific passage —
no intermediate paraphrase exists to drift.

### Type-specialized views of `quotes[]`

Each node type renders a filtered view of the same universal primitive:

- **Person** → `## Statements`, split by `observation_type` (Direct
  Observations / Other Statements) and sorted by `statement_date`.
- **Person (whistleblower)** → additionally `## Claim Inventory`, a
  render-time projection of quotes tagged `category: filed-claim`.
  A filter, not a separate data structure — the filed claim IS the
  quote.
- **Event (hearing)** → `## Key Testimony`, verbatim passages sorted
  by `statement_date`, surfacing evidentiarily-distinctive moments.
- **Document / transcript / media / organization / location** →
  `## Key Passages`, verbatim excerpts of what the source says about
  its subject.

### Hearing events as venues

An event is a venue, not a speaker. F.2a collapsed the prior `What The
Hearing Established` synthesis section into `Witnesses & Testimony`,
a cross-reference table pointing at each witness's transcript and
written-testimony nodes. What a hearing "established" is the verbatim
record those linked nodes carry; the event node navigates to them
rather than paraphrasing.

### Synthesis prose is labeled and drift-checked

Contributor-synthesis prose is limited to labeled synthesis surfaces
(`description`, `background`, `uap_relevance`, `credibility_notes`)
and per-entry synthesis-content notes (`ownership_timeline.note`,
`key_personnel.note`, `vouching_chain.attestation`, etc.).
`validate-research.py` check #16 tokenizes each of these against the
primary-source text and warns on every unmatched significant token
(errors at 100% vocabulary divergence).

### News articles and books

Stored as `document` nodes (kind `non-gov-doc`, doc_form `article` or
`book`). Credibility analysis of the author/publisher lives on the
author's person node or the publisher's organization node, not on the
document.

### Prose-drift discipline on synthesis surfaces

Nodes carry contributor-prose surfaces that sit alongside the verbatim
`quotes[]` content: per-node `description` / `background` /
`uap_relevance` / `credibility_notes` paragraphs, and per-entry
synthesis content notes (`ownership_timeline.note`,
`uap_scope_activity.note`, `key_personnel.note`, `contracts.note`,
`media_versioning.note`, `vouching_chain.attestation`). These are
labeled synthesis — they exist to frame the evidentiary content — but
the F.1c Fravor audit (2026-04-19) surfaced a real failure mode where
contributor prose introduces unstated premises, paraphrase drift, and
content widening even when every referenced quote is verbatim-clean.

`validate-research.py` check #16 (prose-field token drift) verifies
that significant words in these prose fields appear in the referenced
primary-source text. The check is an impartial reporter — it flags
every unmatched token as a warning without classifying whether the
drift is "legitimate synthesis" or "real drift". The contributor
reviews each warning and asks: *does this unmatched token introduce
a fact or premise the source doesn't attest?* Errors fire only at
100% vocabulary divergence (complete mismatch — prose shares no
significant words with the source it claims to draw on), a
mathematical floor on pure fabrication rather than a stylistic
threshold. Below 100%, the validator makes no judgment; careful
contributor review is the quality gate.

Check #16 is explicitly scoped to synthesis prose (free-prose fields
and synthesis-content notes). Compact label cells (role titles, short
relationship descriptors, `timeline[].event`) and cross-reference
descriptor notes (`corroboration_items.note`, `witnesses_testimony.note`,
`org_relationships.note`, `location_relationships.note`) are out of
scope — token-match misfires on those surfaces; fabrication there is
Phase III semantic-review territory.

---

## Confirmed vs Flagged

Any structured section that mixes primary-source-supported entries with
secondary-source-only or unverified entries splits into `### Confirmed`
and `### Flagged` subsections.

- **Confirmed** — established from a primary source linked in the row
- **Flagged** — cited in secondary sources only; requires primary-source
  confirmation before treating as established

Empty Flagged subsections are omitted, not filled with placeholder text.
Presence of `### Flagged` with no rows is a schema violation; absence
indicates no flagged items.

The distinction records source quality, not truth. A Flagged item may
well be true; it hasn't been verified against a primary source yet.

---

## Sworn testimony vs claim verification

Testimony given under oath is a confirmed fact regardless of whether
the underlying claim is independently verified. These are two distinct
facts and must not be merged into a single statement.

**Correct**: "✅ Confirmed as sworn testimony — claim not independently verified"
**Incorrect**: "Claimed that..." (implies testimony is unconfirmed)
**Incorrect**: "Testified that X is true" (conflates testimony with verification)

When an authoritative body later denies a sworn claim, the denial is
logged as a separate dated entry. The sworn testimony row stays confirmed.
Both facts coexist because both are true.

Q&A testimony under oath carries the same evidentiary weight as prepared
written testimony. Oral and written versions of a witness's testimony are
preserved as independent primary records — the hearing transcript node
holds the oral record; the written testimony document node holds the
written record. Cross-entity comparison between the two (where a claim
appears and how the placements differ) is a synthesis finding and
belongs on a finding node, not on either primary record.

---

## Contradictions

Two markers distinguish evidentiary disagreement by the quality of
evidence on each side:

- **`⚠ Disputed — unknown`** — both parties assert opposing claims;
  neither has primary-source evidence beyond their own authority to
  speak. Document what each side says; link to both sources. The
  repository does not adjudicate.
- **`❌ Contradiction`** — positions directly contradict **and at
  least one side is backed by primary-source evidence**. Two shapes:
  (a) both sides have primary-source evidence that conflicts (e.g.,
  AARO HRR Vol I finding vs. a FOIA-released DIRD document);
  (b) one side has primary-source evidence, the other rests on
  self-attestation or on-record claim alone (e.g., DoD PA official
  denial vs. individual's self-reported role). In either shape, each
  source remains confirmed from its own origin; the primary-source
  asymmetry (if any) is noted in the row; the disagreement itself is
  the analytical finding.

When an authoritative source formally contradicts a confirmed claim, the
contradiction is documented on the **synthesis node where the
disagreement gains analytical meaning** — not on the source document
nodes themselves. Document nodes record each source's statement
verbatim in Key Passages; cross-document contradictions are a synthesis
finding, not a property of either document.

| Situation | Where |
|---|---|
| Post-event denial | `Node Versioning` on the relevant person / event / organization node |
| Institutional self-contradiction | `Credibility Notes` on the person / organization node |
| One document's statement contradicts another's | `Institutional Assessment` on the relevant organization node (when an agency finding contradicts a cited claim), or a finding node spanning the conflicting sources |
| Written vs. oral testimony divergence | Finding node spanning the two primary records (transcript + companion written testimony document) |
| Contested affiliation | `Flagged` subsection of `Affiliations` |

The Confirmed/Flagged binary is unchanged by contradictions —
"contradicted" is not a third status. Both sources remain confirmed
from their respective origins; the evidentiary disagreement is
documented separately.

---

## Finding nodes

Some patterns span multiple entities. When an analytical narrative about
a cross-entity pattern would otherwise be duplicated across 3+ entity
nodes, create a single `/findings/{slug}` node.

**Creation threshold:**
- Pattern spans 3+ entity nodes, OR
- Analytical narrative would exceed ~200 words in any single entity
  node's cell, OR
- The same text is about to be written into 3+ different nodes.

Below these thresholds, keep the analysis in the single most relevant
entity node. Don't create a finding for every pairwise cross-reference.

Entity nodes cited by a finding carry a short summary (1–3 sentences) +
link back to the finding, not the full narrative. The finding node is
the single canonical home for that pattern.

Findings are not verdicts. They document cross-entity patterns observed
in primary sources and flag the analytical questions each pattern
raises — without adjudicating intent or assigning responsibility.

---

## Neutrality

The repository documents observed facts from primary sources and does
not adjudicate intent, motivation, or compliance with norms external to
the documentary record. Analytical sections (Institutional Assessment,
Credibility Notes, findings) frame observations in neutral terms.

This principle is repository-wide. Individual nodes and sections do not
need to recite neutrality language per cell — the principle stated here
governs the entire repository.

---

## Versioning

Nodes are never closed and source data is never overwritten.

- **New source adds information** → add a new row with date and source
- **New source contradicts existing claim** → keep original with its
  source; add new claim in a separate row; link the two via
  `Superseded By` (formal correction) or `Contradicted By` (active
  disagreement)
- **Claim formally corrected** → `Superseded By` on the original — do
  not delete the original

Git log is the edit-history record. In-document changelogs are not
maintained — `git log --follow` on the node file is authoritative.

---

## Associated Nodes

Every node carries an `## Associated Nodes` section — a navigational
index of all cross-references grouped by target type (Events,
Documents, Transcripts, News, Organizations, People, Findings).

This section is auto-generated by `scripts/associate.py` from
`[`/path`]` link references in the node body. Do not hand-edit.

---

## Primary sources and archival

Every external URL cited in any node is archived locally in
`/sources/{category}/{filename}` and registered in
`/sources/manifest.yaml`. The local archive is the integrity guarantee;
the Internet Archive Wayback Machine submission (via
`scripts/archive.py`) is insurance.

Citations in prose are direct markdown links to the archived file or
the manifest entry, not prose references to manifest row numbers.

When a source is blocked or paywalled, the manifest entry records the
block status and the archival route (if any) is documented on the
entry. See `sources-access.md` for site-specific workarounds.

---

## Scope

The repository is a general-purpose primary-source investigation
toolkit. Its first instance documents UAP-related public-record
material, but the schema and structure are topic-neutral. Any
investigation grounded in primary sources — historical event, legal
case, policy decision, scientific controversy — can use the same
structure.
