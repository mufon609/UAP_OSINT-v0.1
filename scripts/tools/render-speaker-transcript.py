#!/usr/bin/env python3
"""
Deterministic renderer: speaker-attribution sibling YAML → human-readable
markdown.

Inputs:
  - A speaker-attribution sibling YAML conforming to
    meta/schema-speaker-attribution.yaml.
  - The source transcript file referenced by the sibling's source_path.

Output:
  - One markdown file: source bytes verbatim, wrapped with speaker
    labels and foreign-content markers derived from the sibling's
    turns[]. No text manipulation — every line of body content is
    pulled byte-for-byte from the source file by line range.

This script does NOT call any LLM. It is a pure transform from
(yaml + source) → markdown. Re-runnable; output is a function of the
two inputs alone. The companion validator is
scripts/build/validate-speaker-attribution.py — the renderer assumes
the input has passed validation (no defensive coverage checks here).

Usage:
  render-speaker-transcript.py SIBLING.yaml
      → writes to /tmp/render-{slug}/{stem}-attributed.md

  render-speaker-transcript.py SIBLING.yaml --output PATH
      → writes to PATH

  render-speaker-transcript.py SIBLING.yaml --stdout
      → writes to stdout (for piping / inspection)
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib._common import REPO_ROOT  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_range(s):
    """`N` or `N-M` → (lo, hi) inclusive."""
    if "-" in s:
        lo, hi = s.split("-", 1)
        return int(lo), int(hi)
    n = int(s)
    return n, n


def load_yaml(path):
    with Path(path).open() as f:
        return yaml.safe_load(f)


def load_source_lines(path):
    """Read source file as a list of lines (1-indexed; slot 0 unused)."""
    with Path(path).open() as f:
        raw = f.read().splitlines()
    return [None] + raw  # 1-indexed


# ---------------------------------------------------------------------------
# Rendering — per-turn
# ---------------------------------------------------------------------------

# `foreign-*` kind → display label (used in the section heading; the
# rationale below carries the specific reason).
FOREIGN_LABELS = {
    "foreign-jingle":      "Jingle",
    "foreign-intro":       "Intro voiceover",
    "foreign-outro":       "Outro voiceover",
    "foreign-ad-read":     "Ad read",
    "foreign-narration":   "Third-party narration",
    "foreign-archival":    "Archival recording",
    "foreign-recitation":  "Speaker reciting from a document",
    "foreign-prepared":    "Speaker reading prepared written statement",
    "foreign-music":       "Non-speech audio",
    "foreign-other":       "Non-conversational content",
}


def speaker_label(turn, speakers_by_id):
    """Resolve a turn's speaker_id into the section-heading label."""
    sid = turn["speaker_id"]
    if isinstance(sid, list):
        names = [speakers_by_id[m]["name"] for m in sid]
        return "Speakers — mixed exchange: " + ", ".join(names)
    if isinstance(sid, str) and sid.startswith("foreign-"):
        return f"[{FOREIGN_LABELS.get(sid, sid)}]"
    # single defined speaker
    sp = speakers_by_id[sid]
    label = sp["name"]
    if sp.get("node_link"):
        label += f" ([{sp['node_link']}]({sp['node_link']}))"
    role = sp.get("role")
    if role:
        label += f" — {role}"
    return label


def render_turn(turn, speakers_by_id, source_lines):
    """One turn → markdown block. Header line + annotations + verbatim body."""
    out = []
    label = speaker_label(turn, speakers_by_id)
    lr = turn["line_range"]
    lo, hi = parse_range(lr)

    # Heading: confidence annotation
    suffix_bits = [f"lines {lr}"]
    conf = turn.get("confidence", "high")
    if conf == "medium":
        suffix_bits.append("medium confidence")
    elif conf == "low":
        suffix_bits.append("⚠ LOW CONFIDENCE")
    if turn.get("needs_image_verification"):
        suffix_bits.append("⚠ needs image verification")
    suffix = " · ".join(suffix_bits)

    out.append(f"### {label}  \n*({suffix})*")
    out.append("")

    # Annotation block (rationale + referenced_source + verifier_notes)
    notes = []
    if turn.get("rationale"):
        notes.append(f"> **Rationale:** {turn['rationale']}")
    if turn.get("referenced_source"):
        notes.append(f"> **Recited source:** {turn['referenced_source']}")
    if turn.get("verifier_notes"):
        notes.append(f"> **Verifier note:** {turn['verifier_notes']}")
    if notes:
        out.extend(notes)
        out.append("")

    # Body — verbatim source lines, fenced to preserve [MM:SS] markup
    # exactly as in the source file.
    body_lines = source_lines[lo:hi + 1]
    out.append("```")
    out.extend(body_lines)
    out.append("```")
    out.append("")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Top-level header block
