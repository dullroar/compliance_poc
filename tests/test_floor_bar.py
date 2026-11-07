"""Offline tests of the tune-ais bar (benchmarks/floor_bar.py): every failure kind has a record that must fail; none needs a model."""
import copy
import json
from decimal import Decimal
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks import floor_bar as bar  # noqa: E402
from benchmarks import floor_sweep as sweep  # noqa: E402
from compliance_common.templates import examiner  # noqa: E402

SCENARIOS = ["sample", "fail:ybs", "gap:ybs"]


def paragraph(source="model", words=60, **extra):
    return {"rule_id": "YBS-X", "source": source, "words": words, "problems": [], **extra}


def record(role="ybs", **overrides):
    """A record that passes every check as a model run: change one field to make exactly one thing wrong."""
    base = {"role": role, "rung": 1, "scenario": "sample", "tool_mode": "model", "rep": 0, "design": "model",
            "narrative_source": "model", "attempts": 1, "stopped_at_max_tokens": False,
            "decision_id": "d" * 64, "classification": "Young", "direct_decision_id": "d" * 64, "direct_classification": "Young",
            "paragraphs": [paragraph()], "items": [{"kind": "customer", "sentences": 2, "max_sentence_words": 19},
                                                    {"kind": "refer", "sentences": 1, "max_sentence_words": 12}]}
    base.update(overrides)
    return base


def narrative(**summary):
    return {"role": "narrative", "rung": 1, "scenario": "sample", "tool_mode": "model", "rep": 0, "design": "model", "stopped_at_max_tokens": False,
            "summary": {"source": "model", "words": 90, "violations": [], **summary}}


def runs(rung=1, make=record, scenarios=SCENARIOS):
    return [make(scenario=s, tool_mode=m, rep=r, rung=rung) for s, m, r in sorted(bar.expected_cells(rung, scenarios), key=str)]


