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

Adjudication ledger: ``meta/topic/stub-adjudications.yaml`` records the
clusters a contributor has source-confirmed as NOT one entity (verdict
``distinct`` / ``part-whole`` / ``eponym`` / ``unresolved``). The sweep
suppresses a surfaced cluster ONLY when its membership exactly equals a
ledger entry's ``members``. A cluster that shares members with an entry but
differs from it (a stub joined or left) RE-SURFACES, labelled with the
entry it used to match and the members added or removed. The ledger is topic
content (slugs), so it lives under ``meta/topic/`` and is deleted on a fork. A
missing ledger means no suppression. ``--name`` coinage queries ignore the
ledger.

Usage:
    stub-reconcile.py                       # sweep: unadjudicated clusters
    stub-reconcile.py --show-suppressed     # ... plus the ledger-suppressed
    stub-reconcile.py --name "Vincent Teofilo"   # coinage query: existing
                                                 # stubs for this person?
    stub-reconcile.py --type people              # restrict the sweep
    stub-reconcile.py --type organizations --type people
    stub-reconcile.py --ledger PATH              # alternate ledger file
    stub-reconcile.py --selftest                 # ledger-matching unit test

Exit codes:
    0  — diagnostic ran (regardless of how many candidates surfaced)
    1  — --selftest failure
    2  — usage error (unknown --type) or a malformed ledger
