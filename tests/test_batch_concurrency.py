import argparse
import asyncio
import contextlib
import io
import json
import os
import random
import sys
import tempfile
import unittest
from unittest import mock

from agent_prompts import AGENTS
from compliance_mcp.auditor.adapter import tool_arguments
from orchestrator import batch, cli, launcher
from orchestrator.config import load_agents, load_settings

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



class RateLimitError(Exception):
    """Stands in for the provider SDK's 429 error after its own retries are spent."""


class TimedTransport(Transport):
    """Transport with per-role latency, per-class peak tracking and start and end times."""

    def __init__(self, delays=None, fail=(), errors=None, classes=None):
        super().__init__(fail)
        self.delays, self.errors, self.classes = delays or {}, errors or {}, classes or {}
        self.started, self.ended = {}, {}
        self.class_now, self.class_peak = {}, {}

    async def __call__(self, url, payload, httpx_client=None):
        key = url.rstrip("/").rsplit("/", 1)[1]
        self.calls.append((key, payload))
        kind = self.classes.get(key, "remote")
        self.started[key] = len(self.started)
        self.now += 1
        self.class_now[kind] = self.class_now.get(kind, 0) + 1
        self.peak = max(self.peak, self.now)
        self.class_peak[kind] = max(self.class_peak.get(kind, 0), self.class_now[kind])
        await asyncio.sleep(self.delays.get(key, 0.01))
        self.now -= 1
        self.class_now[kind] -= 1
        self.ended[key] = len(self.ended)
        if key in self.errors:
            raise self.errors[key]
        if key in self.fail:
            raise RuntimeError(f"{key} unreachable")
        return {"parsed": None, "raw_text": "# Report"} if key == "narrative" else {"parsed": self.parsed(key), "raw_text": "{}"}


def with_provider(provider, keys):
    return {k: ({**v, "provider": provider} if k in keys else v) for k, v in CONFIG_ALL.items()}


def run_config(config, transport, **kw):
    with mock.patch.object(batch, "send", transport):
        return asyncio.run(batch.run_batch({"loan": 1}, config, verbose=kw.pop("verbose", False), **kw))


class ProviderGateTests(unittest.TestCase):
    """Remote agents share one gate of `remote_concurrency`; Ollama agents share a gate of 1; `--concurrency` is an overall cap."""

    def test_an_all_remote_batch_runs_as_wide_as_the_remote_width(self):
        for width in (2, 4, 8):
            with self.subTest(width=width):
                transport = TimedTransport()
                run_config(CONFIG_ALL, transport, remote_concurrency=width)
                self.assertEqual(transport.peak, width)
                self.assertEqual(transport.order[-1], "auditor")

    def test_the_default_remote_width_is_two_with_no_flag(self):
        self.assertEqual(batch.DEFAULT_REMOTE_CONCURRENCY, 2)
        transport = TimedTransport()
        run_config(CONFIG_ALL, transport)
        self.assertEqual(transport.peak, 2)

    def test_an_all_local_batch_stays_serial_whatever_the_remote_width(self):
        transport = TimedTransport()
        run_config(CONFIG_ALL, transport, provider="ollama", remote_concurrency=8)
        self.assertEqual(transport.peak, 1)
        transport = TimedTransport()
        run_config(with_provider("ollama", DOMAINS), transport, remote_concurrency=8)
        self.assertEqual(transport.peak, 1)

    def test_a_mixed_batch_has_a_peak_per_class(self):
        local = ["hmda", "ecoa"]
        config = with_provider("ollama", local)
        transport = TimedTransport(classes={k: "local" for k in local})
        run_config(config, transport, remote_concurrency=4)
        self.assertEqual(transport.class_peak, {"remote": 4, "local": 1})
        self.assertEqual(transport.peak, 5)      # the classes overlap each other, each within its own width

    def test_the_local_width_comes_from_the_concurrency_setting(self):
        local = ["hmda", "ecoa", "hpml"]
        transport = TimedTransport(classes={k: "local" for k in local})
        run_config(with_provider("ollama", local), transport, local_concurrency=2, remote_concurrency=3)
        self.assertEqual(transport.class_peak, {"remote": 3, "local": 2})

    def test_an_explicit_concurrency_is_an_overall_cap_and_one_forces_serial(self):
        transport = TimedTransport()
        run_config(CONFIG_ALL, transport, concurrency=1, remote_concurrency=8)
        self.assertEqual(transport.peak, 1)
        transport = TimedTransport()
        run_config(CONFIG_ALL, transport, concurrency=3, remote_concurrency=8)
        self.assertEqual(transport.peak, 3)
        transport = TimedTransport()
        run_config(CONFIG_ALL, transport, concurrency=4)      # alone it keeps its old meaning: that many at once
        self.assertEqual(transport.peak, 4)

    def test_the_provider_of_an_agent_is_its_entry_then_the_cli_then_the_environment_then_anthropic(self):
        entry = {"url": "http://127.0.0.1:1/x", "provider": "openai"}
        bare = {"url": "http://127.0.0.1:1/x"}
        with mock.patch.dict(os.environ, {"COMPLIANCE_PROVIDER": "ollama"}):
            self.assertEqual(batch.resolve_provider(entry, "anthropic"), "openai")
            self.assertEqual(batch.resolve_provider(bare, "anthropic"), "anthropic")
            self.assertEqual(batch.resolve_provider(bare, None), "ollama")
        with mock.patch.dict(os.environ):
            os.environ.pop("COMPLIANCE_PROVIDER", None)
            self.assertEqual(batch.resolve_provider(bare, None), "anthropic")
        self.assertEqual([batch.gate_class(p) for p in ("anthropic", "openai", "ollama")], ["remote", "remote", "local"])


