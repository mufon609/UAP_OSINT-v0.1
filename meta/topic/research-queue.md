---
id: meta/topic/research-queue
type: meta
schema_version: 1
created: 2026-04-17
---

# Research Queue

Unconfirmed leads, secondary-source findings, and unbuilt stubs ordered
by priority.

Two backlogs live here, distinguished by origin:

- **Queue** (top) — leads that don't yet have a `[/path]` reference in
  any built node. These are "here's a lead; no node home yet."
- **Priority Build Queue** — unbuilt stubs that are already referenced
  by built nodes (visible in `scripts/validate.py` broken-link
  registry), curated here with priority and rationale.

Do not add here anything that already has a home in a node's Open
Questions section. Open Questions are gaps *within* a node; this file
is for leads that don't fit in any existing node yet.

---

## Formatting rules

- **Priority values:** High, Medium, Low
- **Status values:** Pending, In-progress, Blocked
- **Active items only.** When a queued item is built, remove its row —
  git log is the build-history record (`git log --diff-filter=A`).

---

## Queue

*Empty.* All current leads have `[/path]` references in built nodes and
appear in the Priority Build Queue below.

| Item | Source | Found In | Priority | Status |
|---|---|---|---|---|

---

## Priority Build Queue

Unbuilt-stub targets referenced from the 7 built nodes (Fravor
document + Graves document + Fravor person + Nimitz encounter + Fravor
oral transcript + FLIR1 video + 2023-07-26 House Oversight hearing
event). Grouped by natural cluster so contributors can choose which
ring to close first.

### Cluster A — 2004 Nimitz encounter (F.2c pilot shipped 2026-04-19; FLIR1 F.4c pilot shipped 2026-04-20)

The encounter event and FLIR1 media node are built; the cluster's
remaining work is corroborator people nodes (Dietrich, Underwood)
and the supporting organization nodes.

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/people/alex-dietrich` | person / eyewitness | High | Co-observer (Fravor's wingman); named in Fravor testimony + multiple interview transcripts | Fravor testimony + CBS 60 Minutes 2021-05-16 transcript (archived) |
| `/organizations/uss-nimitz` | organization / gov (military-service) | High | Ship that launched the Fravor flight; referenced across multiple cluster members | Navy HR + public record |
| `/organizations/uss-princeton` | organization / gov (military-service) | High | Aegis SPY-1 radar platform — instrumented corroboration source | Navy HR + surfpac.navy.mil (archived) |
| `/organizations/vfa-41` | organization / gov (military-service) | High | Fravor's squadron (Black Aces) | Navy HR + public record |
| `/organizations/carrier-airwing-eleven` | organization / gov (military-service) | Medium | Parent of VFA-41 | Navy HR |
| `/organizations/vmfa-232` | organization / gov (military-service) | Low | Marine squadron flying Red Air (testimony mention only) | Marine Corps records |
| `/organizations/us-navy` | organization / gov (military-service) | Medium | Fravor's service — useful hub | public record |
| `/organizations/dod` | organization / gov | Medium | Referenced in Fravor testimony re ATIP | public record |
| `/organizations/ttsa` | organization / private | Medium | Formation narrative in Fravor testimony | Corporate registrations + public record |
| `/people/jay-stratton` | person / institutional-actor | Medium | Named in Fravor testimony as 2009 contact; AATIP / UAPTF relevance | Public record (Coulthart book; AARO HRR) |
| `/people/luis-elizondo` | person / institutional-actor | Medium | Named in Fravor testimony; AATIP disclosure lead | Extensive public record (2023 House testimony + book) |
| `/people/tom-delonge` | person / reporter (or private?) | Low | TTSA co-founder; named in Fravor testimony | Public record |
| `/people/christopher-mellon` | person / institutional-actor | Low | Former Deputy Assistant SecDef for Intelligence; TTSA advisor | Public record |
| `/people/steve-justice` | person / institutional-actor | Low | Former Lockheed Skunk Works director; TTSA | Public record |

### Cluster B — 2023-07-26 House Oversight hearing (hearing event shipped 2026-04-20; Fravor transcript F.3c shipped 2026-04-19)

Hearing event node + Fravor oral transcript built. Cluster's remaining
ring: Grusch and Graves companion document nodes (witness-specific
primary sources already archived), their oral transcripts, and the
two witness person nodes.

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/documents/written-testimony-grusch-2023` | document / gov-doc | High | Grusch's prepared written statement; dense whistleblower primary source; next session target | oversight.house.gov PDF (archived — sha256 `9729f98d…`) |
| `/transcripts/2023-07-26-house-grusch` | transcript / hearing | High | Grusch's oral testimony at the hearing — same stenographic PDF already archived; second F.3b hearing-transcript pilot | congress.gov hearing transcript PDF (archived) |
| `/transcripts/2023-07-26-house-graves` | transcript / hearing | High | Graves's oral testimony at the hearing — same stenographic PDF already archived; third F.3b hearing-transcript pilot | congress.gov hearing transcript PDF (archived) |
| `/people/david-grusch` | person / whistleblower | High | Cluster B anchor witness; PPD-19 urgent-concern filer; written + oral testimony both primary | Grusch written testimony + oral statement (both archived) + NewsNation interview |
| `/people/ryan-graves` | person / eyewitness | High | 2015 Virginia Beach encounters witness; written testimony already archived as document | Graves written testimony (archived + extracted) |
| `/people/sean-kirkpatrick` | person / institutional-actor | Medium | AARO founding director; named in Graves testimony | 2023-04-19 SASC testimony (archived) |
| `/people/tim-gallaudet` | person / institutional-actor | Medium | Former NOAA Chief Scientist and Deputy Administrator; UAP advocate | Public record |
| `/documents/odni-preliminary-assessment-2021` | document / gov-doc | Medium | Referenced in Graves testimony; foundational UAP report | ODNI (public PDF; archived) |

