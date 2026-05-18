"""Media-type renderer.

Renders media nodes (photo / video / audio / imagery-other). All four
kinds share the same section structure; per-kind variation happens
within Media Summary (field list adapts to what document_intrinsic
contains). Media Versioning emits when the artifact has
media_versioning entries OR the node frontmatter has derivation_of
set; canonical / original media omit the section entirely.
"""

from ._common import (
    SECTION_SEP,
    _escape_table_cell,
    _manifest_sha256_for,
    _render_attribution_block,
    _source_path,
    sort_by_id,
)
from ._universal import (
    render_associated_nodes,
    render_description,
    render_preserved_disagreements,
    render_provenance,
    render_source_form_notes,
)


def render_title_media(artifact):
    """H1 title for media nodes. Prefers context_extrinsic.display_title,
    falls back to document_intrinsic.internal_title, then humanized slug."""
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    slug = artifact["target_node"].split("/", 1)[1] if "/" in artifact["target_node"] else ""
    title = (
        ctx.get("display_title")
        or dm.get("internal_title")
        or (slug and " ".join(w.capitalize() for w in slug.split("-")))
        or ""
    )
    return f"# {title}\n"


def render_media_summary(artifact, kind):
    """Media Summary table — kind-agnostic row emission from
    document_intrinsic + context_extrinsic + primary_sources + manifest
    sha256 lookup. Field conventions documented in
    schema-research-artifact.yaml's required_keys section
    (document_intrinsic field comment, media subsection). Rows with empty values are
    skipped — the Summary adapts to what the source and contributor
    populated rather than showing "N/A" placeholders. `kind` comes
    from the node frontmatter (photo / video / audio / imagery-other)
    and renders as the Kind row."""
    dm = artifact.get("document_intrinsic") or {}
    ctx = artifact.get("context_extrinsic") or {}
    path = _source_path(artifact)
    sources = artifact.get("primary_sources") or []
    fmt = None
    if sources and isinstance(sources[0], dict):
        fmt = sources[0].get("format")

    lines = ["## Media Summary", "", "| Field | Value |", "|---|---|"]
    rows_emitted = False

    def row(label, value):
        nonlocal rows_emitted
        if value in (None, "", [], {}):
            return
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value)
        lines.append(f"| {label} | {_escape_table_cell(value)} |")
        rows_emitted = True

    row("Title", ctx.get("display_title") or dm.get("internal_title"))
    row("Kind", kind)
    row("Date Captured", dm.get("capture_date") or dm.get("original_creation_date"))
    row("Date Released", ctx.get("release_date"))
    # Duration + Dimensions: label adapts to what's populated. Video
    # typically has both → "Duration / Dimensions"; audio has only
    # duration → "Duration"; photo / imagery-other has only dimensions
    # → "Dimensions". Keeps the label honest about what the row covers.
    has_dur = bool(dm.get("duration"))
    has_dim = bool(dm.get("dimensions"))
    if has_dur and has_dim:
        row("Duration / Dimensions", f"{dm['duration']} / {dm['dimensions']}")
    elif has_dur:
        row("Duration", dm.get("duration"))
    elif has_dim:
        row("Dimensions", dm.get("dimensions"))
    # Format: document_intrinsic.file_format takes precedence (precise),
    # fall back to primary_sources[0].format (the manifest-registered
    # container type).
    row("Format", dm.get("file_format") or (fmt.upper() if fmt else None))
    row("Codec", dm.get("codec"))
    row("Color Mode", dm.get("color_mode"))
    row("File Size", dm.get("file_size"))
    row("Camera / Device", dm.get("camera_device"))
    row("EXIF / Container Metadata", dm.get("embedded_metadata"))
    if path:
        sha = _manifest_sha256_for(path)
        if sha:
            row("SHA256", sha)
    row("Primary Source URL", ctx.get("primary_source_url"))
    if path:
        row("Local Archive", f"[sources/{path}](../sources/{path})")

    if not rows_emitted:
        lines.append("|  |  |")
    return "\n".join(lines) + "\n"


