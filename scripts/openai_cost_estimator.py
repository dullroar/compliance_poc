#!/usr/bin/env python3
"""Preflight the supported OpenAI smoke-test request against the shared budget.

This script does not send requests or reserve funds. Its only supported
configuration is the guarded GPT-6 Luna Responses smoke test; other uses must
first extend the estimator and durable request accounting.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_openai_live_smoke import (  # noqa: E402
    BUDGET, CONTEXT_LIMIT, LEDGER, MAX_REQUESTS, MODEL, OUTPUT_LIMIT,
    PRICE_CHECKED, PRICING_URL, REQUEST_BOUND, BudgetError, Ledger,
)


def assess(model: str, requests: int, ledger_path: Path, checked_date: str) -> dict:
    """Return a conservative preflight; fail closed when its assumptions do not hold."""
    if model != MODEL:
        raise ValueError(f"Unsupported model {model!r}; extend and validate accounting before calling it")
    if not 1 <= requests <= MAX_REQUESTS:
        raise ValueError(f"This configuration permits 1 to {MAX_REQUESTS} requests per cycle")
    if checked_date != PRICE_CHECKED:
        raise ValueError("Pricing verification is stale; verify current rates and update the accounting before calling")
    if not ledger_path.is_file():
        raise ValueError("Shared ledger is missing; reconcile the prior budget history before calling")
    with Ledger(ledger_path).locked() as (_, rows):
        if not rows:
            raise ValueError("Shared ledger is empty; reconcile the prior budget history before calling")
        allowed = {"cycle_reservation", "request_reservation", "request_outcome", "cycle_end"}
        if any(not isinstance(row, dict) or row.get("event") not in allowed for row in rows):
            raise ValueError("Shared ledger contains an unsupported event; reconcile before calling")
        _, incurred, reserved = Ledger.state(rows)
    # The guarded implementation reserves the full six-request cycle even if
    # the expected number of requests is lower.
    full_cycle = REQUEST_BOUND * MAX_REQUESTS
    remaining = BUDGET - incurred - reserved
    return {"model": MODEL, "pricing_url": PRICING_URL, "pricing_checked": PRICE_CHECKED,
            "request_count": requests, "input_bound_tokens_per_request": CONTEXT_LIMIT,
            "output_bound_tokens_per_request": OUTPUT_LIMIT,
            "expected_request_bound_usd": REQUEST_BOUND * requests,
            "required_cycle_reservation_usd": full_cycle,
            "budget_usd": BUDGET, "conservative_incurred_usd": incurred,
            "outstanding_reservations_usd": reserved, "remaining_before_cycle_usd": remaining,
            "fits": full_cycle <= remaining}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="exact model identifier")
    parser.add_argument("--requests", type=int, required=True, help="maximum expected requests, including retries")
    args = parser.parse_args()
    today = datetime.now(ZoneInfo("America/Denver")).date().isoformat()
    try:
        result = assess(args.model, args.requests, LEDGER, today)
    except (ValueError, BudgetError, OSError, KeyError, TypeError, ArithmeticError) as exc:
        print(f"Cannot establish a safe budget: {exc}", file=sys.stderr)
        return 1
    for key, value in result.items():
        print(f"{key}: {value}")
    print("Preflight only: no reservation was made and no request was sent.")
    print("Supported: standard-tier Responses, no hosted tools, at most 8192 output tokens per request.")
    if not result["fits"]:
        print("The full cycle reservation does not fit the remaining budget.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
