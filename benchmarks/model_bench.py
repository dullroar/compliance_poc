"""Compare local Ollama models on the actual job: narrate a deterministic decision record, with the tool in hand.

  python -m benchmarks.model_bench --models granite4.1:3b lfm2.5:8b --agents hpml hmda vmi --modes model seeded --ctx 16384

For each model x agent x tool mode it runs the real agent runner against sample_loan.json and records:
  seconds, Ollama prompt/output tokens, who made the tool call (model / seeded / harness), whether the output parsed, the
  grounding guard (evidence or identifiers the input does not support), and `unsupported_numbers`: numbers in the narrative
  that appear in neither the decision record, the loan input nor the regulation text it was given (a hallucination proxy).
It also records how much of the model Ollama put on the GPU. Classification is not scored: code decides it, so every model
gets it right by construction. What differs between models is speed, tool use and narrative faithfulness.

Priorities, in order: ACCURACY, SPEED, FIT.
  accuracy  a 0-100 score of how faithfully the narrative reflects the decision record (see `score_narrative`): the
            classification is stated, the record's key figures appear and are right, each missing fact is raised, nothing is
            invented, and the narrative does not contradict the compliance result. A heuristic: read the narratives too.
  speed     wall seconds and generated tokens per second.
  fit       sampled twice a second while the model runs: GPU memory and utilization, CPU cores Ollama is using, Ollama's RAM, and
            what is left over for everything else (free GPU memory, idle cores, free RAM).
"""
from __future__ import annotations

import argparse
import importlib
import subprocess
import threading
import json
import os
import re
import sys
import time
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def ollama(path: str, body: dict | None = None) -> dict:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    request = urllib.request.Request(f"{base}{path}", data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)


def unload_all() -> None:
    for model in ollama("/api/ps").get("models", []):
        ollama("/api/generate", {"model": model["name"], "keep_alive": 0})
    time.sleep(2)


def residency(model: str) -> dict:
    for m in ollama("/api/ps").get("models", []):
        if m["name"] == model:
            return {"total_gb": round(m["size"] / 1e9, 2), "gpu_gb": round(m["size_vram"] / 1e9, 2), "fully_on_gpu": m["size"] == m["size_vram"]}
    return {}


def narrative_text(parsed: dict) -> str:
    summary = parsed.get("compliance_determination_summary") or {}
    parts = [str(summary.get(k, "")) for k in ("reasoning", "examiner_narrative", "status_change_narrative")]
    parts += [str(x) for x in summary.get("data_gaps_followups", [])]
    return "\n".join(parts)


def unsupported_numbers(text: str, haystack: str) -> list[str]:
    norm = lambda s: s.replace(",", "")  # noqa: E731
    hay = norm(haystack)
    found = {n.rstrip(".") for n in re.findall(r"\d[\d,]*\.?\d*", text)}
    return sorted(n for n in found if (len(n) > 1 or "." in n) and norm(n) not in hay)


