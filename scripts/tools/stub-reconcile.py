#!/usr/bin/env python3
"""Duplicate-stub reconcile aid — surface stub slugs that may name one entity.

Read-only diagnostic. Two artifacts can coin DIFFERENT stub slugs for the
same not-yet-built entity, because the build's reuse survey sees only BUILT
nodes — an unbuilt stub another artifact already coined is invisible. So
``/people/v-teofilo`` ("V. Teofilo") and ``/people/vincent-teofilo``
("Vincent Teofilo") both enter the broken-link / Priority-Build registry as
two entries for one person; whichever node is built first orphans the other
reference.

This tool closes the visibility gap. It computes the COMPLETE coined-stub
set — every ``/{type}/{slug}`` the corpus references (built nodes ∪ every
artifact's ``associated_entities`` / path fields / inline ``[`/…`]`` wraps) —
and surfaces clusters of distinct slugs that plausibly name one entity, for
contributor JUDGMENT. It is NOT a gate and never auto-merges: same-surname-
different-person is legitimate and common (``/people/gerald-ford`` [President]
vs ``/people/l-ford`` [physicist L. H. Ford] vs ``/people/lonye-ford`` [Arlo
Solutions]), so the candidate set has irreducible false positives only a human
can rule on. This mirrors ``coverage-suggest.py`` (read-only audit aid) and
the repo's standing rule that fuzzy discovery is not a 0-warning-baseline gate
(see ``scripts/checks/associated_entities.py``).

Matching is NER-free / whole-slug, two rules (a cluster is the transitive
closure of compatible pairs WITHIN one type):

  - **initials** (people, and harmlessly orgs): two slugs share the same
    last token (surname / anchor) and their leading tokens are
    initials-compatible — each aligned pair is equal or one is a single-
    letter prefix of the other (``v``↔``vincent``, ``charles-a``↔``c``).
  - **subset** (orgs, and people with a dropped middle name): one slug's
    token set is a PROPER subset of the other's (``earthtech`` ⊂
    ``earthtech-international``; ``robert-forward`` ⊂ ``robert-l-forward``).

Scope: ``people`` + ``organizations`` by default — the types where "same
entity, divergent stub" is the real failure. Locations are EXCLUDED by
default: place slugs form genuine part-whole pairs (``/locations/new-mexico``
vs ``/locations/santa-fe-new-mexico``) that the subset rule would mis-flag as
duplicates. Widen with ``--type`` when a real need appears.

Usage:
    stub-reconcile.py                       # sweep: all candidate clusters
    stub-reconcile.py --name "Vincent Teofilo"   # coinage query: existing
                                                 # stubs for this person?
    stub-reconcile.py --type people              # restrict the sweep
    stub-reconcile.py --type organizations --type people

Exit codes:
    0  — diagnostic ran (regardless of how many candidates surfaced)
    2  — usage error (unknown --type)
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

# scripts/tools/stub-reconcile.py — put the scripts/ parent on sys.path so
# `from lib._common` resolves from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import (  # noqa: E402
    REPO_ROOT,
    RESEARCH_DIR,
    content_dirs,
    strict_yaml_load,
)


# Default types the sweep clusters. People + organizations only — see the
# module docstring (locations form part-whole pairs that the subset rule
# would mis-flag). Honorifics dropped from a queried name before tokenizing.
_DEFAULT_TYPES = ("people", "organizations")
_HONORIFICS = frozenset({
    "dr", "mr", "mrs", "ms", "prof", "professor", "sir", "dame", "hon",
    "gen", "col", "lt", "maj", "capt", "cmdr", "cdr", "adm", "sgt",
    "sen", "rep", "gov", "pres", "rev", "fr", "st",
})

# Generic institutional / function words that must NOT anchor a subset match
# on their own. Without this, a bare single-token stub of a common word
# (``/organizations/science``, ``/congress``, ``/senate``) is a subset of
# every multi-word slug containing it and union-finds dozens of unrelated orgs
# into one noise cluster. A subset match requires the SMALLER token set to
# carry a distinctive (non-generic, length ≥ 4) token — a real name part like
# ``einstein`` / ``mitre`` / ``representatives``, not ``science`` / ``senate``.
# Surnames are NOT listed here (a bare-surname person stub is a legitimate
# judge-it candidate, e.g. ``/people/einstein`` → ``albert-einstein``).
_GENERIC_TOKENS = frozenset({
    "of", "the", "and", "for", "at", "in", "on", "to",
    "science", "sciences", "technology", "research", "studies", "study",
    "institute", "institutes", "university", "universities", "college",
    "school", "schools", "foundation", "academy",
    "congress", "senate", "house", "committee", "subcommittee", "council",
    "department", "corporation", "company", "incorporated", "agency",
    "office", "bureau", "center", "centre", "laboratory", "laboratories",
    "lab", "labs", "association", "society", "division", "program",
    "programs", "project", "group", "systems", "system", "services",
    "service", "command", "wing", "national", "international", "american",
    "federal", "state", "states", "united", "general", "advanced",
})

# A wrapped body reference: [`/type/slug`]. Backtick-bracket form only, so a
# bare URL path (``.../documents/dia/...``) never false-matches.
_WRAP_RE = re.compile(r"\[`(/[a-z]+/[a-z0-9][a-z0-9-]*)`\]")
# A bare path VALUE — a YAML string that is EXACTLY /type/slug (an
# associated_entities entry or a *_path / *_node field), never a substring.
_BARE_PATH_RE = re.compile(r"^/[a-z]+/[a-z0-9][a-z0-9-]*$")


def _iter_strings(node):
    """Yield every string value in a nested dict / list."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _iter_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _iter_strings(v)


