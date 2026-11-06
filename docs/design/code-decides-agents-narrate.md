---
gist: "Read when: changing what a model may write in a result, the decision record assembly, narrative checks, or an evaluator MCP tool."
---

# Code decides, agents narrate

- Code decides, agents narrate. Each domain has a deterministic evaluator exposed as an MCP tool (`compliance_mcp/<domain>/`). The agent calls the tool, the harness pins the tool arguments to the loan payload, and `compliance_common/assemble.py` builds the result from the tool's decision record plus the model's prose; decision-owned fields the model emits are stripped and logged.
- Narrative checks and schema-constrained JSON reduce common model failures, but do not certify a generated report. Review both the structured guard/fallback metadata and exported Markdown: a local model may return internal-looking or instruction-like text that is not suitable for an examiner-facing report.
