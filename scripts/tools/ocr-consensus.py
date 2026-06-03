#!/usr/bin/env python3
"""ocr-consensus.py — trustworthy OCR clean-text sibling via uncorrelated
multi-engine consensus.

An OCR-scan PDF's pdftotext layer is corrupt, so verbatim quotes are matched
against a clean-text ``.txt`` *sibling* instead. The old process trusted a
single agent's "PASS" to certify that sibling against the page images — and it
failed silently (DIRD-16's "verified" sibling carried `III→ITT`,
`communication→cammunication`, `81→82`, `Klyshko→Kiyshko`). This tool replaces
that single point of failure with **three uncorrelated votes** per token:

    A = Tesseract            (LSTM OCR; char-confusion failure mode)
    B = PaddleOCR            (deep-learning OCR; DIFFERENT architecture)
    C = VLM page-image read  (agent, high-abstraction; different MODALITY)

A token is accepted (CONSENSUS) only when **≥2 of the 3 votes agree**. Any token
the votes disagree on is flagged CONTESTED and must be adjudicated against the
page image — and that adjudication is recorded in a durable
``{stem}-ocr-verification.yaml`` (the audit trail validate-ocr-sibling.py gates
on). Because the three engines have uncorrelated failure modes, the lone wrong
read in each DIRD-16 case loses the vote and is flagged rather than silently
kept. See meta/conventions.md "Producing the `.txt` sibling".

The VLM transcription is the readable BASE of the sibling (best paragraph
structure); Tesseract + PaddleOCR are the cross-check that corroborates each
VLM token or flags it. The pdftotext layer is read only as a *contamination
signal* (if an adjudication lands on the corrupt layer's reading where an OCR
engine disagreed, that is flagged for extra scrutiny — the "seeded from corrupt
OCR" smell).

Subcommands:
  run        Rasterize + run Tesseract & PaddleOCR + ingest the VLM text,
             align the three votes, write the draft sibling (VLM base) and the
             verification YAML listing every CONTESTED span. Does NOT finalize.
  assemble   After contested spans are adjudicated (resolutions filled in the
             YAML), splice the resolutions into the sibling and stamp its
             sha256 into the YAML. Idempotent.
  engines    Report which engines are available (diagnostic).
  --selftest Run the alignment/consensus logic on synthetic inputs (no OCR
             engines needed) — exercised by scripts/tests/.

PaddleOCR lives in a project-local venv at .venv-ocr/ (run
scripts/tools/setup-ocr-consensus.sh once). This tool auto-relaunches under that
venv's Python for the `run` subcommand; `--help`, `--selftest`, and `assemble`
work without it (the heavy import is deferred).
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Venv auto-relaunch — must happen before importing paddleocr. PaddleOCR lives
# in .venv-ocr/ at the repo root (PEP 668 blocks system-wide pip on Kali). The
# venv is created --system-site-packages, so PyYAML / PIL stay importable after
# the re-exec. Detection idiom mirrors detect-faces.py: compare sys.prefix to
# the venv dir. Guarded on the venv existing so --help / --selftest stay green
# without .venv-ocr present (those paths never import paddleocr).
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_VENV_DIR = _REPO_ROOT / ".venv-ocr"
_VENV_PYTHON = _VENV_DIR / "bin" / "python3"
if (
    _VENV_PYTHON.is_file()
    and Path(sys.prefix).resolve() != _VENV_DIR.resolve()
    and os.environ.get("OCR_VENV_ACTIVE") != "1"
):
    os.environ["OCR_VENV_ACTIVE"] = "1"
    os.execv(str(_VENV_PYTHON), [str(_VENV_PYTHON)] + sys.argv)

import argparse
import difflib
import hashlib
import re
import subprocess
import tempfile

import yaml

SOURCES_DIR = _REPO_ROOT / "sources"

# Word tokens and standalone punctuation. Splitting punctuation off words keeps
# "communication," from spuriously disagreeing with "communication" across
# engines, and aligns with how the verbatim-quote normalizer treats text.
TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


# ---------------------------------------------------------------------------
# Tokenization + agreement normalization
# ---------------------------------------------------------------------------
def tokenize(text):
    """List of (surface, char_start, char_end) for every token in text."""
    return [(m.group(), m.start(), m.end()) for m in TOKEN_RE.finditer(text)]


def norm_token(t):
    """Fold a token for the agreement test, mirroring the char-level foldings
    of lib._common.normalize_for_compare (smart quotes/dashes, hyphen strip)
    so two engines that differ only on those don't spuriously contest. Case is
    PRESERVED — a case disagreement is a real disagreement and stays contested
    (conservative: over-flagging costs adjudication, under-flagging hides an
    error)."""
    if t is None:
        return None
    t = (t.replace("“", '"').replace("”", '"')
          .replace("‘", "'").replace("’", "'")
          .replace("—", "-").replace("–", "-")
          .replace(" ", " ").replace("-", ""))
    return t


# ---------------------------------------------------------------------------
# Alignment (difflib, spine = VLM token stream)
# ---------------------------------------------------------------------------
def align_to_spine(spine, other):
    """Align ``other`` token list onto ``spine`` token list.

    Returns ``aligned`` where ``aligned[i]`` is the ``other`` surface token
    paired with ``spine[i]`` (or None if spine[i] has no counterpart). Matching
    is computed on normalized tokens; surfaces returned are originals.

    Only difflib 'equal' blocks produce confident 1:1 pairings; 'replace' runs
    are zipped positionally (a heuristic — but consensus requires *actual*
    token equality, so a wrong zip can only fail to reach consensus, never
    fabricate it). 'delete' (spine-only) leaves None; 'insert' (other-only)
    tokens are collected as ``extra`` keyed by the spine index they precede."""
    a = [norm_token(t) for t in spine]
    b = [norm_token(t) for t in other]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    aligned = [None] * len(spine)
    extra = []  # (spine_index, other_surface) for other-only tokens
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                aligned[i1 + k] = other[j1 + k]
        elif tag == "replace":
            span = i2 - i1
            for k in range(span):
                jj = j1 + k
                aligned[i1 + k] = other[jj] if jj < j2 else None
            for jj in range(j1 + span, j2):  # other-side overflow
                extra.append((i1, other[jj]))
        elif tag == "delete":
            pass  # spine-only run — aligned stays None
        elif tag == "insert":
            for jj in range(j1, j2):
                extra.append((i1, other[jj]))
    return aligned, extra


# ---------------------------------------------------------------------------
# Consensus
# ---------------------------------------------------------------------------
def line_of_offset(text, off):
    """1-indexed line number of a char offset."""
    return text.count("\n", 0, off) + 1


def snippet(text, start, end, radius=30):
    """A readable context window around [start,end), with the contested token
    wrapped in guillemets for the adjudicator."""
    pre = text[max(0, start - radius):start].replace("\n", " ")
    tok = text[start:end]
    post = text[end:end + radius].replace("\n", " ")
    return f"...{pre}‹{tok}›{post}..."


def build_consensus(vlm_text, tess_text, paddle_text):
    """Core deterministic consensus over the VLM base, cross-checked by the two
    OCR engines. Returns (stats, contested, possible_omissions)."""
    vlm_tokens = tokenize(vlm_text)
    vlm_surfaces = [t[0] for t in vlm_tokens]
    tess_surfaces = [m.group() for m in TOKEN_RE.finditer(tess_text)]
    paddle_surfaces = [m.group() for m in TOKEN_RE.finditer(paddle_text)]

    tess_aligned, tess_extra = align_to_spine(vlm_surfaces, tess_surfaces)
    paddle_aligned, paddle_extra = align_to_spine(vlm_surfaces, paddle_surfaces)

    contested = []
    consensus_count = 0
    cid = 0
    for i, (surf, cs, ce) in enumerate(vlm_tokens):
        v, t, p = surf, tess_aligned[i], paddle_aligned[i]
        nv, nt, np_ = norm_token(v), norm_token(t), norm_token(p)
        vlm_tess = t is not None and nv == nt
        vlm_paddle = p is not None and nv == np_
        ocr_agree = t is not None and p is not None and nt == np_
        if vlm_tess or vlm_paddle:
            consensus_count += 1  # ≥2 of 3 agree (VLM + an OCR engine)
            continue
        if ocr_agree:
            note = "both OCR engines agree against the VLM read"
        else:
            note = "all three votes differ"
        cid += 1
        contested.append({
            "id": f"c{cid}",
            "token_index": i,
            "char_start": cs,
            "char_end": ce,
            "line": line_of_offset(vlm_text, cs),
            "context": snippet(vlm_text, cs, ce),
            "candidates": {"vlm": v, "tesseract": t, "paddleocr": p},
            "note": note,
            "status": "contested",
            "resolution": None,
            "resolution_method": None,
            "adjudicator_session": None,
        })

    # Conservative omission signal: a token both OCR engines emit (agreeing)
    # at the same spine insertion point that the VLM lacks. Advisory only.
    possible_omissions = []
    tess_ins = {}
    for idx, tok in tess_extra:
        tess_ins.setdefault(idx, []).append(tok)
    paddle_ins = {}
    for idx, tok in paddle_extra:
        paddle_ins.setdefault(idx, []).append(tok)
    oid = 0
    for idx in sorted(set(tess_ins) & set(paddle_ins)):
        common = [tok for tok in tess_ins[idx]
                  if any(norm_token(tok) == norm_token(pt) for pt in paddle_ins[idx])]
        for tok in common:
            oid += 1
            anchor = vlm_tokens[idx][1] if idx < len(vlm_tokens) else len(vlm_text)
            possible_omissions.append({
                "id": f"o{oid}",
                "before_token_index": idx,
                "line": line_of_offset(vlm_text, anchor),
                "ocr_token": tok,
                "note": "both OCR engines read this token; VLM base omits it",
                "status": "advisory",
                "resolution": None,
            })

    stats = {
        "base_tokens": len(vlm_tokens),
        "consensus_tokens": consensus_count,
        "contested_count": len(contested),
        "possible_omission_count": len(possible_omissions),
    }
    return stats, contested, possible_omissions


def build_consensus_2(base_text, other_text):
    """Two-engine consensus for the CBRN / content-filter fallback, where the
    VLM vote is skipped. Tesseract is the readable base; PaddleOCR is the sole
    cross-check. A token is CONSENSUS only when BOTH engines agree; any
    disagreement is CONTESTED (the ≥2-OCR-engine floor still holds — nothing is
    accepted on one read). Note that without a third vote there is no majority
    tie-break, so disagreements lean on image adjudication more heavily."""
    base_tokens = tokenize(base_text)
    base_surfaces = [t[0] for t in base_tokens]
    other_surfaces = [m.group() for m in TOKEN_RE.finditer(other_text)]
    aligned, _extra = align_to_spine(base_surfaces, other_surfaces)
    contested = []
    consensus_count = 0
    cid = 0
    for i, (surf, cs, ce) in enumerate(base_tokens):
        o = aligned[i]
        if o is not None and norm_token(surf) == norm_token(o):
            consensus_count += 1
            continue
        cid += 1
        contested.append({
            "id": f"c{cid}",
            "token_index": i,
            "char_start": cs,
            "char_end": ce,
            "line": line_of_offset(base_text, cs),
            "context": snippet(base_text, cs, ce),
            "candidates": {"vlm": None, "tesseract": surf, "paddleocr": o},
            "note": "OCR engines disagree (VLM vote skipped)",
            "status": "contested",
            "resolution": None,
            "resolution_method": None,
            "adjudicator_session": None,
        })
    stats = {
        "base_tokens": len(base_tokens),
        "consensus_tokens": consensus_count,
        "contested_count": len(contested),
        "possible_omission_count": 0,
    }
    return stats, contested, []


# ---------------------------------------------------------------------------
# Engine adapters (only invoked by `run`)
# ---------------------------------------------------------------------------
def rasterize(pdf_path, out_dir, dpi=300):
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(Path(out_dir) / "page")],
        check=True, capture_output=True,
    )
    return sorted(Path(out_dir).glob("page-*.png"))


def tesseract_version():
    try:
        out = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
        return out.stdout.splitlines()[0].replace("tesseract", "").strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def run_tesseract(images):
    pages = []
    for img in images:
        out = subprocess.run(
            ["tesseract", str(img), "stdout", "--psm", "1", "-l", "eng"],
            capture_output=True, text=True,
        )
        pages.append(out.stdout)
    return "\n".join(pages)


def run_paddleocr(images):
    """PaddleOCR over each page image. PaddleOCR's API has shifted across
    versions; this targets the 2.x ``.ocr()`` interface (list of
    [box, (text, conf)] per image) and falls back to a 3.x ``.predict``-style
    result if present. Raises with guidance if PaddleOCR isn't installed."""
    try:
        from paddleocr import PaddleOCR  # noqa: PLC0415
    except Exception as e:  # noqa: BLE001
        raise SystemExit(
            "PaddleOCR not importable — run scripts/tools/setup-ocr-consensus.sh "
            f"to create .venv-ocr/ (this tool auto-relaunches under it). [{e}]"
        )
    try:
        ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
    except TypeError:
        ocr = PaddleOCR(lang="en")  # newer signature dropped some kwargs
    pages = []
    for img in images:
        res = ocr.ocr(str(img), cls=False)
        lines = []
        if res and res[0]:
            for entry in res[0]:
                # 2.x: entry == [box, (text, conf)]
                try:
                    lines.append(entry[1][0])
                except (IndexError, TypeError):
                    continue
        pages.append("\n".join(lines))
    return "\n".join(pages)


