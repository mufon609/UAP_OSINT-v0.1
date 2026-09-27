"""Shared scanner for the prose-entry-ID checks (private to checks/).

Research-artifact prose must name the SOURCE — document, date, section —
never an internal entry ID (``q39``, ``nq4``, ``or10``, ``t8``, ``kp1``,
``cw2``, slug ids like ``q-conclusion-feasibility``, or cross-artifact forms
like "aaro q13" / "0446 q1"). IDs are positional: they shift across merges
and rebuilds, nothing checks that a prose reference still resolves to the
entry the author meant, and they render into node bodies (Key Passage
headings, Location rows, Timeline cells) where a reader cannot resolve them.

One check module per owning build phase dispatches this scanner, so a
role's ``--phase`` pass catches the IDs its own output introduced:

  quote_prose_entry_ids      quotes[] prose (significance / context /
                             source.location) — the Worker's output
  synthesis_prose_entry_ids  top-level synthesis prose (description,
                             background, establishes, …) — Build, organize
  link_prose_entry_ids       structured entry lists (timeline, naming_quirks,
                             relationships, …) — Build, link

Each module's phase is read from ``_phases.CHECK_PHASE`` (the routing source
of truth); a top-level section belongs to the phase ``_phases`` assigns the
same-named section check (``timeline`` -> link, ``establishes`` ->
organize), ``quotes`` to extract, and any other key — top-level prose,
``context_extrinsic`` — to organize. A new section is therefore scanned
without a Python edit.

Not scanned (never prose, or verbatim source text that is never edited):
  - ``id`` and the ID-typed pointer fields: the lifecycle pointers
    (``superseded_by`` / ``contradicted_by`` / ``corroborated_by``, resolved
    by ``cross_refs``), ``speaker_id``, and the finding / investigation
    pointers (``evidence_id`` / ``hypothesis_id`` /
    ``against_hypothesis_id`` / ``anchor``);
  - verbatim payload: ``quotes[].text``, ``naming_quirks[].observed``,
    ``records_sought[].identifiers[].value``, all of ``cited_works``;
  - ``primary_sources`` (archive metadata and the machine-stamped
    ``content_block`` / ``quote_corroboration`` records);
  - path / URL fields (``path``, ``url``, ``node_link``, ``target_node``,
    ``*_path``, ``*_url``, ``*_ref``); inside prose, link wraps, URLs and
    file / node paths are blanked before matching.

The token rule is lowercase-only and case-sensitive. A source's own
uppercase labels — a QFR's "Q7", a Congressional Record page "H5120", a
fiscal quarter "Q4" — are not entry IDs, and neither are investigation
hypothesis labels, which the renderer displays as "H1" / "H2" and a reader
can resolve on the page.
"""

import re

from checks import Issue
from checks._phases import CHECK_PHASE, phase_of


# Entry-ID prefixes the corpus assigns, one per entry-bearing section
# (q quotes, cw cited_works, t / tl timeline, nq naming_quirks, or
# org_relationships, kp key_personnel, a / aff affiliations, r / rel
# relationships, p / pi program_involvement + participants, s speakers,
# c / ct contracts + corroboration_items + contradictions + correspondence,
# vc vouching_chain, rs records_sought, rr released_records, lr
# location_relationships, ot ownership_timeline, us top_scope_activity,
# wt witnesses_testimony, h hypotheses, oq open_questions, cf
# cited_findings, ce counter_evidence). The artifact's own id prefixes are
# added at scan time, so a new section's prefix is caught on its own
# artifact without editing this tuple.
_KNOWN_PREFIXES = (
    "q", "cw", "t", "tl", "nq", "or", "kp", "a", "aff", "r", "rel", "p",
    "pi", "s", "c", "ct", "vc", "rs", "rr", "lr", "ot", "us", "wt", "h",
    "oq", "cf", "ce",
)

# Slug-form quote ids (``q-conclusion-feasibility``) — two or more
# hyphenated parts after the ``q-`` prefix.
_SLUG_QUOTE_ID = r"q-[a-z0-9]+(?:-[a-z0-9]+)+"

_ID_KEYS = {
    "id", "superseded_by", "contradicted_by", "corroborated_by",
    "speaker_id", "evidence_id", "hypothesis_id", "against_hypothesis_id",
    "anchor",
}
_REF_KEYS = {"path", "url", "node_link", "target_node"}
_SKIP_SECTIONS = {"primary_sources", "cited_works"}
# (top-level section, key) pairs whose value is verbatim source text.
_VERBATIM = {("quotes", "text"), ("naming_quirks", "observed"),
             ("records_sought", "value")}

