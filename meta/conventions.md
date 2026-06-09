---
id: meta/conventions
type: meta
---

# Conventions

Human-readable rationale for the repository's evidentiary discipline and
structural decisions. The machine-readable specification — required
fields, valid vocabularies, required sections per node type — lives in
`schema.yaml`. This file explains *why* those rules exist.

---

## Contents

- **Part I — Core epistemic principles**
  - [Core principle](#core-principle)
  - [Relevance can be relational](#relevance-can-be-relational)
  - [Structure reflects evidence type](#structure-reflects-evidence-type)
  - [Confirmed vs Flagged](#confirmed-vs-flagged)
  - [Sworn testimony vs claim verification](#sworn-testimony-vs-claim-verification)
  - [Source priority — anchoring when multiple sources attest](#source-priority--anchoring-when-multiple-sources-attest)
  - [Contradictions](#contradictions)
  - [Neutrality](#neutrality)
- **Part II — The evidentiary primitive: quotes**
  - [Statements as the universal evidentiary primitive](#statements-as-the-universal-evidentiary-primitive)
  - [Density is source-driven](#density-is-source-driven)
- **Part IV — The synthesis layer**
  - [Three-layer evidentiary architecture](#three-layer-evidentiary-architecture)
- **Part VII — Repository conventions & hygiene**
  - [Versioning](#versioning)
  - [Scope](#scope)
  - [Repository layout — content flat, tooling organized](#repository-layout--content-flat-tooling-organized)
  - [Working notes are a report, not a residue](#working-notes-are-a-report-not-a-residue)
  - [Comments describe code, not refactor history](#comments-describe-code-not-refactor-history)

---

## Part I — Core epistemic principles

### Core principle

Every claim is anchored to a primary source or explicitly flagged as
unverified. Contradictions are preserved, not reconciled. Testimony under
oath is documented separately from independent verification of the claim.
Primary-source URLs are archived locally so the record survives if the
source site dies.

The repository does not adjudicate between conflicting primary sources.
It documents what each source says and links to both. The reader draws
their own conclusions from the preserved evidence.

The repository **preserves**; it records what each source says verbatim
and does not clean, correct, or improve it. Source-form artifacts — OCR
errors, the document's own typos, garbled-but-legible scan regions — are
preserved as-is and flagged (`naming_quirks` / sic), never silently
fixed. Recovering the human-visible text of a garbled scan is
preservation; deleting or altering it is not.

### Relevance can be relational

An entity earns a node when it has a primary-source-documented connection
to the investigation's subject — and that connection may live in the
entity's *relationships* rather than in its own sources. An entity can be
load-bearing through documented ties — a shared parent organization, a
shared contractor, a sister-office / predecessor / successor
relationship, a named association in another party's record — even when
the entity's own primary sources never mention the subject at all. When
that is the case, the node captures two things: (1) the connecting
relationship(s), each attested by the source that establishes it — the
load-bearing core; and (2) enough basic, source-grounded context about
the entity for the connection to be legible, without sprawling into
detail unrelated to the investigation. The connection is documented
strictly to what the sources support, never beyond; any inference about
*why* it matters stays in the synthesis layer (findings / investigations)
and with the reader.

Corollary: an entity's relevance often cannot be judged from its own
source in isolation — it is judged against the connected record. The
build topology applies this at investigation time (see
`prompts/topology.md` "Source-read-first" — load-bearing-ness judged in
context).

### Structure reflects evidence type

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

### Confirmed vs Flagged

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

### Sworn testimony vs claim verification

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

### Source priority — anchoring when multiple sources attest

When multiple primary sources attest a fact about a subject (rank,
role, capacity, sequence of events, framing of significance), the
contributor anchors on the source closest to the subject's own
first-person attestation:

1. **Subject's own verbatim words** — highest authority for facts
   about themselves. First-person statements, self-published bios,
   filings the subject signed.
2. **Other primary witnesses' attestations** — first-hand observers
   describing the subject. Direct testimony from someone who was
   present.
3. **Media narrator / outlet framing** — lowest priority. The
   outlet's editorial summary or characterization is one step
   removed from the witness's own words.

This applies whether or not sources strictly disagree — the hierarchy
governs which source to cite as the anchor for any fact, not only
which to "believe" in a contradiction.

How to apply per case:

- **Facts about the subject** (rank, role, identity, motivation,
  internal state during an event): prefer the subject's verbatim
  quotes. Fall back to primary witnesses, then outlet framing.
- **Facts about external events the subject observed** (radar
  acquisitions, what other personnel did, command structure):
  prefer whichever primary source has direct attestation —
  typically the institutional source (military document,
  after-action report) over witness recall.
- **When outlet narrator says X but the subject's own quote says
  Y:** anchor on Y. Record the narrator divergence in
  `naming_quirks` if recurring or material; otherwise in the
  relevant entry's `note` field.
- **When a primary witness attests something about the subject
  that the subject hasn't themselves attested:** cite the witness's
  attestation as the source, marking observation_type appropriately.
- **Don't synthesize across sources to produce a "best of both"
  composite fact.** Pick one source as the anchor; if the alternate
  carries material content, capture it as a separate entry with its
  own source attribution and let the divergence stand.

This rule complements [Contradictions](#contradictions) below — the
hierarchy decides which source the contributor anchors on; the
Contradictions framing decides how the divergence itself is documented
when sources directly conflict.

### Contradictions

Two markers distinguish evidentiary disagreement by the quality of
evidence on each side:

- **`⚠ Disputed — unknown`** — both parties assert opposing claims;
  neither has primary-source evidence beyond their own authority to
  speak. Document what each side says; link to both sources. The
  repository does not adjudicate.
- **`❌ Contradiction`** — positions directly contradict **and at
  least one side is backed by primary-source evidence**. Two shapes:
  (a) both sides have primary-source evidence that conflicts (e.g.,
  an agency report's finding vs. a FOIA-released document);
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
| Source-form disagreement (two sources attest opposing forms of the same fact, contributor does not adjudicate) | `naming_quirks` entry with `resolution: disputed`; auto-rendered as `## Preserved Disagreements` near the foot of the node body |

A person stating opposing things across their own statements ("I did" /
"I didn't") is NOT a cross-source contradiction and stays on the person
node: under the `claim_group` grouping of `## Statements` (see
`quote_entry.claim_group`), the two statements sit adjacently in the same
claim group as separate verbatim quotes — both shown, no marker, no
finding. The grouping is pure organization of a single entity's own
statements; it carries no `❌`/`⚠` and no `/findings/` link. Cross-entity
contradictions (one source vs. a *different* entity's source) remain a
finding per the table above — that boundary is unchanged.

The Confirmed/Flagged binary is unchanged by contradictions —
"contradicted" is not a third status. Both sources remain confirmed
from their respective origins; the evidentiary disagreement is
documented separately.

### Neutrality

The repository documents observed facts from primary sources and does
not adjudicate intent, motivation, or compliance with norms external to
the documentary record. Analytical sections (Institutional Assessment,
Credibility Notes, findings) frame observations in neutral terms.

This principle is repository-wide. Individual nodes and sections do not
need to recite neutrality language per cell — the principle stated here
governs the entire repository.

---

## Part II — The evidentiary primitive: quotes

### Statements as the universal evidentiary primitive

The evidentiary content of every node rests on `quotes[]` in the
research artifact — verbatim passages from primary sources. No
contributor-synthesized claim layer sits between source and reader,
on any node type.

The rationale is failure-mode specific: contributor-prose summaries
introduce fine drift (dropped qualifiers, synonym rephrases,
word-level condensations) that mechanical checks catch poorly.
Eliminating the prose claim layer eliminates the drift surface. Other
nodes that cite facts from a source link to the source-bearing node
(document / transcript / media) and reference the specific passage —
no intermediate paraphrase exists to drift.

#### Confirmation is a precondition for inclusion

Quotes appear in node bodies only after confirmation against the
underlying primary source. Confirmation is a precondition for
inclusion, not a rendered flag. The rendered output carries no
verification marker — the source link is the evidence; a reader
verifies a quote by following the link to the archived source, not
by reading a checkbox.

The principle is enforced mechanically by the build validator: the
verbatim-quote check fails any commit where a quote's `text` does not
appear in the extracted source. The check runs against the research
artifact's `quotes[]` directly — `text` + `source.path` are structured
fields, no rendered-output parsing involved. The rendered node body
inherits the verified quote text from the artifact by construction.
The enforcement is invisible to the reader by design. The validator
catches silent drift (a quote edited in an artifact months later that
no longer matches the source) and broken source references; it does
not, and cannot, perform trust on the reader's behalf.

Transcripts of speech sources — congressional hearings, podcasts,
broadcasts, interviews, depositions, conference talks — are
equivalent-footing sources once confirmed against the relevant
primary source. The inclusion bar does not vary by medium: every
quote, whether extracted from a PDF, an HTML page, a stenographic
transcript, or a captioning file, must appear in the cited source.
No marker variant, no different verification path, no renderer
special-casing. What "the cited source" means for a transcript
depends on the transcript's provenance: human-produced transcripts
(stenographic court reporting, outlet-published transcripts with
human editorial review) ARE the primary source; auto-caption files
(YouTube auto-captions, Otter.ai, Whisper output) are machine
extractions of the underlying audio/video, and the underlying media
is the original source. The per-provenance verification path lives in
the `transcript_provenance` enum (`schema.yaml`) and the
`/verify-transcript` skill.

**When a source gets a `.txt` sibling — the rule.** A `.txt` sibling
exists *if and only if* the source's default extraction is not a
faithful rendering of the original text — i.e. its `extraction_type`
is `ocr-scan` or `extraction-lossy`. A `text-native` source (clean
text layer, HTML, plain text) is rendered faithfully by `pdftotext` /
direct read and **never gets a sibling**: producing one is busywork
and adds a drift surface for no gain. The two non-text-native cases
are the "corrupted or image" pair — `ocr-scan` is a scanned image
(OCR reconstructed the text from page pictures), `extraction-lossy`
is a text-native PDF whose extracted *bytes* are wrong (not an image,
but corrupted at the content-stream / extraction layer). Sibling
existence keys on extraction faithfulness, not on file type.

The same `.txt`-sibling preference handles `extraction_type:
extraction-lossy` sources — text-native PDFs whose extracted text is
**pervasively** unreliable for non-OCR reasons: stenographic-format
noise (inline line-number prefixes and page-footer triplets on every
line, as in court-reporter transcripts) or systematic Unicode-mapping
corruption across the document. Such corruption lives in the source
PDF's content stream itself, so switching extraction tools is not a
path forward — the recovery is the sibling.

**A sibling must be proportionate to the damage.** The recovery for a
*pervasively* corrupted extract is the contributor-produced clean
transcription, visually verified against the source page. But a clean,
natively-paginated text layer marred by only a *sparse, isolated*
glyph artifact — a single `11½`→`‡` in one passage of an otherwise
pristine transcript — does **not** warrant hand-transcribing the
document. That manufactures a large, drift-prone artifact to repair
one character. Such a
source stays `text-native`: `pdftotext` is the canonical extract
(natively paginated, so `p. N` resolves for free against its form
feeds), and the isolated glyph is handled at the point of use —
re-derive the affected quote, or add the specific Unicode-confusable
to `normalize_for_compare` — never by transcribing the whole document.
Reserve the sibling for extraction that is broken throughout; the test
is the OCR-producer / pervasive-noise signal (the detection signals in
`archive.md`), not the presence of any single bad character.

### Density is source-driven

Templates and prompts do not impose count targets on artifact content.
This applies uniformly to two surfaces:

- **Entry lists.** `quotes`, `naming_quirks`,
  `affiliations`, `relationships`, `corroboration_items`,
  `program_involvement`, `publication_record`, `vouching_chain`,
  `participants`, `witnesses_testimony`, `timeline`, `key_personnel`,
  `org_relationships`, `contracts`, `media_versioning`, and any
  other entry-list section the schema defines.
- **Free-prose fields.** `description`, `background`, `top_relevance`,
  and `credibility_notes`.

Contributors populate each surface with what archived primary sources
support — no more, no less. The source produces the count. If a
section ends up with one entry, that's correct. If it ends up with
fifty, that's correct. Validators don't check counts; they check
each entry's traceability to source.

Count targets ("aim for ~10 quotes", "1-2 paragraphs",
"approximately 6-10 substantive entries", "2-4 sentences",
"~50 words per paragraph") create pressure that splits two ways under
real source variance: filler entries when the source doesn't support
the count, or hallucinated content when the model fills the gap from
training knowledge. The contributor surface that introduces a count
target is the surface where these failure modes originate — the rule
applies prospectively to template authoring, prompt drafting, and
scope-at-session-start.

Comparison framings also count as targets and should be avoided:
"this section seems sparse", "comparable nodes have N entries; this
one has fewer — anything to add?". Only flag specific entries that
look unsupported by source; never flag aggregate counts.

**Density governs count, not capture.** The rule bars count *targets*;
it does not license declining to capture a class of source material the
source actually carries. Whether the source has a reference list to
record in `cited_works`, whether a passage is a load-bearing quote,
whether a contradiction is attested — those are source-*presence*
questions, answered by reading the source, not density questions. The
misread to refuse is "these references aren't load-bearing, so leave
`cited_works` empty": a source-attested reference list is captured
*because the source carries it* (the build-protocol document-extraction
rubric names References as a capture category). For `cited_works`
specifically, the empty-state ambiguity is closed by the three-state
`cited_works` affirmation (`NONE | IGNORED | non-empty list`) — a bare `[]` is
rejected outright, so the contributor cannot quietly drop a captured
list on "not load-bearing" grounds. Density governs only how many
entries a captured list then yields. The same holds for every
required-but-emptyable source-anchored section: an empty list is
correct only when the source genuinely lacks that material, never as a
discretionary skip.

---

## Part IV — The synthesis layer

### Three-layer evidentiary architecture

The repository carries three distinct evidentiary node layers sitting on
the source substrate. Each has a different role; the boundaries are
load-bearing for the discipline.

#### Tier model and linking contract

Counting the source substrate, the architecture is **four tiers**.
References run **downward** — a node may reference a *lower* tier, never a
*greater* one — with exactly one same-tier exception (entity ↔ entity). This
is the directional contract: facts flow up to synthesis; synthesis never
flows back into the fact substrate.

| Tier | Node types | May reference | Must NOT reference |
|---|---|---|---|
| **1 — Sources** | archived files under `sources/` | — (the evidentiary floor; it is referenced *by* nodes and references nothing) | anything |
| **2 — Entity** | person · organization · document · event · transcript · media · location | Tier 1 (sources) **and Tier 2 (other entity nodes, laterally)** | Tier 3 (findings), Tier 4 (investigations) |
| **3 — Findings** | finding | Tier 1 (sources) + Tier 2 (entity nodes) | Tier 3 (other findings), Tier 4 (investigations) |
| **4 — Investigations** | investigation | Tier 1 + Tier 2 + Tier 3 (findings) | Tier 4 (other investigations) |

Two consequences are worth stating outright:

- **Same-tier links exist only at Tier 2.** Entity nodes cross-reference
  each other — Affiliations → org, Speakers → person, Participants → person,
  transcript `derived_from` → event — and that lateral web is the navigational
  fabric (`## Associated Nodes`). The synthesis tiers do not cross-link at
  their own level: a finding never references another finding (it stays
  cluster-neutral, citable from multiple investigations), and an investigation
  never references another investigation.
- **Nothing references a Tier-4 investigation.** It is the top of the
  iceberg — discoverable from the priority queue and inter-node paths, never
  by a lower tier pointing up at it.

A reference *up* a tier — an entity node naming a finding, a finding naming
an investigation — inverts the flow and is a defect **even in prose, even
when the target exists**: a bare-slug prose mention ("the {slug} finding")
is the same violation as a `/findings/…` path. Four checks enforce the
contract directionally, each catching both the path form and the bare-slug
form (via the finding/investigation node-slug index, `ctx.synthesis_slugs`):
`entity_no_finding_or_investigation_refs` (Tier 2 → 3/4),
`finding_no_investigation_refs` (Tier 3 → 4), `finding_no_finding_refs`
(Tier 3 → 3, same-tier), and `investigation_no_investigation_refs`
(Tier 4 → 4, same-tier). The same-tier checks exclude the node's own slug,
so a self-reference in `id` / `target_node` is not a violation.

#### Entity nodes — facts

Entity nodes (people, organizations, documents, events, transcripts,
media, locations) carry **facts**: single-source attestations,
including load-bearing facts that name other entities. The fact
"witness W on transcript T named organization O as the contractor
they reported to investigators" is a fact about W — it lives on
W's person node, on T's transcript node, and (because it's
load-bearing for O) on O's organization node. Same primary source;
three entity-side fact records. None of
them speculates beyond what the source attests.

Entity nodes keep cross-node links, `## Associated Nodes`, structural
cross-references (Affiliations rows pointing at orgs, Speakers
pointing at persons, transcript `derived_from`, etc.), and prose-
section references to other entities where the primary source
attests them. Those are facts, not findings.

#### Finding nodes — multi-source patterns

A finding documents a **pattern that becomes visible only by reading
multiple primary sources together**. No single source attests the
pattern; the synthesis-of-reading-together produces information not
present in any constituent attestation. Multi-source convergence
(or divergence on a single question) is what makes it a finding,
not the number of entities it touches.

Findings cite primary sources DIRECTLY via `evidence[].source.path`,
never entity-node markdown files. The `attestor_path` field on each
evidence row captures who attested; the citation itself goes to the
source.

Findings duplicate primary-source content from entity nodes BY
DESIGN. If a finding cites material the relevant entity node
doesn't yet attest, the entity node is updated first (primary
source confirmed + archived) before the finding can use it. The
`finding-source-in-entity-node` check enforces this directionally:
every `quotes[].source.path` on a finding artifact must appear in
at least one entity-type research artifact's `primary_sources[]`.
Findings can't introduce sources the entity layer doesn't already
attest.

Findings DO NOT REFERENCE the investigations that consume them —
directional contract enforced by the `finding_no_investigation_refs`
check. Findings stay cluster-neutral so they can be cited from
multiple investigations.

Entity nodes (person / organization / document / event / transcript /
media / location) DO NOT REFERENCE findings or investigations —
symmetric directional contract enforced by the
`entity_no_finding_or_investigation_refs` check. Facts flow up to the
synthesis layer; the synthesis layer does not flow back into the
fact substrate. The Ryder person node attesting that he was named in
the SD004 statement is a fact; pointing the Ryder node at the
finding that synthesizes the multi-source authorship-chain pattern
would invert the flow. Findings and investigations are discoverable
from the priority queue, the research-queue cross-references, and
inter-finding / inter-investigation paths — not from the entity
layer pointing at them.

Findings are not verdicts. They document the multi-source pattern
and stop there — what the convergence establishes, what it doesn't
establish, where it diverges. Hypothesis evaluation belongs on
investigation nodes.

#### Investigation nodes — speculation-tolerant hypothesis evaluation

An investigation pursues an open question or hypothesis by consuming
findings and entity-node facts. Investigations are
**speculation-tolerant** — the layer where hypotheses are evaluated
against the primary-source record. Per-hypothesis status verdicts
capture the current evidentiary standing as free-text phrases
("Substantiated as allegation on record"; "Not established by
primary sources"; etc.).

Investigations link to and summarize findings via `cited_findings[]`
and per-hypothesis `sources[]` rollups; findings do not link back.
Investigations build cases — proving, disproving, or further
pursuing the question.

Investigation prose surfaces (hypothesis_evaluation, best_current_answer,
counter_evidence, open_questions, closure_path) are NOT subject to
the prose-drift check (speculation by design). Instead, the
`investigation_hypothesis_citation` check requires each
hypothesis subsection to carry a non-empty `sources[]` rollup
naming the findings or entity-node anchors the contributor drew on.

#### Bright line — fact vs finding

A **fact** = a single attestation from a single primary source. Lives
on the relevant entity nodes (speaker's node, named-subject's node,
document / transcript / event node where attested). May reference
other entities (because the source names them) but doesn't synthesize
across sources.

A **finding** = a pattern that becomes visible only when multiple
primary sources are read together. No single source establishes the
pattern; the synthesis is the cross-source convergence (or
divergence on a single question).

A witness on a single podcast naming a contractor = fact (one source,
one statement). A company's consistent refusal to deny across three
news outlets' inquiries over a year = finding (three sources, the
pattern is the consistency). A person authored a document
anonymously (named in a separate filing, entered into the public
record) = finding (three-source chain establishing authorship).

#### Promotion thresholds

An open question or caveat below the investigation threshold stays
structurally encoded on the entity node — empty period_end fields
with prose hedges, naming_quirks with `resolution: disputed`, etc.
Don't track sub-investigation items in a workflow surface; the
entity node is the canonical record of what the corpus knows.

An open question becomes an investigation when it picks up ANY of:
active pursuit (someone gathering primary sources to answer it),
cross-entity scope (≥2 entity nodes), competing answers being
weighed (≥2 hypotheses with primary-source backing on different
sides), or analytical content requiring sustained evaluation
(≥ ~100 words).

A finding is justified when the multi-source convergence pattern
emerges — typically when 3+ independent sources converge on (or
diverge on) a single question. The pattern-shape is what matters,
not the entity count.

These structural thresholds govern WHEN analysis moves to a different
node, not HOW LONG a field's prose should be. The finding-node creation
threshold (~200 words, 3+ entity nodes, or text about to be written into
3+ different nodes — see "Bright line — fact vs finding" above) is one
such gate; cross-reference brevity — entity nodes citing a finding carry
a brief summary plus link back, with the canonical narrative living on
the finding node — is likewise structural rather than length-prescribed.

---

## Part VII — Repository conventions & hygiene

### Versioning

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

### Scope

The repository is a general-purpose primary-source investigation
toolkit; the schema and structure are topic-neutral. Any
investigation grounded in primary sources — historical event, legal
case, policy decision, scientific controversy — can use the same
structure.

### Repository layout — content flat, tooling organized

Three tiers, each with a different organizing principle:

**Investigator-facing content** (flat by design):
`/people/`, `/organizations/`, `/documents/`, `/events/`, `/transcripts/`,
`/media/`, `/locations/`, `/findings/` each hold single-level `slug.md`
files. `/sources/` is flat within each category subdirectory. A
researcher looking for `/people/{slug}.md` finds it one click in
— no `/people/{archetype-category}/{sub-category}/{slug}.md`
nesting. The frontmatter (archetype, kind, status) carries the
categorization that hierarchy would otherwise impose.

**Backend tooling** (`/scripts/`) is organized for engineering hygiene,
not researcher browsing. `/scripts/lib/` holds genuinely shared
cross-cutting helpers.

**Governance and structured-data backing** (`/meta/`) is organized
by role: `/meta/templates/`, `/meta/topic/`, `/meta/research/`. Research artifacts live under `/meta/research/`
because they are the contributor-edited Phase I working surface and
the agent-readable structured fact layer (per `AGENT.md`) — not
investigator-read narrative. Putting them with templates (mechanical
scaffolding) and schema (the spec they conform to) reflects what they
actually are: structured data backing the rendered nodes, not content
in their own right.

The flatness rule is about content the investigator reads, not about
files the toolkit maintainers and pipeline scripts edit. Don't
extrapolate the content-layer rule onto the tooling or governance
layer — and don't extrapolate organized-by-role onto the content
layer.

#### Inside `/scripts/` — six tiers by caller / role

`/scripts/` is organized by caller and role rather than by file type.
Every script lives in exactly one of six subdirectories — no Python
script sits directly in `/scripts/` itself. New scripts land at the
tier that matches who invokes them and what role they play:

- **`/scripts/build/`**: the build pipeline + the validators that gate
  each phase. Contributor-facing — contributors invoke these directly
  during a build session. The orchestrators
  (`build-from-research.py`, `validate.py`, `validate-research.py`,
  `review-coverage.py`) plus scaffolders (`new.py`,
  `research-scaffold.py`), Phase I extraction (`extract-source.py`),
  post-build housekeeping (`associate.py`, `build-state.py`).
  Per-type renderer modules dispatched by
  `build-from-research.py` live under `/scripts/build/renderers/`
  (one module per node type plus `_common.py` and `_universal.py`).
- **`/scripts/tools/`**: standalone utilities, integrations, and
  diagnostics — also contributor-facing but not part of the
  scaffold → render → validate transformation pipeline. The
  manifest CLI (`manifest.py`), Wayback submission (`archive.py`),
  YouTube transcription (`transcribe.py`), and read-only contributor
  diagnostics (`check-vocab.py`, `coverage-suggest.py`, `normalize-locations.py`).
  Tools with environmental prerequisites (binaries, env vars, Python
  modules, browser session state) verify those prerequisites at
  `main()` entry rather than deferring the check until first use.
  Existing patterns vary by tool (`preflight()` in `download-video.py`,
  `ensure_tools()` in `extract-frames.py`, `_import_deps()` in
  `detect-faces.py`, inline checks at `main()` entry elsewhere); the
  load-bearing rule is fail-fast with a contributor-friendly install
  hint, not a uniform function name.
- **`/scripts/checks/`**: per-check modules — every named validator
  check (verbatim-quote, prose-drift, chronological-ordering,
  manifest-files-present, iff-section, etc.) lives at
  `scripts/checks/{check_name}.py`. The three validators under
  `scripts/build/` are thin orchestrators that import + dispatch
  these via explicit step lists. Contributors don't usually invoke
  check modules directly (the orchestrators do), but each check is
  individually importable for unit-testing or single-check debugging.
  Shared scaffolding (`_research_utils.py` for entry-list checks)
  lives alongside as a private module.
- **`/scripts/tests/`**: gate-internal infrastructure that exists ONLY
  to support the pre-commit chain — the orchestrator (`pre-commit.sh`)
  plus its internal regression tests (`help-check.sh`, `smoke.py`,
  `test_stopwords.py`, `skills-check.sh`, `file-size-check.sh`,
  `cookies-check.sh`). No
  contributor invokes these directly; the directory is the gate chain's
  private toolkit.
- **`/scripts/lib/`**: shared cross-cutting helpers (`_common.py`)
  imported by scripts in `build/` and `tools/` and by the per-check
  modules in `checks/`. Kept separate so the cross-script lockstep
  guarantee — the verbatim-quote check, prose-drift check, and
  description-drift check all extracting source bytes through the
  same `extract_source_text` and tokenizing through the same
  `STOPWORDS` set — is mechanical rather than comment-discipline-
  based. Also carries the markdown helpers (`parse_frontmatter`,
  `extract_h2_sections`, `extract_section`).
- **`/scripts/scratch/`**: contributor landing zone for in-progress
  exploratory queries against the corpus — one-off scripts that
  answer questions like "which manifest entries lack X," "count
  nodes where archetype = Y," "find videos on disk not in the
  manifest." Contents are gitignored (`.gitignore` tracks only
  itself); the directory exists so new sessions have a known home
  for ad-hoc scripts. When a query class repeats across sessions,
  graduate it to `tools/` as a proper subcommand or standalone tool
  — the scratch tier is the bridge between zero-investment inline
  scripting and the first-class CLI surface, not a permanent home.

The split between `build/` and `tools/` is along produces/transforms
vs assists. `build/` contains scripts that scaffold, render, or
validate the repository content layer (the pipeline that produces
node bodies from artifacts, plus the validators that gate each
phase). `tools/` contains standalone utilities that don't transform
content — they sync the manifest, archive sources, download
transcripts, or report read-only diagnostic information.

New scripts follow the rule: contributor invocation transforming
content → `build/`; contributor invocation that's utility /
integration / diagnostic → `tools/`; per-check module → `checks/`;
gate-only support code → `tests/`; shared helper code → `lib/`;
in-progress exploratory query → `scratch/`. The no-loose-scripts
rule (every script in exactly one subdir) keeps the top of
`scripts/` scannable as six role-labeled directories rather than a
flat heap.

#### Inside `/meta/` — root vs subdirs

`/meta/` itself follows a sub-rule that grew implicitly and is
codified here. New governance items land at the tier that matches
their character:

- **Root** (`meta/conventions.md`, `meta/schema.yaml`,
  `meta/sources-access.md`, `meta/BACKLOG.md`, `meta/roadmap.md`):
  stable governance specs and forward-looking work registers — the
  rules and the active agenda. A contributor consults these at
  session start or when something on the work queue applies.
- **`meta/templates/`**: scaffolding templates, one per node type.
  Consumed mechanically by `scripts/build/new.py`; rarely read directly
  by contributors except when a new node type is being added.
- **`meta/topic/`**: topic-specific governance — the priority
  research queue, topic overview, in-progress contributor working
  notes.
- **`meta/research/`**: YAML research artifacts backing each content
  node — the structured fact layer. One artifact per content node
  (`meta/research/{slug}.yaml`); `target_node` declares the pointer
  to `/{type}/{slug}.md`. Edited by contributors during Phase I,
  consumed mechanically by `scripts/build/build-from-research.py`
  (Phase II) and validated by `scripts/build/validate-research.py`.
  Topic-
  specific in content but governance-neutral in shape — the schema
  governs the shape; the topic determines the entries.

The fork-boundary distinction is load-bearing: a contributor forking
the toolkit to a different investigation deletes `/meta/topic/`,
`/meta/research/`, and the content directories; everything else
under `/meta/` survives because everything else is topic-neutral
toolkit. Items therefore land at the right tier on first author —
topic-specific items in `/meta/topic/` (governance) or
`/meta/research/` (structured facts), toolkit-neutral items at
`meta/`-direct.

`meta/README.md` is a friendly-face index of the directory's
contents; this section is the rule of record.

### Working notes are a report, not a residue

An agent's — or contributor's — analysis, intermediate reasoning, and
findings are a **deliverable**: handed to the user, or returned up the
build pipeline as a handoff. They are never persisted into the
repository's durable surfaces. The repo records *what the sources say*
and *what the code does*; it does not record the working process that
produced either.

Three durable surfaces, three places working notes must not land:

- **Node bodies.** A rendered node (`people/*.md`, `organizations/*.md`,
  …) is renderer output, regenerated from its `meta/research/` artifact;
  it carries source-anchored content, not an agent's commentary about how
  that content was assembled. The `block_node_body_edit.sh` hook enforces
  this mechanically — bodies are not hand-edited at all.
- **Code comments.** Comments describe what the code does and the
  non-obvious why, not who changed it or what an audit found — see
  `### NO BANDAIDS rule` and `### What TO keep in comments` below.
- **Stray files.** No scratch notes, status logs, or "summary of this
  session" files committed to the tree.

Where the record actually lives: **git history** owns the narrative of
what changed and why (commit messages, PR descriptions).

For build work specifically, this is the mechanism the role pipeline
already runs on: each role returns a handoff stub to the orchestrator
rather than writing shared state (`prompts/topology.md`), and
`meta/memory.md` records the drive-builds-through-the-topology discipline
that keeps it that way.

### Comments describe code, not refactor history

Code comments describe what a function or script does and any
non-obvious why — invariants, layering rules, surprising behavior.
They do not carry refactor history. Specifically forbidden in comments:

- BACKLOG identifiers (`per BACKLOG C21`, `closes BACKLOG #3`)
- Commit hashes (`migrated at af5f789`, `per commit 60bb88d`)
- Dated audit notes (`2026-05-05 audit surfaced ...`,
  `corrected during this session`)
- Phase / cluster markers (F.5b, D.4, C17)
- Section blocks: `Origin: introduced at ...`, `Migration: ...`,
  `Anchor pattern: ...`
- "Previously X was Y; now Z" reframings of how the code evolved
- "Mirror X exactly" sync-discipline reminders for code that has
  since been centralized

The PR description and commit message are where the *why we changed
it* lives. The code comment is where the *why it is the way it is*
lives, and only when that why is non-obvious from the identifiers
and structure.

The same describe-current-state rule extends beyond comments to every
governance file — retiring a validator check, deleting a renderer
dispatch branch, removing a conventions section or an obsolete template:
the file describes current state and pending work, not past evolution.
Git log carries the evolution.

#### NO BANDAIDS rule

Any issue found during an audit either gets fixed immediately or
filed in BACKLOG for later. Never document the issue as a comment
in the affected code (`// known issue: X never fires under
condition Y`). The choices are: fix-now (preferred for mechanical
issues, missing checks, hygiene gaps) or BACKLOG-and-track (for
design questions, convention-level changes, items needing user
consensus). Comments are not a third option.

The carrying-cost concern is concrete. Comments referencing closed
BACKLOG entries become stale pointers when the entry is removed.
"Origin / Migration / Anchor pattern" docstrings accumulate as
refactor cycles compound, eventually drowning the description of
what the code currently does.

#### What TO keep in comments

Functional descriptions of what the code does, plus non-obvious
why notes that anchor on still-live concepts:

- `meta/conventions.md` section names (the convention is the
  durable contract)
- schema field paths — `meta/schema.yaml` for node types, or
  `meta/schema-research-artifact.yaml` for artifact fields (e.g.
  `schema-research-artifact.yaml::conditional_keys`, merged into
  `types.research-artifact` at parse time)
- `meta/roadmap.md` mentions when scoping a "not yet implemented"
  check
- Layering invariants (e.g., "presence-guard, not truthy — opens a
  gap with `frontmatter_required` if loosened")

Anchor comments on durable concepts. Avoid anchoring on transient
ones (specific commits, dated audits, phase markers).