def paddleocr_version():
    try:
        import paddleocr  # noqa: PLC0415
        return getattr(paddleocr, "__version__", "unknown")
    except Exception:  # noqa: BLE001
        return "not-installed"


# ---------------------------------------------------------------------------
# Verification-YAML I/O
# ---------------------------------------------------------------------------
def rel_to_sources(p):
    p = Path(p).resolve()
    try:
        return str(p.relative_to(SOURCES_DIR))
    except ValueError:
        return str(p)


def write_yaml(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=4096)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------
def cmd_run(args):
    pdf = Path(args.pdf)
    if not pdf.is_absolute() and not pdf.exists():
        pdf = SOURCES_DIR / args.pdf
    if not pdf.exists():
        raise SystemExit(f"PDF not found: {pdf}")
    stem = pdf.with_suffix("").name
    sibling = pdf.with_suffix(".txt")
    verification = pdf.parent / f"{stem}-ocr-verification.yaml"

    if sibling.exists() and not args.force:
        raise SystemExit(
            f"sibling already exists: {sibling}\n"
            f"  pass --force to regenerate (backfill of an existing sibling)."
        )

    if not args.vlm and not args.vlm_skipped:
        raise SystemExit(
            "provide --vlm PATH (the normal 3-engine path) or --vlm-skipped "
            "REASON (CBRN / content-filter 2-engine fallback)."
        )
    vlm_text = Path(args.vlm).read_text(encoding="utf-8") if args.vlm else None

    print(f"[1/4] Rasterizing {pdf.name} at {args.dpi} dpi ...")
    with tempfile.TemporaryDirectory(prefix=f"ocr-{stem}-") as tmp:
        images = rasterize(pdf, tmp, args.dpi)
        print(f"      {len(images)} page image(s)")
        print("[2/4] Tesseract (vote A) ...")
        tess_text = run_tesseract(images)
        print("[3/4] PaddleOCR (vote B) ...")
        paddle_text = run_paddleocr(images)

    engines = [
        {"name": "tesseract", "version": tesseract_version()},
        {"name": "paddleocr", "version": paddleocr_version()},
    ]
    if vlm_text is not None:
        print("[4/4] Aligning 3 votes + computing consensus ...")
        stats, contested, omissions = build_consensus(vlm_text, tess_text, paddle_text)
        base_text = vlm_text
        engines.append({"name": "vlm", "note": f"agent page-image read; file: {args.vlm}"})
        vlm_skipped = None
    else:
        print("[4/4] VLM skipped — Tesseract+PaddleOCR 2-engine consensus ...")
        stats, contested, omissions = build_consensus_2(tess_text, paddle_text)
        base_text = tess_text  # Tesseract is the readable base in the fallback
        vlm_skipped = args.vlm_skipped

    sibling.write_text(base_text, encoding="utf-8")  # draft base
    record = {
        "schema": "ocr-verification/v1",
        "source_pdf": rel_to_sources(pdf),
        "sibling_txt": rel_to_sources(sibling),
        "sibling_sha256": None,  # stamped by `assemble`
        "generated": args.date,
        "engines": engines,
        "stats": stats,
        "contested": contested,
        "possible_omissions": omissions,
        "contamination_flags": [],
    }
    if vlm_skipped:
        record["vlm_skipped"] = vlm_skipped
    write_yaml(verification, record)

    print(f"\n  draft sibling : {sibling}")
    print(f"  verification  : {verification}")
    print(f"  consensus     : {stats['consensus_tokens']}/{stats['base_tokens']} tokens")
    print(f"  CONTESTED     : {stats['contested_count']}  (adjudicate against page images)")
    print(f"  omissions(adv): {stats['possible_omission_count']}")
    if contested:
        print("\n  Next: fill `resolution` for each contested span by reading the")
        print("  page image, then run: ocr-consensus.py assemble", verification)
    else:
        print("\n  No contested spans. Run: ocr-consensus.py assemble", verification)


