import argparse
import asyncio
import json
import os
import tempfile
import unittest
from unittest import mock

from agent_prompts import AGENTS
from compliance_mcp.auditor.adapter import tool_arguments
from orchestrator import batch, cli, launcher
from orchestrator.config import load_agents

CONFIG = {k: {"url": f"http://127.0.0.1:99{i:02d}/"} for i, k in enumerate(["hmda", "ecoa", "hpml", "ybs", "auditor"])}


def run_with(concurrency):
    state = {"now": 0, "peak": 0, "order": []}

    async def fake_send(url, payload, httpx_client=None):
        state["now"] += 1
        state["peak"] = max(state["peak"], state["now"])
        state["order"].append(url)
        await asyncio.sleep(0.02)
        state["now"] -= 1
        return {"parsed": {"ok": True}, "raw_text": ""}

    with mock.patch.object(batch, "send", fake_send):
        results = asyncio.run(batch.run_batch({"loan": 1}, CONFIG, agents=["hmda", "ecoa", "hpml", "ybs"], verbose=False, concurrency=concurrency))
    return state, results


class ConcurrencyTests(unittest.TestCase):
    def test_default_is_one_call_at_a_time_then_the_auditor(self):
        state, results = run_with(1)
        self.assertEqual(state["peak"], 1)
        self.assertEqual(state["order"][-1], CONFIG["auditor"]["url"])      # the auditor always runs last
        self.assertEqual(list(results), ["hmda", "ecoa", "hpml", "ybs", "auditor"])
        self.assertTrue(all("elapsed_seconds" in r for r in results.values()))

    def test_higher_concurrency_overlaps_calls(self):
        state, _ = run_with(4)
        self.assertGreater(state["peak"], 1)


REGISTRY = load_agents()
DOMAINS = [k for k in REGISTRY if AGENTS[k].get("tool") and k != "auditor"]


class Transport:
    """A fake A2A transport that records every call and fails the roles named in `fail`."""

    def __init__(self, fail=()):
        self.fail, self.calls, self.now, self.peak = set(fail), [], 0, 0

    async def __call__(self, url, payload, httpx_client=None):
        key = url.rstrip("/").rsplit("/", 1)[1]
        self.calls.append((key, payload))
        self.now += 1
        self.peak = max(self.peak, self.now)
        await asyncio.sleep(0.01)
        self.now -= 1
        if key in self.fail:
            raise RuntimeError(f"{key} unreachable")
        return {"parsed": None, "raw_text": "# Report"} if key == "narrative" else {"parsed": self.parsed(key), "raw_text": "{}"}

    @staticmethod
    def parsed(key):
        return {"agent": key, "domain_determination": {"classification": "Fake"}, "determination_status": {"result": "Compliant"}}

    @property
    def order(self):
        return [k for k, _ in self.calls]

    def payload(self, key):
        return next(p for k, p in self.calls if k == key)


CONFIG_ALL = {k: {"url": f"http://127.0.0.1:9{i:03d}/{k}"} for i, k in enumerate(REGISTRY)}


def run_all(transport, **kw):
    with mock.patch.object(batch, "send", transport):
        return asyncio.run(batch.run_batch({"loan": 1}, CONFIG_ALL, verbose=False, **kw))


