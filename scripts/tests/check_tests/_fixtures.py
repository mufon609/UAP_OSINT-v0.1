"""Synthetic-Context fixtures for per-check unit tests.

Each per-check test imports the targeted check module and calls its
``check(ctx)`` callable with a minimal Context constructed via the
helpers below. Fixtures populate only the fields the check reads;
unspecified fields get safe sentinel defaults so tests stay short.

Three constructors mirror the three Context shapes in
``scripts/checks/__init__.py``:

  - ``make_base_ctx``     → BaseContext (manifest + global checks)
  - ``make_node_ctx``     → NodeContext (per-content-node checks)
  - ``make_research_ctx`` → ResearchContext (per-research-artifact checks,
                            including pre-parse and Phase III review)

Test modules under this directory may also import any check module via
``from checks import {name}``; the runner adds ``scripts/`` to
``sys.path`` so that import path works.
"""

from collections import defaultdict
from pathlib import Path

from checks import BaseContext, NodeContext, ResearchContext


def make_base_ctx(*, schema=None, manifest_paths=None, manifest_entries=None,
                  broken_links=None):
    """Construct a synthetic BaseContext.

    Defaults: empty schema (``{"types": {}}``), empty manifest_paths,
    empty manifest_entries, empty broken_links. Tests targeting a
    specific check pass the minimal subset needed to drive its branches.
    """
    return BaseContext(
        schema=schema if schema is not None else {"types": {}},
        manifest_paths=manifest_paths if manifest_paths is not None else set(),
        manifest_entries=manifest_entries if manifest_entries is not None else [],
        broken_links=broken_links if broken_links is not None else defaultdict(set),
    )


def make_node_ctx(*, base=None, rel="people/test.md", text="", fm=None,
                  node_type="person", type_spec=None):
    """Construct a synthetic NodeContext.

    ``rel`` is interpreted as a repo-relative path; ``ctx.path`` and
    ``ctx.rel`` both receive the same Path object — sufficient for
    checks that consult ``ctx.rel`` for error-message paths and
    ``str(ctx.rel)`` for id-path comparison.

    Lazy caches (``h2_sections``, ``section_text``) populate from
    ``text`` on first access — tests that exercise those code paths
    pass an H2-bearing markdown body via ``text``.
    """
    base = base if base is not None else make_base_ctx()
    rel_path = Path(rel)
    return NodeContext(
        base, path=rel_path, rel=rel_path, text=text,
        fm=fm if fm is not None else {},
        node_type=node_type,
        type_spec=type_spec if type_spec is not None else {},
    )


def make_research_ctx(*, base=None, rel="meta/research/test.yaml",
                      raw_lines=None, data=None,
                      target_type=None, target_archetype=None,
                      target_kind=None, target_derivation_of=None,
                      node_path=None, node_text=None, source_text=None):
    """Construct a synthetic ResearchContext.

    Pre-parse checks consume ``raw_lines`` only and may leave ``data``
    at its default ``{}``. Per-artifact checks consume ``data`` and
    target_* fields; pass them explicitly. Phase III review checks
    additionally consume ``node_path`` / ``node_text`` / ``source_text``
    (cross-layer fields populated by the review-coverage orchestrator
    in production).
    """
    base = base if base is not None else make_base_ctx()
    rel_path = Path(rel)
    return ResearchContext(
        base, path=rel_path, rel=rel_path,
        raw_lines=raw_lines if raw_lines is not None else [],
        data=data if data is not None else {},
        target_type=target_type, target_archetype=target_archetype,
        target_kind=target_kind, target_derivation_of=target_derivation_of,
        node_path=node_path, node_text=node_text, source_text=source_text,
    )