class ResourceSampler:
    """Samples the machine twice a second while a model runs (WSL: /proc for CPU and RAM, nvidia-smi for the GPU)."""

    def __init__(self, interval: float = 0.5) -> None:
        self.interval, self.rows, self._stop, self._thread = interval, [], threading.Event(), None
        self.cores = os.cpu_count() or 1

    @staticmethod
    def _pids() -> list[int]:
        pids = []
        for entry in Path("/proc").iterdir():
            if entry.name.isdigit():
                try:
                    if (entry / "comm").read_text().strip() in ("llama-server", "ollama"):
                        pids.append(int(entry.name))
                except OSError:
                    pass
        return pids

    @staticmethod
    def _jiffies(pid: int) -> int:
        try:
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
            return int(fields[11]) + int(fields[12])
        except (OSError, IndexError, ValueError):
            return 0

    @staticmethod
    def _rss_kb(pid: int) -> int:
        try:
            for line in Path(f"/proc/{pid}/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
        except (OSError, ValueError):
            pass
        return 0

    @staticmethod
    def _cpu_total() -> tuple[int, int]:
        values = list(map(int, Path("/proc/stat").read_text().splitlines()[0].split()[1:]))
        return sum(values), values[3] + values[4]            # total, idle + iowait

    @staticmethod
    def _gpu() -> tuple[float, float, float]:
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=5).stdout.strip().split(",")
            return float(out[0]), float(out[1]) / 1024, float(out[2]) / 1024
        except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
            return 0.0, 0.0, 0.0

    @staticmethod
    def _mem_available_gb() -> float:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1048576
        return 0.0

    def _loop(self) -> None:
        pids = self._pids()
        prev_total, prev_idle = self._cpu_total()
        prev_proc = sum(self._jiffies(p) for p in pids)
        while not self._stop.wait(self.interval):
            pids = self._pids()
            total, idle = self._cpu_total()
            proc = sum(self._jiffies(p) for p in pids)
            d_total = max(total - prev_total, 1)
            util, gpu_used, gpu_total = self._gpu()
            self.rows.append({
                "ollama_cores": max(proc - prev_proc, 0) / d_total * self.cores,
                "machine_busy_cores": (d_total - (idle - prev_idle)) / d_total * self.cores,
                "ollama_rss_gb": sum(self._rss_kb(p) for p in pids) / 1048576,
                "ram_available_gb": self._mem_available_gb(), "gpu_util": util, "gpu_used_gb": gpu_used, "gpu_total_gb": gpu_total,
            })
            prev_total, prev_idle, prev_proc = total, idle, proc

    def __enter__(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def summary(self) -> dict:
        rows = self.rows
        if not rows:
            return {}
        mean = lambda k: sum(r[k] for r in rows) / len(rows)  # noqa: E731
        peak = lambda k: max(r[k] for r in rows)  # noqa: E731
        trough = lambda k: min(r[k] for r in rows)  # noqa: E731
        return {"cores_total": self.cores, "gpu_util_mean": round(mean("gpu_util")), "gpu_util_peak": round(peak("gpu_util")),
                "gpu_used_peak_gb": round(peak("gpu_used_gb"), 2), "gpu_free_min_gb": round(trough("gpu_total_gb") - peak("gpu_used_gb"), 2),
                "ollama_cores_mean": round(mean("ollama_cores"), 1), "ollama_cores_peak": round(peak("ollama_cores"), 1),
                "machine_busy_cores_mean": round(mean("machine_busy_cores"), 1), "idle_cores_min": round(self.cores - peak("machine_busy_cores"), 1),
                "ollama_rss_peak_gb": round(peak("ollama_rss_gb"), 2), "ram_available_min_gb": round(trough("ram_available_gb"), 1), "samples": len(rows)}


def _decimals(text: str) -> set[Decimal]:
    found = set()
    for token in re.findall(r"\d[\d,]*\.?\d*", text):
        try:
            found.add(Decimal(token.replace(",", "").rstrip(".")))
        except InvalidOperation:
            pass
    return found


_NEGATION = re.compile(r"\b(not|no|non|neither|never|without|n't)\b|n't\b", re.I)


def states_classification(classification: str, text: str) -> bool:
    """Does the narrative state the classification? Exact wording, or all its significant words in one sentence, with a negation
    in that sentence when the classification is itself negative ('Not HPML' is stated by 'does not meet the definition of an HPML')."""
    lowered = text.lower()
    if classification.lower() in lowered:
        return True
    negative = bool(re.match(r"(not|no|non)[\s-]", classification, re.I))
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", re.sub(r"^(not|no|non)[\s-]", "", classification, flags=re.I).lower()) if len(t) > 1]
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        low = sentence.lower()
        if tokens and all(t in low for t in tokens) and (not negative or _NEGATION.search(sentence)):
            return True
    return False


def score_narrative(decision: dict, parsed: dict, text: str, guard: dict, unsupported: list[str]) -> dict:
    """0-100 faithfulness of a narrative to its decision record. Heuristic; classification is code-decided so it is scored only
    as 'does the narrative state it'. Components (weights): states the classification (20), recalls the record's key figures
    and dates (30), raises each missing fact (20), invents nothing (20), does not contradict the compliance result (10)."""
    lowered = text.lower()
    if len(text.strip()) < 80:        # an empty or near-empty narrative did not do the job, whatever else is true of it
        return {"accuracy": 0, "classification_stated": False, "figure_recall": 0.0, "gap_recall": 0.0, "invented_items": 0, "polarity_ok": True,
                "figures_wanted": 0, "gaps_wanted": 0, "no_narrative": True}
    classification_ok = states_classification(decision["final_classification"], text)
    figures, dates = set(), set()
    for r in decision.get("rule_results", []):
        for key in ("value", "threshold"):
            if r.get(key) is not None:
                try:
                    figures.add(Decimal(str(r[key])))
                except InvalidOperation:
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r[key])):
                        dates.add(str(r[key]))
        if r.get("outcome") in ("not_satisfied", "unable_to_determine", "review_required"):
            dates.update(re.findall(r"\d{4}-\d{2}-\d{2}", r.get("message", "")))
    wanted = [("n", f) for f in sorted(figures)[:12]] + [("d", d) for d in sorted(dates)[:6]]
    present = _decimals(text)
    hit = sum(1 for kind, v in wanted if (v in present if kind == "n" else v in text))
    figure_recall = hit / len(wanted) if wanted else 1.0
    gaps = decision.get("missing_facts", [])[:10]
    def gap_hit(m: dict) -> bool:
        name = re.sub(r"^(lar_context|lar)\.", "", str(m.get("field", ""))).split(".")[-1].lower()
        tokens = [t for t in re.split(r"[_/\s]+", name) if len(t) > 3]
        return name.replace("_", " ") in lowered.replace("_", " ") or (bool(tokens) and all(t in lowered for t in tokens))
    gap_recall = sum(1 for m in gaps if gap_hit(m)) / len(gaps) if gaps else 1.0
    invented = len(unsupported) + len(guard.get("violations", [])) + len(guard.get("stripped_fields", []))
    halluc_ok = max(0.0, 1 - 0.25 * invented)
    negative = re.search(r"non-?\s?compliant|violat|deficien|not satisfied|fails?\b|failure", lowered)
    positive = re.search(r"(?<!non-)(?<!non )(?<!not )\bcompliant\b|fully compl|meets all", lowered)
    result = decision["compliance_result"]
    polarity_ok = not ((result in ("Compliant", "Not Applicable") and negative and not positive) or (result == "Non-Compliant" and positive and not negative))
    score = 100 * (0.20 * classification_ok + 0.30 * figure_recall + 0.20 * gap_recall + 0.20 * halluc_ok + 0.10 * polarity_ok)
    return {"accuracy": round(score), "classification_stated": classification_ok, "figure_recall": round(figure_recall, 2), "gap_recall": round(gap_recall, 2),
            "invented_items": invented, "polarity_ok": polarity_ok, "figures_wanted": len(wanted), "gaps_wanted": len(gaps), "no_narrative": False}


