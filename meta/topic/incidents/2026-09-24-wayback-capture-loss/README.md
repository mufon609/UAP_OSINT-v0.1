---
id: meta/topic/incidents/2026-09-24-wayback-capture-loss/README
type: meta
---

# Incident: Wayback Machine captures lost after indexing (2026-09-24 → 2026-09-25)

**Status:** documented; follow-up decisions open (see "Open questions").
**Recorded:** 2026-09-25, by the maintainer with Claude Code.
**Times:** all UTC. `~` marks a time reconstructed from surrounding events
rather than read from a timestamp; everything else is a Wayback snapshot
ID, a file-name timestamp, or a clock reading printed during the session.

---

## Summary

On 2026-09-24 we submitted 27 Arlo Solutions job-posting URLs to the
Internet Archive's Save Page Now (SPN). SPN reported most submissions as
captured; several showed errors but captured anyway. The CDX index listed
24 of the 27 captures within the hour. About 17 hours later, **8 of those URLs no longer
had any retrievable capture from that session**. Seven of the eight had
been listed in CDX with HTTP 200 on 2026-09-24, and all eight were gone
from CDX, the timemap, and the viewer on 2026-09-25. The other 19 survived.

- **No takedown or exclusion.** None of the 8 URLs returns Wayback's
  "excluded" response. Five were re-captured on 2026-09-25 and those new
  captures load normally, which an exclusion would prevent. The three
  that could not be re-captured return "has not archived that URL", which
  means no capture, not a blocked one. The losses are consistent with an
  Internet Archive infrastructure failure. The cause is not known.
- **Recovery.** 5 URLs were still live and were re-captured. **3 were
  taken down by Arlo before the loss was found and cannot be recovered
  from Wayback** (717, 719, 728). Their only surviving copies are our
  local ones in `evidence/local-copies/`.
- **Corpus impact: none.** No node, research artifact, or manifest entry
  cites any of these URLs. The broader exposure is covered under
  "Impact on the corpus".

---

## Why this matters

The repository's trust model says the **local copy is the integrity
guarantee and Wayback is insurance** (`README.md`, "What this is";
`INVESTIGATOR.md`, lines 66–67). Wayback is still a big part of why a
reader can trust the record. It is an independent third party that
attests a page existed with given content at a given time, separately
from anything we hold. This incident shows that an SPN "success" message,
and even a CDX listing, did not guarantee a durable capture. Wayback's
attestation is best-effort: it can disappear after it has been reported.

The concern that would damage credibility is a **targeted removal**:
captures deleted on request by an interested party. The evidence below
was gathered to test for that, and does not support it.

---

## Intent: why we were archiving these pages

The research question was which Arlo Solutions postings support the
OUSD(I&S) Sensitive Activities & Special Programs (SASP) office. Arlo
holds the SASP call order HQ003425F0104 (see
`organizations/arlo-solutions.md`). Arlo's recruitment postings
describe influence, deception, and perception-management staff roles in
language that parallels IPMO's published mission
(`organizations/ipmo.md`). Job postings disappear when positions fill, so
the maintainer asked for them to be preserved in the Wayback Machine
while they were still live. Where a URL was already archived, the aim was
to confirm the capture rather than resubmit it.

Scope grew in two steps during the session:

1. Four named postings (jobs 4660820007, 4660812007, 5055636007,
   4660800007) were checked. All four already had verified captures and
   were not resubmitted.
2. A survey of Arlo's full Greenhouse board (41 live postings at
   2026-09-24T02:31:41Z) found 26 live postings that had never been
   captured, plus job 4660812007, which had been edited after its last
   capture. Those 27 URLs are the subject of this incident.

---

## Timeline

### 2026-09-24

