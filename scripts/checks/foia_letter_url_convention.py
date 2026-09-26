"""foia-letter-url-convention check — global BaseContext check.

Enforces the letter-URL convention (`sources/README.md` §3, "Request
correspondence") for a FOIA/MDR letter that has no public URL of its
own (no reading-room page, agency portal case page, MuckRock or Black
Vault mirror): its manifest entry's ``url`` is a synthetic anchor of the
form

    {agency FOIA office public URL}#foia/{foia-node-slug}/{YYYY-MM-DD}/{letter-type}

and the original file lives at
``sources/foia/{foia-node-slug}/{YYYY-MM-DD}-{letter-type}.{ext}`` — the
one deliberate exception to the flat one-click-per-category rule
(`sources/README.md` §1), since the synthetic URL carries no natural
path of its own the way a real reading-room URL would.

A letter registered under a real public URL (no ``#foia/`` fragment)
isn't gated by this convention at all — it follows the ordinary flat
``sources/foia/`` placement like any other source.

For every manifest artifact under ``sources/foia/`` whose URL carries a
``#foia/`` fragment:

  - ``wayback_skip`` must be ``true`` — a synthetic anchor URL never
    resolves at archive time, the same rationale as a derived sibling's
    anchor URL.
  - the fragment must parse as ``#foia/{slug}/{YYYY-MM-DD}/{letter-type}``.
  - the fragment's ``{slug}`` must match the artifact's own directory
    (``sources/foia/{slug}/...``) — the one piece of information the
    convention duplicates between the URL and the path, so a copy-paste
    across two different FOIA nodes' letters doesn't go undetected.

Does not cross-check the fragment's ``{YYYY-MM-DD}-{letter-type}``
against the artifact's filename, or the ``{letter-type}`` token against
``correspondence_entry.letter_type_values`` — the research artifact's own
``correspondence[]`` entry (validated by ``scripts/checks/correspondence.py``)
is the source of truth for date and letter_type; this check only guards
the two structural invariants (skip flag + slug) that would otherwise
silently drift.

Dispatched from validate.py's manifest-integrity preflight family
(alongside manifest_artifact_shape) — see scripts/checks/_phases.py
(archive phase).
"""

import re

from checks import Issue
from lib._common import iter_artifacts


CHECK_NAME = "foia_letter_url_convention"
MANIFEST_REL = "sources/manifest.yaml"

_FRAGMENT_RE = re.compile(r"#foia/([^/#]+)/(\d{4}-\d{2}-\d{2})/([a-z0-9-]+)$")


def check(ctx):
    for entry, artifact in iter_artifacts(ctx.manifest_entries):
        path = artifact.get("path") or ""
        if not path.startswith("foia/"):
            continue

        url = entry.get("url") or ""
        if "#foia/" not in url:
            continue  # a real public URL — the synthetic-anchor convention doesn't apply

        if not entry.get("wayback_skip"):
            yield Issue(
                MANIFEST_REL, "error",
                f"sources/{path}: URL carries a synthetic '#foia/' anchor "
                f"({url!r}) but wayback_skip is not set — a synthetic FOIA "
                f"letter anchor never resolves at archive time",
                check_name=CHECK_NAME,
            )

        m = _FRAGMENT_RE.search(url)
        if not m:
            yield Issue(
                MANIFEST_REL, "error",
                f"sources/{path}: '#foia/' anchor {url!r} doesn't match the "
                f"'#foia/{{foia-node-slug}}/{{YYYY-MM-DD}}/{{letter-type}}' "
                f"convention (sources/README.md §3)",
                check_name=CHECK_NAME,
            )
            continue

        frag_slug = m.group(1)
        dir_parts = path.split("/")
        dir_slug = dir_parts[1] if len(dir_parts) >= 3 else None
        if dir_slug != frag_slug:
            yield Issue(
                MANIFEST_REL, "error",
                f"sources/{path}: anchor slug {frag_slug!r} doesn't match "
                f"the artifact's own directory ({dir_slug!r}) — a "
                f"synthetic-URL letter must live under "
                f"sources/foia/{frag_slug}/",
                check_name=CHECK_NAME,
            )
