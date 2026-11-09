# Data source and provenance

## Public source (historical, observed)

- **Institution:** North Carolina Agricultural & Technical State University (N.C. A&T).
- **File:** `Project Data.xlsx` (Exhibit C: Current Site Data).
- **Worksheet:** `Demographics`.
- **Relevant section:** "Residence Hall", columns B–M, 25 property rows.
- **Term headers:** Fall 2022, Spring 2023, Summer 2023, Fall 2023, Spring 2024, Summer 2024.
- **Measurements:** Aggregate occupied spaces per named property and term. These counts are **not** occupancy rates, bed-level availability, or current-year assignments.
- **Publication warning:** "Numbers are historical and not a guarantee of future population."

The workbook includes other dining/services sheets. In particular, **the `Staffing` worksheet is not an RA staffing roster**; it must not be used to claim residence-assistant coverage.

## Transformation

Run `python scripts/clean_public_data.py` after placing the original workbook in `data/raw/Project Data.xlsx`.

The script normalizes a wide source table into:

1. `housing_properties.csv` (one row per property).
2. `academic_terms.csv` (six term records).
3. `occupancy_observations.csv` (one row per property/term).

The ETL strips incidental trailing spaces from names; marks one of Traditional, Suite, Apartment; records the meal-plan requirement; preserves zero summer occupancy records; and **validates each term's observed property sum against the total printed in the source**. All CSV outputs are generated into `data/processed/`, which is ignored by Git.

### Source totals expected for verification

| Term | Occupied spaces |
| --- | ---: |
| Fall 2022 | 5,873 |
| Spring 2023 | 5,732 |
| Summer 2023 | 452 |
| Fall 2023 | 5,705 |
| Spring 2024 | 5,702 |
| Summer 2024 | 257 |

A property can have more occupied spaces in a historical term than a different document's present-day capacity figure. We must reconcile source versions and dates before treating those figures as comparable.

## Implemented synthetic operational data

The 2026-27 operating layer **is implemented** as reproducibly generated fictional records using §scripts/generate_synthetic.py§ (seed 532, baseline 2026-10-28). It includes four halls, 13 floors, 78 fictional rooms, 144 beds, 111 residents, 16 pending room changes, dated assignments, and RA-floor staffing. §scripts/load_database.py§ loads these into the normalized PostgreSQL schema. They must never be represented as N.C. A&T's actual residents or staffing.

## Privacy, security, and repository use

The `data/raw/` and `data/processed/` folders are Git-ignored (apart from their `.gitkeep` files). The source workbook should be stored locally rather than automatically committed. Never commit personally identifiable student information, `.env`, connection strings with real passwords, or private records.

## Supplemental public references

- [N.C. A&T official residence hall directory](https://www.ncat.edu/campus-life/student-affairs/departments/housing-and-residence-life/housing/residence-halls/index.php): selected building names and published characteristics.
- [N.C. A&T Fall 2026/Spring 2027 housing costs](https://www.ncat.edu/campus-life/student-affairs/departments/housing-and-residence-life/resident-resources/cost-for-living-on-campus.php): room-type semester rates, kept distinct from historical occupancy.

**Known reconciliation issue:** The source `Demographics` sheet classifies Blair Hall as Traditional, while current Aggie Village descriptions characterize it as suite-style. The model preserves historical and current classifications separately. No 2026 room capacities or actual current occupancy are inferred from 2022–24 property totals.

**Workbook availability:** The course-provided `Project Data.xlsx` is not checked into Git and no stable public direct download of that exact workbook has been verified. For full grading reproducibility, the team needs to provide instructors an accessible, approved copy or exact source URL. [Local data instructions](../data/README.md) explain the expected path.
