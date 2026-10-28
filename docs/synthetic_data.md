# HousingOps Synthetic Operational Data, Version 1

**Status:** Provisional canonical data contract. Developed for the October/November 2026 DSCI-D 532 Milestone 2 demonstration, before final PostgreSQL table/column mapping. No records describe actual 2026 residents, room assignments, RAs, or move requests.

## Relationship to the approved Milestone 1 proposal and ERD

This generator follows the three blocks in Figure 1 of the team's Milestone 1 proposal:

| Tentative ERD block | Data source and output | What it represents |
| --- | --- | --- |
| **Public/reference** | `housing_properties.csv`, `academic_terms.csv`, `occupancy_observations.csv` from `scripts/clean_public_data.py` | Public 2022–24 historical occupancy; **not synthetic** |
| **Public/reference** | `source_register.csv`, `room_types.csv`, `housing_rates.csv` | Public hall/price provenance; room-type vocabulary and semester rates |
| **Physical inventory** | `buildings.csv`, `floors.csv`, `rooms.csv`, `beds.csv` | Selected known hall names and documented number of floors; room counts, room numbers, beds, and allocations **synthetic** |
| **Operations/requests** | `residents.csv`, `bed_assignments.csv`, `staff.csv`, `staff_floor_assignments.csv`, `room_change_requests.csv`, `request_preferences.csv` | Entirely fictional residents, placements, RAs, coverage dates, requests, and ranked building preferences |

`Building.property_code` connects the simulated building to the separately imported historical `HousingProperty.property_code`. That does **not** mean historical counts describe current room availability. The original model's `RequestPreference` is implemented as rows with one building ID and one explicit rank, rather than a comma-separated preference string. The selected `RoomType` and `HousingRate` reference tables are separate from rooms, consistent with the tentative normalization.

**Provisional names are not SQL table definitions.** If the implemented ERD uses integer PKs, different naming, new lookups, etc., adjust the future PostgreSQL loader/adapter. Keep generation and validation behavior intact.

## Source information vs demo assumptions

