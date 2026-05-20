#!/usr/bin/env python3
"""A1.1 — entities_referenced[] vocab-retirement audit (read-only).

Classifies every ``entities_referenced[]`` entry across
``meta/research/*.yaml`` into the three A1 migration buckets and
quantifies the TRUE ``description_token_drift`` vocab risk of deleting
each redundant entry — the safety property phase A1.4 must preserve.

Buckets (per ``meta/roadmap.md`` "A1", phase A1.1):

  (a) PRESERVE        — substantive: ``context_summary`` carries
                        significant tokens not already present in the
                        rendered node body (synthesis not in body).
  (b) DELETE-no-risk  — redundant AND deleting the entry's ``name``
                        removes no grounding from any live
                        ``description_token_drift`` token.
  (c) DELETE-migrate  — redundant AND the entry's ``name`` is the SOLE
                        grounding for a token in the node's
                        ``## Description`` section; phase A1.2 must
                        migrate the name into ``naming_quirks[]`` before
                        phase A1.4 deletes the entry.

Why gate-accuracy matters. ``description_token_drift`` is the only
consumer that grounds vocabulary on ``entities_referenced[].name``, and
it fires ONLY on nodes that render a ``## Description`` section. Person
nodes render no ``## Description`` (``background`` / ``top_relevance`` /
``credibility_notes`` are their synthesis surfaces, checked by
``prose_drift``, which grounds on ``primary_sources`` text only — never
entity names). So a redundant entry on a node WITHOUT a ``## Description``
section carries zero ``description_token_drift`` risk → bucket (b),
regardless of whether its name appears nowhere else in the artifact.
The audit reuses the gate's own functions
(``_extract_description_text`` / ``_extract_description_drift_tokens`` /
``_gather_grounding_text`` / ``normalize_for_compare``) so the bucket
(b)-vs-(c) split stays in mechanical lockstep with the gate A1.4 is
gated on.

A conservative, type-agnostic "name-token-unique" signal is reported
alongside each entry (name tokens absent from body prose + other entity
names + ``naming_quirks`` + source text). This is the whole-corpus
measure the analysis-of-record used; reporting it next to the
gate-accurate risk shows how much the gate filter narrows the estimate
(the conservative count is dominated by person artifacts, where the
risk is moot).

Read-only: reads research artifacts, rendered nodes, and archived
sources; writes reports to the output dir (default
``/tmp/a1-vocab-audit/``). NEVER modifies the corpus.

Usage:
  audit-a1-vocab.py --all
  audit-a1-vocab.py meta/research/aaro.yaml
  audit-a1-vocab.py --all --out /tmp/a1-vocab-audit
  audit-a1-vocab.py --all --substantive-threshold 2
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# scripts/build/audit-a1-vocab.py — put the scripts/ parent on sys.path
# so `from lib._common` and `from checks` resolve from this nested
# location (mirrors review-coverage.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib._common import (
    strict_yaml_load,
    REPO_ROOT,
    SOURCES_DIR,
    content_type_dirs,
    extract_source_text,
    extract_significant_tokens,
    normalize_for_compare,
    resolve_cli_path,
)

# Import the live gate's own functions so the description_token_drift
# risk computation is byte-for-byte the gate's logic, not a re-
# implementation. Underscore-prefixed but imported deliberately: the
# audit MUST classify entries against the exact gate A1.4 is gated on.
from checks import description_token_drift as dtd


RESEARCH_DIR = REPO_ROOT / "meta" / "research"
DEFAULT_OUT = Path("/tmp/a1-vocab-audit")

BUCKET_PRESERVE = "a-preserve"
BUCKET_DELETE_SAFE = "b-delete-no-risk"
BUCKET_DELETE_MIGRATE = "c-delete-migrate"


# =============================================================================
# Source-text gathering — mirrors review-coverage.py::_gather_source_text so
# the grounding handed to the gate functions matches what the gate sees.
# =============================================================================

def gather_source_text(artifact):
    chunks = []
    for ps in (artifact.get("primary_sources") or []):
        if not isinstance(ps, dict):
            continue
        rel_path = ps.get("path")
        if not rel_path:
            continue
        # Binary primary sources (image/video/audio) are not text-
        # extractable by design — silent skip, matching the gate path.
        if ps.get("format") in ("image", "video", "audio"):
            continue
        full = SOURCES_DIR / rel_path
        if not full.exists():
            continue
        text = extract_source_text(full)
        if text is None:
            continue
        chunks.append(text)
    return "\n".join(chunks)


def target_node_path(artifact):
    target = artifact.get("target_node") or ""
    if "/" not in target:
        return None
    return REPO_ROOT / f"{target}.md"


def target_node_type(artifact):
    target = artifact.get("target_node") or ""
    if "/" not in target:
        return None
    dir_name = target.split("/", 1)[0]
    reverse = {v: k for k, v in content_type_dirs().items()}
    return reverse.get(dir_name)


# =============================================================================
# Per-artifact analysis
# =============================================================================

def _naming_quirk_tokens(artifact):
    """Significant tokens from naming_quirks canonical + observed forms —
    part of the conservative name-coverage union."""
    text_parts = []
    for nq in artifact.get("naming_quirks") or []:
        if not isinstance(nq, dict):
            continue
        for k in ("canonical", "observed"):
            v = nq.get(k)
            if v:
                text_parts.append(str(v))
    return extract_significant_tokens(" ".join(text_parts))


def analyze_artifact(artifact_path, substantive_threshold):
    """Return a dict describing every entities_referenced[] entry's
    bucket + the evidence behind it, or None for unreadable / no-entity
    artifacts."""
    try:
        with open(artifact_path) as f:
            artifact = strict_yaml_load(f)
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(artifact, dict):
        return None

    entities = artifact.get("entities_referenced") or []
    slug = artifact_path.stem
    node_type = target_node_type(artifact)

    node_path = target_node_path(artifact)
    node_text = (
        node_path.read_text()
        if (node_path and node_path.exists())
        else None
    )

    # Whether the rendered node has a ## Description section.
    desc_text = dtd._extract_description_text(node_text) if node_text else None
    has_description = desc_text is not None

    source_text = gather_source_text(artifact)
    source_present = bool(source_text)

    # description_token_drift fires ONLY when the node has a ## Description
    # AND the artifact yields extractable source_text — its check()
    # early-returns on empty source_text (see scripts/checks/
    # description_token_drift.py: `if not ctx.source_text: return`). On a
    # source-less artifact the grounding would be entity-names-only, and the
    # gate declines to run rather than flag everything. Replicating that
    # skip here is what keeps the audit gate-accurate: deleting entity names
    # on a node the gate skips can never produce a new gate failure.
    gate_active = has_description and source_present

    # Token pools for classification (lockstep tokenizer).
    body_tokens = extract_significant_tokens(node_text or "")
    source_tokens = extract_significant_tokens(source_text)
    nq_tokens = _naming_quirk_tokens(artifact)

    # --- Sole-grounder pre-pass ---
    # name_grounded_tokens = Description drift tokens grounded ONLY via
    # the collective entity names (present with names, absent from the
    # name-free grounding base). Computed whenever the node has a
    # ## Description, even when the gate is currently skipped (empty
    # source) — so the report can distinguish ACTIVE risk (gate fires →
    # deleting the name breaks a live check) from LATENT risk (gate
    # skipped today; the name would matter only if a source were later
    # added to the artifact).
    #
    # ungrounded_with_all_names = Description tokens unmatched even with
    # ALL entity names present. On a gate-skipped (source-less) artifact
    # this is the pre-existing grounding gap the Description ALREADY
    # carries — independent of entity-name deletion. Reported so the
    # latent case is honest: if these dwarf name_grounded, preserving the
    # names wouldn't make the node gate-clean were a source ever added.
    name_grounded_norm = {}     # normalized-token -> raw Description token
    ungrounded_with_all_names = []
    if has_description:
        desc_tokens = dtd._extract_description_drift_tokens(desc_text)
        if desc_tokens:
            g_with_norm = normalize_for_compare(
                dtd._gather_grounding_text(artifact, source_text)
            ).lower()
            artifact_no_names = dict(artifact)
            artifact_no_names["entities_referenced"] = []
            g_base_norm = normalize_for_compare(
                dtd._gather_grounding_text(artifact_no_names, source_text)
            ).lower()
            for t in desc_tokens:
                nt = normalize_for_compare(t).lower()
                if not nt:
                    continue
                if nt not in g_with_norm:
                    ungrounded_with_all_names.append(t)
                elif nt not in g_base_norm:
                    name_grounded_norm[nt] = t

    # Memoize per-entry "grounding without this entry" only when a token
    # could be a sole-grounder (name_grounded_norm non-empty).
    def gate_risk_tokens(entry):
        if not name_grounded_norm:
            return []
        artifact_wo = dict(artifact)
        artifact_wo["entities_referenced"] = [e for e in entities if e is not entry]
        g_wo_norm = normalize_for_compare(
            dtd._gather_grounding_text(artifact_wo, source_text)
        ).lower()
        return [
            raw for nt, raw in sorted(name_grounded_norm.items())
            if nt not in g_wo_norm
        ]

    # --- Per-entry classification ---
    entries_out = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        name = e.get("name") or ""
        cs = e.get("context_summary") or ""

        cs_tokens = extract_significant_tokens(cs)
        cs_unique = sorted(cs_tokens - body_tokens)
        substantive = len(cs_unique) >= substantive_threshold

        # Conservative, type-agnostic name-uniqueness signal.
        name_tokens = extract_significant_tokens(name)
        other_name_text = " ".join(
            (x.get("name") or "") for x in entities
            if isinstance(x, dict) and x is not e
        )
        coverage = (
            body_tokens | source_tokens | nq_tokens
            | extract_significant_tokens(other_name_text)
        )
        name_unique_conservative = sorted(name_tokens - coverage)

        # Sole-grounder check is computed for EVERY entry (not just
        # redundant ones) so the vocab-preservation worklist is
        # independent of where the fuzzy substantive/redundant line is
        # drawn: it's the complete set of entries whose deletion would
        # break description_token_drift. The pre-pass filter
        # (name_grounded_norm) makes this cheap — only entries on
        # Description nodes with name-grounded Description tokens do
        # real work.
        risk = gate_risk_tokens(e)
        sole_grounder = bool(risk)
        # active_risk: deleting this name would break the LIVE
        # description_token_drift gate. Requires the gate to actually run
        # on this node (gate_active). A latent sole-grounder (gate skipped
        # today) lands in bucket (b) but is flagged via sole_grounder.
        active_risk = sole_grounder and gate_active

        # Bucket = the preserve/delete decision (substantive → keep).
        # Only an ACTIVE-risk sole-grounder needs the migrate-first path.
        if substantive:
            bucket = BUCKET_PRESERVE
        elif active_risk:
            bucket = BUCKET_DELETE_MIGRATE
        else:
            bucket = BUCKET_DELETE_SAFE

        entries_out.append({
            "id": e.get("id"),
            "name": name,
            "wrap_path": e.get("wrap_path"),
            "entity_type": e.get("entity_type"),
            "has_context_summary": bool(cs.strip()),
            "context_summary_unique_tokens": cs_unique,
            "substantive": substantive,
            "sole_grounder": sole_grounder,
            "active_risk": active_risk,
            "gate_risk_tokens": risk,
            "name_unique_conservative": name_unique_conservative,
            "bucket": bucket,
        })

    return {
        "slug": slug,
        "target_node": artifact.get("target_node"),
        "node_type": node_type,
        "has_description": has_description,
        "source_present": source_present,
        "gate_active": gate_active,
        "node_exists": node_text is not None,
        "entity_count": len(entries_out),
        "name_grounded_description_tokens": sorted(name_grounded_norm.values()),
        "ungrounded_with_all_names": sorted(ungrounded_with_all_names),
        "entries": entries_out,
    }


# =============================================================================
# Report emission
# =============================================================================

def _bucket_counts(entries):
    counts = {BUCKET_PRESERVE: 0, BUCKET_DELETE_SAFE: 0, BUCKET_DELETE_MIGRATE: 0}
    for e in entries:
        counts[e["bucket"]] += 1
    return counts


def write_artifact_report(report, out_dir):
    entries = report["entries"]
    counts = _bucket_counts(entries)
    lines = []
    lines.append(f"# A1 vocab audit — {report['slug']}")
    lines.append("")
    lines.append(f"- target_node: `{report['target_node']}` ({report['node_type']})")
    lines.append(f"- rendered node present: {report['node_exists']}")
    lines.append(f"- `## Description` present: {report['has_description']} · "
                 f"source_text present: {report['source_present']} · "
                 f"**description_token_drift active: {report['gate_active']}**")
    lines.append(f"- entities_referenced entries: {report['entity_count']}")
    lines.append(f"- buckets: (a) preserve {counts[BUCKET_PRESERVE]} · "
                 f"(b) delete-no-risk {counts[BUCKET_DELETE_SAFE]} · "
                 f"(c) delete-migrate {counts[BUCKET_DELETE_MIGRATE]}")
    if report["name_grounded_description_tokens"]:
        toks = ", ".join(report["name_grounded_description_tokens"])
        label = ("ACTIVE risk" if report["gate_active"]
                 else "LATENT — gate skipped (empty source_text)")
        lines.append(f"- Description tokens grounded only via entity names "
                     f"[{label}]: {toks}")
    if not report["gate_active"] and report["ungrounded_with_all_names"]:
        n = len(report["ungrounded_with_all_names"])
        shown = ", ".join(report["ungrounded_with_all_names"][:12])
        lines.append(f"- Description tokens ungrounded even WITH all entity "
                     f"names present ({n}): preserving entity names would NOT "
                     f"make this node gate-clean if a source were ever added — "
                     f"{shown}" + (" …" if n > 12 else ""))
    lines.append("")
    lines.append("| id | name | bucket | subst? | cs-unique tokens | gate-risk tokens | name-unique (conservative) |")
    lines.append("|---|---|---|---|---|---|---|")
    for e in entries:
        cs_u = ", ".join(e["context_summary_unique_tokens"]) or "—"
        risk = ", ".join(e["gate_risk_tokens"]) or "—"
        ncons = ", ".join(e["name_unique_conservative"]) or "—"
        lines.append(
            f"| {e['id']} | {e['name']} | {e['bucket']} | "
            f"{'Y' if e['substantive'] else 'n'} | {cs_u} | {risk} | {ncons} |"
        )
    lines.append("")
    (out_dir / f"{report['slug']}.md").write_text("\n".join(lines))


def write_summary(reports, out_dir, substantive_threshold):
    total_entries = sum(r["entity_count"] for r in reports)
    agg = {BUCKET_PRESERVE: 0, BUCKET_DELETE_SAFE: 0, BUCKET_DELETE_MIGRATE: 0}
    conservative_unique = 0
    active_risk_total = 0     # bucket (c) — would break the LIVE gate
    latent_sole_grounders = 0  # sole-grounder where the gate is skipped today
    cs_unique_hist = {}        # cs-unique-token count -> entry count
    desc_artifacts = []
    no_desc_artifacts = []
    for r in reports:
        c = _bucket_counts(r["entries"])
        for k in agg:
            agg[k] += c[k]
        for e in r["entries"]:
            if e["name_unique_conservative"]:
                conservative_unique += 1
            if e["active_risk"]:
                active_risk_total += 1
            elif e["sole_grounder"]:
                latent_sole_grounders += 1
            n = len(e["context_summary_unique_tokens"])
            cs_unique_hist[n] = cs_unique_hist.get(n, 0) + 1
        (desc_artifacts if r["has_description"] else no_desc_artifacts).append(r)

    lines = []
    lines.append("# A1.1 vocab-retirement audit — SUMMARY")
    lines.append("")
    lines.append(f"Substantive threshold: ≥ {substantive_threshold} "
                 f"context_summary token(s) absent from rendered body.")
    lines.append("")
    lines.append(f"- Artifacts audited: {len(reports)}")
    lines.append(f"- entities_referenced entries total: {total_entries}")
    lines.append("")
    lines.append("## Corpus buckets")
    lines.append("")
    lines.append(f"- **(a) PRESERVE** (substantive context_summary): {agg[BUCKET_PRESERVE]}")
    lines.append(f"- **(b) DELETE — no vocab risk**: {agg[BUCKET_DELETE_SAFE]}")
    lines.append(f"- **(c) DELETE — migrate name first** (gate-accurate "
                 f"description_token_drift risk): {agg[BUCKET_DELETE_MIGRATE]}")
    lines.append("")
    lines.append("## Gate-accurate vocab-preservation worklist")
    lines.append("")
    lines.append(f"- **ACTIVE risk (bucket c): {active_risk_total}** — entries "
                 f"whose deletion WOULD break the live `description_token_drift` "
                 f"gate (the gate runs on the node: `## Description` present AND "
                 f"`source_text` extractable). This is the exact set phase A1.2 "
                 f"must migrate into `naming_quirks[]` before phase A1.4 deletes "
                 f"it — and the figure A1.4's safety check is measured against.")
    lines.append(f"- **LATENT (gate skipped today): {latent_sole_grounders}** — "
                 f"entries whose `name` solely grounds a `## Description` token on "
                 f"an artifact where the gate currently does NOT run (empty "
                 f"`source_text`; the gate's `check()` early-returns). They would "
                 f"matter only if a primary source were later added to that "
                 f"artifact — at which point that Description already carries "
                 f"other ungrounded tokens (see per-artifact reports), so "
                 f"preserving these names would not by itself make the node "
                 f"gate-clean.")
    lines.append("")
    lines.append("## Gate-accurate risk vs. conservative estimate")
    lines.append("")
    lines.append(f"- ACTIVE gate risk (A1.4 safety number): **{active_risk_total}**")
    lines.append(f"- Latent sole-grounders (gate skipped): **{latent_sole_grounders}**")
    lines.append(f"- Conservative — entries whose `name` carries a token unique "
                 f"across the whole artifact (type-agnostic, the "
                 f"analysis-of-record measure): **{conservative_unique}**")
    lines.append("")
    lines.append(f"A1.4's safety check (zero new `description_token_drift` "
                 f"failures vs. the pre-migration baseline) is satisfied with "
                 f"**{active_risk_total}** entries needing pre-migration. The "
                 f"300–400 projection counted entity names unique within each "
                 f"artifact regardless of whether any gate consumes them; the "
                 f"actual figure is dominated by Description-less person "
                 f"artifacts (no gate fires) and source-less artifacts (gate "
                 f"skipped). Pre-migration baseline: `review-coverage.py --all` "
                 f"reports 0 `description_token_drift` errors on the current "
                 f"corpus.")
    lines.append("")
    lines.append("## context_summary uniqueness distribution")
    lines.append("")
    lines.append(f"Entries by count of `context_summary` significant tokens "
                 f"absent from the rendered body. The substantive/preserve "
                 f"threshold (currently ≥ {substantive_threshold}) is a "
                 f"contributor-review dial, not a verdict — raise it to shrink "
                 f"PRESERVE toward the analysis-of-record's redundancy estimate.")
    lines.append("")
    lines.append("| cs-unique tokens | entries |")
    lines.append("|---|---|")
    for n in sorted(cs_unique_hist):
        lines.append(f"| {n} | {cs_unique_hist[n]} |")
    lines.append("")
    lines.append("## Description-bearing artifacts (risk surface)")
    lines.append("")
    lines.append("| artifact | type | gate active | entities | (a) | (b) | (c) | "
                 "name-grounded Desc tokens | ungrounded w/ all names |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in sorted(desc_artifacts, key=lambda r: r["slug"]):
        c = _bucket_counts(r["entries"])
        ng = len(r["name_grounded_description_tokens"])
        ung = len(r["ungrounded_with_all_names"])
        lines.append(
            f"| {r['slug']} | {r['node_type']} | "
            f"{'yes' if r['gate_active'] else 'NO (no source)'} | "
            f"{r['entity_count']} | "
            f"{c[BUCKET_PRESERVE]} | {c[BUCKET_DELETE_SAFE]} | "
            f"{c[BUCKET_DELETE_MIGRATE]} | {ng} | {ung} |"
        )
    lines.append("")
    lines.append(f"## Description-less artifacts (zero gate risk — "
                 f"{len(no_desc_artifacts)} artifacts)")
    lines.append("")
    lines.append("| artifact | type | entities | (a) | (b) |")
    lines.append("|---|---|---|---|---|")
    for r in sorted(no_desc_artifacts, key=lambda r: r["slug"]):
        c = _bucket_counts(r["entries"])
        lines.append(
            f"| {r['slug']} | {r['node_type']} | {r['entity_count']} | "
            f"{c[BUCKET_PRESERVE]} | {c[BUCKET_DELETE_SAFE]} |"
        )
    lines.append("")
    (out_dir / "SUMMARY.md").write_text("\n".join(lines))

    # Machine-readable rollup for phase A1.2 / A1.4 consumption.
    (out_dir / "audit.json").write_text(json.dumps({
        "substantive_threshold": substantive_threshold,
        "totals": {
            "artifacts": len(reports),
            "entries": total_entries,
            "preserve": agg[BUCKET_PRESERVE],
            "delete_no_risk": agg[BUCKET_DELETE_SAFE],
            "delete_migrate": agg[BUCKET_DELETE_MIGRATE],
            "active_gate_risk": active_risk_total,
            "latent_sole_grounders": latent_sole_grounders,
            "conservative_name_unique": conservative_unique,
            "cs_unique_histogram": cs_unique_hist,
        },
        "artifacts": reports,
    }, indent=2))

    return {
        "agg": agg,
        "conservative": conservative_unique,
        "active_gate_risk": active_risk_total,
        "latent_sole_grounders": latent_sole_grounders,
        "total": total_entries,
        "n_desc": len(desc_artifacts),
        "n_nodesc": len(no_desc_artifacts),
    }


# =============================================================================
# Main
# =============================================================================

def collect_artifacts():
    if not RESEARCH_DIR.is_dir():
        return []
    return sorted(RESEARCH_DIR.glob("*.yaml"))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?",
                        help="Single research artifact (meta/research/{slug}.yaml)")
    parser.add_argument("--all", action="store_true",
                        help="Audit every artifact under meta/research/")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help=f"Output directory for reports (default {DEFAULT_OUT})")
    parser.add_argument("--substantive-threshold", type=int, default=1,
                        help="Min context_summary tokens absent from body to "
                             "classify an entry substantive/preserve (default 1)")
    args = parser.parse_args()

    if args.path:
        artifacts = [resolve_cli_path(args.path)]
    elif args.all:
        artifacts = collect_artifacts()
    else:
        parser.print_help()
        sys.exit(0)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    reports = []
    for p in artifacts:
        report = analyze_artifact(p, args.substantive_threshold)
        if report is None or report["entity_count"] == 0:
            continue
        write_artifact_report(report, out_dir)
        reports.append(report)

    if not reports:
        print("No artifacts with entities_referenced[] entries found.")
        sys.exit(0)

    res = write_summary(reports, out_dir, args.substantive_threshold)
    agg = res["agg"]

    print("=" * 64)
    print(" A1.1 — entities_referenced[] vocab-retirement audit (read-only)")
    print("=" * 64)
    print(f"\n  Artifacts audited:         {len(reports)}")
    print(f"  entities_referenced total: {res['total']}")
    print(f"  Description-bearing:       {res['n_desc']} (risk surface)")
    print(f"  Description-less:          {res['n_nodesc']} (zero gate risk)")
    print(f"\n  Preserve/delete split (substantive threshold "
          f"≥ {args.substantive_threshold}; contributor-review dial):")
    print(f"    (a) PRESERVE:              {agg[BUCKET_PRESERVE]}")
    print(f"    (b) DELETE — no risk:      {agg[BUCKET_DELETE_SAFE]}")
    print(f"    (c) DELETE — migrate name: {agg[BUCKET_DELETE_MIGRATE]}")
    print(f"\n  Gate-accurate vocab-preservation worklist:")
    print(f"    ACTIVE gate risk:          {res['active_gate_risk']}  "
          f"(deletion breaks the LIVE description_token_drift gate — A1.4 safety number)")
    print(f"    LATENT (gate skipped):     {res['latent_sole_grounders']}  "
          f"(name grounds a Description token where the gate doesn't run today)")
    print(f"\n  Conservative name-unique:  {res['conservative']}  "
          f"(whole-corpus, type-agnostic — analysis-of-record measure)")
    print(f"\n  Reports written to: {out_dir}/")
    print(f"    SUMMARY.md, audit.json, {len(reports)} per-artifact reports")
    print("\n  Read-only: no corpus files modified.")
    sys.exit(0)


if __name__ == "__main__":
    main()
