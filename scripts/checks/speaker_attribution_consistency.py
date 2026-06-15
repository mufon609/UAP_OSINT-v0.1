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
  - anchor landing in a ``foreign-prepared`` / ``foreign-recitation`` turn
    (an in-room speaker reading their own statement / a document aloud) →
    the quote's speaker_id IS that known reader, so it is **accepted**; it
    becomes an **error** only when the read-aloud span is unambiguously
    bracketed by a single in-room speaker who is NOT the attributed one
    (a genuine misattribution).
  - unresolvable anchor (timestamp absent / not a caption tick), speaker
    unmappable between layers, or anchor landing in a non-speaker foreign
    turn (music / ad-read / intro / archival / …) → **warn** (can't confirm;
    don't block a commit on resolution ambiguity).

A quote whose source has no verified attribution sibling is skipped —
sibling-*presence* is a separate concern (the ``/prepare-transcript-sibling``
eligibility gate), not this check's job.
"""

import bisect
from pathlib import Path

import yaml

from checks import Issue
from checks._research_utils import entries
from lib._common import strict_yaml_load


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


def build_line_ts_map(src_path):
    """Return ``{1-indexed line number: seconds}`` for every source line whose
    first token is a ``[MM:SS]`` / ``[H:MM:SS]`` caption tick. Keying by line
    lets a turn's ``line_range`` resolve directly to the seconds it spans.
    Hour-format ticks are parsed correctly (``_ts_to_seconds`` handles 2- and
    3-part tokens), so sources past 1 h are fully covered. ``{}`` if the file
    can't be read; lines without a leading tick (headers, blanks, wrapped
    continuations) are absent from the map.

    The single line→seconds source of truth shared by
    ``scripts/build/finalize-attribution.py`` (stamps per-turn
    ``start_ts``/``end_ts``), ``scripts/build/validate-speaker-attribution.py``
    (recompute-and-compare), and ``scripts/tools/spot-check-attribution.py``
    (the active-speaker fold gate's burst windows — previously ``[MM:SS]``-only, which
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


# Seconds of slop applied to a quote's anchor span when collecting the turns it
# touches. The line-based resolver this replaces padded ±1 source line to absorb
# (a) a `[MM:SS]` anchor sitting one caption line off the first content word and
# (b) a sub-line speaker transition. One caption line ≈ one inter-tick gap.
# Empirically calibrated against the line-based resolver: swept 0–5s over every
# sibling-backed quote in the repo, 2s is the value at which the per-turn-
# timestamp span EXACTLY reproduces the old line-based span (0 divergences); 0–1s
# drop a boundary speaker, ≥3s start over-including. This is the calibration's
# differential gate. (`anchor_turn` is ε-independent — it matches the
# old nearest-preceding resolution at every ε.)
ANCHOR_TOLERANCE_S = 2


def resolve_anchor_turns(sibling, start_secs, end_secs):
    """Resolve a quote's ``[start_secs, end_secs]`` anchor to the sibling turn(s)
    it touches, purely from the per-turn ``start_ts`` — no source re-read.

    Returns ``(anchor_turn, span_turns, status)``:
      - ``anchor_turn`` — the turn whose contiguous interval owns ``start_secs``
        (each timed turn *i* owns ``[start_ts_i, start_ts_{i+1})``; the nearest
        ``start_ts`` at or before ``start_secs``). This is equivalent to the old
        nearest-preceding-caption-tick resolution: the nearest tick ≤ T lies in
        the turn that owns T.
      - ``span_turns`` — every timed turn whose contiguous interval intersects
        ``[start_secs, end_secs]`` widened by ``ANCHOR_TOLERANCE_S`` (the
        boundary slop that the old ±1-line pad provided).
      - ``status`` — ``"ok"``; ``"pre-first-tick"`` when ``start_secs`` precedes
        the first timed turn (no speaker established yet, → warn); or
        ``"no-timed-turns"`` for a sibling with no timestamped turn.

    Trusts the sibling's timestamps: ``validate-speaker-attribution.py``
    recomputes them from the source and FATALs on drift (same gate chain), so
    staleness is caught upstream rather than re-derived here."""
    timed = [
        (t["start_ts"], t)
        for t in (sibling.get("turns") or [])
        if isinstance(t, dict) and isinstance(t.get("start_ts"), int)
    ]
    if not timed:
        return None, [], "no-timed-turns"
    timed.sort(key=lambda st: st[0])
    starts = [s for s, _ in timed]
    if start_secs < starts[0]:
        return None, [], "pre-first-tick"

    ai = bisect.bisect_right(starts, start_secs) - 1
    anchor_turn = timed[ai][1]

    lo = start_secs - ANCHOR_TOLERANCE_S
    hi = end_secs + ANCHOR_TOLERANCE_S
    span_turns = []
    for i, (s, t) in enumerate(timed):
        nxt = starts[i + 1] if i + 1 < len(timed) else float("inf")
        if s <= hi and nxt > lo:  # contiguous interval [s, nxt) intersects [lo, hi]
            span_turns.append(t)
    return anchor_turn, span_turns, "ok"


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
            data = strict_yaml_load(path.read_text(encoding="utf-8"))
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


def _live_ids(speaker_id):
    """The non-foreign (in-room) speaker ids of a turn's ``speaker_id``
    (string or mixed-exchange list), or ``[]`` for a foreign-* turn."""
    vals = speaker_id if isinstance(speaker_id, list) else [speaker_id]
    return [v for v in vals if isinstance(v, str) and not v.startswith("foreign-")]


def _bracketing_live_ids(sibling, anchor_turn):
    """Sibling-side speaker ids of the nearest live (non-foreign) turn on each
    side of ``anchor_turn`` — the in-room speaker(s) whose own speech brackets
    a read-aloud span. A single shared id means one speaker unambiguously owns
    the surrounding speech (the reader of an OWN-statement/recited span);
    two means the span sits at a hand-off and the reader is ambiguous from
    structure alone. Empty when no live neighbor exists on either side."""
    turns = sibling.get("turns") or []
    try:
        idx = next(i for i, t in enumerate(turns) if t is anchor_turn)
    except StopIteration:
        return set()
    out = set()
    for side in (reversed(turns[:idx]), turns[idx + 1:]):
        for t in side:
            live = _live_ids(t.get("speaker_id")) if isinstance(t, dict) else []
            if live:
                out.update(live)
                break
    return out


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

    # Per-sibling speaker lookup (id → speaker dict), built once per path.
    # Resolution itself reads no source file — it runs off the sibling's
    # per-turn start_ts, which validate-speaker-attribution.py has already
    # proven matches the source in the same gate chain.
    sib_speakers_cache = {}

    def _sib_speakers(spath, sibling):
        if spath not in sib_speakers_cache:
            sib_speakers_cache[spath] = {
                s.get("id"): s
                for s in (sibling.get("speakers") or [])
                if isinstance(s, dict)
            }
        return sib_speakers_cache[spath]

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

        anchor_turn, span_turns, status = resolve_anchor_turns(
            sibling, start_secs, end_secs
        )
        if status == "pre-first-tick":
            yield Issue(
                ctx.rel, "warn",
                f"quotes[{i}] ({q.get('id')!r}): anchor {loc} precedes the "
                f"first timed turn in the attribution sibling for {spath} — "
                f"speaker_id not cross-checked",
                check_name=CHECK_NAME,
            )
            continue
        if status != "ok":
            continue  # sibling has no resolvable timeline — nothing to check

        sib_speakers = _sib_speakers(spath, sibling)

        # Speakers active across the turns the quote spans (anchor + boundary
        # slop), live (non-foreign) only.
        live_sibling_ids = []
        for turn in span_turns:
            tsid = turn.get("speaker_id")
            for one in (tsid if isinstance(tsid, list) else [tsid]):
                if isinstance(one, str) and not one.startswith("foreign-"):
                    live_sibling_ids.append(one)

        anchor_sid = anchor_turn.get("speaker_id") if anchor_turn else None
        anchor_lr = anchor_turn.get("line_range") if anchor_turn else None
        q_ids = set(sid_q if isinstance(sid_q, list) else [sid_q])

        # Anchor turn is foreign-*. `foreign-prepared` (an in-room speaker
        # reading their OWN written statement) and `foreign-recitation` (an
        # in-room speaker reading a document aloud) are SPOKEN by a known
        # in-room person: the quote's speaker_id IS that reader — a declared
        # speaker (quotes.py enforces that), not an unknown/foreign voice.
        # Knowing who is reading is the whole point, so there is nothing
        # editorial to flag — accept it. The one real fault is a contradiction:
        # the read-aloud span is unambiguously bracketed by a single in-room
        # speaker who is NOT the attributed one — a genuine misattribution,
        # which errors like any live mismatch.
        if isinstance(anchor_sid, str) and anchor_sid.startswith("foreign-"):
            if anchor_sid in ("foreign-prepared", "foreign-recitation"):
                bracket_art = set()
                for b in _bracketing_live_ids(sibling, anchor_turn):
                    art_id = _map_to_artifact(sib_speakers.get(b))
                    if art_id is not None:
                        bracket_art.add(art_id)
                if len(bracket_art) == 1 and not (bracket_art & q_ids):
                    reader = next(iter(bracket_art))
                    yield Issue(
                        ctx.rel, "error",
                        f"quotes[{i}] ({q.get('id')!r}): anchor {loc} lands in a "
                        f"{anchor_sid} span (lines {anchor_lr}) read by "
                        f"{reader} ({_id_name(reader, art_speakers)}), but the "
                        f"quote is attributed to "
                        + ", ".join(
                            f"{e} ({_id_name(e, art_speakers)})"
                            for e in sorted(q_ids)
                        ),
                        check_name=CHECK_NAME,
                    )
                continue
            # Genuinely non-in-room foreign content (music / ad-read / intro /
            # outro / narration / jingle / archival / other): no in-room
            # speaker owns these words, so an in-room speaker_id anchored here
            # points at the wrong tick. Worth a look, not a hard error.
            yield Issue(
                ctx.rel, "warn",
                f"quotes[{i}] ({q.get('id')!r}): anchor {loc} lands in a "
                f"non-speaker foreign turn ({anchor_sid!r}, lines {anchor_lr}) "
                f"— verify the [MM:SS] anchor points at in-room speech, not "
                f"{anchor_sid} content",
                check_name=CHECK_NAME,
            )
            continue

        if not live_sibling_ids:
            yield Issue(
                ctx.rel, "warn",
                f"quotes[{i}] ({q.get('id')!r}): anchor {loc} lands in a "
                f"non-conversational turn ({anchor_sid!r}, lines {anchor_lr}) "
                f"in the attribution sibling — verify the [MM:SS] anchor points "
                f"at the first content word of the attributed speaker",
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

        if expected & q_ids:
            continue  # consistent

        exp_names = ", ".join(
            f"{e} ({_id_name(e, art_speakers)})" for e in sorted(expected)
        )
        yield Issue(
            ctx.rel, "error",
            f"quotes[{i}] ({q.get('id')!r}): speaker_id {sid_q!r} disagrees "
            f"with the attribution sibling — anchor {loc} resolves to the turn "
            f"covering lines {anchor_lr}, which the sibling attributes to "
            f"{exp_names}. Fix the quote's speaker_id, or re-check that the "
            f"[MM:SS] anchor points at the first content word of the quoted "
            f"speaker.",
            check_name=CHECK_NAME,
        )
