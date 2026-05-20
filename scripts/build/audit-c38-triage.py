#!/usr/bin/env python3
"""C38.1 — triage audit for the entities_referenced drop + relocate (read-only).

For each retained `entities_referenced` entry, determines whether a
RENDERED relocation home exists for its `context_summary` synthesis —
i.e., whether the entity already occupies a STRUCTURED cross-reference
slot on the artifact (relationship / affiliation / timeline /
key_personnel / participant / speaker / vouching_chain / etc., all of
which carry drift-checked, rendered `.note`/`.event` surfaces). Entries
with no such slot are mentioned-in-passing — they have nowhere to
relocate to, so they DROP.

Sizes the C38.2 relocation effort and tests whether relocation is
warranted at all. Read-only; writes a report to /tmp/c38-triage/.

Architecture note (why a slot is an UPPER BOUND, not a mandate). Even
an entry WITH a structured slot would relocate only a contributor
PARAPHRASE (`context_summary`) into a `.note`. The repo's evidentiary
primitive is the verbatim quote; single-source facts belong as quotes
on the source-bearing node, and cross-source synthesis belongs on
finding nodes — not as paraphrase notes on entity nodes. So a slot
means "a relocation target physically exists," NOT "relocating is the
right call." The contributor judges whether the paraphrase adds
anything the body wrap + the existing structured row + the quotes
don't already carry.

Usage:
  audit-c38-triage.py            # all artifacts → /tmp/c38-triage/
  audit-c38-triage.py --out DIR
"""

import argparse
import glob
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib._common import REPO_ROOT, content_type_dirs  # noqa: E402

RESEARCH_DIR = REPO_ROOT / "meta" / "research"
DEFAULT_OUT = Path("/tmp/c38-triage")

# Structured cross-reference slots that carry a rendered, drift-checked
# .note / .event surface a context_summary could in principle fold into.
# (section_key, path_field, is_list)
SLOT_FIELDS = [
    ("relationships", "person_path", False),
    ("affiliations", "organization_path", False),
    ("program_involvement", "program", False),
    ("timeline", "node_link", False),
    ("vouching_chain", "voucher_path", False),
    ("corroboration_items", "observer_path", False),
    ("publication_record", "node_link", False),
    ("key_personnel", "person_path", False),
    ("org_relationships", "organization_path", False),
    ("participants", "participant_path", False),
    ("witnesses_testimony", "witness_path", False),
    ("witnesses_testimony", "transcript_node", False),
    ("witnesses_testimony", "written_testimony_node", False),
    ("speakers", "node_link", False),
    ("ownership_timeline", "owner_path", False),
    ("location_relationships", "entity_path", False),
    ("contracts", "primary_counterparty_path", False),
    ("top_scope_activity", "actor_paths", True),
]


def node_type(artifact):
    target = artifact.get("target_node") or ""
    if "/" not in target:
        return None
    reverse = {v: k for k, v in content_type_dirs().items()}
    return reverse.get(target.split("/", 1)[0])


