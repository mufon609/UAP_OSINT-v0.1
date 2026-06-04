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

A token is accepted (CONSENSUS) only when **≥2 of the 3 votes agree**. Because the
three engines have uncorrelated failure modes, the lone wrong read in each DIRD-16
case loses the vote and is flagged rather than silently kept. See
meta/conventions.md "Producing the `.txt` sibling".

`run` PRODUCES the sibling (the VLM base is its readable spine). VERIFICATION is
now **quote-scoped** (`ground`, below) — the whole-document gate
(validate-ocr-sibling.py) and its record (`{stem}-ocr-verification.yaml`) were
retired (BACKLOG C1): whole-document token consensus drowns the signal in
non-prose furniture, so the gate confirms only the spans a node quotes/cites.

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
  ground     Quote-scoped grounding (the verification model that supersedes
             whole-document consensus for the gate — BACKLOG C1): for a research
             artifact, OCR each cited OCR-scan source, align to its `.txt`
             sibling, and confirm ONLY the spans the node quotes/cites
             (furniture is never quoted -> never adjudicated). Emits
             {stem}-quote-grounding.yaml; gated by quote_source_grounding.py.
  engines    Report which engines are available (diagnostic).
  --selftest Run the alignment/consensus logic on synthetic inputs (no OCR
             engines needed) — exercised by scripts/tests/.

The `run`/`assemble` whole-document path still produces the VLM-base sibling; the
gate now grounds per quoted/cited span (`ground`) rather than requiring the whole
sibling to be consensus-clean.

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


# A contiguous run of OCR-corroborated tokens absent from the VLM base, anchored
# at a single spine point this large, signals a whole paragraph/page the VLM
# transcription dropped. possible_omissions is advisory and never splices into
# the sibling, so without this the dropped region ships silently — and the
# quote-scoped grounding gate confirms only quoted spans, never whole-sibling
# completeness. This promotes the largest such run to a visible coverage_warning
# at production time (a quote drawn from a dropped region would fail to locate in
# `ground`, but the warning surfaces the gap earlier).
MAX_OMISSION_RUN = 40


