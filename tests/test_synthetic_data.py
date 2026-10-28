"""Independent unit/integrity tests for HousingOps' fictional operational layer."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from scripts.generate_synthetic import (
    AS_OF,
    BUILDINGS,
    bed_is_available,
    eligible_beds,
    generate,
    read_properties,
    save_dataset,
    validate_dataset,
)


@pytest.fixture
def properties(tmp_path: Path):
    # A minimal stand-in for the four hall rows from the public ETL. Tests do
    # not require the external Excel workbook or check in source data.
    file = tmp_path / "housing_properties.csv"
    with file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["property_code", "property_name", "living_style"])
        writer.writeheader()
        for spec in BUILDINGS:
            writer.writerow({
                "property_code": spec["property_code"],
                "property_name": spec["building_name"],
                "living_style": "Traditional" if spec["property_code"] == "blair_hall"
                else spec["living_style_current"],
            })
    return read_properties(file)


@pytest.fixture
def data(properties):
    return generate(properties, seed=532, as_of=AS_OF)


def test_all_tentative_erd_operational_entities_present(data):
    assert set(data) == {
        "source_register", "buildings", "floors", "room_types", "housing_rates", "rooms", "beds",
        "residents", "bed_assignments", "staff", "staff_floor_assignments",
        "room_change_requests", "request_preferences",
    }
    assert len(data["buildings"]) == 4
    assert len(data["floors"]) == 13
    assert len(data["beds"]) > len(data["rooms"])
    assert len(data["room_change_requests"]) >= 4


def test_valid_relationships_and_no_assignment_overlaps(data):
    validate_dataset(data)  # Checks keys, foreign keys, room rates, dates, and overlaps.


def test_same_seed_same_output(properties):
    assert generate(properties, seed=532, as_of=AS_OF) == generate(properties, seed=532, as_of=AS_OF)
    assert generate(properties, seed=533, as_of=AS_OF) != generate(properties, seed=532, as_of=AS_OF)


def test_no_double_booking_is_rejected(data):
    bad = copy.deepcopy(data)
    original = bad["bed_assignments"][0]
    collision = dict(original, assignment_id="ASG_DUPLICATE", resident_id=bad["bed_assignments"][1]["resident_id"])
    bad["bed_assignments"].append(collision)
    with pytest.raises(ValueError, match="Overlapping bed assignments"):
        validate_dataset(bad)


def test_duplicate_resident_assignments_are_rejected(data):
    bad = copy.deepcopy(data)
    original = bad["bed_assignments"][0]
    second = bad["bed_assignments"][1]
    bad["bed_assignments"].append(dict(original,
        assignment_id="ASG_DUPLICATE", bed_id=second["bed_id"]))
    with pytest.raises(ValueError, match="Overlapping resident assignments"):
        validate_dataset(bad)


def test_invalid_foreign_key_is_rejected(data):
    bad = copy.deepcopy(data)
    bad["beds"][0]["room_id"] = "ROOM_DOES_NOT_EXIST"
    with pytest.raises(ValueError, match="Broken foreign key"):
        validate_dataset(bad)


def test_invalid_housing_rate_is_rejected(data):
    bad = copy.deepcopy(data)
    bad["rooms"][0]["room_type_id"] = "private"  # Cooper offers double only.
    with pytest.raises(ValueError, match="no published housing rate"):
        validate_dataset(bad)


def test_requests_have_ranked_building_preferences(data):
    preference_by_request = {}
    for p in data["request_preferences"]:
        preference_by_request.setdefault(p["request_id"], []).append(int(p["rank"]))
    assert all(sorted(preference_by_request[r["request_id"]]) == [1]
               for r in data["room_change_requests"])
    assert all(r["synthetic_record"] == "true" for r in data["residents"])


def test_scenario_matching_results(data):
    requests = {r["demo_scenario"]: r for r in data["room_change_requests"]
                if r["demo_scenario"] != "random_demo"}
    assert len(eligible_beds(data, requests["vacant_now"])) > 0
    assert len(eligible_beds(data, requests["future_opening"])) > 0
    assert eligible_beds(data, requests["budget_blocked"]) == []
    assert eligible_beds(data, requests["floor_unavailable"]) == []


def test_early_occupied_bed_becomes_vacant(data):
    pride_ids = {b["building_id"] for b in data["buildings"] if b["building_name"] == "Pride Hall"}
    floor_by_id = {x["floor_id"]: x for x in data["floors"]}
    room_by_id = {x["room_id"]: x for x in data["rooms"]}
    occupied_then_open = [a for a in data["bed_assignments"]
                          if a["end_date"] == (AS_OF + timedelta(days=18)).isoformat()]
    assert occupied_then_open
    for a in occupied_then_open:
        bed = next(b for b in data["beds"] if b["bed_id"] == a["bed_id"])
        room = room_by_id[bed["room_id"]]
        building_id = floor_by_id[room["floor_id"]]["building_id"]
        if building_id in pride_ids:
            assert not bed_is_available(data, a["bed_id"], AS_OF)
            assert bed_is_available(data, a["bed_id"], AS_OF + timedelta(days=18))
            break
    else:
        pytest.fail("Expected a future-opening Pride bed")


def test_ra_gaps_exist(data):
    covered = {a["floor_id"] for a in data["staff_floor_assignments"]
               if a["start_date"] <= AS_OF.isoformat() < a["end_date"]}
    missing = {f["floor_id"] for f in data["floors"]} - covered
    assert {"BLD_PRIDE_F2", "BLD_COOPER_F3"} == missing


def test_csv_and_manifest_reproducibility(data, tmp_path):
    a = tmp_path / "first"
    b = tmp_path / "second"
    save_dataset(data, a, seed=532, as_of=AS_OF, rooms_per_floor=6)
    save_dataset(data, b, seed=532, as_of=AS_OF, rooms_per_floor=6)
    left = sorted(p.name for p in a.iterdir())
    assert left == sorted(p.name for p in b.iterdir())
    for name in left:
        assert (a / name).read_bytes() == (b / name).read_bytes()
    manifest = json.loads((a / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_kind"] == "fictional_operational_demo"
    assert manifest["counts"]["beds"] == len(data["beds"])


def test_source_mismatch_is_rejected(tmp_path):
    file = tmp_path / "properties.csv"
    file.write_text("property_code,property_name,living_style\ncooper_hall,Wrong Hall,Traditional\n")
    with pytest.raises(ValueError, match="not found"):
        read_properties(file)
