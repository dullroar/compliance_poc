"""R6: the report is assembled by code from the role results; the model writes at most one short summary of at most 150 words.

Offline. Role results come from the real evaluators run through the agent runner with fake models, so the report is built from
exactly what the registry roles return.
"""
import argparse
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_response_runtime as runtime  # noqa: E402
import response_fixtures as rf  # noqa: E402
from agent_prompts import AGENTS  # noqa: E402
from agents.backends import ANTHROPIC_MAX_TOKENS, MAX_TOKENS  # noqa: E402
from agents.runner import run, run_narrative_agent  # noqa: E402
from compliance_common.templates import report  # noqa: E402
from orchestrator.batch import _as_text_or_parsed  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GOOD_SUMMARY = ("Open findings need action in several roles. Start with the roles whose result is not Compliant, "
                "refer the compliance items first, and ask the customer only for the items on the loan-officer sheet.")


def role_results(templates="code", empty_hmda=False):
    """{role: parsed result} for all nine evaluator roles, each with at least one finding."""
    results = {}
    for key in runtime.ROLES:
        payload, _ = runtime.payload_for(key)
        if key == "hmda" and empty_hmda:
            case = rf.base_case("hmda")
            case["lar"] = {}
            payload = {"case_information": {"case_id": "T-1"}, "hmda_case": case}
        server, _, _ = runtime.parity.parts(key)
        model = runtime.Model(key, [])
        model.script = [lambda drafts, model=model: {"narrative": model.narrative(), "examiner_paragraphs": [{"rule_id": d["rule_id"], "text": d["draft"]} for d in drafts]}]
        results[key] = run(key, payload, model, tool_target=server, options={"templates": templates})["parsed"]
    return results


class SummaryBackend:
    provider, model = "fake", "fake-1"

    def __init__(self, text):
        self.text, self.requests, self.messages = text, 0, []

    def complete(self, system, messages, json_mode=True, schema=None):
        self.requests += 1
        self.messages.append(messages)
        if isinstance(self.text, Exception):
            raise self.text
        return self.text


class AssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = role_results()
        cls.report = report.build_report(cls.results, GOOD_SUMMARY)

    def test_the_report_has_its_sections_in_order(self):
        headings = re.findall(r"(?m)^(#{1,3}) (.+)$", self.report)
        titles = [t for level, t in headings if level in ("#", "##")]
        self.assertEqual(titles, ["Compliance Review Summary", "Summary", "Results", "Loan officer sheet", "Examiner findings", "Cross-regime findings"])

    def test_it_contains_both_templates_for_every_regime_verbatim(self):
        for key, parsed in self.results.items():
            templates = parsed["response_templates"]
            for p in templates["examiner"]:
                with self.subTest(role=key, rule=p["rule_id"]):
                    self.assertIn(p["text"], self.report)
            for item in templates["loan_officer"]["needed_from_customer"] + templates["loan_officer"]["refer_to_compliance"]:
                with self.subTest(role=key, item=item["text"]):
                    self.assertIn(item["text"], self.report)

    def test_the_auditor_findings_are_in_their_own_section_and_domain_findings_are_not(self):
        examiner_part, _, cross = self.report.partition("## Cross-regime findings")
        for p in self.results["auditor"]["response_templates"]["examiner"]:
            self.assertIn(p["text"], cross)
            self.assertNotIn(p["text"], examiner_part)
        for key in runtime.ROLES:
            if key != "auditor":
                for p in self.results[key]["response_templates"]["examiner"]:
                    self.assertNotIn(p["text"], cross)

    def test_every_finding_of_every_role_is_in_the_report_once(self):
        for key, parsed in self.results.items():
            for p in parsed["response_templates"]["examiner"]:
                for rule_id in p["rule_ids"]:
                    with self.subTest(role=key, rule=rule_id):
                        self.assertEqual(self.report.count(f"[{p['rule_id']};"), 1)
                        self.assertIn(rule_id, self.report)

    def test_the_results_table_states_each_roles_classification_and_result(self):
        for key, parsed in self.results.items():
            row = next(line for line in self.report.splitlines() if line.startswith("| ") and parsed["agent_metadata"]["agent_name"] in line)
            self.assertIn(parsed["domain_determination"]["classification"], row)
            self.assertIn(parsed["determination_status"]["result"], row)

    def test_assembly_is_deterministic_and_adds_no_text_beyond_the_parts(self):
        self.assertEqual(self.report, report.build_report(self.results, GOOD_SUMMARY))
        parts = " ".join(p["text"] for r in self.results.values() for p in r["response_templates"]["examiner"])
        sheet = " ".join(i["text"] + " " + i["label"] for r in self.results.values() for k in ("needed_from_customer", "refer_to_compliance")
                         for i in r["response_templates"]["loan_officer"][k])
        overhead = len(self.report.split()) - len(parts.split()) - len(sheet.split()) - len(GOOD_SUMMARY.split())
        self.assertLess(overhead, 60 + 40 * len(self.results), "headings, the table and list marks only")

    def test_a_role_with_no_result_is_listed_and_never_reads_as_a_pass(self):
        results = dict(self.results)
        results["trid"] = {"agent_key": "trid", "status": "failed", "failure": "RuntimeError: trid unreachable"}
        results["fzd"] = "prose from an agent that should have returned a result"
        text = report.build_report(results, None)
        self.assertIn("| TRID | no result | no result | not reviewed |", text)
        self.assertIn("## Roles with no result", text)
        self.assertIn("TRID: RuntimeError: trid unreachable", text)
        self.assertIn("FZD: the role returned text, not a structured result", text)
        self.assertIn("No result was returned for TRID, FZD; do not read that as a pass.", text)
        self.assertNotRegex(text.split("## Results")[1].split("##")[0], r"(?i)trid[^\n]*compliant")

    def test_a_clean_review_says_so_instead_of_leaving_empty_sections(self):
        clean = {k: dict(v, response_templates={"templates": "code", "loan_officer": {"needed_from_customer": [], "refer_to_compliance": []}, "examiner": []})
                 for k, v in self.results.items()}
        text = report.build_report(clean, None)
        for line in ("Nothing is needed from the customer.", "Nothing to refer.", "No regime has an open finding.", "The auditor reported no cross-regime finding."):
            self.assertIn(line, text)


