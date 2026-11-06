---
gist: "Read when: a narrative contradicts the decision record, evidence appears fabricated, or the grounding and fact-check guards are changed."
---

# Narrate-only tightening and grounding guards

- 2026-10-09 — Narrate-only tightening. Diagnosis: the earlier "VMI contradiction" was a regex false positive on a sloppy sentence, and most "invented evidence" was real data from other loan sections (only the FZD "included in HMDA case" item was truly fabricated). Fixes: the model sees only its own case; it writes three prose fields only; evidence/data-quality/change blocks and scope notes are code-owned; narratives are fact-checked, retried once, then replaced by a code-written narrative. Granite 3B seeded, 8 agents x seeds 42/7: heuristic accuracy 92.5 / 88.8 (was ~84), 2 of 8 narratives fell back to the deterministic text on seed 42 and 1 of 8 on seed 7 (contradiction watchdog; since narrowed to Compliant results only because "fails to exceed the spread" is normal on Not Applicable).
