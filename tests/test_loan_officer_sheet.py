"""R3: the loan-officer sheet is short, plain and safe.

Every decision record the evaluators produce on the fixture sweep is rendered and checked: sentence and word limits, no internal
field paths, routing by kind, and every missing fact exactly once across the two lists.
"""
import copy
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import response_fixtures as rf  # noqa: E402
from compliance_common.decision import unavailable_record  # noqa: E402
from compliance_common.templates import catalog  # noqa: E402
from compliance_common.templates.loan_officer import render  # noqa: E402

SENTENCE = re.compile(r"(?<=[.!?])\s+")
PATH_TOKEN = re.compile(r"lar_context\.|\blar\.|[a-z_]+\.[a-z_]+\.[a-z_]+|\b[a-z]+_[a-z_]+\b")
PASSIVE = re.compile(r"\b(?:is|are|was|were|been|being)\s+(?!classified\b)\w+ed\b", re.I)


def sentences(text: str) -> list[str]:
    return [s for s in SENTENCE.split(text.strip()) if s]


def rendered():
    for domain, found in rf.records().items():
        for label, decision in found:
            yield domain, label, decision, render(decision)


class LimitTests(unittest.TestCase):
    def test_every_customer_item_has_at_most_two_sentences_of_at_most_twenty_words(self):
        count = 0
        for domain, label, _, sheet in rendered():
            for item in sheet["needed_from_customer"]:
                count += 1
                parts = sentences(item["text"])
                with self.subTest(domain=domain, case=label, field=item["field"]):
                    self.assertLessEqual(len(parts), 2)
                    for sentence in parts:
                        self.assertLessEqual(len(sentence.split()), 20, sentence)
                    self.assertLessEqual(len(item["label"].split()), 8)
        self.assertGreater(count, 100)

    def test_every_referral_has_exactly_one_sentence_of_at_most_twenty_words(self):
        count = 0
        for domain, label, _, sheet in rendered():
            for item in sheet["refer_to_compliance"]:
                count += 1
                parts = sentences(item["text"])
                with self.subTest(domain=domain, case=label, field=item["field"], rules=item["rule_ids"]):
                    self.assertEqual(len(parts), 1, item["text"])
                    self.assertLessEqual(len(parts[0].split()), 20, parts[0])
        self.assertGreater(count, 300)

    def test_no_internal_field_path_or_rule_id_appears_in_the_text(self):
        for domain, label, _, sheet in rendered():
            for item in sheet["needed_from_customer"] + sheet["refer_to_compliance"]:
                shown = [item["text"]] + ([item["label"]] if item["field"] else [])
                for text in shown:
                    with self.subTest(domain=domain, case=label, text=text):
                        self.assertIsNone(PATH_TOKEN.search(text), text)
                        self.assertIsNone(re.search(r"\b[A-Z]{3,5}-[A-Z0-9-]+\b", text), text)

    def test_customer_text_is_active_and_uses_one_word_for_the_person(self):
        for domain, label, _, sheet in rendered():
            for item in sheet["needed_from_customer"]:
                with self.subTest(domain=domain, field=item["field"]):
                    self.assertIsNone(PASSIVE.search(item["text"]), item["text"])
                    self.assertNotRegex(item["text"].lower(), r"\bborrower\b")


