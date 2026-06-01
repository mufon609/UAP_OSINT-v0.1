"""speaker_attribution_consistency check — cross-validates each transcript
quote's ``speaker_id`` against the verified speaker-attribution sibling.

The seam this closes. The attribution sibling
(``sources/transcripts/{slug}-attribution.yaml``) indexes the source
caption file by 1-indexed **line range**; transcript-artifact quotes anchor
by ``[MM:SS]`` **timestamp**. ``quotes.py`` only confirms a quote's
``speaker_id`` resolves to one of the artifact's own ``speakers[].id`` — it
does not confirm the chosen speaker agrees with the sibling's attribution at
that point in the transcript. This check is the cross-validator the schema
(``meta/schema-speaker-attribution.yaml`` :: "Cross-schema integration
points") specifies: it resolves each quote's ``[MM:SS]`` → source line →
covering sibling turn, maps the sibling's speaker to the artifact's speaker
by ``node_link`` / name, and asserts agreement.

Why map by name / node_link, never by raw id. The sibling's ``speakers[]``
and the artifact's ``speakers[]`` are authored independently and their ids
routinely disagree — in ``jre-2194-elizondo-2024`` they are swapped
(sibling ``s1``=Joe Rogan / ``s2``=Luis Elizondo vs. artifact ``s1``=Luis
Elizondo / ``s2``=Joe Rogan). A naive id comparison would be backwards.

Boundary tolerance. A single source line can pack the tail of one turn and
the head of the next (auto-caption ``[MM:SS]`` ticks don't split on speaker
change), and a quote's first words routinely sit mid-line after a narrator
lead-in. So a quote is checked against every speaker active across the lines
it **spans** — both endpoints of a ``[start]–[end]`` range location resolve
to source lines, padded ±1 — and is consistent if its attributed speaker
appears anywhere in that span. This absorbs sub-line / lead-in boundaries
while still catching gross misattribution: a passage whose entire span sits
inside one speaker's turn but is attributed to the other still fails.

Severity.
  - clean live-vs-live mismatch → **error** (schema: "Drift = data error
    routed by route_failure.py to the artifact-data fix role").
  - unresolvable anchor (timestamp absent / not a caption tick), speaker
    unmappable between layers, or anchor landing in a ``foreign-*`` /
    non-conversational turn → **warn** (can't confirm; don't block a commit
    on resolution ambiguity).

A quote whose source has no verified attribution sibling is skipped —
sibling-*presence* is a separate concern (the ``/prepare-transcript-sibling``
eligibility gate), not this check's job.
"""

import bisect
from pathlib import Path

import yaml

from checks import Issue
from checks._research_utils import entries


CHECK_NAME = "speaker_attribution_consistency"

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SOURCES_DIR = _REPO_ROOT / "sources"
_TRANSCRIPTS_DIR = _SOURCES_DIR / "transcripts"

# Leading honorific tokens stripped before name-matching a sibling speaker to
# an artifact speaker. The two speakers[] lists are authored independently, so
# one side carrying "Dr." / "Rep." and the other the bare name is common and
# must not read as two different people (e.g. sibling "Colm Kelleher" vs.
# artifact "Dr. Colm Kelleher"). node_link is the preferred, honorific-immune
# anchor; this normalizer is the fallback when one side lacks a node_link.
_HONORIFICS = frozenset({
    "dr", "mr", "mrs", "ms", "miss", "prof", "professor", "rep", "sen",
    "sir", "gen", "col", "lt", "capt", "maj", "adm", "hon", "fr", "rev",
    "the", "mx",
})


def _ts_to_seconds(token):
    """Parse a ``[M:SS]`` / ``[MM:SS]`` / ``[H:MM:SS]`` caption-tick token
    to integer seconds, or None if it isn't one. Tolerant of leading-zero
    differences (``[1:52]`` vs ``[01:52]``) since it compares by value."""
    if not isinstance(token, str):
        return None
    s = token.strip()
    if not (s.startswith("[") and s.endswith("]")):
        return None
    parts = s[1:-1].split(":")
    if not (2 <= len(parts) <= 3) or not all(p.isdigit() for p in parts):
        return None
    nums = [int(p) for p in parts]
    if len(parts) == 2:
        return nums[0] * 60 + nums[1]
    return nums[0] * 3600 + nums[1] * 60 + nums[2]


