---
id: findings/{{slug}}
type: finding
---

# {{display_name}}

<!-- ─────────────────────────────────────────────────────────────────────
     RENDERER-MANAGED BODY. Do NOT hand-edit the sections below.

     This node body is regenerated from meta/research/{{slug}}.yaml by
     scripts/build/build-from-research.py. The scaffolded sections
     below are a shape reference; once you run build-from-research.py
     the body is replaced entirely (frontmatter above is preserved
     verbatim). Populate the research artifact and re-run the renderer
     (via the `/build` skill). Hand-edits
     to the body trigger the boundary-check failure.
     ───────────────────────────────────────────────────────────────────── -->

<!-- A finding documents a CROSS-SOURCE PATTERN that becomes visible only
     when multiple primary sources are read together. The pattern is not
     established by any single source; the synthesis-of-reading-together
     produces information not present in any constituent attestation.

     Findings CITE PRIMARY SOURCES DIRECTLY via evidence rows' source
     path (never entity-node markdown files). attestor on each row
     captures who attested; the citation itself goes to the source.

     Findings DUPLICATE primary-source content from entity nodes BY
     DESIGN. If a finding cites material the relevant entity node
     doesn't yet attest, the entity node is updated first (primary
     source confirmed + archived) before the finding can use it.

     Findings DO NOT REFERENCE the investigations that consume them.
     Findings stay cluster-neutral so they can be cited from multiple
     investigations.

     The BRIGHT LINE — fact vs finding: a FACT is a single-source
     attestation (lives on the entity node; may name other entities but
     synthesizes nothing). A FINDING is a pattern visible only across
     MULTIPLE sources read together. Worked examples: a witness on one
     podcast naming a contractor = fact (entity node); a company's
     consistent non-denial across three outlets over a year = finding
     (the pattern is the convergence); an anonymous authorship named in a
     separate filing and entered into the public record = finding (two
     sources combine). Findings document the pattern and STOP — verdicts
     belong on investigations. A finding is justified at multi-source
     convergence, typically 3+ independent sources, or when the same
     material is about to be written into 3+ entity nodes; a written-vs-
     oral testimony divergence (oral on the transcript node, written on
     the companion document node, equal evidentiary weight) is a finding
     spanning the two primary records. -->
<!-- Tier model: a finding (Tier 3) references sources + entity nodes,
     never another finding or an investigation. The machine-readable
     tier definition is meta/schema.yaml architecture_layers; the
     directional rule is the build-protocol "Tier linking contract". -->

## Pattern Statement

<!-- One declarative sentence stating the cross-source pattern this
     finding documents. Cluster-neutral framing — table the pattern,
     don't presume which investigation consumes it. -->

---

## Description

<!-- Synthesis prose explaining what the pattern is + scope. Subject
     to the prose-drift check against the convergent source set. -->

---

## Evidence

<!-- Each evidence row renders as an H3 card from quotes[] in the
     research artifact: significance → H3 heading, text → blockquote,
     verification block with Attributed-to / Tier / Attestor / Source /
     Location rows.

     The attestation_tier field on each quote drives the Tier row —
     sworn-oath / sworn-perjury / dopsr-cleared / on-record /
     self-attested / secondary-source. Mixed-tier convergence is the
     typical shape; per-row tier rendering surfaces evidentiary weight
     visibly without contributor prose. -->

---

## What the Record Establishes

<!-- Bullet list of explicit claims about what the convergence proves.
     Anchor each claim to specific evidence rows by id (q1, q2, …).
     Cluster-neutral — what the convergence proves, full stop. -->

-

---

## What the Record Doesn't Establish

<!-- Bullet list of explicit caveats, gaps, divergences. No
     speculation; what the record DOES NOT carry. Open questions
     above the investigation threshold spin up a separate
     investigation node; small caveats stay here. -->

-

---

## Associated Nodes
