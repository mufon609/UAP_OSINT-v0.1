"""Per-check module package + shared contract types.

Each named validator check lives at scripts/checks/{check_name}.py and
exports a single ``check(ctx) -> Iterable[Issue]`` callable.

Routing — three orchestrators dispatch the checks via explicit step
lists in their own files (the lists are the routing source of truth):

  - scripts/build/validate.py — direct dispatch in main() for global
    manifest + governance checks (BaseContext); ``_NODE_CHECKS`` for
    per-content-node checks (NodeContext).
  - scripts/build/validate-research.py — ``_PRE_PARSE_CHECKS`` for
    raw-line checks before YAML parse (minimal ResearchContext);
    ``_ARTIFACT_CHECKS`` for per-research-artifact checks (full
    ResearchContext).
  - scripts/build/review-coverage.py — ``_REVIEW_CHECKS`` for cross-layer
    review (ResearchContext extended with target node body and source
    text).

Layer separation is mechanical via Context type rather than directory
hierarchy — the Context type already encodes the layer in every check's
signature, so per-layer subdirectories would repeat information already
carried by the dispatch step lists.

Two contracts shared across every check:

  - Issue: a per-violation report. Adopted by every check so pre-commit
    output is uniform regardless of which orchestrator dispatched it.

  - Context: shared state passed to each check. BaseContext carries
    repo-global state (schema, manifest, broken-link registry);
    NodeContext and ResearchContext carry per-file state for the two
    iteration shapes.

Preflight checks (``frontmatter_parse``, ``artifact_parse``,
``phase_iii_inputs``) handle parse / load diagnostics. Orchestrators
dispatch them against a minimal-shape Context before the main step list
and short-circuit the chain on any fatal Issue.

Naming — topic, not number. Checks are referenced across the codebase by
topic name (``the verbatim-quote check``, ``the prose-drift check``), never
by a positional number. Numbered lists in module docstrings, if any, are
at-a-glance summaries only and are not referenced externally. Rationale:
numeric identifiers (``check #11``) couple every external reference to
ordering, so retiring a check forces a numbering gap or a mass renumber;
topic names decouple references from position — retiring a check deletes
the function and its topic-named refs together, no placeholder, no
renumber. Names are stable interfaces: a rename ripples like any API rename
(find-replace across refs). Name a check for what it verifies, not how it
is implemented.

Design — impartial reporting. Checks surface drift signals impartially;
they do not bake in category-tuned thresholds that encode editorial
judgment about which fields are "allowed" more drift or which patterns are
"expected noise" (bias dressed as pragmatism). Favored shapes: presence /
absence floors (a token present-or-absent in source is an observation, not
a stylistic judgment); single uniform rules across field types, including
severity — a signal that is definitionally a defect is an ERROR on every
scoped field, and warn level is reserved for genuine per-case contributor
judgment. Disfavored: thresholds calibrated from "expected noise" in
specific fields; aggregate percentage cutoffs ("tolerate up to N%
unmatched") that smuggle a tolerance in as a number; any "synthesis-heavy
fields tolerate higher rates" language. Noise-reduction extensions
(stemming, whitelists, n-gram adjacency) apply uniformly across all scoped
fields — scoping one to "fields we expect to be synthesis-heavy"
reintroduces the category judgment in another layer. This validator-side
discipline pairs with the contributor-side resolution discipline in
``prose_drift.py`` (resolve every flagged token structurally, never
rationalize it away): uniform gate → rigorous resolution.
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
    a location embed it in ``message`` (e.g., entry-shape checks write
    ``"quotes[3] ('q12'): ..."``). Promote when a structured consumer
    (``--format json``, IDE integration) needs it.

    ``tokens`` carries a structured payload for checks whose human-
    readable ``message`` is necessarily truncated (e.g., prose-drift
    warnings preview only the first 8 unmatched tokens). The full set
    lands here for any structured consumer (``--format json``, IDE
    integration, single-check debugging), so contributor iteration loops
    and post-hoc audits don't re-derive what the check already computed.
    ``None`` for checks that don't carry a structured payload — preserves
    backward compatibility.
    """

    path: str
    level: str                                # "error" | "warn"
    message: str
    check_name: Optional[str] = None
    fatal: bool = False
    tokens: Optional[list] = None

    def __post_init__(self):
        # Coerce Path / PosixPath inputs to str so call sites can pass
        # ``rel`` (a Path) directly without stringifying.
        self.path = str(self.path)


