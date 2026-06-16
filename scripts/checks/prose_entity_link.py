"""prose_entity_link check — per-node NodeContext check.

The linking rule (build-protocol "Linking — ingest is the relevance
decision"): every load-bearing entity a source NAMES reaches the node's
auto-generated ``## Associated Nodes`` index, with no "load-bearing vs.
incidental" discretion. An entity gets there by EITHER mechanism
``associate.py`` unions: an inline ``[`/{type}/{slug}`]`` wrap in the node's
own authored prose, OR membership in the structured ``associated_entities``
field (the complete record, and the ONLY home for an entity named solely
inside a verbatim quote — quote text can never be wrapped). The full
source-named coverage is therefore the contributor's job via
``associated_entities`` (auditor-verified, aided by ``coverage-suggest.py``);
``associated_entities.py`` checks that field's shape + superset.

This check is a NARROW, *mechanical, zero-false-positive* guard on the
inline-wrap mechanism only — not the full rule. It cannot detect arbitrary
names (that would need NER). What it CAN do reliably is catch the concrete
drift:

  **a node names an entity that ALREADY EXISTS in the repo (by its
  canonical display name or a registered alias) without wrapping it.**

It builds a ``{display-name / alias -> /type/slug}`` index from every
**person and organization** node's H1 + Identity-table ``Full Name`` /
``Aliases`` rows (cheap, module-cached per worker process), then scans the
node under test. A name matches only as a whole phrase, and only
**multi-token names or all-caps acronyms (≥3 chars)** qualify — never a
bare surname ("Green", "Baker") — which is what keeps it
false-positive-free.

Scope is people + organizations *only* — the proper-noun entity types.
Document / event / transcript / media / location / finding /
investigation nodes carry *descriptive* titles ("DIA Defense Intelligence
Reference Document", "Warp Drive / Extra Dimensions", a release date), not
proper names; harvesting those produces generic-phrase false positives.
Those reference classes are governed by the same convention but caught by
the structured cross-reference fields the renderer already wraps, not by
this mechanical guard.

Carve-outs (faithful to convention):
  - Verbatim ``quote.text`` (rendered as ``>`` blockquote lines) is never
    wrapped — it stays source-faithful — so blockquote lines are excised
    before the scan. A name appearing ONLY inside a quote does not fire here;
    it is carried to ``## Associated Nodes`` by the ``associated_entities``
    field instead (the mechanism that exists precisely for the un-wrappable
    quote-only case).
  - The renderer-generated ``## Name Variants`` / ``## Source-Form Notes``
    sections are excised — they tabulate how *sources* mangle a name; the
    canonical column is reference metadata, not the node arguing about the
    entity. Carrying that canonical navigationally is a separate renderer
    concern. A name appearing ONLY in a variant table does not fire.
  - The ``## References`` (cited_works) section is excised — the
    bibliographic / authorship-network layer is explicitly not a navigation
    surface (the universal-stub carve-out). An entity named only in a
    citation does not fire.
  - A self-reference (the node naming its own subject) is excluded.
  - If the entity's path is wrapped anywhere in the body, it is already
    linked → no issue, regardless of how many times the name also appears
    unwrapped in prose.

The bibliographic ``cited_works`` / ``## References`` layer is out of
scope by design — it is an authorship-network dimension, not a navigation
surface (see the document renderer + the cited_works schema).
"""

import re

from checks import Issue
from lib._common import REPO_ROOT, parse_frontmatter


CHECK_NAME = "prose_entity_link"

# Proper-noun entity types only. Descriptive-title node types (documents,
# events, etc.) are excluded — see module docstring.
_ENTITY_DIRS = ("people", "organizations")

# Generic corporate / legal-form tokens that are never a standalone entity
# name even when they survive as their own key.
_NAME_STOPWORDS = frozenset({
    "LLC", "INC", "CORP", "LTD", "CO", "LLP", "PLC", "GMBH",
})


# Same link grammar associate.py reads to build ## Associated Nodes:
# a backtick-bracketed canonical path. The single source of which entities
# a node has actually linked.
_LINK_RE = re.compile(r"\[`(/[^`]+)`\]")

# Identity / Overview table rows that carry an entity's display name(s).
# Value group is lazy up to the closing pipe; trailing whitespace trimmed
# by the caller. "Name" alone is deliberately excluded — it collides with
# column-header rows ("| Name | Role |").
_FULLNAME_RE = re.compile(r"^\|\s*Full Name\s*\|\s*(.+?)\s*\|", re.MULTILINE)
_ALIASES_RE = re.compile(r"^\|\s*Aliases\s*\|\s*(.+?)\s*\|", re.MULTILINE)
_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

# A name key qualifies for matching only if it is multi-token OR an
# all-caps acronym (≥3 chars, letters/digits/.&- ). This is the
# zero-false-positive gate: bare single-word surnames never become keys.
_ACRONYM_RE = re.compile(r"^[A-Z][A-Z0-9.&-]{2,}$")

