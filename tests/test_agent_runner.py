"""Narrative-only agents: the tool decides, the model explains, code assembles."""
import json
import unittest

from agent_prompts import AGENTS
from agents.runner import run_agent
from compliance_common.narrative_schema import NARRATIVE_SCHEMA
from compliance_mcp.ybs import evaluate_ybs
from compliance_mcp.ybs.server import server as ybs_server

from test_ybs_evaluator import case, person


def loan(subjects):
    return {"case_information": {"case_id": "YBS-TEST"}, "ybs_case": case(subjects)}


GOOD_TEXT = ("The deterministic review classified this case as Young + Beginning + Small with the result Compliant. "
             "Every rule in the decision record was satisfied or did not apply, and the record lists no missing facts.")
NARRATIVE = {"narrative": {"reasoning": GOOD_TEXT, "examiner_narrative": GOOD_TEXT, "data_gaps_followups": []}}


class FakeBackend:
    """Stands in for Backend: optionally calls the tool (with tampered args), then answers."""
    provider, model = "fake", "fake-1"

    def __init__(self, output, call_tool=True, tamper=None):
        self.output, self.call_tool, self.tamper = output, call_tool, tamper
        self.plain_prompts = []

    def complete_with_tool(self, system, messages, spec, execute, calls_made):
        assert "Agent: ybs" in system and f"Agent Version: {AGENTS['ybs']['version']}" in system  # version is in the prompt text
        if self.call_tool:
            args = self.tamper or {"case": {}}
            calls_made.append({"name": spec["name"], "arguments": args, "result": execute(spec["name"], args)})
        return json.dumps(self.output)

    def complete(self, system, messages, json_mode=True, schema=None):
        self.plain_prompts.append(messages[-1]["content"])
        return json.dumps(self.output)


class AgentRunnerTests(unittest.TestCase):
    def run_ybs(self, payload, backend):
        return run_agent("ybs", payload, backend, tool_target=ybs_server)

    def test_model_cannot_change_decision_or_facts(self):
        payload = loan([person()])
        expected = evaluate_ybs(payload["ybs_case"])
        tampered = {"case": case([person(date_of_birth="1960-01-01")])}  # model tries to alter the facts
        output = dict(NARRATIVE, domain_determination={"classification": "Not Eligible"},
                      determination_status={"result": "Non-Compliant"}, threshold_evaluation={"young_age_limit": 99})
        result = self.run_ybs(payload, FakeBackend(output, tamper=tampered))
        parsed = result["parsed"]
        self.assertEqual(result["decision"]["decision_id"], expected["decision_id"])
        self.assertEqual(parsed["domain_determination"]["classification"], "Young + Beginning + Small")
        self.assertEqual(parsed["determination_status"]["result"], "Compliant")
        self.assertEqual(parsed["threshold_evaluation"]["young_age_limit"], 35)
        guard = result["narrative_guard"]
        self.assertFalse(guard["passed"])
        self.assertEqual(guard["model_proposed_classification"], "Not Eligible")
        self.assertEqual(set(guard["stripped_fields"]), {"domain_determination", "determination_status", "threshold_evaluation"})
        self.assertEqual(parsed["compliance_determination_summary"]["reasoning"], GOOD_TEXT)
        self.assertEqual(parsed["narrative_source"], "model")
        self.assertEqual(parsed["agent_metadata"]["agent_version"], AGENTS["ybs"]["version"])
        self.assertEqual(result["tool_calls"], [{"name": "ybs_evaluate", "by": "model"}])

    def test_harness_calls_tool_when_model_does_not(self):
        backend = FakeBackend(NARRATIVE, call_tool=False)
        result = self.run_ybs(loan([person()]), backend)
        self.assertEqual(result["tool_calls"], [{"name": "ybs_evaluate", "by": "harness"}])
        self.assertIn("TOOL RESULT", backend.plain_prompts[0])
        self.assertEqual(result["parsed"]["domain_determination"]["classification"], "Young + Beginning + Small")

    def test_not_eligible_is_not_reported_as_compliant(self):
        old = person(date_of_birth="1960-01-01", years_farming=40, annual_gross_ag_sales=9_000_000)
        result = self.run_ybs(loan([old]), FakeBackend(NARRATIVE))
        self.assertEqual(result["parsed"]["domain_determination"]["classification"], "Not Eligible")
        self.assertEqual(result["parsed"]["determination_status"]["result"], "Not Applicable")

    def test_narrative_input_is_unable_to_determine(self):
        backend = FakeBackend(NARRATIVE)
        result = self.run_ybs("Borrower is 30 and says they are a young farmer.", backend)
        self.assertEqual(result["parsed"]["domain_determination"]["classification"], "Unable To Determine")
        self.assertEqual(result["tool_calls"], [])
        self.assertIn("provide ybs_case", json.dumps(result["decision"]))

    def test_unparseable_model_output_still_returns_the_decision(self):
        class Bad(FakeBackend):
            def complete_with_tool(self, *a, **k):
                super().complete_with_tool(*a, **k)
                return "not json"
        result = self.run_ybs(loan([person()]), Bad(NARRATIVE))
        self.assertIn("not valid JSON", result["narrative_guard"]["violations"][0])
        self.assertEqual(result["parsed"]["domain_determination"]["classification"], "Young + Beginning + Small")
        self.assertEqual(result["parsed"]["narrative_source"], "model_retry")        # the retry (valid JSON from the fake) rescued it


