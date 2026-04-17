#!/usr/bin/env python3
"""
Regenerate a node body from its research artifact (Phase II of layered build).

Reads /research/{slug}.yaml and rewrites /{type}/{slug}.md. Frontmatter is
preserved from the existing node; body sections (H1 title onward) are
replaced entirely by content derived from the artifact.

SCOPE (D.3): document-type nodes only. Extension to the other eight node
types is tracked in BACKLOG.md — supporting them requires per-type
section renderers and type-specific artifact field conventions.

DETERMINISM: given the same artifact + node frontmatter, output is
byte-for-byte identical across runs. Entries are rendered in id-sorted
order (q1, q2, …); no date-of-build or wall-clock state is embedded.

USAGE:
  build-from-research.py research/{slug}.yaml
  build-from-research.py research/{slug}.yaml --dry-run
  build-from-research.py research/{slug}.yaml --no-validate

  --dry-run        : render to stdout only — do not write or invoke associate/validate
  --no-validate    : skip pre-flight research-artifact validation and
                     post-build node validation (speed / debugging)

PIPELINE WIRING:
  Pre-flight:  python3 scripts/validate-research.py {artifact} --quiet
  Regenerate:  this script (writes node body)
  Post-step:   python3 scripts/associate.py {node}   (rewrites Associated Nodes)
  Validate:    python3 scripts/validate.py {node} --quiet
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# =============================================================================
# Constants
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
VALIDATE_RESEARCH = SCRIPTS_DIR / "validate-research.py"
VALIDATE_NODE = SCRIPTS_DIR / "validate.py"
ASSOCIATE = SCRIPTS_DIR / "associate.py"

# Content-node type ↔ directory (mirrors research-scaffold.py / validate-research.py)
TYPE_DIRS = {
    "person": "people", "organization": "organizations", "document": "documents",
    "event": "events", "transcript": "transcripts", "news": "news",
    "book": "books", "location": "locations", "finding": "findings",
}

# Types this script can regenerate (D.3 scope)
SUPPORTED_TYPES = {"document"}

# evidentiary_type → base status string for the What This Establishes table.
# sworn-testimony gets an additional suffix when independently_verifiable is
# not populated — see _claim_status().
EVIDENTIARY_STATUS_BASE = {
    "sworn-testimony": "✅ Confirmed as sworn testimony",
    "documented":      "✅ Confirmed",
    "cited":           "✅ Confirmed as cited — see cited source",
    "secondary":       "⚠ Flagged (secondary source)",
}

# Separator between H2 sections in the rendered node body.
# Matches repository convention: blank line, '---', blank line.
SECTION_SEP = "\n---\n\n"


# =============================================================================
# Loaders
# =============================================================================

def load_artifact(path):
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        sys.exit(f"ERROR: artifact root is not a YAML mapping: {path}")
    return data


def load_frontmatter(node_path):
    """Return (frontmatter_dict, raw_frontmatter_block_including_trailing_newline).
    Raw block is preserved verbatim so frontmatter survives regeneration
    with zero structural change (no yaml.dump reformatting)."""
    text = node_path.read_text()
    if not text.startswith("---"):
        return None, None
    end = text.find("\n---", 3)
    if end < 0:
        return None, None
    fm_yaml = text[3:end]
    try:
        fm = yaml.safe_load(fm_yaml)
    except yaml.YAMLError:
        return None, None
    # raw block ends right after closing `---` + its newline
    block_end = end + len("\n---")
    # Consume single newline after closing ---, if present (so body starts clean)
    if block_end < len(text) and text[block_end] == "\n":
        block_end += 1
    return fm, text[:block_end]


def sort_by_id(entries):
    """Natural-sort entries by id (q1, q2, …, q10) so output order is
    stable and human-expected (q10 doesn't land between q1 and q2)."""
    def key(e):
        if not isinstance(e, dict):
            return ("zzz", 0, "")
        eid = e.get("id") or ""
        m = re.match(r"^([a-zA-Z]+)(\d+)$", eid)
        if m:
            return (m.group(1), int(m.group(2)), eid)
        return ("zzz", 0, eid)
    return sorted(entries, key=key)


# =============================================================================
# Section renderers — each returns a trailing-newline-terminated block
# =============================================================================

def _source_path(artifact):
    sources = artifact.get("primary_sources") or []
    if sources and isinstance(sources[0], dict):
        return sources[0].get("path")
    return None


def render_title(artifact):
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    title = ctx.get("display_title") or dm.get("internal_title")
    if not title:
        slug = artifact["target_node"].split("/", 1)[1]
        title = " ".join(w.capitalize() for w in slug.split("-"))
    return f"# {title}\n"


def render_document_summary(artifact):
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    path = _source_path(artifact)
    lines = ["## Document Summary", ""]
    rows = []
    title = dm.get("internal_title") or ctx.get("display_title")
    if title:
        rows.append(("Title", title))
    if dm.get("internal_date"):
        rows.append(("Authored Date (per document)", dm["internal_date"]))
    if ctx.get("hearing_date"):
        rows.append(("Hearing Date", ctx["hearing_date"]))
    authors = dm.get("authors_per_document")
    if authors:
        rows.append(("Author (per document)", "; ".join(authors) if isinstance(authors, list) else str(authors)))
    if dm.get("classification"):
        rows.append(("Classification", dm["classification"]))
    # Format cell: combines file format + page count when available
    fmt_parts = []
    sources = artifact.get("primary_sources") or []
    if sources and isinstance(sources[0], dict) and sources[0].get("format"):
        fmt_parts.append(sources[0]["format"].upper())
    if dm.get("pages"):
        fmt_parts.append(f"{dm['pages']} pages")
    if fmt_parts:
        rows.append(("Format", ", ".join(fmt_parts)))
    if ctx.get("primary_source_url"):
        rows.append(("Primary Source URL", ctx["primary_source_url"]))
    if path:
        rows.append(("Local Archive", f"[sources/{path}](../sources/{path})"))
    if not rows:
        lines.append("<!-- TODO: populate `document_intrinsic` / `context_extrinsic` / `primary_sources` in the research artifact -->")
        return "\n".join(lines) + "\n"
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    for k, v in rows:
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines) + "\n"


