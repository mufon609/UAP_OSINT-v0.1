#!/usr/bin/env python3
"""ocr-consensus.py — produce a clean-text ``.txt`` sibling for an OCR-scan PDF,
then confirm it against an uncorrelated tool.

An OCR-scan PDF's pdftotext layer is corrupt, so verbatim quotes are matched
against a clean-text ``.txt`` *sibling* instead. The sibling is produced by a
**VLM page-image read** (an agent reads the page images) — a high-fidelity
modality, but one the content filter blocks on some pages, and one no single
read can be trusted on alone (DIRD-16's first single-pass "PASS" sibling carried
`III→ITT`, `communication→cammunication`, `81→82`, `Klyshko→Kiyshko`).

So the sibling is **confirmed with a different tool**: PaddleOCR (a different
modality — deep-learning OCR; not content-blocked) re-reads the pages and is
diffed against the sibling on the **words and numbers only** (load-bearing
tokens — see ``is_load_bearing``). Document structure (punctuation, bullets,
brackets, banners, figure labels, dot-leaders) is never compared — that furniture
is what drowned the retired whole-document consensus in ~99% noise. Each
load-bearing divergence is printed for an agent to reconcile against the page
image, correcting the sibling where the VLM misread. The corrected sibling is
the artifact; **no receipt YAML is written**. (The final quote-vs-source check
happens later, at node audit: an agent verifies the built node's quotes against
the source page images — not the sibling. See meta/conventions.md "Producing the
`.txt` sibling".)

PaddleOCR is the higher-trust OCR engine; Tesseract is an available second
opinion (a token is corroborated if EITHER engine agrees with the sibling, so a
divergence flags only when both disagree). On a fully content-blocked source the
VLM vote is skipped and the sibling is built from OCR alone (``--vlm-skipped``).

Blocked pages — the VLM verifies what it cannot produce. The content filter
blocks model OUTPUT (reproducing a passage), so the VLM cannot transcribe a
blocked page; PaddleOCR fills it instead. But the VLM CAN still verify that fill
against the page image — judging/pinpointing a wrong token is a tiny output, not
reproduction. On a paddle-filled page the sibling text IS PaddleOCR, so the
normal sibling-vs-engines diff is silent (sibling == paddle); ``--blocked-pages``
instead runs PaddleOCR-vs-Tesseract on those page images and prints where the two
engines disagree (the highest-risk tokens), which the agent then VLM-verifies.

Subcommands:
  run        Write the ``.txt`` sibling from the VLM page-image read, then OCR
             the pages (PaddleOCR + Tesseract) and print every load-bearing
             divergence for the agent to reconcile. Writes only the sibling.
             ``--blocked-pages SPEC`` adds the per-blocked-page PaddleOCR-vs-
             Tesseract check.
  verify     Re-confirm an EXISTING sibling against the OCR engines (no
             regeneration) — the same load-bearing divergence report (and
             ``--blocked-pages`` check). Use when re-checking a sibling produced
             earlier.
  engines    Report which engines are available (diagnostic).
  --selftest Run the alignment/consensus logic on synthetic inputs (no OCR
             engines needed) — exercised by scripts/tests/.

PaddleOCR lives in a project-local venv at .venv-ocr/ (run
scripts/tools/setup-ocr-consensus.sh once). This tool auto-relaunches under that
venv's Python for the `run` / `verify` subcommands; `--help` and `--selftest`
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
import bisect
import difflib
import re
import subprocess
import tempfile

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
    (conservative: over-flagging costs a reconcile, under-flagging hides an
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
    wrapped in guillemets for the reviewer."""
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
# the sibling, so without this the dropped region ships silently. This promotes
# the largest such run to a visible coverage_warning at production time, so a
# dropped paragraph/page is recovered before the sibling is used.
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
            f"sibling must cover the whole document; recover the dropped "
            f"region before using the sibling."
        ),
    }


