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
the source page images — not the sibling. See the prepare-ocr-sibling skill
(.claude/skills/prepare-ocr-sibling/SKILL.md).)

After extraction, ``corroborate-quotes`` re-applies the same consensus rule to
just the spans an artifact actually quotes from this source, and stamps the
result (``quote_corroboration``) onto the artifact's ``primary_sources[]``
entry — the durable, machine-written record that every load-bearing quoted
token is engine-corroborated, enumerating the exceptions (tokens the sibling
holds against both engines, and quotes on PaddleOCR-filled pages) the auditor
must settle against the page images. The ``quote_ocr_corroboration`` check
backstops the stamp's presence/freshness at the commit boundary; engines never
run at commit time. What no layer can catch: a correlated misread shared by the
VLM and both OCR engines — only the audit-phase page-image read covers that.

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
  apply      Mechanically apply a verifier's correction list (``LINE <n> |
             FIND: ... | REPLACE: ...``, the ocr-page-verifier output grammar)
             to the sibling — all-or-nothing, each FIND must match exactly once
             on its stated line, dry-run by default. Replaces the orchestrator
             hand-applying each correction with the Edit tool.
  corroborate-quotes
             Check every artifact quote citing this PDF against the engine
             reads (each load-bearing quote token must be corroborated by an
             OCR engine; contested tokens and PaddleOCR-filled-page quotes are
             enumerated as the audit target list) and stamp the canonical
             ``quote_corroboration`` value onto the artifact entry.
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
import datetime
import difflib
import hashlib
import json
import re
import subprocess
import tempfile

SOURCES_DIR = _REPO_ROOT / "sources"
ENGINE_CACHE_ROOT = _REPO_ROOT / ".scratch" / "cache" / "ocr-consensus"

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


# A cluster of OCR-corroborated tokens this large, anchored at a single spine
# point AND genuinely absent elsewhere from the VLM base (see the present-set
# partition in coverage_warning_from_omissions), signals a whole paragraph/page
# the VLM transcription dropped. possible_omissions is advisory and never
# splices into the sibling, so without this the dropped region ships silently.
# This promotes the largest such absent cluster to a visible coverage_warning at
# production time, so a dropped paragraph/page is recovered before the sibling is
# used.
MAX_OMISSION_RUN = 40


