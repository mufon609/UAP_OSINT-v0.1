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
  names Booz Allen as the incumbent on the same task order
  (`government/usaspending-hq003419f0506.txt`,
  `government/usaspending-hq003419f0506-transactions.txt`).
- **[E]** SASP was **re-awarded to Arlo** as HQ003426FE011, a child of BPA
  HQ003425A0004. It was signed 2026-02-17; its period of performance is
  2026-05-13 → 2026-11-27, potentially to 2030-11-27; base and all options
  are $59,372,513.73; $5,694,229.63 is obligated. The description reads
  "…OUSW(IS)SENSITIVE ACTIVITIES AND SPECIAL PROGRAMS (SASP)". A0004 has
  exactly two child orders, F0104 and FE011
  (`government/usaspending-hq003426fe011.txt`,
  `government/usaspending-hq003426fe011-transactions.txt`,
  `government/usaspending-hq003425a0004-child-awards.txt`).
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
- **[E]** IPMO's standalone contract HQ003424C0046 was on the March 2025
  bridge list, yet its USAspending record runs to **2026-05-27**
  (`government/usaspending-hq003424c0046.txt`). The FPDS record
  (`government/fpds-hq003424c0046.txt`) shows how: P00002 (signed
  2025-03-27, change order) moved completion from 2025-03-27 to 2025-07-27,
  the announced bridge period; P00006 (signed 2025-07-25, change order) moved
  it to 2026-05-27. The USAspending transactions
  (`government/usaspending-hq003424c0046-transactions.txt`) describe
  P00002–P00004 as "IPMO SUPPORT SERVICES". **[O]** What carries IPMO
  support after 2026-05-27 is still open.

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
  Both are now built as `foia/dod-23-f-0377` and `foia/dod-23-f-0446`. The log
  cells (tracking number, requester, received/closed dates, disposition) are
  0377 q1 / 0446 q1. The requester's text is 0377 q2–q6 / 0446 q2–q5.
- **[E, requester-published]** The Black Vault's timeline posts
  (`news/blackvault-timeline-oig-meets-tipton-20211019.html`,
  `news/blackvault-timeline-oig-reaches-out-tipton-again-20230111.html`) say:
  - under DODOIG-2023-000021 the OIG "met with Neill Tipton, Director for
    Defense Intelligence, Collection and Special Programs" (0377 q7);
  - 23-F-0377 released "the actual calendar details in the files of Mr.
    Neill Tipton" (0377 q9);
  - under 23-F-0446 the OIG "reached out to Neill Tipton … as OSD/JS" about
    the same evaluation (0446 q7–q8).

  All of this is the requester's account of the releases, not agency text.
- **[E, unquoted]** The 23-F-0446 final response is p. 1 of
  `government/foia-23-f-0446-final-response-tipton-oig-email.pdf`. That page is
  text-native, but the file is flagged `ocr-scan` because p. 2 is a scan, so
  nothing on it is quoted in a node until BACKLOG C9. The letter says:
  - FOID wrote on June 22, 2023, signed by Stephanie L. Carr, Chief.
  - FOID received the request, a January 18, 2023 Privacy Act/FOIA request,
    from the DoD OIG on February 14, 2023. It was a referral, under OIG case
    number 2023-000420.
  - OUSD(I&S) and the DoD OIG reviewed a one-page document and withheld
    portions under (b)(6).
  - The Initial Denial Authorities were Paul M. Plescow, "Chief of Staff,
    All-domain Anomaly Resolution Office (AARO), (OUSD(I&S))", and Searle
    Slutzkin, the DoD OIG's Division Chief FOIA.

  The log records the same case only as received by "E-mail" on 2023-02-14.
