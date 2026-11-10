"""Pure preflight logic for a *proposed* HousingOps room change.

No PostgreSQL connection, status mutation, assignment insert, or booking occurs here.
Real approvals require an atomic transaction and fresh revalidation in the DB.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Mapping, Sequence

from app.logic import validate_stay_window


class TransferPreflightError(ValueError):
    """A proposed transfer cannot be safely previewed using the supplied snapshot."""


@dataclass(frozen=True)
class TransferPreview:
    """Read-only proposed state transition, *not* a persistence command."""

    request_id: str
    resident_id: str
    previous_assignment_id: str
    previous_bed_id: str
    previous_start_date: date
    proposed_previous_end_date: date
    destination_bed_id: str
    destination_building: str
    destination_room: str
    destination_semester_rate_usd: Decimal
    proposed_new_start_date: date
    proposed_new_end_date: date
    proposed_request_status: str = "approved"

    def as_rows(self) -> list[dict[str, object]]:
        """Readable summary for the Streamlit review panel."""
        return [
            {
                "step": "Shorten existing assignment (proposed)",
                "reference": self.previous_assignment_id,
                "bed_id": self.previous_bed_id,
                "start_date": self.previous_start_date,
                "end_date": self.proposed_previous_end_date,
            },
            {
                "step": "Create destination assignment (proposed)",
                "reference": self.request_id,
                "bed_id": self.destination_bed_id,
                "start_date": self.proposed_new_start_date,
                "end_date": self.proposed_new_end_date,
            },
            {
                "step": "Update request status (proposed)",
                "reference": self.request_id,
                "bed_id": self.destination_bed_id,
                "start_date": None,
                "end_date": None,
            },
        ]


def _require_string(row: Mapping[str, object], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise TransferPreflightError(f"Missing or invalid {field} in the database snapshot.")
    return value


def _require_date(row: Mapping[str, object], field: str) -> date:
    value = row.get(field)
    if not isinstance(value, date) or isinstance(value, datetime):
        raise TransferPreflightError(f"Missing or invalid date {field} in the database snapshot.")
    return value


def build_transfer_preview(
    request: Mapping[str, object],
    candidate: Mapping[str, object],
    eligible_beds: Sequence[Mapping[str, object]],
    intersecting_assignments: Sequence[Mapping[str, object]],
    stay_end: date,
) -> TransferPreview:
    """Review existing request, candidate and assignments without writing.

    eligible_beds must come from the full-stay SQL matching query, not raw UI input.
    intersecting_assignments includes all confirmed resident assignments overlapping
    [desired_move_date, stay_end), queried at preview time.

    This check is subject to races between read and write. The actual approval
    transaction must re-evaluate all business rules under suitable locks and
    rely on PostgreSQL exclusion constraints for conflicting assignments.
    """
    request_id = _require_string(request, "request_id")
    resident_id = _require_string(request, "resident_id")
    if request.get("status") != "pending":
        raise TransferPreflightError("Only pending room-change requests can be considered for approval.")
    move_date = _require_date(request, "desired_move_date")
    try:
        validate_stay_window(move_date, stay_end)
    except (ValueError, TypeError) as exc:
        raise TransferPreflightError(str(exc)) from exc

    candidate_bed = _require_string(candidate, "bed_id")
    if candidate.get("request_id") != request_id:
        raise TransferPreflightError("The chosen destination belongs to another request.")
    if not any(
        row.get("bed_id") == candidate_bed and row.get("request_id") == request_id
        for row in eligible_beds
    ):
        raise TransferPreflightError("The chosen bed is not in the latest matching results.")

    try:
        rate = Decimal(str(candidate["semester_rate_usd"]))
        ceiling = Decimal(str(request["max_semester_price_usd"]))
    except (KeyError, TypeError, InvalidOperation) as exc:
        raise TransferPreflightError("Missing or invalid semester rate or budget.") from exc
    if not rate.is_finite() or not ceiling.is_finite() or rate <= 0 or rate > ceiling:
        raise TransferPreflightError("Selected bed exceeds the request budget or has an invalid rate.")

    if len(intersecting_assignments) != 1:
        raise TransferPreflightError(
            "Expected exactly one existing confirmed resident assignment during the proposed stay. "
            "Transfers from empty or multiple assignment histories need manual review."
        )
    existing = intersecting_assignments[0]
    if _require_string(existing, "resident_id") != resident_id:
        raise TransferPreflightError("Existing assignment belongs to a different resident.")
    if existing.get("status") != "confirmed":
        raise TransferPreflightError("Existing assignment is not confirmed.")
    assignment_id = _require_string(existing, "assignment_id")
    source_bed = _require_string(existing, "bed_id")
    source_start = _require_date(existing, "start_date")
    source_end = _require_date(existing, "end_date")
    if not (source_start < move_date < source_end):
        raise TransferPreflightError(
            "The source assignment must start before and cover the desired move date. "
            "Same-day starts and gaps require a separate workflow."
        )
    if source_bed == candidate_bed:
        raise TransferPreflightError("Destination must be different from the currently assigned bed.")

    building = _require_string(candidate, "building_name")
    room_number = _require_string(candidate, "room_number")
    return TransferPreview(
        request_id=request_id,
        resident_id=resident_id,
        previous_assignment_id=assignment_id,
        previous_bed_id=source_bed,
        previous_start_date=source_start,
        proposed_previous_end_date=move_date,
        destination_bed_id=candidate_bed,
        destination_building=building,
        destination_room=room_number,
        destination_semester_rate_usd=rate,
        proposed_new_start_date=move_date,
        proposed_new_end_date=stay_end,
    )