def coverage_warning_from_omissions(omissions, base_text):
    """Return a coverage-warning dict if a cluster of OCR-corroborated tokens is
    genuinely ABSENT from the VLM base — a likely dropped paragraph/page — else
    None. A dropped page becomes one difflib insertion block, so all its tokens
    share a single ``before_token_index``; grouping by that anchor and taking the
    largest group surfaces it.

    The discriminator that separates a real drop from a benign reordering: a
    dropped region's tokens appear NOWHERE in the sibling, whereas a 2-D table
    the VLM rendered as bracketed inline prose (while the OCR engines linearized
    it cell-by-cell in raster order) has every cell value present in the sibling
    — just at a position difflib couldn't align, so it surfaces as one big
    insertion cluster shaped exactly like a dropped page. So the largest
    anchor-run is partitioned by presence elsewhere in ``base_text``, and the
    ``MAX_OMISSION_RUN`` threshold is applied to the ABSENT count only: full
    sensitivity to a real drop (its tokens are absent everywhere) without firing
    on a reordered table/figure (its tokens are present elsewhere)."""
    if not omissions:
        return None
    by_anchor = {}
    for o in omissions:
        by_anchor.setdefault(o["before_token_index"], []).append(o)
    anchor, run = max(by_anchor.items(), key=lambda kv: len(kv[1]))
    present = {norm_token(surf) for surf, _cs, _ce in tokenize(base_text)}
    absent = [o for o in run if norm_token(o["ocr_token"]) not in present]
    if len(absent) < MAX_OMISSION_RUN:
        return None
    elsewhere = len(run) - len(absent)
    return {
        "before_token_index": anchor,
        "line": absent[0]["line"],
        "absent_token_count": len(absent),
        "present_elsewhere_count": elsewhere,
        "run_token_count": len(run),
        "total_omitted_tokens": len(omissions),
        "note": (
            f"{len(absent)} OCR-corroborated tokens at line {absent[0]['line']} "
            f"are absent from the VLM sibling entirely — a candidate dropped "
            f"paragraph/page. The sibling must cover the whole document; recover "
            f"the dropped region before using the sibling."
            + (f" ({elsewhere} other clustered tokens DO appear elsewhere in the "
               f"sibling — likely a reordered table/figure, benign.)"
               if elsewhere else "")
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
# Engine adapters
# ---------------------------------------------------------------------------
def _join_pages(pages):
    """``"\\n".join(pages)`` plus the char offset where each page begins in the
    joined text — the engine-side analogue of ``_concat_pages``'s page_starts,
    so page boundaries are recoverable from any engine read (``verify`` derives
    sibling-side page tags from them; see ``derive_page_starts``)."""
    starts, off = [], 0
    for p in pages:
        starts.append(off)
        off += len(p) + 1   # the joining "\n"
    return "\n".join(pages), starts


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
        try:
            out = subprocess.run(
                ["tesseract", str(img), "stdout", "--psm", "1", "-l", "eng"],
                check=True, capture_output=True, text=True,
            )
        except subprocess.CalledProcessError as exc:
            # A silent Tesseract failure (missing `eng` traineddata, OOM, bad
            # image) would zero out one engine and collapse the two-engine
            # corroboration guarantee to PaddleOCR-only. Fail loudly instead.
            raise SystemExit(
                f"Tesseract failed on {img} (exit {exc.returncode}): "
                f"{(exc.stderr or '').strip()}"
            ) from exc
        pages.append(out.stdout)
        print(f"      Tesseract p.{len(pages)}/{len(images)}", file=sys.stderr, flush=True)
    return _join_pages(pages)


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
        print(f"      PaddleOCR p.{len(pages)}/{len(images)}", file=sys.stderr, flush=True)
    return _join_pages(pages)


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


def derive_page_starts(base_text, engine_text, engine_page_starts):
    """Sibling-side page start offsets, derived by aligning an engine read's
    per-page boundaries onto the sibling base text.

    Computed fresh from the PDF on every call — deliberately NO persisted page
    metadata: token-level verifier corrections edit the sibling between ``run``
    and ``verify``, so any stored offsets would be stale exactly when ``verify``
    runs. A single difflib pass over ``tokenize()`` output collects confident
    ('equal'-opcode) (engine_offset, base_offset) pairs — both coordinates
    monotone because difflib opcodes advance both streams monotonically — then
    each engine page start bisects to the nearest matched pair's base offset.
    Boundary-adjacent rows can therefore land one page off (an empty engine
    page collapses its boundary onto the next); derived tags print as ``~p.N``.
    Returns None when alignment finds no confident pairs (no tags beat wrong
    tags)."""
    base_tokens = tokenize(base_text)
    eng_tokens = tokenize(engine_text)
    sm = difflib.SequenceMatcher(
        a=[norm_token(t[0]) for t in base_tokens],
        b=[norm_token(t[0]) for t in eng_tokens], autojunk=False)
    pairs = []   # (engine_char_off, base_char_off), 'equal' blocks only -> monotone
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                pairs.append((eng_tokens[j1 + k][1], base_tokens[i1 + k][1]))
    if not pairs:
        return None
    eng_offs = [p[0] for p in pairs]
    starts = [0]
    for ps in engine_page_starts[1:]:
        idx = bisect.bisect_left(eng_offs, ps)
        base_off = pairs[idx][1] if idx < len(pairs) else len(base_text)
        starts.append(max(base_off, starts[-1]))   # keep monotone for bisect
    return starts


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


def _print_divergence_rows(rows, sibling, page_starts, derived=False):
    tag = "~p." if derived else "p."
    for c in rows:
        cand = c["candidates"]
        if cand["vlm"] is None:          # OCR-only sibling (VLM skipped): base == tesseract
            reads = f"sibling={cand['tesseract']!r}  paddleocr={cand['paddleocr']!r}"
        else:
            reads = (f"sibling={cand['vlm']!r}  tesseract={cand['tesseract']!r}  "
                     f"paddleocr={cand['paddleocr']!r}")
        page = _page_of_offset(page_starts, c["char_start"])
        loc = f"{tag}{page} line {c['line']}" if page else f"line {c['line']}"
        print(f"    {loc}: {reads}")
        print(f"      {c['context']}")


def print_confirm_report(divergences, sibling, page_starts=None, derived=False):
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

    Page numbers are shown when ``page_starts`` is supplied — exact ``p.N`` from
    ``run --vlm-pages``, or ``~p.N`` when ``derived`` (boundaries aligned onto
    the sibling from the Tesseract page reads; see ``derive_page_starts``)."""
    if not divergences:
        print(f"\n  ✓ CONFIRMED: every load-bearing word/number in {sibling.name} is "
              f"corroborated by an OCR engine. No divergences to reconcile.")
        return
    high = [c for c in divergences if _is_high_signal(c)]
    weak = [c for c in divergences if not _is_high_signal(c)]
    if page_starts and derived:
        loc_hint = (
            "  (page tags ~p.N derived by aligning OCR page boundaries onto the "
            "sibling — boundary-adjacent rows may be off by one page.)")
    elif page_starts:
        loc_hint = ""
    else:
        loc_hint = (
            "  (no page numbers — page boundaries could not be aligned; locate "
            "the line in the sibling to find its page.)")

    print(f"\n  {len(high)} HIGH-SIGNAL divergence(s) — both OCR engines read the same "
          f"token, differing from the sibling. OPEN THE PAGE IMAGE for each and decide "
          f"the true reading there; do NOT infer it from the surrounding sibling text. "
          f"Fix the sibling on a VLM misread; leave it on shared OCR glyph-confusion "
          f"(e.g. µm→um, SiO2→SiOz).{loc_hint}")
    if high:
        _print_divergence_rows(high, sibling, page_starts, derived)
    else:
        print("    (none)")

    print(f"\n  {len(weak)} weak divergence(s) — no single OCR reading corroborated "
          f"(struck-through banners, bracketed [Figure]/[Equation] placeholder text, "
          f"per-engine glyph noise). Skim; open the page image only where one lands on "
          f"body prose.")
    if weak:
        _print_divergence_rows(weak, sibling, page_starts, derived)


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
            return run_paddleocr([left])[0] + "\n" + run_paddleocr([right])[0]
        return run_paddleocr([imgs[0]])[0]


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


def _ocr_pages(pdf, stem, dpi, blocked_pages=(), use_cache=True):
    """Rasterize the PDF and run both OCR engines on the whole document —
    or load the main-pass reads from the engine cache (``_engine_cache_dir``)
    when present; ``use_cache=False`` (``--no-cache``) forces recompute.

    Returns ``(tess_text, paddle_text, blocked_report, tess_starts)``.
    ``tess_starts`` is the per-page start-offset list of the Tesseract join
    (the page authority for derived sibling-side tags; see
    ``derive_page_starts``). ``blocked_report`` is
    ``[(page_number, [divergence, ...]), ...]`` for the content-blocked pages:
    on such a page the sibling text IS the PaddleOCR fill (the VLM couldn't
    produce it), so the only mechanical check is PaddleOCR-vs-Tesseract on that
    one page image. Each divergence is ``{line, context, paddle, tess}`` for a
    load-bearing token the two engines read differently (PaddleOCR is the fill /
    sibling spine; Tesseract cross-checks)."""
    blocked_report = []
    cache = _engine_cache_dir(pdf, dpi)
    t_f, p_f, s_f = cache / "tess.txt", cache / "paddle.txt", cache / "starts.json"
    cached = use_cache and t_f.exists() and p_f.exists() and s_f.exists()
    with tempfile.TemporaryDirectory(prefix=f"ocr-{stem}-") as tmp:
        if cached:
            print(f"      (cached engine reads: {cache})")
            tess_text = t_f.read_text(encoding="utf-8")
            paddle_text = p_f.read_text(encoding="utf-8")
            tess_starts = json.loads(s_f.read_text(encoding="utf-8"))
            images = None
            n_pages = len(tess_starts)
        else:
            images = rasterize(pdf, tmp, dpi)
            print(f"      {len(images)} page image(s)")
            print("      Tesseract (second opinion) ...")
            tess_text, tess_starts = run_tesseract(images)
            print("      PaddleOCR (primary cross-check) ...")
            paddle_text, _ = run_paddleocr(images)
            n_pages = len(images)
            if use_cache:
                cache.mkdir(parents=True, exist_ok=True)
                t_f.write_text(tess_text, encoding="utf-8")
                p_f.write_text(paddle_text, encoding="utf-8")
                s_f.write_text(json.dumps(tess_starts), encoding="utf-8")
        for n in blocked_pages:
            if not (1 <= n <= n_pages):
                print(f"      ! blocked page {n} out of range (1..{n_pages}) — skipped")
                continue
            print(f"      blocked page {n}: PaddleOCR fill vs Tesseract ...")
            img = images[n - 1] if images else _rasterize_one(pdf, n, dpi, tmp)
            p_txt, _ = run_paddleocr([img])
            t_txt, _ = run_tesseract([img])
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
    return tess_text, paddle_text, blocked_report, tess_starts


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


def format_content_block(blocked, vlm_skipped):
    """The artifact's ``content_block`` value, generated from this run's
    blocked-page facts (not hand-narrated). The three returns below are the
    canonical forms — every other surface pastes this verbatim."""
    if vlm_skipped:
        return "All pages — VLM page-image read was content-blocked; produced via OCR."
    if blocked:
        noun = "Page" if len(blocked) == 1 else "Pages"
        verb = "was" if len(blocked) == 1 else "were"
        pages = ", ".join(str(p) for p in blocked)
        return f"{noun} {pages} {verb} content-blocked for the VLM; PaddleOCR-filled."
    return "None"


def print_content_block(blocked, vlm_skipped):
    """Emit the canonical ``content_block`` line (mechanically stamped onto an
    artifact via --stamp-artifact; printed for siblings prepped before any
    artifact exists)."""
    val = format_content_block(blocked, vlm_skipped)
    print("\n  content_block — canonical value for the source's "
          "primary_sources[] entry (--stamp-artifact writes it):")
    print(f"      content_block: '{val}'")


def _locate_source_entry(lines, artifact, pdf_name, flag):
    """(entry_start, entry_end, field_indent) of the artifact's
    primary_sources[] entry whose ``path:`` basename matches the PDF — shared
    by the surgical stampers (``stamp_content_block`` /
    ``stamp_quote_corroboration``). ``entry_end`` is one past the entry's last
    field line. ``field_indent`` is the entry's own field indentation
    (list-item indent + 2): artifacts in the corpus carry both column-0
    (``- path:``) and nested (``  - path:``) list styles, so the indent is
    derived from the matched entry, never assumed."""
    entry_start = None
    item_indent = ""
    for i, ln in enumerate(lines):
        m = re.match(r"^(\s*)- path:\s*(\S+)\s*$", ln)
        if m and Path(m.group(2)).name == pdf_name:
            entry_start, item_indent = i, m.group(1)
            break
    if entry_start is None:
        raise SystemExit(
            f"{flag}: no primary_sources entry with path basename "
            f"{pdf_name!r} in {artifact}")
    field_indent = item_indent + "  "
    entry_end = entry_start + 1
    while entry_end < len(lines):
        ln = lines[entry_end]
        if ln.startswith(item_indent + "- "):   # next sibling list item
            break
        if not ln.startswith(field_indent):     # left the entry's field block
            break
        entry_end += 1
    return entry_start, entry_end, field_indent


def stamp_content_block(artifact_path, pdf_name, val):
    """Write ``content_block: '<val>'`` onto the artifact's primary_sources[]
    entry whose ``path:`` basename matches the PDF — a surgical line edit (no
    YAML reflow), so the value never passes through a hand-paste.

    Replaces an existing ``content_block`` line in the entry, else inserts one
    after the entry's ``format:`` line (or the ``path:`` line). Refuses to
    overwrite a ``vlm_skipped`` sentinel ("All pages — ...") with a derived
    value: ``verify`` cannot know the sibling was OCR-only, so the original
    ``run``'s value stands (see cmd_verify's note)."""
    artifact = Path(artifact_path)
    if not artifact.exists():
        raise SystemExit(f"--stamp-artifact: artifact not found: {artifact}")
    lines = artifact.read_text(encoding="utf-8").splitlines(keepends=True)
    entry_start, entry_end, ind = _locate_source_entry(
        lines, artifact, pdf_name, "--stamp-artifact")

    new_line = f"{ind}content_block: '{val}'\n"
    for j in range(entry_start + 1, entry_end):
        m = re.match(rf"^{ind}content_block:\s*'?(.*?)'?\s*$", lines[j])
        if m:
            existing = m.group(1)
            if existing == val:
                print(f"  content_block already stamped on {artifact} (unchanged)")
                return
            if existing.startswith("All pages"):
                print(f"  content_block NOT overwritten on {artifact}: existing "
                      f"vlm-skipped value {existing!r} is owned by the original "
                      f"run (verify derives only from --blocked-pages)")
                return
            if val == "None" and existing.startswith(("Pages", "Page ")):
                print(f"  content_block NOT overwritten on {artifact}: refusing to "
                      f"downgrade a recorded block {existing!r} to 'None' — re-run "
                      f"with --blocked-pages to restate the blocked pages, or edit "
                      f"the artifact directly if the block is genuinely cleared")
                return
            lines[j] = new_line
            artifact.write_text("".join(lines), encoding="utf-8")
            print(f"  content_block updated on {artifact}: {existing!r} -> {val!r}")
            return

    insert_at = entry_start + 1
    for j in range(entry_start + 1, entry_end):
        if re.match(rf"^{ind}format:", lines[j]):
            insert_at = j + 1
            break
    lines.insert(insert_at, new_line)
    artifact.write_text("".join(lines), encoding="utf-8")
    print(f"  content_block stamped on {artifact}: '{val}'")


# ---------------------------------------------------------------------------
# Quote corroboration — the same consensus rule, scoped to the spans an
# artifact actually quotes from this source. Sibling production confirms the
# whole document once; this re-derives the verdict for exactly the text that
# became quotes, and stamps it durably so the commit gate can verify the run
# happened (and the auditor gets an enumerated target list instead of free
# spot-checking).
# ---------------------------------------------------------------------------
def _find_token_runs(haystack, needle):
    """Every start index where ``needle`` occurs as a contiguous run in
    ``haystack`` (both lists of normalized tokens). All occurrences matter:
    when a quote's text appears twice in the sibling, the artifact doesn't
    record which occurrence it was drawn from, so a contested token in ANY
    occurrence must flag (corroborating only the first would under-flag)."""
    n, m = len(haystack), len(needle)
    if m == 0 or m > n:
        return []
    first = needle[0]
    return [k for k in range(n - m + 1)
            if haystack[k] == first and haystack[k:k + m] == needle]


def corroborate_quote_spans(sib_text, quote_items, divergences):
    """Locate each quote's load-bearing token run in the sibling and intersect
    it with the document's contested tokens.

    ``quote_items`` is ``[(qid, quote_text), ...]``; ``divergences`` is
    ``confirm_report``'s output (already load-bearing-filtered, ``token_index``
    keyed into ``tokenize(sib_text)``). Matching is on the load-bearing tokens
    only, normalized exactly as the consensus normalizes them — punctuation,
    hyphenation and smart quotes can't break the match, mirroring how the
    verbatim-quote check's ``normalize_for_compare`` already matched this
    quote into this sibling.

    Returns ``(per_quote, not_located)``. Each per-quote dict carries the
    matched sibling token indices (all occurrences unioned), their char
    starts (for page mapping), and the contested divergences that fall inside
    the quote. A quote in ``not_located`` means the token-run search failed —
    either the verbatim-quote check is not green for this artifact, or the
    quote has no load-bearing tokens at all; corroboration cannot proceed."""
    sib_tokens = tokenize(sib_text)
    lb_idx, lb_norm = [], []
    for i, (surf, cs, ce) in enumerate(sib_tokens):
        if is_load_bearing(surf, sib_text, cs, ce):
            norm = norm_token(surf)
            if not norm:
                continue  # hyphen-class token: normalizes to nothing, so there
                # is nothing to corroborate — and its load-bearing verdict is
                # whitespace-context-sensitive (`10^11 -10^18` in a quote vs the
                # sibling's line-wrapped `-\n10^18`), so keeping it desyncs the
                # two streams and breaks the run match for a verbatim-green quote
            lb_idx.append(i)
            lb_norm.append(norm)
    div_by_tok = {d["token_index"]: d for d in divergences}
    per_quote, not_located = [], []
    for qid, text in quote_items:
        q_lb = [n for (surf, cs, ce) in tokenize(text)
                if is_load_bearing(surf, text, cs, ce)
                and (n := norm_token(surf))]
        runs = _find_token_runs(lb_norm, q_lb)
        if not runs:
            not_located.append(qid)
            continue
        token_indices = sorted({i for k in runs for i in lb_idx[k:k + len(q_lb)]})
        per_quote.append({
            "qid": qid,
            "lb_token_count": len(q_lb),
            "occurrences": len(runs),
            "char_starts": [sib_tokens[i][1] for i in token_indices],
            "contested": [div_by_tok[i] for i in token_indices if i in div_by_tok],
        })
    return per_quote, not_located


def _blocked_pages_from_content_block(val):
    """Recover the blocked page list from a stamped ``content_block`` value
    (the recorded production fact — ``format_content_block`` is its only
    writer, so this parse is the inverse of that canonical form)."""
    m = re.match(r"^Pages? ([0-9, ]+) (?:was|were) content-blocked", val or "")
    if not m:
        return []
    return sorted(int(p) for p in m.group(1).split(",") if p.strip())


def format_quote_corroboration(date, n_quotes, contested_items, filled_items, sha12):
    """The artifact's ``quote_corroboration`` value, generated from this run's
    facts (never hand-narrated) — the canonical form every other surface
    pastes verbatim. The ``quote_ocr_corroboration`` check parses the quote
    count, the contested count, and the sibling hash back out of it, so those
    three anchors are stable interfaces."""
    parts = [f"{date}: {n_quotes} quote(s) corroborated against the OCR engine reads"]
    if contested_items:
        parts.append(f"{len(contested_items)} contested token(s): "
                     + ", ".join(contested_items)
                     + " — sibling kept against the engines; page-image-verify each at audit")
    else:
        parts.append("0 contested")
    if filled_items:
        parts.append("on PaddleOCR-filled page(s): " + ", ".join(filled_items)
                     + " — single-engine text; page-image-verify at audit")
    parts.append(f"sibling sha256:{sha12}")
    return "; ".join(parts)


def stamp_quote_corroboration(artifact_path, pdf_name, val):
    """Write ``quote_corroboration: '<val>'`` onto the artifact's matching
    primary_sources[] entry — the same surgical line edit as
    ``stamp_content_block`` (no YAML reflow; the value never passes through a
    hand-paste). Replaces an existing line, else inserts after the entry's
    ``content_block`` line (the prep-time stamp this one builds on), falling
    back to ``format:`` / ``path:``."""
    artifact = Path(artifact_path)
    if not artifact.exists():
        raise SystemExit(f"corroborate-quotes: artifact not found: {artifact}")
    lines = artifact.read_text(encoding="utf-8").splitlines(keepends=True)
    entry_start, entry_end, ind = _locate_source_entry(
        lines, artifact, pdf_name, "corroborate-quotes")

    new_line = f"{ind}quote_corroboration: '{val}'\n"
    for j in range(entry_start + 1, entry_end):
        m = re.match(rf"^{ind}quote_corroboration:\s*'?(.*?)'?\s*$", lines[j])
        if m:
            if m.group(1) == val:
                print(f"  quote_corroboration already stamped on {artifact} (unchanged)")
                return
            lines[j] = new_line
            artifact.write_text("".join(lines), encoding="utf-8")
            print(f"  quote_corroboration updated on {artifact}: {val!r}")
            return

    insert_at = entry_start + 1
    for j in range(entry_start + 1, entry_end):
        if re.match(rf"^{ind}(format|content_block):", lines[j]):
            insert_at = j + 1   # last of format:/content_block: wins
    lines.insert(insert_at, new_line)
    artifact.write_text("".join(lines), encoding="utf-8")
    print(f"  quote_corroboration stamped on {artifact}: '{val}'")


def _resolve_pdf(arg):
    pdf = Path(arg)
    if not pdf.is_absolute() and not pdf.exists():
        pdf = SOURCES_DIR / arg
    if not pdf.exists():
        raise SystemExit(f"PDF not found: {pdf}")
    return pdf


def _engine_cache_dir(pdf, dpi):
    """Cache directory for this PDF's engine reads. The key covers every input
    the reads depend on — the PDF bytes, the dpi, and both engine versions —
    and deliberately NOT the sibling: engine output is a pure function of the
    page images, so sibling corrections between `run` and `verify` can never
    stale a hit (the comparison against the sibling is recomputed every call).
    Lives under .scratch/cache/ — derived state, never committed, but expensive
    enough to recompute that it must survive /tmp cleanup (the regeneration-cost
    boundary; see .scratch/.gitignore)."""
    h = hashlib.sha256()
    h.update(Path(pdf).read_bytes())
    h.update(f"|dpi={dpi}|tess={tesseract_version()}|paddle={paddleocr_version()}"
             .encode("utf-8"))
    return ENGINE_CACHE_ROOT / h.hexdigest()[:24]


def _rasterize_one(pdf, page_num, dpi, out_dir):
    """Rasterize a single page — the cached-engine path still needs page images
    for the per-blocked-page engine re-checks."""
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page_num), "-l", str(page_num),
         str(pdf), str(Path(out_dir) / f"only-p{page_num}")],
        check=True, capture_output=True,
    )
    imgs = sorted(Path(out_dir).glob(f"only-p{page_num}*.png"))
    if not imgs:
        raise SystemExit(f"page {page_num}: rasterize produced no image")
    return imgs[0]


def _concat_pages(pages_dir):
    """Concatenate the per-page VLM scratch files (``pNN.txt``, zero-padded) into
    the sibling base text, tracking each page's start offset.

    This replaces the manual ``cat .scratch/drafts/ocr-{stem}/p*.txt`` step so the tool knows the
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
    tess_text, paddle_text, blocked_report, tess_starts = _ocr_pages(
        pdf, stem, args.dpi, blocked, use_cache=not args.no_cache)

    print("[2/2] Writing the sibling + confirming load-bearing words/numbers ...")
    page_starts, derived = None, False
    if args.vlm_pages:
        base_text, page_starts = _concat_pages(args.vlm_pages)   # exact tags
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
        page_starts = derive_page_starts(base_text, tess_text, tess_starts)
        derived = True
    else:
        base_text = tess_text   # OCR-only fallback: Tesseract is the readable base
        vlm_skipped = True
        page_starts = tess_starts   # base IS the Tesseract join — exact tags

    sibling.write_text(base_text, encoding="utf-8")
    print(f"\n  sibling : {sibling}")

    divergences, omissions = confirm_report(base_text, tess_text, paddle_text, vlm_skipped)
    coverage_warning = coverage_warning_from_omissions(omissions, base_text)
    if coverage_warning:
        cw = coverage_warning
        extra = (f" ({cw['present_elsewhere_count']} more clustered here appear "
                 f"elsewhere in the sibling — likely a reordered table/figure, benign)"
                 if cw["present_elsewhere_count"] else "")
        print(f"\n  ⚠ COVERAGE WARNING: {cw['absent_token_count']} OCR-corroborated "
              f"tokens at line {cw['line']} are absent from the VLM sibling entirely "
              f"— a candidate dropped paragraph/page. Recover it before using the "
              f"sibling.{extra}")

    print_confirm_report(divergences, sibling, page_starts, derived)
    print_blocked_report(blocked_report)
    print_content_block(blocked, vlm_skipped)
    if args.stamp_artifact:
        stamp_content_block(args.stamp_artifact, pdf.name,
                            format_content_block(blocked, vlm_skipped))