class WholeRegistryBatchTests(unittest.TestCase):
    def test_the_default_selection_is_every_registered_domain_then_the_auditor_and_never_the_narrator(self):
        self.assertEqual(batch.domain_keys(CONFIG_ALL), DOMAINS)
        self.assertEqual(len(DOMAINS), 8)
        transport = Transport()
        results = run_all(transport)
        self.assertEqual(transport.order, DOMAINS + ["auditor"])
        self.assertEqual(list(results), DOMAINS + ["auditor"])
        self.assertNotIn("narrative", transport.order)

    def test_concurrency_is_bounded_across_the_whole_registry_and_the_auditor_still_runs_last(self):
        for bound in (1, 3):
            with self.subTest(bound=bound):
                transport = Transport()
                run_all(transport, concurrency=bound)
                self.assertEqual(transport.peak, bound)
                self.assertEqual(transport.order[-1], "auditor")
                self.assertEqual(set(transport.order[:-1]), set(DOMAINS))

    def test_a_selection_runs_only_those_domains_in_the_order_given_and_unknown_keys_are_rejected(self):
        transport = Transport()
        results = run_all(transport, agents=["vmi", "hmda"])
        self.assertEqual(list(results), ["vmi", "hmda", "auditor"])
        for bad in (["nope"], ["hmda", "nope"]):
            with self.assertRaisesRegex(ValueError, "Unknown or unconfigured"):
                run_all(Transport(), agents=bad)
        with mock.patch.dict(AGENTS, {"extra": {"key": "extra", "name": "Extra", "version": "1", "compliance_track": "t", "system_prompt": "x"}}):
            with self.assertRaisesRegex(ValueError, "Unknown or unconfigured"):      # known prompt, not in this registry
                run_all(Transport(), agents=["extra"])

    def test_one_failing_domain_is_visible_and_the_others_and_the_auditor_still_run(self):
        transport = Transport(fail=["ecoa"])
        results = run_all(transport)
        self.assertEqual(list(results), DOMAINS + ["auditor"])
        self.assertIsNone(results["ecoa"]["parsed"])
        self.assertEqual(results["ecoa"]["parse_error"], "RuntimeError: ecoa unreachable")
        self.assertIn("elapsed_seconds", results["ecoa"])
        for key in set(DOMAINS) - {"ecoa"}:
            self.assertEqual(results[key]["parsed"], Transport.parsed(key))
        self.assertEqual(results["auditor"]["parsed"], Transport.parsed("auditor"))
        self.assertEqual(transport.payload("auditor")["agent_results"]["ecoa"]["status"], "failed")

    def test_the_real_auditor_adapter_reports_the_failed_domain_as_missing_not_as_a_pass(self):
        transport = Transport(fail=["hmda", "fzd"])
        run_all(transport)
        canonical, _ = tool_arguments(transport.payload("auditor"))
        self.assertEqual(sorted(canonical["case"]["failed_agents"]), ["fzd", "hmda"])
        self.assertEqual(sorted(canonical["case"]["results"]), sorted(set(DOMAINS) - {"hmda", "fzd"}))      # the rest are reviewed

    def test_a_failed_auditor_is_a_visible_failed_result_beside_the_surviving_domain_results(self):
        results = run_all(Transport(fail=["auditor"]))
        self.assertEqual(results["auditor"]["parse_error"], "RuntimeError: auditor unreachable")
        self.assertTrue(all(results[k]["parsed"] for k in DOMAINS))

    def test_the_narrative_runs_only_after_the_auditor_and_is_given_failure_evidence_not_blanks(self):
        transport = Transport(fail=["trid"])
        with mock.patch.object(batch, "send", transport):
            results = asyncio.run(batch.run_batch({"loan": 1}, CONFIG_ALL, verbose=False))
            self.assertNotIn("narrative", transport.order)
            narrative = asyncio.run(batch.run_narrative(results, CONFIG_ALL, verbose=False))
        self.assertEqual(transport.order, DOMAINS + ["auditor", "narrative"])
        self.assertEqual(narrative["raw_text"], "# Report")
        given = transport.payload("narrative")
        self.assertEqual(list(given), DOMAINS + ["auditor"])
        self.assertEqual(given["trid"], {"agent_key": "trid", "status": "failed", "failure": "RuntimeError: trid unreachable"})
        self.assertEqual(given["auditor"], Transport.parsed("auditor"))
        self.assertNotIn("", given.values())

    def test_a_failed_narrative_is_a_visible_failed_result(self):
        with mock.patch.object(batch, "send", Transport(fail=["narrative"])):
            narrative = asyncio.run(batch.run_narrative({"hmda": {"parsed": {"a": 1}, "raw_text": ""}}, CONFIG_ALL, verbose=False))
        self.assertEqual((narrative["raw_text"], narrative["parsed"]), ("", None))
        self.assertEqual(narrative["parse_error"], "RuntimeError: narrative unreachable")

    def test_downstream_stages_see_parsed_then_raw_text_then_failure_evidence(self):
        seen = batch._as_text_or_parsed({
            "a": {"parsed": {"x": 1}, "raw_text": "ignored"},
            "b": {"parsed": None, "raw_text": "prose answer", "parse_error": "not JSON"},
            "c": {"parsed": None, "raw_text": "", "parse_error": "boom"},
            "d": {"parsed": None, "raw_text": ""},
        })
        self.assertEqual(seen["a"], {"x": 1})
        self.assertEqual(seen["b"], "prose answer")
        self.assertEqual(seen["c"], {"agent_key": "c", "status": "failed", "failure": "boom"})
        self.assertEqual(seen["d"]["failure"], "the agent returned no output")


