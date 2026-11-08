"""Offline tests of the live-parity registry driver: fake backends and a scripted provider; no network, no credentials."""
import json
import unittest

from agent_prompts import AGENTS
from agents.backends import Backend
from compliance_common.narrative import deterministic_narrative
from live_parity_common import (GOOD_SOURCES, PHASES, RUN_REQUEST_LIMIT, ScriptedProvider, registry_roles, role_failures, run_registry,
                                violation_kind, paragraph_failures, worst_case_requests, worst_case_table)
from orchestrator.config import load_agents
from test_agent_parity import SAMPLE, FakeModel

ROLES = registry_roles()
DOMAINS = ROLES[:-2]


class RoleFake:
    """A Backend double for the whole registry: the role is read from the tool spec (or the system prompt for plain completions)."""
    provider, model = "fake", "fake-1"

    def __init__(self, *, calls_tool=True, ungrounded=False):
        self.calls_tool, self.ungrounded, self.decisions, self.seen = calls_tool, ungrounded, {}, []

    def _role(self, system):
        return next(k for k, v in AGENTS.items() if system.startswith(v["system_prompt"]))

    def _reply(self, role, decision):
        if not AGENTS[role].get("tool"):
            return "# Compliance narrative\n\nSynthetic report."
        narrative = deterministic_narrative(decision, AGENTS[role]["tool"].removesuffix("_evaluate"))
        if self.ungrounded:
            narrative["reasoning"] += " The borrower also owes 987654321 dollars."
        return json.dumps({"narrative": narrative})

    def complete_with_tool(self, system, messages, spec, execute, calls_made, force_first=True):
        role = self._role(system)
        if self.calls_tool:
            self.decisions[role] = execute(spec["name"], {"case": {}})
            calls_made.append({"name": spec["name"], "arguments": {"case": {}}, "result": self.decisions[role]})
        return self._reply(role, self.decisions[role]) if role in self.decisions else "I will answer without the tool."

    def complete_seeded(self, system, messages, spec, execute, calls_made, arguments, result, schema=None):
        self.seen.append(self._role(system))
        return self._reply(self._role(system), result)

    def complete(self, system, messages, json_mode=True, schema=None):
        role = self._role(system)
        if not AGENTS[role].get("tool"):
            return self._reply(role, None)
        text = messages[-1]["content"] if "TOOL RESULT" in messages[-1]["content"] else next(m["content"] for m in messages if "TOOL RESULT" in m["content"])
        decision, _ = json.JSONDecoder().raw_decode(text.split("explain it, do not change it)\n", 1)[1])
        return self._reply(role, decision)


class RegistryTests(unittest.TestCase):
    def test_roles_are_derived_from_the_registry_in_execution_order(self):
        self.assertEqual(ROLES, [k for k in load_agents() if k not in ("auditor", "narrative")] + ["auditor", "narrative"])
        self.assertEqual(len(ROLES), 10)
        self.assertEqual(set(DOMAINS), {k for k, v in AGENTS.items() if v.get("tool") and k != "auditor"})

    def test_a_changed_registry_changes_the_roles(self):
        config = {k: {"url": "http://x/"} for k in ("ybs", "auditor", "narrative")}
        self.assertEqual(registry_roles(config), ["ybs", "auditor", "narrative"])


