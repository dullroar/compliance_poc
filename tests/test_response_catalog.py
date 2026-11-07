"""R1 and R2: the template catalog covers every rule id and missing fact the evaluators can emit, and never changes a decision.

Coverage is proven, not read: ids come from the evaluator source (literals plus the run-time families built from the packs) and
from the records the real evaluators produce on the fixtures (response_fixtures.py), and every one must resolve to a specific entry.
"""
import re
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import response_fixtures as rf  # noqa: E402
from compliance_common.templates import catalog  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SENTENCE = re.compile(r"(?<=[.!?])\s+")


def sentences(text: str) -> list[str]:
    return [s for s in SENTENCE.split(text.strip()) if s]


# Named in a table but never emitted by any evaluator: auditor EXPLAINS lists "HMDA-LAR-FIELDS", while the evaluator emits HMDA-LAR-01..38.
NEVER_EMITTED = {"HMDA-LAR-FIELDS"}


def fixture_fields() -> set[tuple[str, str]]:
    return {(domain, m["field"]) for domain, found in rf.records().items() for _, d in found for m in d.get("missing_facts", [])}



class CoverageTests(unittest.TestCase):
    def test_every_rule_id_in_the_evaluator_source_has_a_specific_entry(self):
        ids = rf.static_rule_ids()
        self.assertGreater(len(ids), 120)
        uncovered = sorted(i for i in ids - NEVER_EMITTED if catalog.resolve_rule(i).generic)
        self.assertEqual(uncovered, [], "rule ids that fall through to the generic entry")
        emitted = {r["rule_id"] for found in rf.records().values() for _, d in found for r in d["rule_results"]}
        self.assertEqual(emitted & NEVER_EMITTED, set(), "an id listed as never emitted was emitted")

    def test_every_rule_id_the_evaluators_emit_on_the_fixtures_has_a_specific_entry(self):
        emitted = {r["rule_id"] for found in rf.records().values() for _, d in found for r in d["rule_results"]}
        self.assertGreater(len(emitted), 80)
        self.assertEqual(sorted(i for i in emitted if catalog.resolve_rule(i).generic), [])

    def test_every_missing_fact_field_seen_on_the_fixtures_has_a_specific_entry(self):
        seen = fixture_fields()
        self.assertGreater(len(seen), 60)
        self.assertEqual(sorted(f"{d}:{f}" for d, f in seen if catalog.resolve_field(d, f).generic), [])

    def test_every_missing_fact_field_in_the_evaluator_source_has_a_specific_entry(self):
        fields = rf.static_fields()
        self.assertGreater(sum(len(v) for v in fields.values()), 90)
        uncovered = sorted(f"{d}:{n}" for d, names in fields.items() for n in names if catalog.resolve_field(d, n).generic)
        self.assertEqual(uncovered, [])

    def test_a_made_up_id_gets_the_generic_entry_and_is_reported_as_uncovered(self):
        for made_up in ("HMDA-MADE-UP", "NOPE-1", "VMI"):
            with self.subTest(rule_id=made_up):
                self.assertTrue(catalog.resolve_rule(made_up).generic)
        self.assertTrue(catalog.resolve_field("hmda", "lar.made_up").generic)
        self.assertEqual(catalog.resolve_field("hmda", "lar.made_up").route, "refer", "an unknown field is never sent to the customer")
        self.assertFalse(catalog.resolve_rule("HMDA-LAR-10").generic)

    def test_the_issue_examples_resolve_to_one_entry_each(self):
        for rule_id, match in (("HMDA-LAR-10", "HMDA-LAR-10"), ("VMI-REQUEST-RACE", "VMI-REQUEST-*"), ("YBS-ENTITY-SMALL-TRUST", "YBS-ENTITY-*-TRUST"),
                               ("TRID-CD-REVISED-3DAY", "TRID-CD-REVISED-3DAY")):
            with self.subTest(rule_id=rule_id):
                self.assertEqual(catalog.resolve_rule(rule_id).match, match)

    def test_the_family_captures_name_the_item_in_the_text(self):
        entry = catalog.resolve_rule("VMI-REQUEST-MARITAL-STATUS")
        self.assertIn("marital status", entry.text(entry.requirement))
        entry = catalog.resolve_rule("YBS-ENTITY-BEGINNING-TRUST")
        self.assertIn("beginning", entry.text(entry.requirement))


