#!/usr/bin/env python3
"""Estimate Anthropic Messages API costs and reserve a separate $20 budget.

Estimates do not make calls. The ledger starts with an unknown historical
baseline; reconcile it before reserving. The caller must enforce the stated
bounds and record known charges or leave reservations outstanding.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import fcntl
import json
import os
from pathlib import Path
import sys
import uuid
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'usage/anthropic-api-ledger.jsonl'
BUDGET = Decimal('20')
PRICE_CHECKED = '2026-11-06'
PRICE_URL = 'https://platform.claude.com/docs/en/about-claude/pricing'
# USD per million tokens, standard Messages API. Conservative cost assumes every
# input token is a 1-hour cache write and applies the 10% US geography premium.
RATES = {'claude-sonnet-5-5': ('2', '10'), 'claude-opus-5-5': ('4', '20'),
         'claude-sonnet-4-6': ('3', '15'), 'claude-haiku-5-5': ('0.10', '0.50')}
CONTEXT_LIMIT = 1_000_000
OUTPUT_LIMIT = 128_000


class BudgetError(ValueError):
    pass


def rates_for(model, input_tokens):
    """Select the highest applicable input tier using the full input bound."""
    input_rate, output_rate = map(Decimal, RATES[model])
    if model == 'claude-haiku-5-5' and input_tokens > 100_000:
        input_rate *= 5
        output_rate *= 5
    return input_rate, output_rate


def amount(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise BudgetError('Invalid monetary amount') from None
    if not result.is_finite() or result < 0:
        raise BudgetError('Amounts must be finite and non-negative')
    return result


def estimate(model, attempts, input_tokens, output_tokens, checked_date):
    if model not in RATES:
        raise BudgetError('Unsupported model; verify pricing and extend the estimator before use')
    if checked_date != PRICE_CHECKED:
        raise BudgetError('Pricing verification is stale; verify and update rates before use')
    if any(type(x) is not int for x in (attempts, input_tokens, output_tokens)):
        raise BudgetError('Attempts and token bounds must be integers')
    if attempts < 1 or not 0 <= input_tokens <= CONTEXT_LIMIT or not 1 <= output_tokens <= OUTPUT_LIMIT:
        raise BudgetError('Invalid attempt count or token bounds')
    input_rate, output_rate = rates_for(model, input_tokens)
    return (Decimal(attempts) * (Decimal(input_tokens)*input_rate*2 + Decimal(output_tokens)*output_rate)
            * Decimal('1.1') / Decimal(1_000_000))


@contextmanager
def locked(path):
    if not path.is_file():
        raise BudgetError('Ledger missing; reconcile its history before use')
    with path.open('r+', encoding='utf-8') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            rows = [json.loads(line) for line in f if line.strip()]
        except (ValueError, UnicodeError):
            raise BudgetError('Ledger is unreadable') from None
        yield f, rows


def append(f, row):
    row['timestamp'] = datetime.now(timezone.utc).isoformat()
    f.seek(0, os.SEEK_END)
    f.write(json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n')
    f.flush()
    os.fsync(f.fileno())


def state(rows):
    if not rows or not all(isinstance(row, dict) for row in rows) or rows[0].get('event') != 'baseline_unknown':
        raise BudgetError('Ledger has no initial unknown-baseline marker')
    baseline = None
    reservations = {}
    for row in rows[1:]:
        event = row.get('event')
        if event == 'baseline_verified':
            if baseline is not None or reservations:
                raise BudgetError('Invalid baseline event')
            baseline = amount(row['prior_usd'])
        elif event == 'reservation':
            rid = row['reservation_id']
            if baseline is None or rid in reservations:
                raise BudgetError('Invalid reservation event')
            reservations[rid] = {'bound': amount(row['bound_usd']), 'cost': None}
        elif event == 'settlement':
            rid = row['reservation_id']
            if rid not in reservations or reservations[rid]['cost'] is not None:
                raise BudgetError('Invalid settlement event')
            reservations[rid]['cost'] = amount(row['cost_usd'])
        else:
            raise BudgetError('Unrecognized ledger event')
    spent = None if baseline is None else baseline + sum(
        (r['cost'] for r in reservations.values() if r['cost'] is not None), Decimal(0))
    held = sum((r['bound'] for r in reservations.values() if r['cost'] is None), Decimal(0))
    return spent, held, reservations


def baseline(path, prior, source):
    prior = amount(prior)
    if source not in ('billing-dashboard', 'usage-export', 'owner-confirmed'):
        raise BudgetError('A supported baseline source is required')
    with locked(path) as (f, rows):
        spent, _, _ = state(rows)
        if spent is not None:
            raise BudgetError('Baseline already recorded; do not reset the ledger')
        append(f, {'event': 'baseline_verified', 'prior_usd': str(prior), 'source': source})


def reserve(path, model, attempts, input_tokens, output_tokens, checked_date):
    bound = estimate(model, attempts, input_tokens, output_tokens, checked_date)
    input_rate, output_rate = rates_for(model, input_tokens)
    with locked(path) as (f, rows):
        spent, held, _ = state(rows)
        if spent is None:
            raise BudgetError('Prior Anthropic spend is unknown; reconcile the baseline before reserving')
        if spent + held + bound > BUDGET:
            raise BudgetError('Reservation would exceed the $20 Anthropic budget')
        rid = uuid.uuid4().hex
        append(f, {'event': 'reservation', 'reservation_id': rid, 'bound_usd': str(bound),
                   'model': model, 'attempts': attempts, 'input_tokens_per_attempt': input_tokens,
                   'output_tokens_per_attempt': output_tokens, 'pricing_url': PRICE_URL,
                   'pricing_checked': PRICE_CHECKED, 'tier': 'standard', 'geography_bound': 'us-premium',
                   'input_rate_usd_per_million': str(input_rate), 'output_rate_usd_per_million': str(output_rate),
                   'cache_write_multiplier': '2', 'geography_multiplier': '1.1'})
    return rid, bound


def settle(path, rid, cost, source):
    cost = amount(cost)
    if source not in ('api-usage', 'billing-dashboard', 'usage-export'):
        raise BudgetError('A supported settlement source is required')
    with locked(path) as (f, rows):
        _, _, reservations = state(rows)
        if rid not in reservations or reservations[rid]['cost'] is not None:
            raise BudgetError('Unknown or already settled reservation')
        append(f, {'event': 'settlement', 'reservation_id': rid, 'cost_usd': str(cost), 'source': source,
                   'exceeds_reservation': cost > reservations[rid]['bound']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('estimate', 'reserve'):
        p = commands.add_parser(name)
        p.add_argument('--model', required=True)
        p.add_argument('--attempts', type=int, required=True, help='all requests including retries')
        p.add_argument('--input-tokens', type=int, required=True, help='max total input tokens per attempt')
        p.add_argument('--output-tokens', type=int, required=True, help='max output tokens per attempt')
    p = commands.add_parser('baseline')
    p.add_argument('--prior-usd', required=True)
    p.add_argument('--source', required=True, choices=('billing-dashboard', 'usage-export', 'owner-confirmed'))
    p = commands.add_parser('settle')
    p.add_argument('--reservation-id', required=True)
    p.add_argument('--cost-usd', required=True)
    p.add_argument('--source', required=True, choices=('api-usage', 'billing-dashboard', 'usage-export'))
    commands.add_parser('status')
    args = parser.parse_args()
    today = datetime.now(ZoneInfo('America/Denver')).date().isoformat()
    try:
        if args.command == 'baseline':
            baseline(LEDGER, args.prior_usd, args.source)
            print('Verified baseline recorded; no API request sent.')
        elif args.command == 'settle':
            settle(LEDGER, args.reservation_id, args.cost_usd, args.source)
            print('Settlement recorded; no API request sent.')
        else:
            bound = None
            if args.command in ('estimate', 'reserve'):
                bound = estimate(args.model, args.attempts, args.input_tokens, args.output_tokens, today)
                print(f'conservative_request_bound_usd: {bound}')
                print('Scope: first-party standard Messages API, text input, no hosted tools; bounds include retries.')
                print(f'pricing_checked: {PRICE_CHECKED}; source: {PRICE_URL}')
            if args.command == 'reserve':
                rid, _ = reserve(LEDGER, args.model, args.attempts, args.input_tokens, args.output_tokens, today)
                print(f'reservation_id: {rid}')
            with locked(LEDGER) as (_, rows):
                spent, held, _ = state(rows)
            print(f'budget_usd: {BUDGET}; spent_usd: {spent if spent is not None else "unknown"}; reserved_usd: {held}')
            if spent is None:
                print('Prior spend unknown; reconcile the baseline before any Anthropic API call.', file=sys.stderr)
                return 2
            remaining = BUDGET-spent-held
            print(f'remaining_usd: {remaining}')
            if args.command == 'estimate' and bound > remaining:
                print('The estimated bound exceeds the remaining budget.', file=sys.stderr)
                return 1
            if remaining < 0:
                print('The ledger exceeds the budget; stop and reconcile.', file=sys.stderr)
                return 1
    except (BudgetError, OSError, KeyError, TypeError, ArithmeticError) as exc:
        print(f'Cannot establish a safe budget: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
