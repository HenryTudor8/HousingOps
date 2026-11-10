"""Pure date and summary helpers for HousingOps. No database or UI imports."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Iterable, Mapping

DEMO_DATE = date(2026, 10, 28)
DEFAULT_STAY_END = date(2027, 5, 15)
CHECKPOINT_DAYS = (0, 7, 14, 30)


def checkpoint_dates(as_of: date) -> list[tuple[str, date]]:
    """Point-in-time checkpoints; not continuous-stay availability."""
    if not isinstance(as_of, date):
        raise TypeError("as_of must be datetime.date")
    return [
        ("Today" if days == 0 else f"+{days} days", as_of + timedelta(days=days))
        for days in CHECKPOINT_DAYS
    ]


def validate_stay_window(move_date: date, end_date: date) -> None:
    """Enforce a nonempty half-open interval [move_date, end_date)."""
    if not isinstance(move_date, date) or not isinstance(end_date, date):
        raise TypeError("Move and end dates must be datetime.date")
    if move_date >= end_date:
        raise ValueError("Stay end must be after the requested move date (end exclusive).")


def sum_column(rows: Iterable[Mapping[str, object]], key: str) -> int:
    return sum(int(row[key]) for row in rows)


def as_currency(value: object) -> str:
    return "$" + f"{value:,.2f}"


def scenario_totals(rows: Iterable[Mapping[str, object]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in rows:
        label = str(row["checkpoint"])
        totals[label] = totals.get(label, 0) + int(row["available_beds"])
    return totals