class OrderUnderLoadTests(unittest.TestCase):
    def test_order_and_shape_hold_for_random_latencies_and_a_failing_role(self):
        for seed in range(25):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                delays = {k: rng.uniform(0.0, 0.03) for k in REGISTRY}
                failing = rng.choice(DOMAINS)
                transport = TimedTransport(delays=delays, fail=[failing])
                results = run_config(CONFIG_ALL, transport, remote_concurrency=rng.choice((2, 4, 8)))
                self.assertEqual(list(results), DOMAINS + ["auditor"])
                self.assertEqual(results[failing]["parse_error"], f"RuntimeError: {failing} unreachable")
                self.assertTrue(all(results[k]["parsed"] for k in set(DOMAINS) - {failing}))
                self.assertTrue(results["auditor"]["parsed"])
                self.assertGreater(transport.started["auditor"], max(transport.started[k] for k in DOMAINS))
                self.assertGreater(transport.ended["auditor"], max(transport.ended[k] for k in DOMAINS))      # the auditor ends after every domain ends
                with mock.patch.object(batch, "send", transport):
                    asyncio.run(batch.run_narrative(results, CONFIG_ALL, verbose=False))
                self.assertEqual(transport.order[-2:], ["auditor", "narrative"])
                self.assertGreater(transport.ended["narrative"], transport.ended["auditor"])

    def test_the_auditor_input_has_every_domain_result_in_registry_order_even_when_they_finish_out_of_order(self):
        delays = {k: 0.05 - 0.005 * i for i, k in enumerate(DOMAINS)}      # the first domain is the slowest
        transport = TimedTransport(delays=delays)
        run_config(CONFIG_ALL, transport, remote_concurrency=8)
        self.assertEqual(transport.order[:-1], DOMAINS)
        self.assertEqual(list(transport.payload("auditor")["agent_results"]), DOMAINS)
        self.assertEqual(transport.ended["hmda"], len(DOMAINS) - 1)      # it really did finish last


