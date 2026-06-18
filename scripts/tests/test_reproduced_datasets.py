#!/usr/bin/env python3
"""Regression guard for the reproduced-datasets check
(`scripts/checks/reproduced_datasets.py`).

The optional ``reproduced_datasets`` field attaches a bulk table the source
reproduces wholesale (an appendix case index, a frequency table) to a node as a
queryable CSV "data sibling" + the ``## Reproduced Datasets`` section, rather
than exploding its rows into per-row entity links. The check is silent when the
field is absent (optional during rollout); when present it enforces per entry:
shape + required fields + id uniqueness, ``source.path`` registered in the
manifest, and the ``dataset_path`` CSV registered + present on disk + parseable
(``row_count`` matched when given). See
``schema-research-artifact.yaml::optional_keys.reproduced_datasets``.
"""

import csv
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from checks import reproduced_datasets


# Point the check's SOURCES_DIR at a temp dir holding a known CSV so the
# on-disk + row_count branches are exercised without touching the real tree.
_TMP = Path(tempfile.mkdtemp(prefix="test-reproduced-datasets-"))
with (_TMP / "good.csv").open("w", newline="") as _f:
    _w = csv.writer(_f)
    _w.writerow(["case_no", "place"])      # header
    _w.writerow(["1", "WORCESTER CAPE"])    # data row 1
    _w.writerow(["2", "SYDNEY"])            # data row 2
reproduced_datasets.SOURCES_DIR = _TMP

# A manifest stub registering the parent source + the CSV sibling. iter_artifacts
# walks entries[].artifacts[].path.
MANIFEST = [{"artifacts": [{"path": "src.pdf"}, {"path": "good.csv"}]}]


class _Ctx:
    def __init__(self, data, manifest_entries=None):
        self.rel = "test"
        self.data = data
        self.manifest_entries = manifest_entries if manifest_entries is not None else MANIFEST


def _msgs(data, manifest_entries=None):
    return [i.message for i in reproduced_datasets.check(_Ctx(data, manifest_entries))]


def _has(msgs, needle):
    return any(needle in m for m in msgs)


def _entry(**over):
    e = {
        "id": "d1",
        "title": "Appendix B — Case Index",
        "description": "A reproduced case index.",
        "dataset_path": "good.csv",
        "source": {"path": "src.pdf", "location": "Appendix B"},
        "row_count": 2,
    }
    e.update(over)
    return e


CASES = []


def record(label, ok, detail=""):
    CASES.append((label, ok, detail))


def run():
    # absent field — optional during rollout, check is silent
    record("silent when field absent", not _msgs({"description": "no field"}))

    # well-formed, registered, on-disk, row_count matches → clean
    clean = {"reproduced_datasets": [_entry()]}
    record("clean on well-formed registered present entry", not _msgs(clean), repr(_msgs(clean)))

    # non-list value → ERROR
    record("fires on non-list value",
           _has(_msgs({"reproduced_datasets": "NONE"}), "must be a list"))

    # entry not a mapping → ERROR
    record("fires on non-mapping entry",
           _has(_msgs({"reproduced_datasets": ["x"]}), "not a mapping"))

    # missing required field (title) → ERROR
    m = _msgs({"reproduced_datasets": [_entry(title=None)]})
    record("fires on missing required field", _has(m, "missing required field 'title'"))

    # duplicate id → ERROR
    m = _msgs({"reproduced_datasets": [_entry(), _entry()]})
    record("fires on duplicate id", _has(m, "duplicate id"))

    # source not a mapping → ERROR
    m = _msgs({"reproduced_datasets": [_entry(source="src.pdf")]})
    record("fires on non-mapping source", _has(m, "source must be a mapping"))

    # source.path not registered → ERROR (empty manifest)
    m = _msgs({"reproduced_datasets": [_entry()]}, manifest_entries=[])
    record("fires on unregistered source.path", _has(m, "not "
           "registered in sources/manifest.yaml"))

    # dataset_path not registered → ERROR
    m = _msgs({"reproduced_datasets": [_entry(dataset_path="missing.csv")]})
    record("fires on unregistered dataset_path",
           _has(m, "missing.csv") and _has(m, "not registered"))

    # dataset_path registered but absent on disk → ERROR
    nodisk_manifest = [{"artifacts": [{"path": "src.pdf"}, {"path": "ghost.csv"}]}]
    m = _msgs({"reproduced_datasets": [_entry(dataset_path="ghost.csv")]}, nodisk_manifest)
    record("fires on dataset_path missing on disk", _has(m, "not found on disk"))

    # row_count mismatch → ERROR
    m = _msgs({"reproduced_datasets": [_entry(row_count=5)]})
    record("fires on row_count mismatch",
           _has(m, "row_count 5 does not match") and _has(m, "2 data row"))


def main():
    print("=" * 70)
    print(" reproduced-datasets regression test")
    print("=" * 70)
    print()
    run()
    failures = [(label, detail) for label, ok, detail in CASES if not ok]
    if failures:
        print(f"  FAILED — {len(failures)}/{len(CASES)} case(s):")
        for label, detail in failures:
            print(f"    - {label}  {detail}")
        return 1
    print(f"  PASSED — {len(CASES)} cases (silent-absent; shape + manifest/CSV presence fire)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
