# Compliance Agent Orchestrator

A2A fan-out orchestrator for Farm Credit ACA compliance agents: eight deterministic-evaluator domain agents, a cross-regime
auditor, and an optional narrative report agent.
Supports Anthropic, local Ollama, and optional OpenAI runtime narrators. Each agent is backed by a
system prompt in `prompts/<key>.md` (long-form specs are in `specs/`). Versions live
inside the prompt header, not in filenames; git carries history.

For architectural decisions and constraints, see [docs/design/](docs/design/README.md).

---

## Agents

| Key        | Agent Name                                | Regulation              | Notes                          |
|------------|-------------------------------------------|-------------------------|--------------------------------|
| `hmda`     | HMDA Compliance Agent                     | Regulation C            |                                |
| `ecoa`     | ECOA Compliance Agent                     | Regulation B            |                                |
| `hvcre`    | HVCRE Compliance Agent                    | FCA Capital Regs        |                                |
| `hpml`     | HPML Compliance Agent                     | Regulation Z            |                                |
| `trid`     | TRID Compliance Agent                     | Regulation Z §1026.19(e)/(f) |                           |
| `fzd`      | Flood Zone Determination Compliance Agent | NFIA / FDPA             |                                |
| `ybs`      | YBS Eligibility Compliance Agent          | 12 CFR §614.4165        |                                |
| `vmi`      | VMI Compliance Agent                      | Regulation B §1002.13   |                                |
| `auditor`  | Compliance Auditor                        | Cross-regime            | Runs automatically after batch; its own `auditor_evaluate` tool reviews the other agents' results |
| `narrative`| Narrative Agent                           | Report generation       | Requires `--narrative-out`; no tool or decision record. Writes one summary of at most 150 words; code assembles the rest of the report |

---

## Setup

```bash
pip install -r requirements.txt
```

## Deterministic evaluators (MCP tools)

| Domain | Tool | Canonical input in the loan payload | Pack |
|---|---|---|---|
| YBS | `ybs_evaluate` | `ybs_case` | `compliance_mcp/ybs/pack/` |
| HPML | `hpml_evaluate` | `hpml_case` | `compliance_mcp/hpml/pack/` |
| TRID | `trid_evaluate` | `trid_case` | `compliance_mcp/trid/pack/` |
| HMDA | `hmda_evaluate` | `hmda_case` | `compliance_mcp/hmda/pack/` |
| ECOA | `ecoa_evaluate` | `ecoa_case` | `compliance_mcp/ecoa/pack/` |
| VMI | `vmi_evaluate` | `vmi_case` | `compliance_mcp/vmi/pack/` |
| FZD | `fzd_evaluate` | `fzd_case` | `compliance_mcp/fzd/pack/` |
| HVCRE | `hvcre_evaluate` | `hvcre_case` | `compliance_mcp/hvcre/pack/` |

Every domain agent is narrative-only and tool-backed. All packs are `draft_engineering_review`: the rule content is
cited to the pinned eCFR text, but compliance must review it before reliance. Scope of each evaluator, and what it
deliberately leaves to the reviewer:

- **HMDA (12 CFR part 1003):** coverage (institution, 1003.3(c) exclusions, agricultural / business-purpose judgments,
  volume thresholds); action-taken chronology; the rate spread **recomputed as APR minus the same APOR evidence HPML uses**;
  partial-exemption eligibility (1003.3(d)); and **all 38 LAR items of 1003.4(a)**, each with its own applicability (from
  `lar_context` facts), presence and value checks: the ULI and its Appendix C check digit, the Appendix B ethnicity / race / sex
  categories, the five-entry maximum and the visual-observation rules, location and census-tract conditions, and the Regulation Z
  disclosure-based items. An undetermined agricultural or business purpose yields `Potentially Covered`, never a guess. Value domains
  come from the regulation and Appendices B and C only; the FFIEC Filing Instructions Guide code lists are not scriptable and are not
  pinned.
- **ECOA / Regulation B (part 1002):** adverse-action definition, 30-day and 90-day notification deadlines, notice
  content and the specific-reasons standard, incompleteness notices, notice to the primary applicant, marital-status
  inquiry limits, spousal signature, age and public-assistance use. It never decides that discrimination occurred.