class BatchCommandTests(unittest.TestCase):
    """`orchestrator.cli batch`: the narrative stage is opt-in, follows the auditor and its failure is not hidden."""

    @staticmethod
    def load(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def run_cli(self, transport, narrative):
        directory = tempfile.mkdtemp()
        loan = os.path.join(directory, "loan.json")
        with open(loan, "w", encoding="utf-8") as f:
            json.dump({"loan": 1}, f)
        args = argparse.Namespace(loan_file=loan, config=None, concurrency=1, agents=["hmda", "ybs"], spawn_local=False, provider=None, model=None,
                                  json_out=os.path.join(directory, "results.json"), narrative_out=os.path.join(directory, "report.md") if narrative else None)
        error = None
        with mock.patch.object(batch, "send", transport), mock.patch.object(cli, "load_agents", return_value=CONFIG_ALL):
            try:
                cli._batch(args)
            except SystemExit as exit_:
                error = exit_.code
        return args, error

    def test_without_narrative_out_the_narrative_agent_is_never_called(self):
        transport = Transport()
        args, error = self.run_cli(transport, narrative=False)
        self.assertEqual((transport.order, error), (["hmda", "ybs", "auditor"], None))
        self.assertEqual(sorted(self.load(args.json_out)), ["auditor", "hmda", "ybs"])

    def test_the_report_is_written_after_the_auditor(self):
        transport = Transport()
        args, error = self.run_cli(transport, narrative=True)
        self.assertEqual((transport.order, error), (["hmda", "ybs", "auditor", "narrative"], None))
        with open(args.narrative_out, encoding="utf-8") as report:
            self.assertEqual(report.read(), "# Report")

    def test_a_failed_narrative_exits_nonzero_writes_no_empty_report_and_keeps_the_batch_results(self):
        args, error = self.run_cli(Transport(fail=["narrative", "hmda"]), narrative=True)
        self.assertEqual(error, 1)
        self.assertFalse(os.path.exists(args.narrative_out))
        saved = self.load(args.json_out)
        self.assertEqual(sorted(saved), ["auditor", "hmda", "ybs"])
        self.assertEqual(saved["hmda"]["parse_error"], "RuntimeError: hmda unreachable")


class RegistryOptionsTests(unittest.TestCase):
    def test_serve_one_passes_only_the_documented_options_provider_and_model_to_the_app(self):
        entry = {"url": "http://127.0.0.1:9999/", "tool_mode": "seeded", "include_regulations": False, "max_regulation_chars": 10,
                 "provider": "ollama", "model": "m1", "unrelated": 1}
        with mock.patch.object(launcher, "build_app") as build, mock.patch("uvicorn.run") as run:
            launcher.serve_one("ybs", entry, provider="anthropic", model="m2")
        build.assert_called_once_with("ybs", entry["url"], provider="ollama", model="m1",
                                      options={"tool_mode": "seeded", "include_regulations": False, "max_regulation_chars": 10})
        self.assertEqual((run.call_args.kwargs["host"], run.call_args.kwargs["port"]), ("127.0.0.1", 9999))
        with mock.patch.object(launcher, "build_app") as build, mock.patch("uvicorn.run"):
            launcher.serve_one("narrative", {"url": "http://127.0.0.1:9998/"}, provider="anthropic", model="m2")
        build.assert_called_once_with("narrative", "http://127.0.0.1:9998/", provider="anthropic", model="m2", options=None)

    def test_the_shipped_registry_uses_only_valid_options(self):
        from agents.runner import TOOL_MODES
        for key, entry in REGISTRY.items():
            with self.subTest(role=key):
                self.assertLessEqual(set(entry) - {"url"}, {"provider", "model", "tool_mode", "include_regulations", "max_regulation_chars"})
                self.assertIn(entry.get("tool_mode", "model"), TOOL_MODES)


if __name__ == "__main__":
    unittest.main()
