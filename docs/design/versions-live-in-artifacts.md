---
gist: "Read when: bumping or naming a prompt, evaluator, or pack version, or tempted to put a version in a file or directory name."
---

# Versions live inside artifacts

- Versions live inside the artifacts (prompt header line, `EVALUATOR_VERSION`, pack manifest), never in file or directory names; git carries history. Each component is versioned independently.