- **VMI (12 CFR 1002.13):** whether monitoring information must be *requested* (purchase/refinance of a 1-4 unit
  principal-residence dwelling secured by it), each of ethnicity / race / sex / marital status / age, declination notes,
  observation-or-surname notes, the applicant disclosure. Firewall and non-use rules are marked `institution_policy`.
- **FZD (FCA 12 CFR part 614 subpart S):** determination form use/retention, designated-loan test, required amount
  (lesser of balance and maximum available), policy acceptability, notice of special flood hazards, escrow and its
  exceptions, force placement after 45 days. It never makes a flood-zone determination.
- **HVCRE (12 CFR 628.2):** the three-prong test and every exclusion, including the 15% capital exclusion arithmetic;
  loans made before 2025-01-01 are not HVCRE. The Appendix A LTV limit is *not* pinned and is a supplied input.

Interpretations flagged for compliance review: TRID holiday calendar (Saturday holidays not shifted), FZD "reasonable
time" notice (delivered on a date before the transaction; same day is Review Required), and the VMI firewall rules.

HPML covers 12 CFR 1026.35 coverage (APR vs APOR spread by lien position, with `Decimal`
arithmetic) plus the escrow and appraisal obligations. APOR is supplied with its source
(`apor_reference`); the pack pins the regulation text and FHFA one-unit baseline limits, and
requires `applicable_conforming_limit` for first liens above the baseline. APOR is supplied per case and recorded
as evidence by `python -m intake.apor loan.json --write`; sources, caveats and the legacy tables: [`compliance_mcp/hpml/pack/APOR.md`](compliance_mcp/hpml/pack/APOR.md). Exemption
eligibility is a documented input fact, never inferred. `sample_loan.json` carries both
canonical cases.

TRID covers 12 CFR 1026.19(e)/(f): Loan Estimate within 3 creditor business days of application and
7 business days before consummation, Closing Disclosure 3 business days before consummation (mail and
electronic delivery presumed received 3 business days later), a new wait after APR/product/prepayment-penalty
changes, and zero/10% good-faith tolerances with the 60-day refund cure. Both Regulation Z business-day
definitions are implemented (`compliance_common/calendar.py`). The holiday calendar takes each holiday on its
own date (a Saturday holiday is not moved to Friday); compliance should confirm that reading.

## Builder agents (rebuild only what a rule change touches)

Two builder agents generate the evaluators and the narrative-only agents:
`builders/mcp_builder.md` (writes `compliance_mcp/<domain>/` and its tests) and
`builders/agent_builder.md` (writes `prompts/<key>.md`; the shared Output Contract in
`builders/narrative_contract.md` is injected verbatim by the harness).

They do not browse. [`builders/sources.yaml`](builders/sources.yaml) is the registry of canonical
Federal sources per domain (eCFR sections, FHFA, ...) plus spec sites; the harness fetches them
at build time and compares a hash of the normalized text with `builders/sources.lock.yaml`:

```bash
python -m builders.build check                  # what changed upstream? (writes nothing)
python -m builders.build run --domain trid      # stage proposed files under builds/ for review
python -m builders.build run --domain trid --apply --provider anthropic
python -m builders.build lock --domain trid     # accept current upstream text as reviewed
```

