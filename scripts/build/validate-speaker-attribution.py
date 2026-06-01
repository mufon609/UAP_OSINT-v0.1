#!/usr/bin/env python3
"""
Validate speaker-attribution sibling YAMLs against
meta/schema-speaker-attribution.yaml.

A sibling lives at `sources/transcripts/{stem}-attribution.yaml` (in
production) and indexes by 1-indexed line range into the source
transcript at `sources/transcripts/{stem}-downloaded.md` (or .txt). It
is produced by the agent-based `/prepare-transcript-sibling` skill and
consumed by `scripts/tools/render-speaker-transcript.py`.

Structural checks only — does NOT compare against transcript-artifact
quote.speaker_id cross-references (that's a future scripts/checks/ module
called from validate-research.py, per
schema-speaker-attribution.yaml::"Cross-schema integration points" §2).

Checks (run in order; first fatal aborts the file):
  1. yaml_parse              — file parses, top-level is a mapping
  2. top_level_keys          — required keys present; types correct
  3. slug_consistency        — slug matches source_path stem
  4. source_existence        — source_path exists; line count matches
  5. enums                   — verification_status / on_camera_role values
  6. speakers                — entries shape; ids unique
  7. node_links              — referenced /people|/orgs paths exist
  8. turn_speaker_ids        — each speaker_id valid (defined / foreign / mixed)
  9. turn_confidence         — confidence in {high, medium, low}
 10. turn_rationale          — rationale required where mandatory (draft only)
 11. turn_referenced_source  — required for foreign-recitation / -archival
 12. turn_coverage           — every line in [1, source_line_count]
                                covered exactly once; ranges sorted
 13. verification_fields     — verifier_session/notes consistent with status
 14. verified_structured_only — verified siblings carry no rationale /
                                verifier_notes scaffolding (stripped on finalize)
 15. image_verification      — entries shape if present

Usage:
  validate-speaker-attribution.py PATH        # validate one sibling
  validate-speaker-attribution.py             # all sources/transcripts/*-attribution.yaml
  validate-speaker-attribution.py --quiet     # errors only

Exit code 0 on PASS; non-zero on any FATAL.
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib._common import strict_yaml_load, REPO_ROOT  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "meta" / "schema-speaker-attribution.yaml"
SIBLING_GLOB = "sources/transcripts/*-attribution.yaml"


# ---------------------------------------------------------------------------
# Issue accumulator
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    severity: str   # FATAL | WARN
    where: str      # short locator e.g. "turns[3]" / "speakers[1].id"
    msg: str


@dataclass
class Report:
    path: Path
    issues: list = field(default_factory=list)

    def fatal(self, where, msg): self.issues.append(Issue("FATAL", where, msg))
    def warn(self, where, msg): self.issues.append(Issue("WARN", where, msg))

    @property
    def has_fatal(self):
        return any(i.severity == "FATAL" for i in self.issues)


# ---------------------------------------------------------------------------
# Schema loader (cached)
# ---------------------------------------------------------------------------

_schema_cache = None


def load_schema():
    global _schema_cache
    if _schema_cache is None:
        with SCHEMA_PATH.open() as f:
            _schema_cache = yaml.safe_load(f)
    return _schema_cache


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

_RANGE_RE = re.compile(r"^(\d+)(?:-(\d+))?$")


def parse_range(s):
    """Returns (lo, hi) inclusive or None if malformed."""
    if not isinstance(s, str):
        return None
    m = _RANGE_RE.match(s.strip())
    if not m:
        return None
    lo = int(m.group(1))
    hi = int(m.group(2)) if m.group(2) else lo
    if lo < 1 or hi < lo:
        return None
    return (lo, hi)


def check_top_level(data, schema, rpt):
    if not isinstance(data, dict):
        rpt.fatal("<root>", "top-level YAML must be a mapping")
        return False
    required = schema.get("required_keys", [])
    missing = [k for k in required if k not in data]
    if missing:
        rpt.fatal("<root>", f"missing required keys: {missing}")
    # Light type spot-checks
    if "source_line_count" in data and not isinstance(data["source_line_count"], int):
        rpt.fatal("source_line_count", "must be an integer")
    if "speakers" in data and not isinstance(data["speakers"], list):
        rpt.fatal("speakers", "must be a list")
    if "turns" in data and not isinstance(data["turns"], list):
        rpt.fatal("turns", "must be a list")
    return not rpt.has_fatal


def check_slug_consistency(data, rpt):
    slug = data.get("slug", "")
    sp = data.get("source_path", "")
    if not slug or not sp:
        return  # caught by top_level
    sp_path = Path(sp)
    stem = sp_path.stem
    # Tolerate both `{slug}-downloaded.md` and `{slug}.txt` style stems —
    # the convention is `slug + suffix` where suffix carries the source
    # provenance (-downloaded, -youtube-transcript, etc.).
    if stem != slug and not stem.startswith(slug):
        rpt.fatal(
            "slug",
            f"slug {slug!r} does not match source_path stem {stem!r}",
        )


def check_source_existence(data, rpt):
    sp = data.get("source_path", "")
    if not sp:
        return
    src = REPO_ROOT / sp
    if not src.is_file():
        rpt.fatal("source_path", f"file not found: {src}")
        return
    declared = data.get("source_line_count")
    if isinstance(declared, int):
        with src.open() as f:
            actual = sum(1 for _ in f)
        if actual != declared:
            rpt.fatal(
                "source_line_count",
                f"declared {declared} but source file has {actual} lines — "
                f"source changed underneath the sibling; re-run the skill",
            )


def check_enums(data, schema, rpt):
    vs = data.get("verification_status")
    allowed = schema.get("verification_status_values", [])
    if vs not in allowed:
        rpt.fatal("verification_status", f"{vs!r} not in {allowed}")
    on_cam_vals = schema.get("on_camera_role_values", [])
    for i, sp in enumerate(data.get("speakers", []) or []):
        if not isinstance(sp, dict):
            continue
        ocr = sp.get("on_camera_role")
        if ocr not in on_cam_vals:
            rpt.fatal(
                f"speakers[{i}].on_camera_role",
                f"{ocr!r} not in {on_cam_vals}",
            )


def check_speakers(data, rpt):
    speakers = data.get("speakers") or []
    ids = []
    for i, sp in enumerate(speakers):
        if not isinstance(sp, dict):
            rpt.fatal(f"speakers[{i}]", "must be a mapping")
            continue
        for req in ("id", "name", "on_camera_role"):
            if req not in sp:
                rpt.fatal(f"speakers[{i}]", f"missing required key: {req}")
        sid = sp.get("id")
        if sid:
            if sid in ids:
                rpt.fatal(f"speakers[{i}].id", f"duplicate id {sid!r}")
            ids.append(sid)
            # Reserve `foreign-*` prefix for foreign_kind_values
            if sid.startswith("foreign-"):
                rpt.fatal(
                    f"speakers[{i}].id",
                    f"speaker id {sid!r} uses reserved `foreign-` prefix",
                )


def check_node_links(data, rpt):
    """W4 — node_link is the authoritative identity join key.

    In a VERIFIED sibling every live speaker must carry a `/people/{slug}`
    node_link, OR be explicitly marked `no_repo_node: true` (an anonymous /
    unlinkable participant). A stub to an unbuilt node is the CORRECT value
    (meta/conventions.md "stub, never null") — target existence is NOT
    checked here; the broken-link registry tracks it via the transcript node
    body. Draft siblings may still be filling links in, so the requirement
    binds only once verified."""
    verified = data.get("verification_status") == "verified"
    for i, sp in enumerate(data.get("speakers") or []):
        if not isinstance(sp, dict):
            continue
        nl = sp.get("node_link")
        no_node = sp.get("no_repo_node") is True

        if no_node and nl:
            rpt.fatal(
                f"speakers[{i}]",
                f"speaker {sp.get('id')!r} marked no_repo_node: true must not also "
                f"carry a node_link ({nl!r})",
            )
            continue
        if no_node:
            continue  # explicitly unlinkable — exempt from the join-key rule

        if not nl:
            if verified:
                rpt.fatal(
                    f"speakers[{i}].node_link",
                    f"live speaker {sp.get('id')!r} in a verified sibling must carry a "
                    f"/people/{{slug}} node_link (a stub is correct for an unbuilt "
                    f"node; the broken-link registry tracks it) — or set "
                    f"`no_repo_node: true` if it has no resolvable repo identity "
                    f"(e.g. an anonymous anchor)",
                )
            continue

        # node_link present — validate form only; a stub to an unbuilt node is
        # the correct value, so target existence is deliberately NOT checked.
        if not nl.startswith("/people/"):
            rpt.fatal(
                f"speakers[{i}].node_link",
                f"speaker node_link must be a /people/{{slug}} path: {nl!r}",
            )


def check_turn_speaker_ids(data, schema, rpt):
    speaker_ids = {sp.get("id") for sp in (data.get("speakers") or []) if isinstance(sp, dict)}
    foreign_kinds = set(schema.get("foreign_kind_values", []))
    for i, t in enumerate(data.get("turns") or []):
        if not isinstance(t, dict):
            rpt.fatal(f"turns[{i}]", "must be a mapping")
            continue
        sid = t.get("speaker_id")
        if sid is None:
            rpt.fatal(f"turns[{i}].speaker_id", "missing")
            continue
        if isinstance(sid, str):
            if sid in speaker_ids:
                continue
            if sid in foreign_kinds:
                continue
            rpt.fatal(
                f"turns[{i}].speaker_id",
                f"{sid!r} is neither a defined speaker id "
                f"({sorted(speaker_ids)}) nor a foreign-kind "
                f"({sorted(foreign_kinds)})",
            )
        elif isinstance(sid, list):
            if len(sid) < 2:
                rpt.fatal(
                    f"turns[{i}].speaker_id",
                    f"mixed-exchange list must have 2+ ids (got {len(sid)}); "
                    f"use a bare string for single-speaker turns",
                )
                continue
            for j, member in enumerate(sid):
                if not isinstance(member, str):
                    rpt.fatal(
                        f"turns[{i}].speaker_id[{j}]",
                        f"mixed-exchange member must be a string id, got {type(member).__name__}",
                    )
                    continue
                if member in foreign_kinds:
                    rpt.fatal(
                        f"turns[{i}].speaker_id[{j}]",
                        f"foreign-* kind {member!r} cannot appear in a mixed-exchange list "
                        f"(foreign content is not a 'speaker' — use a separate turn)",
                    )
                elif member not in speaker_ids:
                    rpt.fatal(
                        f"turns[{i}].speaker_id[{j}]",
                        f"{member!r} not in speakers[] ({sorted(speaker_ids)})",
                    )
        else:
            rpt.fatal(
                f"turns[{i}].speaker_id",
                f"must be a string or list of strings, got {type(sid).__name__}",
            )


def check_turn_confidence(data, schema, rpt):
    allowed = schema.get("confidence_values", [])
    for i, t in enumerate(data.get("turns") or []):
        if not isinstance(t, dict):
            continue
        c = t.get("confidence")
        if c not in allowed:
            rpt.fatal(f"turns[{i}].confidence", f"{c!r} not in {allowed}")


def check_turn_rationale(data, schema, rpt):
    """rationale required when confidence < high OR speaker_id is foreign-*
    OR speaker_id is a mixed-exchange list — but ONLY while the sibling is
    not yet verified. rationale is draft-phase verification scaffolding the
    independent verifier checks; finalize-attribution.py strips it on verify,
    so a verified sibling carries none (see check_verified_structured_only)."""
    if data.get("verification_status") == "verified":
        return
    foreign_kinds = set(schema.get("foreign_kind_values", []))
    for i, t in enumerate(data.get("turns") or []):
        if not isinstance(t, dict):
            continue
        sid = t.get("speaker_id")
        conf = t.get("confidence")
        rationale = t.get("rationale")
        needs = False
        if conf in ("medium", "low"):
            needs = True
        elif isinstance(sid, str) and sid in foreign_kinds:
            needs = True
        elif isinstance(sid, list):
            needs = True
        if needs and not rationale:
            rpt.fatal(
                f"turns[{i}].rationale",
                "required when confidence < high OR speaker_id is foreign-* OR mixed-exchange",
            )


def check_turn_referenced_source(data, rpt):
    """referenced_source required when speaker_id is foreign-recitation or
    foreign-archival."""
    for i, t in enumerate(data.get("turns") or []):
        if not isinstance(t, dict):
            continue
        sid = t.get("speaker_id")
        if sid in ("foreign-recitation", "foreign-archival") and not t.get("referenced_source"):
            rpt.fatal(
                f"turns[{i}].referenced_source",
                f"required when speaker_id is {sid!r}",
            )


def check_turn_coverage(data, rpt):
    """Coverage discipline: every line in [1, source_line_count] is covered
    by exactly one turn entry; ranges sorted ascending, no gaps, no overlaps."""
    total = data.get("source_line_count")
    if not isinstance(total, int) or total < 1:
        return  # caught by top_level / source_existence
    turns = data.get("turns") or []
    ranges = []
    for i, t in enumerate(turns):
        if not isinstance(t, dict):
            continue
        lr = t.get("line_range")
        parsed = parse_range(lr)
        if parsed is None:
            rpt.fatal(
                f"turns[{i}].line_range",
                f"malformed {lr!r}; expected 'N' or 'N-M' with 1 ≤ N ≤ M",
            )
            continue
        lo, hi = parsed
        if hi > total:
            rpt.fatal(
                f"turns[{i}].line_range",
                f"upper bound {hi} > source_line_count {total}",
            )
            continue
        ranges.append((lo, hi, i))
    if not ranges:
        return
    # Sorted-ascending check + gap/overlap detection
    expected_start = 1
    last_idx = None
    for lo, hi, i in ranges:
        if lo != expected_start:
            if lo < expected_start:
                rpt.fatal(
                    f"turns[{i}].line_range",
                    f"overlaps prior range (starts at line {lo}, expected {expected_start})",
                )
            else:
                rpt.fatal(
                    f"turns[{i}].line_range",
                    f"gap before line {lo}; expected coverage starting at {expected_start}",
                )
        expected_start = hi + 1
        last_idx = i
    if expected_start - 1 != total:
        rpt.fatal(
            f"turns[{last_idx}].line_range",
            f"coverage ends at line {expected_start - 1}; "
            f"source_line_count is {total} — final {total - (expected_start - 1)} line(s) uncovered",
        )


def check_verification_fields(data, rpt):
    vs = data.get("verification_status")
    if vs == "verified" and not data.get("verifier_session"):
        rpt.fatal("verifier_session", "required when verification_status is 'verified'")
    if vs == "rejected" and not data.get("verifier_notes"):
        rpt.fatal("verifier_notes", "required when verification_status is 'rejected'")


def check_verified_structured_only(data, rpt):
    """A VERIFIED sibling is the committed end-product and carries no
    verification scaffolding. rationale + verifier_notes + the
    needs_image_verification flag are stripped on finalize
    (scripts/build/finalize-attribution.py); their presence on a verified
    sibling is a FATAL — the structured fields (speaker_id, line_range,
    confidence) plus any image_verification[] resolution are the durable
    record."""
    if data.get("verification_status") != "verified":
        return
    if data.get("verifier_notes"):
        rpt.fatal(
            "verifier_notes",
            "forbidden on a verified sibling — strip via finalize-attribution.py "
            "(verifier_notes is draft/rejected-only scaffolding)",
        )
    for i, t in enumerate(data.get("turns") or []):
        if not isinstance(t, dict):
            continue
        for field in ("rationale", "verifier_notes", "needs_image_verification"):
            if t.get(field):
                rpt.fatal(
                    f"turns[{i}].{field}",
                    f"forbidden on a verified sibling — strip via "
                    f"finalize-attribution.py ({field} is draft-phase scaffolding; "
                    f"confidence + any image_verification[] resolution are the "
                    f"durable record)",
                )


def check_image_verification(data, rpt):
    ivs = data.get("image_verification")
    if ivs is None:
        return
    if not isinstance(ivs, list):
        rpt.fatal("image_verification", "must be a list when present")
        return
    turn_ranges = {t.get("line_range") for t in (data.get("turns") or []) if isinstance(t, dict)}
    for i, e in enumerate(ivs):
        if not isinstance(e, dict):
            rpt.fatal(f"image_verification[{i}]", "must be a mapping")
            continue
        for req in ("turn_line_range", "resolution", "resolved_speaker_id", "resolved_by"):
            if req not in e:
                rpt.fatal(f"image_verification[{i}]", f"missing required key: {req}")
        # Allowed-key enforcement: the entry is structured-only. Rejects
        # `frames_extracted` (transient /tmp paths → dead references once
        # committed), `baseline_matched` (unread, redundant), and
        # `contributor_notes` (prose restating resolution/resolved_speaker_id).
        allowed = {"turn_line_range", "resolution", "resolved_speaker_id",
                   "resolved_by"}
        extra = sorted(set(e) - allowed)
        if extra:
            rpt.fatal(
                f"image_verification[{i}]",
                f"unknown key(s) {extra}; allowed: {sorted(allowed)}",
            )
        tr = e.get("turn_line_range")
        if tr and tr not in turn_ranges:
            rpt.fatal(
                f"image_verification[{i}].turn_line_range",
                f"{tr!r} does not match any entry in turns[]",
            )
        if e.get("resolution") not in (None, "confirmed", "corrected", "ambiguous"):
            rpt.fatal(
                f"image_verification[{i}].resolution",
                f"{e['resolution']!r} not in [confirmed, corrected, ambiguous]",
            )
        if e.get("resolved_by") not in (None, "agent-verifier", "contributor"):
            rpt.fatal(
                f"image_verification[{i}].resolved_by",
                f"{e['resolved_by']!r} not in [agent-verifier, contributor]",
            )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def validate(path, schema):
    rpt = Report(path)
    try:
        with path.open() as f:
            data = strict_yaml_load(f)
    except yaml.YAMLError as e:
        rpt.fatal("<yaml>", f"parse error: {e}")
        return rpt
    if not check_top_level(data, schema, rpt):
        return rpt
    check_slug_consistency(data, rpt)
    check_source_existence(data, rpt)
    check_enums(data, schema, rpt)
    check_speakers(data, rpt)
    check_node_links(data, rpt)
    check_turn_speaker_ids(data, schema, rpt)
    check_turn_confidence(data, schema, rpt)
    check_turn_rationale(data, schema, rpt)
    check_turn_referenced_source(data, rpt)
    check_turn_coverage(data, rpt)
    check_verification_fields(data, rpt)
    check_verified_structured_only(data, rpt)
    check_image_verification(data, rpt)
    return rpt


def format_report(rpt, quiet=False):
    lines = []
    if rpt.has_fatal or (not quiet and rpt.issues):
        lines.append(f"\n{rpt.path.relative_to(REPO_ROOT) if rpt.path.is_relative_to(REPO_ROOT) else rpt.path}")
    for i in rpt.issues:
        if quiet and i.severity != "FATAL":
            continue
        lines.append(f"    [{i.severity:<5}] {i.where}: {i.msg}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="Validate speaker-attribution sibling YAMLs.",
    )
    ap.add_argument("path", nargs="?", help="path to one sibling .yaml (default: all)")
    ap.add_argument("--quiet", action="store_true", help="errors only")
    args = ap.parse_args()

    schema = load_schema()

    if args.path:
        targets = [Path(args.path)]
    else:
        targets = sorted(REPO_ROOT.glob(SIBLING_GLOB))
        if not targets:
            print(f"No sibling files found at {SIBLING_GLOB} — nothing to validate.")
            sys.exit(0)

    reports = [validate(p, schema) for p in targets]
    output = "\n".join(format_report(r, args.quiet) for r in reports if r.issues)
    if output:
        print(output)

    n_fatal = sum(1 for r in reports for i in r.issues if i.severity == "FATAL")
    n_warn = sum(1 for r in reports for i in r.issues if i.severity == "WARN")
    print(
        f"\n================================================================"
        f"\n  {'PASSED' if n_fatal == 0 else 'FAILED'} — {n_fatal} fatal, {n_warn} warning(s) "
        f"across {len(reports)} file(s)"
    )
    sys.exit(0 if n_fatal == 0 else 1)


if __name__ == "__main__":
    main()