def coverage_warning_from_omissions(omissions):
    """Return a coverage-warning dict if OCR-corroborated tokens absent from the
    VLM base cluster into a large contiguous run at one spine point (a likely
    dropped paragraph/page), else None. A dropped page becomes one difflib
    insertion block, so all its tokens share a single ``before_token_index`` —
    grouping by that anchor and taking the largest group surfaces it."""
    if not omissions:
        return None
    by_anchor = {}
    for o in omissions:
        by_anchor.setdefault(o["before_token_index"], []).append(o)
    anchor, run = max(by_anchor.items(), key=lambda kv: len(kv[1]))
    if len(run) < MAX_OMISSION_RUN:
        return None
    return {
        "before_token_index": anchor,
        "line": run[0]["line"],
        "omitted_token_count": len(run),
        "total_omitted_tokens": len(omissions),
        "note": (
            f"{len(run)} OCR-corroborated tokens absent from the VLM base "
            f"cluster at one point (line {run[0]['line']}) — the VLM "
            f"transcription likely dropped a paragraph or page here. The "
            f"sibling base must cover the whole document; confirm coverage "
            f"before `assemble`."
        ),
    }


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
    """PaddleOCR over each page image. Tolerates both the 3.x ``predict()`` API
    (result objects with a ``rec_texts`` list) and the 2.x ``ocr()`` API (list
    of ``[box, (text, conf)]``). oneDNN is disabled: paddlepaddle's CPU PIR
    executor crashes in the oneDNN path on current builds
    (``ConvertPirAttribute2RuntimeAttribute ... onednn``); the workaround is
    ``FLAGS_use_mkldnn=0`` + ``enable_mkldnn=False``."""
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    try:
        from paddleocr import PaddleOCR  # noqa: PLC0415
    except Exception as e:  # noqa: BLE001
        raise SystemExit(
            "PaddleOCR not importable — run scripts/tools/setup-ocr-consensus.sh "
            f"to create .venv-ocr/ (this tool auto-relaunches under it). [{e}]"
        )
    # Construct across API generations. 3.x default uses the heavy server
    # detection model, which tried to alloc ~43 GB on a 300-dpi page — force the
    # MOBILE det+rec models, cap the detection input side, and disable the extra
    # doc-orientation / unwarping / textline-orientation preprocessors (memory +
    # time). Disable oneDNN every way that's accepted (CPU PIR crash workaround).
    for kwargs in ({"lang": "en", "enable_mkldnn": False,
                    "text_detection_model_name": "PP-OCRv5_mobile_det",
                    "text_recognition_model_name": "en_PP-OCRv5_mobile_rec",
                    "use_doc_orientation_classify": False,
                    "use_doc_unwarping": False,
                    "use_textline_orientation": False,
                    "text_det_limit_side_len": 1280,
                    "text_det_limit_type": "max"},
                   {"lang": "en", "enable_mkldnn": False},
                   {"use_angle_cls": False, "lang": "en", "show_log": False},
                   {"lang": "en"}):
        try:
            ocr = PaddleOCR(**kwargs)
            break
        except TypeError:
            continue
    else:
        ocr = PaddleOCR()

    use_predict = hasattr(ocr, "predict")
    pages = []
    for img in images:
        lines = []
        if use_predict:
            try:
                res = ocr.predict(str(img))
            except TypeError:
                res = ocr.predict(input=str(img))
            for r in res or []:
                try:
                    texts = r["rec_texts"]
                except (KeyError, TypeError):
                    texts = getattr(r, "rec_texts", None)
                if texts:
                    lines.extend(texts)
        else:
            res = ocr.ocr(str(img), cls=False)
            if res and res[0]:
                for entry in res[0]:
                    try:  # 2.x: entry == [box, (text, conf)]
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
    coverage_warning = None
    if vlm_text is not None:
        print("[4/4] Aligning 3 votes + computing consensus ...")
        stats, contested, omissions = build_consensus(vlm_text, tess_text, paddle_text)
        base_text = vlm_text
        engines.append({"name": "vlm", "note": f"agent page-image read; file: {args.vlm}"})
        vlm_skipped = None
        coverage_warning = coverage_warning_from_omissions(omissions)
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
    if coverage_warning:
        record["coverage_warning"] = coverage_warning
    write_yaml(verification, record)

    print(f"\n  draft sibling : {sibling}")
    print(f"  verification  : {verification}")
    print(f"  consensus     : {stats['consensus_tokens']}/{stats['base_tokens']} tokens")
    print(f"  CONTESTED     : {stats['contested_count']}  (adjudicate against page images)")
    print(f"  omissions(adv): {stats['possible_omission_count']}")
    if coverage_warning:
        print(f"\n  ⚠ COVERAGE WARNING: {coverage_warning['omitted_token_count']} "
              f"OCR-corroborated tokens absent from the VLM base cluster at "
              f"line {coverage_warning['line']} — the base likely dropped a "
              f"paragraph/page. Confirm whole-document coverage before assemble.")
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


# ---------------------------------------------------------------------------
# Quote-scoped grounding — the quote-scoped verification model (BACKLOG C1).
#
# Whole-document consensus drowns the signal in furniture noise. The fidelity
# guarantee that matters is per-LOAD-BEARING-SPAN: confirm only the spans a node
# quotes or cites. The `.txt` sibling is the authoritative grab (the spine);
# Tesseract + PaddleOCR cross-check it; a quoted/cited span is grounded when
# every token agrees with >=1 OCR engine or is image-adjudicated. Furniture is
# never quoted -> never confirmed. Record: {stem}-quote-grounding.yaml
# (meta/schema-quote-grounding.yaml). Gate: scripts/checks/quote_source_grounding.py.
# ---------------------------------------------------------------------------
_OCR_TYPES = {"ocr-scan", "extraction-lossy"}