Only domains with a changed (or new) source are rebuilt, and only the components that actually
changed get a version bump (pack, evaluator, agent prompt are versioned independently). `--apply`
runs the domain's tests and rolls everything back on failure. Code, not the LLM, decides what
changed, which paths may be written (`compliance_mcp/<domain>/**` except `pack/sources/`, the
domain's tests, `prompts/<key>.md`), and what the new version numbers are. Sources that cannot be
fetched by script (e.g. the FFIEC APOR page, which blocks bots) are reported as `manual`. For local
models set `OLLAMA_NUM_CTX` large enough for the builder prompts, or use a remote model.

## Deterministic evaluator contract (YBS is the reference)

Every domain agent, and the auditor over the other agents' results, follows the same runtime contract: the agent calls its
evaluator's MCP tool (stdio server `python -m compliance_mcp.<domain>.server`), the harness pins the arguments to the canonical
case in the payload, code assembles the result, and a narrative the model adds is verified before it is used. A payload without
the canonical case yields `Unable To Determine` with no model call. `tests/test_agent_parity.py` proves this for every role in
`agents.yaml` offline: direct evaluation, in-process MCP, stdio MCP and an A2A task return the same decision id and classification,
in both tool modes, with the guard and fallback behavior. The auditor's input is the other agents' results rather than a
`<domain>_case`, and the narrative agent is prompt-only (no tool, decision or guard); neither is required to look like a domain.
The pilot section below describes YBS specifically. All packs, including YBS, are `draft_engineering_review` and need
compliance review before reliance; passing these tests is not compliance approval.

### YBS specifics

The YBS agent is narrative-only. It calls the `ybs_evaluate` MCP tool, which is the
authority for eligibility, thresholds, rule outcomes, and missing-fact status. The
harness pins the tool arguments to the `ybs_case` in the loan payload (the model cannot
alter facts), and `compliance_common/assemble.py` builds the result from the decision
record plus the model's prose. Decision-owned fields the model emits are stripped and
reported in `narrative_guard`. Results carry `decision` (the record), `tool_calls`, and
`narrative_guard`. Tool-backed agents declare `Tool:` in their prompt header. Use a canonical `ybs_case` object (see
[`sample_ybs_case.json`](sample_ybs_case.json)) inside a normal loan payload:

```json
{
  "case_information": {"case_id": "YBS-DETERMINISTIC-2026-001"},
  "ybs_case": {"evaluation_date": "2026-06-01", "subjects": []}
}
```

The canonical input and decision-record contracts live in
`compliance_mcp/ybs/pack/input.schema.json` and
`compliance_mcp/ybs/pack/decision-record.schema.json`. The evaluator is also an
MCP stdio server (`python -m compliance_mcp.ybs.server`, tool `ybs_evaluate`);
Versions are
inside the code (`EVALUATOR_VERSION`) and pack manifest, not file or directory names.

The YBS pack is marked `draft_engineering_review`. Its numeric
thresholds and entity-attribution method are explicit institution-pilot policy,
not claims that 12 CFR §614.4165 supplies those values. The dated eCFR snapshot
and provenance manifest are under `compliance_mcp/ybs/pack/`.
Canonical entity inputs now distinguish an organization, trust, successor, and
reorganization; trusts require trustee and controlling-person attribution, while
successors and reorganizations require documented attribution. Narrative input
and legacy `ybs_information` remain usable for discussion but produce `Unable To
Determine` until a canonical case is supplied.

The default suite runs deterministic fixtures, schema/source-manifest checks,
and Anthropic/Ollama/OpenAI/MCP contract parity with local fakes, including a registry-driven check of every role over
direct, in-process MCP, stdio MCP and A2A. The opt-in Gemma test
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
# Optional — defaults to claude-haiku-5-5
# COMPLIANCE_MODEL=claude-haiku-5-5
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

### Optional OpenAI runtime narrator

OpenAI is an optional runtime narrator provider; Anthropic remains the default.
Choose and record a model explicitly—there is no repository-wide OpenAI model
default. Install the normal requirements, then keep these values in an
untracked `.env` file or the process environment:

```
COMPLIANCE_PROVIDER=openai
COMPLIANCE_MODEL=<approved OpenAI model identifier>
OPENAI_API_KEY=<OpenAI API key>
# Optional: request timeout in seconds (default 60) and SDK retry count (default 2)
# OPENAI_TIMEOUT=60
# OPENAI_MAX_RETRIES=2
```

For a global replacement of the locally started agent backends, use the
environment above with a synthetic fixture first:

```bash
python -m orchestrator.cli batch sample_loan.json --spawn-local
```

OpenAI API use is billed separately from a ChatGPT subscription. Select a model
only after the owner has approved the cost, quality, and data-handling scope.
Start with synthetic or de-identified cases; a real record requires explicit
owner authority and the applicable data-handling review. The provider sends
`store: false` to the Responses API where supported, but that application
setting is not a substitute for an approved data-handling decision.

The approved synthetic YBS smoke-test plan has a separate, opt-in gate:

```bash
RUN_LIVE_OPENAI_TESTS=1 python3 -m unittest discover -s tests -p test_openai_live_smoke.py -v
```

It uses `gpt-6-luna`, the repository's synthetic YBS fixture, an in-process A2A
transport and real MCP evaluator. It sends the fixture, YBS prompt, pinned
regulation text and generated decision record to the OpenAI API. It limits each
cycle to six Responses requests and reserves against a cumulative $20 budget in
`plans/archive/openai-smoketest/runs.jsonl` before making requests. Unknown usage retains
its reservation. The ledger is tracked as plan evidence and must be preserved across
runs; deleting or replacing it defeats the cumulative budget check. Recheck
pricing and update its checked date and rates before running on a later day.
Normal test discovery skips the live gate unless explicitly enabled.

Two further opt-in gates run the whole registry (every domain role, the auditor and
the narrative role, in the model-directed and seeded phases) on the synthetic sample
loan and report per-role cost, latency and narrative sources:

```bash
RUN_LIVE_ANTHROPIC_PARITY=1 python3 -m unittest discover -s tests -p test_anthropic_live_parity.py -v
RUN_LIVE_OPENAI_PARITY=1 python3 -m unittest discover -s tests -p test_openai_live_parity.py -v
```

Each reserves its worst case first and then runs through a guarded client (no SDK
retries, a finite timeout, request and input-size caps, a model/tool/format
allow-list). Anthropic spend is tracked in `usage/anthropic-api-ledger.jsonl`, which
needs an owner-confirmed baseline recorded with
`scripts/anthropic_cost_estimator.py baseline`; OpenAI shares the ledger above. Both
ledgers are append-only plan evidence, and each gate must be preceded by a rate and
date recheck. Results and tolerated findings are in `plans/archive/live-parity/results.md`.
Normal discovery skips both.

For a mixed-provider run, copy `agents.yaml` to an untracked local file, retain
every existing entry, and change only the narrator roles. Do **not** set
`COMPLIANCE_PROVIDER=openai` for this mode: it would select OpenAI for entries
without their own provider. `seeded` is the preferred remote-narrator mode
because code obtains the canonical decision record before the remote model
receives it:

```yaml
# local/openai-narrators.yaml — copied from agents.yaml; excerpt only
agents:
  auditor:
    url: "http://127.0.0.1:9108/"
    provider: openai
    model: <approved OpenAI model identifier>
    tool_mode: seeded
  narrative:
    url: "http://127.0.0.1:9109/"
    provider: openai
    model: <approved OpenAI model identifier>
    tool_mode: seeded
```

```bash
python -m orchestrator.cli batch sample_loan.json \
  --config local/openai-narrators.yaml --spawn-local \
  --provider ollama --model gemma4:26b
```

This sends only `auditor` and `narrative` to OpenAI; the other copied agent
entries use the selected Ollama provider and model. To retain another provider
instead, replace the final `--provider` and `--model` values accordingly.

---

## CLI Usage

Every agent is an A2A server listed in [`agents.yaml`](agents.yaml) (URL, and
optionally provider/model). Local URLs are started by the CLI; remote URLs are
used as-is, so a local Ollama agent and a remote Claude agent can sit side by side.

### Run the agents

```bash
# Start all local agents and leave them running (Ctrl-C to stop)
python -m orchestrator.cli serve --provider ollama --model gemma4:26b
```

### Batch mode — agents run concurrently, then the auditor

```bash
# Against agents that are already running
python -m orchestrator.cli batch sample_loan.json

# Start the local agents just for this run (provider/model apply to them)
python -m orchestrator.cli batch sample_loan.json --spawn-local --provider ollama --model gemma4:26b

# Save JSON results and a Markdown narrative report
python -m orchestrator.cli batch sample_loan.json --json-out results.json --narrative-out report.md

# Selected agents only
python -m orchestrator.cli batch sample_loan.json --agents hmda ecoa hpml
```

A failing agent becomes a result with `parse_error` set; it does not stop the batch. The auditor lists it as missing (never as a
pass) and the narrative agent is given the failure, not a blank. If the narrative stage itself fails, the batch JSON is still
saved, no empty report is written, and the command exits 1.

### Chat / REPL mode — interactive session with one agent

Chat runs the agent in-process (the REPL keeps conversation history).

```bash
python -m orchestrator.cli chat hmda --provider ollama --model gemma4:26b
```

REPL commands:
- `exit` / `quit` — end session
- `reset` — clear history, start fresh with same agent
- `history` — print turn count
- `save <filename>` — write full session + last parsed result to JSON

### Local models: serialized calls and settings outside the repo

`agents.yaml` sets two widths. `concurrency: 1` is how many local (Ollama) agent calls run at once; `remote_concurrency: 8` is how
many Anthropic or OpenAI agent calls run at once (the highest clean width of a live ramp, see `plans/parallelize/results.md`; override with
`--remote-concurrency N`, or lower it if a provider rate-limits: that role then fails alone and the batch summary counts it). An agent's
provider is its `provider` entry, else `--provider`, else `COMPLIANCE_PROVIDER`, else anthropic. `--concurrency N` is different: it caps
every agent call at once (`--concurrency 1` forces a serial run) and, alone, sets both widths. The auditor and the narrative role still
run after the domain agents. To repeat the live measurement (needs `ANTHROPIC_API_KEY`, spends about USD 0.20):
`RUN_LIVE_ANTHROPIC_PARALLEL=1 python3 -m unittest discover -s tests -p test_anthropic_live_parallel.py -v`.
The cheapest setting that still passes the quality bar is measured by `python3 -m benchmarks.floor_sweep --dry-run` (offline, no spend;
`--live --provider anthropic` adds two one-request diagnostics, about USD 0.01). The dated result is `plans/archive/tune-ais/floor.md`.
Machine-specific settings (provider, model, `OLLAMA_NUM_CTX`, `OLLAMA_TIMEOUT`, log dir) belong
in files outside the repo, e.g. an env file plus a copy of `agents.yaml` passed with `--config`. The agents spawn the
MCP evaluators themselves over stdio (`python -m compliance_mcp.<domain>.server`), so no MCP registration is needed.
Model choice on an 8 GB GPU: Ollama can use only ~6 GB of it, so set `OLLAMA_NUM_CTX` deliberately. `granite4.1:3b` stays fully
on the GPU up to a 32k context and runs the eight evaluator-backed agents in ~15 s each; `granite4.1:8b` and `gemma4:26b` spill to
the CPU and are several times slower. Agents can use different models (`provider`/`model` per agent in the config), and a stronger
model is worth using for the cross-regime auditor and the narrative report, where small models were weaker.
The Ollama backend logs prompt/output token counts and warns when a prompt fills `OLLAMA_NUM_CTX` (silent truncation).

### Tool in hand, regulations as given, and tool modes

Every tool-backed prompt opens with `## Your Tool` (call the MCP tool first) and `## Your Role` (a narrator, not an investigator: no
independent research, no remembered law), inserted deterministically by `python -m builders.build prompts` from the tool name and case
key. At run time the agent's system prompt also gets `## Regulations As Given`: the pinned regulation text from the domain's own rule
pack (excerpted by the `excerpt` markers in its manifest), with citation, issue date and hash recorded in each result as
`regulations_given`. `agents.yaml` options per agent: `tool_mode: model` (default; the first Anthropic call is forced to use the tool;
otherwise the harness covers a model that does not call it) or `seeded` (the harness makes the call and presents it as the agent's own
first step; use it for small local models, which do not call tools reliably), `include_regulations`, and `templates`.

### Response templates: the loan-officer sheet and the examiner findings

Every result carries `response_templates` next to the decision record, both written from the record and the catalog in
`compliance_common/templates/catalog/` (outside every rule pack, so editing a sentence never changes a `decision_id`):

- `loan_officer`: what the customer's file still needs (`needed_from_customer`, short plain sentences; where the applicant may decline,
  it says to ask, that they may decline, and to record the decline) and what to refer to compliance (`refer_to_compliance`: facts about
  what the institution did, reviewer judgments and values that break a rule). A fact about what the institution did is never a customer request.
