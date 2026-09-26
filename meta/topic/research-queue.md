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
