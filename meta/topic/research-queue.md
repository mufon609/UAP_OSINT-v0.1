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
| Possible SASP incumbent: order HQ0034-19-F-0506, "Specialized and Sensitive Administrative, Budget, Policy, Operations, and Analytic Support" — reported as awarded to Ian, Evan & Alexander Corporation (IEA), later EverWatch, now Booz Allen; reported as extended past a September 28, 2024 expiry while its replacement was in evaluation, with a protest filed September 25, 2024. Unverified: the SASP link rests only on title similarity to Sancorp's IPMO PWS title ("Specialized and Sensitive Administrative, Security, Policy, Operations, and Analytic Support Services" — [`/organizations/sancorp-consulting`] q35, the April 25, 2022 IPMO PWS title block) | Partial (archived): SAM.gov notice TR011720251116 (`sources/government/samgov-tr011720251116-notice.json`, posted 2025-03-11) lists Booz Allen Hamilton's "WHS-AD TEAMS BPA, HQ003415A0010, Task Order HQ003419F0506" among five OUSD(I&S) I&S Enterprise incumbent contracts ending March 27, 2025, to be bridged to July 27, 2025 (FAR 8.405-6) because the requirements are "going through the procurement process" under the OUSD(I&S) Enterprise BPA — the notice names neither SASP nor HQ003424R0178. Claude-Web thread leads (no URLs given): an OrangeSlices notice and a SAM.gov limited-source justification for the HQ0034-19-F-0506 extension; the USAspending award record for HQ0034-19-F-0506. **Would confirm:** the SAM.gov justification or USAspending record naming solicitation HQ003424R0178 (the SASP/EXDIR RFQ) as the replacement, or naming the OUSD(I&S) SASP office as the requiring office; **would refute:** a different requiring office or replacement solicitation | Claude-Web thread on Sancorp/Arlo SASP competition ([`/organizations/arlo-solutions`], [`/organizations/ousd-is-sasp`]) | Medium | Pending |
| Arlo's SASP call order HQ003425F0104 terminated for convenience vs. Arlo's March 2026 SASP award announcement | Archived: `government/usaspending-hq003425f0104-transactions.txt`. P00003 (2025-07-28) deobligates the full $6,327,156.07 and relabels the scope "…SUPPORT TO THE EXECUTIVE DIRECTORATE"; P00004 (2025-08-19) is "TERMINATE FOR CONVENIENCE (COMPLETE OR PARTIAL)". The award record still shows end_date 2026-03-27. Arlo's 2026-03-16 press release (`news/arlo-press-85m-sasp-20260503.html`) announces a "more than $85 million" SASP contract. **Would confirm a replacement vehicle:** a later Arlo call order under BPA HQ003425A0004 (USAspending/FPDS search of Arlo awards after 2025-08) whose description or requiring office names SASP. **Would explain the termination:** the FPDS record for P00004 (reason-for-modification fields). | [`/organizations/arlo-solutions`] (F0104 contract row, transactions) | High | Pending |
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