class ToolModeAndRegulationTests(unittest.TestCase):
    class Recorder(FakeBackend):
        def __init__(self, output):
            super().__init__(output)
            self.systems, self.seeded = [], []

        def complete_with_tool(self, system, messages, spec, execute, calls_made, force_first=True):
            self.systems.append(system)
            calls_made.append({"name": spec["name"], "arguments": {}, "result": execute(spec["name"], {})})
            return json.dumps(self.output)

        def complete_seeded(self, system, messages, spec, execute, calls_made, arguments, result, schema=None):
            self.systems.append(system)
            self.seeded.append((arguments, result))
            self.schemas = getattr(self, "schemas", []) + [schema]
            return json.dumps(self.output)

    def test_seeded_mode_makes_the_call_and_hands_it_to_the_model_as_its_own_first_step(self):
        backend = self.Recorder(NARRATIVE)
        result = run_agent("ybs", loan([person()]), backend, tool_target=ybs_server, options={"tool_mode": "seeded"})
        self.assertEqual(result["tool_calls"], [{"name": "ybs_evaluate", "by": "seeded"}])
        self.assertEqual(len(backend.seeded), 1)
        arguments, record = backend.seeded[0]
        self.assertEqual(arguments["case"]["subjects"][0]["id"], "p1")
        self.assertEqual(record["decision_id"], result["decision"]["decision_id"])
        self.assertEqual((result["tool_mode"], result["parsed"]["domain_determination"]["classification"]), ("seeded", "Young + Beginning + Small"))
        self.assertEqual(backend.schemas, [NARRATIVE_SCHEMA])                     # the final answer is constrained to the contract

    def test_model_mode_is_the_default_and_a_model_that_skips_the_tool_is_covered(self):
        backend = self.Recorder(NARRATIVE)
        self.assertEqual(run_agent("ybs", loan([person()]), backend, tool_target=ybs_server)["tool_mode"], "model")
        self.assertEqual(backend.seeded, [])
        lazy = FakeBackend(NARRATIVE, call_tool=False)
        self.assertEqual(run_agent("ybs", loan([person()]), lazy, tool_target=ybs_server)["tool_calls"], [{"name": "ybs_evaluate", "by": "harness"}])

    def test_a_malformed_tool_call_from_the_model_falls_back_to_the_harness_not_a_crash(self):
        class Broken(FakeBackend):
            def complete_with_tool(self, system, messages, spec, execute, calls_made, force_first=True):
                raise RuntimeError('Ollama returned HTTP 500: {"error":"invalid character \'#\' after object key:value pair"}')
        result = run_agent("ybs", loan([person()]), Broken(NARRATIVE), tool_target=ybs_server)
        self.assertEqual(result["tool_calls"], [{"name": "ybs_evaluate", "by": "harness"}])
        self.assertEqual(result["parsed"]["domain_determination"]["classification"], "Young + Beginning + Small")

    def test_unknown_tool_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "tool_mode"):
            run_agent("ybs", loan([person()]), FakeBackend(NARRATIVE), tool_target=ybs_server, options={"tool_mode": "psychic"})

    def test_the_pinned_regulation_text_is_given_to_the_model_and_its_provenance_recorded(self):
        backend = self.Recorder(NARRATIVE)
        result = run_agent("ybs", loan([person()]), backend, tool_target=ybs_server)
        system = backend.systems[0]
        self.assertIn("## Regulations As Given", system)
        self.assertIn("Do no outside research", system)
        self.assertIn("614.4165", system)
        provenance = result["regulations_given"]
        self.assertEqual(provenance[0]["citation"], "12 CFR 614.4165")
        self.assertEqual(len(provenance[0]["sha256"]), 64)

    def test_regulations_can_be_switched_off(self):
        backend = self.Recorder(NARRATIVE)
        result = run_agent("ybs", loan([person()]), backend, tool_target=ybs_server, options={"include_regulations": False})
        self.assertNotIn("## Regulations As Given", backend.systems[0])
        self.assertEqual(result["regulations_given"], [])

    def test_every_tool_backed_agent_is_given_regulation_text_that_contains_its_own_rules(self):
        from compliance_common.regulations import regulation_text
        needles = {"ybs": "614.4165", "hpml": "Higher-priced mortgage loan", "trid": "Mortgage loans", "hmda": "Compilation of reportable data",
                   "ecoa": "Adverse action", "vmi": "Information for monitoring purposes", "fzd": "flood insurance", "hvcre": "High volatility commercial real estate"}
        for key, needle in needles.items():
            with self.subTest(agent=key):
                text, provenance = regulation_text(key)
                self.assertIn(needle, text)
                self.assertTrue(provenance)
        self.assertEqual(regulation_text("auditor"), ("", []))