class DriverTests(unittest.TestCase):
    def check_all_good(self, out, phase):
        self.assertEqual([r["role"] for r in out["records"]], ROLES)
        for record in out["records"]:
            with self.subTest(role=record["role"], phase=phase):
                self.assertEqual(role_failures(record), [])
                self.assertIn(record["narrative_source"], GOOD_SOURCES)
        self.assertTrue(out["summary"]["ok"])
        self.assertEqual(out["summary"]["order"], ROLES)

    def test_every_role_passes_in_both_phases_with_a_fake_backend(self):
        for phase in PHASES:
            backend = RoleFake()
            out = run_registry(backend, phase)
            self.check_all_good(out, phase)
            by = {r["role"]: r for r in out["records"]}
            expected_by = "model" if phase == "model" else "seeded"
            for key in DOMAINS + ["auditor"]:
                self.assertEqual(by[key]["tool_calls"], [{"name": AGENTS[key]["tool"], "by": expected_by}])
                self.assertEqual(by[key]["decision"]["decision_id"][:0], "")
            self.assertEqual(by["narrative"]["tool_calls"], [])
            self.assertIsNone(by["narrative"]["decision"])
            if phase == "seeded":
                self.assertEqual(backend.seen, DOMAINS + ["auditor"])

    def test_parity_is_with_direct_evaluation_on_the_exact_payload(self):
        from test_agent_parity import role_input
        out = run_registry(RoleFake(), "model")
        for record in out["records"][:-1]:
            if record["role"] == "auditor":
                continue
            self.assertEqual(record["decision"]["decision_id"], role_input(record["role"])[1]["decision_id"])

    def test_a_model_that_skips_the_tool_is_a_provenance_failure_not_a_pass(self):
        out = run_registry(RoleFake(calls_tool=False), "model")
        self.assertFalse(out["summary"]["ok"])
        for key in DOMAINS + ["auditor"]:
            record = next(r for r in out["records"] if r["role"] == key)
            self.assertEqual(record["tool_calls"][0]["by"], "harness")
            self.assertIn("tool_provenance", role_failures(record))
            self.assertTrue(record["checks"]["decision_parity"])

    def test_a_deterministic_fallback_is_recorded_and_reported_never_counted(self):
        out = run_registry(RoleFake(ungrounded=True), "seeded")
        summary = out["summary"]
        self.assertFalse(summary["ok"])
        self.assertEqual(summary["fallbacks"], DOMAINS + ["auditor"])
        for key in DOMAINS + ["auditor"]:
            self.assertEqual(summary["narrative_sources"][key], "deterministic_fallback")
            self.assertEqual(summary["failed"][key], ["narrative_source"])
        self.assertEqual(next(r for r in out["records"] if r["role"] == "ybs")["guard_attempts"], 2)
        self.assertEqual(summary["narrative_sources"]["narrative"], "model")

    def test_a_failed_role_is_a_failed_record_and_does_not_stop_the_run(self):
        class Broken(RoleFake):
            def complete_seeded(self, system, *args, **kwargs):
                if self._role(system) == "hmda":
                    raise RuntimeError("model unreachable")
                return super().complete_seeded(system, *args, **kwargs)
        out = run_registry(Broken(), "seeded")
        record = next(r for r in out["records"] if r["role"] == "hmda")
        self.assertIn("task", role_failures(record))
        self.assertIn("RuntimeError", record["failure"])
        self.assertEqual([r["role"] for r in out["records"]], ROLES)
        self.assertFalse(out["summary"]["ok"])
        self.assertNotIn("auditor", out["summary"]["failed"])               # the auditor still ran, with hmda reported missing

    def test_records_and_summary_keep_no_bodies(self):
        out = run_registry(RoleFake(), "model")
        text = json.dumps(out)
        case_id = SAMPLE["case_information"]["case_id"]
        for forbidden in (case_id, "Synthetic report", "reasoning", "examiner_narrative", "Narrate the decision record", "payload"):
            self.assertNotIn(forbidden, text)
        for record in out["records"]:
            self.assertLessEqual(set(record), {"role", "phase", "checks", "elapsed_seconds", "tool_backed", "failure", "narrative_source",
                                               "guard_attempts", "tool_calls", "stripped_fields", "decision", "violation_kinds",
                                               "paragraph_failures", "paragraph_sources"})
            self.assertTrue(all(kind in KINDS for attempt in record["violation_kinds"] for kind in attempt))   # labels only, never quoted text


KINDS = {"number", "date", "identifier", "invalid_json", "empty", "other", "contradiction", "missing_narrative"}