- **[O]** The agency's own record of the 2021-10-19 meeting is not yet readable
  here. Two Black Vault screenshots are archived but have no text layer and no
  verified sibling (BACKLOG C9):
  - `government/foia-23-f-0377-tipton-calendar-20211019-bv-excerpt.png`, the
    23-F-0377 calendar entry;
  - `government/foia-dodig-2023-000021-oig-email-20211104-bv-excerpt.jpg`, the
    2021-11-04 OIG email.

  The archive role's visual reads, in their manifest notes, say that:
  - Tipton organized the meeting with OIG Assistant Inspector General Randy
    Stone;
  - it concerned the OIG's UAP evaluation;
  - the email's subject line gives an OIG project number.

  None of this is verified. The project number is printed three ways across the
  sources: "D2021-DEV0SN-0116.000" in the log, "D2021-DEV0SAN-0116" in the JPG
  (visual read) and "D2021-DEVOSN-0116.000" in the 0446 OCR layer.
- **[O]** No found source ties the project to the published report. The
  archived DODIG-2023-109 unclassified summary
  (`government/media-defense-gov-dodig-2023-109-unclassified-summary.pdf`) is
  titled "… Unidentified Anomalous Phenomena", not "Aerial", and prints no
  project number.
- **[I]** In October 2021, the official over the directorate that later
  housed IPMO (established 2022-03-01) was OUSD(I&S)'s point of contact for
  the DoD IG's UAP evaluation. The OIG contacted him again in January 2023.
  By June 2023, AARO's Chief of Staff acted as OUSD(I&S)'s Initial Denial
  Authority on that correspondence. The IDA wording is verbatim on page 1 of
  `government/foia-23-f-0446-final-response-tipton-oig-email.pdf`, which
  has a clean text layer. It can be quoted once C9 produces the file's
  verified sibling.

  **Two readings of the IDA assignment:**
  - **(a)** FOIA review usually goes to the component with an interest in
    the records. On that reading, OUSD(I&S) treated Tipton's correspondence
    with the IG as within AARO's UAP remit.
  - **(b)** AARO's Chief of Staff may simply have been a designated IDA for
    OUSD(I&S) in general, whatever the subject.

  To tell them apart, look at other OUSD(I&S) FOIA responses from 2023: if
  Plescow signs as IDA on non-UAP records, (b) holds; if only on UAP
  records, (a). The agency's words for the meeting itself
  await C9. `people/neill-tipton` is not built: every quotable source about him
  is still the requester's.

## 5. What SASP is, from its own hiring [E]

Arlo's Greenhouse postings for OUSD(I&S) describe these staff lines. The
24 that name the SASP office or its HUMINT & Sensitive Activities
Directorate are archived as `news/arlo-greenhouse-{req}-*-wayback-*.html`
(Wayback raw captures; e.g. `news/arlo-greenhouse-499-reports-and-assessments-staff-officer-i-wayback-20260227.html`
for SA-EXCON, `news/arlo-greenhouse-510-c-wmd-staff-officer-i-wayback-20260227.html`
for Title 50, `news/arlo-greenhouse-514-influence-deception-perception-mgmt-staff-officer-v-wayback-20260804.html`),
and the load-bearing passages are quoted on `organizations/arlo-solutions`.
Twelve name SASP (182, 183, 467, 498, 502, 504, 505, 510, 512, 514, 516 and
the "OUSD(I&S) SASP Incumbent" post); the other twelve name only the HUMINT &
Sensitive Activities Directorate (495–497, 499–501, 506, 507, 509, 511, 666,
667) and do not themselves say the directorate sits in SASP. The C-WMD
postings (510, 512) place their directorate "within the Sensitive
Activities & Special Programs (SASP) Office". Two lines below come from the same 2025-02-24
requisition batch but name their own OUSW(I&S) directorates, not SASP, and
are not archived locally: functional intelligence and defense analysis (515,
`web.archive.org/web/20260227082536/https://job-boards.greenhouse.io/arlosolutionsllc/jobs/4660833007`)
and national programs and policy support (508, `…/jobs/4660772007`, same
capture timestamp).

**[E] The Organization page lists SASP's units.** The OUSD(I&S) Organization
page (`government/ousdi-defense-gov-organization-wayback-20260420.html`,
Wayback capture 2026-04-20, lines 247–252; the same list is in
`government/ousdi-defense-gov-organization-wayback-20250912.html`, lines
252–257) names five units under "Director for Defense Intelligence (DDI),
Sensitive Activities & Special Programs (SASP)":