class SizeTests(unittest.TestCase):
    def test_the_report_is_bounded_even_for_an_empty_hmda_register(self):
        results = role_results(empty_hmda=True)
        text = report.build_report(results, GOOD_SUMMARY)
        hmda = results["hmda"]["response_templates"]["examiner"]
        self.assertTrue(any(p["grouped"] for p in hmda), "the 29+ findings were grouped by LAR section")
        self.assertLess(len(hmda), 10)
        self.assertLess(len(text.split()), 4000)
        self.assertLess(len(text), 30000)


class SummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = role_results()

    def narrate(self, text):
        backend = SummaryBackend(text)
        return run_narrative_agent("narrative", _as_text_or_parsed({k: {"parsed": v, "raw_text": ""} for k, v in self.results.items()}), backend), backend

    def test_a_good_summary_is_used_and_is_the_only_model_text_in_the_report(self):
        result, backend = self.narrate(GOOD_SUMMARY)
        self.assertEqual((result["summary_source"], backend.requests), ("model", 1))
        self.assertIn(GOOD_SUMMARY, result["raw_text"])
        self.assertEqual(result["raw_text"], report.build_report(self.results, GOOD_SUMMARY))
        self.assertEqual((result["parsed"], result["parse_error"]), (None, None))

    def test_the_model_is_shown_a_digest_not_the_report_and_makes_one_request(self):
        result, backend = self.narrate(GOOD_SUMMARY)
        shown = backend.messages[0][-1]["content"]
        prefix = AGENTS["narrative"]["user_message_prefix"] + "\n\n"
        self.assertTrue(shown.startswith(prefix))
        self.assertEqual(json.loads(shown[len(prefix):]), report.digest(self.results))
        for parsed in self.results.values():
            for p in parsed["response_templates"]["examiner"]:
                self.assertNotIn(p["text"], shown)
        self.assertLess(len(shown), 6000)

    def test_a_summary_over_150_words_or_not_plain_or_ungrounded_is_replaced_by_code_and_the_report_is_complete(self):
        cases = {"too long": " ".join(["word"] * 151) + ".",
                 "json": '{"summary": "Open findings need action."}',
                 "fenced": "```\nOpen findings need action.\n```",
                 "a table": "| a | b |\n| - | - |",
                 "invented figure": GOOD_SUMMARY + " The customer owes 987654321 dollars.",
                 "empty after cleaning": "# Heading only"}
        for label, text in cases.items():
            with self.subTest(summary=label):
                result, backend = self.narrate(text)
                self.assertEqual((result["summary_source"], backend.requests), ("code", 1), "no retry: one request")
                self.assertTrue(result["summary_violations"])
                self.assertEqual(result["raw_text"], report.build_report(self.results, None))
                self.assertNotIn("987654321", result["raw_text"])
                self.assertLessEqual(len(report.code_summary(self.results).split()), report.SUMMARY_WORD_LIMIT)

    def test_a_summary_of_exactly_150_words_is_accepted(self):
        text = " ".join(["Open"] * 150)
        result, _ = self.narrate(text)
        self.assertEqual((result["summary_source"], result["summary_words"]), ("model", 150))

    def test_heading_lines_a_model_adds_are_dropped_not_the_sentences(self):
        result, _ = self.narrate("# Compliance narrative\n\n" + GOOD_SUMMARY)
        self.assertEqual(result["summary_source"], "model")
        self.assertEqual(result["raw_text"].count("# Compliance narrative"), 0)
        self.assertIn(GOOD_SUMMARY, result["raw_text"])

    def test_the_code_summary_states_results_findings_and_missing_roles_accurately(self):
        results = dict(self.results, trid={"agent_key": "trid", "status": "failed", "failure": "boom"})
        text = report.code_summary(results)
        self.assertIn("HMDA Potential Issue", text)
        self.assertIn("Findings are open in", text)
        self.assertIn("No result was returned for TRID", text)
        self.assertNotRegex(report.code_summary({k: v for k, v in results.items() if k in ("hmda", "vmi")}), r"(?<!Non-)Compliant")

    def test_a_failed_model_request_fails_the_stage_and_writes_no_report(self):
        with self.assertRaisesRegex(RuntimeError, "no output"):
            self.narrate(RuntimeError("Anthropic returned no output text"))

    def test_results_without_templates_keep_the_old_passthrough(self):
        backend = SummaryBackend("# Report\n\nAll findings explained.")
        result = run("narrative", {"hpml": {"classification": "Not HPML"}}, backend)
        self.assertEqual((result["raw_text"], result.get("parsed"), result.get("parse_error")), ("# Report\n\nAll findings explained.", None, None))
        self.assertNotIn("summary_source", result)

    def test_the_summary_is_far_below_the_output_cap(self):
        # 150 words is about 200 tokens; allow 4 tokens per word. The old report was cut at the 16384-token cap.
        self.assertLessEqual(report.SUMMARY_WORD_LIMIT * 4, 0.10 * min(MAX_TOKENS, ANTHROPIC_MAX_TOKENS))


