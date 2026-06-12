#!/usr/bin/env python3
"""finalize-attribution.py — strip verification scaffolding from a speaker-
attribution sibling, leaving a structured-only verified artifact.

`rationale`, `verifier_notes`, and `needs_image_verification` are DRAFT-PHASE
scaffolding: the producer emits the cue for each contested boundary (and flags
turns it wants confirmed against frames), the independent verifier checks them
against the source. Once the sibling is verified that scaffolding has served its
purpose — it isn't load-bearing on the committed artifact, it eats tokens, and
the prose renders into the `-attributed.md`. This tool removes it deterministically
(agents emit/judge; scripts mutate), so a verified sibling carries only its
structured fields. `confidence: low|medium` remains as the durable uncertainty
marker (alongside any `image_verification[]` resolution); an investigator reads
the source lines to judge any boundary.

Stripped: every turn's `rationale` + `verifier_notes` + `needs_image_verification`,
the top-level `verifier_notes`, and any `contributor_notes` on an
image_verification entry.
Kept: all structured fields, `confidence`, `referenced_source`, speaker
`notes`, `image_verification` (turn_line_range / resolution /
resolved_speaker_id / resolved_by).

Computed: a top-level `source_content_hash` (sha256 of the raw source
bytes — the strong drift detector) and per-turn `start_ts`/`end_ts` (the
caption-tick span of each turn's line_range, hour-format aware). Both are
derived deterministically from the source and are tamper-evident:
`validate-speaker-attribution.py` recomputes and compares. Stamped in both
--video and --no-video modes (pure source read).

Active-speaker fold gate — finalize is mechanically gated on the active-
speaker spot-check. There is NO graceful skip: a sibling whose source has a
recording cannot be finalized unless the spot-check runs clean.

  ./finalize-attribution.py SIBLING.yaml --verifier-session SESSION_ID --video VIDEO.mp4
  ./finalize-attribution.py SIBLING.yaml --verifier-session SESSION_ID --no-video

  - `--video PATH`  runs scripts/tools/spot-check-attribution.py across ALL
    turns; any UNSETTLED `contested-fold` verdict (another in-transcript
    speaker is the active on-camera speaker) BLOCKS finalize and routes back
    to the producer/verifier. Framing false-positives (two-shots, cutaways,
    voiceover) are handled by the dominance + active-speaker + duration
    guards — but the engine can still mis-fire where those guards can't see
    (sub-100px remote-guest tiles, listener mouth motion over a long window),
    so a fold means EITHER a wrong label or an engine miss. The settlement
    record is `image_verification[]` (the schema's durable fold-settlement
    record, written via `--resolve-turn`): a contested-fold turn whose
    line_range carries an entry that still matches the turn's current
    `speaker_id` is SETTLED — reported with its resolution + resolver, not
    blocking. A frame-level adjudication outranks the engine heuristic; an
    entry that no longer matches the turn is STALE and blocks until
    re-adjudicated.
  - `--no-video`  the explicit, honest opt-out for a genuinely audio-only
    source (no recording to verify against). Recorded as the contributor's
    assertion; the source's `confidence` markers carry the residual.
  - neither       refused — the gate is not skippable by omission.

On an already-verified sibling (re-finalize / migration), --verifier-session
may be omitted — the existing one is kept; the fold gate still runs. Run
`validate-speaker-attribution.py` afterwards; a verified sibling that still
carries scaffolding is a FATAL there (this tool is what clears it).

Fold-gate adjudication — `--resolve-turn`. When the gate blocks (or an
image check otherwise settles a turn), the *judgment* of who is speaking is
the agent's / contributor's, but the *write* is this tool's (agents emit/
judge; scripts mutate — the sibling skill carries no Edit tool on purpose):

  ./finalize-attribution.py SIBLING.yaml --resolve-turn 478-512 \
      --speaker s2 --resolution corrected --resolved-by agent-verifier --write

Relabels the turn's `speaker_id` (for corrected/ambiguous; `--speaker`
accepts `s2`, a `foreign-*` kind, or a mixed-exchange list `s1,s2`) and
records the structured `image_verification[]` entry (replacing an earlier
entry for the same turn on re-adjudication). Validates the turn exists, the
speaker ids are in `speakers[]`, and the resolution agrees with the relabel
(corrected must change the label; confirmed must not). Dry run by default;
`--write` applies. Then re-run `validate-speaker-attribution.py` and
re-finalize — the recorded adjudication settles that turn's engine verdict
(reported, never silent), so the gate blocks only on unadjudicated or
stale folds.

`--selftest` runs the gate's partition logic (settled / stale / blocking)
on synthetic rows — no video or .venv-face needed.
"""

