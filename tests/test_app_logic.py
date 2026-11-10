"""Offline tests for dashboard helpers. No Neon connection required."""
from datetime import date
import pytest
from app.logic import as_currency, checkpoint_dates, scenario_totals, sum_column, validate_stay_window


def test_vacancy_checkpoints_are_explicit_dates():
    assert checkpoint_dates(date(2026, 10, 28)) == [
        ("Today", date(2026, 10, 28)),
        ("+7 days", date(2026, 11, 4)),
        ("+14 days", date(2026, 11, 11)),
        ("+30 days", date(2026, 11, 27)),
    ]


def test_checkpoints_allow_different_reference_dates():
    assert checkpoint_dates(date(2026, 11, 10))[1][1] == date(2026, 11, 17)


def test_checkpoint_type_is_validated():
    with pytest.raises(TypeError):
        checkpoint_dates("2026-10-28")


def test_stay_uses_exclusive_end_date():
    validate_stay_window(date(2026, 11, 17), date(2027, 5, 15))


@pytest.mark.parametrize("end", [date(2026, 11, 17), date(2026, 11, 16)])
def test_empty_or_reversed_stay_is_rejected(end):
    with pytest.raises(ValueError, match="after"):
        validate_stay_window(date(2026, 11, 17), end)


def test_stay_date_types_are_validated():
    with pytest.raises(TypeError):
        validate_stay_window("not a date", date(2027, 5, 15))


def test_currency_has_two_decimals():
    assert as_currency(3221.5) == "$3,221.50"


def test_sum_column_handles_empty_rows():
    assert sum_column([], "available_beds") == 0
    assert sum_column([{"available_beds": 4}, {"available_beds": 2}], "available_beds") == 6


def test_checkpoint_totals_group_only_matching_labels():
    assert scenario_totals([
        {"checkpoint": "Today", "available_beds": 9},
        {"checkpoint": "Today", "available_beds": 25},
        {"checkpoint": "+7 days", "available_beds": 39},
    ]) == {"Today": 34, "+7 days": 39}


def test_no_database_credentials_in_pure_logic():
    import app.logic as logic
    assert not hasattr(logic, "database_url")
