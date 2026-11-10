"""Additional *read-only* SQL for room-transfer preview.

The first real write transaction and SQL concurrency verification are reserved
for the database-focused team workstream described in docs/workflow_handoff.md.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.repository import fetch_all

SQL_REQUEST_CONTEXT = """
SELECT request_id, resident_id, status, desired_move_date, max_semester_price_usd
FROM room_change_requests
WHERE request_id = %s
"""


def request_context_for_preview(request_id: str) -> dict[str, Any] | None:
    """Fetch the current request rather than trusting a stale dashboard selection."""
    if not request_id or len(request_id) > 128:
        raise ValueError("Invalid request ID")
    rows = fetch_all(SQL_REQUEST_CONTEXT, (request_id,))
    if len(rows) > 1:
        raise ValueError("Unexpected duplicate request identifiers")
    return rows[0] if rows else None


SQL_REQUEST_ASSIGNMENTS_OVERLAPPING_STAY = """
SELECT q.request_id, q.resident_id,
       a.assignment_id, a.bed_id, a.start_date, a.end_date, a.status
FROM room_change_requests q
JOIN bed_assignments a ON a.resident_id = q.resident_id
WHERE q.request_id = %s
  AND q.status = 'pending'
  AND a.status = 'confirmed'
  AND daterange(a.start_date, a.end_date, '[)') &&
      daterange(q.desired_move_date, %s, '[)')
ORDER BY a.start_date, a.assignment_id
"""


def resident_assignments_for_preview(request_id: str, end_date: date) -> list[dict[str, Any]]:
    """Read confirmed assignments intersecting a request's proposed stay."""
    if not request_id or len(request_id) > 128:
        raise ValueError("Invalid request ID")
    if not isinstance(end_date, date):
        raise TypeError("end_date must be datetime.date")
    return fetch_all(SQL_REQUEST_ASSIGNMENTS_OVERLAPPING_STAY, (request_id, end_date))
