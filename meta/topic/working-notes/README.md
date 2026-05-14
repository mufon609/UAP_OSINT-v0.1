---
id: meta/topic/working-notes/README
type: meta
schema_version: 1
created: 2026-04-28
---

# Working Notes

Holding pen for in-progress topic-specific investigations that haven't
yet been integrated into proper content nodes (`/people/`,
`/organizations/`, `/documents/`, `/events/`, `/transcripts/`,
`/media/`, `/locations/`, `/findings/`).

These are **synthesis documents**, not primary sources. They sit
outside the validated content layer and outside the source archive.
They exist to record investigative threads while the entity nodes
that will eventually carry them are pending.

---

## Lifecycle

1. **Living phase.** The file is created at
   `meta/topic/working-notes/{slug}.md` and edited as the
   investigation deepens. Referenced from contributor-session
   conversation, but **not linked from content nodes** — the working-
   note is contributor synthesis; primary-source citations belong on
   the entity nodes that will replace it.

2. **Integration phase.** As content nodes get built, claims and
   evidence from the working-notes file are absorbed into proper
   structure (description prose, verbatim quotes, entities_referenced,
   finding-node narratives). The `integration_targets` frontmatter
   field tracks which nodes are owed material from the file.

3. **Retirement.** When every `integration_targets` entry is built
   and the working-notes content is fully absorbed, the file is
   deleted in a single commit. Git history preserves the original
   investigation record; the integration commits cite the working-
   notes path so the trail is recoverable.

---

## Frontmatter convention

```yaml
---
id: meta/topic/working-notes/{slug}
type: meta
schema_version: 1
status: working-notes
created: YYYY-MM-DD
integration_targets:
  - /people/{slug}
  - /organizations/{slug}
  - /findings/{slug}    # may reference future / unbuilt nodes
---
```

- `status: working-notes` is a soft convention — the validator does
  not enforce it; it exists for human readers and future cleanup
  sweeps.
- `integration_targets` lists the entity nodes (built or unbuilt) the
  file is intended to be absorbed into. Update as integration
  progresses.

---

## Discipline

- **Don't link from content nodes.** Working-notes files are not
  primary sources and cannot be cited from validated entity nodes.
  Cite the underlying primary sources instead.
- **Don't validate.** The `governance-frontmatter` check (in
  `scripts/checks/governance_files.py`) skips the entire
  `meta/topic/working-notes/` directory by path prefix — its files
  sit outside the schema-frontmatter contract regardless of `type`.
  Use `type: meta` in working-notes frontmatter for human-reader
  consistency with other governance docs, but do not rely on
  `type: meta` alone to confer skip status — the skip is path-based,
  not type-based. Every `.md` file under `meta/` except those in this
  `working-notes/` directory is validated by the governance-files walk
  and must satisfy the meta-required-fields check.
  `scripts/build/validate-research.py` operates on `meta/research/*.yaml`
  artifacts only — a structurally separate scope from the
  governance-doc / content-node walk in `validate.py`.
- **Don't archive in `sources/manifest.yaml`.** These are not
  primary sources; they're contributor synthesis.
- **Do cite primary sources** within the working-notes prose when
  evidence is anchored. The eventual integration step will move those
  citations into proper structured records.

---

## Naming

Slugs follow the same kebab-case convention as content nodes
(`aaro-narrative-management-architecture`,
`oklahoma-encounter-2024-research`, etc.). When in doubt, name the
file after the central thread of the investigation.

---

## Empty-directory note

When all working-notes files are retired, the directory remains
(with this README) so the convention is preserved for future
investigations. Don't delete the README during cleanup sweeps.
