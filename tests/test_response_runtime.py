"""R5: code can always write both templates; a model may only phrase the examiner paragraph.

Offline, with fake models, for every evaluator-backed role (the eight domains and the auditor): accepted, over-limit, ungrounded,
malformed and missing replies; one retry; the code fallback; and `templates: code` making no extra model request.
"""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import response_fixtures as rf  # noqa: E402
import test_agent_parity as parity  # noqa: E402
from agents.runner import DRAFTS_KEY, run_agent  # noqa: E402
from compliance_common.narrative import deterministic_narrative  # noqa: E402
from compliance_common.narrative_schema import NARRATIVE_SCHEMA, NARRATIVE_SCHEMA_CODE  # noqa: E402
from compliance_common.templates import examiner  # noqa: E402
from orchestrator.launcher import agent_options  # noqa: E402

ROLES = list(rf.DOMAINS)


def payload_for(key):
    """(payload, direct decision) with at least one finding for every role."""
    if key == "auditor":
        return parity.role_input("auditor")
    case = rf.failing_case(key)
    return {"case_information": {"case_id": "T-1"}, f"{key}_case": case}, rf.evaluate(key, case)


class Model:
    """A fake model. `script` is a list of functions (drafts -> reply dict or str), one per reply, in order: the tool turn, then each retry."""
    provider, model = "fake", "fake-1"

    def __init__(self, key, script):
        self.key, self.script = key, script
        self.drafts, self.decision, self.schemas, self.retry_prompts, self.requests = None, None, [], [], 0

    def _reply(self):
        step = self.script[min(self.requests, len(self.script) - 1)]
        self.requests += 1
        reply = step(self.drafts or [])
        return reply if isinstance(reply, str) else json.dumps(reply)

    def narrative(self):
        return deterministic_narrative(self.decision, self.key)

    def complete_with_tool(self, system, messages, spec, execute, calls_made, force_first=True, schema=None):
        result = execute(spec["name"], {})
        calls_made.append({"name": spec["name"], "arguments": {}, "result": result})
        self.drafts = result.get(DRAFTS_KEY)
        self.decision = {k: v for k, v in result.items() if k != DRAFTS_KEY}
        self.schemas.append(schema)
        return self._reply()

    def complete_seeded(self, system, messages, spec, execute, calls_made, arguments, result, schema=None):
        self.drafts = result.get(DRAFTS_KEY)
        self.decision = {k: v for k, v in result.items() if k != DRAFTS_KEY}
        self.schemas.append(schema)
        return self._reply()

    def complete(self, system, messages, json_mode=True, schema=None):
        self.retry_prompts.append(messages[-1]["content"])
        self.schemas.append(schema)
        return self._reply()


def faithful(model, edit=None):
    """A reply with the narrative and every draft; `edit(rule_id, text) -> text` changes a paragraph."""
    def step(drafts):
        paragraphs = [{"rule_id": d["rule_id"], "text": edit(d["rule_id"], d["draft"]) if edit else d["draft"]} for d in drafts]
        return {"narrative": model.narrative(), "examiner_paragraphs": paragraphs}
    return step


def run(key, script_factory, **options):
    payload, direct = payload_for(key)
    server, _, _ = parity.parts(key)
    model = Model(key, [])
    model.script = script_factory(model)
    result = run_agent(key, payload, model, tool_target=server, options=options or None)
    return result, model, direct


def examiner_of(result):
    return result["parsed"]["response_templates"]["examiner"]


