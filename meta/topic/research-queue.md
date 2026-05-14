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

### Person Identity table — Source column has no schema backing

The person-node `## Identity` table renders four rows (Full Name, Aliases,
Nationality, Profession) with a Source column that the renderer always
emits as empty (`scripts/build/renderers/person.py::render_identity` hardcodes
`f"| {k} | {v} |  |"`). The schema's `document_intrinsic` for person
artifacts carries `full_name / aliases / nationality / profession` only —
no per-field source pointers. Rendered output therefore shows an empty
Source column on every person node.

**Surfacing case:** `/people/james-ryder` audit (Claude Web, 2026-05-08).
Auditor flagged the empty cells; population would require schema
extension (per-field source pointers on `document_intrinsic`) and
matching renderer logic.

**Three options worth considering:**

1. **Drop the Source column.** Aligns the renderer with current schema;
   if/when per-field sources are added, column comes back. Smallest
   change. Reader-visible improvement (removes noise).
2. **Add per-field source pointers** — `document_intrinsic.full_name_source`
   etc., schema fields validated and rendered. Most expressive; most
   schema work.
3. **Add a single collective Source row** below the Identity table —
   "Sources: see Background, Affiliations, Statements" — pointing readers
   at the rest of the node where attestation lives. No schema change,
   minimal renderer change.

**Priority.** Low. Pure presentation; no correctness implication.

**Scope.** Decision pass + renderer change; if option 2, also schema
field + validator update.

Surfaced: James Ryder Phase 2 audit (Claude Web) — auditor flagged
blank cells; investigation traced root cause to schema gap rather than
node-level oversight.

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
