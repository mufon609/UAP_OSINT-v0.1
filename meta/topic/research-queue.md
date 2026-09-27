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
| SASP incumbent: IEA/EverWatch order HQ003419F0506 (under TEAMS BPA HQ003415A0010): **substantially confirmed** | USAspending (`government/usaspending-hq003419f0506.txt`, `government/usaspending-hq003419f0506-transactions.txt`, archived 2026-09-26): F0506's recipient is "IAN EVAN & ALEXANDER CORP"; signed 2019-08-15; performance to 2026-05-27; $51,413,590.66 obligated. Its transactions from P00035 (2025-07-25, CHANGE ORDER) through P00040 (2026-04-01) carry the description "SENSITIVE ACTIVITIES AND SPECIAL PROGRAMS". The archived SAM.gov notice TR011720251116 names Booz Allen as the incumbent on the same task order (recipient mismatch; a corporate acquisition would explain it but is unsourced). **Would complete:** source the IEA → EverWatch → Booz Allen corporate history, and fetch the pre-2025 transactions to see whether F0506 was SASP support from the start. It would then warrant an IEA/EverWatch organization node. Synthesis: working note §2. | Claude-Web thread lead; USAspending ([`/organizations/arlo-solutions`], [`/organizations/ousd-is`]) | High | In-progress |
| Arlo's SASP call order HQ003425F0104 terminated for convenience vs. Arlo's March 2026 SASP award announcement: **answered; ingested 2026-09-26** | SASP was re-awarded to Arlo as **HQ003426FE011** (a child of BPA HQ003425A0004, which has exactly two child call orders, F0104 and FE011); the FE011 and incumbent F0506 records are archived (`government/usaspending-hq003426fe011.txt`, `-transactions.txt`, `government/usaspending-hq003425a0004-child-awards.txt`, `government/usaspending-hq003419f0506.txt`, `-transactions.txt`) and on the Arlo node. **Remaining:** (1) the FPDS reason-for-modification for F0104's P00004 (FPDS returned its "Site unavailable" maintenance page on 2026-09-26); (2) why Arlo's release says "more than $85 million" against FE011's $59,372,513.73 (recorded side by side, unreconciled). Synthesis: `meta/topic/working-notes/ousd-is-enterprise-bpa-transition.md` §2. | [`/organizations/arlo-solutions`] | High | In-progress |
| SAM.gov award notice names Premier for HQ003423C0061, which USAspending records as Sancorp's IPMO follow-on | Archived: `news/samdaily-fbo-06693814-hq003423c0061.html` (the SAMDaily republication of the award notice, 2023-05-27) names Premier Enterprise Solutions in its Description, while `government/usaspending-hq003423c0061.txt` gives recipient "SANCORP CONSULTING, LLC". Both are preserved as a contradiction on the Premier node. **Would resolve:** the original SAM.gov award notice record (not the republication) or the FPDS contract action report for HQ003423C0061, which names the awardee by UEI. | [`/organizations/premier-enterprise-solutions`], [`/organizations/sancorp-consulting`], [`/organizations/ipmo`] | Medium | Pending |
| Premier node: award record for its second call order HQ003426FE173 | HQ003426FE173 surfaced as a second Premier call order, unretrieved. (The incumbent contract HQ003422C0127 is done, ingested 2026-09-26: `government/usaspending-hq003422c0127.txt`, `-transactions.txt` and `government/fpds-hq003422c0127.txt` / `-start10.txt` show it ran 2022-09-28 to 2025-07-27, the completion date moved to 2025-07-27 by P00011 signed 2025-03-27, coinciding with the bridge in SAM.gov notice TR011720251116.) **Would add:** the USAspending/FPDS record for FE173 (agency, requiring office, dates, values, description), placing Premier's OUSD(I&S) work after the EXDIR order HQ003425F0105. | [`/organizations/premier-enterprise-solutions`] | Medium | Pending |
| Neill Tipton (DDI, Collection & Special Programs) and the DoD IG's UAP evaluation: FOIA 23-F-0377 / 23-F-0446 releases and OIG release DODOIG-2023-000021 | **Partly done (2026-09-26).** Built `foia/dod-23-f-0377` and `foia/dod-23-f-0446` from the FY23 FOID log rows (518, 620) and The Black Vault's two timeline posts; the request text and the posts are the requester's words. Archived but unquotable until the desktop OCR pass (BACKLOG C9): the 23-F-0446 package `government/foia-23-f-0446-final-response-tipton-oig-email.pdf` (p. 1 FOID final response of June 22, 2023, text-native: a DoD OIG referral under OIG case 2023-000420, one page reviewed, (b)(6), IDAs Paul M. Plescow of AARO and Searle Slutzkin of the DoD OIG, signed by Stephanie L. Carr; p. 2 the 2023-01-11 Tipton–OIG email, a scan), plus two screenshots: the 23-F-0377 calendar entry for 2021-10-19 and the DODOIG-2023-000021 email of 2021-11-04. **Not found:** the 23-F-0377 response letter and full release; the DODOIG-2023-000021 response letter and full release; the request letters as filed. Searched: documents2.theblackvault.com, theblackvault.com uploads and its timeline pages, Wayback CDX, the WHS UFOsandUAPs reading room, the DoD OIG UAP-records page and MuckRock. **Remaining:** after C9, `/augment` both foia nodes (correspondence, pages, exemptions, signer, released records); build `/foia/dodoig-2023-000021` if its letter surfaces; decide on `people/neill-tipton`, left unbuilt because every quotable source about him is the requester's. Synthesis: `meta/topic/working-notes/ousd-is-enterprise-bpa-transition.md` §4. | [`/organizations/ipmo`], [`/organizations/ousd-is`] | High | Blocked |
| IPMO support after HQ003424C0046 ends (2026-05-27) | HQ003424C0046's extension history is done, ingested 2026-09-26 on both nodes: FPDS (`government/fpds-hq003424c0046.txt`) shows P00002 (signed 2025-03-27) moved completion to 2025-07-27, the bridge period in SAM.gov notice TR011720251116, and P00006 (signed 2025-07-25) moved it to 2026-05-27; USAspending transactions (`government/usaspending-hq003424c0046-transactions.txt`) describe P00002–P00004 as "IPMO SUPPORT SERVICES". **Would add:** the Enterprise BPA call order, if any, that took over IPMO support after 2026-05-27. Synthesis: working note §3. | [`/organizations/ipmo`], [`/organizations/sancorp-consulting`] | Medium | Pending |
| Whether the Sensitive Activities & Special Programs (SASP) directorate is DDI (Collection & Special Programs) renamed | IPMO's placement is resolved: the OUSD(I&S) Organization page lists "Influence and Perceptional Management Office (IPMO)" (sic) under "Director for Defense Intelligence (DDI), Sensitive Activities & Special Programs (SASP)" (`government/ousdi-defense-gov-organization-wayback-20260420.html`, capture 2026-04-20). The 2022 IPMO PWS §1.2 placed IPMO under DDI(C&SP). Archived captures of the same page bracket the change: C&SP was last seen 2025-07-09 (`…-wayback-20250709.html`); SASP was first seen 2025-09-10 on the Directors missions page (`government/ousdi-defense-gov-ddi-wayback-20250910.html`) and 2025-09-12 on the Organization page (`…-wayback-20250912.html`). No capture shows both names, and no source states a rename. **Would confirm or refute:** a DoD issuance, OSD reorganization announcement or OP-5 narrative naming the change. Synthesis: working note §6. | [`/organizations/ousd-is`], [`/organizations/ipmo`] | Low | Pending |
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
