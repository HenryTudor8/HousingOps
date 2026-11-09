"""Load the 16 HousingOps CSV datasets into an EMPTY PostgreSQL schema.

Milestone 2 reproducible data loading. Compatible with sql/01_schema.sql.

Prerequisites (from the HousingOps repository root):
    python scripts/clean_public_data.py
    python scripts/generate_synthetic.py --seed 532 --as-of 2026-10-28

Provide DATABASE_URL in a local .env file or environment variable. Example:
    DATABASE_URL=postgresql://USERNAME:PASSWORD@HOST/neondb?sslmode=require

Run:
    python scripts/load_database.py

Safety: All tables must be empty, all inserts execute in one transaction,
       and a failure rolls back instead of leaving a half-loaded database.
       This file never drops or truncates tables, and never prints credentials.
"""

from __future__ import annotations

import csv
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql

from generate_synthetic import validate_dataset

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "data" / "processed"
SYNTH_DIR = PUBLIC_DIR / "synthetic"

# Order matters: every referenced parent table is loaded first.
# These 16 names match the existing Milestone 2 sql/01_schema.sql file.
LOAD_ORDER = (
    "housing_properties", "academic_terms", "occupancy_observations",
    "source_register", "room_types", "buildings", "floors", "housing_rates",
    "rooms", "beds", "residents", "staff", "staff_floor_assignments",
    "bed_assignments", "room_change_requests", "request_preferences",
)
PUBLIC_TABLES = frozenset(LOAD_ORDER[:3])
SYNTHETIC_TABLES = frozenset(LOAD_ORDER[3:])

INTEGER_FIELDS = {
    "calendar_year", "occupied_spaces", "source_year", "beds_per_room",
    "published_floor_count", "simulation_rooms_per_floor", "floor_number",
    "preferred_floor_number", "rank",
}
DECIMAL_FIELDS = {"semester_rate_usd", "max_semester_price_usd"}
DATE_FIELDS = {"start_date", "end_date", "created_date", "desired_move_date"}
BOOLEAN_FIELDS = {"meal_plan_required", "synthetic_inventory", "synthetic_record"}
NULLABLE_FIELDS = {("room_change_requests", "preferred_floor_number")}

# Expected historical counts are fixed by the original N.C. A&T workbook.
PUBLIC_TOTALS = {
    "2022_fall": 5873, "2023_spring": 5732, "2023_summer": 452,
    "2023_fall": 5705, "2024_spring": 5702, "2024_summer": 257,
}


def input_path(table: str) -> Path:
    if table not in LOAD_ORDER:
        raise ValueError(f"Unexpected table {table!r}")
    folder = PUBLIC_DIR if table in PUBLIC_TABLES else SYNTH_DIR
    return folder / f"{table}.csv"