class CheckTests(unittest.TestCase):
    def test_a_good_run_passes_every_check_and_is_first_pass(self):
        self.assertEqual(bar.run_checks(record()), {"T1": True, "T2": True, "T3": True, "T4": True})
        self.assertTrue(bar.run_passes(record()))
        self.assertTrue(bar.first_pass(record()))

    def test_t1_fails_for_a_code_fallback_or_a_missing_source_and_passes_model_retry(self):
        for source in ("deterministic_fallback", "deterministic_no_input", "code", None):
            with self.subTest(source=source):
                self.assertFalse(bar.t1(record(narrative_source=source)))
        self.assertTrue(bar.t1(record(narrative_source="model_retry")))
        self.assertFalse(bar.t1(narrative(source="code")))
        self.assertTrue(bar.t1(narrative()))

    def test_t2_fails_when_truncated_and_when_unrecorded(self):
        self.assertFalse(bar.t2(record(stopped_at_max_tokens=True)))
        no_field = record()
        del no_field["stopped_at_max_tokens"]
        self.assertFalse(bar.t2(no_field))
        self.assertFalse(bar.t2(record(stopped_at_max_tokens=None)))

    def test_t3_fails_on_a_different_id_a_different_classification_or_a_missing_value(self):
        self.assertFalse(bar.t3(record(decision_id="e" * 64)))
        self.assertFalse(bar.t3(record(classification="Beginning")))
        self.assertFalse(bar.t3(record(direct_decision_id=None, decision_id=None)))
        self.assertFalse(bar.t3(record(direct_classification=None, classification=None)))
        self.assertTrue(bar.t3(narrative()))                                  # the summary role has no decision

    def test_t4_fails_for_each_way_a_paragraph_can_miss_its_limits(self):
        limit = examiner.LIMITS["ybs"]
        cases = {"over the regime limit": paragraph(words=limit + 1), "under the floor": paragraph(words=examiner.FLOOR - 1),
                 "a recorded problem": paragraph(problems=["no action"]), "flagged over limit by code": paragraph(over_limit=True),
                 "rewritten by code after the retry": paragraph(source="code"), "no word count": paragraph(words=None)}
        for name, bad in cases.items():
            with self.subTest(name=name):
                self.assertFalse(bar.t4(record(paragraphs=[paragraph(), bad])))
        self.assertTrue(bar.t4(record(paragraphs=[paragraph(words=limit), paragraph(words=examiner.FLOOR), paragraph(source="model_retry")])))
        self.assertFalse(bar.t4(record(role="ybs", paragraphs=[paragraph(words=examiner.LIMITS["hmda"])])))      # each regime has its own limit
        self.assertTrue(bar.t4(record(role="hmda", paragraphs=[paragraph(words=examiner.LIMITS["hmda"])])))

    def test_t4_fails_for_each_way_a_sheet_item_can_miss_its_limits(self):
        bad_items = {"customer, three sentences": {"kind": "customer", "sentences": 3, "max_sentence_words": 10},
                     "customer, sentence too long": {"kind": "customer", "sentences": 1, "max_sentence_words": 21},
                     "referral, two sentences": {"kind": "refer", "sentences": 2, "max_sentence_words": 10},
                     "referral, sentence too long": {"kind": "refer", "sentences": 1, "max_sentence_words": 21},
                     "unknown kind": {"kind": "other", "sentences": 1, "max_sentence_words": 5},
                     "empty": {"kind": "refer", "sentences": 0, "max_sentence_words": 0}, "no counts": {"kind": "refer"}}
        for name, bad in bad_items.items():
            with self.subTest(name=name):
                self.assertFalse(bar.t4(record(items=[bad])))
        self.assertTrue(bar.t4(record(items=[])))                             # no findings, no sheet items
        self.assertFalse(bar.t4(record(items=None)))
        self.assertFalse(bar.t4(record(paragraphs=None)))

    def test_t4_for_the_summary_checks_length_violations_and_source(self):
        self.assertTrue(bar.t4(narrative(words=bar.SUMMARY_WORD_LIMIT)))
        for bad in ({"words": bar.SUMMARY_WORD_LIMIT + 1}, {"violations": ["adds a number"]}, {"words": 0}, {"source": "code"}, {"words": None}):
            with self.subTest(bad=bad):
                self.assertFalse(bar.t4(narrative(**bad)))
        self.assertFalse(bar.t4({**narrative(), "summary": None}))

    def test_a_code_rung_passes_t1_by_design_and_is_still_held_to_t4(self):
        code = record(design="code", narrative_source="code", attempts=0, paragraphs=[paragraph(source="code")])
        self.assertTrue(bar.run_passes(code))
        self.assertTrue(bar.first_pass(code))
        self.assertFalse(bar.t4({**code, "paragraphs": [paragraph(source="code", over_limit=True)]}))
        self.assertFalse(bar.t4({**code, "paragraphs": [paragraph(source="code", words=examiner.LIMITS["ybs"] + 5)]}))
        self.assertFalse(bar.t3({**code, "decision_id": "x"}))

    def test_under_templates_code_the_paragraphs_are_code_by_design_and_only_the_narrative_is_the_models_to_get_right(self):
        """Recorded amendment to the bar (Jim 2026-11-07, measure rung 1 with templates: code): a paragraph source of "code" is not a rewrite there."""
        coded = record(templates="code", paragraphs=[paragraph(source="code")])
        self.assertTrue(bar.t4(coded))
        self.assertTrue(bar.first_pass(coded))
        self.assertFalse(bar.t4(record(templates="model", paragraphs=[paragraph(source="code")])))         # unchanged for templates: model
        self.assertFalse(bar.t4(record(paragraphs=[paragraph(source="code")])))                              # and when the field is absent
        self.assertFalse(bar.t4(record(templates="code", paragraphs=[paragraph(source="code", words=examiner.LIMITS["ybs"] + 1)])))      # limits still hold
        self.assertFalse(bar.t4(record(templates="code", paragraphs=[paragraph(source="code", over_limit=True)])))
        self.assertFalse(bar.t1(record(templates="code", narrative_source="deterministic_fallback")))         # the narrative must still be the model's
        self.assertFalse(bar.first_pass(record(templates="code", narrative_source="model_retry", paragraphs=[paragraph(source="code")])))

    def test_first_pass_needs_no_retry_anywhere(self):
        self.assertFalse(bar.first_pass(record(narrative_source="model_retry")))
        self.assertFalse(bar.first_pass(record(paragraphs=[paragraph(), paragraph(source="model_retry")])))
        self.assertTrue(bar.run_passes(record(narrative_source="model_retry")))        # it still passes T1-T4: only the rate suffers
        self.assertFalse(bar.first_pass(record(narrative_source="deterministic_fallback")))
        self.assertTrue(bar.first_pass(narrative()))

    def test_sentences_splits_on_terminal_punctuation_only(self):
        self.assertEqual(bar.sentences("One two. Three four? Five!"), ["One two.", "Three four?", "Five!"])
        self.assertEqual(bar.sentences("No stop"), ["No stop"])
        self.assertEqual(bar.sentences(""), [])
        self.assertEqual(bar.sentences("A 3.5 rate applies."), ["A 3.5 rate applies."])