class RoutingTests(unittest.TestCase):
    def test_a_customer_request_only_comes_from_an_information_gap_or_a_value_rule(self):
        for domain, label, _, sheet in rendered():
            for item in sheet["needed_from_customer"]:
                kinds = {catalog.resolve_rule(r).kind for r in item["rule_ids"]}
                with self.subTest(domain=domain, case=label, field=item["field"]):
                    self.assertTrue(kinds and kinds <= {"G", "V"}, kinds)

    def test_no_finding_of_kind_p_or_r_is_ever_a_customer_request(self):
        for domain, label, decision, sheet in rendered():
            for item in sheet["needed_from_customer"]:
                for rule_id in item["rule_ids"]:
                    with self.subTest(domain=domain, case=label, rule=rule_id):
                        self.assertNotIn(catalog.resolve_rule(rule_id).kind, ("P", "R"))
            self.assertTrue(domain != "ecoa" or not sheet["needed_from_customer"], "ECOA records what the institution did")

    def test_a_marital_status_inquiry_gap_is_referred_and_never_requested(self):
        decision = rf.evaluate("ecoa", rf.without(rf.base_case("ecoa"), "marital_status_inquiry"))
        sheet = render(decision)
        self.assertEqual(sheet["needed_from_customer"], [])
        texts = " ".join(i["text"] for i in sheet["refer_to_compliance"]).lower()
        self.assertIn("marital status", texts)
        self.assertNotRegex(texts, r"obtain|ask the customer|get the customer")
        self.assertTrue(any("marital_status_inquiry" == i["field"] for i in sheet["refer_to_compliance"]))

    def test_a_customer_route_in_the_catalog_cannot_override_a_p_or_r_rule(self):
        loaded = catalog._load()
        entry = next(e for _, e in loaded["ecoa"]["fields"] if e["match"] == "marital_status_inquiry")
        saved = dict(entry)
        try:
            entry["route"] = "customer"
            decision = rf.evaluate("ecoa", rf.without(rf.base_case("ecoa"), "marital_status_inquiry"))
            sheet = render(decision)
        finally:
            entry.clear()
            entry.update(saved)
        self.assertEqual(sheet["needed_from_customer"], [])
        self.assertTrue(sheet["refer_to_compliance"])

    def test_an_unknown_field_and_an_unavailable_record_are_referred_not_requested(self):
        decision = copy.deepcopy(rf.records()["hpml"][0][1])
        decision["missing_facts"] = [{"field": "something.new.here", "reason": "x"}]
        sheet = render(decision)
        self.assertEqual(sheet["needed_from_customer"], [])
        self.assertEqual(len(sheet["refer_to_compliance"]), 1)
        self.assertEqual(sheet["refer_to_compliance"][0]["text"], catalog.GENERIC_REFER)
        unavailable = unavailable_record("trid", "0.1.0", "trid_case", "Canonical trid_case is required.", {})
        sheet = render(unavailable)
        self.assertEqual(sheet["needed_from_customer"], [])
        self.assertEqual(len(sheet["refer_to_compliance"]), 1)

    def test_rollups_do_not_repeat_the_items_they_summarize(self):
        decision = rf.evaluate("hmda", rf.without(rf.base_case("hmda"), "lar.income"))
        rules = {r["rule_id"] for r in decision["rule_results"]}
        self.assertIn("HMDA-LAR-ITEMS", rules)
        sheet = render(decision)
        self.assertNotIn("HMDA-LAR-ITEMS", [r for i in sheet["refer_to_compliance"] for r in i["rule_ids"]])

    def test_the_applicant_may_decline_wording_is_on_vmi_and_hmda_item_10(self):
        vmi = render(rf.evaluate("vmi", rf.without(rf.base_case("vmi"), "monitoring.items.race")))
        item = next(i for i in vmi["needed_from_customer"] if i["field"] == "monitoring.items.race")
        self.assertTrue(item["decline"])
        self.assertEqual(item["text"], "We must ask for race. The applicant may decline; record the decline.")
        hmda = render(rf.evaluate("hmda", rf.without(rf.base_case("hmda"), "lar.applicant")))
        item = next(i for i in hmda["needed_from_customer"] if i["field"] == "lar.applicant")
        self.assertTrue(item["decline"])
        self.assertIn("may decline; record the decline", item["text"])


