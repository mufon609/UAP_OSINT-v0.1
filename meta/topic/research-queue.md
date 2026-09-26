---
id: meta/topic/research-queue
type: meta
---

# Research Queue

Unconfirmed leads, secondary-source findings, and unbuilt stubs ordered by
priority — the **topic-specific** build backlog. (The toolkit-neutral
backlog lives in `meta/BACKLOG.md`.)

Two backlogs live here, distinguished by origin:

- **Queue** — leads with no `[/path]` reference in any built node yet
  ("here's a lead; no node home yet").
- **Priority Build Queue** — unbuilt stubs already referenced by built
  nodes (visible in `scripts/build/validate.py`'s broken-link registry),
  curated with priority + rationale.

## Discipline

- **Priority:** High / Medium / Low. **Status:** Pending / In-progress / Blocked.
- **Active items only.** When a queued item is built, delete its row — git
  log is the build-history record (`git log --diff-filter=A`).
- **Investigate before queueing.** Before adding an entry, confirm it meets
  the relevant `meta/schema.yaml` threshold and would launch with
  substantive density (Scope, Evidence, Build dependencies, Density math,
  Surfaced from). Don't mechanically transcribe audit / agent
  recommendations — that creates thin-shell risk.

---

## Queue

| Item | Source | Found In | Priority | Status |
|---|---|---|---|---|
| Uri Geller Museum opening-date primary source | Old Jaffa museum opening date (currently secondary-only "2021") — would populate affiliation a9 `period_start` | [`/people/uri-geller`] affiliation a9 | Low | Pending |
| SASP incumbent: IEA/EverWatch order HQ003419F0506 (under TEAMS BPA HQ003415A0010): **substantially confirmed** | USAspending (raw, fetched 2026-09-26, in `.scratch/drafts/contractor-postings-20260925/usaspending-sasp/`): F0506's recipient is "IAN EVAN & ALEXANDER CORP"; signed 2019-08-15; performance to 2026-05-27; $51,413,590.66 obligated. Its transactions from P00035 (2025-07-25, CHANGE ORDER) through P00040 (2026-04-01) carry the description "SENSITIVE ACTIVITIES AND SPECIAL PROGRAMS". The archived SAM.gov notice TR011720251116 names Booz Allen as the incumbent on the same task order (recipient mismatch; a corporate acquisition would explain it but is unsourced). **Would complete:** archive the F0506 records, source the IEA → EverWatch → Booz Allen corporate history, and fetch the pre-2025 transactions to see whether F0506 was SASP support from the start. It would then warrant an IEA/EverWatch organization node. Synthesis: working note §2. | Claude-Web thread lead; USAspending ([`/organizations/arlo-solutions`], [`/organizations/ousd-is`]) | High | In-progress |
| Arlo's SASP call order HQ003425F0104 terminated for convenience vs. Arlo's March 2026 SASP award announcement: **answered; ingest pending** | Answered by USAspending records fetched 2026-09-26 (raw, in `.scratch/drafts/contractor-postings-20260925/usaspending-sasp/`, not yet archived). SASP was re-awarded to Arlo as **HQ003426FE011** (a child of BPA HQ003425A0004; signed 2026-02-17; performance 2026-05-13 → 2026-11-27, potentially 2030-11-27; base and all options $59,372,513.73; description "…SENSITIVE ACTIVITIES AND SPECIAL PROGRAMS (SASP)"). The incumbent IEA/EverWatch order HQ003419F0506 carried SASP-labelled change orders from 2025-07-25 to its end on 2026-05-27. **Remaining:** (1) archive the FE011 and F0506 records into `sources/` and add them to the Arlo node; (2) the FPDS reason-for-modification for F0104's P00004 (FPDS was down when checked); (3) why Arlo's release says "more than $85 million" against FE011's $59.37M. Synthesis: `meta/topic/working-notes/ousd-is-enterprise-bpa-transition.md` §2. | [`/organizations/arlo-solutions`] | High | In-progress |
| SAM.gov award notice names Premier for HQ003423C0061, which USAspending records as Sancorp's IPMO follow-on | Archived: `news/samdaily-fbo-06693814-hq003423c0061.html` (the SAMDaily republication of the award notice, 2023-05-27) names Premier Enterprise Solutions in its Description, while `government/usaspending-hq003423c0061.txt` gives recipient "SANCORP CONSULTING, LLC". Both are preserved as a contradiction on the Premier node. **Would resolve:** the original SAM.gov award notice record (not the republication) or the FPDS contract action report for HQ003423C0061, which names the awardee by UEI. | [`/organizations/premier-enterprise-solutions`], [`/organizations/sancorp-consulting`], [`/organizations/ipmo`] | Medium | Pending |
| Premier node: award records for its incumbent contract HQ003422C0127 and its second call order HQ003426FE173 | SAM.gov notice TR011720251116 (archived) names Premier as incumbent on HQ003422C0127 and announces a sole-source bridge; the node has no award record for it. HQ003426FE173 surfaced as a second Premier call order, unretrieved. **Would add:** the USAspending/FPDS records for both (agency, requiring office, dates, values, descriptions), placing Premier's OUSD(I&S) work before and after the EXDIR order HQ003425F0105. | [`/organizations/premier-enterprise-solutions`] | Medium | Pending |
| Neill Tipton (DDI, Collection & Special Programs) and the DoD IG's UAP evaluation: FOIA 23-F-0377 / 23-F-0446 releases and OIG release DODOIG-2023-000021 | Archived: `government/whs-foid-foia-log-fy23.xlsx` (with its `.txt` sibling). Row 518, 23-F-0377 (The Black Vault; received 2023-01-19, closed 2023-06-23, "Granted / Denied in Part") seeks records of "a October 19, 2021, meeting between the DoD/OIG and Neill Tipton, OUSD, as revealed in FOIA case DODOIG-2023-000021", regarding the "Evaluation of the DoD's Actions Regarding the Unidentified Aerial Phenomena (Project No. D2021-DEV0SN-0116.000)". Row 620, 23-F-0446 (closed 2023-06-22, "Granted / Denied in Part") seeks Tipton's emails with the DoD OIG. The IPMO PWS §1.2 places IPMO under DDI(C&SP). **Would add:** the released records (likely published by The Black Vault), which put the meeting and its subject in the agency's own words. They would support two `foia` nodes and a `people/neill-tipton` node. Synthesis: `meta/topic/working-notes/ousd-is-enterprise-bpa-transition.md` §4. | [`/organizations/ipmo`], [`/organizations/ousd-is`] | High | Pending |
| IPMO contract HQ003424C0046: extension history and IPMO support after 2026-05-27 | Archived: `government/samgov-tr011720251116-notice.json` lists HQ003424C0046 among five incumbents "concluding on March 27, 2025", to be bridged to 2025-07-27 while the requirements go through the Enterprise BPA procurement. `government/usaspending-hq003424c0046.txt` nonetheless shows an end date of 2026-05-27. **Would add:** the C0046 transaction history (which modifications extended it, and when), and the Enterprise BPA call order, if any, that took over IPMO support. Synthesis: working note §3. | [`/organizations/ipmo`], [`/organizations/sancorp-consulting`] | Medium | Pending |
| Organizational link between DDI (Collection & Special Programs) and the Sensitive Activities & Special Programs (SASP) office | The IPMO PWS §1.2 (2022) places IPMO under DDI(C&SP). GAO B-422985.4/.5 (2025) names the SASP office as the recipient of call order 2. SASP's Arlo postings include influence, deception and perception-management staff officers. No archived source states whether SASP is C&SP's successor or a component of it. **Would confirm or refute:** an OSD OP-5 narrative, an OUSD(I&S) organization chart or directory, or a DoD issuance that places SASP and IPMO in the same directorate. Synthesis: working note §6. | [`/organizations/ousd-is`], [`/organizations/ipmo`] | Medium | Pending |
| AARO→AIC budget-rebrand finding (Tier-3 finding-build; deferred — do not build without direction) | FY2024/2025/2026 OSD OP-5 submissions (archived): FY2024 named AARO, FY2025 first substituted "AIC", FY2026 retains it; no public DoD renaming announcement and aaro.mil remains active | note-residue audit (ousd-is entity layer must not carry the multi-year pattern) | Medium | Pending |

---

## Priority Build Queue

| Item | Source | Found In | Priority | Status |
|---|---|---|---|---|
| The five unbuilt 23-F-0906 release documents — build **DD 254 first**, then contract, final RFQ, NDA-NPI, award notification: `/documents/foia-23-f-0906-sancorp-ipmo-{dd254,contract,final-rfq,nda-npi,award-notification}` | Archived under `sources/government/foia-23-f-0906-sancorp-ipmo-*.pdf` (WHS FOIA Reading Room, Contracts; 11 / 29 / 50 / 3 / 1 pp.). All five are `extraction_type: ocr-scan` with no sibling yet — each needs `/prepare-ocr-sibling` before any quote. The DD 254 is where the IPMO contract's (HQ003422C0064) classification and access requirements would become quotable (its block 1a and block 9 were read only off the unverified OCR layer during sourcing) | [`/foia/dod-23-f-0906`] `released_records` rr2–rr6 (attested by the Reading Room index) | Medium | Pending |

---

## Externally blocked

Items waiting on an external event the repo can't drive (FOIA resolution, registry access, third-party publication) — the topic-specific home for such items, per `meta/BACKLOG.md`.

- **FOIA 24-F-0266 (BlackVault appeal)** — release of the redacted portion of Christopher Mellon's June 11–13, 2023 Signal-message reply to Sean Kirkpatrick (the visible portions frame Grusch's allegations as "warrant[ing] investigation"). Resolves the open question on [`/investigations/lockheed-martin-uap-materials`]. Status: Blocked — pending BlackVault FOIA appeal resolution.