def structured_slot_paths(artifact):
    """Collect every wrap_path that occupies a structured cross-reference
    slot (a surface with a rendered .note/.event) on this artifact."""
    paths = set()
    for section, field, is_list in SLOT_FIELDS:
        for entry in artifact.get(section) or []:
            if not isinstance(entry, dict):
                continue
            val = entry.get(field)
            if not val:
                continue
            if is_list:
                paths.update(v for v in val if isinstance(v, str))
            elif isinstance(val, str):
                paths.add(val)
    return paths


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    total = with_slot = no_slot = 0
    by_type = {}              # type -> [with_slot, no_slot]
    artifact_rows = []
    relocate_samples = []     # has slot — strongest relocation candidates
    drop_samples = []         # no slot — mentioned-in-passing

    for f in sorted(glob.glob(str(RESEARCH_DIR / "*.yaml"))):
        d = yaml.safe_load(open(f))
        if not isinstance(d, dict):
            continue
        ents = d.get("entities_referenced") or []
        if not ents:
            continue
        slug = Path(f).stem
        ntype = node_type(d)
        slots = structured_slot_paths(d)

        a_with = a_no = 0
        lines = [f"# C38.1 triage — {slug} ({ntype})", ""]
        for e in ents:
            if not isinstance(e, dict):
                continue
            total += 1
            wp = e.get("wrap_path")
            cs = (e.get("context_summary") or "").strip()
            has = wp in slots
            by_type.setdefault(ntype, [0, 0])
            if has:
                with_slot += 1
                a_with += 1
                by_type[ntype][0] += 1
                tag = "RELOCATE?"
                if len(relocate_samples) < 14:
                    relocate_samples.append((slug, ntype, e.get("name"), cs[:120]))
            else:
                no_slot += 1
                a_no += 1
                by_type[ntype][1] += 1
                tag = "DROP (no home)"
                if len(drop_samples) < 10:
                    drop_samples.append((slug, ntype, e.get("name"), cs[:120]))
            lines.append(f"- [{tag}] {e.get('id')} {e.get('name')!r} "
                         f"({e.get('entity_type')}) → {wp}")
            if cs:
                lines.append(f"    context_summary: {cs}")
        (out_dir / f"{slug}.md").write_text("\n".join(lines) + "\n")
        artifact_rows.append((slug, ntype, a_with, a_no))

    # Summary
    s = []
    s.append("# C38.1 — entities_referenced relocate-vs-drop triage\n")
    s.append(f"Retained entries: {total} across {len(artifact_rows)} artifacts\n")
    s.append(f"- **RELOCATE-CANDIDATE** (entity has a structured slot whose "
             f".note could absorb the synthesis): {with_slot}")
    s.append(f"- **DROP — no rendered home** (mentioned-in-passing; nowhere "
             f"to relocate): {no_slot}\n")
    s.append("A structured slot is the UPPER BOUND on relocatable, not a "
             "mandate — relocating moves a paraphrase into a .note, which the "
             "verbatim-quote-first + findings-carry-synthesis architecture "
             "disfavors. The contributor still judges each RELOCATE-CANDIDATE "
             "against 'does this add anything the body wrap + existing "
             "structured row + quotes don't already carry.'\n")
    s.append("## By node type (with-slot / no-slot)\n")
    for t, (w, n) in sorted(by_type.items()):
        s.append(f"- {t}: {w} relocate-candidate / {n} drop-no-home")
    s.append("\n## Per artifact\n")
    s.append("| artifact | type | relocate-candidate | drop-no-home |")
    s.append("|---|---|---|---|")
    for slug, t, w, n in sorted(artifact_rows):
        s.append(f"| {slug} | {t} | {w} | {n} |")
    s.append("\n## Sample — RELOCATE-CANDIDATEs (has a structured slot)\n")
    for slug, t, name, cs in relocate_samples:
        s.append(f"- [{slug}/{t}] {name}: {cs}")
    s.append("\n## Sample — DROP (no rendered home; mentioned-in-passing)\n")
    for slug, t, name, cs in drop_samples:
        s.append(f"- [{slug}/{t}] {name}: {cs}")
    (out_dir / "SUMMARY.md").write_text("\n".join(s) + "\n")

    print("=" * 64)
    print(" C38.1 — entities_referenced relocate-vs-drop triage (read-only)")
    print("=" * 64)
    print(f"\n  Retained entries:            {total} across {len(artifact_rows)} artifacts")
    print(f"  RELOCATE-CANDIDATE (has slot): {with_slot}")
    print(f"  DROP — no rendered home:       {no_slot}")
    print(f"\n  By node type (relocate-candidate / drop-no-home):")
    for t, (w, n) in sorted(by_type.items()):
        print(f"    {t:14s} {w:4d} / {n}")
    print(f"\n  Report: {out_dir}/  (SUMMARY.md + per-artifact)")
    print("  Read-only: no corpus files modified.")
    sys.exit(0)


if __name__ == "__main__":
    main()
