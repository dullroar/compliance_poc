---
gist: "Read when: writing or changing a rule evaluator, the handling of missing facts, undetermined judgment calls, or Review Required outcomes."
---

# Absence is never compliance

- Absence is never compliance. When a fact needed for a rule is not supplied, the rule's outcome is `unable_to_determine` and the fact is listed in `missing_facts`; the evaluators do not treat silence as "not applicable". Judgment calls that the regulation leaves to the institution (for example whether a loan is primarily agricultural) are input facts with an explicit `undetermined` value that yields a Review Required result.