class AcceptedTests(unittest.TestCase):
    def test_every_role_returns_both_templates_and_an_unchanged_decision(self):
        for key in ROLES:
            with self.subTest(role=key):
                result, model, direct = run(key, lambda m: [faithful(m)])
                templates = result["parsed"]["response_templates"]
                self.assertEqual(set(templates), {"templates", "loan_officer", "examiner"})
                self.assertEqual(set(templates["loan_officer"]), {"needed_from_customer", "refer_to_compliance"})
                self.assertTrue(templates["examiner"])
                self.assertEqual({p["source"] for p in templates["examiner"]}, {"model"})
                self.assertEqual(result["decision"]["decision_id"], direct["decision_id"])
                self.assertEqual(result["parsed"]["domain_determination"]["classification"], direct["final_classification"])
                self.assertEqual(result["parsed"]["determination_status"]["result"], direct["compliance_result"])
                self.assertEqual((model.requests, result["parsed"]["narrative_source"]), (1, "model"))
                self.assertNotIn(DRAFTS_KEY, result["decision"], "the drafts are shown to the model only")
                self.assertNotIn("narrative_warnings", result["parsed"])
                self.assertEqual(result["narrative_guard"]["paragraphs"], {"model": len(templates["examiner"])})

    def test_the_model_sees_one_draft_per_finding_in_the_tool_result(self):
        for key in ROLES:
            with self.subTest(role=key):
                result, model, direct = run(key, lambda m: [faithful(m)])
                self.assertEqual([d["rule_id"] for d in model.drafts], [p["rule_id"] for p in examiner.render(direct, key)])
                self.assertTrue(all(d["word_limit"] == examiner.LIMITS[key] for d in model.drafts))
                self.assertEqual(model.schemas, [None], "model mode keeps the default constrained schema")

    def test_a_rephrased_paragraph_that_keeps_every_required_element_is_accepted(self):
        result, model, _ = run("hmda", lambda m: [faithful(m, lambda rule_id, text: text.replace("Basis: ", "Basis: In short, ").replace("Action: ", "Action: To close this, "))])
        self.assertEqual({p["source"] for p in examiner_of(result)}, {"model"})
        self.assertTrue(all("In short," in p["text"] for p in examiner_of(result)))

    def test_the_loan_officer_sheet_is_always_written_by_code(self):
        from compliance_common.templates import loan_officer
        for key in ROLES:
            with self.subTest(role=key):
                result, _, direct = run(key, lambda m: [faithful(m)])
                self.assertEqual(result["parsed"]["response_templates"]["loan_officer"], loan_officer.render(direct))