def render_media_versioning(artifact, fm):
    """Media Versioning table. Emission rules:
      - When the node frontmatter has `derivation_of` set, the section
        MUST emit (per schema.yaml media.conditionally_required) — even
        if `media_versioning` is empty, render a placeholder row so the
        node-body validator's required-section check passes.
      - When `derivation_of` is absent, the section is omitted entirely
        (empty string returned; caller drops it from the body).
    Columns: Aspect / Parent / This / Source / Note.
    """
    items = sort_by_id([
        e for e in (artifact.get("media_versioning") or []) if isinstance(e, dict)
    ])
    is_derivative = bool((fm or {}).get("derivation_of"))
    if not items and not is_derivative:
        return ""  # Canonical / original media — omit the section entirely

    if not items:
        return (
            "## Media Versioning\n\n"
            "<!-- TODO: populate `media_versioning[]` in the research artifact. "
            "Per-aspect differences between the parent (derivation_of) media "
            "node and this derivative. Aspect enum: duration / encoding / "
            "metadata / content / provenance / other. -->\n"
        )

    lines = ["## Media Versioning", "",
             "<!-- Per-aspect differences between the parent (derivation_of) "
             "media node and this derivative. Aspect enum: duration / "
             "encoding / metadata / content / provenance / other. -->",
             "",
             "| Aspect | Parent | This | Source | Note |",
             "|---|---|---|---|---|"]
    for e in items:
        aspect = _escape_table_cell(e.get("aspect"))
        parent = _escape_table_cell(e.get("parent_form"))
        this_v = _escape_table_cell(e.get("this_form"))
        src = e.get("source") or {}
        src_path = src.get("path") if isinstance(src, dict) else ""
        src_loc = src.get("location") if isinstance(src, dict) else ""
        if src_path:
            src_cell = f"[archived source](../sources/{src_path})"
            if src_loc:
                src_cell = f"{src_cell} — {src_loc}"
        else:
            src_cell = ""
        src_cell = _escape_table_cell(src_cell)
        note = _escape_table_cell(e.get("note"))
        lines.append(f"| {aspect} | {parent} | {this_v} | {src_cell} | {note} |")
    return "\n".join(lines) + "\n"


def render_media_key_passages(artifact):
    """Key Passages on media — verbatim speech or visible text. Uses
    the shared `_render_attribution_block` so the flexible source.location
    (timestamp / timestamp+coordinate / spatial-only) flows through.
    H3 per quote using `significance`. May be empty when the source has
    no extractable speech or visible text."""
    quotes = sort_by_id([
        q for q in (artifact.get("quotes") or []) if isinstance(q, dict)
    ])
    head = "## Key Passages\n"
    if not quotes:
        return head + (
            "\n<!-- May be empty when the source has no extractable speech "
            "or visible text. Heavy speech content spins up a separate "
            "transcript node pointing to this media via `derived_from`. -->\n"
        )

    blocks = []
    for q in quotes:
        h3 = q.get("significance") or "Passage"
        text = (q.get("text") or "").rstrip("\n")
        lines = [f"### {h3}", ""]
        for qline in text.split("\n"):
            lines.append(f"> {qline}" if qline else ">")
        lines.append("")
        lines.append(_render_attribution_block(q, artifact))
        blocks.append("\n".join(lines))
    return head + "\n" + "\n\n---\n\n".join(blocks) + "\n"


def render_body_media(artifact, kind, fm):
    """Media-type body composition. All four kinds (photo / video /
    audio / imagery-other) share the same section structure; per-kind
    variation happens within Media Summary (field list adapts to what
    document_intrinsic contains). Media Versioning is conditional on
    the artifact having media_versioning entries — omitted entirely
    for canonical / original media.
    """
    title = render_title_media(artifact).rstrip("\n") + "\n"
    sections = [
        render_media_summary(artifact, kind),
        render_description(artifact),
        render_provenance(artifact),
    ]
    mv_section = render_media_versioning(artifact, fm)
    if mv_section:
        sections.append(mv_section)
    sections.extend([
        render_media_key_passages(artifact),
        render_source_form_notes(artifact),
        render_preserved_disagreements(artifact),
        render_associated_nodes(),
    ])
    sections = [s for s in sections if s]
    joined = SECTION_SEP.join(s.rstrip("\n") + "\n" for s in sections).rstrip() + "\n"
    return title + "\n" + joined