class CompletenessTests(unittest.TestCase):
    def test_every_missing_fact_appears_exactly_once_across_the_two_lists(self):
        checked = 0
        for domain, label, decision, sheet in rendered():
            items = sheet["needed_from_customer"] + sheet["refer_to_compliance"]
            wanted = {(m.get("subject_id"), m["field"]) for m in decision.get("missing_facts", [])}
            for key in wanted:
                checked += 1
                with self.subTest(domain=domain, case=label, key=key):
                    self.assertEqual(sum(1 for i in items if (i["subject_id"], i["field"]) == key), 1)
            fields = {(i["subject_id"], i["field"]) for i in items if i["field"] is not None}
            self.assertEqual(fields, wanted)
        self.assertGreater(checked, 400)

    def test_every_failing_rule_is_explained_by_a_missing_fact_or_a_referral(self):
        for domain, label, decision, sheet in rendered():
            covered = {r for i in sheet["needed_from_customer"] + sheet["refer_to_compliance"] for r in i["rule_ids"]}
            for r in decision["rule_results"]:
                if r["outcome"] in ("not_satisfied", "unable_to_determine", "review_required") and r["rule_id"] != "HMDA-LAR-ITEMS":
                    with self.subTest(domain=domain, case=label, rule=r["rule_id"]):
                        self.assertIn(r["rule_id"], covered)

    def test_a_satisfied_case_has_empty_lists(self):
        for domain in ("ybs", "hpml", "trid", "hmda", "ecoa", "vmi", "fzd", "hvcre"):
            decision = rf.evaluate(domain, rf.base_case(domain, 0 if domain != "ybs" else 0))
            sheet = render(decision)
            with self.subTest(domain=domain):
                bad = [r for r in decision["rule_results"] if r["outcome"] in ("not_satisfied", "unable_to_determine", "review_required")]
                if not bad:
                    self.assertEqual((sheet["needed_from_customer"], sheet["refer_to_compliance"]), ([], []))

    def test_ybs_items_are_grouped_by_subject(self):
        people = [{"id": "p1", "type": "person", "is_agricultural_producer": True, "date_of_birth": "1991-06-02", "years_farming": 10},
                  {"id": "p2", "type": "person", "is_agricultural_producer": True, "years_farming": 3, "annual_gross_ag_sales": 1000},
                  {"id": "p3", "type": "person", "is_agricultural_producer": True, "date_of_birth": "1980-01-01", "years_farming": 3}]
        case = {"case_id": "YBS-TEST", "evaluation_date": "2026-06-01", "subjects": people, "determination_subject_ids": ["p1", "p2", "p3"],
                "evidence": [{"id": "app", "type": "application"}]}
        sheet = render(rf.evaluate("ybs", case))
        subjects = [i["subject_id"] for i in sheet["needed_from_customer"]]
        self.assertEqual(subjects, sorted(subjects, key=lambda s: ["p1", "p2", "p3"].index(s)), "items are grouped by subject, in case order")
        self.assertEqual(sorted(set(subjects)), ["p1", "p2", "p3"])
        self.assertEqual([(i["subject_id"], i["field"]) for i in sheet["needed_from_customer"]],
                         [("p1", "annual_gross_ag_sales"), ("p2", "date_of_birth"), ("p3", "annual_gross_ag_sales")])


class GoldenTests(unittest.TestCase):
    """One golden sheet per regime; the text is what a loan officer reads."""

    def sheet(self, domain, dotted, index=0):
        return render(rf.evaluate(domain, rf.without(rf.base_case(domain, index), dotted)))

    def test_ybs_young_date_of_birth_reproduces_the_r3_pattern(self):
        sheet = self.sheet("ybs", "subjects.0.date_of_birth")
        item = next(i for i in sheet["needed_from_customer"] if i["field"] == "date_of_birth")
        self.assertEqual(item["text"], "To be classified as Young, we need the date of birth. We use it to check the age against the Farm Credit limit.")
        self.assertEqual(item["label"], "date of birth")

    def test_golden_text_for_each_regime(self):
        golden = {
            ("hpml", "apor"): ("refer", "The institution must look up the average prime offer rate and record its source."),
            ("trid", "loan_estimate"): ("refer", "Closing staff must record when and how the Loan Estimate was delivered."),
            ("hmda", "lar.income"): ("customer", "The register needs the income that we used in the credit decision. We need the gross yearly income."),
            ("ecoa", "marital_status_inquiry"): ("refer", "Compliance must record whether the institution asked about marital status."),
            ("vmi", "monitoring.items.age"): ("customer", "We must ask for age. The applicant may decline; record the decline."),
            ("fzd", "collateral.structure"): ("customer", "To check flood rules, we need to know if a building or mobile home is on the property."),
            ("hvcre", "property.agricultural_land_bona_fide_farmer"): ("customer", "To check an exclusion, we need to know if the land is for the farmer's own farm needs."),
        }
        for (domain, dotted), (route, text) in golden.items():
            with self.subTest(domain=domain, field=dotted):
                sheet = self.sheet(domain, dotted)
                lists = {"customer": sheet["needed_from_customer"], "refer": sheet["refer_to_compliance"]}
                self.assertIn(text, [i["text"] for i in lists[route]])
                other = lists["refer" if route == "customer" else "customer"]
                self.assertNotIn(text, [i["text"] for i in other])

    def test_auditor_findings_are_all_referrals(self):
        found = [(label, d) for label, d in rf.records()["auditor"] if any(r["outcome"] == "not_satisfied" for r in d["rule_results"])]
        self.assertTrue(found)
        for label, decision in found:
            sheet = render(decision)
            with self.subTest(case=label):
                self.assertEqual(sheet["needed_from_customer"], [])
                self.assertTrue(sheet["refer_to_compliance"])


if __name__ == "__main__":
    unittest.main()
