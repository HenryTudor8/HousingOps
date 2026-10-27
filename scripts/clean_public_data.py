"""Normalize public historical housing occupancy from the N.C. A&T Exhibit C workbook.

Run from the repository root:
    python scripts/clean_public_data.py

Inputs are public historical aggregates. They are NOT individual residents,
bed-level inventory, or confirmed present/future vacancies.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "data" / "raw" / "Project Data.xlsx"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed"
STYLES = {4: "Traditional", 5: "Suite", 6: "Apartment"}
OCCUPANCY_COLUMNS = range(7, 13)  # Excel columns H through M
TERM_PATTERN = re.compile(r"^(Fall|Spring|Summer)\s+(20\d{2})$", re.IGNORECASE)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def clean_occupancy(source: Path, output_dir: Path) -> None:
    """Read the Demographics section, normalize it, and validate published totals."""
    if not source.is_file():
        raise FileNotFoundError(
            f"Workbook not found: {source}\n"
            "Place the original 'Project Data.xlsx' in data/raw/ first."
        )

    sheet = pd.read_excel(source, sheet_name="Demographics", header=None)
    hall_markers = sheet.index[
        sheet.iloc[:, 1].astype(str).str.strip().eq("Residence Hall")
    ].tolist()
    if len(hall_markers) != 1:
        raise ValueError("Could not uniquely locate the Residence Hall header.")
    header_idx = hall_markers[0]
    term_header = sheet.iloc[header_idx + 1]

    term_info = []
    for col in OCCUPANCY_COLUMNS:
        label = str(term_header.iloc[col]).strip()
        match = TERM_PATTERN.fullmatch(label)
        if not match:
            raise ValueError(f"Unrecognized academic term at Excel column {col + 1}: {label!r}")
        season, year_text = match.groups()
        season = season.title()
        year = int(year_text)
        term_info.append(
            {
                "term_code": f"{year}_{season.lower()}",
                "term_name": f"{season} {year}",
                "calendar_year": year,
                "season": season,
            }
        )

    # The occupancy table has its published total in column G.
    total_matches = [
        idx
        for idx in range(header_idx + 2, len(sheet))
        if str(sheet.iloc[idx, 6]).strip().lower() == "total:"
    ]
    if len(total_matches) != 1:
        raise ValueError("Could not uniquely locate the historical occupancy total row.")
    total_idx = total_matches[0]

    properties = []
    observations = []
    for idx in range(header_idx + 2, total_idx):
        row = sheet.iloc[idx]
        if pd.isna(row.iloc[1]) or not str(row.iloc[1]).strip():
            continue

        property_name = str(row.iloc[1]).strip()
        property_code = slug(property_name)
        marked_styles = [
            style for col, style in STYLES.items()
            if str(row.iloc[col]).strip().upper() == "X"
        ]
        if len(marked_styles) != 1:
            raise ValueError(f"{property_name}: expected one marked living style, got {marked_styles}")

        properties.append(
            {
                "property_code": property_code,
                "property_name": property_name,
                "living_style": marked_styles[0],
                "meal_plan_required": str(row.iloc[2]).strip().upper() == "X",
            }
        )

        for col, term in zip(OCCUPANCY_COLUMNS, term_info):
            raw = row.iloc[col]
            if pd.isna(raw) or not isinstance(raw, (int, float)) or int(raw) != raw or raw < 0:
                raise ValueError(f"{property_name}, {term['term_name']}: invalid occupied-space count {raw!r}")
            observations.append(
                {
                    "property_code": property_code,
                    "term_code": term["term_code"],
                    "occupied_spaces": int(raw),
                    "source_file": source.name,
                    "source_sheet": "Demographics",
                }
            )

    properties_df = pd.DataFrame(properties)
    terms_df = pd.DataFrame(term_info)
    observations_df = pd.DataFrame(observations)

    if properties_df.empty or properties_df["property_code"].duplicated().any():
        raise ValueError("Property identifiers must be nonempty and unique.")
    if len(observations_df) != len(properties_df) * len(terms_df):
        raise ValueError("Each housing property must have one observation for each term.")

    for col, term in zip(OCCUPANCY_COLUMNS, term_info):
        published = sheet.iloc[total_idx, col]
        calculated = int(
            observations_df.loc[
                observations_df["term_code"] == term["term_code"], "occupied_spaces"
            ].sum()
        )
        if pd.isna(published) or calculated != int(published):
            raise ValueError(
                f"Totals do not match for {term['term_name']}: "
                f"calculated={calculated}, published={published}"
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    properties_df.to_csv(output_dir / "housing_properties.csv", index=False)
    terms_df.to_csv(output_dir / "academic_terms.csv", index=False)
    observations_df.to_csv(output_dir / "occupancy_observations.csv", index=False)

    print(f"Validated {len(properties_df)} properties, {len(terms_df)} terms, "
          f"and {len(observations_df)} historical occupancy observations.")
    for term in term_info:
        total = int(observations_df.loc[
            observations_df["term_code"] == term["term_code"], "occupied_spaces"
        ].sum())
        print(f"  {term['term_name']}: {total:,} occupied spaces")
    print(f"CSV files written to: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    clean_occupancy(args.input, args.output_dir)


if __name__ == "__main__":
    main()
