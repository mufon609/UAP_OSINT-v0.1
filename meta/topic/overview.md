---
id: meta/topic/overview
type: meta
schema_version: 1
created: 2026-04-17
---

# Topic Overview — this instance

Required file for every toolkit instance. Describes the specific
investigation this repository is currently documenting. Deleted
(along with everything else in `meta/topic/`) when the toolkit is
forked for a different topic.

---

## Topic statement

*This instance investigates the UAP (Unidentified Anomalous
Phenomena) public record, with emphasis on primary-source-documented
U.S. government programs, congressional hearings, eyewitness and
whistleblower testimony, and the disclosure pipeline.*

---

## Scope boundaries

### In scope

- U.S. government UAP programs and offices (AAWSAP/AATIP, UAPTF,
  AARO, and predecessors) — primary-source documentation of their
  establishment, personnel, mandate, findings, and institutional
  record
- Congressional hearings on UAP and their primary-source transcripts
  and written testimony
- Declassified / FOIA-released government documents in the UAP record
- On-record public statements by named individuals (eyewitnesses,
  whistleblowers, officials, journalists) with documented UAP
  relevance
- Documented incidents (Nimitz 2004, Virginia Beach 2014–2015, etc.)
  with multi-source corroboration potential
- Journalism and book publications that enter the public-record
  discourse (stored as `document` nodes with `doc_form: article` or
  `doc_form: book`; publication records, not evidence of their claims)

### Out of scope

- Unverified claims and secondary-source summaries presented as fact
- Speculative theories without primary-source anchor
- Anonymous or pseudonymous claims without vouching primary source
- UAP-adjacent content (paranormal, cryptid, religious) unless
  documented as institutional activity (e.g., AAWSAP contract work
  at Skinwalker Ranch, which IS in scope because it's
  primary-source-documented institutional activity)
- Adjudication of origin or nature of reported objects — the
  repository documents what primary sources say; it does not
  adjudicate truth of underlying claims
- Real-time current events — the repository builds slowly after
  primary sources stabilize, not reactively

---

## Time period

Active coverage: 1947 (Roswell-era historical floor) through present.

Current focus period: 2017 (first modern public-record disclosure
via NYT / FLIR1 video) through present. Earlier content is built as
primary sources become available.

---

## Primary corpora

The principal primary-source collections this instance draws from:

1. **AAWSAP DIRD set** — 37 FOIA-released U/FOUO Defense Intelligence
   Reference Documents from the 2008–2012 DIA-managed AAWSAP program.
   Corpus addendum: `meta/topic/addenda/aawsap-dird.md`.
2. **Congressional hearings on UAP** — HPSCI (2022), SASC (2023,
   2024), House Oversight (2023, 2024, 2025). Each hearing produces
   an event node, per-witness written-testimony document nodes, and
   per-witness transcript nodes.
3. **Executive agency reports** — ODNI preliminary assessment
   (2021), AARO Historical Record Report Volume I (2024), NASA UAP
   Independent Study Team final report (2023), DoD IG reports.
4. **Primary-source video/footage** — FLIR1, Gimbal, GoFast, DoD
   acknowledgment statements.
5. **Journalistic record** — NYT 2017 coordinated disclosure, The
   Debrief 2023 Grusch disclosure, and subsequent investigative
   reporting.
6. **Named-individual on-record testimony and correspondence** —
   Reid letters, DIA memoranda, IC IG filings, etc.

---

## Agent orientation for this topic

Common query patterns for this instance:

- **"What did [person] say about [topic]?"** — search
  `research/*.yaml` for the person's entries; filter by topic keyword;
  return claims with source citations.
- **"Is [claim] supported by primary sources?"** — locate the claim in
  research artifacts; report the source, audit status, and any
  contradicting or superseding entries.
- **"What hearings / documents cover [event]?"** — traverse
  `/events/` for the event node; follow its Associated Nodes to
  related hearings, documents, and transcripts.
- **"What are open investigation threads?"** — read
  `meta/topic/research-queue.md` (priority queue) and scan
  `research/*.yaml` for unresolved research gaps.

When citing from this repo, reference the source (primary-source PDF
path from manifest) alongside the node narrative. A user asking "is
this true?" should be answered with both the repository's evidentiary
framing (Confirmed / Sworn testimony / Disputed / Contradicted) and a
direct pointer to the primary source so the user can verify
independently.

---

## Build-state snapshot

See `CLAUDE.md` auto-generated section for current node counts and
statuses per type.

---

## Research queue (this topic)

See `meta/topic/research-queue.md` for prioritized investigation
leads and unbuilt-stub backlog specific to this instance.