def _range_seconds(location):
    """``(start_seconds, end_seconds)`` from a ``source.location``: the first
    and last ``[MM:SS]`` ticks it carries. A single-anchor location yields
    ``start == end``; the range form (``[start]–[end]``, en-dash separated —
    the dominant form across the transcript corpus) yields the span the quote
    covers. ``(None, None)`` if it carries no parseable tick."""
    if not isinstance(location, str):
        return None, None
    ticks = []
    i = 0
    while True:
        lb = location.find("[", i)
        if lb == -1:
            break
        rb = location.find("]", lb)
        if rb == -1:
            break
        secs = _ts_to_seconds(location[lb : rb + 1])
        if secs is not None:
            ticks.append(secs)
        i = rb + 1
    if not ticks:
        return None, None
    return ticks[0], ticks[-1]


def _parse_range(line_range):
    """Return ``(lo, hi)`` inclusive for a ``"N"`` / ``"N-M"`` line_range,
    or ``(None, None)`` if malformed."""
    s = str(line_range).strip()
    if "-" in s:
        a, _, b = s.partition("-")
        if a.strip().isdigit() and b.strip().isdigit():
            return int(a), int(b)
        return None, None
    if s.isdigit():
        return int(s), int(s)
    return None, None


def _build_source_index(src_path):
    """Read the raw caption file and return ``(seconds → 1-indexed line,
    total_lines)``. Only lines whose first token is a ``[MM:SS]`` tick are
    indexed; the first line bearing a given timestamp wins (the anchor
    convention points at the quote's first content word). ``(None, 0)`` if
    the file can't be read. Lines are 1-indexed to match the sibling's
    line_range coordinate (``splitlines()`` count equals the
    ``sum(1 for _ in f)`` count that ``validate-speaker-attribution.py``
    writes into ``source_line_count``)."""
    try:
        lines = src_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None, 0
    index = {}
    for n, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if not stripped.startswith("["):
            continue
        end = stripped.find("]")
        if end == -1:
            continue
        secs = _ts_to_seconds(stripped[: end + 1])
        if secs is None:
            continue
        index.setdefault(secs, n)
    return index, len(lines)


def build_line_ts_map(src_path):
    """Return ``{1-indexed line number: seconds}`` for every source line whose
    first token is a ``[MM:SS]`` / ``[H:MM:SS]`` caption tick — the inverse
    view of ``_build_source_index`` (which keys by seconds). Keying by line
    lets a turn's ``line_range`` resolve directly to the seconds it spans.
    Hour-format ticks are parsed correctly (``_ts_to_seconds`` handles 2- and
    3-part tokens), so sources past 1 h are fully covered. ``{}`` if the file
    can't be read; lines without a leading tick (headers, blanks, wrapped
    continuations) are absent from the map.

    The single line→seconds source of truth shared by
    ``scripts/build/finalize-attribution.py`` (W2 — stamps per-turn
    ``start_ts``/``end_ts``), ``scripts/build/validate-speaker-attribution.py``
    (recompute-and-compare), and ``scripts/tools/spot-check-attribution.py``
    (the W3 fold gate's burst windows — previously ``[MM:SS]``-only, which
    silently dropped hour-format turns)."""
    try:
        lines = src_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    out = {}
    for n, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if not stripped.startswith("["):
            continue
        end = stripped.find("]")
        if end == -1:
            continue
        secs = _ts_to_seconds(stripped[: end + 1])
        if secs is not None:
            out[n] = secs
    return out


def turn_ts_range(line_ts_map, lo, hi):
    """``(start_ts, end_ts)`` for an inclusive line range ``[lo, hi]``: the min
    and max caption-tick seconds among the timestamped lines it covers, or
    ``(None, None)`` when the range covers no timestamped line. (On a real
    transcript ticks rise monotonically, so min/max == first/last; min/max is
    robust to any local disorder.) Deterministic derivation shared by
    finalize-attribution.py (stamps the fields) and
    validate-speaker-attribution.py (recomputes and compares — the fields are
    tamper-evident, not hand-authored)."""
    secs = [line_ts_map[ln] for ln in range(lo, hi + 1) if ln in line_ts_map]
    if not secs:
        return None, None
    return min(secs), max(secs)


