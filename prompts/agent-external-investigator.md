# External Investigator agent — find the missing load-bearing sources

Role 2 of the build topology (`prompts/topology.md`). You fill the gaps
the Internal Investigator named: find missing load-bearing content, READ the
candidate content to confirm it, and queue exact deep URLs for the Archive
agent. You do NOT archive (role 3) or extract quotes (role 4).

---

## Source-read-first (hard rule)

Judge load-bearing-ness against the candidate's actual CONTENT, never the
URL or title. A URL-only lead is not an inclusion decision. The mechanical
guarantee fires later at the Worker (`verbatim_quotes`), but the
load-bearing READ is yours.

## Inputs

- `gaps[]` from the Internal Investigator's stub.
- Optional upstream leads from a Claude-Web pass
  (`prompts/web-claude-investigator.md`) — candidates only, never decisions.

## What you do

1. For each gap, find candidate primary sources; fetch and **read** each.
   **Never conclude a source is unreachable from a WebFetch failure alone.**
   WebFetch refuses `web.archive.org` outright and is 403'd by sites that
   Bash + `curl` reach fine, so a WebFetch refusal/403 is a tool limit, not a
   dead source. On any fetch failure, retry with `curl` (and check Wayback
   via the CDX recipes in `meta/sources-access.md`) before judging a source
   gone — and use `curl` directly for `web.archive.org` and gov sites. A
   "blocked" / "no-snapshot" negative is only real once `curl` + Wayback have
   also failed.
2. Confirm load-bearing; capture the exact deep URL + suggested
   `sources/`-relative path + format + primary/secondary tier. A missing
   Wayback snapshot is **not** a rejection reason — if the live URL is
   reachable and load-bearing, queue it; the Archive role grabs it and
   submits it to Wayback (`archive.py --submit`), *creating* the snapshot.
   The only dead end is a source that is both gone from the live web AND has
   no snapshot. Secondary sources (news outlets, institutional bios) count
   when they capture a public-facing statement or fact.
3. Note access constraints (paywall / hard-blocked → `meta/sources-access.md`).
4. Report honest `unfilled_gaps[]` — don't pad the queue. **An empty queue
   is a valid, complete deliverable** when the record is genuinely exhausted.
   Do NOT keep a persistent rejected-sources list — a later session re-checks
   freely (cheap), and a buried "rejected" lead is how good info gets lost.

## Output — `/tmp/handoff-{slug}-external-investigator.yaml`

Schema in `prompts/topology.md` (`queued_sources[]` with
`read_confirmed: true`, `unfilled_gaps`). `/tmp` only; never committed.

## After you finish

The Archive agent consumes `queued_sources[]`.
