---
id: meta/topic/working-notes/dird-coverage-extraction-density-screen
type: meta
status: working-notes
integration_targets:
  - /documents/dird-06-space-access
  - /documents/dird-24-quantum-vacuum-energy-extraction
  - /documents/dird-26-field-effects-biological-tissues
---

# DIRD corpus extraction-density screen (2026-05-27)

**Triage record, not synthesis-for-a-node.** This note flags which DIRD
document nodes are likely **under-extracted (skimmed)** so a future
session can run targeted re-extraction passes. It is not destined to be
absorbed into node prose; it "retires" when the flagged candidates'
re-extraction passes are complete.

## Why this exists

Prompted by an investigation into why `dird-11-advanced-nuclear-propulsion`
and `dird-15-advanced-space-propulsion` render as small nodes (2026-05-27).
That investigation found DIRD-11 genuinely skimmed and DIRD-15 small only
because its source is genuinely short. The user then asked for a corpus-wide
screen to catch any *other* skimmed DIRDs. **DIRD-11 was remediated the same
session** (6 → 33 substantive quotes; see below) and is no longer a candidate.

## Method

Raw quote count is misleading — DIRD-11 had 12 quotes but only 6 were
substantive (the other 6 were provenance/administrative boilerplate:
classification banner, title-page block, Black Vault/FOIA insert,
prepared-by/author block, copyright warning, AAWSA-program note). So each
node was scored on:

- **substantive quotes** = total quotes − provenance boilerplate (classified
  by reading each quote's `significance`/`location`);
- **words per substantive quote** = source word-count (from the verified
  `.txt` sibling) ÷ substantive quotes — the primary skim signal;
- **unref %** = `scripts/tools/coverage-suggest.py` unreferenced-substantive-
  paragraph fraction — a secondary signal.

**Calibration anchors:** DIRD-15 (confirmed short-but-covered) = 586 w/q,
30.8 % unref → healthy. DIRD-11 (confirmed skimmed, pre-remediation) =
2,091 w/q, 53.5 % unref → skimmed. The danger zone is the **conjunction** of
high w/q AND high unref %. High unref % alone is not damning — long, densely
quoted sources (DIRD-09, -18) and short primers (DIRD-02) both run elevated
unref % for benign reasons (equations, figures, reference lists, and small
denominators all count as "paragraphs" but aren't quotable prose).

## Ranked screen (sorted by words-per-substantive-quote, most-skimmed on top)

| DIRD | pg | src words | total q | subst. q | words/subst-q | unref % | verdict |
|---|---|---|---|---|---|---|---|
| dird-11-advanced-nuclear-propulsion *(pre-fix)* | 38 | 12,544 | 12 | 6 | 2,091 | 53.5% | **was skimmed — REMEDIATED 2026-05-27** |
| **dird-06-space-access** | 57 | 20,376 | 16 | 11 | **1,852** | 53.0% | **likely skimmed — candidate #1** |
| **dird-24-quantum-vacuum-energy-extraction** | 58 | 23,671 | 19 | 16 | **1,479** | **56.6%** | **likely skimmed — candidate #2** |
| dird-26-field-effects-biological-tissues | 39 | 13,948 | 21 | 16 | 872 | 54.8% | borderline — watch (candidate #3) |
| dird-03-pulsed-hpm | 38 | 15,320 | 23 | 20 | 766 | 28.3% | normal |
| dird-07-invisibility-cloaking | 30 | 8,972 | 17 | 12 | 748 | 40.1% | normal |
| dird-01-metallic-glasses | 31 | 10,335 | 17 | 14 | 738 | 32.8% | normal |
| dird-10-metallic-spintronics | 28 | 11,166 | 22 | 16 | 698 | 36.9% | normal |
| dird-09-iec-fusion | 73 | 30,115 | 53 | 48 | 627 | 50.8% | well-covered (unref % = long-source effect) |
| dird-02-programmable-matter | 21 | 7,481 | 17 | 12 | 623 | 52.5% | adequately covered (short primer; small-denominator unref %) |
| dird-15-advanced-space-propulsion *(anchor)* | 17 | 5,859 | 13 | 10 | 586 | 30.8% | **short-but-covered — no action** |
| dird-08-positron-aerospace-propulsion | 36 | 10,063 | 29 | 24 | 419 | 40.9% | well-covered |
| dird-18-traversable-wormholes | 43 | 16,487 | 43 | 40 | 412 | 49.3% | well-covered |
| dird-12-bci-controlling-external-devices | 37 | 15,833 | 49 | 43 | 368 | 40.9% | well-covered |
| dird-05-aerospace-platforms-materials | 28 | 12,068 | 50 | 46 | 262 | 31.9% | well-covered |
| dird-04-biomaterials | 33 | 9,640 | 55 | 51 | 189 | 39.1% | well-covered |

*(DIRD-11 row shows the pre-remediation numbers that prompted this screen. As
of 2026-05-27 it carries 39 total / ~33 substantive quotes, ≈380 w/q, 46.8 %
unref — now in the well-covered band.)*

## Re-extraction candidates (besides the already-fixed DIRD-11)

1. **`/documents/dird-06-space-access`** — strongest. 57 pp / 20.4k words (the
   longest mid-tier source), only 11 substantive quotes (1,852 w/q), 53 %
   unref. Quote `location`s jump p.18 → p.33 → p.41, leaving large un-quoted
   mid-document spans (Hypersonic Configuration Concepts, Rocket Propulsion,
   Up-and-Down Operations).
2. **`/documents/dird-24-quantum-vacuum-energy-extraction`** — 58 pp / 23.7k
   words, 16 substantive quotes (1,479 w/q), highest unref % of all 16
   (56.6 %). Quote locations leap p.14 → p.44 — the entire Sections IV/V
   technical core (~30 pp) is unrepresented. Load-bearing for
   `/investigations/lockheed-martin-uap-materials`, so worth doing well.
3. **`/documents/dird-26-field-effects-biological-tissues`** — borderline.
   872 w/q (about half DIRD-11's) but 54.8 % unref, with page-spanning gaps
   (p.20 → p.25 → p.31 Schuessler appendix). Weakest of the three; confirm by
   eye before committing a pass.

## Watch-list resolution (low raw-quote-count nodes)

- **DIRD-02 (17 q)** — adequately covered; 21-pp / 7.5k-word primer, 623 w/q
  is normal; its 52.5 % unref is a small-denominator artifact. Not a candidate.
- **DIRD-01 / DIRD-07 (17 q)** — normal (738 / 748 w/q). Short sources, fine.
- **DIRD-24 (19 q)** and **DIRD-06 (16 q)** — the two watch-list members that
  *do* hold up as under-extracted (above).

## Procedure when remediating a candidate

Same path used for DIRD-11 this session: confirm the source's OCR `.txt`
sibling is verified (OCR gate), `/augment` Shape B → `Agent(worker)` reads the
sibling → merge substantive quotes into the artifact → `validate-research.py
--phase extract` → `build-from-research.py` → `review-coverage.py --all` →
`Agent(auditor)`. Target ≈400–600 words/substantive-quote (the well-covered
band). Keep contiguous spans (no ellipsis / page-break bridging).