def build_consensus_2(base_text, other_text):
    """Two-engine diff for the content-blocked fallback, where the VLM vote is
    skipped (the OCR-only sibling). Tesseract is the readable base; PaddleOCR is
    the sole cross-check. A token is corroborated only when both engines agree;
    any disagreement is flagged for the reviewer to reconcile against the page
    image (with no VLM read, a single OCR engine can't clear it on its own)."""
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
# The load-bearing confirmation report — the "confirm with a different tool"
# step. A token is reported only when it carries a letter/digit (or a numeric
# symbol beside a digit) AND no OCR engine corroborates the sibling's reading.
# Structure/furniture is filtered out (is_load_bearing), so the report is the
# short list of words/numbers an agent must reconcile against the page image.
# ---------------------------------------------------------------------------
def confirm_report(sibling_text, tess_text, paddle_text, vlm_skipped=False):
    """Return (divergences, possible_omissions): the load-bearing divergences
    between the sibling and the OCR engines, plus the OCR-corroborated tokens the
    sibling omits (for the coverage warning). When the VLM vote was skipped
    (OCR-only sibling) the cross-check is the two engines against each other
    (build_consensus_2, no omission signal); otherwise the sibling is the spine
    and both OCR engines cross-check it (build_consensus)."""
    if vlm_skipped:
        _, contested, omissions = build_consensus_2(sibling_text, paddle_text)
    else:
        _, contested, omissions = build_consensus(sibling_text, tess_text, paddle_text)
    divergences = [c for c in contested
                   if is_load_bearing(c["candidates"]["vlm"] or c["candidates"]["tesseract"],
                                      sibling_text, c["char_start"], c["char_end"])]
    return divergences, omissions


def _page_of_offset(page_starts, off):
    """1-indexed page number for a base-text char offset, given the sorted list of
    per-page start offsets (page_starts[k] = char offset where page k+1 begins).
    Returns None when page boundaries are unknown (no --vlm-pages)."""
    if not page_starts:
        return None
    return bisect.bisect_right(page_starts, off)


def _is_high_signal(c):
    """A divergence the reviewer MUST settle against the page image: both OCR
    engines independently read the same token and it differs from the sibling
    (``build_consensus`` note "both OCR engines agree against the VLM read"), OR
    the VLM vote was skipped entirely (OCR-only sibling — every divergence is
    two-engine with no VLM tiebreak). The complement ("all three votes differ")
    is dominated by struck-through banners, bracketed [Figure]/[Equation]
    placeholder text, and per-engine glyph noise — skim, not image-verify."""
    if c["candidates"]["vlm"] is None:      # OCR-only sibling (VLM skipped)
        return True
    return c.get("note", "").startswith("both OCR engines agree")


def _print_divergence_rows(rows, sibling, page_starts):
    for c in rows:
        cand = c["candidates"]
        if cand["vlm"] is None:          # OCR-only sibling (VLM skipped): base == tesseract
            reads = f"sibling={cand['tesseract']!r}  paddleocr={cand['paddleocr']!r}"
        else:
            reads = (f"sibling={cand['vlm']!r}  tesseract={cand['tesseract']!r}  "
                     f"paddleocr={cand['paddleocr']!r}")
        page = _page_of_offset(page_starts, c["char_start"])
        loc = f"p.{page} line {c['line']}" if page else f"line {c['line']}"
        print(f"    {loc}: {reads}")
        print(f"      {c['context']}")


