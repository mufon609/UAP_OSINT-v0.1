#!/usr/bin/env python3
"""stamp-speaker-id.py — derive transcript-quote speaker_id from the verified
attribution sibling (BACKLOG C3-W1).

The sibling (`sources/transcripts/{slug}-attribution.yaml`) is the single
source of truth for who speaks when. Instead of the Worker hand-keying
`speaker_id` on each quote — which can silently contradict the sibling — the
Builder runs this tool. It resolves each quote's `[MM:SS]` anchor through the
sibling, aligns the artifact's `speakers[]` ids + node_links to the sibling
(killing the id-divergence hazard, e.g. the jre artifact whose `s1`/`s2` were
swapped relative to its sibling), and stamps each quote's `speaker_id`. The
`speaker_attribution_consistency` check then becomes defense-in-depth that
should never fire.

Resolution reuses the consistency-check helpers verbatim
(`scripts/checks/speaker_attribution_consistency.py`): `[MM:SS]` → source line
→ covering sibling turn → speaker. A quote already consistent with the sibling
keeps its attribution (only renumbered to the aligned ids); a quote that
disagrees is corrected and reported; a quote with no `speaker_id` (the Worker
no longer keys it) is derived from the sibling anchor turn.

Modes (auto-selected by the artifact's `target_node` type):
  - derive  (transcript artifact): align speakers[] to the sibling and stamp
            every transcript quote's speaker_id.
  - confirm (person / organization / other): warn-only — flag any quote whose
            sibling anchor disagrees with the quote's declared speaker / the
            node subject. Mutates nothing.

Default is a DRY RUN (reports the changes it would make). Pass --write to apply.
ruamel round-trip keeps an unchanged artifact byte-identical, so diffs are
minimal.

  ./stamp-speaker-id.py meta/research/{slug}.yaml            # dry run
  ./stamp-speaker-id.py meta/research/{slug}.yaml --write
  ./stamp-speaker-id.py meta/research/{slug}.yaml --confirm  # force confirm mode
"""

import argparse
import sys
from pathlib import Path

from ruamel.yaml import YAML

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib._common import REPO_ROOT  # noqa: E402
from checks.speaker_attribution_consistency import (  # noqa: E402
    _range_seconds, _build_source_index, _resolve_line, _build_line_map,
    _norm_link, _norm_name, _load_siblings,
)

SOURCES = REPO_ROOT / "sources"


def _yaml() -> YAML:
    """ruamel configured for round-trip fidelity: preserve quotes, never wrap
    long scalars, and emit explicit `null` (so unchanged fields stay byte-
    identical — verified with a 0-line no-op round-trip on the corpus)."""
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.representer.add_representer(
        type(None),
        lambda r, d: r.represent_scalar("tag:yaml.org,2002:null", "null"),
    )
    return y


def _live(turn_sid):
    """The live (non-foreign) speaker ids of a turn's speaker_id (str or list)."""
    ids = turn_sid if isinstance(turn_sid, list) else [turn_sid]
    return [x for x in ids if isinstance(x, str) and not x.startswith("foreign-")]


def _collapse(ids):
    """A sorted unique id set → a bare string (single) or list (mixed), or None."""
    u = sorted(set(ids))
    if not u:
        return None
    return u[0] if len(u) == 1 else u


class _SrcResolver:
    """Per-source cache of (seconds→line index, sorted seconds, line→turn map)."""

    def __init__(self):
        self._cache = {}

    def get(self, spath, sibling):
        if spath not in self._cache:
            index, total = _build_source_index(SOURCES / spath)
            declared = sibling.get("source_line_count")
            if index is None or (isinstance(declared, int) and declared != total):
                self._cache[spath] = (None, None, None)
            else:
                self._cache[spath] = (index, sorted(index), _build_line_map(sibling))
        return self._cache[spath]