| Time (UTC) | Event |
|---|---|
| ~02:00–02:15 | CDX checks of the four named postings. CDX intermittently returned the Internet Archive "Temporarily Offline" page. One query for 5055636007 returned an empty result; a later query returned three captures. Retrieved captures of all four were decompressed and confirmed to contain the posting title and body keywords. |
| **02:19:33** | `scripts/tools/archive.py --submit` for job 5226271007 (733) printed `FAILED: HTTP 500`. SPN had in fact created snapshot `20260924021933`; that only became apparent at ~02:37. |
| ~02:20–02:26 | Four more SPN attempts for 5226271007 via `curl` with a browser User-Agent, each returning HTTP 500. |
| **02:23:29** | Local copy of the live 5226271007 page and its Greenhouse API record saved (`evidence/local-copies/greenhouse-5226271007/`). |
| **02:31:41** | Full Greenhouse board snapshot saved with posting bodies: 41 jobs (`board-20260924T023141Z.json`), and per-job text extracted (`job-text/`). |
| ~02:31–02:33 | Claude fetched titles of 177 removed postings from existing Wayback captures, **four requests at a time**. About 19 succeeded before `web.archive.org:443` started refusing connections. |
| ~02:33–02:35 | `web.archive.org` refused connections from this machine, in both `curl` and Chrome, while `archive.org` stayed reachable. The maintainer was on a hotel (Disney) network at the time. |
| **02:35:25** | `web.archive.org` reachable again. |
| ~02:37 | SPN via Chrome for 5226271007 reported *"The same snapshot had been made 15 minutes ago"*, pointing at `20260924021933`, with *"There was a delay in registering this snapshot."* A direct load of that snapshot returned 404. |
| 02:38:08 – 03:05:26 | SPN via Chrome, one URL at a time, for the remaining 26 URLs. Results are per URL in the ledger. |
| ~03:06–03:07 | Retries: 726 (`Job failed`), 741 (`Job failed`). |
| ~03:10 | CDX verification of all 27 URLs (`checks/cdx-verify-20260924T0310Z.txt`): 24 listed with HTTP 200, not listed: 733, 717, 728. The listing included 726 (`030625`) and 741 (`030729`), despite their `Job failed` UI results. |
| 03:18:49 | 717 resubmitted; UI showed `Job failed`; CDX listed `20260924031849 200`. |
| 03:20:20 | CDX returned "Temporarily Offline" again. |
| **03:20:33** | 733 resubmitted. The UI pointed back to `20260924021933`; the viewer redirected to a new capture `20260924032033`, which was **visually confirmed** to show the full posting (title, Program Security Officer, SAP, SCIF/SAPF, Pentagon). |
| ~03:21 | 728's announced snapshot `20260924025133` loaded as "The Wayback Machine has not archived that URL." Claude reported 26 of 27 confirmed. At that point only 733 had been visually confirmed; the others rested on the SPN UI result and the CDX listing. |

### 2026-09-25

| Time (UTC) | Event |
|---|---|
| **20:17:25** | Board re-snapshot (`board-20260925T201725Z.json`): 41 → 31 postings. 12 removed (717, 718, 719, 720, 722, 723, 726, 727, 728, 729, 740, 741); 2 new (743, 744); 737 retitled to "Program Manager". |
| ~20:17–20:21 | CDX recheck of the 27 URLs (`checks/cdx-recheck-20260925T2020Z.txt`) showed 9 with no capture since 2026-09-24: 734, 717, 719, 726, 728, 711, 712, 725, 730. |
| ~20:21–20:22 | Direct `id_` loads at each missing snapshot timestamp: 726 loaded (HTTP 200, correct title), so its CDX absence was a false negative. The other 8 returned HTTP 404. |
| 20:22:54 – 20:32:18 | Re-captures on a stable home network. `archive.py --submit` succeeded first try for 734, 711, 712, 725, 730 and 743. It skipped 737 by design (a capture already existed), so 737's retitled version was captured by direct SPN. 744 returned HTTP 520 twice but was captured. All new captures were loaded directly and showed the correct title. |
| **20:45:47** | Timemap and https-form CDX re-checked for 734, 719, 717, 728 and 711. No 2026-09-24 mementos; 734 and 711 show only today's re-capture. |
| **20:53:57** | Exclusion test (viewer response) for all 8 lost URLs: none "excluded". 734, 711, 712, 725 and 730 load their 2026-09-25 re-capture; 717, 719 and 728 return "has not archived that URL". |
| 20:55:18 – ~20:57:40 | Attempt to record raw Wayback state (CDX, timemap, viewer, live) per URL for the evidence folder. It sent about five requests per URL with 3 s pauses. From ~20:57:14 `web.archive.org` refused connections again (HTTP 000), and one earlier CDX response was inconsistent with its viewer response. The run was stopped and its output discarded rather than committed, because connection failures would read as "no capture". **This second block was caused by our request rate.** |

---

## Per-URL ledger

All URLs are `https://job-boards.greenhouse.io/arlosolutionsllc/jobs/{job ID}`.
Headings: **"SPN said"** is what Save Page Now reported on 2026-09-24.
**"CDX 09-24"** is the ~03:10 verification. **"State 09-25"** is the
outcome after the 2026-09-25 checks. **"Live 09-25"** is whether the
posting was on Arlo's board at 20:17. The 2026-09-25 states come from
the checks in the timeline and are recorded in the session log (see
"Evidence inventory"). A raw per-URL state capture is still to do; see
"Open questions". For each local copy's SHA-256, see
`evidence/SHA256SUMS`.