# Sibling-encoding markers that are NEVER source-literal text: a superscript
# endnote/citation marker (`^N`) and citation/redaction brackets. No OCR engine
# emits them, so they always land in `contested` — but they are sanctioned by
# the preserved-marker convention, not load-bearing prose. `ground` auto-resolves
# only these (method `markup-convention`, flagged NOT image-read). The set is
# deliberately conservative: defect-prone glyphs a sibling can wrongly inject
# (a stray middot, ordinary punctuation an OCR engine may have read correctly)
# are EXCLUDED, so they still surface for human image-adjudication — which is how
# the dird-01 inserted-middot defect was caught.
SANCTIONED_MARKUP = {"^", "[", "]"}


def _norm_for_locate(s):
    return (s.replace("“", '"').replace("”", '"')
             .replace("‘", "'").replace("’", "'")
             .replace("—", "-").replace("–", "-"))


def _collapsed_index_map(text):
    """Whitespace-collapsed, quote/dash-normalized view of `text` plus a map from
    each collapsed-char index back to the original char offset — so a span
    located in the normalized view is reported in original sibling coordinates
    (the coordinate system the contested spans use). Whitespace after a hyphen is
    dropped (a PDF line-wrap `quant-\\nph` joins to `quant-ph`), mirroring
    lib._common.normalize_for_compare's ``-\\s+`` -> ``-`` so a reflowed citation
    still locates."""
    t = _norm_for_locate(text)
    out, idxmap, prev_ws = [], [], False
    for i, ch in enumerate(t):
        if ch.isspace():
            if out and out[-1] == "-":
                continue  # hyphen line-wrap: join, drop the whitespace
            if not prev_ws:
                out.append(" "); idxmap.append(i); prev_ws = True
        else:
            out.append(ch); idxmap.append(i); prev_ws = False
    return "".join(out), idxmap


def _collapse_query(quote):
    """Normalize a quote/citation the same way as _collapsed_index_map (quote/
    dash fold, hyphen line-wrap join, whitespace collapse) so it matches."""
    q = re.sub(r"-\s+", "-", _norm_for_locate(quote))
    return re.sub(r"\s+", " ", q).strip()


def locate_span(collapsed, idxmap, quote):
    """Return (char_start, char_end) of `quote` in the original text, or None.
    Exact normalized-substring first; head+tail fuzzy fallback for a quote that
    crosses page furniture (a running banner spliced mid-paragraph)."""
    q = _collapse_query(quote)
    if not q:
        return None
    j = collapsed.find(q)
    if j >= 0:
        return idxmap[j], idxmap[j + len(q) - 1] + 1
    head, tail = q[:25], q[-25:]
    a = collapsed.find(head)
    if a < 0:
        return None
    b = collapsed.find(tail, a)
    if b < 0:
        return None
    return idxmap[a], idxmap[b + len(tail) - 1] + 1


def collect_ocr_spans(data, ext_types):
    """Map OCR-scan source path -> [(ref_id, kind, verbatim_text)] for every
    quote and cited_work that cites it."""
    spans = {}
    for q in (data.get("quotes") or []):
        if not isinstance(q, dict):
            continue
        rel = (q.get("source") or {}).get("path")
        txt = q.get("text") or q.get("verbatim")
        if rel and txt and ext_types.get(rel) in _OCR_TYPES:
            spans.setdefault(rel, []).append((q.get("id"), "quote", txt))
    for cw in (data.get("cited_works") or []):
        if not isinstance(cw, dict):
            continue
        rel = (cw.get("source") or {}).get("path")
        txt = cw.get("citation_verbatim")
        if rel and txt and ext_types.get(rel) in _OCR_TYPES:
            spans.setdefault(rel, []).append((cw.get("id"), "cited_work", txt))
    return spans