def read_csv(table: str) -> tuple[list[str], list[dict[str, str]]]:
    path = input_path(table)
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing {path}. Run clean_public_data.py and generate_synthetic.py first."
        )
    with path.open("r", newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        columns = reader.fieldnames
        if not columns or len(columns) != len(set(columns)):
            raise ValueError(f"Missing or duplicate CSV column names in {path}")
        records = list(reader)
    if not records:
        raise ValueError(f"CSV is empty: {path}")
    if any(None in row or row.get(col) is None for row in records for col in columns):
        raise ValueError(f"CSV rows do not match header in {path}")
    return columns, records


def validate_public_data(data: dict[str, list[dict[str, str]]]) -> None:
    properties = data["housing_properties"]
    terms = data["academic_terms"]
    observations = data["occupancy_observations"]
    if (len(properties), len(terms), len(observations)) != (25, 6, 150):
        raise ValueError("Unexpected public input counts; expected 25 properties, 6 terms, 150 observations")
    property_ids = {p["property_code"] for p in properties}
    term_ids = {t["term_code"] for t in terms}
    if len(property_ids) != len(properties) or term_ids != set(PUBLIC_TOTALS):
        raise ValueError("Public property or term identifiers are duplicated/incorrect")
    counts = {term: 0 for term in PUBLIC_TOTALS}
    seen = set()
    for rec in observations:
        p, t = rec["property_code"], rec["term_code"]
        if p not in property_ids or t not in term_ids or (p, t) in seen:
            raise ValueError("Historical occupancy has invalid/duplicate property-term references")
        seen.add((p, t))
        spaces = int(rec["occupied_spaces"])
        if spaces < 0:
            raise ValueError("Historical occupancy cannot be negative")
        counts[t] += spaces
    if counts != PUBLIC_TOTALS:
        raise ValueError(f"Public occupancy totals do not match source: {counts}")


def convert_field(table: str, col: str, raw: str):
    """Convert CSV text to Python types understood by psycopg/PostgreSQL."""
    if raw == "" and (table, col) in NULLABLE_FIELDS:
        return None
    try:
        if col in INTEGER_FIELDS:
            return int(raw)
        if col in DECIMAL_FIELDS:
            return Decimal(raw)
        if col in DATE_FIELDS:
            return date.fromisoformat(raw)
        if col in BOOLEAN_FIELDS:
            if raw.strip().lower() in {"true", "t", "1", "yes"}:
                return True
            if raw.strip().lower() in {"false", "f", "0", "no"}:
                return False
            raise ValueError(f"Invalid boolean {raw!r}")
    except (ValueError, InvalidOperation) as exc:
        raise ValueError(f"Cannot convert {table}.{col} value {raw!r}") from exc
    return raw


def load() -> None:
    load_dotenv(ROOT / ".env")
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL not set. Copy .env.example to .env and paste your Neon "
            "PostgreSQL connection string there. Do not commit or share .env."
        )

    # Validate the files and their relationships BEFORE opening the connection.
    raw_inputs: dict[str, list[dict[str, str]]] = {}
    parsed_inputs = {}
    for table in LOAD_ORDER:
        fields, records = read_csv(table)
        raw_inputs[table] = records
        parsed_inputs[table] = (fields, [tuple(convert_field(table, c, r[c]) for c in fields)
                                         for r in records])

    validate_public_data(raw_inputs)
    validate_dataset({key: raw_inputs[key] for key in SYNTHETIC_TABLES})
    expected = {key: len(values) for key, values in raw_inputs.items()}

    # The connection context commits at the end, or rolls back on any error.
    with psycopg.connect(dsn, connect_timeout=20) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            database, user = cur.fetchone()
            print(f"Connected to PostgreSQL database {database!r} as {user!r} (credentials hidden)")

            for table in LOAD_ORDER:
                fields, records = parsed_inputs[table]
                cur.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = %s",
                    (table,),
                )
                actual_fields = {row[0] for row in cur.fetchall()}
                if not actual_fields:
                    raise RuntimeError(f"Missing public.{table}; run sql/01_schema.sql first")
                if actual_fields != set(fields):
                    missing = sorted(actual_fields - set(fields))
                    unexpected = sorted(set(fields) - actual_fields)
                    raise RuntimeError(
                        f"CSV columns do not match public.{table}. "
                        f"Missing from CSV: {missing}; not in SQL schema: {unexpected}. "
                        "Reconcile with the team's final ERD before importing."
                    )

                cur.execute(sql.SQL("SELECT COUNT(*) FROM public.{}").format(sql.Identifier(table)))
                prior = cur.fetchone()[0]
                if prior:
                    raise RuntimeError(
                        f"public.{table} already has {prior} rows. Refusing to import into a nonempty "
                        "database. Use a fresh Neon development branch or coordinate with your team."
                    )

            for table in LOAD_ORDER:
                fields, records = parsed_inputs[table]
                insert = sql.SQL("INSERT INTO public.{} ({}) VALUES ({})").format(
                    sql.Identifier(table),
                    sql.SQL(", ").join(sql.Identifier(field) for field in fields),
                    sql.SQL(", ").join(sql.Placeholder() for _ in fields),
                )
                cur.executemany(insert, records)
                cur.execute(sql.SQL("SELECT COUNT(*) FROM public.{}").format(sql.Identifier(table)))
                count = cur.fetchone()[0]
                if count != expected[table]:
                    raise RuntimeError(f"Count mismatch on {table}: expected {expected[table]}, loaded {count}")
                print(f"  {table:27s} {count:5d} records")

    print("Success: 16 tables loaded and verified. Transaction committed.")
    print("Note: historic occupancy is public; resident and operational records are synthetic.")


if __name__ == "__main__":
    load()
