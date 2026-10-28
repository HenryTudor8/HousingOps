
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data" / "processed"

EXPECTED_TOTALS = {
    "2022_fall": 5873,
    "2023_spring": 5732,
    "2023_summer": 452,
    "2023_fall": 5705,
    "2024_spring": 5702,
    "2024_summer": 257,
}


def load_data():
    properties = pd.read_csv(DATA / "housing_properties.csv")
    terms = pd.read_csv(DATA / "academic_terms.csv")
    observations = pd.read_csv(DATA / "occupancy_observations.csv")
    return properties, terms, observations


def test_record_counts():
    properties, terms, observations = load_data()
    assert len(properties) == 25
    assert len(terms) == 6
    assert len(observations) == 150


def test_unique_records():
    properties, terms, observations = load_data()
    assert properties["property_code"].is_unique
    assert terms["term_code"].is_unique
    assert not observations.duplicated(
        subset=["property_code", "term_code"]
    ).any()


def test_foreign_key_references():
    properties, terms, observations = load_data()

    assert set(observations["property_code"]).issubset(
        set(properties["property_code"])
    )
    assert set(observations["term_code"]).issubset(
        set(terms["term_code"])
    )


def test_nonnegative_occupancy():
    _, _, observations = load_data()
    assert observations["occupied_spaces"].notna().all()
    assert (observations["occupied_spaces"] >= 0).all()


def test_historical_totals():
    _, _, observations = load_data()

    actual = observations.groupby("term_code")[
        "occupied_spaces"
    ].sum().to_dict()

    assert actual == EXPECTED_TOTALS