def cmd_verify(args):
    """Re-confirm an EXISTING sibling against the OCR engines (no regeneration):
    the same load-bearing divergence report `run` prints, with derived ``~p.N``
    page tags (page boundaries aligned onto the sibling from the Tesseract
    reads — fresh each run, since verifier corrections shift sibling offsets).
    Use when re-checking a sibling that was produced earlier."""
    pdf = _resolve_pdf(args.pdf)
    stem = pdf.with_suffix("").name
    sibling = pdf.with_suffix(".txt")
    if not sibling.exists():
        raise SystemExit(
            f"no sibling to verify: {sibling}\n"
            f"  produce it first: ocr-consensus.py run {args.pdf} --vlm ...")

    blocked = parse_pages(args.blocked_pages)
    print(f"Rasterizing {pdf.name} at {args.dpi} dpi + OCR (re-confirm) ...")
    tess_text, paddle_text, blocked_report, tess_starts = _ocr_pages(
        pdf, stem, args.dpi, blocked, use_cache=not args.no_cache)
    sib_text = sibling.read_text(encoding="utf-8")
    vlm_skipped = bool(args.vlm_skipped)
    divergences, _ = confirm_report(sib_text, tess_text, paddle_text,
                                    vlm_skipped=vlm_skipped)
    page_starts = derive_page_starts(sib_text, tess_text, tess_starts)
    print_confirm_report(divergences, sibling, page_starts, derived=True)
    print_blocked_report(blocked_report)
    # The canonical value derives from this run's recorded production facts:
    # --blocked-pages for the common partial-block case, --vlm-skipped for a
    # whole-doc OCR-only sibling (verify cannot detect that itself — it
    # re-checks, it doesn't produce — so the operator supplies the recorded
    # fact, exactly as with --blocked-pages).
    print_content_block(blocked, vlm_skipped)
    if args.stamp_artifact:
        stamp_content_block(args.stamp_artifact, pdf.name,
                            format_content_block(blocked, vlm_skipped))