- `examiner`: one paragraph per finding in the order Requirement, Condition, Basis, Effect, Action, under a per-regime word limit
  (YBS 70, VMI 100, HPML 90, FZD 90, HVCRE 90, ECOA 100, TRID 100, auditor 110, HMDA 130; floor 25). An HMDA result with more than 20
  findings groups the LAR item findings by LAR section.

`templates: model` (default in `agents.yaml`) shows the model a code-written draft of each paragraph in the tool result and asks the same
narrative call to rephrase it. Each paragraph is checked on its own (parts and order, rule id and citation, the record's own words, the
outcome and result, length, no number, date or identifier the record lacks, no contradiction); one that fails drives the single retry, and
then code writes it. Each paragraph's `source` is `model`, `model_retry` or `code`. `templates: code` asks the model for nothing extra (no
extra output or request) and code writes every paragraph, which is the arm to compare when measuring a model. The sheet is always code.
A report is `batch ... --narrative-out`: code assembles the summary, the results table, the sheets and the findings; the model writes
only the summary, and if it is over 150 words or adds a fact, code writes the summary and the CLI says so.
`OLLAMA_THINK=true` turns on hidden reasoning for models that have it (off by default: it multiplies latency).

### Choosing a local model (accuracy, then speed, then fit)

`python -m benchmarks.model_bench --models ... --agents hpml hmda vmi ecoa --modes seeded` runs the real agents against each model and
records an accuracy score (is the classification stated, are the record's figures recalled correctly, is every missing fact raised, is
anything invented, is the compliance result contradicted), speed (seconds, tokens/s), and fit sampled twice a second (GPU memory and
utilization, CPU cores Ollama uses, its RAM, and what is left free for everything else). Raw results go to `benchmarks/*.jsonl`
(gitignored); the evidence and the decision are in [`benchmarks/RESULTS.md`](benchmarks/RESULTS.md).

