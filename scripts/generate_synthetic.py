"""Generate fictional room-level HousingOps data with documented public reference rates.

This is a *canonical data layer*, not the final PostgreSQL import schema.
No real resident, RA, room inventory, or 2026 occupancy is asserted.

Run from repository root:
    python scripts/generate_synthetic.py
    python scripts/generate_synthetic.py --seed 532 --as-of 2026-10-28

The script reads public housing property names from data/processed/housing_properties.csv
(created by scripts/clean_public_data.py) and writes fictional operations to
 data/processed/synthetic/. Results are deterministic for a given seed/date.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROPERTIES = ROOT / "data" / "processed" / "housing_properties.csv"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "synthetic"
SEED = 532
AS_OF = date(2026, 10, 28)
ACADEMIC_YEAR = "2026-27"
START_DATE = date(2026, 8, 15)
END_DATE = date(2027, 5, 15)  # End is EXCLUSIVE
RATE_URL = "https://www.ncat.edu/campus-life/student-affairs/departments/housing-and-residence-life/resident-resources/cost-for-living-on-campus.php"

# Names are verified against the Excel-derived housing_properties.csv at runtime.
# 'floors' and room-type availability are drawn from official hall descriptions.
# Room counts per floor, bedroom layouts, occupancy, residents, and staff are SYNTHETIC.
# Blair Hall is currently described as part of suite-style Aggie Village even though
# the historical workbook classifies Blair as Traditional. Both remain distinct facts.
BUILDINGS = (
    {
        "building_id": "BLD_COOPER", "property_code": "cooper_hall", "building_name": "Cooper Hall",
        "living_style_current": "Traditional", "eligible_group": "male", "eligible_level": "first_year",
        "floors_published": 4, "floor_count_simulated": 4,
        "rate_choices": (("double", "2554.50"),),
        "profile_url": "https://www.ncat.edu/campus-life/student-affairs/departments/housing-and-residence-life/housing/residence-halls/cooper.php",
    },
    {
        "building_id": "BLD_HOLLAND", "property_code": "holland_hall", "building_name": "Holland Hall",
        "living_style_current": "Traditional", "eligible_group": "female", "eligible_level": "first_year",
        "floors_published": 3, "floor_count_simulated": 3,
        "rate_choices": (("double", "2554.50"),),
        "profile_url": "https://www.ncat.edu/campus-life/student-affairs/departments/housing-and-residence-life/housing/residence-halls/holland.php",
    },
    {
        "building_id": "BLD_BLAIR", "property_code": "blair_hall", "building_name": "Blair Hall",
        "living_style_current": "Suite", "eligible_group": "coed", "eligible_level": "upperclass",
        "floors_published": 3, "floor_count_simulated": 3,
        "rate_choices": (("double", "3208.00"), ("single", "3358.00"),
                         ("private", "3508.00"), ("double_deluxe", "3283.00")),
        "profile_url": "https://www.ncat.edu/campus-life/student-affairs/departments/housing-and-residence-life/housing/residence-halls/aggie-village.php",
    },
    {
        "building_id": "BLD_PRIDE", "property_code": "pride_hall", "building_name": "Pride Hall",
        "living_style_current": "Suite", "eligible_group": "coed", "eligible_level": "upperclass",
        "floors_published": 3, "floor_count_simulated": 3,
        "rate_choices": (("double", "3221.50"), ("single", "3539.00"), ("private", "3693.00")),
        "profile_url": "https://www.ncat.edu/campus-life/student-affairs/departments/housing-and-residence-life/housing/residence-halls/pride.php",
    },
)
ROOM_TYPES = (
    {"room_type_id": "double", "room_type_name": "Double", "beds_per_room": 2},
    {"room_type_id": "single", "room_type_name": "Single", "beds_per_room": 1},
    {"room_type_id": "private", "room_type_name": "Private", "beds_per_room": 1},
    {"room_type_id": "double_deluxe", "room_type_name": "Double Deluxe", "beds_per_room": 2},
)
ROOM_CAPACITY = {r["room_type_id"]: r["beds_per_room"] for r in ROOM_TYPES}


def rows_from_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_properties(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing {path}. Run 'python scripts/clean_public_data.py' first."
        )
    rows = rows_from_csv(path)
    required = {"property_code", "property_name", "living_style"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Public properties CSV is empty or missing columns: {required}")
    props = {r["property_code"]: r for r in rows}
    if len(props) != len(rows):
        raise ValueError("Duplicate property_code in cleaned public data")
    for spec in BUILDINGS:
        row = props.get(spec["property_code"])
        if row is None or row["property_name"] != spec["building_name"]:
            raise ValueError(f"Selected documented hall not found in public dataset: {spec['building_name']}")
    return props


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def overlaps(start1: date, end1: date, start2: date, end2: date) -> bool:
    """True if half-open date intervals [start, end) overlap."""
    return start1 < end2 and start2 < end1


def valid_housing_for_resident(building: dict, resident: dict) -> bool:
    return (building["eligible_group"] in ("coed", resident["eligibility_group"])
            and building["eligible_level"] == resident["student_level"])


def bed_is_available(dataset: dict, bed_id: str, day: date) -> bool:
    """Check confirmed assignment on move date, not full-term future availability."""
    return all(
        not (a["status"] == "confirmed" and a["bed_id"] == bed_id
             and parse_day(a["start_date"]) <= day < parse_day(a["end_date"]))
        for a in dataset["bed_assignments"]
    )


def eligible_beds(dataset: dict, request: dict) -> list[dict]:
    """Basic candidate preview for testing; NOT the final SQL Mobility Engine.

    This checks availability on desired move date only. A production reservation
    must also check the intended stay period and transactionally lock inventory.
    """
    building_by_id = {x["building_id"]: x for x in dataset["buildings"]}
    floor_by_id = {x["floor_id"]: x for x in dataset["floors"]}
    room_by_id = {x["room_id"]: x for x in dataset["rooms"]}
    resident_by_id = {x["resident_id"]: x for x in dataset["residents"]}
    rates = {(r["building_id"], r["room_type_id"]): float(r["semester_rate_usd"])
             for r in dataset["housing_rates"]}
    resident = resident_by_id[request["resident_id"]]
    ranks = {x["building_id"]: int(x["rank"])
             for x in dataset["request_preferences"] if x["request_id"] == request["request_id"]}
    day = parse_day(request["desired_move_date"])
    current_bed_ids = {
        x["bed_id"] for x in dataset["bed_assignments"]
        if x["resident_id"] == resident["resident_id"] and x["status"] == "confirmed"
        and parse_day(x["start_date"]) <= day < parse_day(x["end_date"])
    }
    candidates = []
    for bed in dataset["beds"]:
        room = room_by_id[bed["room_id"]]
        floor = floor_by_id[room["floor_id"]]
        building = building_by_id[floor["building_id"]]
        if building["building_id"] not in ranks or not valid_housing_for_resident(building, resident):
            continue
        if room["room_type_id"] != request["room_type_id"]:
            continue
        if request["preferred_floor_number"] and str(floor["floor_number"]) != request["preferred_floor_number"]:
            continue
        price = rates[(building["building_id"], room["room_type_id"])]
        if price > float(request["max_semester_price_usd"]):
            continue
        if bed["bed_id"] in current_bed_ids or not bed_is_available(dataset, bed["bed_id"], day):
            continue
        candidates.append({"bed_id": bed["bed_id"], "building_id": building["building_id"],
                           "rank": ranks[building["building_id"]], "semester_rate_usd": price})
    return sorted(candidates, key=lambda x: (x["rank"], x["semester_rate_usd"], x["bed_id"]))


def generate(public_properties: dict[str, dict[str, str]], *, seed: int = SEED,
             as_of: date = AS_OF, rooms_per_floor: int = 6) -> dict[str, list[dict]]:
    if rooms_per_floor < 3:
        raise ValueError("Use at least three rooms per floor for demo scenarios")
    if not START_DATE <= as_of < END_DATE - timedelta(days=40):
        raise ValueError("as_of must be within the demonstration academic year")
    rng = random.Random(seed)
    dataset: dict[str, list[dict]] = {key: [] for key in (
        "source_register", "buildings", "floors", "room_types", "housing_rates", "rooms", "beds",
        "residents", "bed_assignments", "staff", "staff_floor_assignments",
        "room_change_requests", "request_preferences")}
    dataset["room_types"] = [dict(x) for x in ROOM_TYPES]
    dataset["source_register"] = [
        {"source_id": "SRC_EXHIBIT_C", "source_name": "N.C. A&T Exhibit C: Current Site Data",
         "source_url": "", "source_year": "2024", "source_kind": "historical_workbook",
         "quality_notes": "Provided public procurement Excel; Demographics totals, not 2026 room inventory"},
        {"source_id": "SRC_RATES_2627", "source_name": "N.C. A&T housing rates 2026-27",
         "source_url": RATE_URL, "source_year": "2026", "source_kind": "public_rate_schedule",
         "quality_notes": "Per-semester room rates for Fall 2026/Spring 2027; availability not implied"},
    ] + [
        {"source_id": f"SRC_{b['building_id']}", "source_name": f"N.C. A&T {b['building_name']} hall profile",
         "source_url": b["profile_url"], "source_year": "2026", "source_kind": "public_hall_profile",
         "quality_notes": "Room arrangement and floor count only; synthetic rooms per floor"}
        for b in BUILDINGS
    ]
    room_idx = 0
    bed_idx = 0
    for spec in BUILDINGS:
        historic = public_properties[spec["property_code"]]
        dataset["buildings"].append({
            "building_id": spec["building_id"], "property_code": spec["property_code"],
            "building_name": spec["building_name"],
            "historical_living_style": historic["living_style"],
            "living_style_current": spec["living_style_current"],
            "eligible_group": spec["eligible_group"], "eligible_level": spec["eligible_level"],
            "published_floor_count": spec["floors_published"],
            "simulation_rooms_per_floor": rooms_per_floor,
            "profile_url": spec["profile_url"],
            "profile_source_id": f"SRC_{spec['building_id']}", "synthetic_inventory": "true",
        })
        choices = [rt for rt, _ in spec["rate_choices"]]
        for rt, amount in spec["rate_choices"]:
            dataset["housing_rates"].append({
                "housing_rate_id": f"RATE_{spec['building_id']}_{rt}",
                "building_id": spec["building_id"], "room_type_id": rt,
                "academic_year": ACADEMIC_YEAR, "semester_rate_usd": amount,
                "source_url": RATE_URL, "source_id": "SRC_RATES_2627",
                "provenance": "published_2026_27",
            })
        for floor_number in range(1, spec["floor_count_simulated"] + 1):
            floor_id = f"{spec['building_id']}_F{floor_number}"
            dataset["floors"].append({
                "floor_id": floor_id, "building_id": spec["building_id"],
                "floor_number": floor_number, "synthetic_inventory": "true",
            })
            for room_ordinal in range(1, rooms_per_floor + 1):
                # Guaranteed Double rooms on every floor; remaining types vary by hall.
                room_type = "double" if room_ordinal <= 3 else choices[(room_ordinal - 3) % len(choices)]
                room_idx += 1
                room_id = f"ROOM_{room_idx:04d}"
                dataset["rooms"].append({
                    "room_id": room_id, "floor_id": floor_id,
                    "room_number": f"{floor_number * 100 + room_ordinal}",
                    "room_type_id": room_type, "synthetic_inventory": "true",
                })
                for n in range(ROOM_CAPACITY[room_type]):
                    bed_idx += 1
                    dataset["beds"].append({
                        "bed_id": f"BED_{bed_idx:04d}", "room_id": room_id,
                        "bed_label": chr(65+n), "synthetic_inventory": "true",
                    })

    floor_by_id = {f["floor_id"]: f for f in dataset["floors"]}
    room_by_id = {r["room_id"]: r for r in dataset["rooms"]}
    building_by_id = {b["building_id"]: b for b in dataset["buildings"]}
    def build_for_bed(bed: dict) -> dict:
        return building_by_id[floor_by_id[room_by_id[bed["room_id"]]["floor_id"]]["building_id"]]

    # Force named vacancy scenarios to make tests and a final presentation repeatable.
    pride_doubles = [bed for bed in dataset["beds"] if
                     build_for_bed(bed)["building_id"] == "BLD_PRIDE"
                     and room_by_id[bed["room_id"]]["room_type_id"] == "double"]
    now_empty, future_opening, future_reserved = pride_doubles[:3]
    special = {b["bed_id"] for b in (now_empty, future_opening, future_reserved)}
    assignment_seq = 0
    resident_seq = 0

    def resident_for(bed: dict) -> dict:
        nonlocal resident_seq
        bld = build_for_bed(bed)
        resident_seq += 1
        elig = bld["eligible_group"] if bld["eligible_group"] != "coed" else rng.choice(("male", "female"))
        person = {"resident_id": f"RES_{resident_seq:04d}",
                  "display_name": f"Fictional Resident {resident_seq:04d}",
                  "eligibility_group": elig, "student_level": bld["eligible_level"],
                  "synthetic_record": "true"}
        dataset["residents"].append(person)
        return person

    def add_assignment(resident: dict, bed: dict, start: date, end: date) -> None:
        nonlocal assignment_seq
        assignment_seq += 1
        dataset["bed_assignments"].append({
            "assignment_id": f"ASG_{assignment_seq:04d}", "resident_id": resident["resident_id"],
            "bed_id": bed["bed_id"], "start_date": start.isoformat(),
            "end_date": end.isoformat(), "status": "confirmed", "synthetic_record": "true",
        })

    for bed in dataset["beds"]:
        if bed["bed_id"] == now_empty["bed_id"]:
            continue  # known vacant bed at demo reference date
        if bed["bed_id"] == future_opening["bed_id"]:
            add_assignment(resident_for(bed), bed, START_DATE, as_of + timedelta(days=18))
        elif bed["bed_id"] == future_reserved["bed_id"]:
            add_assignment(resident_for(bed), bed, as_of + timedelta(days=6), END_DATE)
        elif rng.random() < 0.77:
            # Some assignments end soon, producing time-aware vacancy signals.
            end = as_of + timedelta(days=rng.choice((7, 14, 30))) if rng.random() < 0.17 else END_DATE
            add_assignment(resident_for(bed), bed, START_DATE, end)

    # Every floor except selected gaps gets an effective-dated RA assignment.
    gaps = {"BLD_PRIDE_F2", "BLD_COOPER_F3"}
    ra_idx = 0
    for floor in dataset["floors"]:
        if floor["floor_id"] in gaps:
            continue
        ra_idx += 1
        staff_id = f"RA_{ra_idx:03d}"
        dataset["staff"].append({
            "staff_id": staff_id, "display_name": f"Fictional RA {ra_idx:03d}",
            "role": "RA", "synthetic_record": "true",
        })
        dataset["staff_floor_assignments"].append({
            "staff_floor_assignment_id": f"SFA_{ra_idx:03d}", "staff_id": staff_id,
            "floor_id": floor["floor_id"], "start_date": START_DATE.isoformat(),
            "end_date": END_DATE.isoformat(), "status": "active", "synthetic_record": "true",
        })

    # Requests must refer to existing, currently housed demo residents.
    current_assigned_ids = {a["resident_id"] for a in dataset["bed_assignments"]
                            if parse_day(a["start_date"]) <= as_of < parse_day(a["end_date"])}
    residents_by_id = {r["resident_id"]: r for r in dataset["residents"]}
    residents_of_blair = [a["resident_id"] for a in dataset["bed_assignments"]
                         if a["resident_id"] in current_assigned_ids and
                         build_for_bed(next(b for b in dataset["beds"] if b["bed_id"] == a["bed_id"]))["building_id"] == "BLD_BLAIR"]
    if len(residents_of_blair) < 4:
        raise ValueError("Insufficient assigned Blair residents for test scenarios")
    req_idx = 0
    pref_idx = 0
    used_residents = set()

    def new_request(resident_id: str, day: date, room_type_id: str,
                    ceiling: str, rank_buildings: tuple[str, ...],
                    scenario: str, preferred_floor: str = "") -> None:
        nonlocal req_idx, pref_idx
        if resident_id in used_residents:
            raise ValueError("One pending request per resident in this demo")
        used_residents.add(resident_id)
        req_idx += 1
        req_id = f"REQ_{req_idx:04d}"
        dataset["room_change_requests"].append({
            "request_id": req_id, "resident_id": resident_id,
            "created_date": (as_of - timedelta(days=2)).isoformat(),
            "desired_move_date": day.isoformat(), "room_type_id": room_type_id,
            "max_semester_price_usd": ceiling, "preferred_floor_number": preferred_floor,
            "status": "pending", "demo_scenario": scenario, "synthetic_record": "true",
        })
        for rank, bid in enumerate(rank_buildings, start=1):
            pref_idx += 1
            dataset["request_preferences"].append({
                "preference_id": f"PREF_{pref_idx:04d}", "request_id": req_id,
                "building_id": bid, "rank": rank, "synthetic_record": "true",
            })

    new_request(residents_of_blair[0], as_of, "double", "3300.00", ("BLD_PRIDE",), "vacant_now")
    new_request(residents_of_blair[1], as_of + timedelta(days=20), "double", "3300.00", ("BLD_PRIDE",), "future_opening")
    new_request(residents_of_blair[2], as_of, "private", "2000.00", ("BLD_PRIDE",), "budget_blocked")
    new_request(residents_of_blair[3], as_of, "double", "3300.00", ("BLD_PRIDE",), "floor_unavailable", "99")

    # Additional requests introduce diverse preferences and matching outcomes.
    optional = [r for r in dataset["residents"] if r["resident_id"] in current_assigned_ids
                and r["resident_id"] not in used_residents]
    rng.shuffle(optional)
    for person in optional[:min(12, len(optional))]:
        choices = [b for b in dataset["buildings"] if valid_housing_for_resident(b, person)]
        chosen = rng.choice(choices)
        available_types = [rate for rate in dataset["housing_rates"] if rate["building_id"] == chosen["building_id"]]
        rate = rng.choice(available_types)
        cap = float(rate["semester_rate_usd"]) + rng.choice((-400, 0, 100, 500))
        new_request(person["resident_id"], as_of + timedelta(days=rng.choice((0, 7, 14, 30))),
                    rate["room_type_id"], f"{max(0.0, cap):.2f}", (chosen["building_id"],), "random_demo")

    validate_dataset(dataset)
    return dataset


def validate_dataset(data: dict[str, list[dict]]) -> None:
    """Raise ValueError if generated relations, dates, or assignments are invalid."""
    pk = {
        "source_register": "source_id", "buildings": "building_id",
        "floors": "floor_id", "room_types": "room_type_id",
        "housing_rates": "housing_rate_id", "rooms": "room_id", "beds": "bed_id",
        "residents": "resident_id", "bed_assignments": "assignment_id", "staff": "staff_id",
        "staff_floor_assignments": "staff_floor_assignment_id",
        "room_change_requests": "request_id", "request_preferences": "preference_id",
    }
    ids = {}
    for table, key in pk.items():
        values = [row[key] for row in data[table]]
        if not values or len(set(values)) != len(values) or any(not x for x in values):
            raise ValueError(f"Invalid/duplicate primary key in {table}.{key}")
        ids[table] = set(values)

    def fk(table: str, col: str, target: str) -> None:
        if any(row[col] not in ids[target] for row in data[table]):
            raise ValueError(f"Broken foreign key {table}.{col} -> {target}")

    for table, col, target in (
        ("buildings", "profile_source_id", "source_register"),
        ("housing_rates", "source_id", "source_register"),
        ("floors", "building_id", "buildings"),
        ("housing_rates", "building_id", "buildings"),
        ("housing_rates", "room_type_id", "room_types"),
        ("rooms", "floor_id", "floors"), ("rooms", "room_type_id", "room_types"),
        ("beds", "room_id", "rooms"),
        ("bed_assignments", "resident_id", "residents"),
        ("bed_assignments", "bed_id", "beds"),
        ("staff_floor_assignments", "staff_id", "staff"),
        ("staff_floor_assignments", "floor_id", "floors"),
        ("room_change_requests", "resident_id", "residents"),
        ("room_change_requests", "room_type_id", "room_types"),
        ("request_preferences", "request_id", "room_change_requests"),
        ("request_preferences", "building_id", "buildings"),
    ):
        fk(table, col, target)

    floor_by_id = {f["floor_id"]: f for f in data["floors"]}
    room_by_id = {r["room_id"]: r for r in data["rooms"]}
    bed_by_id = {b["bed_id"]: b for b in data["beds"]}
    building_by_id = {b["building_id"]: b for b in data["buildings"]}
    resident_by_id = {r["resident_id"]: r for r in data["residents"]}
    rates = {(r["building_id"], r["room_type_id"]) for r in data["housing_rates"]}
    if len(rates) != len(data["housing_rates"]):
        raise ValueError("Duplicate building/room-type housing rate")
    for r in data["rooms"]:
        building_id = floor_by_id[r["floor_id"]]["building_id"]
        if (building_id, r["room_type_id"]) not in rates:
            raise ValueError("Room type has no published housing rate for its building")
    room_labels = [(x["floor_id"], x["room_number"]) for x in data["rooms"]]
    if len(room_labels) != len(set(room_labels)):
        raise ValueError("Duplicate room number on a floor")
    bed_labels = [(x["room_id"], x["bed_label"]) for x in data["beds"]]
    if len(bed_labels) != len(set(bed_labels)):
        raise ValueError("Duplicate bed label in room")
    count_by_room = defaultdict(int)
    for b in data["beds"]:
        count_by_room[b["room_id"]] += 1
    for room in data["rooms"]:
        if count_by_room[room["room_id"]] != ROOM_CAPACITY[room["room_type_id"]]:
            raise ValueError("Room/bed capacity mismatch")

    intervals: dict[tuple[str, str], list[tuple[date, date]]] = defaultdict(list)
    for a in data["bed_assignments"]:
        start, end = parse_day(a["start_date"]), parse_day(a["end_date"])
        if start >= end or a["status"] != "confirmed":
            raise ValueError("Invalid assignment date/status")
        bed = bed_by_id[a["bed_id"]]
        room = room_by_id[bed["room_id"]]
        building = building_by_id[floor_by_id[room["floor_id"]]["building_id"]]
        if not valid_housing_for_resident(building, resident_by_id[a["resident_id"]]):
            raise ValueError("Resident violates hall eligibility rule")
        intervals[("bed", a["bed_id"])].append((start, end))
        intervals[("resident", a["resident_id"])].append((start, end))
    for (kind, identifier), spans in intervals.items():
        spans.sort()
        if any(prev[1] > curr[0] for prev, curr in zip(spans, spans[1:])):
            raise ValueError(f"Overlapping {kind} assignments for {identifier}")

    staff_spans = defaultdict(list)
    for a in data["staff_floor_assignments"]:
        start, end = parse_day(a["start_date"]), parse_day(a["end_date"])
        if start >= end:
            raise ValueError("Invalid RA coverage interval")
        staff_spans[a["staff_id"]].append((start, end))
    for staff_id, spans in staff_spans.items():
        spans.sort()
        if any(prev[1] > curr[0] for prev, curr in zip(spans, spans[1:])):
            raise ValueError(f"RA {staff_id} assigned to overlapping floor coverage")

    rank_per_request = defaultdict(set)
    pref_count = defaultdict(int)
    for p in data["request_preferences"]:
        rank = int(p["rank"])
        if rank <= 0 or rank in rank_per_request[p["request_id"]]:
            raise ValueError("Duplicate or invalid request preference rank")
        rank_per_request[p["request_id"]].add(rank)
        pref_count[p["request_id"]] += 1
    pending_by_resident = defaultdict(int)
    for r in data["room_change_requests"]:
        if r["status"] not in ("pending", "approved", "rejected", "cancelled"):
            raise ValueError("Unknown room-change request status")
        if parse_day(r["desired_move_date"]) < parse_day(r["created_date"]):
            raise ValueError("Move date cannot precede request creation")
        if float(r["max_semester_price_usd"]) < 0 or not pref_count[r["request_id"]]:
            raise ValueError("Invalid request price or missing building preference")
        if r["status"] == "pending":
            pending_by_resident[r["resident_id"]] += 1
    if any(count > 1 for count in pending_by_resident.values()):
        raise ValueError("Resident has multiple pending requests")


def save_dataset(data: dict[str, list[dict]], out: Path, *, seed: int, as_of: date,
                 rooms_per_floor: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for table, records in data.items():
        if not records:
            raise ValueError(f"Refusing to write empty table {table}")
        with (out / f"{table}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    manifest = {
        "dataset_kind": "fictional_operational_demo",
        "academic_year": ACADEMIC_YEAR,
        "as_of": as_of.isoformat(),
        "seed": seed,
        "rooms_per_floor": rooms_per_floor,
        "counts": {key: len(records) for key, records in data.items()},
        "source_scope": "Property names are linked to the public historical workbook; selected 2026-27 semester rates and floor counts from N.C. A&T websites.",
        "disclaimer": "Room inventory, bed placements, resident/staff people, assignments, request history, and RA coverage are entirely synthetic. Not actual housing records or forecasts.",
        "source_urls": [RATE_URL] + [b["profile_url"] for b in BUILDINGS],
        "date_intervals": "start_date inclusive, end_date exclusive",
        "scenario_definitions": {
            "vacant_now": "An eligible, affordable double in Pride is vacant on as_of.",
            "future_opening": "A Pride double assignment ends 18 days after as_of; intended move 20 days after.",
            "budget_blocked": "Private Pride room exceeds the synthetic request's price ceiling.",
            "floor_unavailable": "Floor preference 99 intentionally does not exist.",
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--properties", type=Path, default=DEFAULT_PROPERTIES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--as-of", type=date.fromisoformat, default=AS_OF)
    parser.add_argument("--rooms-per-floor", type=int, default=6)
    args = parser.parse_args()
    data = generate(read_properties(args.properties), seed=args.seed,
                    as_of=args.as_of, rooms_per_floor=args.rooms_per_floor)
    save_dataset(data, args.output_dir, seed=args.seed, as_of=args.as_of,
                 rooms_per_floor=args.rooms_per_floor)
    print("HousingOps synthetic scenario created (not actual university records):")
    for key, rows in data.items():
        print(f"  {key}: {len(rows)}")
    print(f"  output: {args.output_dir}")
    for r in data["room_change_requests"]:
        if r["demo_scenario"] != "random_demo":
            print(f"  {r['demo_scenario']}: {len(eligible_beds(data, r))} eligible beds at requested date")


if __name__ == "__main__":
    main()
