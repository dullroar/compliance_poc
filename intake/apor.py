"""Look up the average prime offer rate (APOR) for an HPML case and record it as evidence.

Source: CFPB-hosted FFIEC HMDA Platform Rate Spread API (documented at
https://ffiec.cfpb.gov/documentation/api/rate-spread/). The API returns APR minus APOR, so a fixed
probe APR is sent (never the loan's own APR or any loan data) and APOR = probe - rateSpread.

This runs at intake, not inside the evaluator. The evaluator stays offline; it only sees the
resulting `apor` and `apor_reference`, which carry a hash of the raw API response so the number can
be traced. Nothing pins the value upstream, so re-running later may differ if the Bureau revises a table.

  python -m intake.apor loan.json                 # prints the values it would add
  python -m intake.apor loan.json --write         # fills hpml_case.apor / apor_reference in place
  python -m intake.apor loan.json --write --force # replaces existing values
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Callable

from compliance_common.obs import get_logger

ENDPOINT = "https://ffiec.cfpb.gov/public/rateSpread"
DOC_URL = "https://ffiec.cfpb.gov/documentation/api/rate-spread/"
PROBE_APR = Decimal("10.00")
EARLIEST = date(2017, 1, 2)   # earliest lock-in date the API answered when verified (2026-10-09)
AMORTIZATION = {"fixed": "FixedRate", "adjustable": "VariableRate"}
log = get_logger("intake.apor", "0.1.0")
Post = Callable[[dict[str, Any]], bytes]


class AporLookupError(RuntimeError):
    """The APOR could not be determined; the caller must not guess a value."""


def _post(payload: dict[str, Any]) -> bytes:
    request = urllib.request.Request(ENDPOINT, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read()
        detail = gzip.decompress(detail) if detail[:2] == b"\x1f\x8b" else detail
        raise AporLookupError(f"rate-spread API returned HTTP {exc.code}: {detail.decode(errors='replace')[:200]}") from exc
    except OSError as exc:
        raise AporLookupError(f"rate-spread API unreachable: {exc}") from exc
    return gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body


def lookup_apor(rate_set_date: str, amortization_type: str, term_years: int, post: Post = _post,
                now: Callable[[], datetime] = lambda: datetime.now(UTC)) -> dict[str, Any]:
    """Return {"apor": float, "apor_reference": {...}} for the week containing rate_set_date."""
    if amortization_type not in AMORTIZATION:
        raise AporLookupError(f"amortization_type must be one of {sorted(AMORTIZATION)}")
    if not isinstance(term_years, int) or not 1 <= term_years <= 50:
        raise AporLookupError("apor_term_years must be an integer from 1 to 50 (loan term for fixed, years to first adjustment for adjustable)")
    day = date.fromisoformat(rate_set_date)
    if day < EARLIEST:
        raise AporLookupError(f"the API does not answer for rate-set dates before {EARLIEST}; use the legacy tables in compliance_mcp/hpml/pack/APOR.md")
    request = {"actionTakenType": 1, "loanTerm": term_years, "amortizationType": AMORTIZATION[amortization_type],
               "apr": float(PROBE_APR), "lockInDate": rate_set_date, "reverseMortgage": 2}
    log.debug("apor request", payload=request)
    raw = post(request)
    log.trace("apor raw response", payload=raw.decode(errors="replace"))
    try:
        spread = json.loads(raw)["rateSpread"]
    except (ValueError, KeyError, TypeError) as exc:
        raise AporLookupError(f"unexpected rate-spread response: {raw[:200]!r}") from exc
    if spread == "NA":
        raise AporLookupError("rate-spread API returned NA for this request")
    apor = PROBE_APR - Decimal(str(spread))
    monday = day - timedelta(days=day.weekday())
    reference = {
        "table_date": monday.isoformat(),
        "product": f"{amortization_type} {term_years}-year" + (" (years to first adjustment)" if amortization_type == "adjustable" else ""),
        "source": f"CFPB/FFIEC HMDA Platform Rate Spread API {DOC_URL}",
        "endpoint": ENDPOINT,
        "retrieved_at": now().replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "table_date_basis": "derived: Monday of the week containing rate_set_date; the API returns no table date",
    }
    log.info("APOR %s for %s %s-year on %s", apor, amortization_type, term_years, rate_set_date)
    return {"apor": float(apor), "apor_reference": reference}


def fill_case(loan: dict[str, Any], force: bool = False, post: Post = _post) -> dict[str, Any] | None:
    """Add apor/apor_reference to loan['hpml_case'] if absent (or force). Returns what was added."""
    case = loan.get("hpml_case")
    if not isinstance(case, dict):
        raise AporLookupError("loan has no hpml_case")
    if case.get("apor") is not None and not force:
        return None
    missing = [k for k in ("rate_set_date", "amortization_type", "apor_term_years") if case.get(k) is None]
    if missing:
        raise AporLookupError(f"hpml_case is missing {missing}; they select the APOR table column")
    found = lookup_apor(case["rate_set_date"], case["amortization_type"], case["apor_term_years"], post)
    case.update(found)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record the APOR for an hpml_case as evidence")
    parser.add_argument("loan_file")
    parser.add_argument("--write", action="store_true", help="write the values into the file")
    parser.add_argument("--force", action="store_true", help="replace an existing apor")
    args = parser.parse_args(argv)
    with open(args.loan_file, encoding="utf-8") as source:
        loan = json.load(source)
    try:
        added = fill_case(loan, args.force)
    except AporLookupError as exc:
        print(f"APOR lookup failed: {exc}", file=sys.stderr)
        return 1
    if added is None:
        print("hpml_case already has an apor; use --force to replace it", file=sys.stderr)
        return 0
    print(json.dumps(added, indent=2))
    if args.write:
        with open(args.loan_file, "w", encoding="utf-8") as out:
            json.dump(loan, out, indent=2)
            out.write("\n")
        print(f"[written to {args.loan_file}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