### URLs whose 2026-09-24 capture was lost

| # | Job ID | Title | SPN said (09-24) | CDX 09-24 | State 09-25 | Live 09-25 | Recovery |
|---|---|---|---|---|---|---|---|
| 734 | 5226317007 | Classification/Program Protection Security SME | Done! First Archive `023808` | listed `023808` 200 | gone (404; no memento) | yes | re-captured `20260925202254` |
| 711 | 5205585007 | Senior Manager, Talent Acquisition | Done! First Archive `030428` | listed | gone | yes | re-captured `20260925202331` |
| 712 | 5206505007 | Cyber Training Academy Instructor | Done! First Archive `030526` | listed | gone | yes | re-captured `20260925202436` |
| 725 | 5216612007 | On-Site Program Manager (CISA International) | Done! First Archive `025355` | listed | gone | yes | re-captured `20260925202618` |
| 730 | 5221874007 | Logistics Analyst II (MCA) | Done! First Archive `025647` | listed | gone | yes | re-captured `20260925202804` |
| 717 | 5215711007 | Acquisition Program Analyst – Journeyman (AFRL/RF) | 1st: not observed; retry: `Job failed` | 1st: not listed; retry listed `031849` 200 | gone | **no** | **unrecoverable from Wayback** — local copy only |
| 719 | 5215744007 | Directorate Management Liaison – Journeyman (AFRL/RF) | Done! First Archive `024337` | listed | gone | **no** | **unrecoverable from Wayback** — local copy only |
| 728 | 5218232007 | Logistics and Equipment Management – Journeyman (AFRL/RF) | Done! First Archive `025133` + "delay in registering" | not listed | never retrievable | **no** | **unrecoverable from Wayback** — local copy only |

733's first capture `20260924021933` was also never retrievable: it was
announced with "delay in registering", not listed, and returned 404. 733
is not counted as lost because its second capture `20260924032033`
survives.

### URLs whose 2026-09-24 capture survived

| # | Job ID | Title | 09-24 capture | Notes |
|---|---|---|---|---|
| 733 | 5226271007 | Operations Manager Support Level II (lead PSO, SAP/SCIF) | `032033` | visually confirmed 09-24 and 09-25 |
| 513 | 4660812007 | Influence, Deception, and Perception Management Activities Staff Officer SME IV | `023901` | refresh of an already-archived posting |
| 732 | 5224777007 | CD/TOC Network Analyst Senior | `023957` | |
| 735 | 5226804007 | Counterintelligence Analyst (NOAA) | `024037` | |
| 718 | 5215739007 | Business Analyst for the Chief Scientist & Engineer – Senior (AFRL/RF) | `024240` | removed from board by 09-25 |
| 720 | 5215773007 | Directorate Management Liaison – Senior (AFRL/RF) | `024522` | removed by 09-25 |
| 721 | 5216142007 | Division Business Analyst – Senior | `024620` | |
| 722 | 5216171007 | Division Business Analyst – Journeyman | `024735` | removed by 09-25 |
| 723 | 5216208007 | Financial Operations Specialist – Journeyman | `024839` | removed by 09-25 |
| 726 | 5218228007 | Financial Operations Specialist – Senior | `030625` | UI `Job failed` twice; captured anyway; 09-25 CDX false negative; removed by 09-25 |
| 727 | 5218230007 | Infrastructure Design Support – Senior | `025035` | removed by 09-25 |
| 729 | 5218233007 | Logistics and Equipment Management – Senior | `025255` | removed by 09-25 |
| 724 | 5216541007 | Executive Assistant (DOE) | `025454` | |
| 736 | 5234232007 | Security Control Assessor (Temporary) | `025757` | |
| 737 | 5241604007 | Deputy Director, Program Management | `025939` | retitled "Program Manager"; new version `20260925203218` |
| 739 | 5247459007 | Executive Administrative Support Professional | `030049` | |
| 740 | 5247509007 | Executive Administrative Support Professional | `030134` | removed by 09-25 |
| 741 | 5247722007 | Administrative Support Specialist | `030729` | UI `Job failed` twice; captured anyway; removed by 09-25 |
| 742 | 5247740007 | Administrative Support Specialist | `030330` | |

### Captures that existed before the incident (checked, not submitted)