class ContradictionWatchdogTests(unittest.TestCase):
    def test_a_narrative_that_claims_the_opposite_of_the_code_decided_result_is_flagged(self):
        from compliance_common.assemble import contradicts_result
        wrong = "While the loan satisfies the statutory requirements of each individual regulation, there are minor gaps."
        self.assertIsNotNone(contradicts_result("Non-Compliant", wrong))
        self.assertIsNotNone(contradicts_result("Non-Compliant", "The loan is fully compliant with the rule."))
        self.assertIsNone(contradicts_result("Non-Compliant", "The loan is non-compliant: marital status was not requested."))
        self.assertIsNotNone(contradicts_result("Compliant", "There are serious violations and deficiencies in the file."))
        self.assertIsNone(contradicts_result("Compliant", "The file is compliant; all deadlines were met."))
        self.assertIsNone(contradicts_result("Potential Issue", "Some facts are missing."))

    def test_a_narrative_claiming_compliance_on_a_non_compliant_result_is_rejected_then_replaced_by_code(self):
        wrong = dict(NARRATIVE["narrative"], reasoning="The loan is fully compliant and meets all criteria. " * 4)
        VMI = {"vmi_case": {"evaluation_date": "2024-05-01", "primarily_purchase_or_refinance": True, "principal_residence": True, "secured_by_dwelling": True,
                            "dwelling_units": 1, "monitoring": {"items": {"marital_status": {"requested": False}}}}}

        class Stubborn:
            provider, model = "fake", "fake-1"
            calls = 0

            def complete_with_tool(self, system, messages, spec, execute, calls_made, force_first=True):
                calls_made.append({"name": spec["name"], "arguments": {}, "result": execute(spec["name"], {})})
                return json.dumps({"narrative": wrong})

            def complete(self, system, messages, json_mode=True, schema=None):
                self.calls += 1
                self.last = messages[-1]["content"]
                return json.dumps({"narrative": wrong})
        backend = Stubborn()
        result = run_agent("vmi", VMI, backend, tool_target=__import__("compliance_mcp.vmi.server", fromlist=["server"]).server)
        parsed = result["parsed"]
        self.assertEqual(parsed["determination_status"]["result"], "Non-Compliant")
        self.assertEqual(backend.calls, 1)                                         # exactly one retry
        self.assertIn("claims compliance", backend.last)                           # the retry names the violation
        self.assertEqual(parsed["narrative_source"], "deterministic_fallback")
        self.assertNotIn("fully compliant", parsed["compliance_determination_summary"]["reasoning"])
        self.assertIn("VMI Collection Deficiency", parsed["compliance_determination_summary"]["reasoning"])
        self.assertTrue(any("rejected twice" in w for w in parsed["narrative_warnings"]))
        self.assertEqual(result["narrative_guard"]["source"], "deterministic_fallback")

    def test_clean_narratives_carry_no_warnings(self):
        result = run_agent("ybs", loan([person()]), FakeBackend(NARRATIVE), tool_target=ybs_server)
        self.assertNotIn("narrative_warnings", result["parsed"])