def _resolve_line(index, sorted_secs, target):
    """Resolve a target-seconds anchor to a 1-indexed source line via the
    **nearest preceding** caption tick (the tick at or before ``target``).
    Exact-tick anchors resolve to themselves; this also handles the
    irregular tick spacing of Whisper transcripts and range anchors whose
    start second falls between ticks. None if ``target`` precedes the first
    tick (no speaker established yet)."""
    if not sorted_secs:
        return None
    pos = bisect.bisect_right(sorted_secs, target) - 1
    if pos < 0:
        return None
    return index[sorted_secs[pos]]


def _build_line_map(sibling):
    """Return ``line_number → turn dict`` by expanding every turn's
    line_range. Overlaps don't occur on a validated sibling (turn_coverage
    guarantees each line covered once); last-writer-wins is harmless here."""
    line_map = {}
    for turn in sibling.get("turns") or []:
        if not isinstance(turn, dict):
            continue
        lo, hi = _parse_range(turn.get("line_range"))
        if lo is None:
            continue
        for ln in range(lo, hi + 1):
            line_map[ln] = turn
    return line_map


def _norm_name(name):
    """Canonicalize a display name for cross-layer matching: casefold, drop
    periods/commas, collapse whitespace, and strip leading honorific tokens
    (``_HONORIFICS``). '' if absent. Makes "Dr. Colm Kelleher" and
    "Colm Kelleher" compare equal."""
    if not isinstance(name, str):
        return ""
    toks = name.casefold().replace(".", " ").replace(",", " ").split()
    while toks and toks[0] in _HONORIFICS:
        toks.pop(0)
    return " ".join(toks)


def _norm_link(node_link):
    """Canonicalize a node_link to a leading-slash, no-trailing-slash form
    for cross-layer matching, or '' if absent."""
    s = str(node_link or "").strip().rstrip("/")
    if not s:
        return ""
    return "/" + s.lstrip("/")


