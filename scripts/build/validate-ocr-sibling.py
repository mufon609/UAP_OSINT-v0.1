#!/usr/bin/env python3
"""validate-ocr-sibling.py — gate the OCR-consensus verification records.

Every OCR-scan / extraction-lossy source that has a clean-text `.txt` sibling
must carry a FINALIZED verification record at `{stem}-ocr-verification.yaml`
(produced by `scripts/tools/ocr-consensus.py`, spec in
`meta/schema-ocr-verification.yaml`). This validator is the source-layer gate
that the record exists and is trustworthy; `scripts/checks/quote_source_grounding.py`
is the per-quote counterpart run by validate-research.py.

A record is FINALIZED (and the sibling trustworthy) when:
  1. it conforms to the schema's required keys + contested-entry shape;
  2. its engine set has the 3 required votes with ≥2 OCR engines (so no token
     was ever accepted on the VLM read alone);
  3. every contested span is `adjudicated` with a non-null `resolution`;
  4. `sibling_sha256` is set and equals the sha256 of the sibling bytes on disk
     (catches a sibling edited after verification).

Discovery: every manifest PDF artifact flagged `extraction_type: ocr-scan` or
`extraction-lossy` whose same-stem `.txt` sibling exists on disk. An OCR-scan
source not yet given a sibling is a build-readiness matter (the /build flow
handles it), not this validator's concern, so it is not flagged here.

Usage:
  validate-ocr-sibling.py            # full report
  validate-ocr-sibling.py --quiet    # errors only

Exit 0 if every discovered sibling has a finalized conformant record; 1 otherwise.
"""

import argparse
import hashlib
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from lib._common import (  # noqa: E402
    SOURCES_DIR,
    iter_artifacts,
    load_manifest,
)

SCHEMA_PATH = REPO_ROOT / "meta" / "schema-ocr-verification.yaml"
_OCR_TYPES = {"ocr-scan", "extraction-lossy"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def discover_siblings():
    """Yield (parent_pdf_rel, sibling_txt_path, verification_path) for every
    OCR-scan/extraction-lossy PDF whose same-stem .txt sibling exists."""
    found = []
    for _entry, artifact in iter_artifacts(load_manifest()):
        path = artifact.get("path")
        et = artifact.get("extraction_type")
        if not path or et not in _OCR_TYPES:
            continue
        src = SOURCES_DIR / path
        if src.suffix.lower() != ".pdf":
            continue
        sibling = src.with_suffix(".txt")
        if not sibling.exists():
            continue  # not yet prepared — out of this validator's scope
        stem = src.with_suffix("").name
        verification = src.parent / f"{stem}-ocr-verification.yaml"
        found.append((path, sibling, verification))
    # de-dup (a PDF can appear under multiple manifest URLs)
    seen, uniq = set(), []
    for f in found:
        if f[0] in seen:
            continue
        seen.add(f[0])
        uniq.append(f)
    return uniq


def check_record(parent_rel, sibling, verification, schema):
    """Return a list of error strings for one sibling's verification record."""
    errs = []
    if not verification.exists():
        return [f"sources/{parent_rel}: no verification record "
                f"({verification.name}) — sibling fidelity unverified; "
                f"run ocr-consensus.py"]
    try:
        rec = yaml.safe_load(verification.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        return [f"{verification.name}: unreadable ({e})"]
    if not isinstance(rec, dict):
        return [f"{verification.name}: top level is not a mapping"]

    name = verification.name
    for key in schema["required_top_level_keys"]:
        if key not in rec:
            errs.append(f"{name}: missing required key '{key}'")
    if rec.get("schema") != schema["schema_version"]:
        errs.append(f"{name}: schema must be '{schema['schema_version']}', "
                    f"got {rec.get('schema')!r}")

    # Engines: both OCR engines hard-required (the ≥2 uncorrelated-OCR floor);
    # the VLM vote is recommended but waivable via a recorded `vlm_skipped`.
    eng_names = [e.get("name") for e in (rec.get("engines") or []) if isinstance(e, dict)]
    for req in schema["engines"]["required_ocr_engines"]:
        if req not in eng_names:
            errs.append(f"{name}: engines missing required OCR engine '{req}' "
                        f"(the ≥2 uncorrelated-OCR floor — a token must never rest "
                        f"on a single read)")
    if "vlm" not in eng_names and not rec.get("vlm_skipped"):
        errs.append(f"{name}: VLM vote absent and no `vlm_skipped` reason recorded "
                    f"(omit the VLM vote only for the CBRN / content-filter fallback)")

    # Contested entries: shape + finalization.
    ce = schema["contested_entry"]
    for c in (rec.get("contested") or []):
        if not isinstance(c, dict):
            errs.append(f"{name}: contested entry is not a mapping")
            continue
        cid = c.get("id", "?")
        for fld in ce["required_fields"]:
            if fld not in c:
                errs.append(f"{name}: contested {cid} missing field '{fld}'")
        if c.get("status") not in ce["status_values"]:
            errs.append(f"{name}: contested {cid} status {c.get('status')!r} "
                        f"not in {ce['status_values']}")
        if c.get("status") != "adjudicated" or not c.get("resolution"):
            errs.append(f"{name}: contested {cid} NOT finalized "
                        f"(status must be 'adjudicated' with a non-null resolution)")
        rm = c.get("resolution_method")
        if rm is not None and rm not in ce["resolution_method_values"]:
            errs.append(f"{name}: contested {cid} resolution_method {rm!r} "
                        f"not in {ce['resolution_method_values']}")

    # Finalization: sibling_sha256 set + matches sibling bytes on disk.
    recorded = rec.get("sibling_sha256")
    if not recorded:
        errs.append(f"{name}: not finalized (sibling_sha256 unset) — run "
                    f"`ocr-consensus.py assemble`")
    elif sibling.exists():
        actual = sha256_file(sibling)
        if actual != recorded:
            errs.append(f"{name}: sibling sources/{sibling.relative_to(SOURCES_DIR)} "
                        f"sha256 ≠ recorded — sibling edited since verification; re-verify")
    else:
        errs.append(f"{name}: sibling sources/{parent_rel} .txt missing")

    # Advisory lists must at least be lists when present.
    for k in ("possible_omissions", "contamination_flags"):
        if k in rec and not isinstance(rec[k], list):
            errs.append(f"{name}: '{k}' must be a list")
    return errs


def main():
    ap = argparse.ArgumentParser(
        description="Gate OCR-consensus verification records for OCR-scan siblings.")
    ap.add_argument("--quiet", action="store_true", help="errors only")
    args = ap.parse_args()

    schema = load_schema()
    targets = discover_siblings()

    if not args.quiet:
        print("=" * 64)
        print(" OCR-sibling verification-record validation")
        print("=" * 64)
        print(f"  OCR-scan siblings discovered: {len(targets)}")

    total_errs = 0
    for parent_rel, sibling, verification in targets:
        errs = check_record(parent_rel, sibling, verification, schema)
        if errs:
            total_errs += len(errs)
            print(f"\n  ✗ sources/{parent_rel}")
            for e in errs:
                print(f"      - {e}")
        elif not args.quiet:
            print(f"  ✓ sources/{parent_rel}")

    if not args.quiet:
        print("\n" + "=" * 64)
        print(f"  {'PASSED' if total_errs == 0 else 'FAILED'} — {total_errs} error(s)")
    elif total_errs:
        print(f"validate-ocr-sibling.py: {total_errs} error(s)")
    sys.exit(0 if total_errs == 0 else 1)


if __name__ == "__main__":
    main()