| # | Job ID | Title | Captures | Live 09-24 |
|---|---|---|---|---|
| 514 | 4660820007 | Influence, Deception, and Perception Management Activities Staff Officer V | 2025-04-28 → 2026-08-04 | no (already removed) |
| 513 | 4660812007 | (same role) SME IV | 2025-04-28 → 2026-08-04 | yes |
| — | 5055636007 | OUSW (I&S) SASP Incumbent | 2026-02-27, 2026-05-21, 2026-08-04 | yes |
| 512 | 4660800007 | Counter-Weapons of Mass Destruction (C-WMD) Staff Officer II | 2025-04-28 → 2026-02-27 | no (already removed) |

Postings first seen on 2026-09-25 and captured then: 743 (5248865007,
`20260925202956`) and 744 (5249173007; SPN returned HTTP 520 twice, but
a 2026-09-25 capture loads).

---

## What the Internet Archive did (observed behaviour)

These are recorded as observed; no explanation is inferred.

1. **Errors that still captured.** SPN HTTP 500 (733, five times; the
   first created `021933`), SPN UI `Job failed` (717, 726, 741), and SPN
   HTTP 520 (744, twice) all produced real captures. An SPN error is not
   evidence that nothing was captured.
2. **Announced snapshots that never became retrievable.** Both snapshots
   announced with *"There was a delay in registering this snapshot"*
   (733 `021933`, 728 `025133`) never loaded.
3. **Indexed captures that later vanished.** Seven captures listed in CDX
   with HTTP 200 on 2026-09-24 were absent from CDX, the timemap, and the
   viewer on 2026-09-25. A CDX listing is not proof a capture will last.
4. **CDX false negatives.** On 2026-09-24, CDX returned nothing for
   5055636007 and later returned three captures. On 2026-09-25, a
   date-filtered CDX query returned nothing for 726 while its capture
   loaded directly. A single empty CDX query is not proof of loss. The
   losses above were each confirmed by a direct load, the timemap, and
   the availability API.
5. **Service degradation.** CDX returned "Temporarily Offline" at least
   three times on 2026-09-24, and `web.archive.org` refused connections
   for a few minutes while `archive.org` stayed reachable.

---

## Our own actions that may have contributed

Recorded here so the account stays complete:

- **Concurrent requests.** Claude fetched archived pages four at a time
  (~02:31). The connection refusal followed within minutes, so this
  probably triggered a temporary rate-limit block. There is no evidence
  it affected captures made after 02:35 or the index; some lost captures
  (e.g. 711 at `030428`) were made 30+ minutes later. The same thing
  happened on 2026-09-25 at ~20:57, at about five requests per URL with
  3 s pauses, which caused a second block. Wayback's rate limit is
  tighter than those rates.
- **Network.** The 2026-09-24 session ran on a shared hotel network, and
  the maintainer suspects this affected how Wayback treated the traffic.
  On 2026-09-25, on a home network, `archive.py` succeeded first try for
  6 of the 7 URLs it submitted, and the seventh's HTTP 520 still
  captured.
- **Anonymous SPN.** All submissions were unauthenticated. Whether
  logged-in SPN captures ("Save also in my web archive") are more durable
  is unknown.
- **Verification depth.** On 2026-09-24 Claude reported 26 of 27
  confirmed. That rested on SPN UI results and CDX listings; only 733 was
  visually confirmed. Given observations 2–3, that was not proof of
  durable capture.
- **SPN result screens were not saved to disk.** They exist only in the
  session log.

---

## Impact on the corpus

- **Direct impact: none.** No `greenhouse.io` URL appears in any node,
  research artifact, or `sources/manifest.yaml` (checked 2026-09-25). The
  Arlo recruitment quote in `organizations/arlo-solutions.md` cites the
  locally archived careers page `news/arlo-recruitment-20260503.html`,
  not Greenhouse.
- **Exposure: Wayback status is a one-time check.** Manifest
  `archive_status` bit 1 and `wayback_date` are set once, when `archive.py`
  first confirms or submits a URL, and are never re-checked by design
  ("no retry storms on confirmed entries"). As of 2026-09-25 (after
  rebasing onto the remote), 399 of 556 manifest entries carry a
  `wayback_date`. This incident shows such a
  record can go stale without anyone noticing.
- **Highest-risk entries (Wayback-only, `archive_status: 2`)** were
  spot-checked on 2026-09-25. Four of five resolve. The fifth
  (`https://doi.org/10.1088/0963-0252/24/5/055022`, recorded `2026-05-07`)
  has no `doi.org` capture on that date, only 302 redirects from 2018 and
  2022. The likely matching capture is of the redirect target,
  `iopscience.iop.org/article/10.1088/0963-0252/24/5/055022` at
  `20260508020059` (HTTP 200). Because the manifest records only a day,
  it cannot show which snapshot was meant. That is a precision gap in our
  own records, not an observed loss.

---

## Evidence inventory