"""

import argparse
import re
import sys
import tempfile
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

# The adjudicated-cluster ledger (topic content — see the module docstring).
_LEDGER_PATH = REPO_ROOT / "meta" / "topic" / "stub-adjudications.yaml"
_VERDICTS = frozenset({"distinct", "part-whole", "eponym", "unresolved"})
_LEDGER_REQUIRED = ("id", "members", "verdict", "rationale", "sources", "date")
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


class LedgerError(Exception):
    """The adjudication ledger exists but is malformed."""


def load_ledger(path):
    """Return the ledger's entries, each with a ``key`` (frozenset of its
    ``/type/slug`` members) and ``type``, or None when the file is absent (a
    fresh fork: nothing is suppressed). Raises LedgerError on a malformed
    ledger rather than silently suppressing on bad data."""
    if not path.exists():
        return None
    try:
        data = strict_yaml_load(path.read_text()) or {}
    except Exception as e:
        raise LedgerError(f"{path}: YAML parse error: {e}")
    entries = data.get("adjudications")
    if not isinstance(entries, list):
        raise LedgerError(f"{path}: top-level 'adjudications' list missing")
    seen_ids, seen_keys = set(), {}
    out = []
    for i, e in enumerate(entries):
        where = f"{path.name} entry {i + 1}"
        if not isinstance(e, dict):
            raise LedgerError(f"{where}: not a mapping")
        missing = [f for f in _LEDGER_REQUIRED if f not in e]
        if missing:
            raise LedgerError(f"{where}: missing field(s) {missing}")
        eid = e["id"]
        if eid in seen_ids:
            raise LedgerError(f"{where}: duplicate id {eid!r}")
        seen_ids.add(eid)
        if e["verdict"] not in _VERDICTS:
            raise LedgerError(f"{where} ({eid}): verdict {e['verdict']!r} "
                              f"not in {sorted(_VERDICTS)}")
        members = e["members"]
        if (not isinstance(members, list) or len(members) < 2
                or not all(isinstance(m, str) and _BARE_PATH_RE.match(m)
                           for m in members)):
            raise LedgerError(f"{where} ({eid}): members must be ≥ 2 "
                              f"'/type/slug' paths")
        types = {m.split("/")[1] for m in members}
        if len(types) != 1:
            raise LedgerError(f"{where} ({eid}): members span types "
                              f"{sorted(types)} — a cluster is one type")
        key = frozenset(members)
        if len(key) != len(members):
            raise LedgerError(f"{where} ({eid}): duplicate member")
        if key in seen_keys:
            raise LedgerError(f"{where} ({eid}): same membership as "
                              f"{seen_keys[key]!r}")
        seen_keys[key] = eid
        out.append({**e, "key": key, "type": types.pop()})
    return out


def classify(typ, clusters, ledger):
    """Split one type's clusters against the ledger. Returns
    ``(shown, suppressed)``: shown is ``[(members, rules, drifted)]`` where
    ``drifted`` lists the ``(entry, added, removed)`` ledger entries the
    cluster overlaps without matching exactly (empty for a never-ruled
    cluster); suppressed is ``[(members, rules, entry)]`` — exact matches."""
    by_key = {e["key"]: e for e in (ledger or [])}
    shown, suppressed = [], []
    for members, rules in clusters:
        key = frozenset(f"/{typ}/{s}" for s in members)
        entry = by_key.get(key)
        if entry is not None:
            suppressed.append((members, rules, entry))
            continue
        drifted = [(e, sorted(key - e["key"]), sorted(e["key"] - key))
                   for e in (ledger or []) if e["key"] & key]
        shown.append((members, rules, drifted))
    return shown, suppressed


def _print_members(typ, members, stubs):
    for slug in members:
        referers = stubs[typ][slug]
        built = "(built)" in referers
        refs = sorted(r for r in referers if r != "(built)")
        tag = "BUILT" if built else "stub"
        print(f"    /{typ}/{slug}  [{tag}]  ← {refs or '—'}")


def run_sweep(stubs, types, ledger, ledger_path, show_suppressed=False):
    """Sweep mode: report candidate duplicate-stub clusters per type, minus
    those the adjudication ledger rules on with exactly this membership.
    Returns the number of clusters shown."""
    total = 0
    all_suppressed = []
    matched_ids = set()
    for typ in types:
        clusters = cluster(list(stubs.get(typ, {}).keys()))
        shown, suppressed = classify(typ, clusters, ledger)
        all_suppressed += [(typ, s) for s in suppressed]
        matched_ids |= {e["id"] for _, _, e in suppressed}
        matched_ids |= {e["id"] for _, _, d in shown for e, _, _ in d}
        if not shown:
            continue
        print(f"── {typ}: {len(shown)} candidate cluster(s) ──\n")
        for members, member_rules, drifted in shown:
            total += 1
            print(f"  [{', '.join(member_rules)}]")
            for e, added, removed in drifted:
                delta = "; ".join(
                    p for p in (
                        f"+ {', '.join(added)}" if added else "",
                        f"− {', '.join(removed)}" if removed else "",
                    ) if p)
                print(f"  RE-SURFACED — membership changed since ledger "
                      f"entry {e['id']!r} ({e['verdict']}, {e['date']}): "
                      f"{delta}")
            _print_members(typ, members, stubs)
            print()

    if show_suppressed and all_suppressed:
        print(f"── suppressed as adjudicated: {len(all_suppressed)} "
              f"cluster(s) ──\n")
        for typ, (members, member_rules, e) in all_suppressed:
            print(f"  [{', '.join(member_rules)}]  {e['id']}: "
                  f"{e['verdict']} ({e['date']})")
            print(f"    {e['rationale']}")
            _print_members(typ, members, stubs)
            print()
        idle = [e for e in ledger if e["type"] in types
                and e["id"] not in matched_ids]
        if idle:
            print("  Ledger entries matching no surfaced cluster "
                  "(surfaced: false = recorded, never clustered; otherwise "
                  "stale — a member was renamed or removed):")
            for e in idle:
                tag = ("surfaced: false" if e.get("surfaced") is False
                       else "stale?")
                print(f"    {e['id']}  [{e['verdict']}; {tag}]")
            print()

    if total == 0:
        print("No unadjudicated candidate duplicate-stub clusters surfaced.")
    else:
        print(f"{total} candidate cluster(s). Read-only — judge each:")
        print("  - Same entity? → canonicalize to ONE slug (prefer the fullest")
        print("    source-attested form), rewrite the losing artifacts'")
        print("    associated_entities / wraps, and re-render.")
        print("  - Not one entity (distinct / part-whole / eponym)? → record")
        print("    the ruling in the adjudication ledger so the sweep stops")
        print("    surfacing it (exact-membership match).")
    try:
        shown_path = ledger_path.relative_to(REPO_ROOT)
    except ValueError:
        shown_path = ledger_path
    if ledger is None:
        print(f"\nNo adjudication ledger at {shown_path}: nothing suppressed.")
    else:
        hint = ("" if show_suppressed or not all_suppressed
                else " (--show-suppressed lists them)")
        print(f"\n{len(all_suppressed)} cluster(s) suppressed as adjudicated "
              f"in {shown_path}{hint}.")
    return total


def run_selftest():
    """Exercise the ledger matching on synthetic stubs: exact-match
    suppression, re-surfacing on changed membership, the missing-ledger
    case, and malformed-ledger rejection. No corpus read."""
    import contextlib
    import io

    failures = []
    stubs = {"people": defaultdict(set)}
    for slug in ("l-ford", "lonye-ford",              # ruled, unchanged
                 "x-jones", "xavier-jones",            # ruled, then grew
                 "xavier-q-jones",
                 "v-teofilo", "vincent-teofilo"):      # never ruled
        stubs["people"][slug].add("fixture")
    ledger_text = (
        "adjudications:\n"
        "- id: ford\n"
        "  members: [/people/l-ford, /people/lonye-ford]\n"
        "  verdict: distinct\n"
        "  rationale: fixture\n"
        "  sources: [x.pdf]\n"
        "  date: '2026-01-01'\n"
        "- id: jones\n"
        "  members: [/people/x-jones, /people/xavier-jones]\n"
        "  verdict: distinct\n"
        "  rationale: fixture\n"
        "  sources: [x.pdf]\n"
        "  date: '2026-01-01'\n"
    )
    with tempfile.TemporaryDirectory() as td:
        lp = Path(td) / "stub-adjudications.yaml"
        lp.write_text(ledger_text)
        ledger = load_ledger(lp)
        clusters = cluster(list(stubs["people"].keys()))
        shown, suppressed = classify("people", clusters, ledger)

        sup = [m for m, _, _ in suppressed]
        if sup != [["l-ford", "lonye-ford"]]:
            failures.append(f"exact match: expected only the ford cluster "
                            f"suppressed, got {sup}")
        by_members = {tuple(m): d for m, _, d in shown}
        jones = by_members.get(("x-jones", "xavier-jones", "xavier-q-jones"))
        if not jones or jones[0][0]["id"] != "jones" \
                or jones[0][1] != ["/people/xavier-q-jones"]:
            failures.append(f"changed membership: expected the jones cluster "
                            f"re-surfaced with + xavier-q-jones, got {jones}")
        if by_members.get(("v-teofilo", "vincent-teofilo")) != []:
            failures.append("unruled cluster: expected shown with no ledger "
                            "annotation")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            n = run_sweep(stubs, ["people"], ledger, lp)
        out = buf.getvalue()
        if n != 2 or "RE-SURFACED" not in out or "/people/l-ford " in out:
            failures.append(f"sweep output: expected 2 shown, a RE-SURFACED "
                            f"line and ford hidden; got n={n}")

        # Missing ledger → None → nothing suppressed.
        absent = load_ledger(Path(td) / "absent.yaml")
        if absent is not None:
            failures.append("missing ledger: expected None")
        shown0, sup0 = classify("people", clusters, absent)
        if sup0 or len(shown0) != 3:
            failures.append(f"missing ledger: expected 3 shown / 0 "
                            f"suppressed, got {len(shown0)} / {len(sup0)}")

        # Malformed ledger → LedgerError, never silent suppression.
        lp.write_text(ledger_text.replace("verdict: distinct",
                                          "verdict: same", 1))
        try:
            load_ledger(lp)
            failures.append("malformed ledger: bad verdict not rejected")
        except LedgerError:
            pass

    if failures:
        print("stub-reconcile selftest FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("stub-reconcile selftest: ok (exact-match suppression, "
          "re-surfacing on changed membership, missing ledger, "
          "malformed ledger)")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Surface stub slugs that may name one entity (read-only "
            "duplicate-stub reconcile aid)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "The sweep suppresses a cluster whose membership exactly equals\n"
            "an entry in the adjudication ledger (meta/topic/stub-\n"
            "adjudications.yaml: clusters ruled distinct / part-whole /\n"
            "eponym / unresolved). A ruled cluster that gains or loses a\n"
            "member re-surfaces, marked RE-SURFACED with the delta. No\n"
            "ledger file = no suppression.\n"
            "\n"
            "Examples:\n"
            "  stub-reconcile.py\n"
            "  stub-reconcile.py --show-suppressed\n"
            "  stub-reconcile.py --name \"Vincent Teofilo\"\n"
            "  stub-reconcile.py --type people\n"
        ),
    )
    ap.add_argument("--name", help="Coinage query: list existing stubs that "
                    "may name this person/org (instead of the corpus sweep). "
                    "Ignores the ledger.")
    ap.add_argument("--type", action="append", dest="types",
                    help="Restrict to this content type (repeatable). "
                    f"Default: {', '.join(_DEFAULT_TYPES)}.")
    ap.add_argument("--show-suppressed", action="store_true",
                    help="Also list the clusters the adjudication ledger "
                    "suppresses (with verdict + rationale), and ledger "
                    "entries that match no surfaced cluster.")
    ap.add_argument("--ledger", type=Path, default=_LEDGER_PATH,
                    help="Adjudication ledger path. Default: "
                    f"{_LEDGER_PATH.relative_to(REPO_ROOT)}.")
    ap.add_argument("--selftest", action="store_true",
                    help="Run the ledger-matching selftest on synthetic "
                    "stubs (no corpus read) and exit.")
    args = ap.parse_args()

    if args.selftest:
        return run_selftest()

    valid = set(content_dirs())
    types = args.types or list(_DEFAULT_TYPES)
    for t in types:
        if t not in valid:
            ap.error(f"unknown --type {t!r}; valid: {sorted(valid)}")

    stubs = collect_stubs(set(types))

    if args.name:
        run_query(args.name, stubs, types)
    else:
        try:
            ledger = load_ledger(args.ledger)
        except LedgerError as e:
            print(f"ERROR: malformed adjudication ledger — {e}",
                  file=sys.stderr)
            return 2
        print(f"Stub-reconcile sweep over {', '.join(types)} "
              f"(built ∪ artifact-referenced stubs)\n")
        run_sweep(stubs, types, ledger, args.ledger.resolve(),
                  show_suppressed=args.show_suppressed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