def print_confirm_report(divergences, sibling, page_starts=None):
    """Print the load-bearing divergence report, partitioned so the agent
    image-verifies the right (small) set instead of skimming everything.

    Two groups, by ``build_consensus`` note (see ``_is_high_signal``):
      • HIGH-SIGNAL — both OCR engines agree against the sibling. EACH must be
        settled against the PAGE IMAGE: it is either a VLM misread to fix, or a
        shared OCR glyph-confusion where the sibling is right. The page-image read
        is the ONLY way to tell them apart — surrounding-text plausibility is not,
        because that re-trusts the VLM against itself (the exact failure PaddleOCR
        exists to catch).
      • weak — no single OCR reading corroborated (banners, bracketed figure/
        equation placeholders, per-engine glyph noise). Skim; image-check only
        where one lands on body prose.

    Page numbers are shown when ``page_starts`` is supplied (``run --vlm-pages``)."""
    if not divergences:
        print(f"\n  ✓ CONFIRMED: every load-bearing word/number in {sibling.name} is "
              f"corroborated by an OCR engine. No divergences to reconcile.")
        return
    high = [c for c in divergences if _is_high_signal(c)]
    weak = [c for c in divergences if not _is_high_signal(c)]
    loc_hint = "" if page_starts else (
        "  (no page numbers — sibling produced without `run --vlm-pages`; locate "
        "the line in the sibling to find its page.)")

    print(f"\n  {len(high)} HIGH-SIGNAL divergence(s) — both OCR engines read the same "
          f"token, differing from the sibling. OPEN THE PAGE IMAGE for each and decide "
          f"the true reading there; do NOT infer it from the surrounding sibling text. "
          f"Fix the sibling on a VLM misread; leave it on shared OCR glyph-confusion "
          f"(e.g. µm→um, SiO2→SiOz).{loc_hint}")
    if high:
        _print_divergence_rows(high, sibling, page_starts)
    else:
        print("    (none)")

    print(f"\n  {len(weak)} weak divergence(s) — no single OCR reading corroborated "
          f"(struck-through banners, bracketed [Figure]/[Equation] placeholder text, "
          f"per-engine glyph noise). Skim; open the page image only where one lands on "
          f"body prose.")
    if weak:
        _print_divergence_rows(weak, sibling, page_starts)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------
def parse_pages(spec):
    """Parse a `--blocked-pages` spec ('5-7,10,14-15') into a sorted int list.
    Accepts single pages and inclusive N-M ranges; ignores blanks."""
    if not spec:
        return []
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return sorted(out)


def _paddle_fill_page(pdf, page_num, two_column, dpi):
    """PaddleOCR-fill one content-blocked page and return its text.

    A blocked page is one the VLM content filter refused to *reproduce* (e.g. a
    copyrighted excerpt or a flagged passage); PaddleOCR is a non-generative OCR
    engine and is not content-blocked, so it reads the page image fine. A
    two-column page is cropped into left/right halves and OCR'd in reading order —
    a whole-page PaddleOCR pass interleaves the two columns into scrambled text."""
    with tempfile.TemporaryDirectory(prefix=f"ocrfill-p{page_num}-") as tmp:
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page_num), "-l", str(page_num),
             str(pdf), str(Path(tmp) / "pg")],
            check=True, capture_output=True,
        )
        imgs = sorted(Path(tmp).glob("pg*.png"))
        if not imgs:
            raise SystemExit(f"blocked-page fill: page {page_num} produced no image")
        if two_column:
            from PIL import Image  # noqa: PLC0415
            im = Image.open(imgs[0])
            w, h = im.size
            mid = int(w * 0.5)
            left, right = Path(tmp) / "L.png", Path(tmp) / "R.png"
            im.crop((0, 0, mid, h)).save(left)
            im.crop((mid, 0, w, h)).save(right)
            return run_paddleocr([left]) + "\n" + run_paddleocr([right])
        return run_paddleocr([imgs[0]])


