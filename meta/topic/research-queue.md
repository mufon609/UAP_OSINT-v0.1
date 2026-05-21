---
id: meta/topic/research-queue
type: meta
schema_version: 1
created: 2026-04-17
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

_Empty._

| Item | Source | Found In | Priority | Status |
|---|---|---|---|---|

---

## Priority Build Queue

_Empty._
