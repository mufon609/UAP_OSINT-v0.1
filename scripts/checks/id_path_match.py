"""id-path-match check — per-node NodeContext check.

Verifies the frontmatter ``id`` field matches the node's file path
(with the ``.md`` suffix stripped). The ``id`` field is the canonical
slug-of-record across cross-references; drift between id and path
produces broken navigation between linked nodes — a node referenced
elsewhere as ``[/people/alex]`` whose own frontmatter says
``id: people/alex-dietrich`` silently breaks any link resolver that
keys off either form.

Absent id is handled by frontmatter_required; this check no-ops when
``id`` isn't set so the two checks compose without double-reporting.

Origin: foundational schema discipline; present in the initial commit
``af5f789`` alongside frontmatter_required and schema_version compat.
No specific incident drove its creation — id↔path consistency is part
of the toolkit's basic invariant. The class of failure protected
against is cross-reference correctness: a renamed file whose
frontmatter id wasn't updated would silently break links from every
other node referencing it, plus the broken-link registry and the
associate.py auto-generator (both key off the slug).

Paired-check layering: frontmatter_required handles id presence; this
check handles id↔path consistency. Both use falsy-tolerant semantics
(frontmatter_required's ``field not in fm``; this check's
``if fm_id and fm_id != expected_id`` short-circuit on falsy id),
which means a nullified id (``id:`` with no value) slips through
both. Unlike archetype / kind / status (whose presence-guarded
``status_archetype_kind`` enum check fires on null values), id has
no enum-validation downstream — the null case has no third-line
defense. Accepted gap: the corpus is clean, contributor scaffolders
(new.py, research-scaffold.py) populate id automatically, and
tightening here without a real incident would be defensive coverage
of a scenario that hasn't surfaced.

Migration to per-module shape happened at commit ``60bb88d`` (C11
session 3); C18 confirmed byte-identity through that move.
"""

from checks import Issue


CHECK_NAME = "id_path_match"


def check(ctx):
    expected_id = str(ctx.rel).removesuffix(".md")
    fm_id = ctx.fm.get("id")
    if fm_id and fm_id != expected_id:
        yield Issue(
            ctx.rel, "error",
            f"Frontmatter id '{fm_id}' does not match path '{expected_id}'",
            check_name=CHECK_NAME,
        )
