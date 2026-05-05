"""Per-check module package + shared contract types (C11 / C13 / C14).

Each named validator check lives at scripts/checks/{check_name}.py and
exports a single ``check(ctx) -> Iterable[Issue]`` callable. Contributors
asking "where does the verbatim-quote check live" should ``ls
scripts/checks/`` rather than grep a thousand-line megafile.

Two contracts shared across every check:

  - Issue: a per-violation report. Adopted by every check so pre-commit
    output is uniform regardless of which validator orchestrator dispatched
    the check.

  - Context: shared state passed to each check. BaseContext carries
    repo-global state (schema, manifest, broken-link registry); NodeContext
    and ResearchContext carry per-file state for the two iteration shapes.

See meta/toolkit-notes/c11-validator-decomposition-design.md for the full
design rationale. Sessions 2 and 3 migrate the remaining checks against
this contract.
"""

from collections import defaultdict


class Issue:
    """A single violation, warning, or report from a check.

    ``fatal=True`` signals the orchestrator to stop running further
    checks against this file (e.g., frontmatter parse failure makes
    every downstream check trip noisily on missing data).

    ``check_name`` is filled by the orchestrator at yield time so checks
    don't repeat their own name on every Issue. Powers a future
    ``--check NAME`` filter.

    ``line`` is deliberately not a structured field — checks that know
    the line embed it in ``message`` (e.g., the verbatim-quote check
    writes ``"Quote at line 42 ..."``). Promote when a structured
    consumer (``--format json``, IDE integration) needs it.
    """

    def __init__(self, path, level, message, check_name=None, fatal=False):
        self.path = str(path)
        self.level = level                    # "error" | "warn"
        self.message = message
        self.check_name = check_name
        self.fatal = fatal


class BaseContext:
    """Repo-global state. Loaded once at orchestrator entry; shared by
    every check.

    Manifest is exposed two ways: ``manifest_paths`` (the set of paths
    cited in artifacts; primary use case is path-existence checks) and
    ``manifest_entries`` (the full list of entries; needed by the
    manifest-integrity checks that examine sha256, status, archive
    bits, extraction_type). Loading once here resolves the manifest-
    loaded-3x duplication in the legacy validators.

    ``broken_links`` is the out-of-band metadata channel. Link-resolution
    writes to it; orchestrator reads it for the registry print. NOT an
    Issue stream — broken stubs are backlog signal, not violations.
    """

    def __init__(self, schema, manifest_paths=None, manifest_entries=None,
                 broken_links=None):
        self.schema = schema
        self.manifest_paths = manifest_paths if manifest_paths is not None else set()
        self.manifest_entries = manifest_entries if manifest_entries is not None else []
        self.broken_links = broken_links if broken_links is not None else defaultdict(set)


class NodeContext(BaseContext):
    """Per-content-node state (people, organizations, documents, events,
    transcripts, media, locations, findings).

    Constructed once per node by the orchestrator. ``fm`` is parsed
    frontmatter; if parsing failed the orchestrator emits a fatal Issue
    and skips downstream checks (so checks here can assume non-None).
    """

    def __init__(self, base, path, rel, text, fm=None, node_type=None,
                 type_spec=None):
        super().__init__(
            schema=base.schema,
            manifest_paths=base.manifest_paths,
            manifest_entries=base.manifest_entries,
            broken_links=base.broken_links,
        )
        self.path = path
        self.rel = rel
        self.text = text
        self.fm = fm
        self.node_type = node_type
        self.type_spec = type_spec


class ResearchContext(BaseContext):
    """Per-research-artifact state (meta/research/*.yaml).

    ``raw_lines`` is the file content split into lines for pre-parse
    checks (yaml_hash_truncation, yaml_colon_space) that scan before
    yaml.safe_load runs. ``data`` is the parsed YAML, populated by the
    orchestrator after pre-parse checks succeed.

    target_* fields are discovered by reading the target node's
    frontmatter; routes archetype-specific and kind-specific section
    requirements.
    """

    def __init__(self, base, path, rel, raw_lines, data=None,
                 target_type=None, target_archetype=None,
                 target_kind=None, target_derivation_of=None):
        super().__init__(
            schema=base.schema,
            manifest_paths=base.manifest_paths,
            manifest_entries=base.manifest_entries,
            broken_links=base.broken_links,
        )
        self.path = path
        self.rel = rel
        self.raw_lines = raw_lines
        self.data = data
        self.target_type = target_type
        self.target_archetype = target_archetype
        self.target_kind = target_kind
        self.target_derivation_of = target_derivation_of
