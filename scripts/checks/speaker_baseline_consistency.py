"""speaker_baseline_consistency check — kebab-case identity-slug chain
discipline from transcript speakers to photo-identity baselines.

The chain we want to lock down:

  artifact.speakers[].node_link
      ↓ (kebab-case slug)
  sources/photo-identity-log/baselines/{slug}/

Each ``speakers[]`` entry whose ``node_link`` points at ``/people/{slug}``
should have a baseline directory at
``sources/photo-identity-log/baselines/{slug}/`` carrying at least one
image file. Missing baselines surface as ``warn`` — the speaker's
identity is confirmed via the node_link anchor; the baseline is
video-pipeline diagnostic. Useful flag for contributor: "register a
baseline to enable speaker disambiguation on future videos featuring
this person."

Severity rationale: ``warn``, not ``error``. The structural attribution
still works via ``speaker_id`` and ``node_link`` — the baseline is
downstream video-pipeline plumbing. But the missing-baseline state is a
real drift surface over time and worth surfacing.
"""

from pathlib import Path

from checks import Issue
from checks._research_utils import entries


CHECK_NAME = "speaker_baseline_consistency"

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BASELINES_DIR = _REPO_ROOT / "sources" / "photo-identity-log" / "baselines"

_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")


def _slug_from_people_link(node_link):
    """Return the kebab-case slug if ``node_link`` is a /people/X path,
    else None. Tolerates the prefix-with or prefix-without slash forms
    by stripping leading slash before matching."""
    s = str(node_link or "").strip().lstrip("/")
    if s.startswith("people/"):
        slug = s.removeprefix("people/")
        # Strip any trailing slash or .md suffix
        return slug.rstrip("/").removesuffix(".md")
    return None


def _baseline_has_images(slug):
    """True if ``baselines/{slug}/`` exists and contains at least one
    .jpg/.jpeg/.png file. An empty directory does not count — the chain
    is structural, not nominal."""
    d = _BASELINES_DIR / slug
    if not d.is_dir():
        return False
    for f in d.iterdir():
        if f.is_file() and f.suffix.lower() in _IMAGE_SUFFIXES:
            return True
    return False


def check(ctx):
    """Each transcript-artifact speakers[].node_link that points at
    /people/X should have a baseline at baselines/X/."""
    if ctx.target_type != "transcript":
        return
    speakers = entries(ctx.data, "speakers")
    for i, s in enumerate(speakers):
        if not isinstance(s, dict):
            continue
        slug = _slug_from_people_link(s.get("node_link"))
        if not slug:
            continue
        if not _baseline_has_images(slug):
            yield Issue(
                ctx.rel, "warn",
                f"speakers[{i}] ({s.get('id')!r}): node_link "
                f"/people/{slug} has no baseline at "
                f"sources/photo-identity-log/baselines/{slug}/ — register "
                f"one via scripts/tools/detect-faces.py to enable "
                f"video-pipeline speaker disambiguation for this person",
                check_name=CHECK_NAME,
            )