def _anchor_speakers(q, sibling, spath, res):
    """(anchor_live_ids, span_live_ids, status) for a quote, resolving its
    `[MM:SS]` location through the sibling. `span` pads ±1 line to absorb sub-
    line / lead-in boundaries (same tolerance as the consistency check)."""
    src = q.get("source") or {}
    start, end = _range_seconds(src.get("location"))
    if start is None:
        return [], [], "no-anchor"
    index, sorted_secs, line_map = res.get(spath, sibling)
    if index is None:
        return [], [], "stale-source"
    sl = _resolve_line(index, sorted_secs, start)
    if sl is None:
        return [], [], "pre-first-tick"
    el = _resolve_line(index, sorted_secs, end) or sl
    anchor = line_map.get(sl)
    anchor_live = _live(anchor.get("speaker_id")) if anchor else []
    span = []
    for ln in range(min(sl, el) - 1, max(sl, el) + 2):
        t = line_map.get(ln)
        if t:
            span += _live(t.get("speaker_id"))
    return anchor_live, span, "ok"


def _node_dir(art):
    """The node-type directory segment of target_node (e.g. `transcripts`,
    `people`) — note it is the plural directory name, not the singular
    node_type used by build-from-research."""
    target = str(art.get("target_node") or "").strip("/")
    return target.split("/")[0] if target else ""


def _sibling_paths(quotes, siblings):
    return sorted({
        (q.get("source") or {}).get("path")
        for q in quotes if isinstance(q, dict)
    } & set(siblings))


# ---------------------------------------------------------------------------
# derive mode (transcript artifact)
# ---------------------------------------------------------------------------

def _derive(art, sibling, spath, changes, warnings):
    res = _SrcResolver()
    sib_speakers = sibling.get("speakers") or []
    sib_by_id = {s.get("id"): s for s in sib_speakers if isinstance(s, dict)}
    sib_by_link, sib_by_name = {}, {}
    for s in sib_speakers:
        if not isinstance(s, dict):
            continue
        link = _norm_link(s.get("node_link"))
        if link:
            sib_by_link[link] = s.get("id")
        name = _norm_name(s.get("name"))
        if name:
            sib_by_name[name] = s.get("id")

    # --- align artifact speakers[] ids + node_links to the sibling ---
    art_speakers = art.get("speakers") or []
    remap = {}
    for a in art_speakers:
        aid = a.get("id")
        link = _norm_link(a.get("node_link"))
        sid = sib_by_link.get(link) if link else None
        if sid is None:
            sid = sib_by_name.get(_norm_name(a.get("name")))
        if sid is None:
            warnings.append(f"speaker {aid!r} ({a.get('name')!r}) has no sibling "
                            f"match (by node_link or name) — left unchanged")
            remap[aid] = aid
        else:
            remap[aid] = sid
    matched = [v for k, v in remap.items() if k != v or v in sib_by_id]
    if len(set(matched)) != len([v for v in remap.values()]):
        # collision: two artifact speakers map to one sibling id
        if len(set(remap.values())) != len(remap):
            sys.exit(f"error: speaker-id remap is not 1:1 ({remap}); manual review")

    for a in art_speakers:
        old = a.get("id")
        new = remap[old]
        if new != old:
            changes.append(f"speaker id {old} -> {new} ({a.get('name')})")
            a["id"] = new
        sib = sib_by_id.get(new)
        if sib is not None and a.get("node_link") != sib.get("node_link"):
            changes.append(f"speaker {new} node_link "
                           f"{a.get('node_link')!r} -> {sib.get('node_link')!r}")
            a["node_link"] = sib.get("node_link")
    art_speakers.sort(key=lambda s: str(s.get("id")))

    # --- stamp quotes ---
    for q in art.get("quotes") or []:
        if not isinstance(q, dict):
            continue
        if (q.get("source") or {}).get("path") != spath:
            continue
        old = q.get("speaker_id")
        old_set = {remap.get(x, x) for x in (old if isinstance(old, list) else [old])} if old else set()
        anchor_live, span, status = _anchor_speakers(q, sibling, spath, res)

        if status != "ok":
            new = _collapse(old_set) if old_set else None
            if not old_set:
                warnings.append(f"quote {q.get('id')!r}: cannot derive speaker_id "
                                f"({status}) and none was keyed — left unset")
        elif old_set and (old_set & set(span)):
            new = _collapse(old_set)  # consistent — renumber only
        else:
            derived = anchor_live or span
            if not derived:
                warnings.append(f"quote {q.get('id')!r}: anchor lands in a "
                                f"non-speaker turn — left unchanged")
                continue
            new = _collapse(derived)
            if old_set:
                warnings.append(f"quote {q.get('id')!r}: CORRECTED speaker_id "
                                f"{_collapse(old_set)!r} -> {new!r} "
                                f"(was inconsistent with the sibling)")

        if new is not None and new != old:
            changes.append(f"quote {q.get('id')!r}: speaker_id {old!r} -> {new!r}")
            q["speaker_id"] = new