def _load_siblings():
    """Glob every verified ``*-attribution.yaml`` and index it by the
    sources-relative path of its parent caption file (the form quotes use
    in ``source.path``). Keys strip the leading ``sources/`` from the
    sibling's repo-root-relative ``source_path``."""
    out = {}
    if not _TRANSCRIPTS_DIR.is_dir():
        return out
    for path in sorted(_TRANSCRIPTS_DIR.glob("*-attribution.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("verification_status") != "verified":
            continue
        sp = data.get("source_path")
        if not isinstance(sp, str) or not sp.strip():
            continue
        rel = sp[len("sources/"):] if sp.startswith("sources/") else sp
        out[rel] = data
    return out


def _id_name(art_id, art_speakers):
    """Display name for an artifact speaker id (falls back to the id)."""
    for s in art_speakers:
        if isinstance(s, dict) and s.get("id") == art_id:
            return str(s.get("name") or art_id)
    return str(art_id)


def check(ctx):
    if ctx.target_type != "transcript":
        return

    siblings = _load_siblings()
    if not siblings:
        return

    art_speakers = entries(ctx.data, "speakers")
    # Artifact-side lookup: node_link (preferred) and name → artifact id.
    art_by_link = {}
    art_by_name = {}
    for s in art_speakers:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        if not sid:
            continue
        link = _norm_link(s.get("node_link"))
        if link:
            art_by_link[link] = sid
        name = _norm_name(s.get("name"))
        if name:
            art_by_name[name] = sid

    def _map_to_artifact(sib_speaker):
        """Sibling speaker dict → this artifact's speaker id, by node_link
        (preferred, honorific-immune) then normalized name. None when
        neither side carries a shared anchor."""
        if not isinstance(sib_speaker, dict):
            return None
        link = _norm_link(sib_speaker.get("node_link"))
        if link and link in art_by_link:
            return art_by_link[link]
        return art_by_name.get(_norm_name(sib_speaker.get("name")))

    # Per-source caches: resolved index/line-map (built once per path).
    src_cache = {}

    def _resolve_source(spath, sibling):
        if spath in src_cache:
            return src_cache[spath]
        index, total = _build_source_index(_SOURCES_DIR / spath)
        declared = sibling.get("source_line_count")
        # Unreadable source, OR a stale sibling whose source changed
        # underneath it (line→turn mapping unreliable) — skip silently.
        # validate-speaker-attribution.py owns the drift case and fatals on
        # it in the same gate chain.
        if index is None or (isinstance(declared, int) and declared != total):
            src_cache[spath] = (None, [], {}, {})
            return src_cache[spath]
        sorted_secs = sorted(index)
        line_map = _build_line_map(sibling)
        sib_speakers = {
            s.get("id"): s
            for s in (sibling.get("speakers") or [])
            if isinstance(s, dict)
        }
        src_cache[spath] = (index, sorted_secs, line_map, sib_speakers)
        return src_cache[spath]

    for i, q in enumerate(entries(ctx.data, "quotes")):
        if not isinstance(q, dict):
            continue
        src = q.get("source")
        if not isinstance(src, dict):
            continue  # quotes.py errors on a malformed source
        spath = src.get("path")
        sibling = siblings.get(spath)
        if sibling is None:
            continue  # no verified sibling for this source — not our concern
        sid_q = q.get("speaker_id")
        if not sid_q:
            continue  # quotes.py errors on missing speaker_id

        loc = src.get("location")
        start_secs, end_secs = _range_seconds(loc)
        if start_secs is None:
            yield Issue(
                ctx.rel, "warn",
                f"quotes[{i}] ({q.get('id')!r}): speaker_id not cross-checked "
                f"against the attribution sibling — source.location {loc!r} "
                f"is not a resolvable [MM:SS] anchor",
                check_name=CHECK_NAME,
            )
            continue

        index, sorted_secs, line_map, sib_speakers = _resolve_source(spath, sibling)
        if index is None:
            continue  # unreadable / stale source — flagged elsewhere
        start_line = _resolve_line(index, sorted_secs, start_secs)
        if start_line is None:
            yield Issue(
                ctx.rel, "warn",
                f"quotes[{i}] ({q.get('id')!r}): anchor {loc} precedes the "
                f"first caption tick in {spath} — speaker_id not cross-checked "
                f"against the attribution sibling",
                check_name=CHECK_NAME,
            )
            continue
        end_line = _resolve_line(index, sorted_secs, end_secs) or start_line

        # Speakers active across the lines the quote spans, padded ±1 to
        # absorb sub-line / narrator-lead-in boundaries.
        lo = min(start_line, end_line) - 1
        hi = max(start_line, end_line) + 1
        span_turns = [line_map[ln] for ln in range(lo, hi + 1) if ln in line_map]
        live_sibling_ids = []
        for turn in span_turns:
            tsid = turn.get("speaker_id")
            for one in (tsid if isinstance(tsid, list) else [tsid]):
                if isinstance(one, str) and not one.startswith("foreign-"):
                    live_sibling_ids.append(one)

        anchor_turn = line_map.get(start_line)
        anchor_sid = anchor_turn.get("speaker_id") if anchor_turn else None
        line_no = start_line  # cited in messages below

        if not live_sibling_ids:
            yield Issue(
                ctx.rel, "warn",
                f"quotes[{i}] ({q.get('id')!r}): anchor {loc} (source line "
                f"{line_no}) lands in a non-conversational turn "
                f"({anchor_sid!r}) in the attribution sibling — verify the "
                f"[MM:SS] anchor points at the first content word of the "
                f"attributed speaker",
                check_name=CHECK_NAME,
            )
            continue

        expected = set()
        for lid in live_sibling_ids:
            art_id = _map_to_artifact(sib_speakers.get(lid))
            if art_id is not None:
                expected.add(art_id)
        if not expected:
            yield Issue(
                ctx.rel, "warn",
                f"quotes[{i}] ({q.get('id')!r}): the sibling's anchor-turn "
                f"speaker(s) {sorted(set(live_sibling_ids))} could not be "
                f"matched to this artifact's speakers[] by node_link or name "
                f"— speaker_id not cross-checked",
                check_name=CHECK_NAME,
            )
            continue

        q_ids = set(sid_q if isinstance(sid_q, list) else [sid_q])
        if expected & q_ids:
            continue  # consistent

        exp_names = ", ".join(
            f"{e} ({_id_name(e, art_speakers)})" for e in sorted(expected)
        )
        yield Issue(
            ctx.rel, "error",
            f"quotes[{i}] ({q.get('id')!r}): speaker_id {sid_q!r} disagrees "
            f"with the attribution sibling — anchor {loc} resolves to source "
            f"line {line_no}, which the sibling attributes to {exp_names}. "
            f"Fix the quote's speaker_id, or re-check that the [MM:SS] anchor "
            f"points at the first content word of the quoted speaker.",
            check_name=CHECK_NAME,
        )