# ---------------------------------------------------------------------------

def render_header(data, source_lines):
    out = []
    out.append(f"# Speaker-attributed transcript — {data['slug']}")
    out.append("")
    out.append(f"**Source:** `{data['source_path']}` ({data['source_line_count']} lines)  ")
    out.append(f"**Generated:** {data['generated_date']} via `/prepare-transcript-sibling`  ")
    out.append(f"**Producer session:** `{data['producer_session']}`  ")
    if data.get("verifier_session"):
        out.append(f"**Verifier session:** `{data['verifier_session']}`  ")
    out.append(f"**Verification status:** **{data['verification_status']}**")
    out.append("")
    out.append("**Speakers:**")
    out.append("")
    for sp in data.get("speakers", []):
        bits = [f"- **{sp['name']}** (`{sp['id']}`)"]
        if sp.get("role"):
            bits.append(f"— {sp['role']}")
        if sp.get("node_link"):
            bits.append(f"— [`{sp['node_link']}`]({sp['node_link']})")
        bits.append(f"— *on-camera:* {sp['on_camera_role']}")
        out.append(" ".join(bits))
    out.append("")
    out.append(
        "> This file is **generated** by `scripts/tools/render-speaker-transcript.py`. "
        "Source-of-truth is the source transcript file plus the "
        f"`{data['slug']}-attribution.yaml` sibling. Do not edit this file directly — "
        "edits go through the sibling YAML and a re-render."
    )
    out.append("")

    # Coverage note
    if data.get("verification_status") != "verified":
        out.append(
            f"> ⚠ Verification status is `{data['verification_status']}`. "
            "Speaker attribution has not yet been independently verified. "
            "Treat low-confidence turns and mixed-exchange labels as provisional."
        )
        out.append("")

    out.append("---")
    out.append("")
    return "\n".join(out)


def render_image_verification_block(data):
    ivs = data.get("image_verification") or []
    if not ivs:
        return ""
    out = ["---", "", "## Image-verification audit trail", ""]
    out.append(
        "Turns whose `needs_image_verification: true` flag was resolved "
        "against `sources/photo-identity-log/baselines/`. Preserved here "
        "as the audit trail for downstream cross-checks."
    )
    out.append("")
    out.append("| Turn lines | Resolution | Resolved speaker | Resolved by |")
    out.append("|---|---|---|---|")
    for e in ivs:
        sid = e.get("resolved_speaker_id")
        sid_disp = ", ".join(sid) if isinstance(sid, list) else sid
        out.append(
            f"| `{e['turn_line_range']}` | {e['resolution']} | "
            f"`{sid_disp}` | {e['resolved_by']} |"
        )
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def render(yaml_path):
    data = load_yaml(yaml_path)
    source_path = REPO_ROOT / data["source_path"]
    if not source_path.is_file():
        sys.exit(f"error: source_path file not found: {source_path}")
    source_lines = load_source_lines(source_path)

    speakers_by_id = {sp["id"]: sp for sp in data.get("speakers", [])}

    parts = [render_header(data, source_lines)]
    for turn in data.get("turns", []):
        parts.append(render_turn(turn, speakers_by_id, source_lines))
    iv_block = render_image_verification_block(data)
    if iv_block:
        parts.append(iv_block)

    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(
        description="Render a speaker-attribution sibling YAML to markdown.",
    )
    ap.add_argument("yaml_path", help="path to the .attribution.yaml sibling")
    out_group = ap.add_mutually_exclusive_group()
    out_group.add_argument(
        "--output", "-o",
        help="write to PATH (default: /tmp/render-{slug}/{stem}-attributed.md)",
    )
    out_group.add_argument(
        "--stdout", action="store_true",
        help="write to stdout instead of a file",
    )
    args = ap.parse_args()

    text = render(args.yaml_path)

    if args.stdout:
        sys.stdout.write(text)
        return

    if args.output:
        out_path = Path(args.output)
    else:
        # Default: /tmp/render-{slug}/{slug}-attributed.md — use the yaml's
        # slug directly rather than trying to strip provenance suffixes off
        # the source stem (which would require the renderer to know every
        # source-naming convention in the corpus). The skill's manifest-
        # registration step decides the final landing filename.
        data = load_yaml(args.yaml_path)
        slug = data["slug"]
        out_dir = Path(f"/tmp/render-{slug}")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{slug}-attributed.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(f"Wrote {out_path} ({len(text):,} chars)")


if __name__ == "__main__":
    main()