import argparse
import csv
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib._common import REPO_ROOT, strict_yaml_load  # noqa: E402
from checks.speaker_attribution_consistency import (  # noqa: E402
    _parse_range,
    build_line_ts_map,
    turn_ts_range,
)

SPOT_CHECK = REPO_ROOT / "scripts" / "tools" / "spot-check-attribution.py"

HEADER = (
    "# Speaker-attribution sibling — verified, structured-only. Verification\n"
    "# scaffolding (rationale / verifier_notes / needs_image_verification) was\n"
    "# stripped by\n"
    "# scripts/build/finalize-attribution.py once the independent verifier\n"
    "# passed; source_content_hash + per-turn start_ts/end_ts are machine-\n"
    "# computed from the source by the same tool (tamper-evident, regeneratable).\n"
    "# Indexes into the source transcript by 1-indexed line range;\n"
    "# references only, no transcript text. Conforms to\n"
    "# meta/schema-speaker-attribution.yaml.\n"
)


def _partition_contested(contested: list, data: dict) -> tuple:
    """Split the engine's `contested-fold` rows into (blocking, settled)
    against the sibling's recorded `image_verification[]` adjudications.

    A frame-level adjudication outranks the engine heuristic: a row whose
    line_range carries an entry is SETTLED — reported, never blocking —
    provided the entry still describes the turn (its `resolved_speaker_id`
    equals the turn's current `speaker_id`; a mismatch means the turn was
    relabeled after the adjudication, so the entry is STALE and the row
    blocks until re-adjudicated). Every resolution settles (confirmed /
    corrected / ambiguous): each is a recorded frame read, and `confidence`
    on the turn stays the durable uncertainty marker.

    Returns (blocking, settled): blocking is [(row, stale_entry_or_None)],
    settled is [(row, entry)]."""
    turns = {str(t.get("line_range")): t
             for t in data.get("turns") or [] if isinstance(t, dict)}
    entries = {str(e.get("turn_line_range")): e
               for e in data.get("image_verification") or []
               if isinstance(e, dict)}
    blocking, settled = [], []
    for row in contested:
        lr = str(row.get("line_range"))
        entry = entries.get(lr)
        if entry is None:
            blocking.append((row, None))
        elif (turns.get(lr) or {}).get("speaker_id") != entry.get("resolved_speaker_id"):
            blocking.append((row, entry))
        else:
            settled.append((row, entry))
    return blocking, settled


def run_fold_gate(sibling_path: Path, video_path: Path) -> tuple:
    """Fold gate — run the active-speaker spot-check across all turns and
    partition the `contested-fold` rows against the sibling's recorded
    `image_verification[]` adjudications (`_partition_contested`). Returns
    (blocking, settled); any blocking row refuses finalize. Exits non-zero if
    the spot-check itself cannot run (missing video / .venv-face): no graceful
    skip — an unrunnable gate blocks finalize rather than passing silently."""
    out_csv = Path(tempfile.mkdtemp(prefix="finalize-foldgate-")) / "spot-check.csv"
    cmd = [sys.executable, str(SPOT_CHECK), str(sibling_path),
           "--video", str(video_path), "--output", str(out_csv)]
    print("Active-speaker fold gate: running spot-check across all turns…")
    if subprocess.run(cmd).returncode != 0 or not out_csv.is_file():
        sys.exit(
            "error: active-speaker fold gate could not run the spot-check (video + .venv-face "
            "are required; no graceful skip). Fix the environment, or use "
            "--no-video for a genuinely audio-only source."
        )
    with out_csv.open() as f:
        contested = [r for r in csv.DictReader(f) if r.get("verdict") == "contested-fold"]
    if not contested:
        return [], []
    with sibling_path.open() as f:
        data = strict_yaml_load(f)
    if not isinstance(data, dict):
        sys.exit("error: sibling is not a YAML mapping")
    return _partition_contested(contested, data)