class ViolationKindTests(unittest.TestCase):
    def test_a_violation_is_reduced_to_a_label_that_quotes_nothing(self):
        for text, kind in (("the number '987654321' does not appear in the decision record", "number"),
                           ("the date '2026-01-01' does not appear in the decision record or the case", "date"),
                           ("the identifier 'ZZ-9' does not appear in the decision record or the case", "identifier"),
                           ("the reply was not valid JSON: Expecting value", "invalid_json"),
                           ("the narrative is empty or too short to explain the decision record", "empty"),
                           ("the narrative says the loan is compliant but the record says otherwise", "other")):
            self.assertEqual(violation_kind(text), kind)

    def test_a_contradiction_and_a_missing_narrative_object_have_their_own_labels(self):
        for text, kind in (("the narrative describes violations or deficiencies, but the decision record's result is Compliant", "contradiction"),
                           ("the narrative claims compliance, but the decision record's result is Non-Compliant", "contradiction"),
                           ("the reply did not contain the required narrative object", "missing_narrative")):
            self.assertEqual(violation_kind(text), kind)

    def test_an_ungrounded_narrative_records_number_kinds_for_both_attempts(self):
        script = ScriptedProvider(narrative="ungrounded")
        records = run_registry(script.backend(), "seeded")["records"]
        hmda = next(r for r in records if r["role"] == "hmda")
        self.assertEqual(hmda["narrative_source"], "deterministic_fallback")
        self.assertEqual([set(a) for a in hmda["violation_kinds"]], [{"number", "identifier"}] * 2)
        self.assertNotIn("987654321", json.dumps(records))


class ParagraphFailureTests(unittest.TestCase):
    GUARD = {"paragraph_violations": {"YBS-X": ["the paragraph has 91 words; the limit is 70", "the number '987654321' does not appear in the decision record"],
                                      "YBS-Y": ["the paragraph must cite 12 CFR 614.4"]},
             "retry_paragraph_violations": {"YBS-Y": ["no paragraph was written for this finding"]}}

    def test_each_attempt_lists_the_failing_rule_ids_with_labels_only(self):
        self.assertEqual(paragraph_failures(self.GUARD),
                         [[{"rule_id": "YBS-X", "kinds": ["limit", "number"]}, {"rule_id": "YBS-Y", "kinds": ["citation"]}],
                          [{"rule_id": "YBS-Y", "kinds": ["missing"]}]])
        self.assertNotIn("987654321", json.dumps(paragraph_failures(self.GUARD)))

    def test_a_clean_or_absent_guard_gives_two_empty_attempts(self):
        self.assertEqual(paragraph_failures({}), [[], []])
        self.assertEqual(paragraph_failures({"paragraph_violations": {}, "retry_paragraph_violations": {}}), [[], []])

    def test_every_check_of_the_examiner_paragraph_has_its_own_label(self):
        from compliance_common.templates import examiner
        from live_parity_common import paragraph_violation_kind
        known = {"parts_order": "the paragraph must have the parts Requirement:", "rule_id": "the paragraph must name YBS-X",
                 "citation": "the paragraph must cite 12 CFR", "record_words": "the Condition must quote the record's own words for this rule",
                 "outcome": "the paragraph must state the outcome 'x'", "result": "the paragraph must state the result Compliant",
                 "action": "the Action must say what closes the finding", "floor": "the paragraph has 3 words; the floor is 25",
                 "limit": "the paragraph has 99 words; the limit is 70", "missing": "no paragraph was written for this finding",
                 "duplicate": "more than one paragraph was written for this finding"}
        for kind, text in known.items():
            self.assertEqual(paragraph_violation_kind(text), kind)
        self.assertEqual(paragraph_violation_kind("something new"), "other")
        self.assertTrue(examiner.FLOOR and examiner.LIMITS)