#### Non-Gemma comparison on the sample loan (2026-10-12)

The four installed small local models were compared with `tool_mode: seeded`, all eight domain agents, a 32,768-token context, temperature 0.2,
four CPU threads, and seeds 42 and 7 (one run per model/agent/seed). The accuracy score is a heuristic measure of narrative faithfulness, not
the compliance decision. Means below cover 16 agent runs per model; seconds per agent are the mean across those runs.

| Model | Mean narrative score (population SD) | Mean seconds / agent | Peak GPU memory | Guarded fallbacks (16 runs) |
|---|---:|---:|---:|---:|
| `granite4.1:3b` | 95.3 (8.0) | 6.2 s | 3.63 GB | 1 |
| `qwen3.5:4b` | 96.2 (8.0) | 9.5 s | 4.25 GB | 1 |
| `lfm2.5:8b` | 90.0 (14.0) | 3.2 s | 5.27 GB | 1 |
| `ministral-3:3b` | 94.4 (11.0) | 8.6 s | 4.88 GB | 1 |

Scores varied by as much as 30 points among individual cells. This is a single sample loan and two seeds, so the small mean-score differences
do not establish a reliable accuracy ranking. LFM2.5 was fastest per agent, but also had the lowest mean and highest peak GPU use; its full-run
TRID narrative was rejected by the grounding guard. Granite was a strong speed/fit compromise, while Qwen had the highest mean score in this
small run. All four models fit on the GPU in this configuration.

