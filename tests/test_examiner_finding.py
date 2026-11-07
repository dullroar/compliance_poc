"""R4: one examiner paragraph per finding, in a fixed five-part order, under a per-regime word limit.

Order: Requirement, Condition, Basis, Effect, Action. Every decision record the evaluators produce on the fixture sweep is rendered.
"""
import copy
import json
import re
import statistics
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import response_fixtures as rf  # noqa: E402
from compliance_common.assemble import contradicts_result  # noqa: E402
from compliance_common.narrative import allowed_numbers  # noqa: E402
from compliance_common.templates import catalog  # noqa: E402
from compliance_common.templates.examiner import FLOOR, GROUP_THRESHOLD, LAR_SECTIONS, LIMITS, LimitError, findings, render  # noqa: E402

PARTS = ("Requirement", "Condition", "Basis", "Effect", "Action")
OUTCOME_WORDS = {"not_satisfied": "not satisfied", "unable_to_determine": "unable to determine", "review_required": "review required"}
NUMBER = re.compile(r"\d[\d,]*\.?\d*")


def words(text: str) -> int:
    return len(text.split())


def rendered():
    for domain, found in rf.records().items():
        for label, decision in found:
            yield domain, label, decision, render(decision, domain)


class OrderAndElementsTests(unittest.TestCase):
    def test_every_paragraph_has_the_five_parts_in_order(self):
        count = 0
        for domain, label, _, paragraphs in rendered():
            for p in paragraphs:
                count += 1
                positions = [p["text"].find(part + ":") for part in PARTS]
                with self.subTest(domain=domain, case=label, rule=p["rule_id"]):
                    self.assertNotIn(-1, positions)
                    self.assertEqual(positions, sorted(positions))
                    self.assertEqual([p["text"].count(part + ":") for part in PARTS], [1] * 5, "each part appears once")
                    self.assertEqual(p["text"].count("\n"), 0, "one paragraph")
        self.assertGreater(count, 1000)

    def test_each_paragraph_carries_the_rule_id_citation_a_record_figure_or_fact_the_outcome_the_result_and_an_action(self):
        for domain, label, decision, paragraphs in rendered():
            for p in paragraphs:
                entry = catalog.resolve_rule(p["rule_id"])
                finding = p["finding"]
                text = p["text"]
                with self.subTest(domain=domain, case=label, rule=p["rule_id"]):
                    self.assertIn(p["rule_id"], text)
                    self.assertIn(entry.cite, text)
                    self.assertIn(finding["message"].rstrip(".").strip()[:60], text, "the record's own words for the condition")
                    self.assertIn(OUTCOME_WORDS[finding["outcome"]], text.lower())
                    self.assertIn(decision["compliance_result"], text)
                    self.assertIn(decision["final_classification"], text)
                    self.assertRegex(text, r"Action: \S")

    def test_figures_are_quoted_only_from_the_record_or_the_catalog_entry(self):
        for domain, label, decision, paragraphs in rendered():
            record = json.dumps(decision, default=str)
            for p in paragraphs:
                entry = catalog.resolve_rule(p["rule_id"])
                allowed = allowed_numbers(record, entry.cite, entry.text(entry.requirement), entry.text(entry.action))
                shown = p["text"].replace(p["rule_id"], "").replace(entry.cite, "")
                with self.subTest(domain=domain, case=label, rule=p["rule_id"]):
                    for token in NUMBER.findall(shown):
                        normal = allowed_numbers(token)
                        self.assertTrue(normal <= allowed, f"{token} is not in the record or the catalog entry")

    def test_the_paragraph_never_contradicts_the_code_decided_result(self):
        for domain, label, decision, paragraphs in rendered():
            for p in paragraphs:
                with self.subTest(domain=domain, case=label, rule=p["rule_id"]):
                    self.assertIsNone(contradicts_result(decision["compliance_result"], p["text"], domain == "auditor"))

    def test_rendering_is_deterministic(self):
        for domain, found in rf.records().items():
            decision = found[-1][1]
            self.assertEqual(render(decision, domain), render(copy.deepcopy(decision), domain))