class PromptTests(unittest.TestCase):
    def test_the_narrative_prompt_asks_for_one_short_summary_and_nothing_else(self):
        prompt = AGENTS["narrative"]["system_prompt"]
        self.assertEqual(AGENTS["narrative"]["version"], "0.3.0")
        self.assertIn("ONE paragraph of at most 150 words", prompt)
        for gone in ("Loan Officer Coaching Narrative", "Examiner Narrative", "Compliance Officer Narrative", "Internal Audit Narrative", "Executive Summary",
                     "Remediation", "coaching"):
            self.assertNotIn(gone, prompt)
        self.assertLess(len(prompt), 3000, "the old multi-audience prompt was about 14,000 characters")
        self.assertNotIn("Return ONLY the Markdown report", prompt)


class CommandTests(unittest.TestCase):
    """`orchestrator.cli batch` keeps its behavior: the stage follows the auditor, a failure is visible and writes no empty report."""

    def run_cli(self, narrative_result):
        from orchestrator import batch, cli
        import test_batch_concurrency as tb
        directory = tempfile.mkdtemp()
        loan = os.path.join(directory, "loan.json")
        with open(loan, "w", encoding="utf-8") as f:
            json.dump({"loan": 1}, f)
        args = argparse.Namespace(loan_file=loan, config=None, concurrency=1, agents=["hmda", "ybs"], spawn_local=False, provider=None, model=None,
                                  json_out=os.path.join(directory, "results.json"), narrative_out=os.path.join(directory, "report.md"))

        async def send(url, payload, httpx_client=None):
            key = url.rstrip("/").rsplit("/", 1)[1]
            return narrative_result if key == "narrative" else {"parsed": tb.Transport.parsed(key), "raw_text": "{}"}
        err, code = io.StringIO(), None
        with mock.patch.object(batch, "send", send), mock.patch.object(cli, "load_agents", return_value=tb.CONFIG_ALL), contextlib.redirect_stderr(err):
            try:
                cli._batch(args)
            except SystemExit as exit_:
                code = exit_.code
        return args, code, err.getvalue()

    def test_the_assembled_report_is_written_and_a_code_summary_is_reported_on_stderr(self):
        args, code, err = self.run_cli({"parsed": None, "raw_text": "# Compliance Review Summary\n\nbody", "summary_source": "code", "summary_violations": ["the summary has 151 words; the limit is 150"]})
        self.assertIsNone(code)
        self.assertEqual(Path(args.narrative_out).read_text(encoding="utf-8"), "# Compliance Review Summary\n\nbody")
        self.assertIn("Narrative summary written by code", err)

    def test_a_failed_narrative_still_exits_nonzero_writes_no_report_and_saves_the_batch(self):
        args, code, err = self.run_cli({"parsed": None, "raw_text": "", "parse_error": "RuntimeError: narrative unreachable"})
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(args.narrative_out))
        self.assertEqual(sorted(json.loads(Path(args.json_out).read_text(encoding="utf-8"))), ["auditor", "hmda", "ybs"])
        self.assertIn("NOT written", err)


if __name__ == "__main__":
    unittest.main()