def fill_blocked_pages(pdf, pages_dir, blocked, two_column, dpi):
    """Write a PaddleOCR fill into ``{pages_dir}/pNN.txt`` for every blocked page
    that has no (non-empty) per-page VLM file yet, and return the pages filled.

    This is the step the VLM producer cannot do — the content filter blocks
    *reproducing* a blocked page, so PaddleOCR fills its slice. Performing it here
    (rather than leaving it a manual ``pdftoppm | paddle`` step the contributor
    improvises) is what makes ``--blocked-pages`` safe: a blocked page can never be
    silently absent from the assembled sibling. A page already produced by the VLM
    (non-empty ``pNN.txt``) is left untouched."""
    pages_dir = Path(pages_dir)
    filled = []
    for n in blocked:
        target = pages_dir / f"p{n:02d}.txt"
        if target.exists() and target.read_text(encoding="utf-8").strip():
            continue
        target.write_text(_paddle_fill_page(pdf, n, n in two_column, dpi) + "\n",
                          encoding="utf-8")
        filled.append(n)
    return filled


def _ocr_pages(pdf, stem, dpi, blocked_pages=()):
    """Rasterize the PDF and run both OCR engines on the whole document.

    Returns ``(tess_text, paddle_text, blocked_report)``. ``blocked_report`` is
    ``[(page_number, [divergence, ...]), ...]`` for the content-blocked pages:
    on such a page the sibling text IS the PaddleOCR fill (the VLM couldn't
    produce it), so the only mechanical check is PaddleOCR-vs-Tesseract on that
    one page image. Each divergence is ``{line, context, paddle, tess}`` for a
    load-bearing token the two engines read differently (PaddleOCR is the fill /
    sibling spine; Tesseract cross-checks)."""
    blocked_report = []
    with tempfile.TemporaryDirectory(prefix=f"ocr-{stem}-") as tmp:
        images = rasterize(pdf, tmp, dpi)
        print(f"      {len(images)} page image(s)")
        print("      Tesseract (second opinion) ...")
        tess_text = run_tesseract(images)
        print("      PaddleOCR (primary cross-check) ...")
        paddle_text = run_paddleocr(images)
        for n in blocked_pages:
            if not (1 <= n <= len(images)):
                print(f"      ! blocked page {n} out of range (1..{len(images)}) — skipped")
                continue
            print(f"      blocked page {n}: PaddleOCR fill vs Tesseract ...")
            p_txt = run_paddleocr([images[n - 1]])
            t_txt = run_tesseract([images[n - 1]])
            # PaddleOCR is the fill (the sibling on this page) → it is the spine;
            # build_consensus_2 hardcodes candidates.tesseract=base, .paddleocr=other,
            # so normalize the keys to true engine names here.
            _, contested, _ = build_consensus_2(p_txt, t_txt)
            div = [{"line": c["line"], "context": c["context"],
                    "paddle": c["candidates"]["tesseract"],   # base = PaddleOCR fill
                    "tess": c["candidates"]["paddleocr"]}     # other = Tesseract
                   for c in contested
                   if is_load_bearing(c["candidates"]["tesseract"], p_txt,
                                      c["char_start"], c["char_end"])]
            blocked_report.append((n, div))
    return tess_text, paddle_text, blocked_report


def print_blocked_report(blocked_report):
    """Print the PaddleOCR-vs-Tesseract check for each content-blocked page.
    The sibling on these pages is the PaddleOCR fill, so the agent must VLM-verify
    each against the page image regardless — this surfaces where the two OCR
    engines disagree (the highest-risk tokens to check)."""
    for n, div in blocked_report:
        if not div:
            print(f"\n  blocked page {n}: PaddleOCR fill and Tesseract agree on every "
                  f"load-bearing token — still VLM-verify the page against its image.")
            continue
        print(f"\n  blocked page {n}: {len(div)} PaddleOCR-vs-Tesseract divergence(s) — the "
              f"sibling here IS the PaddleOCR fill; VLM-verify each against the page image "
              f"and correct the sibling where PaddleOCR is wrong:")
        for d in div:
            print(f"    line {d['line']}: paddleocr(fill)={d['paddle']!r}  tesseract={d['tess']!r}")
            print(f"      {d['context']}")


def _resolve_pdf(arg):
    pdf = Path(arg)
    if not pdf.is_absolute() and not pdf.exists():
        pdf = SOURCES_DIR / arg
    if not pdf.exists():
        raise SystemExit(f"PDF not found: {pdf}")
    return pdf