class OneParagraphPerFindingTests(unittest.TestCase):
    def test_paragraphs_match_the_failing_rules_one_for_one(self):
        for domain, label, decision, paragraphs in rendered():
            wanted = [(f.get("subject_id"), f["rule_id"], f["outcome"]) for f in findings(decision)]
            made = [(p["subject_id"], p["rule_id"], p["finding"]["outcome"]) for p in paragraphs]
            with self.subTest(domain=domain, case=label):
                self.assertEqual(made, wanted)
                top_level = [r for r in decision["rule_results"] if r["outcome"] in OUTCOME_WORDS]
                self.assertEqual(len(made), len(top_level), "none omitted and none merged against the record's own rule list")

    def test_a_passing_case_has_no_paragraphs_and_not_eligible_is_not_a_finding(self):
        for domain, label, decision, paragraphs in rendered():
            if not any(r["outcome"] in OUTCOME_WORDS for r in decision["rule_results"]):
                with self.subTest(domain=domain, case=label):
                    self.assertEqual(paragraphs, [])
            self.assertFalse([p for p in paragraphs if p["finding"]["outcome"] == "not_eligible"])

    def test_two_subjects_with_the_same_gap_get_two_distinct_paragraphs(self):
        people = [{"id": "p1", "type": "person", "is_agricultural_producer": True, "years_farming": 10, "annual_gross_ag_sales": 1},
                  {"id": "p2", "type": "person", "is_agricultural_producer": True, "years_farming": 3, "annual_gross_ag_sales": 1}]
        case = {"case_id": "YBS-TEST", "evaluation_date": "2026-06-01", "subjects": people, "determination_subject_ids": ["p1", "p2"],
                "evidence": [{"id": "app", "type": "application"}]}
        paragraphs = render(rf.evaluate("ybs", case), "ybs")
        dob = [p for p in paragraphs if p["rule_id"] == "YBS-PERSON-YOUNG-DOB"]
        self.assertEqual([p["subject_id"] for p in dob], ["p1", "p2"])
        self.assertEqual(len({p["text"] for p in dob}), 2)


class LimitTests(unittest.TestCase):
    def test_the_limit_table_covers_every_regime_and_the_floor_is_25(self):
        self.assertEqual(set(LIMITS), set(rf.DOMAINS))
        self.assertEqual(FLOOR, 25)
        for domain in rf.DOMAINS:
            self.assertGreater(LIMITS[domain], FLOOR)

    def test_every_paragraph_is_between_the_floor_and_its_regime_limit(self):
        for domain, label, _, paragraphs in rendered():
            for p in paragraphs:
                with self.subTest(domain=domain, case=label, rule=p["rule_id"]):
                    self.assertGreaterEqual(words(p["text"]), FLOOR)
                    self.assertLessEqual(words(p["text"]), LIMITS[domain])
                    self.assertEqual(p["words"], words(p["text"]))

    def test_the_compact_form_is_used_only_when_the_full_form_is_over_the_limit(self):
        def paragraph_for(extra_words):
            decision = copy.deepcopy(next(d for _, d in rf.records()["hpml"] if any(r["outcome"] in OUTCOME_WORDS for r in d["rule_results"])))
            bad = next(r for r in decision["rule_results"] if r["outcome"] in OUTCOME_WORDS)
            bad["message"] = "The record shows " + " ".join(["detail"] * extra_words) + "."
            return next(p for p in render(decision, "hpml") if p["rule_id"] == bad["rule_id"])

        forms = []
        for extra in range(1, 90):
            try:
                forms.append((extra, paragraph_for(extra)))
            except LimitError:
                break
        self.assertEqual(forms[0][1]["form"], "full")
        switch = next(extra for extra, p in forms if p["form"] == "compact")
        self.assertTrue(all(p["form"] == "full" for extra, p in forms if extra < switch))
        self.assertTrue(all(p["form"] == "compact" for extra, p in forms if extra >= switch))
        for _, p in forms:
            self.assertLessEqual(p["words"], LIMITS["hpml"])
            self.assertIn(p["rule_id"], p["text"])
            self.assertRegex(p["text"], r"Action: \S")
        compact = next(p for extra, p in forms if extra == switch)
        self.assertNotIn(catalog.resolve_rule(compact["rule_id"]).requirement.rstrip("."), compact["text"], "the compact form drops the requirement sentence")
        with self.assertRaises(LimitError):
            paragraph_for(forms[-1][0] + 2)                                        # a message this long fits no form: the caller must escalate

    def test_the_full_form_fits_nearly_every_paragraph_in_every_regime(self):
        total, compact = {}, {}
        for domain, _, _, paragraphs in rendered():
            for p in paragraphs:
                total[domain] = total.get(domain, 0) + 1
                compact[domain] = compact.get(domain, 0) + (p["form"] == "compact")
        for domain in total:
            with self.subTest(domain=domain):
                self.assertLessEqual(compact[domain] / total[domain], 0.10, f"{compact[domain]} of {total[domain]} needed the compact form")