class RejectedTests(unittest.TestCase):
    def test_an_over_limit_paragraph_is_retried_once_and_then_accepted(self):
        for key in ROLES:
            with self.subTest(role=key):
                long = lambda rule_id, text: text + " " + " ".join(["detail"] * examiner.LIMITS[key])        # noqa: E731
                result, model, _ = run(key, lambda m: [faithful(m, long), faithful(m)])
                self.assertEqual({p["source"] for p in examiner_of(result)}, {"model_retry"})
                self.assertEqual((model.requests, len(model.retry_prompts)), (2, 1))
                self.assertIn("the limit is", model.retry_prompts[0])
                self.assertEqual(result["parsed"]["narrative_source"], "model_retry")

    def test_an_over_limit_paragraph_twice_is_written_by_code_and_passes_the_checks(self):
        for key in ROLES:
            with self.subTest(role=key):
                long = lambda rule_id, text: text + " " + " ".join(["detail"] * examiner.LIMITS[key])        # noqa: E731
                result, model, direct = run(key, lambda m: [faithful(m, long)])
                self.assertEqual(model.requests, 2, "one retry, no more")
                expected = {p["rule_id"]: p for p in examiner.render(direct, key)}
                for p in examiner_of(result):
                    self.assertEqual((p["source"], p["text"]), ("code", expected[p["rule_id"]]["text"]))
                    self.assertEqual(examiner.check_paragraph(p["text"], expected[p["rule_id"]], direct, key), [])
                self.assertIn("written by code", " ".join(result["parsed"]["narrative_warnings"]))
                self.assertEqual(result["parsed"]["narrative_source"], "model_retry", "the narrative itself was fine")

    def test_an_ungrounded_paragraph_is_rejected_and_replaced_by_code(self):
        invented = lambda rule_id, text: text + " The customer owes 987654321 dollars under file ZZ-987654321."        # noqa: E731
        for key in ROLES:
            with self.subTest(role=key):
                result, model, _ = run(key, lambda m: [faithful(m, invented)])
                self.assertEqual({p["source"] for p in examiner_of(result)}, {"code"})
                self.assertIn("987654321", model.retry_prompts[0])
                self.assertNotIn("987654321", json.dumps(result["parsed"]["response_templates"]))

    def test_a_paragraph_that_contradicts_the_result_is_rejected(self):
        wrong = lambda rule_id, text: text + " The loan is fully compliant."        # noqa: E731
        for key in ("vmi", "trid"):
            with self.subTest(role=key):
                result, model, direct = run(key, lambda m: [faithful(m, wrong)])
                self.assertEqual(direct["compliance_result"], "Non-Compliant")
                self.assertEqual({p["source"] for p in examiner_of(result)}, {"code"})
                self.assertIn("claims compliance", model.retry_prompts[0])

    def test_a_paragraph_that_loses_a_required_part_or_the_citation_is_rejected(self):
        for label, edit in (("a part", lambda rule_id, text: text.replace("Basis:", "Because:")),
                            ("the rule id", lambda rule_id, text: text.replace(rule_id, "THE-RULE")),
                            ("the result", lambda rule_id, text: text.replace("Effect:", "Effect (no result stated):").replace("result ", "")),
                            ("the record's words", lambda rule_id, text: text.partition("Condition:")[0] + "Condition: Something else happened. Basis:" + text.partition(" Basis:")[2])):
            with self.subTest(removed=label):
                result, model, _ = run("hmda", lambda m: [faithful(m, edit)])
                self.assertIn("code", {p["source"] for p in examiner_of(result)})
                self.assertTrue(model.retry_prompts)

    def test_malformed_replies_are_retried_then_written_by_code(self):
        for label, bad in (("not json", lambda drafts: "this is not json"),
                           ("no paragraphs key", None),
                           ("empty list", None),
                           ("an unknown rule id", None),
                           ("a duplicate", None)):
            with self.subTest(reply=label):
                def script(m, label=label, bad=bad):
                    def reply(drafts):
                        paragraphs = [{"rule_id": d["rule_id"], "text": d["draft"]} for d in drafts]
                        if label == "no paragraphs key":
                            return {"narrative": m.narrative()}
                        if label == "empty list":
                            return {"narrative": m.narrative(), "examiner_paragraphs": []}
                        if label == "an unknown rule id":
                            return {"narrative": m.narrative(), "examiner_paragraphs": [{"rule_id": "NOPE-1", "text": paragraphs[0]["text"]}, *paragraphs[1:]]}
                        return {"narrative": m.narrative(), "examiner_paragraphs": [*paragraphs, paragraphs[0]]}
                    return [bad or reply]
                result, model, _ = run("hmda", script)
                self.assertEqual(model.requests, 2)
                sources = {p["source"] for p in examiner_of(result)}
                self.assertIn("code", sources)

    def test_a_malformed_first_reply_that_the_retry_repairs_is_marked_model_retry(self):
        result, model, _ = run("hmda", lambda m: [lambda drafts: "not json", faithful(m)])
        self.assertEqual({p["source"] for p in examiner_of(result)}, {"model_retry"})
        self.assertEqual(result["parsed"]["narrative_source"], "model_retry")

    def test_each_paragraph_is_judged_on_its_own(self):
        result, model, direct = run("hmda", lambda m: [faithful(m, lambda rule_id, text: text + " The customer owes 987654321 dollars." if rule_id == "HMDA-COVERAGE" else text)])
        sources = {p["rule_id"]: p["source"] for p in examiner_of(result)}
        self.assertEqual(sources["HMDA-COVERAGE"], "code")
        self.assertEqual({v for k, v in sources.items() if k != "HMDA-COVERAGE"}, {"model"}, "the others passed the first time and are kept")
        self.assertGreater(len(sources), 2)

    def test_a_paragraph_the_retry_fixes_while_another_stays_bad_keeps_both_sources(self):
        def first(m):
            return faithful(m, lambda rule_id, text: text + " 987654321 dollars" if rule_id in ("HMDA-COVERAGE", "HMDA-RATE-SPREAD") else text)

        def second(m):
            return faithful(m, lambda rule_id, text: text + " 987654321 dollars" if rule_id == "HMDA-COVERAGE" else text)
        result, _, _ = run("hmda", lambda m: [first(m), second(m)])
        sources = {p["rule_id"]: p["source"] for p in examiner_of(result)}
        self.assertEqual((sources["HMDA-COVERAGE"], sources["HMDA-RATE-SPREAD"]), ("code", "model_retry"))

    def test_the_retry_names_the_failing_paragraph_and_the_violation(self):
        result, model, _ = run("hmda", lambda m: [faithful(m, lambda rule_id, text: text.replace("Basis:", "Because:") if rule_id == "HMDA-COVERAGE" else text), faithful(m)])
        self.assertIn("HMDA-COVERAGE", model.retry_prompts[0])
        self.assertIn("Requirement:", model.retry_prompts[0])

    def test_a_narrative_that_fails_twice_is_still_replaced_by_code_while_good_paragraphs_survive(self):
        def script(m):
            def reply(drafts):
                return {"narrative": {**m.narrative(), "reasoning": "The loan is fully compliant and meets all criteria. " * 4},
                        "examiner_paragraphs": [{"rule_id": d["rule_id"], "text": d["draft"]} for d in drafts]}
            return [reply]
        result, model, _ = run("vmi", script)
        self.assertEqual(result["parsed"]["narrative_source"], "deterministic_fallback")
        self.assertEqual(model.requests, 2)
        self.assertEqual({p["source"] for p in examiner_of(result)}, {"model"}, "paragraphs that passed the first time are kept")


