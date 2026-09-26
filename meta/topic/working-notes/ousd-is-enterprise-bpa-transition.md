---
id: meta/topic/working-notes/ousd-is-enterprise-bpa-transition
type: meta
status: working-notes
integration_targets:
  - /organizations/ousd-is
  - /organizations/arlo-solutions
  - /organizations/sancorp-consulting
  - /organizations/premier-enterprise-solutions
  - /organizations/ipmo
  - /organizations/aaro
  - /people/neill-tipton
  - /foia/dod-23-f-0377
  - /foia/dod-23-f-0446
  - /findings/ousd-is-enterprise-bpa-consolidation
---

# OUSD(I&S) support contracts: the move to the Enterprise BPA, and where IPMO and AARO sit in it

**Synthesis, not a primary source.** This note joins archived records into a
working account of how OUSD(I&S)'s contractor support was restructured from
2025 on, and what that shows about the offices that handle influence,
deception and perception management (IPMO) and UAP (AARO). Every claim points
to an archived file under `sources/`. Labels:

- **[E]** established by the cited records;
- **[I]** inference;
- **[O]** open question.

Written 2026-09-26.

---

## 1. One competed vehicle replaced office-by-office sole-source contracts [E]

- On 2025-02-14 WHS established four OUSD(I&S) Enterprise BPAs under
  solicitation HQ003424R0178: HQ003425A0001 (Sancorp), A0002 (Comprehensive
  Approach), A0003 (Premier) and A0004 (Arlo). They are recorded on the org
  nodes with their USAspending IDV records.
- SAM.gov notice TR011720251116, posted 2025-03-11
  (`government/samgov-tr011720251116-notice.json`), announces four-month
  sole-source bridges, 2025-03-28 to 2025-07-27, for **five** incumbent
  contracts, all "concluding on March 27, 2025":

  | # | Incumbent | Contract |
  |---|---|---|
  | 1 | Booz Allen | TEAMS task order HQ003419F0506 |
  | 2 | Booz Allen | HQ003424C0050 |
  | 3 | Digital Forensics Services | HQ003421C0050 |
  | 4 | Sancorp | **HQ003424C0046, the IPMO support contract** |
  | 5 | Premier | HQ003422C0127 |

  The notice gives the reason: "the Government has established an Enterprise
  Blanket Purchase Agreement for OUSD (I&S), and the requirements are going
  through the procurement process for award."
- Call orders under the BPAs then took over standalone work:
  - EXDIR: Premier HQ003425F0105, 2025-02-21 (`government/usaspending-hq003425f0105.txt`);
  - SASP: Arlo HQ003425F0104, 2025-02-21 (see §2);
  - OUSD(AT&L)-funded work: Sancorp HQ003425FE174, 2025-06-20;
  - CL&S: Sancorp HQ003425FE388, 2025-09-11 (`government/usaspending-hq003425fe388-20260926.txt`);
  - Sancorp HQ003426FE050, 2026-01-28 (`government/usaspending-hq003426fe050.txt`); see §3.
- **Consequence [E/I]:** support for EXDIR, SASP, CL&S and, very probably,
  AARO now runs through one competed vehicle. It has four vendors, one
  funding office ("OSD OUSD(I)" on the award records) and overlapping WHS
  contracting staff.

## 2. SASP: the first award never performed; the incumbent kept SASP until Arlo's second award took over in May 2026 [E]

- **[E]** Arlo's SASP order F0104 and Premier's EXDIR order F0105 were signed
  the same day, 2025-02-21. **F0105 performed.** Obligations accumulate, an
  option was exercised on 2025-12-26 for $10,466,026.20, and $16.66M is
  obligated to date (`government/usaspending-hq003425f0105-transactions.txt`).
- **[E]** F0104 ended with **$0 net obligation**
  (`government/usaspending-hq003425f0104-transactions.txt`):
  - P00003 (2025-07-28) deobligated the full $6,327,156.07, **one day after
    the bridge period ended**;
  - P00004 (2025-08-19) is "TERMINATE FOR CONVENIENCE (COMPLETE OR PARTIAL)";
  - the award record still shows end_date 2026-03-27.
- **[E→I]** The "…SUPPORT TO THE EXECUTIVE DIRECTORATE" description on F0104
  from P00003 on is **not evidence of a SASP-to-EXDIR re-scope.** F0105
  received the identical new description in its P00004 on 2025-07-25. Both
  records were rewritten by the same office within three days.
- **[E]** GAO B-422985.4/.5 (2025-06-11) dismissed Sancorp's SASP challenge
  and denied its EXDIR challenge (`government/gao-b-422985-wayback-20250708.html`).
  GAO held that "because Sancorp had actual knowledge of the unavailability
  of X, the protester was obligated to advise the agency."
