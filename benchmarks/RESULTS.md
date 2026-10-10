# Local model selection (2026-10-09)

Machine: RTX 5070 Laptop (8 GB; Ollama can use ~6.1 GB of it), 20 CPU cores, 31 GB RAM, Ollama 0.32.14 as a systemd service in WSL.
Priorities, in order: **accuracy, speed, fit** (including "can the machine still be used while the model runs").

Method: `python -m benchmarks.model_bench`. The real agent runner narrates the real deterministic decision record for
`sample_loan.json`, with the tool in hand (`tool_mode: seeded`), the pinned regulation text in the system prompt, and the final
answer constrained to the narrative JSON schema. Temperature 0.2, fixed seed. Context 16,384.

## Findings that shaped the setup

| Finding | Evidence | Consequence |
|---|---|---|
| No model under ~9B reliably calls its MCP tool itself | lfm2.5:8b, granite4.1:3b, gemma4:e4b, ministral-3:3b used the harness every time; qwen3.5:4b sometimes | `tool_mode: seeded` for small local models (also one model call instead of two) |
| Free-form JSON from small models fails in three ways: prose instead of JSON, wrong keys, inline `<think>` blocks | zero-score cells for 4 of 5 models before the fix | final answer is constrained to `NARRATIVE_SCHEMA` (Ollama `format`); no zeros afterwards; LFM2.5 went from 20-70 s to 4-9 s per agent |
| llama.cpp spins ~10 of 20 cores even for a model fully on the GPU | `ollama_cores` ~10 for every model | `OLLAMA_NUM_THREAD=4`: ~2 cores used, no loss of speed (10.6 s vs 12.0 s) |
| Only ~6.1 GB of 8 GB VRAM is usable | granite4.1:8b needs 6.8 GB at an 8k context and always spills to CPU (~2000% CPU, 13-20 tok/s); gemma4:26b likewise | models must be ~4-5 GB or smaller at the context in use |
| Hidden "thinking" tokens multiply latency | gemma4:26b emitted ~2,300 tokens before a short tool call | `think: false` unless `OLLAMA_THINK=true` |

## Accuracy (0-100 heuristic) and speed, both seeds (12 runs per model)

The score weighs: classification stated (20), the record's key figures recalled (30), each missing fact raised (20), nothing
invented (20), no contradiction of the compliance result (10); an empty narrative scores 0. It is a proxy; narratives were also read.

| Model | Accuracy mean (sd) | Worst cell | Seconds per agent | All 8 agents | GPU peak / free | Idle cores (min) |
|---|---|---|---|---|---|---|
| qwen3.5:4b | 86 (15) | 60 | 46 | 359 s | 4.2 / 3.8 GB | 6.7 |
| granite4.1:3b | 84 (13) | 65 | 16 | 150 s | 3.5 / 4.4 GB | 5.9 |
| gemma4:e4b | 84 (13) | 50 | 27 | 224 s | 4.8 / 3.2 GB | 2.0 |
| lfm2.5:8b | 80 (17) | 50 | 6 | 45 s | 5.2 / 2.8 GB | 6.6 |
| ministral-3:3b (one seed, dropped) | 78 | 50 | 58 | n/a | 4.8 / 3.2 GB | 4.7 |

**How to read it.** With 12 runs per model the standard error is about 4-5 points and a cell moves 5-14 points between seeds, so qwen,
granite and gemma e4b are statistically tied on accuracy; lfm2.5 is slightly behind and has misstated legal triggers when read closely.
Speed and footprint are the decisive differences. Ministral invents the most (1-3 unsupported items per run) and is slowest.

## Decision

* **Eight domain agents (each narrates one decision record): `granite4.1:3b`**, `tool_mode: seeded`. Tied for best accuracy, 3x
  faster than qwen, smallest footprint (3.5 GB; 4.4 GB of VRAM left free), fully on the GPU up to a 32k context.
* **Cross-regime audit narrative and final report (synthesis over many results): `qwen3.5:4b`.** On identical input granite wrote
  "the loan satisfies the statutory requirements of each individual regulation" in two separate runs while VMI was Non-Compliant;
  qwen led with the correct overall verdict and used the exact status labels. It costs about 70 s once per loan.
* Server/process: `OLLAMA_NUM_THREAD=4`, `OLLAMA_NUM_CTX=32768`, `OLLAMA_TEMPERATURE=0.2`, `OLLAMA_SEED=42`.
* Not retested after the first measurements (known bad fits here): granite4.1:8b, gemma4:26b.

## Caveats

* One sample loan; one run per cell per seed. Run-to-run variance exists even with a fixed seed (the same ECOA cell scored 70 and 85).
  The decision record is exact and code-owned; only the prose varies.
* The accuracy score is heuristic. Re-run with more loans before treating small differences as real.
* The FFIEC HMDA Filing Instructions Guide code lists are not pinned, so HMDA free-form items are checked for presence only.

## Narrate-only tightening (same day, after the table above)

Change: models write reasoning / examiner narrative / follow-ups only, see only their own case plus the decision record, and every
narrative is fact-checked (numbers, dates, identifiers vs record + case + regulation text; contradiction of the result; emptiness) with
one retry and then a code-written fallback. Evidence, data-quality and change blocks are code-derived.

granite4.1:3b, seeded, ctx 32768, 8 domain agents, seeds 42 and 7 (one run per cell): accuracy mean 92.5 and 88.8 (previous table: 84, with
the old scorer counting guard-removed evidence as invented), 3-7 s per agent. First-attempt rejections: 2/8 (seed 42), 1/8 (seed 7); the retry
did not rescue the two HPML/VMI cases, so code wrote those narratives (accuracy of a fallback narrative is lower on the heuristic because it
states figures less richly: 65-95). Earlier claims about hallucinated "compliance" and "invented evidence" were overstated: see MEMORY.md.
Caveat: 16 cells, one loan; treat as direction, not a ranking.