def finalize(data: dict, verifier_session: str | None) -> dict:
    """Set verified status + session and strip scaffolding. Returns counts."""
    if verifier_session:
        data["verification_status"] = "verified"
        data["verifier_session"] = verifier_session
    else:
        if data.get("verification_status") != "verified" or not data.get("verifier_session"):
            sys.exit(
                "error: sibling is not verified and no --verifier-session given. "
                "Finalize only an independent-verifier-approved sibling."
            )

    counts = {"rationale": 0, "turn_verifier_notes": 0,
              "top_verifier_notes": 0, "needs_image_verification": 0,
              "contributor_notes": 0}

    if data.pop("verifier_notes", None) is not None:
        counts["top_verifier_notes"] = 1
    for t in data.get("turns") or []:
        if isinstance(t, dict):
            if t.pop("rationale", None) is not None:
                counts["rationale"] += 1
            if t.pop("verifier_notes", None) is not None:
                counts["turn_verifier_notes"] += 1
            if t.pop("needs_image_verification", None) is not None:
                counts["needs_image_verification"] += 1
    for e in data.get("image_verification") or []:
        if isinstance(e, dict) and e.pop("contributor_notes", None) is not None:
            counts["contributor_notes"] += 1
    return counts


def _set_after(d: dict, anchor_key: str, new_key: str, value) -> None:
    """Insert/replace `new_key` immediately after `anchor_key`, preserving the
    rest of the key order (falls back to end if the anchor is absent). Mutates
    `d` in place. Idempotent: a pre-existing `new_key` anywhere is removed
    first, so re-finalize lands it in the same position → byte-stable dump."""
    d.pop(new_key, None)
    rebuilt = {}
    for k, v in d.items():
        rebuilt[k] = v
        if k == anchor_key:
            rebuilt[new_key] = value
    if new_key not in rebuilt:
        rebuilt[new_key] = value
    d.clear()
    d.update(rebuilt)


def stamp_computed_fields(source_path: Path, data: dict) -> dict:
    """Stamp the derived, tamper-evident fields from the source file:
    a top-level `source_content_hash` (sha256 of the raw bytes) and per-turn
    `start_ts`/`end_ts` (the caption-tick span of each turn's line_range, via
    the shared hour-aware `build_line_ts_map`/`turn_ts_range`). Both are
    regeneratable from (source, line_range) — `validate-speaker-attribution.py`
    recomputes and compares. Deterministic + idempotent: fields are popped then
    re-set in a fixed position, so re-finalizing an unchanged sibling produces
    byte-identical output. Returns counts for the summary."""
    digest = "sha256:" + hashlib.sha256(source_path.read_bytes()).hexdigest()
    _set_after(data, "source_line_count", "source_content_hash", digest)

    line_ts = build_line_ts_map(source_path)
    counts = {"timed": 0, "untimed": 0}
    for t in data.get("turns") or []:
        if not isinstance(t, dict):
            continue
        # pop-then-(maybe)-set last → stable key order across re-finalize
        t.pop("start_ts", None)
        t.pop("end_ts", None)
        lo, hi = _parse_range(t.get("line_range"))
        start, end = (None, None) if lo is None else turn_ts_range(line_ts, lo, hi)
        if start is None:
            counts["untimed"] += 1
            continue
        t["start_ts"] = start
        t["end_ts"] = end
        counts["timed"] += 1
    return counts


