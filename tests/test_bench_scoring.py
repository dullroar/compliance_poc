import time
import unittest

from benchmarks.model_bench import ResourceSampler, score_narrative, states_classification, unsupported_numbers

DECISION = {"final_classification": "Not HPML", "compliance_result": "Not Applicable",
            "rule_results": [{"rule_id": "HPML-SPREAD", "outcome": "does_not_apply", "value": "1.26", "threshold": "1.5", "message": "x"},
                             {"rule_id": "HPML-X", "outcome": "unable_to_determine", "message": "needed by 2024-06-01"}],
            "missing_facts": [{"field": "lar.uli", "reason": "r"}, {"field": "lar_context.subject_to_hoepa", "reason": "r"}]}


PAD = " The reviewer should read the decision record for the complete rule-by-rule explanation of this determination."


class ScoringTests(unittest.TestCase):
    def test_a_faithful_narrative_scores_full_marks(self):
        text = "Not HPML: the spread of 1.26 is below the 1.5 threshold. Still needed by 2024-06-01: the uli and whether the loan is subject to hoepa."
        score = score_narrative(DECISION, {}, text, {}, [])
        self.assertEqual((score["accuracy"], score["figure_recall"], score["gap_recall"], score["polarity_ok"]), (100, 1.0, 1.0, True))

    def test_numbers_are_compared_as_numbers_not_strings(self):
        self.assertEqual(score_narrative(DECISION, {}, "Not HPML. 1.260 versus 1.50. 2024-06-01. uli. subject to hoepa." + PAD, {}, [])["figure_recall"], 1.0)

    def test_each_failure_costs_its_share(self):
        base = "Not HPML: the spread of 1.26 is below the 1.5 threshold. Needed by 2024-06-01: the uli and hoepa status subject to hoepa."
        self.assertEqual(score_narrative(DECISION, {}, base, {}, [])["accuracy"], 100)
        self.assertEqual(score_narrative(DECISION, {}, base.replace("Not HPML", "Higher priced"), {}, [])["accuracy"], 80)       # classification not stated
        self.assertLess(score_narrative(DECISION, {}, base.replace("1.26", "9.99"), {}, [])["figure_recall"], 1.0)
        self.assertEqual(score_narrative(DECISION, {}, base, {"violations": ["the number x is unsupported"]}, ["9.99"])["invented_items"], 2)
        self.assertLess(score_narrative(DECISION, {}, base, {"stripped_fields": ["domain_determination"]}, [])["accuracy"], 100)

    def test_polarity_contradictions_are_caught(self):
        ok = "Not HPML 1.26 1.5 2024-06-01 uli hoepa." + PAD
        self.assertFalse(score_narrative(DECISION, {}, ok + " The loan has serious violations and deficiencies.", {}, [])["polarity_ok"])
        bad = {**DECISION, "compliance_result": "Non-Compliant"}
        self.assertFalse(score_narrative(bad, {}, ok + " The loan is fully compliant.", {}, [])["polarity_ok"])
        self.assertTrue(score_narrative(bad, {}, ok + " The loan is non-compliant.", {}, [])["polarity_ok"])

    def test_unsupported_numbers_ignore_single_digits_and_supported_values(self):
        self.assertEqual(unsupported_numbers("Rate 7.85 and 3 items and 12,345 dollars and 99.9", "7.85 12345"), ["99.9"])

    def test_an_empty_narrative_scores_zero_not_a_free_50(self):
        for text in ("", "  \n", "ok"):
            score = score_narrative({**DECISION, "missing_facts": []}, {}, text, {}, [])
            self.assertEqual((score["accuracy"], score["no_narrative"]), (0, True))

    def test_classification_is_recognised_through_negation_but_not_through_the_opposite(self):
        self.assertTrue(states_classification("Not HPML", "The spread is 1.26. The loan does not meet the definition of a Higher-Priced Mortgage Loan (HPML)."))
        self.assertTrue(states_classification("Not HPML", "Result: Not HPML."))
        self.assertTrue(states_classification("HPML", "The loan is an HPML."))
        self.assertFalse(states_classification("Not HPML", "The loan is an HPML and the spread is large."))        # affirmative, no negation
        self.assertFalse(states_classification("Not HPML", "The spread was fine."))
        self.assertTrue(states_classification("Young + Beginning + Small", "The borrower qualifies as Young, Beginning and Small."))

    def test_the_sampler_reads_this_machine(self):
        sampler = ResourceSampler(interval=0.05)
        with sampler:
            time.sleep(0.4)
        summary = sampler.summary()
        self.assertGreater(summary["samples"], 0)
        self.assertGreaterEqual(summary["cores_total"], 1)


if __name__ == "__main__":
    unittest.main()