# Blanked before matching: link wraps, URLs, file paths with an extension,
# and rooted node paths — an ID-shaped slug segment is not a prose reference.
_NON_PROSE = re.compile(
    r"\[`[^`]+`\]"
    r"|https?://\S+"
    r"|[\w.-]*/[\w./-]*\.[A-Za-z0-9]{2,5}\b"
    r"|(?<![\w/])/[a-z][a-z-]*/[\w./-]+"
)


def _token_res(prefixes):
    """(slug id, numeric id, numeric id ending a string, range end). The
    numeric form allows a hyphen boundary so hyphen-joined ranges
    ("q21-q23") are caught; ``find_entry_ids`` uses the last two to drop a
    hyphen neighbour that is not itself part of a range (so a slug-like
    word such as ``sec-q3`` is not)."""
    alt = "|".join(sorted(set(prefixes), key=len, reverse=True))
    numeric = rf"(?:{alt})\d+[a-z]?"
    return (
        re.compile(rf"(?<![A-Za-z0-9_-]){_SLUG_QUOTE_ID}(?![A-Za-z0-9_-])"),
        re.compile(rf"(?<![A-Za-z0-9_]){numeric}(?![A-Za-z0-9_])"),
        re.compile(rf"(?:^|[^A-Za-z0-9_]){numeric}$"),   # an ID ending here
        re.compile(rf"(?:{numeric}|\d+[a-z]?)(?![A-Za-z0-9_])"),  # range end
    )


def _artifact_prefixes(data):
    out = set()
    for val in data.values():
        if isinstance(val, list):
            for e in val:
                if isinstance(e, dict) and isinstance(e.get("id"), str):
                    m = re.fullmatch(r"([a-z]+)\d+[a-z]?", e["id"])
                    if m:
                        out.add(m.group(1))
    return out


def section_phase(section):
    """Owning phase of a top-level artifact key (see module docstring)."""
    if section == "quotes":
        return "extract"
    p = CHECK_PHASE.get(section)
    return p if p in ("extract", "organize", "link") else "organize"


def _skip_key(section, key):
    return (
        key in _ID_KEYS or key in _REF_KEYS
        or key.endswith(("_path", "_url", "_ref"))
        or (section, key) in _VERBATIM
    )


def _leaves(obj, section, path):
    if isinstance(obj, dict):
        for k, v in obj.items():
            k = str(k)
            if _skip_key(section, k):
                continue
            yield from _leaves(v, section, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            tag = v.get("id") if isinstance(v, dict) else None
            label = f"{i} ({tag!r})" if isinstance(tag, str) else str(i)
            yield from _leaves(v, section, f"{path}[{label}]")
    elif isinstance(obj, str):
        yield path, obj


def find_entry_ids(text, token_res):
    """ID tokens in one prose string, after blanking non-prose spans. A
    numeric token touching a hyphen counts only as one end of a range: the
    hyphen's other side must be an ID (``q21-q23``) or a bare number
    (``q21-23``)."""
    slug_re, num_re, ends_id, range_end = token_res
    cleaned = _NON_PROSE.sub(lambda m: " " * len(m.group(0)), text)
    found = []
    for m in slug_re.finditer(cleaned):
        found.append((m.start(), m.group(0)))
    cleaned = slug_re.sub(lambda m: " " * len(m.group(0)), cleaned)
    for m in num_re.finditer(cleaned):
        start, end = m.span()
        if start and cleaned[start - 1] == "-" and not ends_id.search(cleaned[:start - 1]):
            continue
        if cleaned[end:end + 1] == "-" and not range_end.match(cleaned, end + 1):
            continue
        found.append((start, m.group(0)))
    return [tok for _, tok in sorted(found)]


def scan(ctx, check_name):
    """Yield one error per prose field carrying entry-ID tokens, for the
    sections owned by ``check_name``'s phase."""
    data = ctx.data
    if not isinstance(data, dict):
        return
    phase = phase_of(check_name)
    token_res = _token_res(_KNOWN_PREFIXES + tuple(_artifact_prefixes(data)))
    for section, val in data.items():
        section = str(section)
        if section in _SKIP_SECTIONS or _skip_key(None, section):
            continue
        if section_phase(section) != phase:
            continue
        for path, text in _leaves(val, section, section):
            tokens = find_entry_ids(text, token_res)
            if not tokens:
                continue
            uniq = list(dict.fromkeys(tokens))
            yield Issue(
                ctx.rel, "error",
                f"{path}: internal entry ID(s) in prose "
                f"{', '.join(repr(t) for t in uniq)} — entry IDs are "
                f"positional and unresolvable by a reader; name the source "
                f"(document, date, section) instead. For a stale reference, "
                f"check the claim against the entry actually meant.",
                check_name=check_name,
            )