# ---------------------------------------------------------------------------
# apply — mechanically apply a verifier's correction list to the sibling.
# The ocr-page-verifier agents REPORT corrections (they never edit); this script
# applies them, enforcing the "each FIND matches exactly once" rule mechanically
# and keeping the whole sibling lifecycle on the agents-judge / scripts-mutate
# line.
# ---------------------------------------------------------------------------

CORRECTION_RE = re.compile(r"^LINE (\d+) \| FIND: (.+?) \| REPLACE: (.+)$")


def parse_corrections(text):
    """Parse a verifier correction list — one ``LINE <n> | FIND: ... |
    REPLACE: ...`` per line, the exact grammar the ocr-page-verifier contract
    emits. Any other non-blank line is a hard error: feed corrections only,
    never the verifier's prose or its end-of-run summary line. Returns
    ``[(line_no, find, replace), ...]`` in input order; raises ValueError on
    any grammar violation (no-op FIND==REPLACE, duplicate LINE+FIND, junk)."""
    corrections, seen = [], set()
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = CORRECTION_RE.match(line)
        if not m:
            raise ValueError(
                "unparseable correction line (expected "
                f"'LINE <n> | FIND: ... | REPLACE: ...'):\n  {line}")
        n, find, replace = int(m.group(1)), m.group(2), m.group(3)
        if find == replace:
            raise ValueError(f"LINE {n}: FIND and REPLACE are identical: {find!r}")
        key = (n, find)
        if key in seen:
            raise ValueError(f"LINE {n}: duplicate correction for FIND: {find!r}")
        seen.add(key)
        corrections.append((n, find, replace))
    if not corrections:
        raise ValueError("empty correction list")
    return corrections


