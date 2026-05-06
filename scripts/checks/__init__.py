"""Per-check module package + shared contract types.

Each named validator check lives at scripts/checks/{check_name}.py and
exports a single ``check(ctx) -> Iterable[Issue]`` callable. Contributors
asking "where does the verbatim-quote check live" should ``ls
scripts/checks/`` rather than grep a thousand-line megafile.

Routing — three orchestrators dispatch the checks via explicit step
lists. The lists themselves are the routing-map source of truth; this
package intentionally does not enumerate them inline, since duplication
would create a drift surface:

  - scripts/validate.py — direct dispatch in main() for global manifest
    + governance checks (BaseContext); ``_NODE_CHECKS`` for per-content-
    node checks (NodeContext).
  - scripts/validate-research.py — ``_PRE_PARSE_CHECKS`` for raw-line
    checks before YAML parse (minimal ResearchContext);
    ``_ARTIFACT_CHECKS`` for per-research-artifact checks (full
    ResearchContext).
  - scripts/review-coverage.py — ``_REVIEW_CHECKS`` for Phase III cross-
    layer review (ResearchContext extended with target node body and
    source text).

Layer separation is mechanical via Context type rather than directory
hierarchy. The decomposition design rejected
scripts/checks/{node,research,coverage}/ subdivision because the Context
type already encodes the layer in every check's signature; subdirectories
would repeat information already carried by the dispatch step lists. See
meta/toolkit-notes/c11-validator-decomposition-design.md §4 for the
reasoning of record and the post-cluster Phase 0 reaffirmation.

Two contracts shared across every check:

  - Issue: a per-violation report. Adopted by every check so pre-commit
    output is uniform regardless of which validator orchestrator dispatched
    the check.

  - Context: shared state passed to each check. BaseContext carries
    repo-global state (schema, manifest, broken-link registry); NodeContext
    and ResearchContext carry per-file state for the two iteration shapes.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional


@dataclass
class Issue:
    """A single violation, warning, or report from a check.

    ``fatal=True`` signals the orchestrator to stop running further
    checks against this file (e.g., frontmatter parse failure makes
    every downstream check trip noisily on missing data).

    ``check_name`` is filled by each check itself via a module-level
    ``CHECK_NAME`` constant — convention is ``check_name=CHECK_NAME``
    on every yielded Issue. Powers a future ``--check NAME`` filter
    and keeps Issue provenance carried even when checks are called
    standalone (tests, single-check debugging) without an orchestrator
    decorating the stream.

    ``line`` is deliberately not a structured field — checks that know
    the line embed it in ``message`` (e.g., the verbatim-quote check
    writes ``"Quote at line 42 ..."``). Promote when a structured
    consumer (``--format json``, IDE integration) needs it.
    """

    path: str
    level: str                                # "error" | "warn"
    message: str
    check_name: Optional[str] = None
    fatal: bool = False

    def __post_init__(self):
        # Coerce Path / PosixPath inputs to str so call sites can pass
        # ``rel`` (a Path) directly. Matches the legacy Issue classes'
        # behavior (validate.py / validate-research.py / review-coverage.py)
        # so the migration window doesn't change call-site semantics.
        self.path = str(self.path)


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

    Two lazy caches share work across multiple checks:

    - ``h2_sections``: list of H2 heading titles, computed once per
      Context. Multiple checks walk the H2 list (required_sections,
      section_rules, chronological_tables, table_cell_word_budget,
      governance-style enforcers); centralizing the extraction here
      avoids re-running ``re.findall`` for each consumer.

    - ``section_text(name)``: memoized extraction of a single H2
      section's body text. Called multiple times across section_rules,
      table_cell_word_budget, etc. The lazy dict caches None for
      absent sections too so probing for an optional section's
      presence is O(1) on the second access.
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
        self._h2_sections = None         # lazy; populated on first .h2_sections access
        self._section_text_cache = {}    # lazy per-section memoization

    @property
    def h2_sections(self):
        """Lazy list of H2 heading titles in document order. Cached for
        the lifetime of this NodeContext."""
        if self._h2_sections is None:
            from lib._common import extract_h2_sections
            self._h2_sections = extract_h2_sections(self.text)
        return self._h2_sections

    def section_text(self, name):
        """Lazy memoized extraction of a single H2 section's body text.
        Returns None if the section is absent (and caches the None)."""
        if name not in self._section_text_cache:
            from lib._common import extract_section
            self._section_text_cache[name] = extract_section(self.text, name)
        return self._section_text_cache[name]


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
                 target_kind=None, target_derivation_of=None,
                 node_path=None, node_text=None, source_text=None):
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
        # Cross-layer fields used by review-coverage.py checks (Phase III).
        # Populated by the review-coverage orchestrator after target-node
        # resolution + source extraction; left None for validate-research.py
        # checks (which don't access them).
        self.node_path = node_path
        self.node_text = node_text
        self.source_text = source_text
        # Lazy regenerated-body cache (BACKLOG C16). First access spawns
        # build-from-research.py --dry-run --no-validate and stores the
        # result; subsequent accesses return the cached tuple. Closes the
        # subprocess-per-cross-layer-check question — multiple consumers
        # of the regenerated body now share one spawn.
        self._regenerated = None  # populated lazily as (body, error)

    @property
    def regenerated_body(self):
        """Lazily spawn ``build-from-research.py --dry-run --no-validate``
        for this artifact and return ``(body_text, error_or_None)``.
        Cached for the lifetime of the ResearchContext — a second cross-
        layer check accessing this property doesn't respawn the
        subprocess. ``body_text`` is None when the spawn fails (error
        message lives in the second tuple element).
        """
        if self._regenerated is None:
            import subprocess
            from pathlib import Path
            build_script = (
                Path(__file__).resolve().parent.parent / "build-from-research.py"
            )
            try:
                proc = subprocess.run(
                    ["python3", str(build_script),
                     str(self.path), "--dry-run", "--no-validate"],
                    capture_output=True, text=True, timeout=60,
                )
                if proc.returncode == 0:
                    self._regenerated = (proc.stdout, None)
                else:
                    detail = (proc.stderr.strip() or proc.stdout.strip())[:200]
                    self._regenerated = (
                        None,
                        f"build-from-research.py exited {proc.returncode}: {detail}",
                    )
            except subprocess.TimeoutExpired:
                self._regenerated = (
                    None,
                    "build-from-research.py timed out during dry-run",
                )
        return self._regenerated
