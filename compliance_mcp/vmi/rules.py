"""Deterministic VMI / monitoring-information evaluator (Regulation B, 12 CFR 1002.13).

Required when the application is primarily for the purchase or refinancing of a 1-4 unit dwelling that is
(or will be) the applicant's principal residence and secures the credit (1002.13(a)(1), (a)(2)). Then the
creditor must REQUEST ethnicity, race, sex, marital status (married / unmarried / separated) and age; the
applicant is asked but not required to answer, a declination must be noted on the form, and for ethnicity,
race and sex the creditor then notes them by visual observation or surname to the extent possible
(1002.13(b)); the applicant must be told why the information is requested (1002.13(c)).
Firewall controls and non-use in underwriting are institution policy here (the regulation text does not
prescribe them); they are reported with basis `institution_policy`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from compliance_common.decision import base_record, finalize, rule
from compliance_common.pack import EvaluatorValidationError, Pack, as_date, load_pack, validate_instance

EVALUATOR_VERSION = "0.1.0"
PACK_DIR = Path(__file__).resolve().parent / "pack"
ITEMS = ("ethnicity", "race", "sex", "marital_status", "age")
OBSERVED = ("ethnicity", "race", "sex")


def _pack() -> Pack:
    return load_pack("vmi", PACK_DIR, ("thresholds",))


def validate_vmi_rule_pack() -> None:
    _pack()


def validate_vmi_decision_record(record: dict[str, Any]) -> None:
    validate_instance(record, _pack().decision_schema, "VMI decision record")


def _required(case: dict[str, Any], t: dict[str, Any], missing: list) -> bool | None:
    keys = ("primarily_purchase_or_refinance", "principal_residence", "secured_by_dwelling", "dwelling_units")
    absent = [k for k in keys if case.get(k) is None]
    for k in absent:
        missing.append({"field": k, "reason": "needed to decide whether monitoring-information collection is required (1002.13(a))"})
    if any(case.get(k) is False for k in keys[:3]) or (case.get("dwelling_units") is not None and case["dwelling_units"] > t["max_dwelling_units"]):
        return False
    return None if absent else True


def _item_rules(case: dict[str, Any], rules: list, missing: list) -> None:
    items = (case.get("monitoring") or {}).get("items") or {}
    channel = case.get("application_channel")
    for name in ITEMS:
        label, item = name.replace("_", " "), items.get(name)
        rid = name.upper().replace("_", "-")
        if item is None:
            missing.append({"field": f"monitoring.items.{name}", "reason": f"needed to test that {label} was requested (1002.13(a)(1))"})
            rules.append(rule(f"VMI-REQUEST-{rid}", "unable_to_determine", "regulatory", f"No record of whether {label} was requested."))
            continue
        if item.get("requested") is False:
            rules.append(rule(f"VMI-REQUEST-{rid}", "not_satisfied", "regulatory", f"{label.capitalize()} was not requested; it must be requested as part of the application (1002.13(a)(1))."))
            continue
        if item.get("requested") is None:
            missing.append({"field": f"monitoring.items.{name}.requested", "reason": "request not recorded"})
            rules.append(rule(f"VMI-REQUEST-{rid}", "unable_to_determine", "regulatory", f"It is not recorded whether {label} was requested."))
            continue
        if item.get("provided"):
            outcome, text = "satisfied", f"{label.capitalize()} was requested and the applicant provided it."
        elif item.get("declined"):
            if item.get("declination_noted") is True:
                outcome, text = "satisfied", f"{label.capitalize()} was requested; the applicant declined and the declination is noted on the form (1002.13(b))."
            elif item.get("declination_noted") is False:
                outcome, text = "not_satisfied", f"The applicant declined to give {label} but the declination is not noted on the form (1002.13(b))."
            else:
                missing.append({"field": f"monitoring.items.{name}.declination_noted", "reason": "needed under 1002.13(b)"})
                outcome, text = "unable_to_determine", f"It is not recorded whether the declination of {label} was noted on the form."
        else:
            missing.append({"field": f"monitoring.items.{name}", "reason": "neither a provided value nor a declination is recorded"})
            outcome, text = "unable_to_determine", f"Neither an answer nor a declination is recorded for {label}."
        rules.append(rule(f"VMI-REQUEST-{rid}", outcome, "regulatory", text))
        if name == "marital_status" and item.get("provided") and item.get("terms_valid") is False:
            rules.append(rule("VMI-MARITAL-TERMS", "not_satisfied", "regulatory", "Marital status must use only married, unmarried and separated (1002.13(a)(1)(iii))."))
        if name in OBSERVED and item.get("declined"):
            noted = item.get("observation_or_surname_noted")
            if noted is True:
                rules.append(rule(f"VMI-OBSERVATION-{rid}", "satisfied", "regulatory", f"{label.capitalize()} was noted by visual observation or surname to the extent possible (1002.13(b))."))
            elif noted is False:
                rules.append(rule(f"VMI-OBSERVATION-{rid}", "not_satisfied" if channel == "face_to_face" else "review_required", "regulatory",
                                  f"{label.capitalize()} was not noted by visual observation or surname (1002.13(b)); " + ("required for a face-to-face application." if channel == "face_to_face" else "observation may not be possible for a non-face-to-face application, so a reviewer must judge it.")))
            else:
                missing.append({"field": f"monitoring.items.{name}.observation_or_surname_noted", "reason": "needed under 1002.13(b)"})
                rules.append(rule(f"VMI-OBSERVATION-{rid}", "unable_to_determine", "regulatory", f"It is not recorded whether {label} was noted by observation or surname."))


def evaluate_vmi(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a canonical VMI case without network or model calls."""
    if not isinstance(case, dict):
        raise EvaluatorValidationError("VMI input must be an object")
    pack = _pack()
    validate_instance(case, pack.input_schema, "canonical VMI input")
    t = pack.files["thresholds"]
    base = base_record("vmi", EVALUATOR_VERSION, pack, case, as_date(case["evaluation_date"], "evaluation_date"))
    facts, missing, rules = base["facts_used"], base["missing_facts"], base["rule_results"]
    ev: dict[str, Any] = {"application_channel": case.get("application_channel")}
    required = _required(case, t, missing)
    ev["collection_required"] = required
    facts.extend({"field": k, "value": case[k]} for k in ("primarily_purchase_or_refinance", "principal_residence", "secured_by_dwelling", "dwelling_units") if case.get(k) is not None)

    def done(classification: str, status: str, result: str) -> dict[str, Any]:
        base["vmi_evaluation"] = ev
        finalize(base, classification, status, result)
        validate_instance(base, pack.decision_schema, "VMI decision record")
        return base

    if required is None:
        rules.append(rule("VMI-COVERAGE", "unable_to_determine", "regulatory", "Whether collection is required cannot be decided from the facts supplied."))
        return done("Unable To Determine", "Unable To Determine", "Unable To Determine")

    items = (case.get("monitoring") or {}).get("items") or {}
    if not required:
        rules.append(rule("VMI-COVERAGE", "does_not_apply", "regulatory", "Not primarily a purchase or refinancing of a 1-4 unit principal-residence dwelling secured by that dwelling; 1002.13 does not require collection."))
        marital = items.get("marital_status") or {}
        if marital.get("requested") and case.get("individual_unsecured") and not case.get("community_property"):
            rules.append(rule("VMI-PROHIBITED", "not_satisfied", "regulatory", "Marital status was requested for individual unsecured credit outside a community property context (1002.5(d)(1))."))
            return done("VMI Collection Deficiency", "Determined", "Non-Compliant")
        if case.get("hmda_reportable"):
            rules.append(rule("VMI-PERMITTED", "applies", "regulatory", "HMDA-reportable: ethnicity, race, sex and age are collected under Regulation C (1003.4(a)(10)); collection is permitted."))
            return done("VMI Permitted", "Determined", "Compliant")
        return done("VMI Not Required", "Determined", "Not Applicable")

    rules.append(rule("VMI-COVERAGE", "applies", "regulatory", "Purchase or refinancing of a 1-4 unit principal-residence dwelling secured by that dwelling: the creditor must request monitoring information (1002.13(a)(1))."))
    if case.get("substitute_monitoring_program"):
        rules.append(rule("VMI-SUBSTITUTE", "review_required", "regulatory", "A substitute monitoring program is claimed (1002.13(d)); a reviewer must confirm that an agency required it."))
        return done("VMI Required", "Review Required", "Potential Issue")
    if not case.get("monitoring"):
        missing.append({"field": "monitoring", "reason": "no record of the monitoring-information request"})
        rules.append(rule("VMI-REQUEST", "unable_to_determine", "regulatory", "Collection is required but no record of the request was supplied."))
        return done("VMI Required", "Determined", "Potential Issue")
    _item_rules(case, rules, missing)
    disclosure = (case.get("monitoring") or {}).get("disclosure_given")
    if disclosure is None:
        missing.append({"field": "monitoring.disclosure_given", "reason": "needed under 1002.13(c)"})
    rules.append(rule("VMI-DISCLOSURE", "unable_to_determine" if disclosure is None else ("satisfied" if disclosure else "not_satisfied"), "regulatory",
                      "The applicant must be told the information is requested by the Federal Government to monitor compliance and that, if declined, the creditor must note it by observation or surname (1002.13(c))."))
    used = (case.get("data_use") or {}).get("used_in_underwriting")
    if used is None:
        missing.append({"field": "data_use.used_in_underwriting", "reason": "institution policy requires monitoring data to stay out of credit decisions"})
    rules.append(rule("VMI-USE", "unable_to_determine" if used is None else ("not_satisfied" if used else "satisfied"), "institution_policy",
                      "Monitoring information must not be used in the credit decision (institution policy; see also 1002.4 and 1002.6)."))
    fw = case.get("firewall") or {}
    fw_keys = ("underwriting_access_restricted", "decision_makers_without_access", "audit_logging")
    fw_unknown = [k for k in fw_keys if fw.get(k) is None]
    for k in fw_unknown:
        missing.append({"field": f"firewall.{k}", "reason": "firewall control not recorded"})
    rules.append(rule("VMI-FIREWALL", "not_satisfied" if any(fw.get(k) is False for k in fw_keys) else ("unable_to_determine" if fw_unknown else "satisfied"), "institution_policy",
                      "Monitoring data must be segregated from underwriting: access restricted, decision-makers without access, and access audit logging (institution policy)."))

    outcomes = {r["outcome"] for r in rules}
    if "not_satisfied" in outcomes:
        return done("VMI Collection Deficiency", "Determined", "Non-Compliant")
    if outcomes & {"unable_to_determine", "review_required"}:
        return done("Potential Issue", "Determined", "Potential Issue")
    return done("VMI Collected Properly", "Determined", "Compliant")
