"""Read-only, parameterized SQL access to the existing 16-table HousingOps schema.

User selections are passed with psycopg parameters, never interpolated into SQL.
Fresh connections prevent sharing sessions across Streamlit users.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from app.logic import checkpoint_dates, validate_stay_window

ROOT = Path(__file__).resolve().parents[1]


class DatabaseNotConfigured(RuntimeError):
    """The local Neon DATABASE_URL has not been configured."""


def database_url() -> str:
    load_dotenv(ROOT / ".env")
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        raise DatabaseNotConfigured(
            "No DATABASE_URL found. Copy .env.example to .env and set your private connection URL."
        )
    return dsn


def fetch_all(statement: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Run one SELECT in a read-only transaction. Never write or migrate here."""
    with psycopg.connect(database_url(), connect_timeout=10, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(statement, params)
            return list(cur.fetchall())


SQL_INVENTORY = """
WITH inventory AS (
    SELECT b.building_name, bed.bed_id,
           EXISTS (
               SELECT 1 FROM bed_assignments a
               WHERE a.bed_id = bed.bed_id
                 AND a.status = 'confirmed'
                 AND a.start_date <= %s AND a.end_date > %s
           ) AS occupied
    FROM beds bed
    JOIN rooms r ON r.room_id = bed.room_id
    JOIN floors f ON f.floor_id = r.floor_id
    JOIN buildings b ON b.building_id = f.building_id
)
SELECT building_name,
       COUNT(*)::int AS total_beds,
       COUNT(*) FILTER (WHERE occupied)::int AS occupied_beds,
       COUNT(*) FILTER (WHERE NOT occupied)::int AS available_beds
FROM inventory
GROUP BY building_name
ORDER BY building_name
"""

SQL_RA_COVERAGE = """
SELECT b.building_name, f.floor_number,
       EXISTS (
           SELECT 1 FROM staff_floor_assignments sfa
           JOIN staff s ON s.staff_id = sfa.staff_id
           WHERE sfa.floor_id = f.floor_id
             AND s.role = 'RA' AND sfa.status = 'active'
             AND sfa.start_date <= %s AND sfa.end_date > %s
       ) AS covered
FROM floors f
JOIN buildings b ON b.building_id = f.building_id
ORDER BY b.building_name, f.floor_number
"""

SQL_PENDING_REQUESTS = """
SELECT q.request_id, q.demo_scenario, q.desired_move_date,
       q.max_semester_price_usd, q.preferred_floor_number,
       rt.room_type_name
FROM room_change_requests q
JOIN room_types rt ON rt.room_type_id = q.room_type_id
WHERE q.status = 'pending'
ORDER BY q.request_id
"""

SQL_MATCHES = """
WITH selected_request AS (
    SELECT q.request_id, q.resident_id, q.desired_move_date,
           q.room_type_id, q.max_semester_price_usd,
           q.preferred_floor_number, q.demo_scenario,
           res.eligibility_group, res.student_level
    FROM room_change_requests q
    JOIN residents res ON res.resident_id = q.resident_id
    WHERE q.request_id = %s AND q.status = 'pending'
      AND q.desired_move_date < %s
)
SELECT q.request_id, q.demo_scenario, q.desired_move_date,
       pref.rank AS preference_rank, b.building_name, f.floor_number,
       r.room_number, bed.bed_id, rt.room_type_name, rate.semester_rate_usd
FROM selected_request q
JOIN request_preferences pref ON pref.request_id = q.request_id
JOIN buildings b ON b.building_id = pref.building_id
JOIN floors f ON f.building_id = b.building_id
JOIN rooms r ON r.floor_id = f.floor_id
JOIN beds bed ON bed.room_id = r.room_id
JOIN room_types rt ON rt.room_type_id = r.room_type_id
JOIN housing_rates rate
  ON rate.building_id = b.building_id
 AND rate.room_type_id = r.room_type_id
 AND rate.academic_year = '2026-27'
WHERE r.room_type_id = q.room_type_id
  AND rate.semester_rate_usd <= q.max_semester_price_usd
  AND (q.preferred_floor_number IS NULL
       OR f.floor_number = q.preferred_floor_number)
  AND (b.eligible_group = 'coed'
       OR b.eligible_group = q.eligibility_group)
  AND b.eligible_level = q.student_level
  AND NOT EXISTS (
      SELECT 1 FROM bed_assignments a
      WHERE a.bed_id = bed.bed_id AND a.status = 'confirmed'
        AND daterange(a.start_date, a.end_date, '[)') &&
            daterange(q.desired_move_date, %s, '[)')
  )
ORDER BY pref.rank, rate.semester_rate_usd,
         b.building_name, f.floor_number, r.room_number, bed.bed_id
"""

SQL_HISTORICAL_TOTALS = """
SELECT t.term_code, t.term_name, t.calendar_year, t.season,
       COUNT(o.property_code)::int AS properties_reported,
       SUM(o.occupied_spaces)::int AS total_occupied_spaces
FROM occupancy_observations o
JOIN academic_terms t ON t.term_code = o.term_code
GROUP BY t.term_code, t.term_name, t.calendar_year, t.season
ORDER BY t.calendar_year,
         CASE t.season WHEN 'Spring' THEN 1 WHEN 'Summer' THEN 2 ELSE 3 END
"""

SQL_HISTORICAL_PROPERTIES = """
SELECT p.property_name, t.term_name, t.calendar_year, t.season,
       o.occupied_spaces
FROM occupancy_observations o
JOIN housing_properties p ON p.property_code = o.property_code
JOIN academic_terms t ON t.term_code = o.term_code
ORDER BY p.property_name, t.calendar_year,
         CASE t.season WHEN 'Spring' THEN 1 WHEN 'Summer' THEN 2 ELSE 3 END
"""


def inventory_on(on_date: date) -> list[dict[str, Any]]:
    return fetch_all(SQL_INVENTORY, (on_date, on_date))


def vacancy_checkpoints(as_of: date) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for label, when in checkpoint_dates(as_of):
        for row in inventory_on(when):
            output.append({"checkpoint": label, "check_date": when, **row})
    return output


def ra_coverage_on(on_date: date) -> list[dict[str, Any]]:
    return fetch_all(SQL_RA_COVERAGE, (on_date, on_date))


def pending_requests() -> list[dict[str, Any]]:
    return fetch_all(SQL_PENDING_REQUESTS)


def matching_beds(request_id: str, move_date: date, end_date: date) -> list[dict[str, Any]]:
    """Return candidates for an existing pending request, never reserve a bed."""
    validate_stay_window(move_date, end_date)
    if not request_id or len(request_id) > 128:
        raise ValueError("Invalid request ID")
    return fetch_all(SQL_MATCHES, (request_id, end_date, end_date))


def historical_totals() -> list[dict[str, Any]]:
    return fetch_all(SQL_HISTORICAL_TOTALS)


def historical_by_property() -> list[dict[str, Any]]:
    return fetch_all(SQL_HISTORICAL_PROPERTIES)