Each model was also run once through the complete sample pipeline, including the eight domain agents, the cross-regime auditor, and the final
report. The eight domain agents and auditor took a summed 68-98 seconds per model; report generation added about 38 seconds for Granite,
65 for Qwen, 41 for LFM2.5, and 101 for Ministral. All four produced the same core deterministic outcomes and auditor decision. The full
reports were not uniformly reliable: LFM2.5's exported Markdown included an inline `<think>` block and instruction-like prompt text, and its
TRID narrative fell back to the deterministic version after unsupported numbers were rejected. Treat reports as drafts for review, not as
authoritative compliance conclusions.

For a reproducible comparison, run from the repository root with the project virtual environment active and Ollama running:

```bash
OLLAMA_NUM_THREAD=4 OLLAMA_TEMPERATURE=0.2 OLLAMA_SEED=42 \
python -m benchmarks.model_bench \
  --models granite4.1:3b qwen3.5:4b lfm2.5:8b ministral-3:3b \
  --agents hmda ecoa hvcre hpml trid fzd ybs vmi \
  --modes seeded --ctx 32768 --reps 1 --out /tmp/small-models-seed42.jsonl
```

Repeat with `OLLAMA_SEED=7` and a different output file for the second seed. The full-pipeline command requires a config copy that sets
`tool_mode: seeded` on the eight tool-backed domain agents; point `--config` at that copy:

