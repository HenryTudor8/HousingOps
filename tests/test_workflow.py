"""Offline tests for proposal-only transfer workflow: no DB writes or Neon access."""
from datetime import date
from decimal import Decimal

import pytest

from app.workflow import TransferPreflightError, build_transfer_preview

START = date(2026, 8, 15)
MOVE = date(2026, 11, 17)
END = date(2027, 5, 15)


def fixtures():
    req = {
        "request_id": "REQ_0002", "resident_id": "RES_0001", "status": "pending",
        "desired_move_date": MOVE, "max_semester_price_usd": Decimal("3800.00"),
    }
    bed = {
        "request_id": "REQ_0002", "bed_id": "BED_0140", "building_name": "Pride Hall",
        "room_number": "301", "semester_rate_usd": Decimal("3221.50"),
    }
    old = {
        "resident_id": "RES_0001", "assignment_id": "ASG_0001", "bed_id": "BED_0010",
        "start_date": START, "end_date": END, "status": "confirmed",
    }
    return req, bed, old


def preview(req=None, bed=None, assignments=None, eligible=None, end=END):
    base_req, base_bed, old = fixtures()
    return build_transfer_preview(
        req if req is not None else base_req,
        bed if bed is not None else base_bed,
        eligible if eligible is not None else [base_bed],
        assignments if assignments is not None else [old],
        end,
    )


def test_preview_proposes_split_without_mutating_original_data():
    req, bed, old = fixtures()
    output = preview(req=req, bed=bed, assignments=[old])
    assert output.proposed_previous_end_date == MOVE
    assert output.proposed_new_start_date == MOVE
    assert output.proposed_new_end_date == END
    assert output.destination_bed_id == "BED_0140"
    assert output.proposed_request_status == "approved"
    assert old["end_date"] == END
    assert req["status"] == "pending"
    assert len(output.as_rows()) == 3


def test_preview_is_value_object_not_database_write():
    result = preview()
    assert result.destination_semester_rate_usd == Decimal("3221.50")
    assert result.previous_assignment_id == "ASG_0001"


def test_rejects_non_pending_request():
    req, _, _ = fixtures()
    req["status"] = "approved"
    with pytest.raises(TransferPreflightError, match="pending"):
        preview(req=req)


def test_rejects_wrong_candidate_request():
    _, bed, _ = fixtures()
    bed["request_id"] = "REQ_OTHER"
    with pytest.raises(TransferPreflightError, match="another request"):
        preview(bed=bed)


def test_rejects_stale_or_unranked_candidate():
    with pytest.raises(TransferPreflightError, match="latest matching"):
        preview(eligible=[])


def test_rejects_expensive_candidate():
    _, bed, _ = fixtures()
    bed["semester_rate_usd"] = Decimal("5000")
    with pytest.raises(TransferPreflightError, match="budget"):
        preview(bed=bed, eligible=[bed])


def test_rejects_nonfinite_price():
    _, bed, _ = fixtures()
    bed["semester_rate_usd"] = "NaN"
    with pytest.raises(TransferPreflightError, match="invalid rate"):
        preview(bed=bed, eligible=[bed])


def test_rejects_no_source_assignment():
    with pytest.raises(TransferPreflightError, match="exactly one"):
        preview(assignments=[])


def test_rejects_second_confirmed_future_assignment():
    _, _, old = fixtures()
    future = dict(old, assignment_id="ASG_FUTURE", start_date=date(2027, 1, 1))
    with pytest.raises(TransferPreflightError, match="exactly one"):
        preview(assignments=[old, future])


def test_rejects_source_that_starts_on_move_date():
    _, _, old = fixtures()
    old["start_date"] = MOVE
    with pytest.raises(TransferPreflightError, match="start before"):
        preview(assignments=[old])


def test_rejects_other_resident_assignment():
    _, _, old = fixtures()
    old["resident_id"] = "RES_OTHER"
    with pytest.raises(TransferPreflightError, match="different resident"):
        preview(assignments=[old])


def test_rejects_noop_bed_transfer():
    _, bed, old = fixtures()
    bed["bed_id"] = old["bed_id"]
    with pytest.raises(TransferPreflightError, match="different"):
        preview(bed=bed, eligible=[bed])


def test_rejects_invalid_interval():
    with pytest.raises(TransferPreflightError, match="after"):
        preview(end=MOVE)


def test_rejects_missing_field():
    req, _, _ = fixtures()
    del req["resident_id"]
    with pytest.raises(TransferPreflightError, match="resident_id"):
        preview(req=req)