def collect_stubs(valid_types):
    """Return ``{type: {slug: set(referers)}}`` over the whole corpus.

    Referers are artifact stems (``dird-30``) or the literal ``(built)`` when
    a node file exists. Sources unioned:
      - built node files ``{type}/*.md`` → marks the slug ``(built)``
      - each artifact's inline ``[`/type/slug`]`` wraps (prose)
      - each artifact's exact ``/type/slug`` string values
        (``associated_entities`` entries + ``*_path`` / ``*_node`` fields)
    """
    out = defaultdict(lambda: defaultdict(set))

    def add(path, referer):
        parts = path.strip("/").split("/")
        if len(parts) != 2:
            return
        typ, slug = parts
        if typ not in valid_types:
            return
        out[typ][slug].add(referer)

    # Built nodes
    for typ in valid_types:
        d = REPO_ROOT / typ
        if d.is_dir():
            for md in d.glob("*.md"):
                add(f"/{typ}/{md.stem}", "(built)")

    # Artifact references
    for art in sorted(RESEARCH_DIR.glob("*.yaml")):
        stem = art.stem
        raw = art.read_text()
        for m in _WRAP_RE.findall(raw):
            add(m, stem)
        try:
            data = strict_yaml_load(raw) or {}
        except Exception:
            continue
        for s in _iter_strings(data):
            if _BARE_PATH_RE.match(s):
                add(s, stem)

    return out


def _tokens(slug):
    return slug.split("-")


def _tok_compat(a, b):
    """Two tokens are compatible if equal, or one is a single-letter prefix
    of the other (an initial of the fuller name)."""
    if a == b:
        return True
    if len(a) == 1 and b.startswith(a):
        return True
    if len(b) == 1 and a.startswith(b):
        return True
    return False


def _initials_compatible(ta, tb):
    """Same last token (surname / anchor) AND leading tokens align position-
    wise under ``_tok_compat`` (the shorter leading-list compared against the
    longer's prefix; the longer may carry extra trailing middle names)."""
    if ta[-1] != tb[-1]:
        return False
    la, lb = ta[:-1], tb[:-1]
    if not la or not lb:
        return False  # a bare-surname slug is too ambiguous to auto-pair
    short, long_ = (la, lb) if len(la) <= len(lb) else (lb, la)
    return all(_tok_compat(s, l) for s, l in zip(short, long_))


def _subset_compatible(ta, tb):
    """One token set is a PROPER subset of the other, and the smaller set
    carries a distinctive token (non-generic, length ≥ 4) so a lone common /
    institutional word ('science', 'senate') can't link unrelated slugs."""
    sa, sb = set(ta), set(tb)
    if sa == sb:
        return False
    small, big = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
    if not small < big:
        return False
    return any(len(t) >= 4 and t not in _GENERIC_TOKENS for t in small)


def _compatible(slug_a, slug_b):
    """Return the rule name linking two slugs of one type, or None."""
    ta, tb = _tokens(slug_a), _tokens(slug_b)
    if _initials_compatible(ta, tb):
        return "initials"
    if _subset_compatible(ta, tb):
        return "subset"
    return None


def cluster(slugs):
    """Union-find clusters over compatible pairs. Returns a list of
    (sorted_slugs, sorted_rules) for clusters of size ≥ 2."""
    parent = {s: s for s in slugs}
    rules = defaultdict(set)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    slist = sorted(slugs)
    for i in range(len(slist)):
        for j in range(i + 1, len(slist)):
            rule = _compatible(slist[i], slist[j])
            if rule:
                union(slist[i], slist[j])
                rules[frozenset((slist[i], slist[j]))].add(rule)

    groups = defaultdict(list)
    for s in slist:
        groups[find(s)].append(s)

    out = []
    for members in groups.values():
        if len(members) < 2:
            continue
        member_rules = set()
        for r_key, r_vals in rules.items():
            if r_key <= set(members):
                member_rules |= r_vals
        out.append((sorted(members), sorted(member_rules)))
    return sorted(out)