# ---------------------------------------------------------------------------
# confirm mode (person / org / other)
# ---------------------------------------------------------------------------

def _confirm(art, siblings, warnings):
    res = _SrcResolver()
    subject = _norm_link(art.get("target_node"))
    art_speakers = art.get("speakers") or []
    art_link_by_id = {s.get("id"): _norm_link(s.get("node_link"))
                      for s in art_speakers if isinstance(s, dict)}
    for q in art.get("quotes") or []:
        if not isinstance(q, dict):
            continue
        spath = (q.get("source") or {}).get("path")
        sibling = siblings.get(spath)
        if sibling is None:
            continue
        anchor_live, span, status = _anchor_speakers(q, sibling, spath, res)
        if status != "ok" or not span:
            continue
        sib_by_id = {s.get("id"): s for s in (sibling.get("speakers") or [])
                     if isinstance(s, dict)}
        span_links = {_norm_link(sib_by_id.get(i, {}).get("node_link")) for i in span}
        span_links.discard("")
        if not span_links:
            continue
        # Who does the artifact attribute this quote to?
        qsid = q.get("speaker_id")
        declared = {art_link_by_id.get(x) for x in (qsid if isinstance(qsid, list) else [qsid])}
        declared.discard("")
        declared = declared or {subject}
        if declared and not (declared & span_links):
            warnings.append(
                f"quote {q.get('id')!r}: attributed to {sorted(declared)} but the "
                f"sibling for {spath} attributes its [MM:SS] span to "
                f"{sorted(span_links)} — verify the attribution")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("artifact", help="path to meta/research/{slug}.yaml")
    ap.add_argument("--write", action="store_true",
                    help="apply changes (default: dry run / report only)")
    ap.add_argument("--confirm", action="store_true",
                    help="force confirm mode (warn-only) regardless of node type")
    args = ap.parse_args()

    path = Path(args.artifact)
    if not path.is_file():
        sys.exit(f"error: not found: {path}")

    y = _yaml()
    with path.open() as f:
        art = y.load(f)
    if art is None:
        sys.exit("error: empty artifact")

    siblings = _load_siblings()
    quotes = art.get("quotes") or []
    sib_paths = _sibling_paths(quotes, siblings)
    changes, warnings = [], []

    mode = "confirm" if (args.confirm or _node_dir(art) != "transcripts") else "derive"

    if mode == "derive":
        if len(sib_paths) != 1:
            sys.exit(f"error: derive mode expects exactly one verified transcript "
                     f"sibling among the quotes' sources; found {sib_paths or 'none'}. "
                     f"(Is the sibling finalized? Use --confirm for a non-transcript "
                     f"artifact.)")
        _derive(art, siblings[sib_paths[0]], sib_paths[0], changes, warnings)
    else:
        _confirm(art, siblings, warnings)

    print(f"stamp-speaker-id [{mode}] — {path.name}")
    for c in changes:
        print(f"  CHANGE  {c}")
    for w in warnings:
        print(f"  WARN    {w}")
    if not changes and not warnings:
        print("  (no changes; already consistent with the sibling)")

    if mode == "derive" and changes:
        if args.write:
            with path.open("w") as f:
                y.dump(art, f)
            print(f"  → wrote {len(changes)} change(s) to {path}")
        else:
            print(f"  → dry run; {len(changes)} change(s) NOT written (pass --write)")


if __name__ == "__main__":
    main()