class ScriptedProviderTests(unittest.TestCase):
    """The real SDK tool loops, over an offline transport, stay within the derived per-role bounds."""

    def run_scenario(self, provider, phase, **behavior):
        script = ScriptedProvider(provider=provider, **behavior)
        out = run_registry(script.backend(), phase)
        return script, out

    def test_cooperative_models_pass_on_both_providers_and_phases(self):
        for provider in ("anthropic", "openai"):
            for phase in PHASES:
                with self.subTest(provider=provider, phase=phase):
                    script, out = self.run_scenario(provider, phase)
                    self.assertEqual([r for r in out["summary"]["failed"]], [], out["summary"]["failed"])
                    self.assertTrue(out["summary"]["ok"])
                    self.assertFalse(script.refused)
                    for role in ROLES:
                        self.assertLessEqual(script.count(role, phase), worst_case_requests(provider, phase, role))
                    self.assertTrue(all(r["model"] == script.model for r in script.requests))

    def test_a_forced_first_call_is_made_by_the_model_on_both_providers(self):
        for provider in ("anthropic", "openai"):
            script, out = self.run_scenario(provider, "model")
            self.assertEqual(script.count("ybs", "model"), 2, provider)                     # forced call, then the answer
            self.assertEqual(next(r for r in out["records"] if r["role"] == "ybs")["tool_calls"][0]["by"], "model")

    def test_the_bounds_are_reached_by_the_worst_legitimate_path_and_never_exceeded(self):
        for provider in ("anthropic", "openai"):
            for phase in PHASES:
                with self.subTest(provider=provider, phase=phase):
                    # model phase: tool call, empty answer (RuntimeError), harness fallback, rejected narrative, retry = the bound;
                    # seeded phase: rejected narrative and its retry (the bound also allows one more anthropic tool turn)
                    script, out = self.run_scenario(provider, phase, narrative="ungrounded", empty_after_tool=phase == "model")
                    self.assertFalse(script.refused)
                    self.assertEqual(out["summary"]["fallbacks"], DOMAINS + ["auditor"])
                    for role in DOMAINS + ["auditor"]:
                        bound = worst_case_requests(provider, phase, role)
                        self.assertLessEqual(script.count(role, phase), bound)
                    if phase == "model":
                        self.assertEqual(script.count("ybs", phase), worst_case_requests(provider, phase, "ybs"))

    def test_a_model_that_never_calls_the_tool_is_covered_by_the_harness_within_the_bound(self):
        for provider in ("anthropic", "openai"):
            script, out = self.run_scenario(provider, "model", tool="none")
            record = next(r for r in out["records"] if r["role"] == "hmda")
            self.assertEqual(record["tool_calls"][0]["by"], "harness")
            self.assertLessEqual(script.count("hmda", "model"), worst_case_requests(provider, "model", "hmda"))

    def test_a_model_that_calls_the_tool_forever_is_stopped_at_the_cap_and_the_role_fails(self):
        for provider in ("anthropic", "openai"):
            script, out = self.run_scenario(provider, "model", tool="repeat")
            self.assertTrue(script.refused)
            self.assertFalse(out["summary"]["ok"])
            for role in ROLES:
                self.assertLessEqual(script.count(role, "model"), worst_case_requests(provider, "model", role))
            self.assertIn("task", role_failures(next(r for r in out["records"] if r["role"] == "ybs")))

    def test_outbound_requests_are_measured_in_bytes_and_stay_under_the_anthropic_bound(self):
        script, _ = self.run_scenario("anthropic", "model")
        sizes = {role: max(r["bytes"] for r in script.requests if r["role"] == role) for role in ROLES}
        self.assertTrue(all(0 < size <= 100_000 for size in sizes.values()), sizes)


class BoundsTests(unittest.TestCase):
    def test_totals_fit_the_plan_ceiling(self):
        for provider in ("anthropic", "openai"):
            table = worst_case_table(provider)
            self.assertLessEqual(table["total"], RUN_REQUEST_LIMIT, provider)
            self.assertEqual(set(table["per_role"]), set(PHASES))
            self.assertEqual(set(table["per_role"]["model"]), set(ROLES))

    def test_known_values(self):
        self.assertEqual(worst_case_requests("anthropic", "model", "ybs"), 4)
        self.assertEqual(worst_case_requests("anthropic", "seeded", "ybs"), 3)
        self.assertEqual(worst_case_requests("openai", "seeded", "ybs"), 2)
        self.assertEqual(worst_case_requests("openai", "model", "narrative"), 1)
        self.assertEqual((worst_case_table("anthropic")["total"], worst_case_table("openai")["total"]), (65, 56))

    def test_unknown_provider_or_phase_is_refused(self):
        with self.assertRaises(ValueError):
            worst_case_requests("ollama", "model", "ybs")
        with self.assertRaises(ValueError):
            worst_case_requests("openai", "other", "ybs")


if __name__ == "__main__":
    unittest.main()
