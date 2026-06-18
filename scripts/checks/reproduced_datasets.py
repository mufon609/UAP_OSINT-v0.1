"""reproduced-datasets check — ResearchContext check (every artifact type).

Validates the optional ``reproduced_datasets`` field: bulk tabular data a
primary source reproduces wholesale (an appendix case index, a frequency
table, any reproduced catalog), captured as a queryable CSV "data sibling"
under ``sources/`` and surfaced as the ``## Reproduced Datasets`` section
rather than exploded into per-row entity links. See
``schema-research-artifact.yaml::optional_keys.reproduced_datasets`` and the
``reproduced_dataset_entry`` shape.

Optional / absence-silent (like ``associated_entities`` during the rollout).
When the field IS present this check enforces, per entry:

  1. Shape — a mapping carrying the required keys (id, title, description,
     dataset_path, source{path, location}); ids unique within the list.
  2. Source registered — ``source.path`` is a real entry in
     ``sources/manifest.yaml`` (the dataset is anchored in an archived
     source, the same invariant ``quotes[].source`` / ``cited_work.source``
     carry).
  3. Sibling registered + present + parseable — ``dataset_path`` is a
     registered manifest artifact, exists on disk under ``sources/``, and
     parses as CSV; when ``row_count`` is given it matches the CSV's
     data-row count (a transcription guard).

Phase: link — a back-matter structured field + cross-reference, alongside
``associated_entities``.

Severity: error — a declared reproduced dataset whose CSV is missing,
unregistered, or row-count-mismatched is a broken back-matter link, the
same class of defect a dangling ``source.path`` is. The field is optional,
so nothing legitimate is blocked — a node simply omits it.
"""

import csv

from checks import Issue
from lib._common import SOURCES_DIR, iter_artifacts


CHECK_NAME = "reproduced_datasets"

_REQUIRED = ("id", "title", "description", "dataset_path", "source")


def check(ctx):
    value = ctx.data.get("reproduced_datasets")
    if value is None:
        return  # optional; absence is silent (rollout)
    if not isinstance(value, list):
        yield Issue(
            ctx.rel, "error",
            f"reproduced_datasets must be a list of reproduced_dataset_entry; "
            f"got {type(value).__name__}",
            check_name=CHECK_NAME,
        )
        return

    registered_paths = {
        artifact.get("path")
        for _, artifact in iter_artifacts(ctx.manifest_entries)
    }

    seen_ids = set()
    for i, entry in enumerate(value):
        if not isinstance(entry, dict):
            yield Issue(
                ctx.rel, "error",
                f"reproduced_datasets[{i}]: not a mapping",
                check_name=CHECK_NAME,
            )
            continue

        for key in _REQUIRED:
            if not entry.get(key):
                yield Issue(
                    ctx.rel, "error",
                    f"reproduced_datasets[{i}]: missing required field {key!r}",
                    check_name=CHECK_NAME,
                )

        eid = entry.get("id")
        if eid:
            if eid in seen_ids:
                yield Issue(
                    ctx.rel, "error",
                    f"reproduced_datasets[{i}]: duplicate id {eid!r} "
                    f"(ids are unique within the list)",
                    check_name=CHECK_NAME,
                )
            seen_ids.add(eid)

        src = entry.get("source")
        if isinstance(src, dict):
            spath = src.get("path")
            if not spath:
                yield Issue(
                    ctx.rel, "error",
                    f"reproduced_datasets[{i}]: source.path is required",
                    check_name=CHECK_NAME,
                )
            elif spath not in registered_paths:
                yield Issue(
                    ctx.rel, "error",
                    f"reproduced_datasets[{i}]: source.path {spath!r} is not "
                    f"registered in sources/manifest.yaml",
                    check_name=CHECK_NAME,
                )
        elif "source" in entry:
            yield Issue(
                ctx.rel, "error",
                f"reproduced_datasets[{i}]: source must be a mapping with "
                f"path + location",
                check_name=CHECK_NAME,
            )

        dpath = entry.get("dataset_path")
        if not dpath:
            continue  # required-field error already emitted

        if dpath not in registered_paths:
            yield Issue(
                ctx.rel, "error",
                f"reproduced_datasets[{i}]: dataset_path {dpath!r} is not "
                f"registered in sources/manifest.yaml — register the CSV data "
                f"sibling (format: csv)",
                check_name=CHECK_NAME,
            )

        csv_file = SOURCES_DIR / dpath
        if not csv_file.exists():
            yield Issue(
                ctx.rel, "error",
                f"reproduced_datasets[{i}]: dataset_path {dpath!r} not found "
                f"on disk under sources/ — produce the CSV data sibling",
                check_name=CHECK_NAME,
            )
            continue

        try:
            with csv_file.open(newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
        except (OSError, csv.Error, UnicodeDecodeError) as e:
            yield Issue(
                ctx.rel, "error",
                f"reproduced_datasets[{i}]: dataset_path {dpath!r} did not "
                f"parse as CSV: {e}",
                check_name=CHECK_NAME,
            )
            continue

        data_rows = max(len(rows) - 1, 0)  # minus the header row
        rc = entry.get("row_count")
        if rc is not None and rc != data_rows:
            yield Issue(
                ctx.rel, "error",
                f"reproduced_datasets[{i}]: row_count {rc} does not match the "
                f"CSV's {data_rows} data row(s) in {dpath!r}",
                check_name=CHECK_NAME,
            )
