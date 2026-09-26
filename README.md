# Compliance Agent Orchestrator

Sequential fan-out orchestrator for seven Farm Credit ACA compliance agents.
Supports Anthropic and local Ollama models. Each agent is backed by a
spec-derived system prompt; input and output contracts mirror the v0.2 schemas.

For architectural decisions and constraints, see [DESIGN.md](DESIGN.md).

---

## Agents

| Key        | Agent Name                                | Regulation              | Notes                          |
|------------|-------------------------------------------|-------------------------|--------------------------------|
| `hmda`     | HMDA Compliance Agent                     | Regulation C            |                                |
| `ecoa`     | ECOA Compliance Agent                     | Regulation B            |                                |
| `hvcre`    | HVCRE Compliance Agent                    | FCA Capital Regs        |                                |
| `hpml`     | HPML Compliance Agent                     | Regulation Z            |                                |
| `fzd`      | Flood Zone Determination Compliance Agent | NFIA / FDPA             |                                |
| `ybs`      | YBS Eligibility Compliance Agent          | 12 CFR §614.4165        |                                |
| `vmi`      | VMI Compliance Agent                      | Regulation B §1002.13   |                                |
| `auditor`  | Compliance Auditor                        | Cross-regime            | Runs automatically after batch |
| `narrative`| Narrative Agent                           | Report generation       | Requires `--narrative-out`     |

---

## Setup

```bash
pip install -r requirements.txt
```

## Deterministic YBS pilot

YBS determinations now run through an offline evaluator before the YBS model is
called. The evaluator is provider-neutral and is the authority for eligibility,
thresholds, rule outcomes, and missing-fact status; the LLM may only explain its
decision record. Use a canonical `ybs_case` object (see
[`sample_ybs_case.json`](sample_ybs_case.json)) inside a normal loan payload:

```json
{
  "case_information": {"case_id": "YBS-DETERMINISTIC-2026-001"},
  "ybs_case": {"evaluation_date": "2026-06-01", "subjects": []}
}
```

The canonical input and decision-record contracts are versioned in
`rulepacks/ybs/ybs-v0.1/input.schema.json` and
`rulepacks/ybs/ybs-v0.1/decision-record.schema.json`. Optional provider tool
adapters use the same evaluator; batch operation always calls it directly.

The initial `ybs-v0.1` pack is marked `draft_engineering_review`. Its numeric
thresholds and entity-attribution method are explicit institution-pilot policy,
not claims that 12 CFR §614.4165 supplies those values. The dated eCFR snapshot
and provenance manifest are under `regs/ybs/` and `rulepacks/ybs/ybs-v0.1/`.
Canonical entity inputs now distinguish an organization, trust, successor, and
reorganization; trusts require trustee and controlling-person attribution, while
successors and reorganizations require documented attribution. Narrative input
and legacy `ybs_information` remain usable for discussion but produce `Unable To
Determine` until a canonical case is supplied.

The default suite runs deterministic fixtures, schema/source-manifest checks,
and Anthropic/Ollama/MCP contract parity with local fakes. The opt-in Gemma test
runs the full YBS prompt twice and asserts that the authoritative deterministic
decision ID and classification replay identically; model prose is not assumed
to be byte-identical. See [YBS_CHANGE_CONTROL.md](YBS_CHANGE_CONTROL.md) for
required review paths and the GitHub branch-protection setting that activates
the included CODEOWNERS rules.

Run the offline test suite with:

```bash
python3 -m unittest discover -s tests -v

# Requires a running local Ollama with gemma4:26b; runs the YBS prompt twice.
RUN_LIVE_OLLAMA_TESTS=1 python3 -m unittest tests.test_ybs_gemma_integration -v
```

Create a `.env` file in this directory:

```
COMPLIANCE_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
# Optional — defaults to claude-sonnet-4-20250514
# COMPLIANCE_MODEL=claude-sonnet-4-20250514
```

For Ollama running in the same WSL environment:

```
COMPLIANCE_PROVIDER=ollama
# Optional — defaults to gemma4:26b
# COMPLIANCE_MODEL=gemma4:26b
OLLAMA_BASE_URL=http://localhost:11434
# Optional; local models can take a while on their first request
OLLAMA_TIMEOUT=300
```