def _name_to_slug_tokens(name):
    """Normalize a free-text person name to slug tokens: lowercase, drop
    honorifics + periods/commas, kebab the rest. 'Dr. V. Teofilo' → ['v',
    'teofilo']."""
    cleaned = re.sub(r"[.,]", " ", name.lower())
    toks = [t for t in re.split(r"[\s\-]+", cleaned) if t]
    toks = [t for t in toks if t not in _HONORIFICS]
    return toks


def run_query(name, stubs, types):
    """Coinage-time mode: given a person/org name, list existing stubs (built
    + unbuilt) whose slug is compatible with the name, so the coiner reuses
    one instead of minting a divergent slug."""
    qtoks = _name_to_slug_tokens(name)
    if not qtoks:
        print(f"Could not derive tokens from name {name!r}.")
        return
    qslug = "-".join(qtoks)
    print(f"Query: {name!r} → candidate slug tokens {qtoks}\n")
    any_hit = False
    for typ in types:
        hits = []
        for slug, referers in stubs.get(typ, {}).items():
            if slug == qslug:
                hits.append((slug, referers, "exact"))
            else:
                rule = _compatible(qslug, slug)
                if rule:
                    hits.append((slug, referers, rule))
        if hits:
            any_hit = True
            print(f"── {typ} ──")
            for slug, referers, rule in sorted(hits):
                built = "(built)" in referers
                refs = sorted(r for r in referers if r != "(built)")
                tag = "BUILT" if built else "stub"
                print(f"  /{typ}/{slug}  [{tag}; {rule}]  ← {refs or '—'}")
            print()
    if not any_hit:
        print("No existing stub matches — coining a new slug is correct.\n"
              "Prefer the fullest source-attested name form for the slug.")
    else:
        print("If a hit names the SAME entity, REUSE its slug (prefer the "
              "fullest source-attested form) instead of coining a new one.")


def run_sweep(stubs, types):
    """Sweep mode: report candidate duplicate-stub clusters per type."""
    total = 0
    for typ in types:
        clusters = cluster(list(stubs.get(typ, {}).keys()))
        if not clusters:
            continue
        print(f"── {typ}: {len(clusters)} candidate cluster(s) ──\n")
        for members, member_rules in clusters:
            total += 1
            print(f"  [{', '.join(member_rules)}]")
            for slug in members:
                referers = stubs[typ][slug]
                built = "(built)" in referers
                refs = sorted(r for r in referers if r != "(built)")
                tag = "BUILT" if built else "stub"
                print(f"    /{typ}/{slug}  [{tag}]  ← {refs or '—'}")
            print()
    if total == 0:
        print("No candidate duplicate-stub clusters surfaced.")
    else:
        print(f"{total} candidate cluster(s). Read-only — judge each:")
        print("  - Same entity? → canonicalize to ONE slug (prefer the fullest")
        print("    source-attested form), rewrite the losing artifacts'")
        print("    associated_entities / wraps, and re-render.")
        print("  - Distinct people sharing a surname? → leave as-is (expected;")
        print("    e.g. President Ford vs physicist L. H. Ford).")
    return total


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Surface stub slugs that may name one entity (read-only "
            "duplicate-stub reconcile aid)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  stub-reconcile.py\n"
            "  stub-reconcile.py --name \"Vincent Teofilo\"\n"
            "  stub-reconcile.py --type people\n"
        ),
    )
    ap.add_argument("--name", help="Coinage query: list existing stubs that "
                    "may name this person/org (instead of the corpus sweep).")
    ap.add_argument("--type", action="append", dest="types",
                    help="Restrict to this content type (repeatable). "
                    f"Default: {', '.join(_DEFAULT_TYPES)}.")
    args = ap.parse_args()

    valid = set(content_dirs())
    types = args.types or list(_DEFAULT_TYPES)
    for t in types:
        if t not in valid:
            ap.error(f"unknown --type {t!r}; valid: {sorted(valid)}")

    stubs = collect_stubs(set(types))

    if args.name:
        run_query(args.name, stubs, types)
    else:
        print(f"Stub-reconcile sweep over {', '.join(types)} "
              f"(built ∪ artifact-referenced stubs)\n")
        run_sweep(stubs, types)
    return 0


if __name__ == "__main__":
    sys.exit(main())