- **[E]** SASP support stayed with the incumbent, IEA (later EverWatch),
  after the bridge. Its order HQ003419F0506 (under TEAMS BPA HQ003415A0010;
  "ADMINISTRATIVE AND ANALYTICAL SUPPORT") was never cut off at 2025-07-27.
  From 2025-07-25 its transactions carry the description **"SENSITIVE
  ACTIVITIES AND SPECIAL PROGRAMS"**:

  | Date | Mod | Action | Amount |
  |---|---|---|---|
  | 2025-07-25 | P00035 | CHANGE ORDER | $1,977,626.47 |
  | 2025-09-02 | P00036 | SUPPLEMENTAL AGREEMENT FOR WORK WITHIN SCOPE | $4,127,105.22 |
  | 2025-09-16 to 2026-04-01 | P00037–P00040 | FUNDING ONLY ACTION | ≈$0.96M in total |

  Its period of performance runs to **2026-05-27**. USAspending records the
  recipient as "IAN EVAN & ALEXANDER CORP"; the March 2025 bridge notice
  names Booz Allen as the incumbent on the same task order. (Raw USAspending
  responses, fetched 2026-09-26 and not yet archived in `sources/`:
  `.scratch/drafts/contractor-postings-20260925/usaspending-sasp/usaspending-award-HQ003419F0506-*.json`
  and `usaspending-hq003419f0506-transactions-*.json`.)
- **[E]** SASP was **re-awarded to Arlo** as HQ003426FE011, a child of BPA
  HQ003425A0004. It was signed 2026-02-17; its period of performance is
  2026-05-13 → 2026-11-27, potentially to 2030-11-27; base and all options
  are $59,372,513.73; $5,694,229.63 is obligated. The description reads
  "…OUSW(IS)SENSITIVE ACTIVITIES AND SPECIAL PROGRAMS (SASP)". A0004 has
  exactly two child orders, F0104 and FE011. (Raw:
  `…/usaspending-sasp/usaspending-award-HQ003426FE011-*.json`,
  `usaspending-hq003426fe011-transactions-*.json`,
  `usaspending-idv-children-HQ003425A0004-fixed-*.json`; not yet archived.)
- **[E + I]** The sequence of events:

  | Date | Event |
  |---|---|
  | 2025-07-25 | F0506 gets a SASP change order |
  | 2025-07-27 | The bridge period ends |
  | 2025-07-28 | F0104 is fully deobligated |
  | 2025-08-19 | F0104 is terminated for convenience |
  | 2026-02-17 | FE011 is signed |
  | 2026-02-18 | Arlo posts its "OUSW (I&S) SASP Incumbent" job, which fits capture of F0506's staff [I] |
  | 2026-05-13 | FE011 performance begins |
  | 2026-05-27 | F0506 ends |

  The job posting (Greenhouse job 5055636007) is in the board snapshot
  `meta/topic/incidents/2026-09-24-wayback-capture-loss/evidence/local-copies/board-20260924T023141Z.json`.
  The whole sequence shows the government keeping the incumbent on SASP
  and re-issuing the SASP order to Arlo, rather than transitioning to F0104.
- **[O]** Why F0104 was terminated and re-issued rather than started. FPDS
  was unavailable when checked, so no reason-for-modification text is in
  hand; USAspending gives only "TERMINATE FOR CONVENIENCE (COMPLETE OR
  PARTIAL)".
- **[O]** Why Arlo's 2026-03-16 release says "more than $85 million"
  (`news/arlo-press-85m-sasp-20260503.html`) when FE011's base and all
  options are $59,372,513.73.
- **[O]** The IEA versus Booz Allen recipient mismatch on F0506. A
  corporate acquisition would explain it; no source for that is archived.

## 3. The contractor map was reshuffled [E + I]

- **Sancorp**, all [E] except where marked:
  - lost the SASP competition;
  - gained FE174 (Jun 2025) and CL&S FE388 (Sep 2025);
  - very probably gained the **AARO** follow-on FE050 (Jan 2026) [I, strong].
    The FE050 services description appears verbatim in Sancorp requisition
    1258, which is "in direct support to Research, Development, Test &
    Evaluation Activities within … (OUSW(I&S)) All-Domain Anomaly Resolution
    Office (AARO)" (`news/sancorp-adp-req1258-staff-officer-iii-20260925.json`).
    FE050 started 2026-01-28, three days before Sancorp's AARO contract
    HQ003424C0096 ended (2026-01-31). Arlo's AARO key-personnel postings,
    617 and 619 (`news/arlo-greenhouse-617-*`, `news/arlo-greenhouse-619-*`),
    were live 2025-12-17 to 2026-01-19. FE050 drew 4 offers, and Arlo holds
    one of the four BPAs.
- **Arlo** [E]: its CL&S orders HQ003422F0271, HQ003423F0356 and HQ003424F0190
  all end in April 2026 (see the `arlo-solutions` contracts table), **after**
  Sancorp's CL&S order FE388 began.