class SettingTests(unittest.TestCase):
    def test_every_cell_good_clears_the_bar(self):
        verdict = bar.setting_verdict(runs(), rung=1, scenarios=SCENARIOS)
        self.assertEqual((verdict["clears"], verdict["runs"], verdict["expected"], verdict["first_pass_rate"]), (True, 18, 18, 1.0))
        self.assertEqual(verdict["reasons"], [])

    def test_the_grid_is_scenarios_times_both_modes_times_three_repetitions(self):
        self.assertEqual(len(bar.expected_cells(1, SCENARIOS)), 3 * 2 * 3)
        self.assertEqual({m for _, m, _ in bar.expected_cells(1, SCENARIOS)}, {"model", "seeded"})
        self.assertEqual({r for _, _, r in bar.expected_cells(1, SCENARIOS)}, {0, 1, 2})
        self.assertEqual(bar.expected_cells(0, SCENARIOS), {(s, None, 0) for s in SCENARIOS})

    def test_one_bad_run_in_any_check_fails_the_setting(self):
        bad = {"T1": {"narrative_source": "deterministic_fallback"}, "T2": {"stopped_at_max_tokens": True},
               "T3": {"classification": "Other"}, "T4": {"paragraphs": [paragraph(words=500)]}}
        for name, change in bad.items():
            with self.subTest(check=name):
                rows = runs()
                rows[4].update(change)
                verdict = bar.setting_verdict(rows, rung=1, scenarios=SCENARIOS)
                self.assertFalse(verdict["clears"])
                self.assertEqual(verdict["failures"][name], 1)
                self.assertTrue(any(name in r for r in verdict["reasons"]), verdict["reasons"])

    def test_a_missing_skipped_or_timed_out_run_is_not_a_pass(self):
        rows = runs()
        del rows[0]
        verdict = bar.setting_verdict(rows, rung=1, scenarios=SCENARIOS)
        self.assertFalse(verdict["clears"])
        self.assertIn("incomplete: 17 of 18 runs", verdict["reasons"])
        self.assertFalse(bar.setting_verdict([], rung=1, scenarios=SCENARIOS)["clears"])
        self.assertFalse(bar.setting_verdict(runs()[:9], rung=1, scenarios=SCENARIOS)["clears"])

    def test_a_duplicate_or_unplanned_run_is_flagged(self):
        rows = runs() + [copy.deepcopy(runs()[0])]
        self.assertFalse(bar.setting_verdict(rows, rung=1, scenarios=SCENARIOS)["clears"])
        rows = runs() + [record(scenario="surprise")]
        self.assertFalse(bar.setting_verdict(rows, rung=1, scenarios=SCENARIOS)["clears"])

    def test_the_first_pass_rate_is_ninety_percent_inclusive_and_a_retry_that_rescues_is_counted_not_hidden(self):
        rows = runs(scenarios=SCENARIOS + ["s4", "s5"])              # 5 scenarios x 6 = 30 cells
        scenarios = SCENARIOS + ["s4", "s5"]
        for row in rows[:3]:                                         # 3 of 30 retried = exactly 90%
            row["narrative_source"] = "model_retry"
        at_bar = bar.setting_verdict(rows, rung=1, scenarios=scenarios)
        self.assertEqual((at_bar["first_pass_rate"], at_bar["retried"], at_bar["clears"]), (0.9, 3, True))
        rows[3]["narrative_source"] = "model_retry"                  # 4 of 30 = 86.7%: every run passes T1-T4 but the rate fails
        below = bar.setting_verdict(rows, rung=1, scenarios=scenarios)
        self.assertEqual(below["failures"], {"T1": 0, "T2": 0, "T3": 0, "T4": 0})
        self.assertFalse(below["clears"])
        self.assertTrue(any("first-pass rate" in r for r in below["reasons"]))

    def test_rung_zero_is_scored_on_one_cell_per_scenario_by_the_same_bar(self):
        make = lambda **kw: record(design="code", narrative_source="code", attempts=0, paragraphs=[paragraph(source="code")], **kw)
        rows = runs(rung=0, make=make)
        self.assertEqual(len(rows), 3)
        self.assertTrue(bar.setting_verdict(rows, rung=0, scenarios=SCENARIOS)["clears"])
        rows[1]["paragraphs"] = [paragraph(source="code", over_limit=True)]
        self.assertFalse(bar.setting_verdict(rows, rung=0, scenarios=SCENARIOS)["clears"])

    def test_the_lowest_passing_rung_is_the_first_that_clears_and_none_when_none_does(self):
        yes, no = {"clears": True}, {"clears": False}
        self.assertEqual(bar.lowest_passing_rung({0: no, 1: yes, 2: yes}), 1)
        self.assertEqual(bar.lowest_passing_rung({0: yes, 1: yes}), 0)
        self.assertEqual(bar.lowest_passing_rung({2: yes, 0: no, 1: no}), 2)
        self.assertIsNone(bar.lowest_passing_rung({0: no, 1: no, 2: no}))
        self.assertIsNone(bar.lowest_passing_rung({}))


