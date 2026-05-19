"""speaker_baseline_consistency check — kebab-case identity-slug chain
discipline across transcript speakers, photo-identity baselines, and
person nodes.

The chain we want to lock down:

  artifact.speakers[].node_link
      ↓ (kebab-case slug)
  /people/{slug}.md
      ↓ (same slug)
  sources/photo-identity-log/baselines/{slug}/

When the chain is intact, speaker identity is mechanically traceable
across the corpus — the video-pipeline tooling (detect-faces.py,
stitch-transcript.py) finds the visual baseline by the same slug the
artifact uses to name the speaker.

Two directions:

  1. ``speakers[].node_link → baseline`` (per-artifact, transcript-scoped)

     Each ``speakers[]`` entry whose ``node_link`` points at
     ``/people/{slug}`` should have a baseline directory at
     ``sources/photo-identity-log/baselines/{slug}/`` carrying at
     least one image file. Missing baselines surface as ``warn`` —
     the speaker's identity is confirmed via the node_link anchor; the
     baseline is video-pipeline diagnostic. Useful flag for
     contributor: "register a baseline to enable speaker
     disambiguation on future videos featuring this person."

  2. ``baselines/{slug}/ → /people/{slug}.md`` (manifest-wide)

     Each baseline directory should have a corresponding person node.
     Orphan baselines surface as ``warn`` — either a preparatory
     registration for a person whose node isn't built yet (acceptable
     per the existing pattern: jake-barber, danny-sheehan, etc. were
     registered before their person nodes), OR a slug-typo (e.g.,
     ``davd-grusch/`` instead of ``david-grusch/``). The warn forces
     visual review; contributor either builds the missing node or
     fixes the typo.

Direction 1 runs as a per-artifact ResearchContext check (transcript-
target only). Direction 2 is exposed via ``manifest_wide_check()``,
called once by the orchestrator after the per-artifact worker pool
completes; not safe to do per-artifact since validate-research.py
forks workers and module-level state doesn't survive the fork.

Severity rationale: both directions emit ``warn``, not ``error``.
Neither failure mode blocks evidentiary correctness — the structural
attribution still works via ``speaker_id`` and ``node_link``; the
baseline is downstream video-pipeline plumbing. But both are real
drift surfaces over time and worth surfacing.
"""

from pathlib import Path

from checks import Issue
from checks._research_utils import entries


CHECK_NAME = "speaker_baseline_consistency"

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BASELINES_DIR = _REPO_ROOT / "sources" / "photo-identity-log" / "baselines"
_PEOPLE_DIR = _REPO_ROOT / "people"

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


def _person_node_exists(slug):
    """True if ``/people/{slug}.md`` exists."""
    return (_PEOPLE_DIR / f"{slug}.md").is_file()


def check(ctx):
    """Direction 1: each transcript-artifact speakers[].node_link that points
    at /people/X should have a baseline at baselines/X/."""
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


def manifest_wide_check():
    """Direction 2: each baselines/{slug}/ directory should have a
    corresponding /people/{slug}.md node. Yields ``warn`` Issues for
    orphans. Called once by the orchestrator after the per-artifact
    worker pool — fork-shared module state would not preserve once-only
    semantics across workers, so this direction lives outside the
    per-artifact dispatch.

    The Issue path is set to ``sources/photo-identity-log/baselines/`` —
    the location of the inconsistency, not any specific artifact."""
    if not _BASELINES_DIR.is_dir():
        return
    sentinel_rel = "sources/photo-identity-log/baselines"
    for slug_dir in sorted(_BASELINES_DIR.iterdir()):
        if not slug_dir.is_dir():
            continue
        slug = slug_dir.name
        if _person_node_exists(slug):
            continue
        yield Issue(
            sentinel_rel, "warn",
            f"baselines/{slug}/ has no corresponding /people/{slug}.md "
            f"node — either a preparatory registration for a person not "
            f"yet built (acceptable; the baseline becomes structurally "
            f"connected when the person node ships), OR a slug-typo. "
            f"Verify by checking whether {slug!r} matches any planned "
            f"person-node path",
            check_name=CHECK_NAME,
        )