def render_description(artifact):
    desc = (artifact.get("description") or "").strip()
    body = desc if desc else "<!-- TODO: populate `description` in the research artifact -->"
    return f"## Description\n\n{body}\n"


def render_provenance(artifact):
    ctx = artifact.get("context_extrinsic") or {}
    prov = ctx.get("provenance")
    lines = ["## Provenance", ""]
    if not isinstance(prov, list) or not prov:
        lines.append("<!-- TODO: populate `context_extrinsic.provenance` in the research artifact -->")
        return "\n".join(lines) + "\n"
    lines.append("| Step | Date | Entity | Verified |")
    lines.append("|---|---|---|---|")
    for step in prov:
        if not isinstance(step, dict):
            continue
        lines.append(
            f"| {step.get('step', '')} | {step.get('date', '')} | "
            f"{step.get('entity', '')} | {step.get('verified', '')} |"
        )
    return "\n".join(lines) + "\n"


def _claim_status(claim):
    et = claim.get("evidentiary_type")
    base = EVIDENTIARY_STATUS_BASE.get(et, "⏳ Pending")
    if et == "sworn-testimony" and not claim.get("independently_verifiable"):
        return base + " — claim not independently verified"
    return base


def _claim_source_cell(claim):
    srcs = claim.get("sources") or []
    parts = []
    for s in srcs:
        if isinstance(s, dict) and s.get("location"):
            parts.append(str(s["location"]))
    return "; ".join(parts)


def render_what_establishes(artifact):
    claims = sort_by_id(artifact.get("claims") or [])
    lines = ["## What This Establishes", ""]
    if not claims:
        lines.append("<!-- TODO: populate `claims` in the research artifact -->")
        return "\n".join(lines) + "\n"
    lines.append("| Claim | Status | Source |")
    lines.append("|---|---|---|")
    for c in claims:
        if not isinstance(c, dict):
            continue
        stmt = (c.get("statement") or "").replace("\n", " ").strip()
        status = _claim_status(c)
        src = _claim_source_cell(c)
        lines.append(f"| {stmt} | {status} | {src} |")
    return "\n".join(lines) + "\n"


def render_key_passages(artifact):
    quotes = sort_by_id(artifact.get("quotes") or [])
    ctx = artifact.get("context_extrinsic") or {}
    attribution = ctx.get("quote_attribution") or ""
    path = _source_path(artifact)
    src_link = f"[archived source](../sources/{path})" if path else ""

    head = "## Key Passages\n"
    if not quotes:
        return head + "\n<!-- TODO: populate `quotes` in the research artifact -->\n"

    blocks = []
    for q in quotes:
        if not isinstance(q, dict):
            continue
        h3 = q.get("significance") or "Passage"
        text = (q.get("text") or "").rstrip("\n")
        loc = ""
        if isinstance(q.get("source"), dict):
            loc = q["source"].get("location") or ""
        lines = [f"### {h3}", ""]
        for qline in text.split("\n"):
            lines.append(f"> {qline}" if qline else ">")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|---|---|")
        if attribution:
            lines.append(f"| Attributed to | {attribution} |")
        if src_link:
            lines.append(f"| Source | {src_link} |")
        lines.append("| Verified | ✅ Confirmed — verified verbatim against archived source |")
        if loc:
            lines.append(f"| Location | {loc} |")
        blocks.append("\n".join(lines))

    return head + "\n" + "\n\n---\n\n".join(blocks) + "\n"