class CodeModeTests(unittest.TestCase):
    def test_templates_code_asks_the_model_for_nothing_extra_and_makes_no_extra_request(self):
        for key in ROLES:
            for mode in ("model", "seeded"):
                with self.subTest(role=key, tool_mode=mode):
                    result, model, direct = run(key, lambda m: [lambda drafts: {"narrative": m.narrative()}], templates="code", tool_mode=mode)
                    self.assertEqual(model.requests, 1)
                    self.assertEqual(model.retry_prompts, [])
                    self.assertIsNone(model.drafts, "no draft is shown to the model")
                    self.assertEqual(model.schemas, [NARRATIVE_SCHEMA_CODE])
                    self.assertNotIn("examiner_paragraphs", NARRATIVE_SCHEMA_CODE["properties"])
                    expected = {p["rule_id"]: p for p in examiner.render(direct, key)}
                    templates = result["parsed"]["response_templates"]
                    self.assertEqual(templates["templates"], "code")
                    self.assertEqual({p["source"] for p in templates["examiner"]}, {"code"})
                    for p in templates["examiner"]:
                        self.assertEqual(examiner.check_paragraph(p["text"], expected[p["rule_id"]], direct, key), [])
                    self.assertEqual(result["decision"]["decision_id"], direct["decision_id"])
                    self.assertNotIn("narrative_warnings", result["parsed"])

    def test_templates_code_ignores_paragraphs_a_model_volunteers(self):
        result, model, _ = run("hmda", lambda m: [lambda drafts: {"narrative": m.narrative(), "examiner_paragraphs": [{"rule_id": "HMDA-COVERAGE", "text": "x"}]}], templates="code")
        self.assertEqual({p["source"] for p in examiner_of(result)}, {"code"})
        self.assertNotIn(" x", " ".join(p["text"] for p in examiner_of(result)))

    def test_model_and_code_modes_give_the_same_decision_the_same_sheet_and_the_same_findings(self):
        for key in ROLES:
            with self.subTest(role=key):
                a, _, _ = run(key, lambda m: [faithful(m)])
                b, _, _ = run(key, lambda m: [lambda drafts: {"narrative": m.narrative()}], templates="code")
                self.assertEqual(a["decision"]["decision_id"], b["decision"]["decision_id"])
                self.assertEqual(a["parsed"]["response_templates"]["loan_officer"], b["parsed"]["response_templates"]["loan_officer"])
                self.assertEqual([p["rule_id"] for p in examiner_of(a)], [p["rule_id"] for p in examiner_of(b)])
                self.assertEqual([p["text"] for p in examiner_of(a)], [p["text"] for p in examiner_of(b)], "a faithful model echoes the code text")

    def test_the_option_is_validated_defaults_to_model_and_reaches_the_server_options(self):
        with self.assertRaisesRegex(ValueError, "templates"):
            run("ybs", lambda m: [faithful(m)], templates="psychic")
        self.assertEqual(agent_options({"url": "http://127.0.0.1:1/", "templates": "code"}), {"templates": "code"})
        self.assertEqual(agent_options({"url": "http://127.0.0.1:1/"}), {})
        from agents.runner import DEFAULT_OPTIONS
        self.assertEqual(DEFAULT_OPTIONS["templates"], "model")


class NoInputTests(unittest.TestCase):
    def test_an_unavailable_input_still_gets_both_templates_and_makes_no_model_call(self):
        server, _, _ = parity.parts("trid")
        model = Model("trid", [lambda drafts: self.fail("the model was called")])
        result = run_agent("trid", {"case_information": {"case_id": "T-9"}}, model, tool_target=server)
        templates = result["parsed"]["response_templates"]
        self.assertEqual(model.requests, 0)
        self.assertEqual(templates["loan_officer"]["needed_from_customer"], [])
        self.assertTrue(templates["loan_officer"]["refer_to_compliance"])
        self.assertEqual(templates["examiner"], [])


class RegistryTests(unittest.TestCase):
    def test_the_roles_covered_are_exactly_the_registry_roles_with_an_evaluator(self):
        self.assertEqual(set(ROLES), set(parity.DOMAINS) | {"auditor"})

    def test_the_schema_with_paragraphs_is_the_contract_and_the_code_schema_omits_them(self):
        self.assertIn("examiner_paragraphs", NARRATIVE_SCHEMA["required"])
        contract = (Path(__file__).resolve().parents[1] / "builders/narrative_contract.md").read_text(encoding="utf-8")
        self.assertIn('"examiner_paragraphs"', contract)
        self.assertEqual(NARRATIVE_SCHEMA_CODE["required"], ["narrative"])
        self.assertEqual(NARRATIVE_SCHEMA_CODE["properties"]["narrative"], NARRATIVE_SCHEMA["properties"]["narrative"])


if __name__ == "__main__":
    unittest.main()