- Strategic Coordination Program Management Office
- Special Programs
- HUMINT & Sensitive Activities
- National Programs & Policy Support
- "Influence and Perceptional Management Office (IPMO)" (sic)

Several staff lines above match these units:

- The HUMINT & Sensitive Activities Directorate is named by the twelve
  postings that do not themselves mention SASP (e.g. 499,
  `news/arlo-greenhouse-499-reports-and-assessments-staff-officer-i-wayback-20260227.html`
  line 3). The page lists "HUMINT & Sensitive Activities" under SASP (line
  250).
- The page lists "National Programs & Policy Support" under SASP (line 251).
  Posting 508 names that line's directorate without naming SASP, and 508 is
  not archived locally.
- The influence, deception and perception-management postings match the
  IPMO line (line 252).

Two lines do not match:

- The "Functional Intelligence & Defense Analysis Directorate" (515) is
  listed under DDI PREM, not SASP (line 243).
- The C-WMD postings (510, 512) put the "Counter Proliferation and Weapons
  of Mass Destruction Directorate within the Sensitive Activities & Special
  Programs (SASP) Office" (`news/arlo-greenhouse-510-c-wmd-staff-officer-i-wayback-20260227.html`
  line 3). The page lists no WMD unit under SASP. Its only WMD line, "Weapons
  of Mass Destruction Deterrence", sits under DDI OSIP (line 268).

The two records are recorded side by side, not reconciled.

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
4660812007, SME IV, text at
`meta/topic/incidents/2026-09-24-wayback-capture-loss/evidence/local-copies/job-text/job-4660812007.txt`;
job 4660820007, SME V, `news/arlo-greenhouse-514-*`), **three days after
F0104's award**. They belong to SASP's own
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

**[E]** IPMO sits under SASP. The OUSD(I&S) Organization page lists
"Influence and Perceptional Management Office (IPMO)" (sic) under
"Director for Defense Intelligence (DDI), Sensitive Activities & Special
Programs (SASP)":

- 2026-04-20 capture: `government/ousdi-defense-gov-organization-wayback-20260420.html`,
  lines 247 and 252;
- earliest capture with SASP, 2025-09-12:
  `government/ousdi-defense-gov-organization-wayback-20250912.html`, lines
  252 and 257, headed "Director of War Intelligence (DWI)".

The same page lists "All-domain Anomaly Resolution Office" under "Direct
Report Offices" (2026-04-20 capture, lines 273–274; 2025-09-12 capture,
lines 280–281).

**Dating the structure.** The Wayback captures of the same page bracket the
change:

- Every capture read from 2022-08-11 to 2025-07-09 lists a "Director for
  Defense Intelligence (Collection & Special Programs)", with Technical
  Collection, HUMINT & Sensitive Activities and Special Programs under it.
  None lists IPMO or AARO anywhere. The captures read and archived are
  `…-wayback-{20220811,20230112,20240417,20250709}.html`; in the 2025-07-09
  capture the C&SP line is at line 279.
- C&SP is last seen on 2025-07-09. SASP is first seen on 2025-09-10, on the
  Directors missions page (`government/ousdi-defense-gov-ddi-wayback-20250910.html`),
  and on 2025-09-12 on the Organization page.
- Wayback holds no capture of either page between those dates.

No capture shows both names, and no found source says SASP is C&SP renamed.

**[O]** Whether SASP is C&SP renamed or a new directorate. Both carry
"Special Programs" and "HUMINT & Sensitive Activities". IPMO was placed
under DDI(C&SP) in the 2022 PWS, but the C&SP-era page never lists it.

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
   Tipton and the IG UAP evaluation in the agency's own words (§4). Partly
   done: both foia nodes are built. The agency text is archived but waits on
   the BACKLOG C9 OCR pass.
3. IPMO's post-May-2026 support (§3). HQ003424C0046's extension history is
   answered from FPDS and ingested on `organizations/ipmo` and
   `organizations/sancorp-consulting`.
4. Whether SASP is DDI(C&SP) renamed (§6). IPMO's placement under SASP is
   answered from the OUSD(I&S) Organization page. The captures bracket the
   change between 2025-07-09 and 2025-09-10, but no source states a rename.