class CatalogIntegrityTests(unittest.TestCase):
    def entries(self):
        for domain in catalog.DOMAINS:
            data = yaml.safe_load((catalog.CATALOG_DIR / f"{domain}.yaml").read_text(encoding="utf-8"))
            yield domain, data["rules"], data["fields"]

    def test_every_rule_entry_matches_a_known_rule_id_and_every_field_names_a_real_rule_entry(self):
        ids = rf.static_rule_ids()
        for domain, rules, fields in self.entries():
            matches = {r["match"] for r in rules}
            self.assertEqual(len(matches), len(rules), f"{domain}: duplicate rule entries")
            self.assertEqual(len({f["match"] for f in fields}), len(fields), f"{domain}: duplicate field entries")
            for entry in rules:
                with self.subTest(domain=domain, rule=entry["match"]):
                    hits = [i for i in ids if catalog.domain_of(i) == domain and catalog._regex(entry["match"]).match(i)]
                    self.assertTrue(hits, "an entry that no rule id uses")
            for entry in fields:
                with self.subTest(domain=domain, field=entry["match"]):
                    if "*" in entry["rule"]:               # a family: every id it covers must have a specific entry
                        family = [i for i in ids - NEVER_EMITTED if catalog.domain_of(i) == domain and catalog._regex(entry["rule"]).match(i)]
                        self.assertTrue(family)
                        self.assertEqual([i for i in family if catalog.resolve_rule(i).generic], [])
                    else:
                        self.assertIn(entry["rule"], matches, "a field entry must name the rule entry it belongs to")

    def test_regulation_entries_cite_a_section_pinned_in_a_rule_pack_snapshot(self):
        pinned = {re.sub(r"-extract$", "", p.stem.replace("12-cfr-", "")).replace("-", ".") for p in
                  (ROOT / "compliance_mcp").glob("*/pack/sources/12-cfr-*")}
        self.assertIn("1026.19", pinned)
        self.assertIn("614.4940", pinned)
        for domain, rules, _ in self.entries():
            for entry in rules:
                with self.subTest(domain=domain, rule=entry["match"]):
                    sections = set(re.findall(r"\b(\d{3,4}\.\d+)", entry["cite"]))
                    if entry["basis"] == "regulation":
                        self.assertTrue(sections, "a regulation entry must cite a section")
                        self.assertLessEqual(sections, pinned, "cites a section that has no pinned snapshot")

    def test_one_entry_per_family_does_not_hide_a_kind_mismatch(self):
        # A finding the customer cannot fix must not be routed to the customer. Kind P (institution record) and R (reviewer) never route to a customer.
        for domain, rules, fields in self.entries():
            kind = {r["match"]: r["kind"] for r in rules}
            for entry in fields:
                with self.subTest(domain=domain, field=entry["match"]):
                    if entry["route"] == "customer":
                        self.assertIn(kind[entry["rule"]], ("G", "V"), "a customer request must come from an information gap or a value rule")
                        self.assertNotEqual(domain, "ecoa", "ECOA facts record what the institution did; they are never customer requests")

    def test_sheet_text_is_short_and_plain(self):
        for domain, rules, fields in self.entries():
            for entry in fields:
                for kind, text in (("why", entry["why"]), ("label", entry["label"])):
                    with self.subTest(domain=domain, field=entry["match"], part=kind):
                        resolved = catalog.FieldEntry(domain, entry["match"], entry["rule"], entry["route"], entry["label"], entry["why"], captures=("x",)).text(text)
                        parts = sentences(resolved)
                        self.assertLessEqual(len(parts), 2 if kind == "why" else 1)
                        for sentence in parts:
                            self.assertLessEqual(len(sentence.split()), 20 if kind == "why" else 8, sentence)
                        self.assertNotRegex(resolved, r"lar_context\.|\b\w+\.\w+\.\w+")
            for entry in rules:
                with self.subTest(domain=domain, rule=entry["match"], part="refer"):
                    parts = sentences(entry["refer"])
                    self.assertEqual(len(parts), 1)
                    self.assertLessEqual(len(parts[0].split()), 20, parts[0])

    def test_marital_status_is_never_a_request_in_the_ecoa_catalog(self):
        entry = catalog.resolve_field("ecoa", "marital_status_inquiry")
        self.assertEqual(entry.route, "refer")
        self.assertNotRegex(entry.why.lower(), r"obtain marital|ask the customer for marital")
        for domain, _, fields in self.entries():
            for f in fields:
                if domain != "vmi" and "marital" in f["why"].lower():
                    self.assertEqual(f["route"], "refer")

    def test_vmi_items_and_hmda_item_10_say_the_applicant_may_decline(self):
        for domain, name in (("vmi", "monitoring.items.race"), ("hmda", "lar.applicant"), ("hmda", "lar.co_applicant")):
            entry = catalog.resolve_field(domain, name)
            with self.subTest(field=name):
                self.assertTrue(entry.decline)
                self.assertIn("may decline", entry.why)
                self.assertIn("record the decline", entry.why)


class DecisionUnchangedTests(unittest.TestCase):
    """R2: templates live outside every rule pack and cannot change a decision."""

    def test_the_catalog_is_outside_every_pack(self):
        self.assertEqual([p for p in catalog.CATALOG_DIR.rglob("*") if "pack" in p.relative_to(ROOT).parts], [])
        for pack in (ROOT / "compliance_mcp").glob("*/pack"):
            self.assertFalse(str(catalog.CATALOG_DIR).startswith(str(pack)))

    def test_editing_the_catalog_in_memory_leaves_every_decision_id_and_pack_hash_unchanged(self):
        before = {d: [(label, rec["decision_id"], rec["rule_pack"]["file_sha256"]) for label, rec in found[:3]] for d, found in rf.records().items() if d != "auditor"}
        loaded = catalog._load()
        saved = []
        try:
            for domain in loaded:                      # rewrite every sentence in the loaded catalog
                for section in loaded[domain].values():
                    for _, entry in section:
                        saved.append((entry, dict(entry)))
                        for key in ("requirement", "action", "refer", "why", "label"):
                            if key in entry:
                                entry[key] = "EDITED " + entry[key]
            self.assertTrue(catalog.resolve_rule("HMDA-LAR-10").requirement.startswith("EDITED"))
            rf.records.cache_clear()
            after = {d: [(label, rec["decision_id"], rec["rule_pack"]["file_sha256"]) for label, rec in found[:3]] for d, found in rf.records().items() if d != "auditor"}
        finally:
            for entry, original in saved:
                entry.clear()
                entry.update(original)
            rf.records.cache_clear()
        self.assertEqual(before, after)
        self.assertFalse(catalog.resolve_rule("HMDA-LAR-10").requirement.startswith("EDITED"))


if __name__ == "__main__":
    unittest.main()