1. Source workbook: N.C. A&T **Exhibit C: Current Site Data** (2024), `Demographics` tab, processed by `clean_public_data.py`. Includes 25 named properties and six term totals. This is the *real-data foundation* approved for the project.
2. [Official residence hall directory](https://www.ncat.edu/campus-life/student-affairs/departments/housing-and-residence-life/housing/residence-halls/index.php) and hall profiles provide selected names, room styles, and floor counts.
3. [Official Fall 2026/Spring 2027 housing rates](https://www.ncat.edu/campus-life/student-affairs/departments/housing-and-residence-life/resident-resources/cost-for-living-on-campus.php) provide **per-semester rates**. We do not assume they apply to the 2022–24 historical occupancy observations.

The V1 simulated subset uses **Cooper Hall (4 floors), Holland Hall (3), Blair Hall (3), Pride Hall (3)**. Each floor is deliberately generated with **six fictional rooms**, yielding an **illustrative partial inventory**; there is no assertion that N.C. A&T has six rooms per floor or that our synthetic bed count equals its actual capacity.

| Hall | Published current room style | Demonstration price (USD/semester) | Source |
| --- | --- | --- | --- |
| Cooper Hall | Double | 2,554.50 | Official Fall 2026/Spring 2027 rate page |
| Holland Hall | Double | 2,554.50 | Same |
| Blair Hall (Aggie Village) | Double / Double Deluxe / Single / Private | 3,208 / 3,283 / 3,358 / 3,508 | Same |
| Pride Hall | Double / Single / Private | 3,221.50 / 3,539 / 3,693 | Same |

**Known reconciliation issue:** The historical Excel `Demographics` sheet marks **Blair Hall as Traditional**, while the present-day official Aggie Village pages describe Blair as **suite-style**. We preserve the original classification in `historical_living_style` and current classification in `living_style_current`. A real ETL report should record this disagreement rather than overwrite history. Official pages also conflict in some published building capacities (e.g. Cooper); **we don't feed those disputed capacities into the simulation**.

**Demo-specific simplifications:** `eligibility_group` (`male`, `female`, `coed`) and `student_level` (`first_year`, `upperclass`) are simplified scenario rules based on published hall descriptions, not a comprehensive institutional housing eligibility engine. All people are labeled `Fictional Resident XXXX` or `Fictional RA XXX` and are not actual persons. Their gender/level buckets are artificial eligibility inputs, not real demographic claims. Room configurations are invented even where real styles are used; we do not claim actual bed locations or building occupancy. Rates are reference facts rather than invented synthetic prices.

## Reproduce the outputs

Run from the repository root (use the `.venv` interpreter if you haven't activated it):

```powershell
# First generate the clean *public* files from the local workbook.
.\.venv\Scripts\python.exe scripts\clean_public_data.py

# Then generate the fictional operations for an explicit scenario date.
.\.venv\Scripts\python.exe scripts\generate_synthetic.py --seed 532 --as-of 2026-10-28

# Run independent tests (no workbook needed for the synthetic tests).
.\.venv\Scripts\python.exe -m pytest tests\test_synthetic_data.py -v
```

The generator reads `data/processed/housing_properties.csv` (requires exact matching source building names), then writes **13 CSV files and one JSON manifest** to `data/processed/synthetic/`. They are Git-ignored; use the script to reproduce them on any machine. The manifest captures seed, as-of date, counts, source links, and scenario descriptions.

Options include `--properties`, `--output-dir`, `--seed`, `--as-of` (ISO YYYY-MM-DD), and `--rooms-per-floor` (minimum 3). Default values are seed **532**, as-of **2026-10-28**, and six fictional rooms per floor. Interval convention: `start_date` is inclusive and `end_date` is exclusive, `[start_date, end_date)`.

Changing seed may change the number of assigned residents/requests, but required edge scenarios and integrity rules remain present. Identical inputs and seed produce identical byte-for-byte CSV/JSON outputs.

## Operational scenario design

- **Vacant now:** An intentionally empty Pride double bed is available on the scenario date and a fictional Blair resident requests it within budget.
- **Future opening:** One Pride double assignment ends 18 days after the reference date; an eligible request seeks to move 20 days afterward. These are confirmed **fictional** assignment dates, not a statistical prediction.
- **Future reservation:** Another Pride double bed acquires a future assignment six days after the reference date, so 'vacant today' does not imply 'vacant forever'.
- **Budget blocked:** A requested private Pride room with a $2,000 semester ceiling is invalid as a match against the published price.
- **Floor unavailable:** A request for floor 99 in Pride has no physical match.
- **RA coverage gaps:** Pride floor 2 and Cooper floor 3 are intentionally uncovered by a fictional RA assignment on the scenario date.
- **Additional requests:** Twelve seeded synthetic requests vary move dates, affordability, and room preferences.

`eligible_beds()` is a **small Python preview/test helper**. It filters beds available **on the desired move date**, matches selected buildings/room type/ceiling/floor and simple hall eligibility, then ranks by building preference and price. It does **not** establish full-stay availability, hold a bed, mutate any booking, or substitute for the final SQL Mobility Engine and transactional room changes. Final SQL must test the entire intended occupancy interval and use safe transactions.

## Data integrity and two invalid examples for Milestone 2

The `validate_dataset()` function checks nonempty unique keys, foreign-key references, valid building-specific room/rate combinations, room and bed uniqueness/capacity, date ranges, allowed hall eligibility, effective-dated RA/staff coverage, unique preference ranks, and no resident/bed double booking.

1. Add a new **confirmed** bed assignment that overlaps an existing confirmed assignment for the same `bed_id`: the validator rejects it with `Overlapping bed assignments`.
2. Add a bed whose `room_id` does not exist in the rooms table: the validator rejects it with `Broken foreign key`.

Other tests reject a resident assigned overlapping beds, an unavailable room type in a hall, and invalid/missing request preferences.

**Crucial limitation:** These are *pre-load application checks*. For Milestone 2, Vishwambhara and Sanchit must also demonstrate that the actual PostgreSQL database enforces declared primary keys/foreign keys/uniqueness and appropriate overlap protection. Passing Python tests alone does not prove database enforcement or CRUD.

## PostgreSQL integration contract and next steps

Agreements to establish before writing the final loader:

- Naming/PK conventions (`BLD_COOPER` IDs vs generated integer keys).
- Normalize `room_types`, `housing_rates`, and source metadata vs inline attributes.
- Decide which referential constraints are SQL `FOREIGN KEY` vs application validation, and which date-overlap rules use PostgreSQL exclusion constraints/transactions.
- Define effective-dated room occupancy and RA coverage, the intended duration of a new assignment, and the approved-move transaction design.
- Determine whether the final ERD includes an explicit rate-period dimension.

A future `scripts/load_database.py` should handle mapping these canonical CSVs into the agreed implemented SQL schema. It must load public tables separately, then synthetic operational tables in FK-safe order. Both teammates should run and explain the SQL load and queries.

## AI-use acknowledgement (review before using in submissions)

ChatGPT (OpenAI) assisted with the draft generator, documentation, and test scaffolding. The team must review the program, verify public rate inputs and source links, explain its design, validate the generated counts, and revise the adapter to match the implemented PostgreSQL schema. The generated scripts are not a substitute for authors' understanding, tests, or independent database design.