def _parse_speaker_spec(data: dict, spec: str):
    """Parse `--speaker` into a turn-shaped speaker_id value: a speakers[].id
    string, a `foreign-*` kind, or a 2+ mixed-exchange list (`s1,s2` — ids
    only, per the schema). Validates every token against speakers[]."""
    speaker_ids = {s.get("id") for s in data.get("speakers") or []
                   if isinstance(s, dict)}
    tokens = [t.strip() for t in spec.split(",") if t.strip()]
    if not tokens:
        sys.exit("error: --speaker is empty")
    if len(tokens) == 1:
        tok = tokens[0]
        if tok not in speaker_ids and not tok.startswith("foreign-"):
            sys.exit(f"error: --speaker {tok!r} matches no speakers[].id "
                     f"({sorted(speaker_ids)}) and is not a foreign-* kind")
        return tok
    bad = [t for t in tokens if t not in speaker_ids]
    if bad:
        sys.exit(f"error: mixed-exchange list may contain only speakers[].id "
                 f"({sorted(speaker_ids)}); not: {bad}")
    return tokens


def resolve_turn(data: dict, line_range: str, resolved, resolution: str,
                 resolved_by: str):
    """Apply one fold-gate adjudication: relabel the turn's `speaker_id` (for
    corrected/ambiguous) and upsert the structured `image_verification[]`
    entry for that turn. The judgment is the caller's; this is only the write.
    Returns (old_speaker_id, replaced_existing_entry)."""
    turn = next((t for t in data.get("turns") or []
                 if isinstance(t, dict)
                 and str(t.get("line_range")) == line_range), None)
    if turn is None:
        sys.exit(f"error: no turn with line_range {line_range!r} "
                 f"(it must match a turns[].line_range exactly — the form the "
                 f"fold gate prints)")
    current = turn.get("speaker_id")
    if resolution == "corrected" and current == resolved:
        sys.exit(f"error: resolution=corrected but the turn already carries "
                 f"{current!r} — use confirmed for image evidence that "
                 f"supports the existing label")
    if resolution == "confirmed" and current != resolved:
        sys.exit(f"error: resolution=confirmed but the turn carries "
                 f"{current!r}, not {resolved!r} — use corrected to relabel")
    if resolution in ("corrected", "ambiguous"):
        turn["speaker_id"] = resolved
    entry = {"turn_line_range": line_range, "resolution": resolution,
             "resolved_speaker_id": resolved, "resolved_by": resolved_by}
    ivs = data.setdefault("image_verification", [])
    for i, e in enumerate(ivs):
        if isinstance(e, dict) and e.get("turn_line_range") == line_range:
            ivs[i] = entry
            return current, True
    ivs.append(entry)
    return current, False


def cmd_resolve(args, path: Path) -> None:
    """`--resolve-turn` mode — the draft-phase adjudication write."""
    for val, name in ((args.speaker, "--speaker"),
                      (args.resolution, "--resolution"),
                      (args.resolved_by, "--resolved-by")):
        if not val:
            sys.exit(f"error: --resolve-turn requires {name}")
    if args.video or args.no_video or args.verifier_session:
        sys.exit("error: --resolve-turn is the adjudication write only — it "
                 "takes no gate/session flags (re-run finalize afterwards)")
    with path.open() as f:
        data = strict_yaml_load(f)
    if not isinstance(data, dict):
        sys.exit("error: sibling is not a YAML mapping")

    resolved = _parse_speaker_spec(data, args.speaker)
    old, replaced = resolve_turn(data, args.resolve_turn, resolved,
                                 args.resolution, args.resolved_by)

    print(f"Turn {args.resolve_turn}: speaker_id {old!r} -> {resolved!r} "
          f"({args.resolution}, by {args.resolved_by})")
    print(f"image_verification[]: entry "
          f"{'replaced for re-adjudication' if replaced else 'appended'}")
    if not args.write:
        print("\nDRY RUN — nothing written; pass --write to apply, then re-run "
              "validate-speaker-attribution.py + finalize")
        return
    body = yaml.safe_dump(data, sort_keys=False, default_flow_style=False,
                          allow_unicode=True, width=4096)
    prefix = HEADER + "\n" if data.get("verification_status") == "verified" else ""
    with path.open("w") as f:
        f.write(prefix + body)
    print(f"\nApplied to {path}")
    print("Next: validate-speaker-attribution.py, then re-run finalize — the "
          "recorded adjudication settles this turn's engine verdict (reported, "
          "never silent); the gate blocks only on unadjudicated/stale folds")


