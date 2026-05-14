---
id: people/{{slug}}
type: person
schema_version: 1
status: active
archetype: {{archetype}}
created: {{today}}
---

# {{display_name}}

## Identity

| Field | Value | Source |
|---|---|---|
| Full Name |  |  |
| Aliases |  |  |
| Nationality |  |  |
| Profession |  |  |

---

## Background

<!-- Prose only. Length is whatever the archived primary sources support
     for this person — let source density drive the length, not a target.
     Structured career data belongs in Affiliations, not here. Do not
     include tables in this section. -->

---

## {{topic_display_name}} Relevance

<!-- Why is this person in this repository? What makes their role /
     testimony / reporting / observation load-bearing? Length is
     whatever the source attests — let source density drive it. -->

---

## Affiliations

### Confirmed

| Organization | Role | Period | Source | Node Link |
|---|---|---|---|---|
|  |  |  |  |  |

<!-- Rows are listed in chronological order (earliest start-of-Period
     first). The chronological-ordering check enforces this. -->

### Flagged

<!-- Omit this subsection entirely if no flagged affiliations exist. -->

---

## Statements

<!-- Universal statement surface. Every verbatim utterance by this
     person goes here — first-hand testimony, relayed claims, on-record
     statements in any venue. Each entry is a block quote followed by a
     3-field verification table. No contributor-paraphrased claims; the
     only text between source and reader is the contributor's
     attribution line.

     Split by `observation_type`:
       - Direct Observations — first-hand sensory testimony (what the
         person personally saw / heard / measured).
       - Other Statements    — everything else (relayed, inferential,
         interpretive, filed-as-claim, published).

     Both subsections list entries in chronological order by the date in
     each statement's verification block — earliest first. The Phase II
     person renderer sorts mechanically at build time. The
     chronological-ordering check enforces table-row ordering universally
     but does not yet cross-check block-quote statement order.

     Entry shape: a markdown blockquote with the verbatim passage,
     then a 3-row verification table with rows
       Attributed to / Source / Location.
     Source field renders as a markdown link to the archived source
     (e.g., `[archived source](../sources/government/some.pdf)`). See
     prompts/build.md (Step 6 — quotes discipline) for the canonical
     shape. -->


### Direct Observations

<!-- First-hand sensory observations. May be empty (most common for
     reporter / institutional-actor archetypes). Omit the subsection
     header entirely when empty? NO — keep the header so the statement-
     surface shape is uniform across archetypes. Contributor writes
     "(None documented.)" under the header when empty. -->

### Other Statements

<!-- Relayed / inferential / interpretive / filed-claim / published.
     Always populated on any person node worth building — if this is
     empty the person has no on-record statements and the node probably
     shouldn't exist yet. -->

---

## Timeline

| Date | Event | Category | Source | Node Link |
|---|---|---|---|---|
|  |  |  |  |  |

<!-- Aggregated chronological record of all dated facts about this
     person. One row per dated event. Category column values:
     affiliation / role / observation / testimony / publication /
     clearance / incident / filing / other.
     Rows listed earliest first; the chronological-ordering check enforces. -->

---

## Relationships

### Confirmed

| Person | Relationship | Node Link |
|---|---|---|
|  |  |  |

### Flagged

<!-- Omit if empty. -->

---

<!-- ARCHETYPE: eyewitness -->
## Corroboration

| Source | Type | What It Confirms | Node Link |
|---|---|---|---|
|  |  |  |  |

<!-- Cross-reference surface — OTHER observers / instruments /
     government statements that corroborate this person's direct
     observations. NOT a statement surface; it doesn't contain this
     person's utterances (those live in `## Statements`). Type column
     values: testimonial / instrumented / government-statement /
     documentary. -->

---
<!-- /ARCHETYPE -->

<!-- ARCHETYPE: whistleblower -->
## Claim Inventory

| Claim | Document | Status | Node Link |
|---|---|---|---|
|  |  |  |  |

<!-- Derived view of this person's filed claims — each row maps to one
     or more statements tagged `category: filed-claim` in the research
     artifact. The statements are primary; this table is a render-time
     index grouping them claim → supporting document → status.

     Status values:
     - Document exists and supports
     - Document exists and contradicts
     - No document anchor identified -->

---
<!-- /ARCHETYPE -->

<!-- ARCHETYPE: institutional-actor -->
## Program Involvement

| Program | Role | Period | Evidentiary Basis | Confidence | Source |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

<!-- Metadata surface — programs this person had access to and the role
     they held. Evidentiary Basis cites the primary source that confirms
     the role (primary-source / sworn-testimony / on-record /
     self-attested / secondary). Confidence: high / medium / low. Rows
     listed earliest first by Period start date. -->

---
<!-- /ARCHETYPE -->

<!-- ARCHETYPE: reporter -->
## Publication Record

| Date | Publication | Outlet | Beat / Role | Source | Node Link |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

<!-- Cross-reference surface — indexed list of published works. Rows
     listed earliest first by Date. When a publication is also a
     document node in the repository, fill Node Link. -->

---
<!-- /ARCHETYPE -->

## Credibility Notes

<!-- Analytical paragraphs grounded in primary sources. For eyewitnesses,
     include an observational framing note. When a discrete finding
     spans 3+ entity nodes or otherwise meets the finding-node creation
     threshold (see meta/schema.yaml::types.finding.creation_threshold),
     promote it to a finding node. -->

---

<!-- ARCHETYPE: whistleblower -->
## Vouching Chain

| Name | Credentials | Statement | Source | Node Link |
|---|---|---|---|---|
|  |  |  |  |  |

<!-- Cross-reference surface inside Credibility Notes' analytical
     frame. Only direct, on-record, attributed statements qualify. The
     Statement column is a verbatim excerpt from the voucher's
     testimony; when a full verbatim passage is useful, register it as
     a quote entry in the vouching person's own research artifact and
     link to their person node via Node Link. -->

---
<!-- /ARCHETYPE -->

## Associated Nodes

<!-- Auto-generated by scripts/build/associate.py. Do not hand-edit. -->