No Ollama Python package or API key is required. Make sure `ollama serve` is
running and that the selected model appears in `ollama list`.

---

## CLI Usage

### Batch mode — all agents against a loan file

Runs all seven domain agents sequentially, then the auditor automatically.

```bash
python compliance_orchestrator.py batch sample_loan.json
```

Save structured JSON results and a Markdown narrative report:

```bash
python compliance_orchestrator.py batch sample_loan.json \
  --json-out results.json --narrative-out report.md
```

Redirect JSON to stdout:

```bash
python compliance_orchestrator.py batch sample_loan.json > results.json
```

### Batch mode — selected agents only

```bash
python compliance_orchestrator.py batch sample_loan.json --agents hmda ecoa hpml
```

Select a local model for an individual run:

```bash
python compliance_orchestrator.py batch sample_loan.json \
  --provider ollama --model gemma4:26b --agents hmda ecoa

python compliance_orchestrator.py chat hmda \
  --provider ollama --model gemma4:26b
```

### Chat / REPL mode — interactive session with one agent

```bash
python compliance_orchestrator.py chat hmda
python compliance_orchestrator.py chat ecoa
```

REPL commands:
- `exit` / `quit` — end session
- `reset` — clear history, start fresh with same agent
- `history` — print turn count
- `save <filename>` — write full session + last parsed result to JSON

---

## Programmatic Usage

```python
from compliance_orchestrator import run_batch, call_agent

# Load your loan data
import json
with open("sample_loan.json") as f:
    loan = json.load(f)

# Run all seven agents sequentially
results = run_batch(loan, provider="ollama", model="gemma4:26b")

# Access individual results
hmda = results["hmda"]
print(hmda["parsed"]["determination_status"])
print(hmda["parsed"]["compliance_determination_summary"]["examiner_narrative"])

# Run one agent, check for parse errors
result = call_agent("ecoa", loan)
if result["parse_error"]:
    print("Parse failed:", result["parse_error"])
    print(result["raw_text"])  # raw model output for debugging
else:
    print(json.dumps(result["parsed"], indent=2))

# Narrative input also works
result = call_agent(
    "hmda",
    "Borrower applied for a farm purchase loan. Collateral includes a dwelling "
    "used as principal residence. Loan originated 2024-05-01."
)
```

---

## Output Structure

Each agent returns:

```json
{
  "agent_key": "hmda",
  "agent_name": "HMDA Compliance Agent",
  "raw_text": "...",
  "parsed": {
    "agent_metadata": { ... },
    "authority": { ... },
    "determination_status": {
      "result": "Compliant | Non-Compliant | Potential Issue | Not Applicable | Unable To Determine",
      "confidence": "High | Moderate | Low"
    },
    "evidence_assessment": { ... },
    "data_quality": { ... },
    "determination_trace": [ { "step": "...", "finding": "...", "basis": "..." } ],
    "change_assessment": { ... },
    "compliance_determination_summary": {
      "reasoning": "...",
      "examiner_narrative": "...",
      "status_change_narrative": "...",
      "data_gaps_followups": ["..."]
    }
  },
  "parse_error": null,
  "timestamp": "2024-06-01T12:00:00+00:00"
}
```

`parsed` is `null` and `parse_error` is populated if the model response could not
be parsed as JSON (rare, but handle it).

---

## Adding Agents

1. Add an entry to `AGENTS` in `agent_prompts.py` following the existing pattern.
2. The new key is immediately available to `run_batch()` and `call_agent()`.
3. No changes needed in `compliance_orchestrator.py`.

---

## Notes

- **Sequential execution**: agents run one at a time. Each call is independent;
  no agent sees another agent's output. Upgrade to `asyncio` with
  `anthropic.AsyncAnthropic` when ready for parallel execution.
- **Conversation history**: the REPL maintains in-memory history per session only.
  Use `save <filename>` to persist a session for audit purposes.
- **Model pinning**: set `COMPLIANCE_MODEL` in `.env` to lock a specific model
  version for reproducibility, or pass `model=` / `--model` for a single run.
- **Token budget**: `MAX_TOKENS=8192` covers full structured output. Increase if
  a specific agent consistently truncates.