class NarrativeSchemaTests(unittest.TestCase):
    def test_the_schema_matches_the_contract_text_and_accepts_a_valid_narrative(self):
        from pathlib import Path
        import jsonschema
        contract = (Path(__file__).resolve().parents[1] / "builders/narrative_contract.md").read_text(encoding="utf-8")
        for key in NARRATIVE_SCHEMA["required"]:
            self.assertIn(f'"{key}"', contract)
        for key in NARRATIVE_SCHEMA["properties"]["narrative"]["required"]:
            self.assertIn(f'"{key}"', contract)
        jsonschema.validate(NARRATIVE, NARRATIVE_SCHEMA)
        for broken in ({"narrative": {"reasoning": "x"}}, {**NARRATIVE, "surprise": 1}, {"narrative": {**NARRATIVE["narrative"], "extra": 1}}):
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(broken, NARRATIVE_SCHEMA)


class ExtractJsonTests(unittest.TestCase):
    def test_inline_reasoning_fences_and_prose_do_not_break_parsing(self):
        from agents.runner import extract_json, split_thinking
        cases = {
            "plain": '{"a": 1}', "fenced": '```json\n{"a": 1}\n```', "prose around": 'Sure: {"a": 1} done',
            "reasoning with braces first": '<think>I could output {"x": maybe} or {nested}</think>\n{"a": 1}',
            "reasoning then fence": '<think>hmm {</think>```json\n{"a": 1}\n```', "closer without opener": 'planning... {oops</think> {"a": 1}',
            "two objects": '{"a": 1} {"a": 2}',
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.assertEqual(extract_json(text), ({"a": 1}, None))
        self.assertIsNone(extract_json("no json here")[0])
        self.assertEqual(split_thinking("<think>why</think>answer"), ("answer", "why"))
        self.assertEqual(split_thinking("answer only"), ("answer only", ""))


class FactCheckTests(unittest.TestCase):
    """The model may restate the record, the case and the regulation text; it may not add facts."""
    LOAN = loan([person()])
    LOAN["case_information"]["case_id"] = LOAN["ybs_case"]["case_id"] = "TEST-2024-001"

    def run_with(self, narrative, backend_cls=FakeBackend):
        return run_agent("ybs", self.LOAN, backend_cls({"narrative": narrative}), tool_target=ybs_server)

    def test_an_invented_number_date_or_identifier_is_rejected_and_the_retry_is_told_why(self):
        bad = dict(NARRATIVE["narrative"], reasoning=GOOD_TEXT + " The borrower earned 777,123 dollars on 2019-03-04 under file TEST-2004-001.")
        seen = []

        class Learns(FakeBackend):
            def complete(self, system, messages, json_mode=True, schema=None):
                seen.append(messages[-1]["content"])
                return json.dumps(NARRATIVE)
        result = self.run_with(bad, Learns)
        self.assertEqual(result["parsed"]["narrative_source"], "model_retry")
        self.assertEqual(result["parsed"]["compliance_determination_summary"]["reasoning"], GOOD_TEXT)
        for needle in ("777,123", "2019-03-04", "TEST-2004-001"):
            self.assertIn(needle, seen[0])
        self.assertIn("model_retry", result["narrative_guard"]["source"])
        self.assertGreaterEqual(len(result["narrative_guard"]["violations"]), 3)

    def test_figures_from_the_record_the_case_and_the_regulation_pass(self):
        ok = dict(NARRATIVE["narrative"], reasoning=GOOD_TEXT + " Case TEST-2024-001 was reviewed under 12 CFR 614.4165.")
        result = self.run_with(ok)
        self.assertEqual(result["parsed"]["narrative_source"], "model")
        self.assertEqual(result["narrative_guard"]["violations"], [])

    def test_an_empty_or_tiny_narrative_is_not_accepted(self):
        result = self.run_with({"reasoning": "ok", "examiner_narrative": "", "data_gaps_followups": []})
        self.assertNotEqual(result["parsed"]["narrative_source"], "model")

    def test_evidence_data_quality_and_change_blocks_come_from_code_not_the_model(self):
        output = dict(NARRATIVE, evidence_assessment={"rating": "Great", "primary_evidence_present": ["Imaginary appraisal"]})
        result = run_agent("ybs", self.LOAN, FakeBackend(output), tool_target=ybs_server)
        evidence = result["parsed"]["evidence_assessment"]
        self.assertNotIn("Imaginary appraisal", json.dumps(result["parsed"]))
        self.assertIn(evidence["rating"], ("Sufficient", "Partially Sufficient", "Insufficient"))
        self.assertFalse(result["parsed"]["change_assessment"]["status_changed"])

    def test_the_model_sees_its_own_case_not_the_whole_loan_file(self):
        loan_file = dict(self.LOAN, unrelated_section={"secret": "SHOULD-NOT-APPEAR-9876"})
        backend = FakeBackend(NARRATIVE, call_tool=False)
        run_agent("ybs", loan_file, backend, tool_target=ybs_server)
        self.assertNotIn("SHOULD-NOT-APPEAR", backend.plain_prompts[0])
        self.assertIn("TEST-2024-001", backend.plain_prompts[0])


class AuditorAgentTests(unittest.TestCase):
    def test_the_auditor_agent_calls_its_tool_over_the_other_agents_results_and_narrates(self):
        from compliance_mcp.auditor.server import server as auditor_server
        from test_auditor_evaluator import SAMPLE, assembled
        payload = {"loan_data": SAMPLE, "agent_results": assembled(SAMPLE)}

        class Backend(FakeBackend):
            def complete_with_tool(self, system, messages, spec, execute, calls_made, force_first=True):
                assert system.index("## Your Tool") < system.index("## Your Role")
                calls_made.append({"name": spec["name"], "arguments": {}, "result": execute(spec["name"], {})})
                return json.dumps(NARRATIVE)
        result = run_agent("auditor", payload, Backend(NARRATIVE), tool_target=auditor_server)
        parsed = result["parsed"]
        self.assertEqual(parsed["domain_determination"]["classification"], "Multiple Cross-Regime Deficiencies")
        self.assertEqual(sorted(f["id"] for f in parsed["cross_regime_findings"]), ["AUD-DEMOGRAPHICS", "AUD-RATE-SPREAD"])
        self.assertEqual(parsed["audit_summary"]["agents_missing"], [])
        self.assertEqual(result["tool_calls"], [{"name": "auditor_evaluate", "by": "model"}])
        self.assertEqual(parsed["audit_determination_summary"], parsed["compliance_determination_summary"])


class AllToolBackedAgentsTests(unittest.TestCase):
    """Every tool-backed agent runs end to end against the sample loan through its own adapter."""

    def test_sample_loan_through_every_tool_backed_agent(self):
        import importlib
        from pathlib import Path
        sample = json.loads((Path(__file__).resolve().parents[1] / "sample_loan.json").read_text(encoding="utf-8"))
        expected = {
            "ybs": ("Young + Beginning + Small", "Compliant", "threshold_evaluation"),
            "hpml": ("Not HPML", "Not Applicable", "hpml_evaluation"),
            "trid": ("TRID Covered", "Compliant", "trid_evaluation"),
            "hmda": ("Potentially Covered", "Potential Issue", "hmda_evaluation"),
            "ecoa": ("No Adverse Action", "Potential Issue", "ecoa_evaluation"),
            "vmi": ("VMI Collection Deficiency", "Non-Compliant", "vmi_evaluation"),
            "fzd": ("Flood Insurance Not Required", "Not Applicable", "fzd_evaluation"),
            "hvcre": ("Non-HVCRE", "Compliant", "hvcre_evaluation"),
        }
        self.assertEqual({k for k, a in AGENTS.items() if a.get("tool")} - {"auditor"}, set(expected))     # no tool-backed agent is left untested
        for key, (classification, status, extra) in expected.items():
            with self.subTest(agent=key):
                target = importlib.import_module(f"compliance_mcp.{key}.server").server

                class Backend(FakeBackend):
                    def complete_with_tool(self, system, messages, spec, execute, calls_made, force_first=True):
                        assert f"Agent: {key} " in system
                        calls_made.append({"name": spec["name"], "arguments": {}, "result": execute(spec["name"], {})})
                        return json.dumps(NARRATIVE)
                result = run_agent(key, sample, Backend(NARRATIVE), tool_target=target)
                parsed = result["parsed"]
                self.assertEqual(parsed["domain_determination"]["classification"], classification)
                self.assertEqual(parsed["determination_status"]["result"], status)
                self.assertIn(extra, parsed)
                self.assertTrue(parsed["determination_trace"])
                self.assertEqual(parsed["agent_metadata"]["decision_id"], result["decision"]["decision_id"])
                self.assertEqual(result["tool_calls"], [{"name": f"{key}_evaluate", "by": "model"}])


if __name__ == "__main__":
    unittest.main()