- **[I, moderate]** CL&S moved from Arlo to Sancorp while SASP moved to Arlo.
  The subject areas match, but no record links the orders.
- **[O]** IPMO's standalone contract HQ003424C0046 was on the March 2025
  bridge list, yet its USAspending record runs to **2026-05-27**
  (`government/usaspending-hq003424c0046.txt`). How was it extended, and what
  carries IPMO support now?

## 4. IPMO's chain of command meets UAP oversight [E, requester-described]

- **[E]** The IPMO PWS §1.2 places IPMO under the Director for Defense
  Intelligence (Collection and Special Programs), DDI(C&SP)
  (`government/foia-23-f-0906-sancorp-ipmo-pws.pdf`; quoted on `ipmo` as
  q6/q7, which match the page images). IPMO's remit includes deception,
  perception management and "reveal/conceal".
- **[E, requester-described]** The WHS FOID FY23 FOIA log
  (`government/whs-foid-foia-log-fy23.xlsx`, with its `.txt` sibling)
  records two requests by The Black Vault, both "Granted / Denied in Part":
  - **Row 518, 23-F-0377** (received 2023-01-19, closed 2023-06-23), for
    records of "a October 19, 2021, meeting between the DoD/OIG and Neill
    Tipton, OUSD, as revealed in FOIA case DODOIG-2023-000021 … regarding
    the Evaluation of the DoD's Actions Regarding the Unidentified Aerial
    Phenomena (Project No. D2021-DEV0SN-0116.000)".
  - **Row 620, 23-F-0446** (received 2023-02-14, closed 2023-06-22), for all
    emails between the DoD OIG and "Neill Tipton, Director for Defense
    Intelligence, Collection and Special Programs" (2022-01-01 to 2023-02-10).
- **[I]** In October 2021, the official over the directorate that later
  housed IPMO (established 2022-03-01) was OUSD(I&S)'s point of contact for
  the DoD IG's UAP evaluation. The meeting description is the requester's,
  citing an OIG release; the agency's own words are not yet in hand.
  Neill Tipton has no node.

## 5. What SASP is, from its own hiring [E]

Arlo's SASP postings (177 Wayback captures, summarized in
`.scratch/drafts/contractor-postings-20260925/arlo-wayback-history/summary.csv`,
parked under BACKLOG C6) describe these staff lines:

- special operations support policy
- HUMINT policy
- sensitive activities policy
- countering adversary defense industry
- counter-WMD (Title 50)
- functional intelligence and defense analysis
- national programs and policy support
- influence, deception and perception management (SME IV/V)
- reports and assessments, supporting the **Sensitive Activities Executive
  Council (SA-EXCON)**

Several of these roles produce reports for Congress. The influence,
deception and perception management postings date from 2025-02-24 (job
4660812007), **three days after F0104's award**. They belong to SASP's own
remit and were not a reaction to IPMO's contract ending.

## 6. What this does not show

No record in hand shows influence, deception or perception-management
activity directed at UAP matters. What is now documented is **structural
proximity**:

- one parent, OUSD(I&S);
- one contract vehicle;
- shared vendors (Sancorp supported both IPMO and AARO);
- one funding office;
- a DDI(C&SP) over IPMO who met the IG about its UAP evaluation.

**[O]** Whether IPMO sits under SASP. The DDI(C&SP)/SASP link rests on
naming ("Special Programs") and overlapping functions; no organizational
document states it.

## 7. Evidence-handling lessons from these sources

- Federal systems disagree. A SAM.gov award notice (SAMDaily republication
  `news/samdaily-fbo-06693814-hq003423c0061.html`) names Premier for
  HQ003423C0061, which USAspending gives to Sancorp. Cross-check two
  systems before relying on a recipient or description.
- FPDS descriptions are edited administratively, as the F0104/F0105 July
  2025 relabelling shows. A description change is not proof of a scope
  change.
- The Claude-web thread that surfaced several of these leads made six
  factual errors (see the `premier-enterprise-solutions`, `aaro` and
  `sean-kirkpatrick` corrections). It is a lead generator, not a source.

## 8. Next moves (tracked in `meta/topic/research-queue.md`)

1. Archive the FE011 and F0506 USAspending records into `sources/`, and add
   them to `organizations/arlo-solutions` (and a future IEA/EverWatch node)
   (§2). The FPDS termination reason for F0104 P00004 is still to fetch.
2. The 23-F-0377 and 23-F-0446 releases and OIG release DODOIG-2023-000021:
   Tipton and the IG UAP evaluation in the agency's own words (§4).
3. HQ003424C0046's transaction history and IPMO's post-May-2026 support (§3).
4. An organizational source linking DDI(C&SP) and the SASP office (§6).
