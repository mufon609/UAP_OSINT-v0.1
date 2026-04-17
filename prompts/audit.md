# Audit prompt

Paste into a Claude Code session to audit an existing node.

---

Run the onboarding steps in `prompts/onboard.md` first if you haven't
this session.

The audit target is: **{PATH}**  (ask the user if not specified)

Audit goals:

1. **Evidentiary integrity** — every confirmed claim traces to a
   primary source archived in `sources/` and registered in
   `sources/manifest.yaml`. Flag any claim that does not.
2. **Quote verbatim check** — every `> blockquote` has a verification
   block. Re-verify a sample of quotes against the archived source
   file. Flag any paraphrase masquerading as verbatim.
3. **Contradiction markers** — `❌ Contradiction` used where positions
   contradict and at least one side has primary-source evidence;
   `⚠ Disputed — unknown` used only where neither side has
   primary-source evidence. Reclassify if wrong.
4. **Section requirements** — run `python3 scripts/validate.py PATH`
   and fix any errors.
5. **Associated Nodes freshness** — run
   `python3 scripts/associate.py PATH` to regenerate.
6. **Open Questions realism** — each item should have concrete
   methodology. Remove items that are truly unresolvable-and-trivial;
   keep anything that names an investigation pathway.
7. **Cross-node consistency** — check that claims in this node agree
   with claims in nodes it references. Flag any unexplained divergence.

Audit output:

1. Summary of findings (errors, warnings, suggestions)
2. Proposed changes (diff preview before applying)
3. After user approval, apply changes in focused commits

**Do not:**
- Bulk-delete Open Questions without spot-checking each against body content
- Remove Flagged items without verifying them against a new primary source
- Introduce new claims without new archived sources
- Reframe existing confirmed claims without new evidentiary basis