class GroupingTests(unittest.TestCase):
    """Jim's decision of 2026-11-07: above 20 findings in one HMDA result, group the LAR item findings by LAR section; never below, never silently."""

    @classmethod
    def setUpClass(cls):
        case = rf.base_case("hmda")
        case["lar"] = {}
        cls.empty = rf.evaluate("hmda", case)                      # an empty register: every applicable LAR item fails

    def trimmed(self, count):
        """The empty-register decision cut to exactly `count` findings (passing rules kept)."""
        decision = copy.deepcopy(self.empty)
        kept, seen = [], 0
        for r in decision["rule_results"]:
            if r["outcome"] in OUTCOME_WORDS:
                seen += 1
                if seen > count:
                    continue
            kept.append(r)
        decision["rule_results"] = kept
        return decision

    def test_the_threshold_is_20_and_the_sections_partition_the_38_items(self):
        self.assertEqual(GROUP_THRESHOLD, 20)
        items = sorted(n for section in LAR_SECTIONS for n in section["items"])
        self.assertEqual(items, list(range(1, 39)))
        self.assertEqual(len({section["id"] for section in LAR_SECTIONS}), len(LAR_SECTIONS))

    def test_the_empty_register_is_over_the_threshold(self):
        self.assertGreater(len(findings(self.empty)), GROUP_THRESHOLD)

    def test_at_20_findings_nothing_is_grouped_and_at_21_the_lar_items_are(self):
        at_20 = render(self.trimmed(20), "hmda")
        self.assertEqual(len(at_20), 20)
        self.assertFalse(any(p["grouped"] for p in at_20))
        at_21 = render(self.trimmed(21), "hmda")
        self.assertTrue(any(p["grouped"] for p in at_21))
        self.assertLess(len(at_21), 21)

    def test_every_finding_is_in_exactly_one_paragraph_and_nothing_else_is_merged(self):
        decision = self.empty
        paragraphs = render(decision, "hmda")
        wanted = [f["rule_id"] for f in findings(decision)]
        listed = [rule_id for p in paragraphs for rule_id in p["rule_ids"]]
        self.assertEqual(sorted(listed), sorted(wanted), "every finding appears once, none omitted or duplicated")
        for p in paragraphs:
            if not p["grouped"]:
                self.assertEqual(len(p["rule_ids"]), 1)
                self.assertFalse(p["rule_id"].startswith("HMDA-LAR-") and p["rule_id"] != "HMDA-LAR-ITEMS" and len(findings(decision)) > GROUP_THRESHOLD,
                                 "a LAR item finding must be grouped above the threshold")
            else:
                self.assertGreater(len(p["rule_ids"]), 1)
                sections = {next(s["id"] for s in LAR_SECTIONS if int(rule_id[-2:]) in s["items"]) for rule_id in p["rule_ids"]}
                self.assertEqual(len(sections), 1, "one paragraph covers one section")
                for rule_id in p["rule_ids"]:
                    self.assertIn(rule_id, p["text"])

    def test_a_grouped_paragraph_has_the_five_parts_in_order_within_the_limit_and_the_outcome_and_result(self):
        grouped = [p for p in render(self.empty, "hmda") if p["grouped"]]
        self.assertGreaterEqual(len(grouped), 3)
        for p in grouped:
            with self.subTest(section=p["rule_id"]):
                positions = [p["text"].find(part + ":") for part in PARTS]
                self.assertNotIn(-1, positions)
                self.assertEqual(positions, sorted(positions))
                self.assertEqual([p["text"].count(part + ":") for part in PARTS], [1] * 5)
                self.assertGreaterEqual(p["words"], FLOOR)
                self.assertLessEqual(p["words"], LIMITS["hmda"])
                self.assertIn(self.empty["compliance_result"], p["text"])
                outcomes = {f["outcome"] for f in p["findings"]}
                self.assertTrue(all(OUTCOME_WORDS[o] in p["text"].lower() for o in outcomes))
                self.assertRegex(p["text"], r"Action: \S")

    def test_a_grouped_paragraph_quotes_no_figure_that_the_record_or_the_section_entry_lacks(self):
        record = json.dumps(self.empty, default=str)
        for p in render(self.empty, "hmda"):
            if not p["grouped"]:
                continue
            section = next(s for s in LAR_SECTIONS if s["id"] == p["section"])
            allowed = allowed_numbers(record, section["cite"], section["requirement"], section["action"])
            shown = re.sub(r"HMDA-LAR-\d\d|HMDA-LAR-SECTION-[A-Z]+", "", p["text"]).replace(section["cite"], "")
            for token in NUMBER.findall(shown):
                with self.subTest(section=p["section"], token=token):
                    self.assertTrue(allowed_numbers(token) <= allowed)

    def test_grouping_makes_the_report_shorter_without_dropping_a_finding(self):
        grouped_words = sum(p["words"] for p in render(self.empty, "hmda"))
        decision = copy.deepcopy(self.empty)
        ungrouped_words = 0
        for f in findings(decision):                                     # the one-paragraph-each text, for the size comparison only
            from compliance_common.templates import examiner
            ungrouped_words += len(examiner._paragraph(f, decision, "hmda", True).split())
        self.assertLess(grouped_words, ungrouped_words / 2)

    def test_grouping_is_deterministic(self):
        self.assertEqual(render(self.empty, "hmda"), render(copy.deepcopy(self.empty), "hmda"))


def calibration() -> dict[str, dict[str, float]]:
    """Min, median, p95 and max words per regime, and findings per loan, on the fixture sweep (evidence for step 03)."""
    out = {}
    for domain, found in rf.records().items():
        counts, per_loan = [], []
        for _, decision in found:
            paragraphs = render(decision, domain)
            per_loan.append(len(paragraphs))
            counts += [p["words"] for p in paragraphs]
        counts.sort()
        out[domain] = {"n": len(counts), "min": counts[0], "median": statistics.median(counts), "p95": counts[int(0.95 * (len(counts) - 1))],
                       "max": counts[-1], "limit": LIMITS[domain], "findings_per_loan_max": max(per_loan),
                       "findings_per_loan_median": statistics.median(per_loan)}
    return out


if __name__ == "__main__":
    unittest.main()
