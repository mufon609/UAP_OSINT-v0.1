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
  by built nodes (visible in `scripts/build/validate.py` broken-link
  registry), curated here with priority and rationale.

---

## Formatting rules

- **Priority values:** High, Medium, Low
- **Status values:** Pending, In-progress, Blocked
- **Active items only.** When a queued item is built, remove its row —
  git log is the build-history record (`git log --diff-filter=A`).
- **Completed audits table = node + most-recent audit date only.** No
  round labels, no cycle annotations, no per-pass summaries. Fix history
  lives in `git log` (`git log --grep "<node>"` shows the audit-related
  commits). The table tells future contributors which nodes have been
  audited and when; the per-node "Known caveats" sections below carry
  forward the substantive caveats and open questions.

---

## Queue

*Empty.* All current leads have `[/path]` references in built nodes and
appear in the Priority Build Queue below.

| Item | Source | Found In | Priority | Status |
|---|---|---|---|---|

---

## Priority Build Queue

Unbuilt-stub targets referenced from the built nodes (current
build state in CLAUDE.md). Grouped by natural cluster so
contributors can choose which ring to close first.

### Cluster A — 2004 Nimitz encounter (event + FLIR1 + Fravor + Dietrich built; orgs remain)

The encounter event, FLIR1 media node, and Dietrich eyewitness person
node are built; the cluster's remaining work is Underwood (FLIR1
pilot / corroborator), the supporting organization nodes, and the 19
interview-venue stubs Dietrich's build surfaced (CBS News + Bill
Whitaker; the five podcast organizations + hosts; Linda Hall Library
+ Nadia Drake; American Veterans Center + Tom Gibbs; seven interview
transcript nodes — all visible in `scripts/build/validate.py` broken-link
registry).

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/organizations/uss-nimitz` | organization / gov (military-service) | High | Ship that launched the Fravor flight; referenced across multiple cluster members | Navy HR + public record |
| `/organizations/uss-princeton` | organization / gov (military-service) | High | Aegis SPY-1 radar platform — instrumented corroboration source | Navy HR + surfpac.navy.mil (archived) |
| `/organizations/vfa-41` | organization / gov (military-service) | High | Fravor's squadron (Black Aces) | Navy HR + public record |
| `/organizations/carrier-airwing-eleven` | organization / gov (military-service) | Medium | Parent of VFA-41 | Navy HR |
| `/organizations/vmfa-232` | organization / gov (military-service) | Low | Marine squadron flying Red Air (testimony mention only) | Marine Corps records |
| `/organizations/us-navy` | organization / gov (military-service) | Medium | Fravor's service — useful hub | public record |
| `/organizations/dod` | organization / gov | Medium | Referenced in Fravor testimony re ATIP | public record |
| `/people/jay-stratton` | person / institutional-actor | Medium | Named in Fravor testimony as 2009 contact; AATIP / UAPTF relevance | Public record (Coulthart book; AARO HRR) |
| `/people/luis-elizondo` | person / institutional-actor | Medium | Named in Fravor testimony; AATIP disclosure lead | Extensive public record (2023 House testimony + book) |
| `/people/tom-delonge` | person / reporter (or private?) | Low | TTSA co-founder; named in Fravor testimony | Public record |
| `/people/christopher-mellon` | person / institutional-actor | Low | Former Deputy Assistant SecDef for Intelligence; TTSA advisor | Public record |
| `/people/steve-justice` | person / institutional-actor | Low | Former Lockheed Skunk Works director; TTSA | Public record |

### Cluster B — 2023-07-26 House Oversight hearing (complete)

Ring complete — hearing event node, all three oral transcripts
(Fravor, Grusch, Graves), all three written testimony documents, and
all three witness person nodes (Fravor, Grusch, Graves) built.
Remaining stubs below are cross-cluster dependencies surfaced by the
Cluster B build (Gallaudet is cross-referenced from Graves's
testimony; ODNI report is a foundational document referenced from
Graves).

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/people/tim-gallaudet` | person / institutional-actor | Medium | Former NOAA Chief Scientist and Deputy Administrator; UAP advocate | Public record |
| `/documents/odni-preliminary-assessment-2021` | document / gov-doc | Medium | Referenced in Graves testimony; foundational UAP report | ODNI (public PDF; archived) |

### Cluster E — Grusch disclosure ecosystem (rebuild surfaced these)

Grusch person-node rebuild expanded source coverage from 2 sources
(written testimony + bio) to 15 (added oral hearing transcript,
4 YouTube transcripts, 4 FOIA PDFs, Debrief piece, Burlison
announcement, 3 Burchett press releases, Rubio interviews, UAPDA
package). The rebuild surfaced new entities across four groups —
vouchers, Sol Foundation peers, disclosure journalists, and
documents/transcripts cited in Grusch's statements. All appear in
the `scripts/build/validate.py` broken-link registry.