def run_one(model: str, agent: str, mode: str, ctx: int, sample: dict) -> dict:
    os.environ["OLLAMA_NUM_CTX"] = str(ctx)
    from agents import backends
    from agents.runner import run_agent
    from compliance_common.regulations import regulation_text
    stats = {"prompt_tokens": 0, "output_tokens": 0, "calls": 0}
    original = backends.OllamaClient._chat

    def counting(self, payload):
        body = original(self, payload)
        stats["prompt_tokens"] += body.get("prompt_eval_count") or 0
        stats["output_tokens"] += body.get("eval_count") or 0
        stats["calls"] += 1
        return body
    backends.OllamaClient._chat = counting
    server = importlib.import_module(f"compliance_mcp.{agent}.server").server
    started = time.monotonic()
    sampler = ResourceSampler()
    try:
        with sampler:
            result = run_agent(agent, sample, backends.Backend("ollama", model), tool_target=server, options={"tool_mode": mode})
    except Exception as exc:  # a model that errors is a result, not a crash
        return {"model": model, "agent": agent, "mode": mode, "error": f"{type(exc).__name__}: {exc}"[:200]}
    finally:
        backends.OllamaClient._chat = original
    seconds = time.monotonic() - started
    parsed = result["parsed"]
    text = narrative_text(parsed)
    haystack = json.dumps(result["decision"]) + json.dumps(sample) + regulation_text(agent)[0]
    guard = result["narrative_guard"]
    unsupported = unsupported_numbers(text, haystack)
    return {"model": model, "agent": agent, "mode": mode, "seconds": round(seconds, 1), **stats,
            "tokens_per_second": round(stats["output_tokens"] / seconds, 1) if seconds else 0,
            **score_narrative(result["decision"], parsed, text, guard, unsupported), **sampler.summary(),
            "narrative": text[:2500],
            "tool_by": [c["by"] for c in result["tool_calls"]], "parse_ok": result["parse_error"] is None,
            "narrative_source": guard.get("source"), "first_attempt_violations": guard.get("violations", []), "retry_violations": guard.get("retry_violations", []),
            "stripped_fields": guard.get("stripped_fields"), "unsupported_numbers": unsupported,
            "narrative_chars": len(text), "mentions_classification": parsed["domain_determination"]["classification"].lower() in text.lower(),
            "followups": len((parsed.get("compliance_determination_summary") or {}).get("data_gaps_followups", [])),
            "reasoning": (parsed.get("compliance_determination_summary") or {}).get("reasoning", "")[:700], **residency(model)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--agents", nargs="+", default=["hpml", "hmda", "vmi"])
    parser.add_argument("--modes", nargs="+", default=["model", "seeded"], choices=["model", "seeded"])
    parser.add_argument("--ctx", type=int, default=16384)
    parser.add_argument("--reps", type=int, default=1, help="repeat each cell (only useful with temperature > 0)")
    parser.add_argument("--out", default="benchmarks/results.jsonl")
    args = parser.parse_args()
    os.environ.setdefault("COMPLIANCE_LOG_LEVEL", "WARNING")
    os.environ.setdefault("COMPLIANCE_LOG_DIR", str(REPO / "logs"))
    os.environ.setdefault("OLLAMA_TIMEOUT", "1500")
    sample = json.loads((REPO / "sample_loan.json").read_text(encoding="utf-8"))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for model in args.models:
        unload_all()
        for agent in args.agents:
            for mode, rep in ((m, r) for m in args.modes for r in range(args.reps)):
                row = {**run_one(model, agent, mode, args.ctx, sample), "rep": rep}
                with out.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row) + "\n")
                print(f"{model:18} {agent:6} {mode:7} r{rep} " + (row.get("error") or f"{row['seconds']:>6.1f}s {row['tokens_per_second']:>6.1f}tok/s acc={row['accuracy']:>3} tool={row['tool_by']} "
                      f"gpu={row.get('gpu_used_peak_gb')}GB/{row.get('gpu_util_mean')}% cores={row.get('ollama_cores_mean')} ram_free={row.get('ram_available_min_gb')}GB"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
