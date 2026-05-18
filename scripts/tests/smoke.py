#!/usr/bin/env python3
"""Fixture-based smoke tests — single-process, parallel.

For every node-type + archetype / kind combination, scaffold via
``new.py``, validate via ``validate.py``, and (for types whose
renderer ships) scaffold a research artifact + run
``validate-research``, ``build-from-research``, ``review-coverage``.
Each step is a fixture pass/fail; failures surface with the source
error message in the summary.

Catches regressions in:
  - ``new.py`` scaffolding (template rendering, conditional-block
    filtering by --archetype / --kind, placeholder substitution)
  - ``meta/templates/*.md`` body content (the governance-files check
    catches template frontmatter drift; only this test catches
    body-section drift)
  - ``validate.py``'s required-section / archetype-conditional /
    kind-conditional enforcement
  - ``research-scaffold.py`` + ``validate-research.py`` on empty-
    content artifacts; ``build-from-research.py`` + ``review-
    coverage.py`` for the types whose renderer ships

Architecture — three optimizations against per-fixture subprocess cost:

  * Modules imported once via ``importlib.util``; forked workers
    inherit the parent's loaded state. No python3 cold start per
    fixture.
  * Manifest YAML parsed once at startup; ``load_manifest`` rebound
    on ``lib._common`` so every consumer hits the cached value.
  * Manifest-integrity + governance-file checks no-op'd for the
    smoke path — they walk the whole manifest / all governance
    files and their results don't depend on the individual fixture.
    The full-corpus ``validate.py`` pre-commit gate runs them once
    against real state.

Concurrency: ``ProcessPoolExecutor`` with the ``fork`` mp_context.
Workers inherit the parent's pre-loaded modules, caches, and the
check no-ops. Three phases sequence by data dependency:

  Phase 1 — 21 independent scaffolds (no inter-deps)
  Phase 2 — 2 dependent scaffolds (transcript-other → doc-gov;
            media-deriv → media-video)
  Phase 3 — 14 research-artifact pipelines (independent per artifact)

Cleanup is pattern-based on the ``__smoke-*`` slug convention. Fires
at startup (clears debris from a prior crashed run) and on exit.

Exits 0 on all-green; 1 otherwise.
"""

import importlib.util
import multiprocessing as mp
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
os.chdir(REPO_ROOT)
# ``scripts/`` enables ``from lib._common``, ``from checks`` (used by
# every build script). ``scripts/build/`` enables ``from renderers.X``
# (used by build-from-research.py) — when each build script runs as
# ``python3 scripts/build/foo.py``, Python auto-inserts the script's
# directory at sys.path[0]; ``importlib.util.spec_from_file_location``
# does not do that, so we set it explicitly.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "build"))

# ── Pre-load schema + manifest into the lib._common cache ──────────────
# Children forked from this process inherit the cached state, so each
# worker pays the load cost zero additional times.

from lib import _common
from lib._common import MANIFEST_PATH, strict_yaml_load

_common.load_schema()
with open(MANIFEST_PATH) as f:
    _MANIFEST = strict_yaml_load(f) or []
_common.load_manifest = lambda: _MANIFEST
_common.load_manifest_paths = lambda: {
    e.get("path") for e in _MANIFEST if e.get("path")
}

# ── No-op manifest integrity + governance checks for the smoke run ─────
# These walk the whole manifest / all governance files; their results
# don't depend on the individual fixture being validated. The full-
# corpus ``validate.py`` pre-commit gate covers them.

from checks import (
    manifest_checksums,
    manifest_archive_status,
    manifest_extraction_type,
    manifest_value_enums,
    governance_files,
)

def _noop_check(ctx):
    return iter([])

for _check_mod in (
    manifest_checksums,
    manifest_archive_status,
    manifest_extraction_type,
    manifest_value_enums,
    governance_files,
):
    _check_mod.check = _noop_check

# ── Load each build script as a module ─────────────────────────────────