def _partition_prior_spans(old, node_slug):
    """From an existing grounding record `old`, split its grounded_spans for a
    re-ground of `node_slug`:

      - ``other_spans`` — spans belonging to a DIFFERENT node; preserved verbatim
        so a record that aggregates several citing nodes isn't clobbered when one
        node is re-grounded (the shared-source merge).
      - ``prior`` — ``{(ref, char_start): (resolution, method, session)}`` for THIS
        node's spans (and for untagged legacy v1 spans, which were single-node by
        construction), so image-adjudications carry across the re-ground.

    Other nodes' adjudications stay intact because their whole span entries are
    preserved in ``other_spans`` — they are never rebuilt, so never re-keyed.
    """
    prior, other = {}, []
    for gs in (old.get("grounded_spans") or []):
        g_node = gs.get("node")
        if g_node is not None and g_node != node_slug:
            other.append(gs)
            continue
        for c in (gs.get("contested") or []):
            prior[(gs.get("ref"), c.get("char_start"))] = (
                c.get("resolution"), c.get("resolution_method"),
                c.get("adjudicator_session"))
    return prior, other


def cmd_ground(args):
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))
    from lib._common import _load_extraction_types  # noqa: PLC0415

    artifact = Path(args.artifact)
    node_slug = artifact.stem  # spans are namespaced by node so two nodes' ids don't collide
    data = yaml.safe_load(artifact.read_text(encoding="utf-8"))
    spans_by_source = collect_ocr_spans(data, _load_extraction_types())
    if not spans_by_source:
        print("no quotes/cited_works cite an OCR-scan source — nothing to ground.")
        return

    skipped = []
    for rel, spans in spans_by_source.items():
        pdf = SOURCES_DIR / rel
        sibling = pdf.with_suffix(".txt")
        stem = pdf.with_suffix("").name
        record_path = pdf.parent / f"{stem}-quote-grounding.yaml"
        # Skip-and-warn rather than abort: a node often cites several OCR-scan
        # sources, and one missing PDF/sibling must not block grounding the
        # rest. A skipped source's spans stay ungrounded — the gate flags them.
        if not pdf.exists():
            print(f"   ! SKIP {rel}: source PDF not found — "
                  f"{len(spans)} span(s) ungrounded")
            skipped.append((rel, "source PDF not found"))
            continue
        if not sibling.exists():
            print(f"   ! SKIP {rel}: no .txt sibling (produce it first: "
                  f"ocr-consensus.py run --vlm ...) — {len(spans)} span(s) ungrounded")
            skipped.append((rel, "no .txt sibling"))
            continue
        sib_text = sibling.read_text(encoding="utf-8")

        print(f"[{rel}] {len(spans)} span(s) — rasterize + OCR cross-check ...")
        with tempfile.TemporaryDirectory(prefix=f"ground-{stem}-") as tmp:
            images = rasterize(pdf, tmp, args.dpi)
            tess = run_tesseract(images)
            paddle = run_paddleocr(images)
        # The sibling is the authoritative grab (spine); the 2 OCR engines
        # cross-check. contested = sibling tokens corroborated by neither engine.
        _, contested, _ = build_consensus(sib_text, tess, paddle)

        # Merge semantics: one record aggregates every node that cites this
        # source. Re-grounding a node replaces only THAT node's spans and
        # preserves the others (spans are namespaced by `node` so two nodes'
        # identically-numbered ids — both "q4" — never collide). Carry prior
        # adjudications for THIS node by (ref, char_start); a span with no
        # `node` (legacy v1 record, single-node by construction) is treated as
        # this node's prior, not another node's, so v1 -> v2 migrates in place.
        prior, other_spans = {}, []
        if record_path.exists():
            old = yaml.safe_load(record_path.read_text(encoding="utf-8")) or {}
            prior, other_spans = _partition_prior_spans(old, node_slug)

        collapsed, idxmap = _collapsed_index_map(sib_text)
        sib_tokens = tokenize(sib_text)
        grounded, total_contested, unlocated, auto_markup = [], 0, 0, 0
        for ref, kind, txt in spans:
            loc = locate_span(collapsed, idxmap, txt)
            if loc is None:
                unlocated += 1
                grounded.append({"node": node_slug, "ref": ref, "kind": kind,
                                 "located": False,
                                 "note": "verbatim text not found in sibling — "
                                         "re-check the quote/citation"})
                print(f"   ! {ref}: NOT located in sibling")
                continue
            qs, qe = loc
            n_tokens = sum(1 for (_s, cs, _ce) in sib_tokens if qs <= cs < qe)
            cin = []
            for c in contested:
                # start-in-span — the same membership test as n_tokens, so
                # confirmed = n_tokens - len(cin) is exact and never negative
                # (quotes begin at a token boundary, so no token straddles qs).
                if qs <= c["char_start"] < qe:
                    sib_tok = c["candidates"]["vlm"]
                    res, meth, sess = prior.get((ref, c["char_start"]), (None, None, None))
                    if res is None and sib_tok in SANCTIONED_MARKUP:
                        # Sanctioned sibling-encoding marker — auto-confirm by
                        # convention, flagged NOT image-read (see SANCTIONED_MARKUP).
                        res, meth = sib_tok, "markup-convention"
                        sess = (f"auto: sanctioned markup token {sib_tok!r} "
                                f"(superscript/bracket marker, not source-literal text)")
                        auto_markup += 1
                    cin.append({
                        "token_index": c["token_index"],
                        "char_start": c["char_start"],
                        "char_end": c["char_end"],
                        "line": c["line"],
                        "context": c["context"],
                        "sibling": c["candidates"]["vlm"],
                        "tesseract": c["candidates"]["tesseract"],
                        "paddleocr": c["candidates"]["paddleocr"],
                        "resolution": res,
                        "resolution_method": meth,
                        "adjudicator_session": sess,
                    })
            total_contested += len(cin)
            grounded.append({
                "node": node_slug, "ref": ref, "kind": kind, "located": True,
                "char_start": qs, "char_end": qe,
                "tokens": n_tokens, "confirmed": n_tokens - len(cin),
                "contested": cin,
            })
            print(f"   - {ref} ({kind}): {n_tokens} tokens, "
                  f"{'OK' if not cin else str(len(cin)) + ' contested'}")

        record = {
            "schema": "quote-grounding/v2",
            "source_pdf": rel,
            "sibling_txt": str(sibling.relative_to(SOURCES_DIR)),
            "sibling_sha256": sha256_file(sibling),
            "generated": args.date,
            "confirming_engines": [
                {"name": "tesseract", "version": tesseract_version()},
                {"name": "paddleocr", "version": paddleocr_version()},
            ],
            "grounded_spans": other_spans + grounded,
        }
        write_yaml(record_path, record)
        human = total_contested - auto_markup
        print(f"   -> {record_path}")
        msg = (f"      {len(spans) - unlocated}/{len(spans)} span(s) located; "
               f"{total_contested} contested ({auto_markup} auto-resolved as "
               f"sanctioned markup, {human} to image-adjudicate)")
        if human:
            msg += (" — read the page image at each unresolved token, fill "
                    "`resolution` (= what the image shows) + resolution_method: "
                    "image-adjudication + adjudicator_session.")
        print(msg)

    if skipped:
        print(f"\nSKIPPED {len(skipped)} source(s) — their spans remain ungrounded "
              f"(produce the sibling, then re-run `ground`):")
        for rel, why in skipped:
            print(f"  - {rel}: {why}")


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

    p_grd = sub.add_parser(
        "ground",
        help="quote-scoped grounding: confirm a node's quoted/cited spans of an "
             "OCR-scan source against the OCR engines -> {stem}-quote-grounding.yaml")
    p_grd.add_argument("artifact", help="research artifact (meta/research/{node}.yaml)")
    p_grd.add_argument("--dpi", type=int, default=300)
    p_grd.add_argument("--date", default=None, help="YYYY-MM-DD for the grounding record")
    p_grd.set_defaults(func=cmd_ground)

    args = ap.parse_args()
    if args.selftest:
        sys.exit(cmd_selftest(args))
    if not getattr(args, "func", None):
        ap.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
