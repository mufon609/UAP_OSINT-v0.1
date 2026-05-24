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
| Puthoff–Targ "The Record" SRI daily log | SRI-internal daily log (location/archival TBD) — resolves the five-week-vs-eight-day SRI-tenure chronology | [`/people/uri-geller`] rumor r1 | Low | Pending |
| Uri Geller Museum opening-date primary source | Old Jaffa museum opening date (currently secondary-only "2021") — would graduate rumor r4 and populate affiliation a9 `period_start` | [`/people/uri-geller`] rumor r4 / affiliation a9 | Low | Pending |
| AARO→AIC budget-rebrand finding (Tier-3 finding-build; deferred — do not build without direction) | FY2024/2025/2026 OSD OP-5 submissions (archived): FY2024 named AARO, FY2025 first substituted "AIC", FY2026 retains it; no public DoD renaming announcement and aaro.mil remains active | note-residue audit (ousd-is entity layer must not carry the multi-year pattern) | Medium | Pending |

---

## Priority Build Queue

_Empty._

---

## Externally blocked

Items waiting on an external event the repo can't drive (FOIA resolution, registry access, third-party publication) — the topic-specific home for such items, per `meta/BACKLOG.md`.

- **FOIA 24-F-0266 (BlackVault appeal)** — release of the redacted portion of Christopher Mellon's June 11–13, 2023 Signal-message reply to Sean Kirkpatrick (the visible portions frame Grusch's allegations as "warrant[ing] investigation"). Resolves the open question on [`/investigations/lockheed-martin-uap-materials`]. Status: Blocked — pending BlackVault FOIA appeal resolution.