Everything under `evidence/` is committed. SHA-256 for every file is in
`evidence/SHA256SUMS`.

| Path | What it is | Captured |
|---|---|---|
| `local-copies/board-20260924T023141Z.json` | Greenhouse board API, all 41 live postings **with full HTML bodies**. This is the primary local record for 717, 719 and 728. | 2026-09-24T02:31:41Z |
| `local-copies/board-20260925T201725Z.json` | Same, 31 live postings | 2026-09-25T20:17:25Z |
| `local-copies/job-text/job-{id}.txt` | Plain-text extraction of each posting body from the board JSON (derived; the JSON is the original) | 2026-09-24 ~02:31 (743, 744: 2026-09-25) |
| `local-copies/greenhouse-5226271007/` | 733 live page HTML + API JSON | 2026-09-24T02:23:29Z |
| `checks/save-queue-20260924.txt` | The 27 URLs submitted, in submission order | 2026-09-24 |
| `checks/cdx-verify-20260924T0310Z.txt` | CDX verification of the 27 on 2026-09-24 | 2026-09-24 ~03:10 |
| `checks/cdx-recheck-20260925T2020Z.txt` | CDX recheck on 2026-09-25, which surfaced the losses | 2026-09-25 ~20:20 |
| `checks/cdx-all-job-ids-20260924.txt` | Every Arlo job ID with a CDX 200 capture as of 2026-09-24 (192 IDs) | 2026-09-24 ~02:31 |
| `checks/cdx-removed-titles-partial-20260924.txt` | Titles of removed postings from their captures; mostly `<no title>` because of the connection refusal | 2026-09-24 ~02:31–02:33 |

**Session log.** The full Claude Code session log is
`~/.claude/projects/-home-neural-Desktop-REFACTOR/e80debc1-4714-4bb9-8c4d-9fa0c81c86de.jsonl`.
It is the complete timestamped record of every request and response,
including the SPN result screenshots. It is kept outside the committed
evidence because it contains the full session context and account
details, and this repository has a remote. The maintainer froze a copy
at 2026-09-25T21:04:50Z (`session-log-20260925T210450Z.jsonl`), kept
locally and gitignored in the scratch drafts tree. Its hash:

```
SHA-256  8e2312e1a56325d070e6b70a56d2eeb6c3566d7c406e4736c33cdf2d3d369809
```

The live log kept growing after that point, since the session was still
open. The frozen copy covered everything through the drafting of this
report; the hash applies to that copy, not the live file.

The frozen copy was deleted on 2026-09-26 by maintainer decision. It was
insurance against a takedown of the Greenhouse postings or their captures,
and that concern was not borne out. The hash above remains the record of
what the copy contained; the committed evidence under `evidence/` is
unaffected.

---

## What is known and what is not

**Known**
- 8 of 27 URLs submitted on 2026-09-24 lost every capture from that
  session within about 17 hours, 7 of them after being listed in CDX.
- None of the 8 is excluded, and 5 accepted and serve new captures.
- 19 captures from the same hour survived, including several of the
  postings most relevant to the research (513, 733, 732, 735). The losses
  did not avoid relevant postings: 734 (Classification/Program Protection)
  was lost and re-captured.
- SPN success or error messages and single CDX results did not reliably
  predict whether a capture would last.

**Not known**
- Why the 8 captures were lost, and why these 8 and not the others.
- Whether the lost captures could reappear (for example, an index
  partition coming back online).
- Whether earlier captures in the manifest have been lost the same way.

---

## Open questions (for the follow-up discussion)

These are deliberately left for the next step.

1. Should the manifest's Wayback status be re-verified periodically, and
   should it store the full snapshot timestamp or URL instead of a day?
   Related but distinct: the BACKLOG entry "Close the Wayback-submission
   gap on the all-internal build branch" covers sources that are never
   submitted. This incident covers submitted captures that are later
   lost.
2. Should a submission count as "Wayback confirmed" only after a delayed
   direct load (e.g. more than 24 hours later) rather than an SPN or CDX
   result?
3. Should perishable sources get a second independent archive (e.g.
   archive.today) alongside Wayback?
4. Should the Arlo postings (at least 733, 734, 513, 5055636007 and the
   board snapshot) enter `sources/` through the archive step so they carry
   the corpus's normal integrity treatment?
5. Should the Internet Archive be told about the lost captures?
6. Record the raw per-URL Wayback state (CDX, timemap, viewer) into
   `evidence/` in a slow pass, one request at a time with long pauses,
   so the 2026-09-25 findings rest on committed responses as well as the
   session log. The first attempt was rate-limited (see timeline,
   2026-09-25 20:55).
