"""Shared month handling, so expenses, budgets and the summary all define "a month" the same way."""
from datetime import date


def month_bounds(month: str) -> tuple[date, date]:
    """'2026-09' -> (2026-09-01, 2026-10-01): a half-open range covering that month.

    Callers must pass a validated 'YYYY-MM' string (routers enforce this with a regex).
    """
    year, mon = (int(part) for part in month.split("-"))
    start = date(year, mon, 1)
    # December is the edge case: the next month is January of the *next year*.
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return start, end