**Vouchers (high priority — directly support Grusch credibility):**

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/people/karl-nell` | person / institutional-actor | High | UAPTF Army liaison 2021-2022; Sol Foundation co-founder; "beyond reproach" + "fundamentally correct" voucher in Debrief 2023-06-05 | Debrief piece + Sol Symposium video (archived) |
| `/people/tim-burchett` | person / institutional-actor | High | House Oversight UAP Subcommittee member; 3 archived credibility-attestation press releases | burchett.house.gov press releases (archived) |
| `/people/eric-burlison` | person / institutional-actor | High | Hired Grusch as House Task Force on Declassification advisor 2025-03-27; ongoing employer | Burlison press release + X post (archived) |
| `/people/marco-rubio` | person / institutional-actor | Medium | Then-SSCI Vice Chair; public on-record multi-witness vouching June 2023 | NewsNation interview + The Hill op-ed (archived via Wayback) |
| `/people/anna-paulina-luna` | person / institutional-actor | Medium | House Oversight UAP Subcommittee chair (later); presided over Grusch-related proceedings; `Florida Politics` quote archived | florida politics article (archived) |

**Sol Foundation peers (institutional context for Grusch's post-disclosure work):**

Jay Stratton and Christopher Mellon also appear in Cluster A with
Nimitz-era rationale; Grusch-ecosystem priorities upgrade both — see
the "Priority reconciliation" note at the end of this cluster.

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/organizations/sol-foundation` | organization / private | High | Grusch's post-2023 employer (COO / advisor); 2 Sol pages + Nell white paper + 2024 symposium page archived | thesolfoundation.org pages (archived) |
| `/people/garry-nolan` | person / institutional-actor | Medium | Sol Foundation co-founder named by Grusch as Sol co-founder | Public record |
| `/people/peter-skafish` | person / institutional-actor | Medium | Sol Foundation co-founder named by Grusch as Sol co-founder | Public record |
| `/people/harry-reid` | person / institutional-actor | Low | Former Senate Majority Leader; Grusch recounted Spring 2021 Las Vegas meeting (JRE #2065 testimony) | Public record |

**Disclosure journalists (primary media channels for Grusch's public statements):**

Ralph Blumenthal and Leslie Kean also appear in Cluster C as NYT 2017
co-authors; Debrief-2023 co-authorship is a separate rationale but
the build targets are the same person nodes — see priority
reconciliation below.

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/people/ross-coulthart` | person / reporter | High | NewsNation "Reality Check"; primary journalist channel since June 2023; JRE #2065 co-guest | NewsNation transcripts (archived) |
| `/people/jesse-michels` | person / reporter | Medium | American Alchemy "72 hrs With Grusch" documentary ~Oct 2023 | YouTube transcript (archived) |
| `/people/joe-rogan` | person / reporter | Low | JRE #2065 host 2023-11-21; long-form Grusch interview | YouTube transcript (archived) |
| `/organizations/newsnation` | organization / private | Medium | Publisher of Coulthart-Grusch reporting; multiple articles archived | Public record |
| `/organizations/the-debrief` | organization / private | Medium | Debrief article venue; already used as Dietrich source; now needed for Grusch disclosure provenance | Public record |
| `/organizations/american-alchemy` | organization / private | Low | Jesse Michels's YouTube channel | Public record |
| `/organizations/joe-rogan-experience` | organization / private | Low | JRE podcast org | Public record |

**Transcripts to build (verbatim-verified pilots):**

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/transcripts/newsnation-coulthart-grusch-2023` | transcript / other | Medium | First on-camera disclosure interview (2023-06-11) | transcribe.py output (archived) |
| `/transcripts/jre-2065-grusch-2023` | transcript / other | Medium | Most-extensive long-form interview (2023-11-21) | transcribe.py output (archived) |
| `/transcripts/american-alchemy-grusch-72hrs-2023` | transcript / other | Low | Jesse Michels documentary | transcribe.py output (archived) |
| `/transcripts/grusch-sol-2023-closing` | transcript / other | Low | Grusch closing remarks at Sol Foundation Symposium | transcribe.py output (archived) |

**Documents to build:**

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/documents/debrief-grusch-2023` | document / non-gov-doc (article) | High | Kean/Blumenthal June 5 2023 disclosure-breaking article | Already archived (HTML in sources) |
| `/documents/burlison-grusch-advisor-announcement-2025` | document / gov-doc | Medium | House press release naming Grusch advisor (2025-03-27) | Already archived |
| `/documents/grusch-ppd-19-procedural-filing` | document / gov-doc (complaint) | Medium | Unclassified PPD-19 reprisal complaint | Already archived (via Internet Archive) |
| `/documents/aaro-invitations-to-grusch-2024` | document / gov-doc | Medium | AARO letters inviting Grusch to interview (Grusch declined); FOIA 24-F-0266 | Already archived (via BlackVault mirror) |
| `/documents/grusch-dopsr-request-2023` | document / gov-doc | Low | DOPSR pre-publication review materials; FOIA 23-F-0946 | Already archived (via BlackVault mirror) |

**Institutional stubs surfaced (Grusch-exclusive — cross-cluster cases handled separately below):**

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/organizations/hpsci` | organization / gov | Low | House Permanent Select Committee on Intelligence — Grusch's historical reporting venue | Public record |
| `/organizations/hasc` | organization / gov | Low | House Armed Services Committee | Public record |
| `/organizations/sasc` | organization / gov | Low | Senate Armed Services Committee | Public record |
| `/organizations/house-uap-caucus` | organization / gov | Low | House Task Force on Declassification / UAP Caucus — Grusch's current advisor affiliation | Public record |
| `/organizations/lockheed-martin` | organization / private | Low | Named by Grusch as recipient of UAP material under his allegations | Public record |
| `/organizations/bigelow-aerospace` | organization / private | Medium | AAWSAP-era material custodian per Grusch's JRE testimony; already 2 cross-refs | Public record |
| `/people/james-lacatski` | person / institutional-actor | Medium | AAWSAP-era program lead; 2 cross-refs (Grusch + Skinwalker) | Public record |
| `/people/robert-bigelow` | person / institutional-actor | Medium | Bigelow Aerospace founder; AAWSAP-era material context | Public record (Skinwalker + Grusch cross-ref) |
| `/people/kirsten-gillibrand` | person / institutional-actor | Low | UAPDA co-sponsor; legislative response to Grusch disclosure | senate.gov press release (archived) |
| `/people/chuck-schumer` | person / institutional-actor | Low | UAPDA co-author; legislative response | senate.gov press release (archived) |
| `/people/mike-rounds` | person / institutional-actor | Low | UAPDA co-author; legislative response | senate.gov press release (archived) |

**Priority reconciliation — stubs already listed in earlier clusters:**

These five person nodes appear in both Cluster A/C and here. Priority
follows the highest-priority cluster in which the stub surfaces
(build-candidate decisions are global to the stub, not per-cluster).

| Path | Earlier cluster | Grusch-context rationale | Resolved priority |
|---|---|---|---|
| `/people/jay-stratton` | Cluster A (Medium — 2009 Fravor contact) | UAPTF director who tasked Grusch to identify SAPs/CAPs (2019); 6 cross-refs in built nodes | **High** |
| `/people/christopher-mellon` | Cluster A (Low — TTSA advisor) | Former DASD(I); Sol Foundation peer; 4 cross-refs; Grusch contradiction-context (AARO-trust observation in Debrief) | **Medium** |
| `/people/luis-elizondo` | Cluster A (Medium — AATIP lead) | AATIP-era program office; 4 cross-refs | Medium (unchanged) |
| `/people/ralph-blumenthal` | Cluster C (Low — NYT 2017) | Co-author of Debrief 2023 piece that broke Grusch disclosure | **Medium** |
| `/people/leslie-kean` | Cluster C (Low — NYT 2017) | Co-author of Debrief 2023 piece that broke Grusch disclosure | **Medium** |

### Cluster C — NYT 2017 disclosure chain

Secondary cluster surfaced through Fravor testimony narrative.

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/people/leslie-kean` | person / reporter | Low | NYT Dec 2017 co-author; named in Fravor testimony | Public record (byline history + book) |
| `/people/ralph-blumenthal` | person / reporter | Low | NYT Dec 2017 co-author | Public record |
| `/people/helene-cooper` | person / reporter | Low | NYT Dec 2017 co-author | Public record |

### Cluster F — SRI parapsychology / remote-viewing primary-source corpus

The Stanford Research Institute parapsychology investigation 1972-1990 is
currently anchored in this repository via the Stanford Research Institute
([`/organizations/stanford-research-institute`]) org node, the Hal Puthoff
([`/people/hal-puthoff`]) and Russell Targ ([`/people/russell-targ`])
person nodes, the Uri Geller ([`/people/uri-geller`]) person node, and
three newly-built document nodes from the 2026-05-16 archival sweep:
the 1974 Nature paper ([`/documents/nature-1974-targ-puthoff-information-transmission`])
which names Geller and Pat Price as the foundational SRI subjects;
the August 1973 CIA SRI Geller report
([`/documents/cia-sri-geller-aug1973`]) which records the eight-day
Aug 4-11 1973 picture-drawing experiments at SRI; and the 2015 Tablet
Magazine interview ([`/documents/tablet-spy-who-bent-a-million-spoons`])
which carries Geller's own account of his Israeli-intelligence
recruitment chain through Yoav Shaham, Meir Amit, and Aharon Yariv.

The 2026-05-16 archival sweep also added nine other CIA STARGATE-era
primary sources to the manifest as archived-only (cite-from-existing-
nodes targets, not standalone /documents/ nodes): the Appendix I
parallel-copy of the Aug 1973 Geller report
(CIA-RDP96-00791R000100480003-3), the Dec 1972 – Jan 1973 progress report
on contract 1471(S)73 (CIA-RDP96-00787R000100180001-3), the Oct 1973
Technical Proposal Part One (CIA-RDP96-00791R000100420002-0), the
Progress Report No. 1 with 13 numbered Geller experiments
(CIA-RDP96-00787R000700100004-2), the 1975 SRI Final Report Part Two
(CIA-RDP96-00791R000300030004-9 — also the queue item below), the
Part One Executive Summary (CIA-RDP96-00787R000700050001-1), the Kress
1977 parallel-copy (CIA-RDP96-00791R000200030040-0), and the 1995 CIA
Public Affairs Q&A (CIA-RDP96-00791R000100030062-7).

The remaining open queue items below close per-subject identification
gaps (Ingo Swann, Hella Hammid) and the SRI-internal chronology question
(The Record daily log) that the new corpus does not fully resolve.

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/documents/puthoff-targ-the-record-daily-log` | document / non-gov-doc | High | SRI-internal daily log documenting each Geller visit window. Per web-research audit on the Uri Geller node (rumor r1, 2026-05-16), "The Record" documents two distinct Geller visits — a five-week period in late 1972 and an eight-day visit August 4-11 1973 — that Targ's 2007 Burton-interview recollection of "six weeks in 1973" may collapse into a single period. The Dec 1972 – Jan 1973 contract progress report (CIA-RDP96-00787R000100180001-3, archived 2026-05-16) attests the earlier SRI engagement window; the Aug 1973 report (now built at /documents/cia-sri-geller-aug1973) attests the August window — but the chronology bridge between the two windows and Targ's "six weeks in 1973" recollection still requires "The Record". | Published by Puthoff-Targ with consent; archival route TBD |
| `/documents/sri-perceptual-augmentation-techniques-final-report-1975` | document / non-gov-doc | Medium | The SRI internal Final Report by Puthoff and Targ (December 1, 1975), cited by the 1995 American Institutes for Research evaluation. Archived 2026-05-16 as CIA-RDP96-00791R000300030004-9 (5.7MB OCR-scan PDF); document-node build pending. May or may not name Geller specifically — confirmable from the archived file. | Archived in manifest; awaits node build |
| `/people/ingo-swann` | person / institutional-actor | Medium | 1972 magnetometer subject per Kress 1977; named by Targ IRVA 2002 retrospective as foundational SRI subject. Subject node closes the early-SRI-subjects cluster alongside Geller and Pat Price. | Public record + IRVA bio |
| `/people/pat-price` | person / institutional-actor | Medium | 1973 'third sensitive subject' per Kress 1977; named by Targ IRVA 2002 retrospective. Per public record also named alongside Geller in the 1974 Nature paper. | Public record |
| `/people/hella-hammid` | person / institutional-actor | Low | 1974 'control subject' brought in to supplement Pat Price and Ingo Swann per Targ IRVA 2009 retrospective; ten-year SRI tenure 1974-1984. | Public record (IRVA bio) |
| `/people/andrija-puharich` | person / institutional-actor | Medium | Introducer who brought Geller to the USA and into SRI per Brendan Burton article ¶5. Per Burton, Puharich previously worked with 'Dr Vinod' on 'The Nine' channelled information and was a pivotal figure in the contactee movement. | Public record (Puharich self-published books) |
| `/people/edgar-mitchell` | person / institutional-actor | Medium | Apollo 14 astronaut; introduced to Geller via Puharich per Brendan Burton ¶5; named in Burton's Sources list as a correspondence source. UAPDA-era IONS (Institute of Noetic Sciences) founder — separately relevant. | Public record |

### Cluster D — UAP oversight institutions (AARO + UAPTF + ONI shipped)

AARO, UAPTF, and ONI now built. Remaining stubs (surfaced by the AARO +
UAPTF + ONI builds):

| Path | Type / Kind | Priority | Rationale | Source Access |
|---|---|---|---|---|
| `/organizations/nia` | organization / gov | High | Naval Intelligence Activity — signed the September 2020 UAPTF Charter; issued the April 2020 UAP Security Classification Guide | UAPTF Charter + UAP SCG (both archived) |
| `/people/david-norquist` | person / institutional-actor | Medium | Deputy Secretary of Defense who approved UAPTF establishment (August 4, 2020) | DoD press release (archived) + public record |
| `/people/travis-taylor` | person / institutional-actor | Medium | Dr. Travis Taylor — informal UAPTF Chief Scientist; U.S. Army Space and Missile Defense Command employee on time-limited assignment | Black Vault Gough article (archived) + SMDC statement |
| `/organizations/americans-for-safe-aerospace` | organization / private | Low | Ryan Graves's nonprofit; also lists Jay Stratton as Ex Director UAPTF | safeaerospace.org home page (archived) |
| `/organizations/aiaa` | organization / private | Low | Aerospace engineering professional society — pilot-reporting context | Public record |
| `/organizations/faa` | organization / gov | Low | Aviation authority — pilot-reporting context | Public record |
| `/organizations/noaa` | organization / gov | Low | Referenced in Graves testimony re Tim Gallaudet | Public record |
| `/organizations/vfa-11` | organization / gov (military-service) | Low | Graves's squadron (Red Rippers) | Navy HR |

---

## Completed audits

One row per node. Fix history lives in `git log`; substantive caveats and
open questions live in the per-node sections below.

| Node | Most recent audit |
|---|---|
| `/people/david-fravor` | 2026-04-19 |
| `/organizations/arlo-solutions` | 2026-05-03 |
| `/organizations/aaro` | 2026-05-03 |

---

## Pending corpus-wide convention questions

Patterns surfaced across the corpus that aren't yet ready for a
convention pass — all awaiting a 3+ node pattern before codifying.

### Period convention for "known start, unknown end (but not ongoing)"

Current corpus conventions: bare `period_start` → ongoing;
`period_start – period_end` → closed period; `– period_end` → unknown
start, known end. **No convention** for known-start, unknown-end-but-
not-ongoing. The Phillips kp2 case (above) is the surfacing example;
affects any role with documented start, attested-vacant later state,
undocumented departure. Current stop-gap (bare `period_start` + prose
hedge) trades a misleading "ongoing" render for an honest "we don't
know" prose flag — net judgment is the prose flag is less misleading
than a fabricated end date. Worth a convention pass once the pattern
recurs across 3+ nodes.

### Name-form inconsistency — pattern recognition pending

"Dr. Jon T. Kosloski" vs "Dr. Jon Kosloski"; "Sancorp Consulting, LLC"
vs "Sancorp Consulting"; analogous patterns likely recur across other
multi-source nodes. Per `feedback_prose_drift_warnings_must_resolve.md`,
source vocabulary takes precedence and each form may be source-attested
in its own context. Resolution requires per-instance source-form audit
(which source attests which form), not opportunistic harmonization.
Worth a systematic pass once a clear pattern emerges across 3+ nodes.

### Deceased subject — `status` field semantics + structured lifespan

The schema's `status` field on a person artifact carries values
`active | in-progress` and reflects the *node's* maintenance state
(actively maintained vs in-progress build), not the *subject's*
life status. The current schema has no structured `died`, `born`,
`lifespan`, or equivalent field — death is captured only in
`credibility_notes` prose and (when the date is uncertain) in
`rumors[]`. `/people/james-ryder` is the surfacing case in the
REFACTOR repo: deceased subject, `status: active` per node-
maintenance semantics, with the deceased state documented in
credibility_notes prose. The Affiliations row for his IVS Chairman
role has no `period_end` because the IVS leadership page (the source
attestation for the role) hasn't been updated since his death — the
"ongoing" render is technically correct against source but
implicitly contradicted by the deceased-status prose. Adjacent to
the "known start, unknown end" facet above; both stem from "what
should the structured surface say when the source attestation is
stale relative to a known-but-unsourced fact". Worth a convention
pass once a 3+ node pattern accumulates (legacy parent repo has
several deceased subjects already; if those nodes are migrated into
REFACTOR, the pattern reaches threshold immediately).

### Source-rot annotation pattern — date-relative language in older sources

When an archived source contains date-relative phrasing that has rotted
since the source was written ("Michael Jackson's latest albums" where
the source predates MJ's June 25 2009 death and refers to Invincible
(October 30 2001) — Invincible became MJ's final studio album upon his
death; "current Director" attestations made before subsequent leadership
transitions; "next year we will…" promises made in source written
decades ago), no existing structural mechanism flags the rot to the
reader. The `naming_quirks` resolution enum (`preserve-as-sic-in-quotes`
/ `use-canonical` / `disputed` / `unresolved`) does not include a category
for date-relative-language source-rot. Candidate resolution: a new
`source-rot` enum value paired with a `rot_date` or `rot_context` field
capturing what specifically has shifted.

**Surfacing case:** Uri Geller node web-audit (2026-05-16) — biography
page preserves "Michael Jackson's latest albums" wording from a pre-2009
source revision; MJ's actual final studio album (Invincible, 2001)
became "final" rather than "latest" upon his death (June 25, 2009).

**Status:** pending pattern accumulation (need 3+ instances before
codifying).

### Geographic-anachronism naming-quirk resolution

The Israel-1946 birthplace case (Uri Geller node nq11) is a
geographic-anachronism — Geller's bio writes "born in Israel on
December 20, 1946" but the State of Israel was declared May 14, 1948,
17 months after his birth, and the territory of his birth was the
British Mandate of Palestine at the time. Currently bucketed under
`resolution: preserve-as-sic-in-quotes`, but the rendered framing
"Source Form / Canonical" doesn't quite capture the geographic-vs-
temporal mismatch (it's not a typo, alias, or two-source dispute —
it's a political-geographic naming choice the source makes that's
ahistorical to the period). A `resolution: geographic-anachronism`
value with rendered framing "Source attests / Period-accurate name"
would be more honest. Likely also covers cases like Stalin-era
"Petrograd" vs modern "St. Petersburg", "Ceylon" vs "Sri Lanka", etc.

**Surfacing case:** Uri Geller node web-audit (2026-05-16) — nq11
Israel/1946.

**Status:** pending pattern accumulation (need 3+ instances before
codifying).

### Per-quote attestation-class field

Person artifacts currently distinguish `observation_type: direct |
relayed` on quotes (driving the Statements section split into Direct
Observations vs Other Statements). Program_involvement carries
`evidentiary_basis` (`primary-source` / `sworn-testimony` /
`on-record` / `self-attested` / `secondary`) and `confidence`
(`high` / `medium` / `low`). Quotes themselves carry neither — every
quote in `quotes[]` is implicitly assumed to be attested by its
`source.path`, but the attestation class (self-attestation on
subject's own publication; first-hand observation; third-party
narration about the subject) is not structurally captured.

When a person's biography page makes a sweeping self-attested claim
(e.g., Geller's Sigmund Freud lineage claim; Geller's CIA / FBI
collaboration claims about KGB file erasure / serial-killer tracking /
Russian-negotiator influence), the `credibility_notes` prose has to
flag the self-attestation manually. A per-quote `attestation_class`
field matching the `program_involvement.evidentiary_basis` enum would
let the renderer surface "Self-attestation" / "First-hand observation"
/ "Third-party narration" labels on each Statement verification
block, removing the need for manual `credibility_notes` prose flags
and reducing prose-drift surface.

**Surfacing case:** Uri Geller node web-audit (2026-05-16) — Web
flagged the Freud lineage claim as unverified beyond Geller's own
statements. Per-quote attestation-class would let q2 render
"Attestation class: self-attestation on subject's own publication"
in its verification block automatically.

**Status:** pending pattern accumulation (need 3+ instances before
codifying); schema extension + renderer update required.

---

## Milestones

Long-term structural improvements not blocked on primary sources.

| Milestone | Description | Target | Status |
|---|---|---|---|
| Close Cluster A (Nimitz) ring | Build Dietrich + FLIR1 + key orgs (Nimitz / Princeton / VFA-41) so Fravor's broken-link stubs resolve | FLIR1 built; Dietrich built; orgs remain | In progress |
| Close Cluster B (2023-07-26 hearing) ring | Build Grusch doc + Grusch/Graves transcripts + Grusch/Graves person | Hearing event + all three transcripts + all three written testimony docs + all three witness person nodes built | Done |
| Close Cluster D (UAP oversight institutions) ring | Build AARO + UAPTF + their support stubs (ONI, NIA, Norquist, Travis Taylor, etc.) | AARO + UAPTF + ONI built; NIA, Norquist, Taylor stubs surfaced and queued | In progress |
| First finding node | Build a cross-entity finding spanning 3+ nodes (e.g., UAP video-release provenance chain) | After ≥3 cluster rings close | Pending |

---

## Finding-node candidates

Finding-node ideas surfaced during entity-node builds. Per `meta/schema.yaml`,
a finding is justified when the pattern spans 3+ entity nodes, exceeds ~200
words in any single entity cell, or is about to be duplicated across 3+
nodes. Candidates here document scope + evidence chain so they can be built
substantively rather than as thin shells.

### F.X — DoD/DoW terminology asymmetry post-EO-14347

**Scope.** Document the structural pattern that statutory references and
federal-procurement systems retain "Department of Defense" while
non-statutory branding (contractor marketing, press attributions,
contractor-prepared documents) increasingly adopts "Department of War"
following EO 14347 (Sept 5, 2025). Surfaces the asymmetry as a measurable
phenomenon rather than a contributor observation embedded in any one entity
node.

**Evidence already in repo (built nodes).**

| Surface | Terminology used | Source |
|---|---|---|
| AARO — FY 2026 OP-5 program description | "AIC" (Defense-statutory framing) | `government/osd-op5-fy26-wayback-20260201.pdf` |
| AARO — public-facing aaro.mil | "AARO" (Defense-era branding retained) | aaro.mil |
| Sancorp — USAspending HQ003425FE405 | "OUSD(P)" Defense | `government/usaspending-*.txt` |
| Sancorp — Past Performance document (FOIA) | "OUSW(P)" War | FOIA release |
| Sancorp — HigherGov public profile + sancorpcorp.com marketing | "Department of War" / "DoW" branding | HigherGov + corporate site |

**Build dependencies (in priority order).** The finding is gated on these
to launch with substantive density rather than as a 2-entity observation:

1. `/organizations/arlo-solutions` (built) — second contractor
   data point beyond Sancorp; tests whether the marketing/procurement
   asymmetry generalizes across the OUSD(I&S) contractor substrate.
   Arlo's built record attests SASP and CL&S as customer offices;
   no IPMO-direct contract is attested in the Arlo primary-source corpus
   (see Arlo node rumors r1).
2. `/organizations/ipmo` (built) — third architectural layer
   under OUSD(I&S). No Arlo-IPMO contract attested in either
   node's record.
3. `/documents/eo-14347-restoring-department-of-war` (built) — legal
   foundation (Sec 2(a) authorization, Sec 2(b) non-statutory
   adoption, Sec 2(e) statutory preservation).
4. `/organizations/dod` — top-level institutional anchor; 17 refs from
   built nodes (most-referenced unbuilt org in registry). **Last
   unbuilt F.X gate.**
5. `/organizations/ousd-is` (built) — direct parent of AARO
   + IPMO; cognizant entity where the cross-architectural-layer
   asymmetry plays out at the supervisory level.

**Useful but not gating:** `/organizations/whs` (contracting office, 4 refs);
`/documents/blackvault-sancorp-23-f-1114-aaro-pws` (Sancorp PWS, already
archived).

**Density at launch (when all 5 required pre-builds ship).** F.X spans
7 entity nodes: AARO + Sancorp + Arlo + IPMO + OUSD(I&S) + DoD + EO 14347.
With optional pre-builds: 9 entities. Comfortably exceeds the 3-entity
schema threshold and supports multi-surface evidence (statutory,
organizational, contractor-marketing, federal-procurement, press).

**Status:** Pending — 4 of 5 required pre-builds shipped (arlo-solutions,
ipmo, eo-14347, ousd-is); gated on `/organizations/dod` (the last
unbuilt anchor).

**Surfaced from:** AARO Phase 2 audit — N6 recommendation deferred
cross-outlet attribution to the Finding-node queue; investigation
traced two distinct candidate findings, of which this one (DoD/DoW
asymmetry) met the 3-entity threshold while the other (April-2026
disclosure-coordination press cycle) did not.

### F.SRI — SRI Geller engagement duration: Targ 2007 recollection vs CIA contemporaneous record

**Scope.** Document the divergence between Russell Targ's 2007
retrospective recollection — "Uri was at our laboratory at SRI for
six weeks in 1973" (Brendan Burton article on urigeller.com) — and
the CIA contemporaneous record, which attests approximately 17 days
of Geller engagement at SRI across two windows: a nine-day Geller
field measurement program in November-December 1972 within the
contract 1471(S)73 contract window (Dec 1 1972 – Jan 15 1973), and
an eight-day session Aug 4-11 1973. Targ's "six weeks in 1973"
recollection exceeds the contemporaneous record by approximately
four weeks and assigns the engagement entirely to 1973 even though
the bulk per the contract progress report was in November-December
1972.

**Evidence already in repo.**

| Surface | Attestation | Source |
|---|---|---|
| Targ retrospective (2007) | "Uri was at our laboratory at SRI for six weeks in 1973" | Brendan Burton article (urigeller.com), Nov 24, 2007 — quoted on `/people/uri-geller` r5 and `/people/russell-targ` |
| CIA Aug 1973 SRI report | Eight-day session Aug 4-11 1973 per R. Targ cover memo dated August 13, 1973 | `/documents/cia-sri-geller-aug1973` (CIA-RDP79-00999A000300030027-0) |
| Contract 1471(S)73 progress report (22 February 1973) | "Task 3 covers a nine-day field measurement program within the time period 1 December 1972 to 15 January 1973 with consultant Uri Geller" (Section A, page 2); "The experiments conducted with Geller in November-December, 1972..." (Section III, page 11); sample picture-drawing experiment dated 12/7/72 (Figure 5, page 21) | manifest entry `government/cia-rdp96-00787r000100180001-3-contract-1471s73-progress-dec1972.pdf` (cite-only; doc node unbuilt) |

**What the primary record DOES NOT support.** Web's external research
audit (the 2026-05-16 investigation that produced the Geller node r1
rumor) attributed a "five-week period in late 1972" framing to
Puthoff-Targ's SRI-internal daily log "The Record" (unarchived in
this repository). The contract 1471(S)73 progress report —
contemporaneous to the engagement window and authored by Puthoff
and Targ — attests a nine-day program, not a five-week period.
"The Record" itself remains unarchived; either (a) "The Record"
disagrees with the contract progress report (which would itself be
a finding), or (b) Web's attribution to "The Record" is a secondary-
source error misattributing the 5-week figure. Without "The Record"
archived, the discrepancy cannot be adjudicated; the finding
acknowledges both possibilities.

**Build dependencies (in priority order).**

1. `/documents/cia-sri-geller-aug1973` (built) — primary
   attestation of the Aug 1973 window.
2. `/people/uri-geller` (built, audited + corrected 2026-05-16) —
   carries the r1 rumor this finding would graduate from.
3. `/people/russell-targ` (built) — carries the 2007 Targ
   retrospective quote that diverges from the contemporaneous record.
4. `/documents/sri-contract-1471s73-progress-dec1972` (unbuilt;
   archived) — would tighten the late 1972 cross-reference and add
   the only built-doc-node anchor for the 9-day attestation. The
   finding can ship without this doc-node by citing the manifest path
   directly, but the doc-node would convert the cite-only reference
   into a full structural cross-reference and supersede the inline
   Section A / Section III page references with proper Key-Passage
   quotes.

**Useful but not gating:** `/documents/puthoff-targ-the-record-daily-log`
(unbuilt; unarchived per Cluster F High priority). "The Record"
would either confirm or refute the contract progress report's 9-day
attestation, potentially adding a fourth-source data point to the
divergence.

**Density at launch.** F.SRI spans 4 entity nodes minimum (Aug 1973
SRI report + Geller + Targ + contract progress manifest entry); 5
with the contract progress doc-node built; 6 if "The Record" ships
later and reveals an additional discrepancy. Substantive analysis:
the ~4-week divergence between Targ's 2007 recollection and the
contemporaneous primary records (~30 years apart) is the pattern;
the finding documents what each source says, computes the per-window
day-counts, and stops short of adjudicating whether Targ's 2007
memory is an error, a stylization, or includes off-contract days
not captured in the contract progress report. Meets the 3+ entity
threshold; exceeds the ~200-word threshold via the per-source
attestation narrative + the recollection-vs-record analysis.

**Status:** Shippable. Two paths:
(a) build now with cite-only reference to the Dec 1972 contract
progress manifest entry; OR
(b) wait for `/documents/sri-contract-1471s73-progress-dec1972`
and/or "The Record" for tighter cross-references. Path (a) is
faster; path (b) gives the finding stronger structural cross-
references and allows Key-Passage quotes from the contract progress
report. Either way the r1 rumor on Geller node graduates to a
brief cross-reference back to the finding.

**Surfaced from:** Uri Geller node audit Phase 3 (2026-05-16) —
the r1 rumor on the Geller node carried this multi-source analysis
at single-entity scope; graduating to a finding-node moves the
canonical analysis to a cross-entity surface. Investigation pass
on the queued candidate (same date) read the contract 1471(S)73
progress report directly, surfaced the 9-day attestation that
sharpens the divergence, and corrected the math (≈ 17 days total,
not the ≈ 7 weeks originally claimed) before this entry stabilized.

---

## Externally blocked

Items waiting on an external event the repo can't drive — FOIA
resolutions, subscription registry access, third-party publication.
Each has a clear closure path. They aren't numbered because there's
no in-repo work to schedule; they sit here for visibility so a future
session reviewing the relevant node or context knows the trigger is
pending.

### Reveal Systems Inc. — California SoS / OpenCorporates registry hunt

Per the Kirkpatrick audit § 7 ("Items still open"), specific
state-of-incorporation entity number, filing date, current operating
status, and principals-beyond-inventor list for the Kirkpatrick /
Bogaard / Fairchild patent-assignee Reveal Systems Inc. were not
retrievable through open-access channels. What was established during
the archival pass:

- California is the state of incorporation per the May 2020 USPTO
  assignment record on US20200357080A1: the assignment-of-assignor's-
  interest record on the original non-provisional names "REVEAL
  SYSTEMS, INC., CALIFORNIA" as the assignee.
- The California Secretary of State business search portal is
  Imperva-blocked at the API layer (HTTP 403 to all automated POSTs);
  the bizfileonline.sos.ca.gov frontend returns an Incapsula JS
  challenge page with `noindex,nofollow` headers. Wayback Machine
  has no usable captures of registry-search result pages.
- OpenCorporates is HAProxy CAPTCHA-blocked (hCaptcha challenge on
  every request) and has no Wayback presence for Reveal-Systems-named
  entities.

**Name-collision warning** (load-bearing for any future Reveal Systems
Inc. node build under audit § 6): a different "Reveal Systems Inc."
exists with a Bloomberg company profile (ticker `0408205D:US`) — that
entity produces real estate software (custom legal forms, contracts).
It is **not** the patent-assignee Reveal Systems Inc. Future research
must distinguish via patent-assignee chain (CA assignment record →
USPTO file wrapper) rather than by name search alone.

**Path to closure** when subscription / interactive access becomes
available:
1. CA SoS bizfileonline.sos.ca.gov direct interactive query (browser-
   solved Imperva challenge) — yields entity number + filing date +
   current status + agent for service of process.
2. PACER / federal court records — would surface any litigation,
   bankruptcy, dissolution.
3. CrunchBase / PitchBook subscription — yields any institutional-
   investor activity (audit § 3.1 noted "no documented public-facing
   product launch, marketing presence, or commercial activity"; this
   would confirm or correct that observation).

**Priority.** Low. Not a correctness issue; depth-of-record question
for the eventual `/organizations/reveal-systems-inc` node build (audit
§ 6 recommendation). Patent-record evidence is sufficient for the
existing Kirkpatrick-node Credibility Notes framing.

**Scope.** Single registry-lookup pass once interactive access is
available; otherwise indefinite-blocked.

Surfaced: Kirkpatrick audit-iteration follow-up — open-access
registry hunt established CA state of incorporation per patent
record but blocked at SoS / OpenCorporates layer; name-collision
discovery worth recording so future Reveal Systems node-build
sessions don't conflate.

---

### Mellon–Kirkpatrick Signal exchange — Black Vault FOIA appeal pending

The April 18 2024 BlackVault release of FOIA case 24-F-0266 includes
the June 11–13 2023 Signal text-message exchange between Sean
Kirkpatrick and Christopher Mellon. Kirkpatrick's responses
("absurd and false"; "defending and adjudicating, and you're
undermining the very organization you purported to help establish
for this purpose") are visible verbatim in the released screenshots
and are now registered as Statements quotes q36 and q37 on
`/people/sean-kirkpatrick`.

Mellon's full reply on the same exchange is partially redacted in
the released screenshot — the visible portion documents Mellon
responding that he never claimed Grusch's claims were "accurate" but
felt Grusch was "sincere and credible," that he expressly called the
allegations "warrant[ing] investigation," and that he would "seek to
avoid further communication unless it is something that seems
extraordinary or if [Kirkpatrick] initiate[s]." The remaining text
is cut off in the released screenshot and Black Vault has filed a
FOIA appeal under case 24-F-0266 for the redacted portion.

**Status.** Pending external FOIA-appeal resolution. Out of repository
control; cannot be advanced through technical or research action.

**Path to closure** (passive, requires external event):
- Black Vault FOIA appeal resolves and the redacted text is released.
  At that point, Mellon's full reply becomes registerable on the
  Mellon person node (when built — that node is unbuilt per audit § 6
  Sol Foundation / disclosure-ecosystem build queue).
- Until resolution, the documentary record on Kirkpatrick's side is
  complete; the Mellon-side completion is downstream.

**Priority.** Low. Not a correctness issue for Kirkpatrick's node;
adds nuance to the documentary record on the Mellon side. Holds
until either (a) the FOIA appeal resolves, or (b) the Mellon node
is built (audit § 6 disclosure-ecosystem cluster) and the
incomplete-reply note becomes load-bearing for the Mellon Statements
section.

**Scope.** When the appeal resolves: re-fetch the FOIA 24-F-0266
release from Black Vault, re-extract, register Mellon's full reply
as a quote on the Mellon node (when built), and update Credibility
Notes Group B on the Kirkpatrick node accordingly.

Surfaced: Kirkpatrick audit-iteration follow-up — audit § 7 "Mellon
Signal reply text (full)" Open item logged for visibility so a
future session reviewing the Mellon node or the Kirkpatrick
credibility notes knows the appeal is pending.