def render_associated_nodes():
    # Placeholder — associate.py rewrites this section post-build by scanning
    # body links. We emit a stub so the section exists for associate.py to find.
    return (
        "## Associated Nodes\n\n"
        "<!-- Auto-generated by scripts/associate.py. Do not hand-edit. -->\n"
        "<!-- placeholder — associate.py rewrites this section post-build -->\n"
    )


def render_open_questions(artifact):
    gaps = sort_by_id(artifact.get("research_gaps") or [])
    head = "## Open Questions / Research Gaps\n"
    items = []
    for g in gaps:
        if not isinstance(g, dict):
            continue
        stmt = (g.get("statement") or "").strip()
        if not stmt:
            continue
        if g.get("resolved"):
            if not g.get("retain_as_done"):
                # Resolution lives in node body (as a new claim / prose); omit
                continue
            rd = g.get("resolved_date", "")
            rs = g.get("resolution_summary", "")
            items.append(f"- [x] {stmt} — DONE {rd}: {rs}")
        else:
            method = g.get("methodology") or ""
            items.append(f"- [ ] {stmt} — {method}" if method else f"- [ ] {stmt}")
    if not items:
        return head + "\n<!-- No open research gaps recorded in artifact. -->\n"
    return head + "\n" + "\n".join(items) + "\n"


# =============================================================================
# Composition
# =============================================================================

def render_body(artifact, node_kind):
    # H1 title stands alone — no `---` separator between H1 and first H2
    title = render_title(artifact).rstrip("\n") + "\n"
    sections = [
        render_document_summary(artifact),
        render_description(artifact),
    ]
    if node_kind == "gov-doc":
        sections.append(render_provenance(artifact))
    sections.extend([
        render_what_establishes(artifact),
        render_key_passages(artifact),
        render_associated_nodes(),
        render_open_questions(artifact),
    ])
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined


def compose_node(raw_frontmatter, body):
    return raw_frontmatter.rstrip() + "\n\n" + body.lstrip()


# =============================================================================
# Pre-flight / post-build validators
# =============================================================================

def preflight_validate_artifact(artifact_path):
    proc = subprocess.run(
        ["python3", str(VALIDATE_RESEARCH), str(artifact_path), "--quiet"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        sys.exit("ERROR: research artifact failed validation — aborting build.")


def post_build_validate(node_path):
    proc = subprocess.run(
        ["python3", str(VALIDATE_NODE), str(node_path), "--quiet"],
        capture_output=True, text=True,
    )
    sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode == 0


def run_associate(node_path):
    subprocess.run(
        ["python3", str(ASSOCIATE), str(node_path)],
        check=False,
    )


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("artifact", help="Path to research artifact (research/{slug}.yaml)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Render to stdout, do not write node or invoke associate/validate")
    parser.add_argument("--no-validate", action="store_true",
                        help="Skip pre-flight research-validation and post-build node-validation")
    args = parser.parse_args()

    artifact_path = Path(args.artifact).resolve()
    if not artifact_path.exists():
        sys.exit(f"ERROR: artifact not found: {artifact_path}")

    if not args.no_validate:
        preflight_validate_artifact(artifact_path)

    artifact = load_artifact(artifact_path)

    target_node = artifact.get("target_node") or ""
    if "/" not in target_node:
        sys.exit(f"ERROR: artifact target_node {target_node!r} is malformed")
    dir_name, slug = target_node.split("/", 1)
    reverse = {v: k for k, v in TYPE_DIRS.items()}
    node_type = reverse.get(dir_name)
    if node_type is None:
        sys.exit(f"ERROR: unknown content-dir {dir_name!r} in target_node")
    if node_type not in SUPPORTED_TYPES:
        sys.exit(f"ERROR: build-from-research.py currently supports "
                 f"{sorted(SUPPORTED_TYPES)} only (got {node_type!r}). "
                 f"Extension to other node types is tracked in BACKLOG.md.")

    node_path = REPO_ROOT / dir_name / f"{slug}.md"
    if not node_path.exists():
        sys.exit(f"ERROR: target node does not exist: {node_path.relative_to(REPO_ROOT)}\n"
                 f"  Run scripts/new.py to scaffold the node first.")

    fm, raw_fm = load_frontmatter(node_path)
    if fm is None or raw_fm is None:
        sys.exit(f"ERROR: cannot parse frontmatter of {node_path.relative_to(REPO_ROOT)}")

    node_kind = fm.get("kind")
    body = render_body(artifact, node_kind)
    new_text = compose_node(raw_fm, body)

    if args.dry_run:
        sys.stdout.write(new_text)
        return

    node_path.write_text(new_text)
    print(f"✓ Regenerated {node_path.relative_to(REPO_ROOT)} "
          f"from {artifact_path.relative_to(REPO_ROOT)}")

    run_associate(node_path)

    if not args.no_validate:
        ok = post_build_validate(node_path)
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    main()