class RateLimitTests(unittest.TestCase):
    def test_a_rate_limited_role_fails_alone_and_the_summary_counts_it(self):
        error = RateLimitError("Error code: 429 - rate_limit_error: retry-after: 7")
        transport = TimedTransport(errors={"hpml": error})
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            results = run_config(CONFIG_ALL, transport, remote_concurrency=8, verbose=True)
        self.assertIn("RateLimitError", results["hpml"]["parse_error"])
        self.assertIsNone(results["hpml"]["parsed"])
        for key in set(DOMAINS) - {"hpml"}:
            self.assertEqual(results[key]["parsed"], Transport.parsed(key))
        self.assertEqual(results["auditor"]["parsed"], Transport.parsed("auditor"))
        self.assertEqual(batch.rate_limited_roles(results), ["hpml"])
        self.assertIn("1 role failed on rate limits: hpml", stderr.getvalue())

    def test_other_failures_are_not_counted_as_rate_limits(self):
        results = run_config(CONFIG_ALL, TimedTransport(fail=["ecoa"], errors={"fzd": RateLimitError("rate limit exceeded")}))
        self.assertEqual(batch.rate_limited_roles(results), ["fzd"])
        self.assertEqual(batch.rate_limited_roles(run_config(CONFIG_ALL, TimedTransport(fail=["ecoa"]))), [])

    def test_the_retry_after_value_is_read_from_the_error_text_when_present(self):
        self.assertEqual(batch.retry_after("429 Too Many Requests; retry-after: 12"), "12")
        self.assertEqual(batch.retry_after("Retry-After=3.5 seconds"), "3.5")
        self.assertIsNone(batch.retry_after("429 with no hint"))

    def test_a_quiet_batch_prints_no_rate_limit_line(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            run_config(CONFIG_ALL, TimedTransport(), verbose=True)
        self.assertNotIn("rate limit", stderr.getvalue())


class WidthSettingTests(unittest.TestCase):
    def test_settings_default_and_validate_the_remote_width(self):
        with tempfile.TemporaryDirectory() as directory:
            def settings(text):
                path = os.path.join(directory, "agents.yaml")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text + "\nagents: {hmda: {url: 'http://127.0.0.1:1/'}}\n")
                return load_settings(path)
            self.assertEqual(settings(""), {"concurrency": 1, "remote_concurrency": 2})
            self.assertEqual(settings("concurrency: 3\nremote_concurrency: 8"), {"concurrency": 3, "remote_concurrency": 8})
            with self.assertRaisesRegex(ValueError, "remote_concurrency"):
                settings("remote_concurrency: 0")

    def test_the_committed_registry_is_serial_for_local_and_eight_wide_for_remote(self):
        # 8 = the highest clean width of the live ramp 2, 4, 8 (plans/archive/parallelize/results.md); lower it there if a provider rate-limits
        self.assertEqual(load_settings(), {"concurrency": 1, "remote_concurrency": 8})

    def test_the_cli_turns_flags_and_settings_into_widths(self):
        def widths(**given):
            return cli._widths(argparse.Namespace(**{"config": None, "concurrency": None, "remote_concurrency": None, "provider": None, **given}))
        committed = load_settings()
        self.assertEqual(widths(), {"concurrency": None, "local_concurrency": committed["concurrency"], "remote_concurrency": committed["remote_concurrency"]})
        self.assertEqual(widths(remote_concurrency=4), {"concurrency": None, "local_concurrency": committed["concurrency"], "remote_concurrency": 4})
        self.assertEqual(widths(concurrency=1), {"concurrency": 1, "local_concurrency": None, "remote_concurrency": None})
        self.assertEqual(widths(concurrency=1, remote_concurrency=4), {"concurrency": 1, "local_concurrency": None, "remote_concurrency": 4})

    def test_batch_passes_the_widths_and_the_provider_to_run_batch(self):
        with mock.patch.object(batch, "send", Transport()), mock.patch.object(cli, "load_agents", return_value=CONFIG_ALL), \
                mock.patch.object(cli, "run_batch", wraps=batch.run_batch) as spy:
            directory = tempfile.mkdtemp()
            loan = os.path.join(directory, "loan.json")
            with open(loan, "w", encoding="utf-8") as f:
                json.dump({"loan": 1}, f)
            args = argparse.Namespace(loan_file=loan, config=None, concurrency=None, remote_concurrency=4, agents=["hmda", "ybs"], spawn_local=False,
                                      provider="ollama", model=None, json_out=os.path.join(directory, "r.json"), narrative_out=None)
            cli._batch(args)
        self.assertEqual({k: spy.call_args.kwargs[k] for k in ("concurrency", "local_concurrency", "remote_concurrency", "provider")},
                         {"concurrency": None, "local_concurrency": 1, "remote_concurrency": 4, "provider": "ollama"})

    def test_the_parser_accepts_remote_concurrency(self):
        with mock.patch.object(sys, "argv", ["cli", "batch", "loan.json", "--remote-concurrency", "4"]), \
                mock.patch.object(cli, "_batch") as run:
            cli.main()
        self.assertEqual(run.call_args.args[0].remote_concurrency, 4)


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
