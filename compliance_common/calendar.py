"""Business-day arithmetic for Regulation Z timing rules (12 CFR 1026.2(a)(6)).

Two definitions exist:
  * creditor business days: days the creditor's offices are open for substantially all
    business functions (general definition);
  * "specific" business days: every calendar day except Sundays and the legal public
    holidays of 5 U.S.C. 6103(a) (used for 1026.19(e)(1)(iii)(B), (e)(1)(iv), (e)(4)(ii),
    (f)(1)(ii), (f)(1)(iii), among others).

Holidays are computed from rules (pack calendar.yaml). A holiday falling on a Saturday is
NOT shifted to the observed Friday; this is an interpretation flagged for compliance review.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable, Iterable

_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The n-th (1-based) `weekday` (Mon=0) of a month; n=-1 means the last one."""
    if n > 0:
        first = date(year, month, 1)
        return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
    last = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def holidays(year: int, rules: Iterable[dict[str, Any]]) -> set[date]:
    found: set[date] = set()
    for rule in rules:
        if year < rule.get("first_year", 0):
            continue
        if "month_day" in rule:
            month, day = rule["month_day"]
            found.add(date(year, month, day))
        else:
            found.add(nth_weekday(year, rule["month"], _WEEKDAYS.index(rule["weekday"]), rule["nth"]))
    return found


def specific_business_day(rules: list[dict[str, Any]]) -> Callable[[date], bool]:
    cache: dict[int, set[date]] = {}

    def is_business_day(day: date) -> bool:
        if day.weekday() == 6:
            return False
        return day not in cache.setdefault(day.year, holidays(day.year, rules))

    return is_business_day


def creditor_business_day(open_days: Iterable[str], closed_dates: Iterable[date] = ()) -> Callable[[date], bool]:
    open_set = {_WEEKDAYS.index(name) for name in open_days}
    closed = set(closed_dates)
    return lambda day: day.weekday() in open_set and day not in closed


def add_business_days(start: date, count: int, is_business_day: Callable[[date], bool]) -> date:
    """The `count`-th business day after `start` (start itself is day 0)."""
    day, remaining = start, count
    while remaining > 0:
        day += timedelta(days=1)
        if is_business_day(day):
            remaining -= 1
    return day


def subtract_business_days(start: date, count: int, is_business_day: Callable[[date], bool]) -> date:
    """The `count`-th business day before `start` (start itself is day 0)."""
    day, remaining = start, count
    while remaining > 0:
        day -= timedelta(days=1)
        if is_business_day(day):
            remaining -= 1
    return day
