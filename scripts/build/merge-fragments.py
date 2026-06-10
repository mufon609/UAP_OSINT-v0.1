#!/usr/bin/env python3
"""merge-fragments.py — mechanical transport of worker-fragment verbatim data
into a research artifact.

The worker emits its fragment as a YAML file (``/tmp/fragments-{slug}/{stem}.yaml``
— `.claude/agents/worker.md`); this script copies the **verbatim
payload** — ``quotes[]`` and ``cited_works`` — into the artifact byte-exactly.
An LLM retyping verbatim spans into the artifact is a drift surface the
verbatim-quote check exists to catch (and was the builder's single largest
token cost); a mechanical copy removes the surface. The judgment payload
(``cross_ref_candidates`` / ``background_material`` / ``naming_quirks_flagged``
/ ``notes``) is **not** transported — the builder reads it from the fragment
file and exercises contract-owned judgment.

Policy-injection defense: only the schema fields below are copied; anything
else in a fragment file is ignored. Prose cannot ride the transport.

Fragment file shape (one per source; the worker stub carries its path):
  slug: {slug}
  worker_kind: pdf            # pdf | html | caption | foia
  source: {category}/{file}.pdf
  quotes:                     # may be [] (about-the-subject source)
    - text: "<verbatim>"
      location: "<source-shape anchor>"
      # optional: significance, context, claim_group, statement_date,
      #           observation_type, category
  cited_works: NONE | IGNORED | [{citation_key, author, citation_verbatim,
                                  location, year?, title?}, ...]
                              # document sources only; bare [] REJECTED
  cross_ref_candidates: [...] # judgment payload — read by the builder, not merged here
  background_material: [...]
  naming_quirks_flagged: [...]
  notes: |                    # optional, non-normative (stub-schemas.md)

What this script writes onto the artifact:
  quotes[]      — id q1..qN (fragment argument order), added_date (today),
                  source: {path: <fragment source>, location: <location>},
                  the optional fields copied verbatim when present
  cited_works   — sentinel, or entries with id cw1..cwN + added_date +
                  source: {path, location}; multi-fragment lists concatenate;
                  a sentinel/list shape mismatch across fragments exits with
                  ``cited_works_shape_conflict`` (the builder's fail token)

Guards: refuses an artifact whose quotes[] is already populated (the build
merge runs once, post-scaffold) — ``--append`` is the explicit maintenance
path (`/augment` Shape B): it allows a populated artifact and continues id
numbering from the highest existing qN/cwN. Validates every quote has
non-empty text+location; rejects ``cited_works: []``. After a merge, the
builder runs ``validate-research.py --phase extract`` — this script is
transport, not the gate.

Usage:
  merge-fragments.py meta/research/{slug}.yaml /tmp/fragments-{slug}/{stem}.yaml [...]
  merge-fragments.py --append meta/research/{slug}.yaml /tmp/fragments-... [...]
  merge-fragments.py --selftest
"""

import argparse
import datetime
import sys
from pathlib import Path

from ruamel.yaml import YAML

QUOTE_OPTIONAL = ("significance", "context", "claim_group", "statement_date",
                  "observation_type", "category")
CITED_REQUIRED = ("citation_key", "author", "citation_verbatim", "location")
CITED_OPTIONAL = ("year", "title")
SENTINELS = ("NONE", "IGNORED")


def _yaml() -> YAML:
    """ruamel configured for round-trip fidelity (mirrors stamp-speaker-id.py):
    preserve quotes, never wrap long scalars, explicit `null`."""
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.representer.add_representer(
        type(None),
        lambda r, d: r.represent_scalar("tag:yaml.org,2002:null", "null"),
    )
    return y


def _fail(msg):
    raise SystemExit(f"merge-fragments: {msg}")