# H1 split — only the org "ABBR — Full Name" dash compound, NOT commas
# (a Full Name like "Sancorp Consulting, LLC" is one name, not two).
_H1_SPLIT_RE = re.compile(r"\s+[—–]\s+|\s+-\s+")

# Aliases cell split — these ARE explicitly multi-valued.
_ALIAS_SPLIT_RE = re.compile(r"\s*[;,/]\s*|\s+[—–]\s+|\s+-\s+")

# Blockquote line (verbatim quote.text) — excised before the prose scan.
_BLOCKQUOTE_LINE_RE = re.compile(r"^\s*>.*$", re.MULTILINE)

# Leading YAML frontmatter block.
_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

# Renderer-generated variant-catalog sections — these tabulate how SOURCES
# mangle a name (the canonical column is reference metadata, not the node
# arguing about that entity). Making the canonical column navigable is a
# separate renderer concern; this check governs authored ARGUMENT prose, so
# it excises these sections like it excises blockquotes.
_METADATA_SECTION_RE = re.compile(
    r"^## (?:Name Variants|Source-Form Notes|References)\s*$.*?(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)


# Module-level cache of the entity index — built once per process. Validation
# forks workers, so each worker pays the ≈85-file read exactly once.
_ENTITY_INDEX = None


def _qualifies(name):
    """A name is matchable only if multi-token or an all-caps acronym, and
    not a generic legal-form token."""
    name = name.strip()
    if not name or name.upper() in _NAME_STOPWORDS:
        return False
    if len(name.split()) >= 2:
        return True
    return bool(_ACRONYM_RE.match(name))


def _names_from_node_text(text):
    """Yield candidate display names / aliases for one node body.

    Sources: the H1 (split on em/en-dash so an org's 'ABBR — Full Name'
    yields both sides), the ``Full Name`` row (taken whole — never comma-
    split), and each ``Aliases`` cell entry. Caller filters by
    ``_qualifies``.
    """
    names = []
    m = _H1_RE.search(text)
    if m:
        names.extend(_H1_SPLIT_RE.split(m.group(1)))
    m = _FULLNAME_RE.search(text)
    if m:
        names.append(m.group(1))
    m = _ALIASES_RE.search(text)
    if m:
        names.extend(_ALIAS_SPLIT_RE.split(m.group(1)))
    # Drop any cell that is itself a link wrap or empty.
    for n in names:
        n = n.strip()
        if n and "[`/" not in n and _qualifies(n):
            yield n


def _build_entity_index():
    """Build ``{name -> set(paths)}`` from every person + organization
    node's identity surfaces. Cached module-level. A name shared by two
    entities maps to both paths (matching tolerates either being
    wrapped)."""
    index = {}
    for d in _ENTITY_DIRS:
        cdir = REPO_ROOT / d
        if not cdir.is_dir():
            continue
        for node in sorted(cdir.glob("*.md")):
            try:
                text = node.read_text()
            except OSError:
                continue
            fm, _ = parse_frontmatter(text)
            if not fm or "id" not in fm:
                continue
            path = "/" + str(fm["id"]).strip("/")
            for name in _names_from_node_text(text):
                index.setdefault(name, set()).add(path)
    return index


def _entity_index():
    global _ENTITY_INDEX
    if _ENTITY_INDEX is None:
        _ENTITY_INDEX = _build_entity_index()
    return _ENTITY_INDEX


def _prose_outside_quotes(text):
    """Node body with frontmatter and verbatim ``>`` blockquote lines
    removed — the authored-prose surface the universal-stub rule governs.
    """
    text = _FRONTMATTER_RE.sub("", text)
    text = _METADATA_SECTION_RE.sub("", text)
    return _BLOCKQUOTE_LINE_RE.sub("", text)


def check(ctx):
    self_path = "/" + str(ctx.fm.get("id", "")).strip("/") if ctx.fm else None

    body = ctx.text
    wrapped = set(_LINK_RE.findall(body))
    prose = _prose_outside_quotes(body)

    index = _entity_index()
    for name in sorted(index):
        paths = index[name]
        # Self-reference (subject naming itself) is never wrapped — skip.
        if self_path and paths == {self_path}:
            continue
        targets = paths - ({self_path} if self_path else set())
        if not targets:
            continue
        # Already linked if ANY candidate path is wrapped in the body.
        if targets & wrapped:
            continue
        # Whole-phrase, case-sensitive — the name must stand as its own
        # token run, not a substring of a longer word.
        if re.search(r"(?<![\w'])" + re.escape(name) + r"(?![\w'])", prose):
            target = sorted(targets)[0]
            yield Issue(
                ctx.rel, "error",
                f"prose_entity_link: names existing entity {name!r} in prose "
                f"but never wraps its stub {target} — add a [`{target}`] wrap "
                f"so it reaches ## Associated Nodes (universal-stub rule; see "
                f"build-protocol 'name it, wrap it').",
                check_name=CHECK_NAME,
            )