### Cluster C — NYT 2017 disclosure chain

Secondary cluster surfaced through Fravor testimony narrative.

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/people/leslie-kean` | person / reporter | Low | NYT Dec 2017 co-author; named in Fravor testimony | Public record (byline history + book) |
| `/people/ralph-blumenthal` | person / reporter | Low | NYT Dec 2017 co-author | Public record |
| `/people/helene-cooper` | person / reporter | Low | NYT Dec 2017 co-author | Public record |

### Cluster D — UAP oversight institutions

Referenced in Graves testimony; lower priority until a specific
investigation thread demands them.

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/organizations/aaro` | organization / gov | Medium | All-domain Anomaly Resolution Office; central to current UAP record | defense.gov press releases (archived) |
| `/organizations/uaptf` | organization / gov | Medium | UAP Task Force; AARO predecessor | public record |
| `/organizations/americans-for-safe-aerospace` | organization / private | Low | Ryan Graves's nonprofit | safeaerospace.com (archived) |
| `/organizations/aiaa` | organization / private | Low | Aerospace engineering professional society — pilot-reporting context | Public record |
| `/organizations/faa` | organization / gov | Low | Aviation authority — pilot-reporting context | Public record |
| `/organizations/noaa` | organization / gov | Low | Referenced in Graves testimony re Tim Gallaudet | Public record |
| `/organizations/vfa-11` | organization / gov (military-service) | Low | Graves's squadron (Red Rippers) | Navy HR |

---

## Completed audits

Nodes audited via `prompts/audit.md`. Build history is in git; this
table tracks audit history only.

| Node | Audit date |
|---|---|
| `/people/david-fravor` (i0 → i1 audit-correction) | 2026-04-19 |

---

## Milestones

Long-term structural improvements not blocked on primary sources.

| Milestone | Description | Target | Status |
|---|---|---|---|
| Close Cluster A (Nimitz) ring | Build Dietrich + FLIR1 + key orgs (Nimitz / Princeton / VFA-41) so Fravor's broken-link stubs resolve | F.2c + F.3 + F.4 shipped; FLIR1 built; Dietrich + orgs remain | In progress |
| Close Cluster B (2023-07-26 hearing) ring | Build Grusch doc + Grusch/Graves transcripts + Grusch/Graves person | Hearing event + Fravor transcript built; Grusch doc is next-session target | In progress |
| First finding node | Build a cross-entity finding spanning 3+ nodes (e.g., UAP video-release provenance chain) | After ≥3 cluster rings close | Pending |