def load_fragment(path):
    """Load + shape-check one fragment file. Returns the parsed dict."""
    p = Path(path)
    if not p.exists():
        _fail(f"fragment not found: {p}")
    frag = _yaml().load(p.read_text(encoding="utf-8"))
    if not isinstance(frag, dict):
        _fail(f"{p}: fragment is not a YAML mapping")
    src = frag.get("source")
    if not isinstance(src, str) or not src.strip():
        _fail(f"{p}: missing/empty `source` (the {{category}}/{{file}} path)")
    quotes = frag.get("quotes")
    if not isinstance(quotes, list):
        _fail(f"{p}: `quotes` must be a list (may be empty)")
    for i, q in enumerate(quotes, 1):
        if not isinstance(q, dict):
            _fail(f"{p}: quotes[{i}] is not a mapping")
        for req in ("text", "location"):
            v = q.get(req)
            if not isinstance(v, str) or not v.strip():
                _fail(f"{p}: quotes[{i}] missing/empty `{req}`")
    cw = frag.get("cited_works", None)
    if cw is not None:
        if isinstance(cw, str):
            if cw not in SENTINELS:
                _fail(f"{p}: cited_works string must be one of {SENTINELS}, got {cw!r}")
        elif isinstance(cw, list):
            if not cw:
                _fail(f"{p}: cited_works: [] is REJECTED — affirm NONE, IGNORED, "
                      f"or a non-empty list (three-state affirmation)")
            for i, e in enumerate(cw, 1):
                if not isinstance(e, dict):
                    _fail(f"{p}: cited_works[{i}] is not a mapping")
                for req in CITED_REQUIRED:
                    v = e.get(req)
                    if v is None or (isinstance(v, str) and not v.strip()):
                        _fail(f"{p}: cited_works[{i}] missing/empty `{req}`")
        else:
            _fail(f"{p}: cited_works must be NONE / IGNORED / non-empty list")
    return frag


def merge_cited_works(fragments):
    """Resolve the artifact-level cited_works from the fragments' three-state
    values. All sentinels equal -> that sentinel; all lists -> concatenation in
    fragment order; absent everywhere -> None (leave artifact untouched); any
    mixed shape -> cited_works_shape_conflict."""
    present = [(f, f.get("cited_works")) for f in fragments
               if f.get("cited_works") is not None]
    if not present:
        return None
    vals = [v for _, v in present]
    if all(isinstance(v, str) for v in vals):
        if len(set(vals)) > 1:
            _fail("cited_works_shape_conflict: fragments affirm different "
                  f"sentinels {sorted(set(vals))} — route to the owning role")
        return vals[0]
    if all(isinstance(v, list) for v in vals):
        merged = []
        for f, v in present:
            merged.extend((f["source"], e) for e in v)
        return merged
    _fail("cited_works_shape_conflict: fragments mix sentinel and list shapes "
          "— route to the owning role")


def _next_n(entries, prefix):
    """1 + the highest existing {prefix}N id (0 base when none)."""
    top = 0
    for e in entries or []:
        i = str(e.get("id", ""))
        if i.startswith(prefix) and i[len(prefix):].isdigit():
            top = max(top, int(i[len(prefix):]))
    return top + 1


def merge(artifact_path, fragment_paths, today=None, append=False):
    """The merge. Returns (n_quotes, cited_shape_desc) after writing."""
    today = today or datetime.date.today().isoformat()
    y = _yaml()
    ap = Path(artifact_path)
    if not ap.exists():
        _fail(f"artifact not found: {ap}")
    art = y.load(ap.read_text(encoding="utf-8"))
    if not isinstance(art, dict) or "quotes" not in art:
        _fail(f"{ap}: not a research artifact (no quotes section)")
    if art.get("quotes") and not append:
        _fail(f"{ap}: quotes[] already populated — the build merge runs once, "
              f"post-scaffold; this guard prevents a double merge "
              f"(maintenance additions use --append)")

    fragments = [load_fragment(p) for p in fragment_paths]

    qn = _next_n(art.get("quotes"), "q") - 1 if append else 0
    base_qn = qn
    quotes_out = list(art.get("quotes") or []) if append else []
    for frag in fragments:
        for q in frag["quotes"]:
            qn += 1
            entry = {"id": f"q{qn}", "added_date": today, "text": q["text"],
                     "source": {"path": frag["source"], "location": q["location"]}}
            for opt in QUOTE_OPTIONAL:
                if q.get(opt) is not None:
                    entry[opt] = q[opt]
            quotes_out.append(entry)
    art["quotes"] = quotes_out

    cited = merge_cited_works(fragments)
    cited_desc = "untouched (no fragment carried cited_works)"
    if isinstance(cited, str):
        existing = art.get("cited_works")
        if append and isinstance(existing, list) and existing:
            _fail("cited_works_shape_conflict: fragment affirms a sentinel but "
                  "the artifact already carries entries — route to the owning role")
        art["cited_works"] = cited
        cited_desc = cited
    elif isinstance(cited, list):
        existing = art.get("cited_works")
        out, cn = [], 0
        if append and isinstance(existing, list):
            out = list(existing)
            cn = _next_n(existing, "cw") - 1
        elif append and isinstance(existing, str) and existing in SENTINELS:
            _fail("cited_works_shape_conflict: fragment carries entries but the "
                  f"artifact affirms {existing} — route to the owning role")
        for src_path, e in cited:
            cn += 1
            entry = {"id": f"cw{cn}", "added_date": today,
                     "citation_key": e["citation_key"], "author": e["author"]}
            for opt in CITED_OPTIONAL:
                if e.get(opt) is not None:
                    entry[opt] = e[opt]
            entry["citation_verbatim"] = e["citation_verbatim"]
            entry["source"] = {"path": src_path, "location": e["location"]}
            out.append(entry)
        art["cited_works"] = out
        cited_desc = f"{len(out)} entries"

    with ap.open("w", encoding="utf-8") as fh:
        y.dump(art, fh)
    return qn - base_qn, cited_desc