def apply_corrections(sib_text, corrections):
    """Apply parsed corrections to the sibling text, all-or-nothing. Each FIND
    must occur exactly once on its stated 1-indexed line (0 or >1 is an error
    and NOTHING is applied). Same-line corrections apply in input order against
    the already-corrected line. REPLACE is single-line by grammar, so the line
    count is invariant and later line numbers never shift. Returns
    ``(new_text, report_lines)``; raises ValueError listing every violation."""
    lines = sib_text.splitlines(keepends=True)
    errors, report = [], []
    for n, find, replace in corrections:
        if not 1 <= n <= len(lines):
            errors.append(f"LINE {n}: out of range (sibling has {len(lines)} lines)")
            continue
        body = lines[n - 1]
        count = body.count(find)
        if count != 1:
            errors.append(
                f"LINE {n}: FIND must match exactly once on the line, "
                f"found {count}: {find!r}")
            continue
        lines[n - 1] = body.replace(find, replace, 1)
        report.append(f"LINE {n}: {find!r} -> {replace!r}")
    if errors:
        raise ValueError("\n".join(errors))
    return "".join(lines), report


def cmd_apply(args):
    """Mechanically apply a verifier correction list to the EXISTING sibling
    (read from stdin), then point at `verify` to re-confirm. Dry run by
    default; --write applies. All-or-nothing: any violation writes nothing."""
    pdf = _resolve_pdf(args.pdf)
    sibling = pdf.with_suffix(".txt")
    if not sibling.exists():
        raise SystemExit(
            f"no sibling to correct: {sibling}\n"
            f"  produce it first: ocr-consensus.py run {args.pdf} --vlm-pages ...")
    if not args.stdin:
        raise SystemExit(
            "apply reads the correction list from stdin: pass --stdin and feed "
            "the verifier's LINE/FIND/REPLACE lines (heredoc)")
    try:
        corrections = parse_corrections(sys.stdin.read())
        new_text, report = apply_corrections(
            sibling.read_text(encoding="utf-8"), corrections)
    except ValueError as e:
        raise SystemExit(f"apply: nothing written —\n{e}")
    for r in report:
        print(r)
    if args.write:
        sibling.write_text(new_text, encoding="utf-8")
        print(f"\nApplied {len(report)} correction(s) to {sibling}")
        print(f"Re-confirm: ocr-consensus.py verify {args.pdf} "
              f"[--blocked-pages ...]")
    else:
        print(f"\nDRY RUN — {len(report)} correction(s) parse clean and each "
              f"FIND matches exactly once; pass --write to apply")