```bash
OLLAMA_NUM_CTX=32768 OLLAMA_NUM_THREAD=4 OLLAMA_TEMPERATURE=0.2 OLLAMA_SEED=42 \
python -m orchestrator.cli batch sample_loan.json --config /path/to/seeded-agents.yaml \
  --spawn-local --provider ollama --model granite4.1:3b \
  --json-out /tmp/granite-results.json --narrative-out /tmp/granite-report.md
```

Change the model and output filenames to repeat the full run for each candidate. On the tested WSL machine, the Ollama service was configured
with `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_NUM_PARALLEL=1`, and `OLLAMA_MAX_LOADED_MODELS=1`; these service-level
settings were active during the comparison, but were not varied as part of it.

The practical starting choice remains `granite4.1:3b` for the eight domain agents and `qwen3.5:4b` for synthesis when prioritizing a clearer
cross-regime report over latency. This is a role-based starting point, not a winning-model claim: all compliance outcomes are code-owned and
all generated narratives and reports require review. Small local models are not dependable MCP tool callers, so use `tool_mode: seeded`.
On Ollama, a seeded agent's final response is constrained to `compliance_common/narrative_schema.py`; it writes reasoning, examiner narrative,
and follow-ups for its own domain case and decision record, while evidence, data-quality, change, and scope blocks come from code.
`compliance_common/narrative.py:check_narrative` checks numbers, dates, identifiers, contradictions, and empty output, retries once, then uses a
deterministic fallback if necessary. The decision record always governs.

### Logging

`COMPLIANCE_LOG_LEVEL` = `INFO` (default) | `DEBUG` | `TRACE`. Records are JSONL on
stderr and in `logs/<component>.jsonl`, each with `run_id`, component, component
version and `decision_id`. `TRACE` adds full prompts (which carry the agent version
in their first line), raw model text and tool results.

---

## Programmatic Usage

```python
import asyncio, json
from orchestrator.batch import run_batch
from orchestrator.config import load_agents
from orchestrator.cli import call_agent   # in-process single agent

with open("sample_loan.json") as f:
    loan = json.load(f)

# Run the configured A2A agents concurrently (they must be running: see `serve`)
results = asyncio.run(run_batch(loan, load_agents()))

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

1. Add `prompts/<key>.md`. Line 1 is the header (`Agent: … | Name: … | Agent Version: … | Track: … | Output: …`);
   `agent_prompts.py` loads it.
2. The new key is immediately available to `run_batch()` and `call_agent()`.
3. Add it to `agents.yaml` (a URL; `serve` starts it).

---

## Notes

- **Concurrent, independent agents**: domain agents run in parallel over A2A. No
  domain agent sees another's output; only the auditor and narrative agents do.
- **Conversation history**: the REPL maintains in-memory history per session only.
  Use `save <filename>` to persist a session for audit purposes.
- **Model pinning**: set `COMPLIANCE_MODEL` in `.env` to lock a specific model
  version for reproducibility, or pass `model=` / `--model` for a single run.
- **Token budget**: `MAX_TOKENS=8192` covers full structured output. Increase if
  a specific agent consistently truncates.
