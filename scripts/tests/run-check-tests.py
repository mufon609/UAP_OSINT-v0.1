#!/usr/bin/env python3
"""Per-check unit-test runner — discovers and runs every test module
under ``scripts/tests/check_tests/``.

Test modules are plain Python files matching ``*_test.py`` that export
top-level ``test_*`` functions. Each function asserts an invariant
about a single check — typically that the check fires the expected
Issue on a synthetic broken-input fixture, and stays silent on a clean
fixture. Fixtures come from ``check_tests/_fixtures.py``.

Closes the gap left by the corpus pre-commit gate: that gate verifies
the happy path (live corpus → 0/0), this gate verifies error paths
(synthetic broken input → expected Issue). A logic bug in a check that
fires only on broken inputs would slip past the corpus pass; this
runner catches that class of regression.

No pytest dependency — keeps the gate chain free of external Python
deps. Per-test signature: any ``test_*`` function returning normally
counts as pass; any uncaught exception (typically AssertionError)
counts as fail. Failures print the traceback for fast diagnosis.

Wired into ``scripts/tests/pre-commit.sh`` as a gate after smoke and
before the orchestrator gates.
"""

import importlib.util
import sys
import traceback
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEST_DIR = Path(__file__).resolve().parent / "check_tests"


def discover_test_files():
    if not TEST_DIR.is_dir():
        return []
    return sorted(TEST_DIR.glob("*_test.py"))


def load_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def collect_test_functions(mod):
    for name in sorted(dir(mod)):
        if not name.startswith("test_"):
            continue
        fn = getattr(mod, name)
        if callable(fn):
            yield name, fn


def main():
    # ``scripts/`` on sys.path so test modules can ``from checks import {name}``;
    # ``check_tests/`` on sys.path so test modules can ``from _fixtures import ...``.
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    sys.path.insert(0, str(TEST_DIR))

    print("=" * 70)
    print(" Per-check unit tests")
    print("=" * 70)
    print()

    test_files = discover_test_files()
    if not test_files:
        print("  No test files under scripts/tests/check_tests/")
        return 0

    passed = 0
    failed = []

    for tf in test_files:
        try:
            mod = load_module(tf)
        except Exception:
            failed.append((tf.stem, "<module-load>", traceback.format_exc()))
            continue
        for name, fn in collect_test_functions(mod):
            try:
                fn()
                passed += 1
            except Exception:
                failed.append((tf.stem, name, traceback.format_exc()))

    total = passed + len(failed)
    print(f"  Passed: {passed}")
    print(f"  Failed: {len(failed)}")
    print(f"  Total:  {total} across {len(test_files)} module(s)")

    if failed:
        print()
        print("Failures:")
        for mod_name, test_name, tb in failed:
            print()
            print(f"  ── {mod_name}::{test_name} ──")
            for line in tb.rstrip().splitlines():
                print(f"  {line}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