def cmd_corroborate(args):
    """Corroborate every artifact quote citing this PDF against the engine
    reads, then stamp the canonical ``quote_corroboration`` value onto the
    artifact's entry. The consensus rule is the sibling-production one, scoped
    to quoted spans: a load-bearing quoted token passes when an OCR engine
    corroborates the sibling's reading; the exceptions — contested tokens
    (sibling against both engines) and quotes on PaddleOCR-filled pages
    (single-engine text) — are enumerated for the auditor to settle against
    the page images. Production facts (``vlm_skipped``, blocked pages) derive
    from the entry's stamped ``content_block``, so the operator re-supplies
    nothing. Refuses to stamp when any quote cannot be located in the sibling
    (the verbatim-quote check must be green first)."""
    pdf = _resolve_pdf(args.pdf)
    stem = pdf.with_suffix("").name
    sibling = pdf.with_suffix(".txt")
    if not sibling.exists():
        raise SystemExit(
            f"no sibling to corroborate against: {sibling}\n"
            f"  produce + confirm one first via /prepare-ocr-sibling")
    artifact = Path(args.artifact)
    if not artifact.exists():
        raise SystemExit(f"corroborate-quotes: artifact not found: {artifact}")
    import yaml  # noqa: PLC0415  (deferred, like the engine imports)
    data = yaml.safe_load(artifact.read_text(encoding="utf-8")) or {}
    sources = data.get("primary_sources") or []
    entry = next((s for s in sources if isinstance(s, dict)
                  and Path(s.get("path") or "").name == pdf.name), None)
    if entry is None:
        raise SystemExit(
            f"corroborate-quotes: no primary_sources entry with path basename "
            f"{pdf.name!r} in {artifact}")
    content_block = entry.get("content_block")
    if not content_block:
        raise SystemExit(
            f"corroborate-quotes: the entry carries no content_block — stamp the "
            f"production facts first:\n"
            f"  ocr-consensus.py verify {args.pdf} --stamp-artifact {artifact}")
    vlm_skipped = content_block.startswith("All pages")
    blocked = _blocked_pages_from_content_block(content_block)

    quote_items = []
    for i, q in enumerate(data.get("quotes") or []):
        if not isinstance(q, dict) or not isinstance(q.get("text"), str):
            continue
        src = q.get("source")
        path = src.get("path") if isinstance(src, dict) else None
        if path and Path(path).name == pdf.name:
            quote_items.append((q.get("id") or f"quotes[{i}]", q["text"]))
    if not quote_items:
        print(f"no quotes in {artifact} cite {pdf.name} — nothing to corroborate; "
              f"no stamp written")
        return

    print(f"Corroborating {len(quote_items)} quote(s) citing {pdf.name} "
          f"against the OCR engine reads ...")
    tess_text, paddle_text, _, tess_starts = _ocr_pages(
        pdf, stem, args.dpi, (), use_cache=not args.no_cache)
    sib_text = sibling.read_text(encoding="utf-8")
    divergences, _ = confirm_report(sib_text, tess_text, paddle_text,
                                    vlm_skipped=vlm_skipped)
    per_quote, not_located = corroborate_quote_spans(sib_text, quote_items, divergences)
    page_starts = derive_page_starts(sib_text, tess_text, tess_starts)

    contested_items, filled_items = [], []
    for pq in per_quote:
        occ = f" ({pq['occurrences']} occurrences, unioned)" if pq["occurrences"] > 1 else ""
        on_blocked = sorted({p for cs in pq["char_starts"]
                             for p in [_page_of_offset(page_starts, cs)]
                             if p in blocked}) if blocked and page_starts else []
        if not pq["contested"] and not on_blocked:
            print(f"  ✓ {pq['qid']}: {pq['lb_token_count']} load-bearing token(s), "
                  f"every one engine-corroborated{occ}")
            continue
        if pq["contested"]:
            print(f"  ⚠ {pq['qid']}: {len(pq['contested'])} contested token(s) — the "
                  f"sibling holds these against the engines; settle each against the "
                  f"PAGE IMAGE{occ}:")
            _print_divergence_rows(pq["contested"], sibling, page_starts, derived=True)
            for c in pq["contested"]:
                surf = c["candidates"]["vlm"] or c["candidates"]["tesseract"]
                contested_items.append(f"{pq['qid']} ‹{surf}› (line {c['line']})")
        if on_blocked:
            pages = ", ".join(f"p.{p}" for p in on_blocked)
            print(f"  ◍ {pq['qid']}: spans PaddleOCR-filled {pages} — the sibling "
                  f"there IS the fill (single-engine text); page-image-verify at audit")
            filled_items.append(f"{pq['qid']} ({pages})")
    if not_located:
        raise SystemExit(
            f"corroborate-quotes: {len(not_located)} quote(s) could not be located "
            f"in the sibling token stream: {', '.join(not_located)}\n"
            f"  run the verbatim-quote check first (validate-research.py --phase "
            f"extract {artifact}) — corroboration stamps nothing until every "
            f"quote locates.")

    sha12 = hashlib.sha256(sibling.read_bytes()).hexdigest()[:12]
    val = format_quote_corroboration(
        datetime.date.today().isoformat(), len(quote_items),
        contested_items, filled_items, sha12)
    print(f"\n  {len(quote_items)} quote(s): {len(contested_items)} contested "
          f"token(s), {len(filled_items)} on PaddleOCR-filled pages.")
    stamp_quote_corroboration(artifact, pdf.name, val)


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

    # Case 6: derived page starts — engine pages aligned onto a base text that
    # diverges by one mutated and one deleted token; each derived start must hit
    # the base offset of that page's first token, and an empty middle page must
    # not break monotonicity.
    eng_pages = ["alpha bravo charlie", "delta echo foxtrot", "", "golf hotel india"]
    eng_text, eng_starts = _join_pages(eng_pages)
    base6 = "alpha bravo charlie delta XXXXX foxtrot golf india"  # echo mutated, hotel deleted
    starts6 = derive_page_starts(base6, eng_text, eng_starts)
    if not starts6 or len(starts6) != 4:
        failures.append(f"case6: expected 4 derived starts, got {starts6}")
    else:
        if starts6[0] != 0 or starts6[1] != base6.index("delta"):
            failures.append(f"case6: page-2 start should be base offset of 'delta', got {starts6}")
        if starts6 != sorted(starts6):
            failures.append(f"case6: derived starts not monotone: {starts6}")
        if _page_of_offset(starts6, base6.index("golf")) != 4:
            failures.append(f"case6: 'golf' should tag page 4, got {_page_of_offset(starts6, base6.index('golf'))}")

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

    # Case 9: content_block stamping — insert, idempotent re-stamp, update, and
    # the vlm-skipped overwrite refusal; surgical edit leaves every other byte.
    art_body = ("id: meta/research/example\n"
                "primary_sources:\n"
                "- path: government/example-2010.pdf\n"
                "  format: pdf\n"
                "- path: government/other.pdf\n"
                "  format: pdf\n"
                "quotes: []\n")
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tf:
        tf.write(art_body)
        art = Path(tf.name)
    try:
        stamp_content_block(art, "example-2010.pdf", "None")
        t1 = art.read_text(encoding="utf-8")
        if "- path: government/example-2010.pdf\n  format: pdf\n  content_block: 'None'\n" not in t1:
            failures.append(f"case9: insert-after-format failed:\n{t1}")
        if t1.count("content_block") != 1:
            failures.append("case9: stamped the wrong entry too")
        stamp_content_block(art, "example-2010.pdf", "None")          # idempotent
        if art.read_text(encoding="utf-8") != t1:
            failures.append("case9: re-stamp with same value changed the file")
        stamp_content_block(art, "example-2010.pdf",
                            "Pages 5, 6 were content-blocked for the VLM; PaddleOCR-filled.")
        if "Pages 5, 6" not in art.read_text(encoding="utf-8"):
            failures.append("case9: update of existing value failed")
        sentinel = "All pages — VLM page-image read was content-blocked; produced via OCR."
        stamp_content_block(art, "example-2010.pdf", sentinel)        # run may set it
        stamp_content_block(art, "example-2010.pdf", "None")          # verify must not clobber
        if sentinel not in art.read_text(encoding="utf-8"):
            failures.append("case9: vlm-skipped sentinel was overwritten by a derived value")
        if art.read_text(encoding="utf-8").replace(
                f"  content_block: '{sentinel}'\n", "") != art_body:
            failures.append("case9: stamp touched bytes outside the content_block line")
    finally:
        art.unlink()

    # Case 9b: nested-indent list style ("  - path:") — the corpus carries both
    # styles, so the stampers derive the entry's field indent instead of
    # assuming column-0 (the assumption that broke four backfill stamps).
    art_body9b = ("id: meta/research/example\n"
                  "primary_sources:\n"
                  "  - path: government/example-2010.pdf\n"
                  "    format: pdf\n"
                  "  - path: government/other.pdf\n"
                  "    format: pdf\n"
                  "quotes: []\n")
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tf:
        tf.write(art_body9b)
        art9b = Path(tf.name)
    try:
        stamp_content_block(art9b, "example-2010.pdf", "None")
        t9b = art9b.read_text(encoding="utf-8")
        if ("  - path: government/example-2010.pdf\n    format: pdf\n"
                "    content_block: 'None'\n  - path:") not in t9b:
            failures.append(f"case9b: nested-indent insert failed:\n{t9b}")
        if t9b.count("content_block") != 1:
            failures.append("case9b: stamped the wrong entry too")
        stamp_quote_corroboration(art9b, "example-2010.pdf", "test-value")
        t9b2 = art9b.read_text(encoding="utf-8")
        if "    content_block: 'None'\n    quote_corroboration: 'test-value'\n" not in t9b2:
            failures.append(f"case9b: nested-indent quote_corroboration insert failed:\n{t9b2}")
    finally:
        art9b.unlink()

    # Case 10: quote corroboration — locate each quote's load-bearing token run
    # in the sibling, intersect with the document's contested tokens. A clean
    # quote reports zero contested; a quote containing the document's contested
    # token inherits exactly that divergence; punctuation/smart-quote drift
    # between quote and sibling can't break the match; a repeated phrase unions
    # all occurrences; an absent quote refuses to locate.
    sib10 = ('Report alpha bravo, volume 82 by Klyshko and Shih. '
             'The phrase delta echo recurs; delta echo closes it.')
    tess10 = sib10.replace("82", "81")
    paddle10 = sib10.replace("82", "81")
    div10, _ = confirm_report(sib10, tess10, paddle10)
    pq, nl = corroborate_quote_spans(
        sib10,
        [("q1", "alpha bravo"),                      # clean
         ("q2", 'volume 82 by "Klyshko"'),           # contains the contested token
         ("q3", "delta echo"),                       # two occurrences
         ("q4", "never in the document")],           # must refuse to locate
        div10)
    by_id = {p["qid"]: p for p in pq}
    if nl != ["q4"]:
        failures.append(f"case10: expected only q4 not-located, got {nl}")
    if "q1" not in by_id or by_id["q1"]["contested"]:
        failures.append(f"case10: q1 should locate with 0 contested, got {by_id.get('q1')}")
    q2 = by_id.get("q2")
    if not q2 or len(q2["contested"]) != 1 or q2["contested"][0]["candidates"]["vlm"] != "82":
        failures.append(f"case10: q2 should inherit the ‹82› divergence, got {q2}")
    if not by_id.get("q3") or by_id["q3"]["occurrences"] != 2:
        failures.append(f"case10: q3 should union 2 occurrences, got {by_id.get('q3')}")

    # Case 10b: whitespace-context hyphen asymmetry — a numeric-sign hyphen is
    # load-bearing in the quote (`-10^18`) but line-wrap makes it structure in
    # the sibling (`-` + space); tokens that normalize to nothing are dropped
    # from both streams, so the verbatim-green quote still locates.
    sib10b = "density of (~ 10^11\n- 10^18 kg/m^3), having a diameter"
    q10b = [("q1", "density of (~ 10^11 -10^18 kg/m^3), having")]
    pq10b, nl10b = corroborate_quote_spans(sib10b, q10b, [])
    if nl10b:
        failures.append(f"case10b: hyphen-asymmetric quote failed to locate: {nl10b}")
    elif pq10b[0]["contested"]:
        failures.append("case10b: clean quote should carry no contested tokens")

    # Case 11: quote_corroboration stamp — canonical value carries the three
    # parse anchors (quote count / contested count / sibling hash); the stamp
    # inserts after content_block, is idempotent, and updates in place leaving
    # every other byte alone.
    v_clean = format_quote_corroboration("2026-06-11", 3, [], [], "abc123def456")
    for anchor in ("3 quote(s) corroborated", "0 contested", "sha256:abc123def456"):
        if anchor not in v_clean:
            failures.append(f"case11: clean value missing anchor {anchor!r}: {v_clean}")
    v_cont = format_quote_corroboration(
        "2026-06-11", 3, ["q2 ‹82› (line 1)"], ["q5 (p.9)"], "abc123def456")
    if "1 contested token(s): q2 ‹82› (line 1)" not in v_cont or "q5 (p.9)" not in v_cont:
        failures.append(f"case11: contested/filled value malformed: {v_cont}")
    art_body11 = ("id: meta/research/example\n"
                  "primary_sources:\n"
                  "- path: government/example-2010.pdf\n"
                  "  format: pdf\n"
                  "  content_block: 'None'\n"
                  "quotes: []\n")
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tf:
        tf.write(art_body11)
        art11 = Path(tf.name)
    try:
        stamp_quote_corroboration(art11, "example-2010.pdf", v_clean)
        t1 = art11.read_text(encoding="utf-8")
        if f"  content_block: 'None'\n  quote_corroboration: '{v_clean}'\n" not in t1:
            failures.append(f"case11: insert-after-content_block failed:\n{t1}")
        stamp_quote_corroboration(art11, "example-2010.pdf", v_clean)   # idempotent
        if art11.read_text(encoding="utf-8") != t1:
            failures.append("case11: re-stamp with same value changed the file")
        stamp_quote_corroboration(art11, "example-2010.pdf", v_cont)    # update
        t2 = art11.read_text(encoding="utf-8")
        if v_cont not in t2 or v_clean in t2:
            failures.append("case11: update of existing value failed")
        if t2.replace(f"  quote_corroboration: '{v_cont}'\n", "") != art_body11:
            failures.append("case11: stamp touched bytes outside the quote_corroboration line")
    finally:
        art11.unlink()
    # content_block parse round-trip (the recorded production facts).
    if _blocked_pages_from_content_block(format_content_block([5, 6], False)) != [5, 6]:
        failures.append("case11: blocked-pages round-trip through content_block failed")
    if _blocked_pages_from_content_block(format_content_block([], True)) != []:
        failures.append("case11: vlm-skipped sentinel should parse to no blocked pages")
    if _blocked_pages_from_content_block("None") != []:
        failures.append("case11: 'None' should parse to no blocked pages")

    # Case 12: apply — the verifier-correction grammar + the all-or-nothing
    # application rules (exactly-once FIND, line-count invariance, same-line
    # sequencing, junk/duplicate/no-op rejection, out-of-range rejection).
    sib12 = "alpha cstimate of the beta\nthe Kiyshko paper\nplain line\n"
    cs12 = parse_corrections(
        "LINE 1 | FIND: cstimate of the | REPLACE: estimate of the\n"
        "\n"
        "LINE 2 | FIND: Kiyshko | REPLACE: Klyshko\n")
    new12, rep12 = apply_corrections(sib12, cs12)
    if "estimate of the" not in new12 or "Klyshko" not in new12 or len(rep12) != 2:
        failures.append(f"case12: corrections not applied: {new12!r}")
    if new12.count("\n") != sib12.count("\n"):
        failures.append("case12: line count changed (REPLACE must be single-line)")
    # same-line corrections apply in order against the corrected line
    new12b, _ = apply_corrections(
        "aa bb\n", [(1, "aa", "cc"), (1, "bb", "aa")])
    if new12b != "cc aa\n":
        failures.append(f"case12: same-line sequencing wrong: {new12b!r}")
    for bad, why in [
            ("fixed 3 tokens, left 2\n", "junk (summary) line accepted"),
            ("LINE 1 | FIND: x | REPLACE: x\n", "no-op FIND==REPLACE accepted"),
            ("LINE 1 | FIND: a | REPLACE: b\nLINE 1 | FIND: a | REPLACE: b\n",
             "duplicate LINE+FIND accepted"),
            ("", "empty list accepted")]:
        try:
            parse_corrections(bad)
            failures.append(f"case12: {why}")
        except ValueError:
            pass
    for bad_cs, why in [
            ([(1, "absent", "x")], "0-match FIND applied"),
            ([(1, "a", "x")], "ambiguous (multi-match) FIND applied"),
            ([(1, "cstimate", "estimate"), (99, "x", "y")],
             "all-or-nothing violated (good correction + out-of-range)")]:
        try:
            apply_corrections(sib12, bad_cs)
            failures.append(f"case12: {why}")
        except ValueError:
            pass

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
    print("  case6: derived page starts -> engine boundaries land on base offsets, monotone")
    print("  case8: load-bearing filter -> words/numbers confirmed, structure not")
    print("  case9: content_block stamp -> insert/idempotent/update surgical, "
          "vlm-skipped sentinel preserved")
    print("  case9b: nested-indent list style -> both stampers derive the "
          "entry's field indent")
    print("  case10b: hyphen load-bearing asymmetry -> empty-normalized tokens "
          "dropped from both streams, verbatim-green quote locates")
    print("  case10: quote corroboration -> located, contested-intersected, "
          "occurrences unioned, absent quote refused")
    print("  case11: quote_corroboration stamp -> canonical anchors, surgical "
          "insert/idempotent/update, content_block fact round-trip")
    print("  case12: apply -> verifier grammar parsed strictly, exactly-once "
          "FIND, all-or-nothing, line count invariant")
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
                                     "base; report rows get derived ~p.N tags (use --vlm-pages "
                                     "for exact ones)")
    p_run.add_argument("--vlm-skipped", metavar="REASON",
                       help="build an OCR-only sibling (Tesseract base, PaddleOCR cross-check) "
                            "and record this reason; for fully content-blocked sources only")
    p_run.add_argument("--dpi", type=int, default=300)
    p_run.add_argument("--no-cache", action="store_true",
                       help="recompute the engine reads even when cached (cache key: "
                            "PDF bytes + dpi + engine versions, under the system temp dir)")
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
    p_run.add_argument("--stamp-artifact", metavar="YAML",
                       help="research artifact whose matching primary_sources[] entry gets "
                            "the content_block value written mechanically (surgical line "
                            "edit; replaces the hand-paste)")
    p_run.set_defaults(func=cmd_run)

    p_vfy = sub.add_parser(
        "verify", help="re-confirm an EXISTING sibling against the OCR engines "
                       "(no regeneration) — same load-bearing divergence report, "
                       "with derived ~p.N page tags")
    p_vfy.add_argument("pdf", help="source PDF whose .txt sibling to re-confirm")
    p_vfy.add_argument("--dpi", type=int, default=300)
    p_vfy.add_argument("--no-cache", action="store_true",
                       help="recompute the engine reads even when cached (cache key: "
                            "PDF bytes + dpi + engine versions, under the system temp dir)")
    p_vfy.add_argument("--blocked-pages", metavar="SPEC", default=None,
                       help="pages filled by PaddleOCR (e.g. '5-7,10'); print the "
                            "PaddleOCR-vs-Tesseract check for each")
    p_vfy.add_argument("--vlm-skipped", action="store_true",
                       help="the sibling is a whole-doc OCR-only production (the VLM read "
                            "was content-blocked at prep, per the sibling's manifest note) — "
                            "derives the 'All pages' content_block sentinel and frames the "
                            "report as the 2-engine comparison it actually is")
    p_vfy.add_argument("--stamp-artifact", metavar="YAML",
                       help="research artifact whose matching primary_sources[] entry gets "
                            "the content_block value written mechanically (a vlm-skipped "
                            "sentinel from the original run is never overwritten by a "
                            "derived value)")
    p_vfy.set_defaults(func=cmd_verify)

    p_app = sub.add_parser(
        "apply", help="mechanically apply a verifier correction list "
                      "(LINE <n> | FIND: ... | REPLACE: ..., from stdin) to the "
                      "EXISTING sibling — all-or-nothing, each FIND must match "
                      "exactly once on its stated line; dry run by default")
    p_app.add_argument("pdf", help="source PDF whose .txt sibling to correct")
    p_app.add_argument("--stdin", action="store_true", required=True,
                       help="read the correction list from stdin (heredoc) — "
                            "correction lines only, never the verifier's prose "
                            "or summary line")
    p_app.add_argument("--write", action="store_true",
                       help="apply the corrections (default: dry run / report only)")
    p_app.set_defaults(func=cmd_apply)

    p_cor = sub.add_parser(
        "corroborate-quotes",
        help="check every artifact quote citing this PDF against the engine "
             "reads and stamp the canonical quote_corroboration value onto "
             "the artifact entry (contested tokens + PaddleOCR-filled-page "
             "quotes enumerated as the audit target list)")
    p_cor.add_argument("pdf", help="source PDF whose quoted spans to corroborate")
    p_cor.add_argument("--artifact", metavar="YAML", required=True,
                       help="research artifact whose quotes cite this PDF; its "
                            "matching primary_sources[] entry must already carry "
                            "content_block (verify --stamp-artifact) and receives "
                            "the quote_corroboration stamp")
    p_cor.add_argument("--dpi", type=int, default=300)
    p_cor.add_argument("--no-cache", action="store_true",
                       help="recompute the engine reads even when cached (cache key: "
                            "PDF bytes + dpi + engine versions, under the system temp dir)")
    p_cor.set_defaults(func=cmd_corroborate)

    args = ap.parse_args()
    if args.selftest:
        sys.exit(cmd_selftest(args))
    if not getattr(args, "func", None):
        ap.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