class SampleTests(unittest.TestCase):
    ROLES = ["hmda", "ecoa", "hvcre", "hpml", "trid", "fzd", "ybs", "vmi", "auditor"]

    def paragraphs(self, per_role=6):
        return [{"role": role, "scenario": f"s{n % 3}", "tool_mode": "model", "rep": n // 3, "rule_id": f"{role.upper()}-R{n}"}
                for role in self.ROLES for n in range(per_role)]

    def test_twelve_paragraphs_four_from_hmda_and_one_from_each_other_role(self):
        out = bar.t5_sample(self.paragraphs(), self.ROLES)
        self.assertEqual((out["total"], out["short"]), (bar.T5_TOTAL, {}))
        counts = {r: sum(1 for p in out["sample"] if p["role"] == r) for r in self.ROLES}
        self.assertEqual(counts, {"hmda": 4, **{r: 1 for r in self.ROLES[1:]}})
        self.assertEqual(len({(p["role"], p["rule_id"]) for p in out["sample"]}), 12)

    def test_the_choice_is_deterministic_seeded_and_independent_of_input_order(self):
        rows = self.paragraphs()
        first = bar.t5_sample(rows, self.ROLES)
        self.assertEqual(first, bar.t5_sample(list(reversed(rows)), self.ROLES))
        self.assertNotEqual([p["rule_id"] for p in first["sample"]], [p["rule_id"] for p in bar.t5_sample(rows, self.ROLES, seed="another")["sample"]])

    def test_hmda_paragraphs_come_from_different_scenarios_and_rules_when_available(self):
        out = bar.t5_sample(self.paragraphs(), self.ROLES)
        hmda = [p for p in out["sample"] if p["role"] == "hmda"]
        self.assertEqual(len({p["rule_id"] for p in hmda}), 4)
        self.assertGreaterEqual(len({p["scenario"] for p in hmda}), 3)

    def test_a_role_with_too_few_paragraphs_is_reported_short_not_padded(self):
        rows = [p for p in self.paragraphs() if not (p["role"] == "vmi")] + self.paragraphs()[:0]
        out = bar.t5_sample(rows, self.ROLES)
        self.assertEqual((out["total"], out["short"]), (11, {"vmi": 1}))
        few = [p for p in self.paragraphs() if p["role"] != "hmda"] + [p for p in self.paragraphs() if p["role"] == "hmda"][:2]
        self.assertEqual(bar.t5_sample(few, self.ROLES)["short"], {"hmda": 2})


# --- the sweep (benchmarks/floor_sweep.py), offline with fake backends -----------------------------------------------------------
class SweepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenarios = sweep.build_scenarios()

    def small(self, backends=None, roles=("ybs", "hvcre", "narrative"), **kw):
        backends = backends or sweep.DryBackends()
        kw.setdefault("rung1", "all")          # most tests exercise rung 1; the default (needed) has its own test
        return backends, sweep.sweep(self.scenarios, backends, width=kw.pop("width", 4), roles=list(roles), **kw)

    def test_scenarios_are_chosen_by_script_deterministically_and_listed(self):
        again = sweep.build_scenarios()
        self.assertEqual(list(again), list(self.scenarios))
        self.assertTrue(all(again[k].loan == self.scenarios[k].loan for k in again))
        self.assertEqual(self.scenarios["sample"].loan, sweep.SAMPLE)
        for domain in sweep.DOMAINS:
            for kind in ("fail", "gap"):
                if f"{kind}:{domain}" in self.scenarios:
                    scenario = self.scenarios[f"{kind}:{domain}"]
                    self.assertNotEqual(scenario.loan[f"{domain}_case"], sweep.SAMPLE[f"{domain}_case"])
                    others = {k: v for k, v in scenario.loan.items() if k != f"{domain}_case"}
                    self.assertEqual(others, {k: v for k, v in sweep.SAMPLE.items() if k != f"{domain}_case"})      # only the regime's own case changes
        self.assertEqual(sweep.role_scenarios("auditor", self.scenarios), ["sample", "fail:all", "gap:all"])
        self.assertEqual(sweep.role_scenarios("narrative", self.scenarios), ["sample", "fail:all", "gap:all"])
        self.assertEqual(sweep.role_scenarios("ybs", self.scenarios)[0], "sample")
        text = sweep.scenarios_markdown(self.scenarios)
        for scenario_id in self.scenarios:
            self.assertIn(f"`{scenario_id}`", text)
        self.assertTrue(text.startswith("---\ngist: \"Read when:"))

    def test_a_failing_case_has_a_not_satisfied_finding_and_a_gap_case_only_unable_to_determine(self):
        for scenario in self.scenarios.values():
            if scenario.kind in ("fail", "gap") and scenario.regime in sweep.DOMAINS:
                decision = sweep.fixtures.evaluate(scenario.regime, scenario.loan[f"{scenario.regime}_case"])
                outcomes = {r["outcome"] for r in decision["rule_results"]}
                if scenario.kind == "fail":
                    self.assertIn("not_satisfied", outcomes, scenario.id)
                else:
                    self.assertIn("unable_to_determine", outcomes, scenario.id)
                    self.assertNotIn("not_satisfied", outcomes, scenario.id)

    def test_rung_zero_asks_no_model_and_scores_every_role_by_the_same_bar(self):
        backends, result = self.small(roles=("ybs", "narrative"))
        self.assertNotIn(0, {rung for rung, _ in backends.asked})
        for role in ("ybs", "narrative"):
            verdict = result["ladder"][role]["tried"][0]
            self.assertEqual((verdict["clears"], verdict["runs"], verdict["expected"]), (True, 3 if role == "narrative" else 2, 3 if role == "narrative" else 2))
        zero = [r for r in result["records"] if r["rung"] == 0 and r["role"] == "ybs"]
        self.assertTrue(all(r["design"] == "code" and r["narrative_source"] == "code" and r["tool_mode"] is None for r in zero))

    def test_rung_one_runs_the_whole_grid_in_both_tool_modes_and_three_repetitions(self):
        _, result = self.small(roles=("ybs",))
        runs = [r for r in result["records"] if r["rung"] == 1]
        self.assertEqual(len(runs), len(sweep.role_scenarios("ybs", self.scenarios)) * 2 * 3)
        self.assertEqual({r["tool_mode"] for r in runs}, {"model", "seeded"})
        self.assertEqual({r["rep"] for r in runs}, {0, 1, 2})
        self.assertTrue(result["ladder"]["ybs"]["tried"][1]["clears"])
        self.assertTrue(all(r["narrative_source"] == "model" and r["decision_id"] == r["direct_decision_id"] for r in runs))

    def test_a_role_that_clears_rung_zero_skips_rung_two_and_says_why(self):
        _, result = self.small(roles=("ybs",))
        ladder = result["ladder"]["ybs"]
        self.assertEqual(ladder["lowest_passing_rung"], 0)
        self.assertEqual(sorted(ladder["tried"]), [0, 1])
        self.assertEqual(ladder["skipped"], {2: "not run: rung 0 cleared the bar"})

    def test_by_default_rung_one_runs_only_where_rung_zero_failed_jims_decision(self):
        import inspect
        self.assertEqual(inspect.signature(sweep.sweep).parameters["rung1"].default, "needed")
        backends = sweep.DryBackends()
        result = sweep.sweep(self.scenarios, backends, width=2, roles=["ybs"])
        self.assertEqual(backends.asked, [])
        self.assertEqual(result["ladder"]["ybs"]["lowest_passing_rung"], 0)
        with self.failing_code("ybs"):
            backends = sweep.DryBackends()
            sweep.sweep(self.scenarios, backends, width=2, roles=["ybs"])
        self.assertEqual({rung for rung, _ in backends.asked}, {1})

    def test_rung_one_can_be_limited_to_roles_where_rung_zero_failed_and_the_skip_is_recorded(self):
        backends, result = self.small(roles=("ybs", "hvcre"), rung1="needed")
        self.assertEqual({r for rung, r in backends.asked if rung == 1}, set())
        self.assertEqual(result["ladder"]["ybs"]["skipped"][1], "not run: rung 0 cleared the bar")
        self.assertEqual(sorted(result["ladder"]["ybs"]["tried"]), [0])

    def failing_code(self, role):
        real = sweep.code_record

        def wrapped(r, scenario, inputs):
            record, texts = real(r, scenario, inputs)
            if r == role:
                record["paragraphs"] = [{**p, "words": 999} for p in record["paragraphs"]] or [{"rule_id": "X", "source": "code", "words": 999, "problems": []}]
            return record, texts
        return mock.patch.object(sweep, "code_record", wrapped)

    def test_a_role_that_fails_rung_zero_climbs_to_haiku_and_stops_there_when_it_passes(self):
        with self.failing_code("ybs"):
            backends, result = self.small(roles=("ybs",))
        ladder = result["ladder"]["ybs"]
        self.assertFalse(ladder["tried"][0]["clears"])
        self.assertTrue(ladder["tried"][1]["clears"])
        self.assertEqual((ladder["lowest_passing_rung"], sorted(ladder["tried"]), ladder["skipped"]), (1, [0, 1], {2: "not run: rung 1 cleared the bar"}))
        self.assertNotIn(2, {rung for rung, _ in backends.asked})

    def test_a_role_that_fails_rungs_zero_and_one_is_the_only_one_sent_to_sonnet(self):
        with self.failing_code("ybs"):
            backends, result = self.small(sweep.DryBackends(weak={"ybs"}), roles=("ybs", "hvcre"))
        self.assertEqual(result["ladder"]["ybs"]["lowest_passing_rung"], 2)
        self.assertFalse(result["ladder"]["ybs"]["tried"][1]["clears"])
        self.assertGreater(result["ladder"]["ybs"]["tried"][1]["failures"]["T1"], 0)
        self.assertEqual({role for rung, role in backends.asked if rung == 2}, {"ybs"})
        self.assertEqual(result["ladder"]["hvcre"]["lowest_passing_rung"], 0)

    def test_a_role_that_clears_no_rung_is_a_finding_not_a_pass(self):
        with self.failing_code("ybs"):
            _, result = self.small(sweep.DryBackends(weak={"ybs"}, weak_rungs={1, 2}), roles=("ybs",))
        ladder = result["ladder"]["ybs"]
        self.assertIsNone(ladder["lowest_passing_rung"])
        self.assertEqual(sorted(ladder["tried"]), [0, 1, 2])
        self.assertIn("none", [row[1] for row in sweep.table_rows(result)])

    def test_a_truncated_reply_fails_t2_at_that_rung(self):
        _, result = self.small(sweep.DryBackends(truncating={"ybs"}), roles=("ybs",))
        verdict = result["ladder"]["ybs"]["tried"][1]
        self.assertFalse(verdict["clears"])
        self.assertEqual(verdict["failures"]["T2"], verdict["runs"])
        self.assertEqual(result["ladder"]["ybs"]["lowest_passing_rung"], 0)

    def test_the_run_width_is_respected_and_runs_really_overlap(self):
        lock, state = threading.Lock(), {"now": 0, "peak": 0}

        def hold():
            with lock:
                state["now"] += 1
                state["peak"] = max(state["peak"], state["now"])
            time.sleep(0.01)
            with lock:
                state["now"] -= 1
        for width in (1, 3):
            state.update(now=0, peak=0)
            self.small(sweep.DryBackends(hold=hold), roles=("hvcre",), width=width)
            self.assertEqual(state["peak"], width)

    def test_the_default_width_is_the_committed_remote_width(self):
        from orchestrator.config import load_settings
        with mock.patch.object(sweep, "sweep", return_value={"ladder": {}, "records": [], "texts": {}, "scenarios": []}) as swept, \
                mock.patch.object(sweep, "build_scenarios", return_value={}):
            self.assertEqual(sweep.main(["--dry-run"]), 0)
        self.assertEqual(swept.call_args.kwargs["width"], load_settings()["remote_concurrency"])

    def test_the_run_file_is_metadata_only_and_lists_every_rung_tried_per_role(self):
        _, result = self.small(sweep.DryBackends(weak={"ybs"}), roles=("ybs", "narrative"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runs.jsonl"
            sweep.write_run_file(path, result, {"mode": "dry-run"})
            text = path.read_text(encoding="utf-8")
        rows = [json.loads(line) for line in text.splitlines()]
        self.assertEqual({r["event"] for r in rows}, {"sweep_start", "run", "verdict", "ladder"})
        ladders = {r["role"]: r for r in rows if r["event"] == "ladder"}
        self.assertEqual(ladders["ybs"]["rungs_tried"], [0, 1])
        self.assertIn("2", ladders["ybs"]["skipped"])
        self.assertNotIn("987654321", text)                                   # the weak model's invented figure never reaches the file
        for row in rows:
            self.assertFalse({"text", "raw_text", "payload", "narrative"} & set(row), row.get("event"))
        self.assertTrue(all(len(str(v)) < 200 for r in rows for v in r.values() if isinstance(v, str)))

    def test_the_table_has_the_report_layout_one_row_per_role_and_a_cell_for_every_rung(self):
        _, result = self.small(roles=("ybs", "narrative"))
        rows = sweep.table_rows(result)
        table = sweep.render_table(rows)
        header = table.splitlines()[0]
        for column in sweep.TABLE_COLUMNS:
            self.assertIn(column, header)
        self.assertEqual(len(table.splitlines()), 2 + 2)
        self.assertEqual(rows[0][:3], ["ybs", "0 (code only)", "pass"])
        self.assertEqual({len(r) for r in rows}, {len(sweep.TABLE_COLUMNS)})

    def test_the_t5_candidates_come_from_each_roles_lowest_passing_rung_and_carry_no_text(self):
        _, result = self.small(roles=("ybs", "hvcre"))
        candidates = sweep.t5_candidates(result)
        self.assertTrue(candidates)
        self.assertEqual({"role", "scenario", "tool_mode", "rep", "rule_id", "source"}, set(candidates[0]))
        self.assertTrue(all(c["source"] == "code" for c in candidates))        # both roles cleared rung 0, so the paragraphs are code's

    def test_live_mode_supports_only_anthropic_and_a_bare_call_asks_for_a_mode(self):
        self.assertEqual(sweep.main(["--live", "--provider", "openai"]), 2)
        self.assertEqual(sweep.main(["--live"]), 2)
        with self.assertRaises(SystemExit):
            sweep.main([])

    def test_live_mode_stops_with_exit_3_before_any_live_request_when_a_role_fails_rung_zero(self):
        with self.failing_code("ybs"), mock.patch.object(sweep, "diagnose") as diagnose, mock.patch.object(sweep, "build_scenarios", return_value=self.scenarios), \
                mock.patch.object(sweep, "ROLES", ["ybs"]):
            self.assertEqual(sweep.live("anthropic", Path(tempfile.gettempdir()) / "never-written.jsonl"), 3)
        diagnose.assert_not_called()


# --- the one-request live diagnostics (offline here, over a scripted provider) -----------------------------------------------------
class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        from scripts import anthropic_cost_estimator as estimator
        self.estimator, self.temp = estimator, tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = Path(self.temp.name) / "ledger.jsonl"
        self.ledger.write_text(json.dumps({"event": "baseline_unknown", "version": 1}) + "\n")
        estimator.baseline(self.ledger, "0", "owner-confirmed")
        self.runs = Path(self.temp.name) / "runs.jsonl"

    def sdk(self, script):
        import anthropic
        import httpx
        return anthropic.Anthropic(api_key="sk-ant-OFFLINE", max_retries=0, timeout=5.0, http_client=httpx.Client(transport=httpx.MockTransport(script.handler)))

    def run_one(self, model, script):
        script.caps = False
        script.begin_role(sweep.DIAGNOSTIC_ROLE, "model")          # the fake builds its plain answer for the role it is told about
        return sweep.diagnose(self.sdk(script), model, ledger=self.ledger, runs_path=self.runs, today=self.estimator.PRICE_CHECKED)

    def ledger_rows(self):
        return [json.loads(line) for line in self.ledger.read_text().splitlines()]

    def test_each_candidate_gets_exactly_one_request_inside_its_own_reservation_and_is_settled_from_usage(self):
        from live_parity_common import ScriptedProvider
        for model, choice in (("claude-haiku-5-5", "tool"), ("claude-sonnet-5-5", "auto")):
            with self.subTest(model=model):
                script = ScriptedProvider(model=model)
                out = self.run_one(model, script)
                self.assertEqual(len(script.requests), 1)
                self.assertEqual((out["outcome"], out["tool_choice_sent"], out["requests"]), ("tool_called", choice, 1))
                self.assertFalse(out["reservation_retained"])
                self.assertEqual(script.rejected, [])
        events = [r["event"] for r in self.ledger_rows()]
        self.assertEqual((events.count("reservation"), events.count("settlement")), (2, 2))
        rows = [json.loads(line) for line in self.runs.read_text().splitlines()]
        self.assertEqual([r["event"] for r in rows if r["event"] == "diagnostic"], ["diagnostic", "diagnostic"])
        self.assertNotIn("987654321", self.runs.read_text())
        self.assertTrue(all("text" not in r and "messages" not in r for r in rows))

    def test_sonnet_that_ignores_the_instruction_is_a_recorded_outcome_not_an_error(self):
        from live_parity_common import ScriptedProvider
        out = self.run_one("claude-sonnet-5-5", ScriptedProvider(model="claude-sonnet-5-5", tool="none"))
        self.assertEqual(out["outcome"], "no_tool_call")
        self.assertFalse(out["reservation_retained"])

    def test_a_400_is_recorded_with_its_type_and_the_whole_reservation_is_retained(self):
        import httpx
        from live_parity_common import ScriptedProvider

        class Rejecting(ScriptedProvider):
            def handler(self, request):
                return httpx.Response(400, json={"type": "error", "error": {"type": "invalid_request_error", "message": "synthetic"}})
        out = self.run_one("claude-haiku-5-5", Rejecting(model="claude-haiku-5-5"))
        self.assertEqual(out["outcome"], "error")
        self.assertTrue(out["reservation_retained"])
        self.assertEqual([r["event"] for r in self.ledger_rows()].count("settlement"), 0)

    def test_a_model_outside_the_allow_list_is_refused_before_any_reservation(self):
        from live_parity_common import ScriptedProvider
        from test_anthropic_live_parity import GuardRefusal
        with self.assertRaises(GuardRefusal):
            self.run_one("claude-opus-5-5", ScriptedProvider())
        self.assertEqual(len(self.ledger_rows()), 2)


# --- live backends (reservation per batch), offline over a scripted provider -----------------------------------------------------
class LiveBackendTests(unittest.TestCase):
    def setUp(self):
        from scripts import anthropic_cost_estimator as estimator
        self.estimator, self.temp = estimator, tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = Path(self.temp.name) / "ledger.jsonl"
        self.ledger.write_text(json.dumps({"event": "baseline_unknown", "version": 1}) + "\n")
        estimator.baseline(self.ledger, "0", "owner-confirmed")
        self.runs = Path(self.temp.name) / "runs.jsonl"

    def make(self, script, **kw):
        import anthropic
        import httpx
        script.caps = False
        sdk = anthropic.Anthropic(api_key="sk-ant-OFFLINE", max_retries=0, timeout=5.0, http_client=httpx.Client(transport=httpx.MockTransport(script.handler)))
        return sweep.LiveBackends(sdk, ledger=self.ledger, runs_path=self.runs, today=self.estimator.PRICE_CHECKED, observer=script.begin_role, **kw)

    def events(self):
        return [json.loads(line)["event"] for line in self.ledger.read_text().splitlines()]

    def test_each_role_and_mode_batch_is_reserved_before_its_cells_and_settled_from_usage(self):
        from live_parity_common import ScriptedProvider
        script = ScriptedProvider(model="claude-haiku-5-5")
        backends = self.make(script, templates="code")
        scenarios = sweep.build_scenarios()
        result = sweep.sweep(scenarios, backends, width=4, rung1="all", roles=["ybs", "narrative"], templates="code", max_rung=1)
        self.assertEqual(self.events().count("reservation"), self.events().count("settlement"))
        self.assertEqual(self.events().count("reservation"), 4)               # ybs model, ybs seeded, narrative model, narrative seeded
        self.assertTrue(result["ladder"]["ybs"]["tried"][1]["clears"], result["ladder"]["ybs"]["tried"][1])
        self.assertTrue(result["ladder"]["narrative"]["tried"][1]["clears"])
        runs = [r for r in result["records"] if r["rung"] == 1 and r["role"] == "ybs"]
        self.assertTrue(all(r["templates"] == "code" and r["narrative_source"] == "model" for r in runs))
        self.assertEqual({tuple(r["tool_by"]) for r in runs}, {("model",), ("seeded",)})
        rows = [json.loads(line) for line in self.runs.read_text().splitlines()]
        self.assertEqual(sum(1 for r in rows if r["event"] == "batch_reservation"), 4)
        self.assertEqual(sum(1 for r in rows if r["event"] == "request_start"), len(script.requests))
        usage = backends.usage_table(result)
        self.assertGreater(Decimal(usage[("ybs", 1)]["cost_per_successful_narrative_usd"]), 0)
        self.assertEqual(Decimal(backends.spent), sum((Decimal(json.loads(line)["cost_usd"]) for line in self.ledger.read_text().splitlines() if '"settlement"' in line), Decimal(0)))

    def test_a_cell_that_stops_at_max_tokens_fails_t2_for_that_cell_only(self):
        from live_parity_common import ScriptedProvider

        class Cut(ScriptedProvider):
            def _text(self, anthropic, text):
                body = super()._text(anthropic, text)
                if anthropic and self.rep_seen % 3 == 0:
                    body["stop_reason"] = "max_tokens"
                self.rep_seen += 1
                return body
        script = Cut(model="claude-haiku-5-5")
        script.rep_seen = 0
        backends = self.make(script, templates="code")
        result = sweep.sweep(sweep.build_scenarios(), backends, width=1, rung1="all", roles=["narrative"], templates="code", max_rung=1)
        verdict = result["ladder"]["narrative"]["tried"][1]
        truncated = sum(1 for r in result["records"] if r["rung"] == 1 and r["stopped_at_max_tokens"])
        self.assertGreater(truncated, 0)
        self.assertLess(truncated, verdict["runs"])                             # not every cell: the flag is per cell
        self.assertEqual(verdict["failures"]["T2"], truncated)

    def test_a_batch_whose_worst_case_is_over_the_ceiling_is_refused_before_it_is_reserved(self):
        from live_parity_common import ScriptedProvider
        backends = self.make(ScriptedProvider(model="claude-sonnet-5-5"))
        with self.assertRaises(sweep.BudgetStop):
            backends.open_batch(2, "hmda", "model", 9)                          # Sonnet: 36 attempts of the full bound is far over USD 1.50
        self.assertEqual(self.events(), ["baseline_unknown", "baseline_verified"])

    def test_unknown_usage_stops_the_sweep_and_keeps_the_reservation(self):
        import httpx
        from live_parity_common import ScriptedProvider

        class Failing(ScriptedProvider):
            def handler(self, request):
                raise httpx.ConnectError("synthetic")
        backends = self.make(Failing(model="claude-haiku-5-5"), templates="code")
        with self.assertRaises(sweep.BudgetStop):
            sweep.sweep(sweep.build_scenarios(), backends, width=2, rung1="all", roles=["narrative"], templates="code", max_rung=1)
        self.assertEqual(self.events().count("settlement"), 0)
        self.assertEqual(self.events().count("reservation"), 1)


class ConstantsTests(unittest.TestCase):
    """The bar reads its limits from the response-templates modules; these tests keep the one constant it holds honest."""

    def test_limits_are_the_response_templates_limits_not_copies(self):
        self.assertIs(bar.PARAGRAPH_LIMITS, examiner.LIMITS)
        self.assertEqual(bar.PARAGRAPH_FLOOR, examiner.FLOOR)
        self.assertEqual(set(bar.PARAGRAPH_LIMITS), {"ybs", "vmi", "hpml", "fzd", "hvcre", "ecoa", "trid", "auditor", "hmda"})

    def test_every_sheet_the_real_renderer_writes_for_the_fixture_records_is_inside_the_item_limits(self):
        sys.path.insert(0, str(ROOT / "tests"))
        import response_fixtures
        from compliance_common.templates import loan_officer
        checked = 0
        for domain, items in response_fixtures.records().items():
            for label, decision in items[:40]:
                sheet = loan_officer.render(decision)
                for kind, key in (("customer", "needed_from_customer"), ("refer", "refer_to_compliance")):
                    for item in sheet[key]:
                        parts = bar.sentences(item["text"])
                        entry = {"kind": kind, "sentences": len(parts), "max_sentence_words": max(len(p.split()) for p in parts)}
                        self.assertTrue(bar._item_ok(entry), (domain, label, item["text"]))
                        checked += 1
        self.assertGreater(checked, 200)

    def test_the_bar_file_has_no_io_or_model_dependency(self):
        source = (ROOT / "benchmarks/floor_bar.py").read_text(encoding="utf-8")
        for word in ("open(", "requests", "anthropic", "openai", "subprocess", "socket"):
            self.assertNotIn(word, source.replace("opening", ""), word)


if __name__ == "__main__":
    unittest.main()
