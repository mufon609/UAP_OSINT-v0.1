#!/usr/bin/env python3
"""
Manage sources/manifest.yaml — the source-archival index.

Manifest shape: each entry is one URL with zero or more archived
artifacts (renderings). URL-level fields (status, archive_status,
wayback_date, wayback_skip, note) describe the source; artifact-level
fields (format, path, archived_date, extraction_type,
transcript_provenance, note) describe each rendering. See
meta/schema.yaml manifest_entry / artifact_entry for the canonical
spec.

Commands:
  manifest.py add URL --path PATH [--format FMT] [--note TEXT]
  manifest.py add-sibling {clean-text|speaker-attribution} \
              (--parent-path PATH | --parent-url URL) ...
                                       # register a derived sibling: anchor URL,
                                       # wayback_skip, paths, formats, and the
                                       # note skeleton all derived; pairing with
                                       # the parent entry is checked, not
                                       # remembered
  manifest.py status URL               # show URL entry with all artifacts
  manifest.py pending                  # list URLs needing archival
  manifest.py usage URL                # list nodes citing URL
  manifest.py orphans                  # manifest entries no node cites
  manifest.py missing                  # URLs cited in nodes not in manifest
  manifest.py summary                  # counts by status / format
  manifest.py verify-paths             # check every artifact path exists
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import date
from collections import Counter, defaultdict

try:
    import yaml
except ImportError:
    print("ERROR: Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# scripts/tools/manifest.py — put the scripts/ parent on sys.path so
# `from lib._common` resolves from this nested location.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Wayback-URL detection + manifest I/O share helpers with archive.py
# via lib._common.
from lib._common import (  # noqa: E402
    REPO_ROOT,
    SOURCES_DIR,
    content_dirs,
    format_from_path,
    is_gitignored,
    iter_artifacts,
    load_manifest,
    normalize_source_rel_path,
    save_manifest,
    wayback_url_date,
)

CONTENT_DIRS = content_dirs()

URL_PATTERN = re.compile(r"https?://[^\s\|\)>`\]]+")


def scan_urls_in_nodes():
    usage = defaultdict(set)
    for d in CONTENT_DIRS:
        cd = REPO_ROOT / d
        if not cd.is_dir():
            continue
        for node in cd.glob("*.md"):
            text = node.read_text()
            for url in URL_PATTERN.findall(text):
                url = url.rstrip(";,.)]*")
                usage[url].add(str(node.relative_to(REPO_ROOT)))
    return usage


def _find_entry(entries, url):
    """Return the entry dict for a URL, or None."""
    return next((e for e in entries if e.get("url") == url), None)


def _refresh_archive_status(entry):
    """Recompute archive_status bits for a URL entry. Bit 0 = locally
    archived (status==archived AND at least one artifact); bit 1 =
    Wayback present (wayback_date set)."""
    has_local = (
        entry.get("status") == "archived"
        and bool(entry.get("artifacts"))
    )
    has_wayback = bool(entry.get("wayback_date"))
    entry["archive_status"] = (1 if has_local else 0) | (2 if has_wayback else 0)


def cmd_add(args):
    """Register URL + path + format. Three cases:

    - URL not in manifest: create a new entry with the artifact.
    - URL exists, path is new to this URL: append a new artifact.
    - URL exists, path matches an existing artifact for this URL:
      idempotent no-op (logs which artifact matched).

    Errors loudly if the supplied path is already registered under a
    DIFFERENT URL (path uniqueness across the manifest).
    """
    entries = load_manifest()
    path = normalize_source_rel_path(args.path) if args.path else None

    # Path uniqueness check: a given file path must belong to exactly
    # one URL. (Same file can't be a rendering of two different URLs.)
    if path:
        for e in entries:
            if e.get("url") == args.url:
                continue
            for a in e.get("artifacts") or []:
                if a.get("path") == path:
                    print(
                        f"ERROR: sources/{path} is already registered under a "
                        f"different URL: {e['url']}",
                        file=sys.stderr,
                    )
                    sys.exit(1)

    entry = _find_entry(entries, args.url)

    if entry is None:
        # Brand-new URL entry.
        entry = {
            "url": args.url,
            "status": "archived" if path else "pending",
        }
        wb_date = wayback_url_date(args.url)
        if wb_date:
            entry["wayback_date"] = wb_date
        if args.wayback_skip:
            entry["wayback_skip"] = True
        if args.note and not path:
            # URL-level note only when no artifact accompanies (pending /
            # blocked entries). When a path is supplied, the note attaches
            # to the artifact below.
            entry["note"] = args.note
        entry["artifacts"] = []
        # Insert at the URL-sorted position so the write touches only this new
        # entry. save_manifest no longer globally re-sorts (that churned
        # unrelated entries on every write); a sorted manifest stays sorted,
        # and a drifted one still gets a clean single-entry diff.
        pos = next((i for i, e in enumerate(entries)
                    if e.get("url", "") > args.url), len(entries))
        entries.insert(pos, entry)
        created_url_entry = True
    else:
        created_url_entry = False

    appended_artifact = None
    if path:
        artifacts = entry.setdefault("artifacts", [])
        existing = next((a for a in artifacts if a.get("path") == path), None)
        if existing:
            print(f"Already in manifest: {args.url}")
            print(f"  artifact path: sources/{path}  format: {existing.get('format')!r}")
            return
        artifact = {
            "format": args.format or format_from_path(path) or "html",
            "path": path,
            "archived_date": args.archived_date or date.today().isoformat(),
        }
        full_path = SOURCES_DIR / path
        if not full_path.exists():
            print(f"WARNING: path does not exist (archival incomplete): "
                  f"sources/{path}", file=sys.stderr)
        if args.extraction_type:
            artifact["extraction_type"] = args.extraction_type
        if args.transcript_provenance:
            artifact["transcript_provenance"] = args.transcript_provenance
        if args.note:
            artifact["note"] = args.note
        artifacts.append(artifact)
        appended_artifact = artifact
        # If the URL was previously pending (no artifacts) and we just
        # archived an artifact, promote status to archived.
        if entry.get("status") != "archived":
            entry["status"] = "archived"

    _refresh_archive_status(entry)

    if getattr(args, "dry_run", False):
        verb = "add new URL entry" if created_url_entry else "append to existing URL"
        print(f"[dry-run] would {verb}: {args.url}")
        if appended_artifact:
            print(f"[dry-run]   artifact: sources/{path}  "
                  f"format: {appended_artifact['format']!r}")
        print("[dry-run] validation OK (URL / path / format / path-uniqueness); "
              "manifest not written")
        return

    save_manifest(entries)

    if created_url_entry and appended_artifact:
        print(f"✓ Added: {args.url}")
        print(f"  artifact: sources/{path}  format: {appended_artifact['format']!r}")
    elif created_url_entry:
        print(f"✓ Added (no artifact): {args.url}")
    elif appended_artifact:
        print(f"✓ Appended artifact to existing URL: {args.url}")
        print(f"  artifact: sources/{path}  format: {appended_artifact['format']!r}")
    print(f"  archive_status: {entry['archive_status']}")
    if entry.get("wayback_date"):
        print(f"  wayback_date:   {entry['wayback_date']}")


def cmd_status(args):
    entries = load_manifest()
    entry = _find_entry(entries, args.url)
    if not entry:
        print(f"Not in manifest: {args.url}")
        sys.exit(1)
    print(yaml.dump(entry, sort_keys=False, default_flow_style=False,
                    allow_unicode=True))


def cmd_pending(args):
    entries = load_manifest()
    pending = [e for e in entries if e.get("status") != "archived"]
    for e in pending:
        status = e.get("status", "?")
        print(f"{status:15}  {e['url']}")
    print(f"\n{len(pending)} pending of {len(entries)} total URLs")


def cmd_usage(args):
    usage = scan_urls_in_nodes()
    citers = usage.get(args.url, set())
    if not citers:
        print(f"No node cites: {args.url}")
        return
    for n in sorted(citers):
        print(f"  {n}")
    print(f"\n{len(citers)} citing node(s)")


def cmd_orphans(args):
    entries = load_manifest()
    usage = scan_urls_in_nodes()
    orphans = [e for e in entries if e["url"] not in usage]
    for e in orphans:
        print(f"  {e['url']}")
    print(f"\n{len(orphans)} manifest entries not cited by any node")


def cmd_missing(args):
    entries = load_manifest()
    manifest_urls = {e["url"] for e in entries}
    usage = scan_urls_in_nodes()
    missing = {u: src for u, src in usage.items() if u not in manifest_urls}
    for url in sorted(missing.keys()):
        print(f"\n  {url}")
        for s in sorted(missing[url]):
            print(f"    <- {s}")
    print(f"\n{len(missing)} URLs cited in nodes not in manifest")


def cmd_summary(args):
    entries = load_manifest()
    by_status = Counter(e.get("status", "?") for e in entries)
    by_format = Counter(a.get("format", "?") for _, a in iter_artifacts(entries))
    n_artifacts = sum(1 for _ in iter_artifacts(entries))
    print(f"Total URLs:      {len(entries)}")
    print(f"Total artifacts: {n_artifacts}")
    print("\nBy URL status:")
    for s, n in by_status.most_common():
        print(f"  {s:25} {n}")
    print("\nBy artifact format:")
    for f, n in by_format.most_common():
        print(f"  {f:25} {n}")


def cmd_verify_paths(args):
    """Confirm every archived artifact's file exists on disk. A missing
    git-TRACKED file is real breakage (exit 1); a missing git-IGNORED file
    (the large sources/video/ media kept out of the remote) is
    expected-absent on a fresh clone — reported, but not a failure."""
    entries = load_manifest()
    missing = []           # git-tracked, absent — real breakage
    expected_absent = []   # git-ignored media, absent — expected on a clone
    for entry, artifact in iter_artifacts(entries):
        path = artifact.get("path")
        if not path or (SOURCES_DIR / path).exists():
            continue
        bucket = expected_absent if is_gitignored(f"sources/{path}") else missing
        bucket.append((entry["url"], path))
    for url, path in missing:
        print(f"  MISSING  sources/{path}")
        print(f"           (for {url})")
    if expected_absent:
        print(f"\n{len(expected_absent)} git-ignored media absent locally "
              f"(expected on a fresh clone; recover via source URL / Wayback)")
    print(f"\n{len(missing)} git-tracked artifacts with missing local files")
    sys.exit(1 if missing else 0)


def cmd_edit(args):
    """Correct a registered artifact in place — target it by ``--path`` and
    set one or more fields. The CLI surface for fixing a mis-registered entry
    without a hand-edit to the manifest YAML (which the build rules discourage).

    - ``--new-path`` renames the registered path (rename the file on disk
      first; uniqueness-checked, warns if the new path is absent on disk).
    - ``--note`` rewrites the artifact's note; ``--format`` /
      ``--extraction-type`` / ``--transcript-provenance`` / ``--archived-date``
      set those fields.

    Only the fields you pass change; everything else is left as-is. Errors if
    the path matches no registered artifact, or if ``--new-path`` collides with
    an already-registered path.
    """
    entries = load_manifest()
    target_rel = normalize_source_rel_path(args.path)

    found = None
    for entry in entries:
        for artifact in entry.get("artifacts") or []:
            if artifact.get("path") == target_rel:
                found = (entry, artifact)
                break
        if found:
            break
    if not found:
        print(f"ERROR: no registered artifact with path: sources/{target_rel}",
              file=sys.stderr)
        sys.exit(1)
    entry, artifact = found

    changes = []  # (field, old, new)
    if args.new_path:
        new_rel = normalize_source_rel_path(args.new_path)
        if new_rel != target_rel:
            for e in entries:
                for a in e.get("artifacts") or []:
                    if a.get("path") == new_rel:
                        print(f"ERROR: target path already registered under "
                              f"{e.get('url')}: sources/{new_rel}",
                              file=sys.stderr)
                        sys.exit(1)
            if not (SOURCES_DIR / new_rel).exists():
                print(f"WARNING: new path does not exist on disk (rename the "
                      f"file first): sources/{new_rel}", file=sys.stderr)
            changes.append(("path", target_rel, new_rel))

    for field in ("format", "extraction_type", "transcript_provenance",
                  "archived_date", "note"):
        val = getattr(args, field)
        if val is not None:
            changes.append((field, artifact.get(field), val))

    if not changes:
        print("Nothing to change — pass at least one of --new-path / --note / "
              "--format / --extraction-type / --transcript-provenance / "
              "--archived-date.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"[dry-run] would edit artifact sources/{target_rel} "
              f"(URL: {entry.get('url')}):")
        for field, old, new in changes:
            print(f"[dry-run]   {field}: {old!r} -> {new!r}")
        print("[dry-run] manifest not written")
        return

    for field, _old, new in changes:
        artifact[field] = new
    save_manifest(entries)

    final_path = next((n for f, _o, n in changes if f == "path"), target_rel)
    print(f"✓ Edited artifact: sources/{final_path} (URL: {entry.get('url')})")
    for field, old, new in changes:
        print(f"  {field}: {old!r} -> {new!r}")


# Sibling-kind table: anchor fragment + which parent artifacts qualify.
# clean-text pairs to an OCR-scan/extraction-lossy PDF; speaker-attribution
# pairs to a label-less transcript (anything but the two labeled classes).
SIBLING_KINDS = {
    "clean-text": {
        "fragment": "clean-text-transcription",
        "gate_field": "extraction_type",
        "gate_ok": lambda v: v in ("ocr-scan", "extraction-lossy"),
        "gate_msg": "parent is not flagged ocr-scan / extraction-lossy",
        "parent_suffixes": (".pdf",),
    },
    "speaker-attribution": {
        "fragment": "speaker-attribution",
        "gate_field": "transcript_provenance",
        "gate_ok": lambda v: v not in ("stenographic", "published-transcript"),
        "gate_msg": "parent is a labeled-class transcript (stenographic / "
                    "published-transcript) — it needs no attribution sibling",
        "parent_suffixes": (".md", ".txt"),
    },
}


def _resolve_parent(entries, kind, parent_url, parent_path):
    """Resolve the parent (entry, artifact) a sibling pairs to. By --parent-path
    when given (paths are manifest-unique); by --parent-url otherwise, picking
    the entry's single kind-eligible artifact — ambiguity is an error directing
    the caller to --parent-path. Erroring when no parent exists is the point:
    the sibling↔parent pairing invariant is checked, not remembered."""
    spec = SIBLING_KINDS[kind]
    if parent_path:
        rel = normalize_source_rel_path(parent_path)
        for e in entries:
            for a in e.get("artifacts") or []:
                if a.get("path") == rel:
                    return e, a
        print(f"ERROR: no registered artifact with path: sources/{rel} — "
              f"a sibling pairs to an already-registered parent (register the "
              f"parent first via `manifest.py add`)", file=sys.stderr)
        sys.exit(1)
    entry = _find_entry(entries, parent_url)
    if entry is None:
        print(f"ERROR: parent URL not in manifest: {parent_url} — a sibling "
              f"pairs to an already-registered parent (register the parent "
              f"first via `manifest.py add`)", file=sys.stderr)
        sys.exit(1)
    candidates = [a for a in entry.get("artifacts") or []
                  if str(a.get("path", "")).endswith(spec["parent_suffixes"])]
    if len(candidates) != 1:
        print(f"ERROR: {parent_url} carries {len(candidates)} artifact(s) "
              f"eligible as a {kind} parent — disambiguate with --parent-path",
              file=sys.stderr)
        sys.exit(1)
    return entry, candidates[0]


def _add_via_cmd_add(url, path, fmt, note, archived_date, dry_run):
    """Register one sibling artifact through cmd_add — the single manifest
    write path (path-uniqueness, sorted insert, archive_status, save)."""
    cmd_add(argparse.Namespace(
        url=url, path=path, format=fmt, note=note,
        extraction_type=None, transcript_provenance=None,
        wayback_skip=True, archived_date=archived_date, dry_run=dry_run))


def cmd_add_sibling(args):
    """Register a derived sibling on the manifest with every mechanical part
    derived instead of hand-composed: the synthetic anchor URL (parent URL +
    kind fragment), wayback_skip, the sibling path(s) from the parent stem
    (speaker-attribution registers the .yaml source-of-truth AND the rendered
    -attributed.md view in one call), formats, archived_date, and the note
    skeleton (the genuinely editorial remainder rides --details verbatim).
    The parent must already be registered (pairing checked, not remembered);
    the sibling file(s) must exist on disk (register at the moment of
    creation — an unregistered sibling is a silent dependency)."""
    kind = args.kind
    spec = SIBLING_KINDS[kind]
    if not args.parent_url and not args.parent_path:
        print("ERROR: pass --parent-path or --parent-url", file=sys.stderr)
        sys.exit(1)
    if kind == "clean-text" and not args.method:
        print("ERROR: clean-text requires --method (VLM page-image read / "
              "Tesseract / cloud-OCR / manual — recording the production "
              "method is deliberate, so there is no default)", file=sys.stderr)
        sys.exit(1)
    if kind == "speaker-attribution" and not args.image_verification:
        print("ERROR: speaker-attribution requires --image-verification "
              "('none (mandatory active-speaker fold gate clean — 0 "
              "contested-fold across N turns)' or 'N turns resolved ...')",
              file=sys.stderr)
        sys.exit(1)

    entries = load_manifest()
    entry, parent = _resolve_parent(entries, kind, args.parent_url,
                                    args.parent_path)
    parent_rel = parent["path"]
    gate_val = parent.get(spec["gate_field"])
    if not spec["gate_ok"](gate_val):
        print(f"WARNING: {spec['gate_msg']} "
              f"({spec['gate_field']}: {gate_val!r} on sources/{parent_rel})",
              file=sys.stderr)

    anchor = f"{entry['url']}#{spec['fragment']}"
    produced = args.produced or date.today().isoformat()
    details = f" {args.details}" if args.details else ""

    if kind == "clean-text":
        sib_rel = str(Path(parent_rel).with_suffix(".txt"))
        blocked = (f"pages content-blocked for the VLM PaddleOCR-filled "
                   f"({args.blocked_pages})" if args.blocked_pages
                   else "zero pages content-blocked")
        note = (f"Clean-text sibling ({args.method}) of the OCR-scanned "
                f"{Path(parent_rel).name} (paired entry; same path stem). "
                f"Produced {produced}; {blocked}.{details}")
        siblings = [(sib_rel, "txt", note)]
    else:
        stem = Path(parent_rel).stem
        parent_dir = Path(parent_rel).parent
        yaml_rel = str(parent_dir / f"{stem}-attribution.yaml")
        md_rel = str(parent_dir / f"{stem}-attributed.md")
        verified = args.verified or date.today().isoformat()
        session = f" (session {args.verify_session})" if args.verify_session else ""
        yaml_note = (f"Speaker-attribution sibling of the label-less transcript "
                     f"at {parent_rel}. Produced {produced} via "
                     f"/prepare-transcript-sibling (agent-based). Verified "
                     f"{verified} by a separate agent session — PASS{session}. "
                     f"Image-verification: {args.image_verification}.{details}")
        md_note = (f"Human-readable rendering of the speaker-attribution "
                   f"sibling ({Path(yaml_rel).name}) over the source caption "
                   f"bytes. Derived view; the YAML is the source-of-truth.")
        siblings = [(yaml_rel, "yaml", yaml_note), (md_rel, "md", md_note)]

    missing = [rel for rel, _f, _n in siblings
               if not (SOURCES_DIR / rel).exists()]
    if missing:
        for rel in missing:
            print(f"ERROR: sibling file not on disk: sources/{rel} — produce "
                  f"it first (register at the moment of creation, not before)",
                  file=sys.stderr)
        sys.exit(1)

    print(f"Derived registration ({kind}):")
    print(f"  anchor URL:    {anchor}")
    print(f"  paired parent: sources/{parent_rel}")
    for rel, fmt, note in siblings:
        print(f"  artifact:      sources/{rel}  format: {fmt!r}")
        print(f"    note: {note}")
    print()
    for rel, fmt, note in siblings:
        _add_via_cmd_add(anchor, rel, fmt, note, produced, args.dry_run)
    if not args.dry_run:
        print(f"\n✓ {kind} sibling registered under {anchor}")


COMMANDS = {
    "add": cmd_add,
    "add-sibling": cmd_add_sibling,
    "edit": cmd_edit,
    "status": cmd_status,
    "pending": cmd_pending,
    "usage": cmd_usage,
    "orphans": cmd_orphans,
    "missing": cmd_missing,
    "summary": cmd_summary,
    "verify-paths": cmd_verify_paths,
}


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("add")
    p.add_argument("url")
    p.add_argument("--path")
    p.add_argument("--format")
    p.add_argument("--note")
    p.add_argument(
        "--extraction-type",
        choices=["text-native", "ocr-scan", "extraction-lossy"],
        help="How the source's text is extracted "
             "(default: text-native; field omitted from entry when default)")
    p.add_argument(
        "--transcript-provenance",
        choices=["stenographic", "published-transcript",
                 "human-corrected-caption", "auto-caption", "unknown"],
        help="How a format=transcript source's text was produced "
             "(default: unknown; field omitted from entry when unset). "
             "See schema.yaml artifact_entry.transcript_provenance_values "
             "for the per-value semantics.")
    p.add_argument(
        "--wayback-skip",
        action="store_true",
        help="Mark the URL entry as ineligible for Wayback submission "
             "(synthetic deep-link URLs that won't resolve at archive time)")
    p.add_argument(
        "--archived-date",
        help="Archival date (YYYY-MM-DD) for the artifact; defaults to today. "
             "Use when the file was downloaded in a prior session so "
             "archived_date isn't conflated with the registration date.")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the add (URL / path / format / path-uniqueness) and "
             "report what would change, without writing the manifest. Lets the "
             "External Investigator self-check a lead before the Archive agent "
             "commits it.")

    p = subparsers.add_parser(
        "add-sibling",
        help="register a derived sibling (clean-text .txt or speaker-"
             "attribution .yaml + rendered .md) with anchor URL, wayback_skip, "
             "paths, and note skeleton derived; parent pairing checked")
    p.add_argument("kind", choices=sorted(SIBLING_KINDS),
                   help="sibling flavor (decides the anchor fragment, derived "
                        "paths, and note template)")
    p.add_argument("--parent-path",
                   help="registered path of the parent artifact the sibling "
                        "pairs to (paths are manifest-unique)")
    p.add_argument("--parent-url",
                   help="parent entry URL (works when it has exactly one "
                        "kind-eligible artifact; otherwise use --parent-path)")
    p.add_argument("--produced",
                   help="date the sibling was produced (YYYY-MM-DD; default "
                        "today) — also the artifacts' archived_date")
    p.add_argument("--method",
                   help="(clean-text, required) production method for the note "
                        "— e.g. 'VLM page-image read, confirmed against "
                        "PaddleOCR + Tesseract', 'Tesseract 5, contributor-"
                        "reviewed', 'manual transcription'")
    p.add_argument("--blocked-pages",
                   help="(clean-text) content-blocked pages PaddleOCR-filled, "
                        "as prose for the note (e.g. '9-11, 29-30'); omit when "
                        "zero pages blocked")
    p.add_argument("--verified",
                   help="(speaker-attribution) independent-verification date "
                        "(YYYY-MM-DD; default today)")
    p.add_argument("--verify-session",
                   help="(speaker-attribution) verifier session id recorded in "
                        "the note")
    p.add_argument("--image-verification",
                   help="(speaker-attribution, required) fold-gate outcome for "
                        "the note — 'none (mandatory active-speaker fold gate "
                        "clean — 0 contested-fold across N turns)' or 'N turns "
                        "resolved against photo-identity-log baselines'")
    p.add_argument("--details",
                   help="editorial remainder appended verbatim to the note "
                        "(preserved typos, redaction handling, FOIA inserts, "
                        "draft/iteration specifics)")
    p.add_argument("--dry-run", action="store_true",
                   help="validate + report the derived entry without writing "
                        "the manifest")

    p = subparsers.add_parser(
        "edit",
        help="correct a registered artifact in place (target by --path); set a "
             "field, rewrite the note, or --new-path to rename the registered path")
    p.add_argument("--path", required=True,
                   help="path of the registered artifact to edit "
                        "(paths are unique across the manifest)")
    p.add_argument("--new-path",
                   help="rename the registered path (rename the file on disk first)")
    p.add_argument("--note", help="rewrite the artifact's note")
    p.add_argument("--format")
    p.add_argument(
        "--extraction-type",
        choices=["text-native", "ocr-scan", "extraction-lossy"])
    p.add_argument(
        "--transcript-provenance",
        choices=["stenographic", "published-transcript",
                 "human-corrected-caption", "auto-caption", "unknown"])
    p.add_argument("--archived-date",
                   help="set the artifact's archived_date (YYYY-MM-DD)")
    p.add_argument("--dry-run", action="store_true",
                   help="report what would change without writing the manifest")

    p = subparsers.add_parser("status")
    p.add_argument("url")

    subparsers.add_parser("pending")

    p = subparsers.add_parser("usage")
    p.add_argument("url")

    subparsers.add_parser("orphans")
    subparsers.add_parser("missing")
    subparsers.add_parser("summary")
    subparsers.add_parser("verify-paths")

    args = parser.parse_args()
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