def cmd_selftest() -> int:
    """Exercise `_partition_contested` on synthetic rows — settled (all three
    resolutions), stale, unadjudicated, and list-valued speaker_id — with no
    video / .venv-face dependency."""
    failures = []
    data = {
        "turns": [
            {"line_range": "10-20", "speaker_id": "s1"},
            {"line_range": "30-40", "speaker_id": "s2"},
            {"line_range": "50-60", "speaker_id": ["s1", "s2"]},
            {"line_range": "70-80", "speaker_id": "s1"},
            {"line_range": "90-99", "speaker_id": "s2"},
        ],
        "image_verification": [
            {"turn_line_range": "10-20", "resolution": "confirmed",
             "resolved_speaker_id": "s1", "resolved_by": "contributor"},
            {"turn_line_range": "30-40", "resolution": "corrected",
             "resolved_speaker_id": "s2", "resolved_by": "agent-verifier"},
            {"turn_line_range": "50-60", "resolution": "ambiguous",
             "resolved_speaker_id": ["s1", "s2"], "resolved_by": "contributor"},
            {"turn_line_range": "70-80", "resolution": "corrected",
             "resolved_speaker_id": "s2", "resolved_by": "contributor"},
        ],
    }
    rows = [{"line_range": lr, "verdict": "contested-fold"}
            for lr in ("10-20", "30-40", "50-60", "70-80", "90-99")]
    blocking, settled = _partition_contested(rows, data)

    settled_lrs = {r.get("line_range") for r, _ in settled}
    if settled_lrs != {"10-20", "30-40", "50-60"}:
        failures.append(f"settled set wrong: {sorted(settled_lrs)} "
                        f"(expected confirmed + corrected + ambiguous matches, "
                        f"incl. the list-valued speaker_id)")
    by_lr = {r.get("line_range"): stale for r, stale in blocking}
    if set(by_lr) != {"70-80", "90-99"}:
        failures.append(f"blocking set wrong: {sorted(by_lr)}")
    # 70-80: entry says s2 but the turn carries s1 → stale, entry returned
    if not isinstance(by_lr.get("70-80"), dict):
        failures.append("stale adjudication did not return its entry")
    # 90-99: no entry at all → blocking with None
    if by_lr.get("90-99", "missing") is not None:
        failures.append("unadjudicated row should block with entry=None")
    # no contested rows → trivially clean partition
    if _partition_contested([], data) != ([], []):
        failures.append("empty contested list should partition to ([], [])")

    if failures:
        print(f"SELFTEST FAILED ({len(failures)}):")
        for msg in failures:
            print(f"  - {msg}")
        return 1
    print("selftest: 6 partition expectations green (settled confirmed/"
          "corrected/ambiguous + list speaker_id; stale + unadjudicated block)")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?",
                    help="path to {slug}-attribution.yaml (required except "
                         "with --selftest)")
    ap.add_argument("--verifier-session",
                    help="verifier agent session id (sets status=verified). "
                         "Optional when the sibling is already verified.")
    gate = ap.add_mutually_exclusive_group(required=False)
    gate.add_argument("--video", help="source recording — runs the active-speaker "
                                      "fold gate; contested-fold blocks finalize")
    gate.add_argument("--no-video", action="store_true",
                      help="explicit opt-out for a genuinely audio-only source "
                           "(no recording to verify against)")
    ap.add_argument("--resolve-turn", metavar="LINE_RANGE",
                    help="fold-gate adjudication write: relabel this turn (by "
                         "its exact line_range) + record the structured "
                         "image_verification[] entry, instead of finalizing. "
                         "Requires --speaker / --resolution / --resolved-by; "
                         "dry run unless --write.")
    ap.add_argument("--speaker",
                    help="(resolve) final speaker_id — a speakers[].id, a "
                         "foreign-* kind, or a mixed-exchange list 's1,s2'")
    ap.add_argument("--resolution", choices=["confirmed", "corrected", "ambiguous"],
                    help="(resolve) image-evidence verdict per the schema")
    ap.add_argument("--resolved-by", choices=["agent-verifier", "contributor"],
                    help="(resolve) who made the adjudication call")
    ap.add_argument("--write", action="store_true",
                    help="(resolve) apply the adjudication (default: dry run)")
    ap.add_argument("--selftest", action="store_true",
                    help="run the fold-gate partition logic on synthetic rows "
                         "(no video / .venv-face needed) and exit")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(cmd_selftest())
    if not args.path:
        ap.error("path to {slug}-attribution.yaml is required (or --selftest)")
    path = Path(args.path)
    if not path.is_file():
        sys.exit(f"error: not found: {path}")

    if args.resolve_turn:
        cmd_resolve(args, path)
        return
    if args.write or args.speaker or args.resolution or args.resolved_by:
        sys.exit("error: --speaker/--resolution/--resolved-by/--write belong "
                 "to --resolve-turn mode")
    if not args.video and not args.no_video:
        ap.error("one of --video / --no-video is required to finalize "
                 "(the fold gate is not skippable by omission)")

    # Active-speaker fold gate — runs before any mutation, so a blocked finalize leaves the
    # sibling untouched for the producer/verifier to fix and re-run.
    if args.video:
        video = Path(args.video)
        if not video.is_file():
            sys.exit(f"error: --video not found: {video}")
        blocking, settled = run_fold_gate(path, video)
        for row, entry in settled:
            print(f"  lines {row.get('line_range'):>12} engine contested-fold — settled by "
                  f"image_verification[] ({entry.get('resolution')}, "
                  f"by {entry.get('resolved_by')}; "
                  f"speaker_id {entry.get('resolved_speaker_id')!r})")
        if blocking:
            print("\nACTIVE-SPEAKER GATE BLOCKED — unsettled contested-fold turn(s); finalize "
                  "refused. Fix attribution (relabel), or adjudicate from frames "
                  "(--resolve-turn) if the engine is wrong, and re-run:", file=sys.stderr)
            for row, stale in blocking:
                note = ""
                if stale is not None:
                    note = (f" [STALE adjudication: entry resolved_speaker_id "
                            f"{stale.get('resolved_speaker_id')!r} no longer matches the "
                            f"turn — re-adjudicate]")
                print(f"  lines {row.get('line_range'):>12} "
                      f"(assigned {row.get('speaker_id')}): {row.get('notes')}{note}",
                      file=sys.stderr)
            sys.exit(2)
        if settled:
            print(f"Active-speaker fold gate: clean ({len(settled)} contested-fold "
                  f"verdict(s) settled by recorded adjudication; 0 unsettled).")
        else:
            print("Active-speaker fold gate: clean (0 contested-fold).")

    with path.open() as f:
        data = strict_yaml_load(f)
    if not isinstance(data, dict):
        sys.exit("error: sibling is not a YAML mapping")

    counts = finalize(data, args.verifier_session)

    # Stamp derived fields (content hash + per-turn timestamps) from the
    # source. Pure source read, so it runs in both --video and --no-video modes.
    source_path = REPO_ROOT / data.get("source_path", "")
    if not source_path.is_file():
        sys.exit(f"error: source_path not found: {source_path}")
    ts_counts = stamp_computed_fields(source_path, data)

    # sort_keys=False preserves the producer's key order; width avoids wrapping
    # long scalars (source_path). After stripping, every value is a short
    # scalar or list, so the dump is clean and stable across re-runs.
    body = yaml.safe_dump(data, sort_keys=False, default_flow_style=False,
                          allow_unicode=True, width=4096)
    with path.open("w") as f:
        f.write(HEADER + "\n" + body)

    total = sum(counts.values())
    print(f"Finalized {path}")
    print(f"  verification_status: {data['verification_status']}   "
          f"verifier_session: {data.get('verifier_session')}")
    print(f"  stripped: {counts['rationale']} rationale, "
          f"{counts['turn_verifier_notes']} turn verifier_notes, "
          f"{counts['top_verifier_notes']} top verifier_notes, "
          f"{counts['needs_image_verification']} needs_image_verification, "
          f"{counts['contributor_notes']} contributor_notes "
          f"({total} scaffolding field(s) total)")
    print(f"  computed: source_content_hash {data['source_content_hash'][:14]}…, "
          f"start_ts/end_ts on {ts_counts['timed']} turn(s) "
          f"({ts_counts['untimed']} untimed)")


if __name__ == "__main__":
    main()