def _load_module(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, str(REPO_ROOT / rel_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MODULES = {
    "new": _load_module("new_module", "scripts/build/new.py"),
    "validate": _load_module("validate_module", "scripts/build/validate.py"),
    "research-scaffold": _load_module("research_scaffold_module", "scripts/build/research-scaffold.py"),
    "validate-research": _load_module("validate_research_module", "scripts/build/validate-research.py"),
    "build-from-research": _load_module("build_from_research_module", "scripts/build/build-from-research.py"),
    "review-coverage": _load_module("review_coverage_module", "scripts/build/review-coverage.py"),
}


def _call_main(name: str, argv: list) -> tuple:
    """Call ``_MODULES[name].main()`` with the given argv. Returns
    ``(rc, stdout, stderr)``. ``main()`` typically calls sys.exit;
    a 0-or-None code is treated as success.

    Both Python-level (``sys.stdout``/``sys.stderr`` → StringIO) and
    fd-level (fd 1 / fd 2 → /dev/null) redirection. ``build-from-
    research.py`` shells out to ``associate.py`` (and to validator
    scripts) via ``subprocess.run``; subprocesses inherit fd 1 / fd 2,
    not Python's ``sys.stdout``. Without fd-level redirect, those
    prints bleed through to the harness output. We don't act on
    subprocess stdout (the captured-output subprocesses keep theirs
    in-memory; ``run_associate`` output is purely cosmetic), so
    /dev/null is fine."""
    mod = _MODULES[name]
    old_argv = sys.argv
    sys.argv = [name + ".py"] + list(argv)
    out_buf, err_buf = StringIO(), StringIO()
    rc = 0

    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    saved_stdout_fd = os.dup(1)
    saved_stderr_fd = os.dup(2)
    try:
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            try:
                mod.main()
            except SystemExit as e:
                if isinstance(e.code, int):
                    rc = e.code
                elif e.code is None:
                    rc = 0
                else:
                    # Non-int code is the error message itself
                    # (``sys.exit("msg")`` pattern). Python's auto-
                    # print only fires when SystemExit propagates
                    # uncaught; we caught it, so route the message
                    # to err_buf so the failure summary surfaces it.
                    rc = 1
                    err_buf.write(str(e.code))
                    if not err_buf.getvalue().endswith("\n"):
                        err_buf.write("\n")
    finally:
        os.dup2(saved_stdout_fd, 1)
        os.dup2(saved_stderr_fd, 2)
        os.close(saved_stdout_fd)
        os.close(saved_stderr_fd)
        os.close(devnull_fd)
        sys.argv = old_argv
    return rc, out_buf.getvalue(), err_buf.getvalue()


# ── Fixture-cleanup discipline ─────────────────────────────────────────

_FIXTURE_GLOBS = [
    "people/__smoke-*.md",
    "organizations/__smoke-*.md",
    "documents/__smoke-*.md",
    "events/__smoke-*.md",
    "transcripts/__smoke-*.md",
    "media/__smoke-*.md",
    "locations/__smoke-*.md",
    "findings/__smoke-*.md",
    "investigations/__smoke-*.md",
    "meta/research/__smoke-*.yaml",
]


def cleanup_fixtures():
    for pattern in _FIXTURE_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


# ── Result type + per-job runners ──────────────────────────────────────

@dataclass
class Result:
    label: str
    ok: bool
    message: Optional[str] = None


def _parse_created_path(out: str) -> Optional[str]:
    """``new.py`` and ``research-scaffold.py`` both print a first
    line of the form ``✓ Created {path}``. Pull the path from there."""
    for line in out.splitlines():
        if line.startswith("✓ Created "):
            return line[len("✓ Created "):].strip()
    return None


def _err_summary(out: str, err: str, max_lines: int = 2) -> str:
    """Pull the first few ERROR lines from validator output for the
    failure message, or fall back to first non-empty line of stdout
    / stderr."""
    errors = [l for l in (out + err).splitlines() if "ERROR" in l]
    if errors:
        return "; ".join(errors[:max_lines])
    for stream in (out, err):
        for line in stream.splitlines():
            if line.strip():
                return line.strip()
    return "(no output)"


def run_scaffold(label: str, args: list) -> list:
    """Scaffold a fixture node + validate it. Returns one Result."""
    rc, out, err = _call_main("new", args)
    if rc != 0:
        return [Result(label, False, f"scaffold failed (rc={rc}): {_err_summary(out, err)}")]
    file_path = _parse_created_path(out)
    if not file_path:
        return [Result(label, False, "couldn't parse scaffold path from new.py output")]
    rc, out, err = _call_main("validate", [file_path, "--quiet"])
    if rc != 0:
        return [Result(label, False, f"validate.py failed: {_err_summary(out, err)}")]
    return [Result(label, True)]


def run_research(label: str, target: str, steps: tuple) -> list:
    """Scaffold a research artifact + validate-research. Optionally
    also run build-from-research and/or review-coverage. Each step
    is its own Result."""
    results: list = []
    slug = target.rsplit("/", 1)[-1]
    artifact = f"meta/research/{slug}.yaml"

    rc, out, err = _call_main("research-scaffold", ["--target", target])
    if rc != 0:
        results.append(Result(f"{label} scaffold", False,
                              f"research-scaffold failed (rc={rc}): {_err_summary(out, err)}"))
        return results
    results.append(Result(f"{label} scaffold", True))

    rc, out, err = _call_main("validate-research", [artifact, "--quiet"])
    if rc != 0:
        results.append(Result(f"{label} validate-research", False,
                              f"validate-research failed: {_err_summary(out, err)}"))
        return results
    results.append(Result(f"{label} validate-research", True))

    if "build" in steps:
        rc, out, err = _call_main("build-from-research", [artifact])
        if rc != 0:
            results.append(Result(f"{label} build-from-research", False,
                                  f"build-from-research failed: {_err_summary(out, err)}"))
            return results
        results.append(Result(f"{label} build-from-research", True))

    if "coverage" in steps:
        rc, out, err = _call_main("review-coverage", [artifact])
        if rc != 0:
            results.append(Result(f"{label} review-coverage", False,
                                  f"review-coverage failed: {_err_summary(out, err)}"))
            return results
        results.append(Result(f"{label} review-coverage", True))

    return results


# ── Fixture catalogues ─────────────────────────────────────────────────

# Phase 1 — independent scaffolds. (label, args) tuples.
PHASE1_SCAFFOLDS = [
    ("person eyewitness",          ["person", "--archetype", "eyewitness",          "--slug", "__smoke-person-eyewitness"]),
    ("person whistleblower",       ["person", "--archetype", "whistleblower",       "--slug", "__smoke-person-whistleblower"]),
    ("person institutional-actor", ["person", "--archetype", "institutional-actor", "--slug", "__smoke-person-iact"]),
    ("person reporter",            ["person", "--archetype", "reporter",            "--slug", "__smoke-person-reporter"]),
    ("org gov",                    ["organization", "--kind", "gov",                "--slug", "__smoke-org-gov"]),
    ("org gov-contractor",         ["organization", "--kind", "gov-contractor",     "--slug", "__smoke-org-contractor"]),
    ("org private",                ["organization", "--kind", "private",            "--slug", "__smoke-org-private"]),
    ("document gov-doc",           ["document", "--kind", "gov-doc",     "--form", "testimony",   "--slug", "__smoke-doc-gov"]),
    ("document non-gov-doc",       ["document", "--kind", "non-gov-doc", "--form", "article",     "--slug", "__smoke-doc-non-gov"]),
    ("document book",              ["document", "--kind", "non-gov-doc", "--form", "book", "--archival-status", "excerpts-only", "--slug", "__smoke-doc-book"]),
    ("document social-post",       ["document", "--kind", "non-gov-doc", "--form", "social-post", "--slug", "__smoke-doc-social"]),
    ("event hearing",              ["event", "--kind", "hearing",   "--slug", "__smoke-event-hearing"]),
    ("event encounter",            ["event", "--kind", "encounter", "--slug", "__smoke-event-encounter"]),
    ("transcript hearing",         ["transcript", "--kind", "hearing", "--slug", "__smoke-trans-hearing"]),
    ("media photo",                ["media", "--kind", "photo",         "--slug", "__smoke-media-photo"]),
    ("media video",                ["media", "--kind", "video",         "--slug", "__smoke-media-video"]),
    ("media audio",                ["media", "--kind", "audio",         "--slug", "__smoke-media-audio"]),
    ("media imagery-other",        ["media", "--kind", "imagery-other", "--slug", "__smoke-media-imagery"]),
    ("location",                   ["location",      "--slug", "__smoke-location"]),
    ("finding",                    ["finding",       "--slug", "__smoke-finding"]),
    ("investigation",              ["investigation", "--slug", "__smoke-investigation", "--question", "Does the test question resolve?"]),
]

# Phase 2 — scaffolds that reference Phase 1 outputs. transcript-other
# uses --derived-from /documents/__smoke-doc-gov; media-deriv uses
# --derivation-of /media/__smoke-media-video.
PHASE2_SCAFFOLDS = [
    ("transcript other", [
        "transcript", "--kind", "other", "--source-medium", "podcast",
        "--derived-from", "/documents/__smoke-doc-gov",
        "--slug", "__smoke-trans-other",
    ]),
    ("media derivative", [
        "media", "--kind", "video",
        "--derivation-of", "/media/__smoke-media-video",
        "--slug", "__smoke-media-deriv",
    ]),
]

# Phase 3 — research-artifact pipelines. ``steps`` declares which of
# {build, coverage} run after validate-research; validate-research
# always runs. ``build`` + ``coverage`` apply to types whose renderer
# ships; ``coverage`` is reserved for entity-node types (skipped on
# finding / investigation per Phase III dispatch).
PHASE3_RESEARCH = [
    ("doc-gov",        "documents/__smoke-doc-gov",                ()),
    ("media-photo",    "media/__smoke-media-photo",                ("build", "coverage")),
    ("media-video",    "media/__smoke-media-video",                ("build", "coverage")),
    ("media-audio",    "media/__smoke-media-audio",                ("build", "coverage")),
    ("media-imagery",  "media/__smoke-media-imagery",              ("build", "coverage")),
    ("media-deriv",    "media/__smoke-media-deriv",                ("build", "coverage")),
    ("trans-hearing",  "transcripts/__smoke-trans-hearing",        ()),
    ("trans-other",    "transcripts/__smoke-trans-other",          ()),
    ("location",       "locations/__smoke-location",               ("build", "coverage")),
    ("org-gov",        "organizations/__smoke-org-gov",            ("build", "coverage")),
    ("org-contractor", "organizations/__smoke-org-contractor",     ("build", "coverage")),
    ("org-private",    "organizations/__smoke-org-private",        ("build", "coverage")),
    ("finding",        "findings/__smoke-finding",                 ("build",)),
    ("investigation",  "investigations/__smoke-investigation",     ("build",)),
]


# ── Orchestration ──────────────────────────────────────────────────────

def _run_phase(executor, jobs) -> list:
    """Submit every (fn, *args) tuple in ``jobs`` to ``executor`` and
    collect Results from each completed future. Each job's callable
    returns a list[Result]; phase results flatten."""
    futures = [executor.submit(fn, *args) for fn, *args in jobs]
    out: list = []
    for f in as_completed(futures):
        out.extend(f.result())
    return out


def main() -> int:
    cleanup_fixtures()

    ctx = mp.get_context("fork")
    # nproc = 4 on the dev machine; ProcessPoolExecutor defaults to
    # os.cpu_count(). max_workers explicit for predictable behavior
    # across machines.
    workers = os.cpu_count() or 4

    all_results: list = []
    try:
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as exe:
            phase1_jobs = [(run_scaffold, label, args) for label, args in PHASE1_SCAFFOLDS]
            all_results.extend(_run_phase(exe, phase1_jobs))

            phase2_jobs = [(run_scaffold, label, args) for label, args in PHASE2_SCAFFOLDS]
            all_results.extend(_run_phase(exe, phase2_jobs))

            phase3_jobs = [(run_research, label, target, steps)
                           for label, target, steps in PHASE3_RESEARCH]
            all_results.extend(_run_phase(exe, phase3_jobs))
    finally:
        cleanup_fixtures()

    passed = sum(1 for r in all_results if r.ok)
    failed = [r for r in all_results if not r.ok]

    print("=" * 70)
    print(" Fixture smoke tests")
    print("=" * 70)
    print()
    print(f"  Passed: {passed}")
    print(f"  Failed: {len(failed)}")

    if failed:
        print()
        print("Failures:")
        for r in failed:
            print(f"  - {r.label} — {r.message}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