def _concat_pages(pages_dir):
    """Concatenate the per-page VLM scratch files (``pNN.txt``, zero-padded) into
    the sibling base text, tracking each page's start offset.

    This replaces the manual ``cat /tmp/{stem}/p*.txt`` step so the tool knows the
    page boundaries — letting the divergence report tag each token with its page,
    which makes the page-image verification step actually locatable. Each page is
    newline-terminated before joining so pages can't glue together and every page
    begins on a line boundary.

    Returns ``(base_text, page_starts)`` where ``page_starts[k]`` is the char
    offset at which page ``k+1`` begins."""
    files = sorted(Path(pages_dir).glob("p*.txt"))
    if not files:
        raise SystemExit(f"--vlm-pages: no p*.txt files found in {pages_dir}")
    parts, page_starts, off = [], [], 0
    for f in files:
        t = f.read_text(encoding="utf-8")
        if not t.endswith("\n"):
            t += "\n"
        page_starts.append(off)
        parts.append(t)
        off += len(t)
    return "".join(parts), page_starts


def cmd_run(args):
    """Produce the .txt sibling from the VLM page-image read, then confirm it
    against the OCR engines and print the load-bearing divergence report. Writes
    only the sibling — no receipt YAML."""
    pdf = _resolve_pdf(args.pdf)
    stem = pdf.with_suffix("").name
    sibling = pdf.with_suffix(".txt")

    if sibling.exists() and not args.force:
        raise SystemExit(
            f"sibling already exists: {sibling}\n"
            f"  pass --force to regenerate (backfill), or use `verify` to "
            f"re-confirm the existing sibling without regenerating."
        )

    if not args.vlm and not args.vlm_pages and not args.vlm_skipped:
        raise SystemExit(
            "provide --vlm-pages DIR (per-page VLM scratch files — page-aware, "
            "preferred), --vlm PATH (a pre-concatenated VLM file — no page "
            "numbers), or --vlm-skipped REASON (fully content-blocked source → "
            "OCR-only 2-engine sibling)."
        )

    blocked = parse_pages(args.blocked_pages)
    two_column = set(parse_pages(getattr(args, "two_column_pages", None)))

    # Fill any content-blocked page the VLM couldn't reproduce BEFORE assembling
    # the sibling, so a blocked page is never silently missing (the footgun this
    # closes). Only --vlm-pages mode has a per-page dir to fill into; a --vlm
    # pre-concatenated base must already include its blocked pages.
    if args.vlm_pages and blocked:
        filled = fill_blocked_pages(pdf, args.vlm_pages, blocked, two_column, args.dpi)
        if filled:
            tc = sorted(two_column & set(filled))
            print(f"      PaddleOCR-filled blocked page(s): {','.join(map(str, filled))}"
                  + (f"  (two-column, column-split: {','.join(map(str, tc))})" if tc else ""))

    print(f"[1/2] Rasterizing {pdf.name} at {args.dpi} dpi + OCR ...")
    tess_text, paddle_text, blocked_report = _ocr_pages(pdf, stem, args.dpi, blocked)

    print("[2/2] Writing the sibling + confirming load-bearing words/numbers ...")
    page_starts = None
    if args.vlm_pages:
        base_text, page_starts = _concat_pages(args.vlm_pages)
        vlm_skipped = False
        # Footgun guard: every declared blocked page must now carry content, so the
        # sibling cannot ship with a silent gap where the VLM was blocked.
        gap = [n for n in blocked
               if not (Path(args.vlm_pages) / f"p{n:02d}.txt").exists()
               or not (Path(args.vlm_pages) / f"p{n:02d}.txt").read_text(encoding="utf-8").strip()]
        if gap:
            raise SystemExit(
                f"blocked page(s) {gap} still have no content after fill — the sibling "
                f"would ship with a gap. (Blocked-page fill needs --vlm-pages mode.)")
    elif args.vlm:
        base_text = Path(args.vlm).read_text(encoding="utf-8")
        vlm_skipped = False
    else:
        base_text = tess_text   # OCR-only fallback: Tesseract is the readable base
        vlm_skipped = True

    sibling.write_text(base_text, encoding="utf-8")
    print(f"\n  sibling : {sibling}")

    divergences, omissions = confirm_report(base_text, tess_text, paddle_text, vlm_skipped)
    coverage_warning = coverage_warning_from_omissions(omissions)
    if coverage_warning:
        print(f"\n  ⚠ COVERAGE WARNING: {coverage_warning['omitted_token_count']} "
              f"OCR-corroborated tokens absent from the VLM base cluster at "
              f"line {coverage_warning['line']} — the base likely dropped a "
              f"paragraph/page. Recover the dropped region before using the sibling.")

    print_confirm_report(divergences, sibling, page_starts)
    print_blocked_report(blocked_report)