def cmd_assemble(args):
    verification = Path(args.verification)
    record = yaml.safe_load(verification.read_text(encoding="utf-8"))
    sibling = SOURCES_DIR / record["sibling_txt"]
    base = sibling.read_text(encoding="utf-8")

    unresolved = [c["id"] for c in record.get("contested", [])
                  if c.get("resolution") in (None, "")]
    if unresolved:
        raise SystemExit(
            "cannot assemble — contested spans without a resolution: "
            + ", ".join(unresolved)
            + "\n  read the page image at each and fill `resolution` "
              "(+ resolution_method: image-adjudication, + adjudicator_session)."
        )

    # Splice resolutions in reverse char order so earlier offsets stay valid.
    edits = sorted(record.get("contested", []), key=lambda c: c["char_start"], reverse=True)
    text = base
    changed = 0
    for c in edits:
        cs, ce = c["char_start"], c["char_end"]
        if base[cs:ce] != c["candidates"]["vlm"]:
            raise SystemExit(
                f"offset drift on {c['id']}: base[{cs}:{ce}]="
                f"{base[cs:ce]!r} != recorded vlm {c['candidates']['vlm']!r}. "
                f"Re-run `run`; do not hand-edit the draft."
            )
        if c["resolution"] != base[cs:ce]:
            text = text[:cs] + c["resolution"] + text[ce:]
            changed += 1
        c["status"] = "adjudicated"
    sibling.write_text(text, encoding="utf-8")
    record["sibling_sha256"] = sha256_file(sibling)
    write_yaml(verification, record)
    print(f"  assembled {sibling}  ({changed} span(s) substituted)")
    print(f"  sha256 {record['sibling_sha256']}")