def cmd_selftest():
    import tempfile
    failures = []
    yam = _yaml()

    def write(tmpdir, name, obj):
        p = Path(tmpdir) / name
        with p.open("w", encoding="utf-8") as fh:
            yam.dump(obj, fh)
        return p

    scaffold = {"id": "meta/research/t", "type": "research-artifact",
                "target_node": "documents/t", "status": "active",
                "primary_sources": [{"path": "government/t.pdf", "format": "pdf"}],
                "document_intrinsic": {}, "context_extrinsic": {},
                "quotes": [], "naming_quirks": [], "description": "",
                "cited_works": ""}
    tricky = ("Prepared by: (b)(3):10 USC 424 — RuO₂ gives 1,300 F/cm³; "
              "'single' \"double\" …µm→um")
    frag1 = {"slug": "t", "worker_kind": "pdf", "source": "government/t.pdf",
             "quotes": [{"text": tricky, "location": "Summary, ¶1",
                         "significance": "sig", "claim_group": "g1"},
                        {"text": "second span", "location": "Ch. 2 anchor"}],
             "cited_works": [{"citation_key": "1", "author": "P. simon",
                              "citation_verbatim": "¹ P. simon, Science, 313, 1760 (2006)",
                              "location": "Endnotes, entry 1", "year": 2006}],
             "cross_ref_candidates": [{"entity": "/organizations/x"}],
             "notes": "advisory only — must not merge"}

    with tempfile.TemporaryDirectory() as td:
        a = write(td, "artifact.yaml", dict(scaffold))
        f1 = write(td, "frag1.yaml", frag1)
        n, desc = merge(a, [f1], today="2026-06-10")
        back = yam.load(a.read_text(encoding="utf-8"))
        if n != 2 or len(back["quotes"]) != 2:
            failures.append(f"merge count: expected 2 quotes, got {n}")
        q1 = back["quotes"][0]
        if q1["text"] != tricky:
            failures.append(f"byte-exact round-trip failed: {q1['text']!r}")
        if q1["id"] != "q1" or q1["added_date"] != "2026-06-10":
            failures.append(f"id/date stamping failed: {q1['id']}/{q1['added_date']}")
        if q1["source"]["path"] != "government/t.pdf" or q1["source"]["location"] != "Summary, ¶1":
            failures.append(f"source block wrong: {dict(q1['source'])}")
        cw = back["cited_works"][0]
        if (cw["id"], cw["citation_verbatim"]) != ("cw1", "¹ P. simon, Science, 313, 1760 (2006)"):
            failures.append(f"cited_works transport failed: {dict(cw)}")
        if "notes" in back or any("cross_ref" in k for k in back):
            failures.append("judgment payload leaked into artifact")
        # double-merge guard
        try:
            merge(a, [f1], today="2026-06-10")
            failures.append("double-merge guard did not fire")
        except SystemExit as e:
            if "already populated" not in str(e):
                failures.append(f"double-merge guard wrong message: {e}")

        # --append continues id numbering on a populated artifact
        frag_app = {"slug": "t", "worker_kind": "pdf", "source": "government/t2.pdf",
                    "quotes": [{"text": "appended span", "location": "¶3"}],
                    "cited_works": [{"citation_key": "2", "author": "B",
                                     "citation_verbatim": "² B, line", "location": "entry 2"}]}
        fa = write(td, "frag-append.yaml", frag_app)
        n2, _ = merge(a, [fa], today="2026-06-11", append=True)
        back2 = yam.load(a.read_text(encoding="utf-8"))
        if n2 != 1 or back2["quotes"][-1]["id"] != "q3":
            failures.append(f"append: expected q3 appended, got n={n2}, last id "
                            f"{back2['quotes'][-1]['id']}")
        if back2["quotes"][0]["text"] != tricky:
            failures.append("append: existing quotes disturbed")
        if back2["cited_works"][-1]["id"] != "cw2" or back2["cited_works"][0]["id"] != "cw1":
            failures.append(f"append: cited_works numbering wrong: "
                            f"{[c['id'] for c in back2['cited_works']]}")
        # append sentinel-vs-entries conflict
        fs = write(td, "frag-app-none.yaml", dict(frag_app, cited_works="NONE"))
        try:
            merge(a, [fs], append=True)
            failures.append("append sentinel-vs-entries conflict not detected")
        except SystemExit as e:
            if "cited_works_shape_conflict" not in str(e):
                failures.append(f"append conflict wrong token: {e}")

        # bare [] rejection
        a2 = write(td, "a2.yaml", dict(scaffold))
        bad = dict(frag1, cited_works=[])
        f2 = write(td, "frag-bad.yaml", bad)
        try:
            merge(a2, [f2])
            failures.append("bare [] cited_works accepted")
        except SystemExit as e:
            if "REJECTED" not in str(e):
                failures.append(f"bare [] wrong message: {e}")

        # sentinel/list shape conflict
        a3 = write(td, "a3.yaml", dict(scaffold))
        f3 = write(td, "frag-none.yaml", dict(frag1, cited_works="NONE"))
        try:
            merge(a3, [f1, f3])
            failures.append("shape conflict not detected")
        except SystemExit as e:
            if "cited_works_shape_conflict" not in str(e):
                failures.append(f"conflict wrong token: {e}")

        # missing location rejected
        a4 = write(td, "a4.yaml", dict(scaffold))
        f4 = write(td, "frag-noloc.yaml",
                   dict(frag1, quotes=[{"text": "x"}], cited_works="NONE"))
        try:
            merge(a4, [f4])
            failures.append("missing location accepted")
        except SystemExit as e:
            if "location" not in str(e):
                failures.append(f"missing-location wrong message: {e}")

    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELFTEST PASSED — verbatim transport is byte-exact and guarded")
    print("  byte-exact quote + citation round-trip (unicode, sic, quote chars)")
    print("  id/added_date/source stamping; judgment payload never merged")
    print("  guards: double-merge, bare [] cited_works, shape conflict, missing location")
    print("  --append: continues qN/cwN numbering, never disturbs existing entries")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Mechanically merge worker fragment files' verbatim payload "
                    "(quotes, cited_works) into a research artifact.")
    ap.add_argument("--selftest", action="store_true",
                    help="run synthetic merge tests and exit (no repo files touched)")
    ap.add_argument("--append", action="store_true",
                    help="maintenance mode (/augment Shape B): allow a populated "
                         "artifact and continue id numbering from the highest "
                         "existing qN/cwN")
    ap.add_argument("artifact", nargs="?", help="meta/research/{slug}.yaml")
    ap.add_argument("fragments", nargs="*", help="fragment file path(s), in source order")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(cmd_selftest())
    if not args.artifact or not args.fragments:
        ap.error("artifact and at least one fragment path required (or --selftest)")
    n, cited_desc = merge(args.artifact, args.fragments, append=args.append)
    print(f"✓ merged {n} quote(s) from {len(args.fragments)} fragment(s) into {args.artifact}")
    print(f"  cited_works: {cited_desc}")
    print(f"  next: python3 scripts/build/validate-research.py --phase extract {args.artifact}")


if __name__ == "__main__":
    main()
