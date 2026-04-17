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

*Empty — Phase 2 pilots not started.*

| Item | Source | Found In | Priority | Status |
|---|---|---|---|---|

---

## Priority Build Queue

*Empty — Phase 2 pilots not started.*

| Path | Type / Kind | Rationale | Source Access |
|---|---|---|---|

---

## Completed audits

Nodes audited via `prompts/audit.md`. Build history is in git; this
table tracks audit history only.

| Node | Audit date |
|---|---|

---

## Milestones

Long-term structural improvements not blocked on primary sources.

*No milestones yet — Phase 2 pilots not started.*

| Milestone | Description | Target | Status |
|---|---|---|---|