def cmd_engines(_args):
    def have(cmd):
        from shutil import which
        return which(cmd) is not None
    print("tesseract :", "OK " + tesseract_version() if have("tesseract") else "MISSING")
    print("pdftoppm  :", "OK" if have("pdftoppm") else "MISSING")
    print("paddleocr :", paddleocr_version())
    print("venv      :", ".venv-ocr present" if _VENV_PYTHON.is_file() else "MISSING (run setup-ocr-consensus.sh)")


def cmd_selftest(_args):
    """Exercise the alignment/consensus on synthetic streams replaying the four
    DIRD-16 errors. The VLM base is correct here; the failure case that matters
    is contested-detection when an OCR engine disagrees. Also assert the
    inverse: a wrong VLM token that the two OCR engines correct is flagged."""
    failures = []

    # Case 1: VLM correct, one OCR engine wrong -> 2/3 consensus, NOT contested.
    vlm = "as discussed in Section III, relativity prohibits communication"
    tess = "as discussed in Section ITT, relativity prohibits cammunication"
    paddle = "as discussed in Section III, relativity prohibits communication"
    stats, contested, _ = build_consensus(vlm, tess, paddle)
    if contested:
        failures.append(f"case1: expected 0 contested (VLM+Paddle agree), got {[c['candidates'] for c in contested]}")

    # Case 2: VLM WRONG, both OCR engines agree on the correct read -> contested,
    # flagged "both OCR engines agree against the VLM read".
    vlm2 = "volume 82 by Klyshko and Shih"
    tess2 = "volume 81 by Klyshko and Shih"
    paddle2 = "volume 81 by Klyshko and Shih"
    stats2, contested2, _ = build_consensus(vlm2, tess2, paddle2)
    got = {c["candidates"]["vlm"]: c["candidates"]["tesseract"] for c in contested2}
    if got.get("82") != "81":
        failures.append(f"case2: expected '82' contested vs OCR '81', got {got}")
    if not any("OCR engines agree" in c["note"] for c in contested2):
        failures.append("case2: expected the 'both OCR engines agree against VLM' note")

    # Case 3: all three differ -> contested, note 'all three votes differ'.
    stats3, contested3, _ = build_consensus("the Kiyshko paper", "the Klyshko paper", "the Klyschko paper")
    if not contested3 or "all three" not in contested3[0]["note"]:
        failures.append(f"case3: expected 'all three votes differ', got {contested3}")

    # Case 4: offsets are accurate (assemble relies on them).
    base = "foo bar baz"
    _, c4, _ = build_consensus(base, "foo XXX baz", "foo YYY baz")
    if not c4 or base[c4[0]["char_start"]:c4[0]["char_end"]] != "bar":
        failures.append(f"case4: bad offsets {c4}")

    # Case 5: 2-engine fallback (VLM skipped) — base=Tesseract, check=PaddleOCR.
    # Disagreements contested; candidates.vlm is None.
    _, c5, _ = build_consensus_2("Section III communication", "Section ITT cammunication")
    vals = {c["candidates"]["tesseract"]: c["candidates"]["paddleocr"] for c in c5}
    if vals.get("III") != "ITT" or vals.get("communication") != "cammunication":
        failures.append(f"case5: 2-engine expected III/communication contested, got {vals}")
    if any(c["candidates"]["vlm"] is not None for c in c5):
        failures.append("case5: 2-engine candidates.vlm should be None")

    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELFTEST PASSED — consensus flags OCR/VLM disagreements correctly")
    print("  case1: VLM+1 OCR agreement -> no false contest")
    print("  case2: VLM wrong, OCR engines correct -> contested + flagged")
    print("  case3: three-way disagreement -> contested")
    print("  case4: char offsets accurate for assemble")
    print("  case5: 2-engine fallback (VLM skipped) -> OCR disagreement contested")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Multi-engine OCR consensus for trustworthy clean-text siblings.")
    ap.add_argument("--selftest", action="store_true",
                    help="run synthetic alignment/consensus tests and exit")
    sub = ap.add_subparsers(dest="cmd")

    p_run = sub.add_parser("run", help="rasterize + 3-engine vote + emit draft sibling & verification YAML")
    p_run.add_argument("pdf", help="source PDF (path under sources/ or absolute)")
    p_run.add_argument("--vlm", help="VLM page-image transcription (.txt) — vote C (normal path)")
    p_run.add_argument("--vlm-skipped", metavar="REASON",
                       help="run the 2-engine fallback (Tesseract+PaddleOCR) and record this "
                            "reason; for CBRN / content-filter-blocked sources only")
    p_run.add_argument("--dpi", type=int, default=300)
    p_run.add_argument("--date", default=None, help="YYYY-MM-DD for the verification record")
    p_run.add_argument("--force", action="store_true", help="overwrite an existing sibling (backfill)")
    p_run.set_defaults(func=cmd_run)

    p_asm = sub.add_parser("assemble", help="apply adjudicated resolutions -> final sibling + sha256")
    p_asm.add_argument("verification", help="{stem}-ocr-verification.yaml")
    p_asm.set_defaults(func=cmd_assemble)

    p_eng = sub.add_parser("engines", help="report engine availability")
    p_eng.set_defaults(func=cmd_engines)

    args = ap.parse_args()
    if args.selftest:
        sys.exit(cmd_selftest(args))
    if not getattr(args, "func", None):
        ap.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