def cmd_verify(args):
    """Re-confirm an EXISTING sibling against the OCR engines (no regeneration):
    the same load-bearing divergence report `run` prints. Use when re-checking a
    sibling that was produced earlier."""
    pdf = _resolve_pdf(args.pdf)
    stem = pdf.with_suffix("").name
    sibling = pdf.with_suffix(".txt")
    if not sibling.exists():
        raise SystemExit(
            f"no sibling to verify: {sibling}\n"
            f"  produce it first: ocr-consensus.py run {args.pdf} --vlm ...")

    blocked = parse_pages(args.blocked_pages)
    print(f"Rasterizing {pdf.name} at {args.dpi} dpi + OCR (re-confirm) ...")
    tess_text, paddle_text, blocked_report = _ocr_pages(pdf, stem, args.dpi, blocked)
    sib_text = sibling.read_text(encoding="utf-8")
    divergences, _ = confirm_report(sib_text, tess_text, paddle_text, vlm_skipped=False)
    print_confirm_report(divergences, sibling)
    print_blocked_report(blocked_report)


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

    # Case 4: char offsets are accurate (the divergence report locates by them).
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

    # Case 8: load-bearing filter — words/numbers are confirmed; structure is not.
    lb = lambda s: is_load_bearing(s, s, 0, len(s))
    for tok in ("Section", "82", "AAWSA"):
        if not lb(tok):
            failures.append(f"case8: {tok!r} should be load-bearing")
    for tok in ("•", "[", "]", "*", ",", ";"):
        if lb(tok):
            failures.append(f"case8: {tok!r} (structure) should NOT be load-bearing")
    # decimal point counts only between digits; a sentence period does not.
    if not is_load_bearing(".", "3.5", 1, 2):
        failures.append("case8: decimal '.' in '3.5' should be load-bearing")
    if is_load_bearing(".", "end. Next", 3, 4):
        failures.append("case8: sentence '.' should NOT be load-bearing")

    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELFTEST PASSED — consensus flags OCR/VLM disagreements correctly")
    print("  case1: VLM+1 OCR agreement -> no false contest")
    print("  case2: VLM wrong, OCR engines correct -> contested + flagged")
    print("  case3: three-way disagreement -> contested")
    print("  case4: char offsets accurate")
    print("  case5: 2-engine fallback (VLM skipped) -> OCR disagreement contested")
    print("  case8: load-bearing filter -> words/numbers confirmed, structure not")
    return 0


