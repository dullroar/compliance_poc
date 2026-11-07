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
    PARITY_INPUT_BOUND_TOKENS, PARITY_MAX_REQUESTS, PARITY_REQUEST_BOUND, PRICE_CHECKED, PRICING_URL, REQUEST_BOUND,
    BudgetError, Ledger,
)

PARITY_RUN_CEILING = 5     # USD; plans/archive/live-parity R1: one conservative reservation of at most 5 per registry-wide run


def assess(model: str, requests: int, ledger_path: Path, checked_date: str, profile: str = "smoke") -> dict:
    """Return a conservative preflight; fail closed when its assumptions do not hold.

    profile "smoke" is the original guarded cycle (1 to 6 requests, each bounded at the model's context limit). Profile
    "parity" is the registry-wide live-parity cycle: up to PARITY_MAX_REQUESTS requests, each bounded at
    PARITY_INPUT_BOUND_TOKENS of input, and a cycle that reserves exactly `requests` slots."""
    if model != MODEL:
        raise ValueError(f"Unsupported model {model!r}; extend and validate accounting before calling it")
    if profile not in ("smoke", "parity"):
        raise ValueError(f"Unknown profile {profile!r}")
    limit = MAX_REQUESTS if profile == "smoke" else PARITY_MAX_REQUESTS
    if not 1 <= requests <= limit:
        raise ValueError(f"This configuration permits 1 to {limit} requests per cycle")
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
    remaining = BUDGET - incurred - reserved
    if profile == "parity":
        # The parity cycle reserves exactly the requested slots, each at the per-request bound for the input limit.
        full_cycle = PARITY_REQUEST_BOUND * requests
        return {"model": MODEL, "profile": profile, "pricing_url": PRICING_URL, "pricing_checked": PRICE_CHECKED,
                "request_count": requests, "input_bound_tokens_per_request": PARITY_INPUT_BOUND_TOKENS,
                "output_bound_tokens_per_request": OUTPUT_LIMIT,
                "expected_request_bound_usd": PARITY_REQUEST_BOUND * requests,
                "required_cycle_reservation_usd": full_cycle,
                "per_run_ceiling_usd": PARITY_RUN_CEILING,
                "budget_usd": BUDGET, "conservative_incurred_usd": incurred,
                "outstanding_reservations_usd": reserved, "remaining_before_cycle_usd": remaining,
                "fits": full_cycle <= remaining and full_cycle <= PARITY_RUN_CEILING}
    # The guarded implementation reserves the full six-request cycle even if
    # the expected number of requests is lower.
    full_cycle = REQUEST_BOUND * MAX_REQUESTS
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
    parser.add_argument("--profile", choices=("auto", "smoke", "parity"), default="auto",
                        help="smoke: the 1-6 request cycle; parity: the registry-wide cycle (up to 80 requests); "
                             "auto picks parity only above the smoke maximum")
    args = parser.parse_args()
    today = datetime.now(ZoneInfo("America/Denver")).date().isoformat()
    profile = args.profile if args.profile != "auto" else ("parity" if args.requests > MAX_REQUESTS else "smoke")
    try:
        result = assess(args.model, args.requests, LEDGER, today, profile)
    except (ValueError, BudgetError, OSError, KeyError, TypeError, ArithmeticError) as exc:
        print(f"Cannot establish a safe budget: {exc}", file=sys.stderr)
        return 1
    for key, value in result.items():
        print(f"{key}: {value}")
    print("Preflight only: no reservation was made and no request was sent.")
    print("Supported: standard-tier Responses, no hosted tools, at most 8192 output tokens per request.")
    if profile == "parity":
        print(f"Parity profile: the guarded client must refuse any request over {PARITY_INPUT_BOUND_TOKENS} UTF-8 bytes of input.")
    if not result["fits"]:
        print("The full cycle reservation does not fit the remaining budget.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