class BaseContext:
    """Repo-global state. Loaded once at orchestrator entry; shared by
    every check.

    Manifest is exposed two ways: ``manifest_paths`` (the set of paths
    cited in artifacts; primary use case is path-existence checks) and
    ``manifest_entries`` (the full list of entries; needed by the
    manifest-integrity checks that examine status, archive bits,
    extraction_type).

    ``broken_links`` is the out-of-band metadata channel. Link-resolution
    writes to it; orchestrator reads it for the registry print. NOT an
    Issue stream — broken stubs are backlog signal, not violations.

    ``missing_sources`` is the same shape of out-of-band channel for a
    different signal: archived manifest artifacts whose file is absent on
    disk *and* whose path is git-ignored (the large primary-source media
    deliberately kept out of the git remote per ``.gitignore`` —
    ``sources/video/``). On a fresh clone these are expected-absent, not
    corrupt, so ``manifest_files_present`` records them here (keyed
    ``sources/<path>`` → source URL) and yields no Issue. A genuinely
    *tracked* file gone missing still errors. Orchestrator prints the
    registry so a fresh checkout sees what to recover (source URL /
    Wayback). NOT an Issue stream.

    ``source_to_artifacts`` is the cross-artifact index keyed by source
    path, mapping to the list of entity-type artifacts (people /
    organizations / documents / events / transcripts / media / locations)
    that cite that source in their ``primary_sources[]``. Built once at
    orchestrator entry by ``load_source_to_artifacts_index()``; consumed
    by the ``finding_source_in_entity_node`` check to enforce the
    three-layer architecture rule that findings duplicate entity-node
    primary-source content rather than introducing it.
    """

    def __init__(self, schema, manifest_paths=None, manifest_entries=None,
                 broken_links=None, source_to_artifacts=None,
                 synthesis_slugs=None, missing_sources=None):
        self.schema = schema
        self.manifest_paths = manifest_paths if manifest_paths is not None else set()
        self.manifest_entries = manifest_entries if manifest_entries is not None else []
        self.broken_links = broken_links if broken_links is not None else defaultdict(set)
        self.source_to_artifacts = source_to_artifacts if source_to_artifacts is not None else {}
        # Slugs of every finding / investigation node, keyed by layer
        # ({"finding": frozenset, "investigation": frozenset}). Built once at
        # orchestrator entry by load_synthesis_slugs(); consumed by the
        # directional checks to catch bare-slug prose references the
        # /findings/ // /investigations/ path needles miss.
        self.synthesis_slugs = synthesis_slugs if synthesis_slugs is not None else {"finding": frozenset(), "investigation": frozenset()}
        # Out-of-band registry, populated by manifest_files_present for
        # git-ignored archived artifacts missing on disk (expected-absent
        # on a fresh clone). Keyed sources/<path> → source URL. Only the
        # global manifest check writes it (against the base context), so —
        # unlike broken_links — it is not forwarded through the per-node /
        # per-artifact subclasses.
        self.missing_sources = missing_sources if missing_sources is not None else {}


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
            source_to_artifacts=base.source_to_artifacts,
            synthesis_slugs=base.synthesis_slugs,
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
    strict_yaml_load runs. ``data`` is the parsed YAML; the orchestrator
    is responsible for the load + parse and populates ``data`` on
    success or ``parse_error`` (string from yaml.YAMLError) on failure.
    The ``artifact_parse`` preflight check inspects this state and
    yields fatal Issues for missing file / parse error / non-dict root —
    no second file read.

    target_* fields are discovered by reading the target node's
    frontmatter; routes archetype-specific and kind-specific section
    requirements.
    """

    def __init__(self, base, path, rel, raw_lines, data=None,
                 parse_error=None,
                 target_type=None, target_archetype=None,
                 target_kind=None, target_derivation_of=None,
                 target_status=None,
                 node_path=None, node_text=None, source_text=None):
        super().__init__(
            schema=base.schema,
            manifest_paths=base.manifest_paths,
            manifest_entries=base.manifest_entries,
            broken_links=base.broken_links,
            source_to_artifacts=base.source_to_artifacts,
            synthesis_slugs=base.synthesis_slugs,
        )
        self.path = path
        self.rel = rel
        self.raw_lines = raw_lines
        self.data = data
        self.parse_error = parse_error
        self.target_type = target_type
        self.target_archetype = target_archetype
        self.target_kind = target_kind
        self.target_derivation_of = target_derivation_of
        self.target_status = target_status
        # Cross-layer fields used by review-coverage.py checks (Phase III).
        # Populated by the review-coverage orchestrator after target-node
        # resolution + source extraction; left None for validate-research.py
        # checks (which don't access them).
        self.node_path = node_path
        self.node_text = node_text
        self.source_text = source_text
        # Lazy regenerated-body cache. First access spawns
        # build-from-research.py --dry-run --no-validate and stores the
        # result so multiple cross-layer consumers share one spawn.
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
            # scripts/checks/__init__.py.parent.parent == scripts/;
            # build-from-research.py lives at scripts/build/.
            build_script = (
                Path(__file__).resolve().parent.parent
                / "build" / "build-from-research.py"
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