# ---------------------------------------------------------------------------
# Load-bearing filter — what the confirmation report compares.
#
# A token is load-bearing iff it carries a letter or digit, or it is one of the
# numeric symbols (. - % $ °) sitting immediately beside a digit (a decimal
# point, sign, range dash, percent/currency/degree unit). Everything else —
# bare punctuation, bullets, brackets, markup `*`, banners, figure labels, TOC
# dot-leaders — is document STRUCTURE, never source-literal prose, and is not
# compared. This is what keeps a whole-sibling diff from drowning in furniture
# noise (~99% of a banner/figure-heavy government PDF) while still catching every
# real defect (III→ITT, 81→82, Klyshko→Kiyshko, He³→He?).
_LB_ALNUM = re.compile(r"[A-Za-z0-9]")
_LB_NUM_SYMBOLS = {".", "-", "%", "$", "°"}


def is_load_bearing(surface, text, cs, ce):
    """True iff `surface` (the sibling token at text[cs:ce]) is a word/number we
    must confirm. Numeric symbols count only when adjacent to a digit, so a
    sentence comma or a list hyphen stays structure but a `3.5` / `-40°` / `5%`
    keeps its decimal/sign/unit."""
    if not surface:
        return False
    if _LB_ALNUM.search(surface):
        return True
    if surface in _LB_NUM_SYMBOLS:
        before = text[cs - 1] if cs > 0 else ""
        after = text[ce] if ce < len(text) else ""
        return before.isdigit() or after.isdigit()
    return False


def main():
    ap = argparse.ArgumentParser(
        description="Produce a clean-text .txt sibling for an OCR-scan PDF (VLM "
                    "page-image read) and confirm it against PaddleOCR + Tesseract.")
    ap.add_argument("--selftest", action="store_true",
                    help="run synthetic alignment/consensus tests and exit")
    sub = ap.add_subparsers(dest="cmd")

    p_run = sub.add_parser(
        "run", help="write the .txt sibling from the VLM read, then print the "
                    "load-bearing divergence report against the OCR engines")
    p_run.add_argument("pdf", help="source PDF (path under sources/ or absolute)")
    p_run.add_argument("--vlm-pages", metavar="DIR",
                       help="directory of per-page VLM scratch files (pNN.txt, zero-padded) — "
                            "PREFERRED: the tool concatenates them itself and tags each "
                            "divergence with its page number (p.N) so the page-image "
                            "verification step is locatable")
    p_run.add_argument("--vlm", help="pre-concatenated VLM transcription (.txt) — the sibling "
                                     "base; no page numbers in the report (use --vlm-pages for those)")
    p_run.add_argument("--vlm-skipped", metavar="REASON",
                       help="build an OCR-only sibling (Tesseract base, PaddleOCR cross-check) "
                            "and record this reason; for fully content-blocked sources only")
    p_run.add_argument("--dpi", type=int, default=300)
    p_run.add_argument("--force", action="store_true", help="overwrite an existing sibling (backfill)")
    p_run.add_argument("--blocked-pages", metavar="SPEC", default=None,
                       help="pages the VLM content filter blocked; the tool PaddleOCR-FILLS "
                            "each into the --vlm-pages dir (so it is never silently dropped), "
                            "then prints the PaddleOCR-vs-Tesseract check (e.g. '5-7,10,14-15'). "
                            "Mark any two-column ones with --two-column-pages.")
    p_run.add_argument("--two-column-pages", metavar="SPEC", default=None,
                       help="subset of --blocked-pages that are two-column; each is "
                            "column-split (left half then right) before the PaddleOCR fill so "
                            "the two columns don't interleave into scrambled text (e.g. '30')")
    p_run.set_defaults(func=cmd_run)

    p_vfy = sub.add_parser(
        "verify", help="re-confirm an EXISTING sibling against the OCR engines "
                       "(no regeneration) — same load-bearing divergence report")
    p_vfy.add_argument("pdf", help="source PDF whose .txt sibling to re-confirm")
    p_vfy.add_argument("--dpi", type=int, default=300)
    p_vfy.add_argument("--blocked-pages", metavar="SPEC", default=None,
                       help="pages filled by PaddleOCR (e.g. '5-7,10'); print the "
                            "PaddleOCR-vs-Tesseract check for each")
    p_vfy.set_defaults(func=cmd_verify)

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
