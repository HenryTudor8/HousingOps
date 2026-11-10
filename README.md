# HousingOps

**DSCI-D 532 | Fall 2026 | Sanchit Kumar and Viswambhara Chinmaye Palaparthi**

HousingOps is a PostgreSQL-based demonstration of university housing operations. It supports date-aware bed availability, Resident Assistant (RA) coverage checks, ranked room-change recommendations, and historical housing occupancy analysis. The first read-only Streamlit dashboard prototype is now on SanBranch.

**Milestone 2 status:** Implemented database with 16 PostgreSQL tables, a reproducible Python data pipeline, SQL queries, CRUD demonstrations, and integrity tests. A read-only Streamlit prototype was added after Milestone 2, but still requires local Neon/UI validation. Final project target: December 13, 2026.

## What is real and what is simulated?

- **Public historical data:** 25 N.C. A&T housing properties, 6 terms (Fall 2022 to Summer 2024), and 150 occupied-space observations from `Project Data.xlsx`, worksheet `Demographics`. These are **occupied-space counts**, not percentages, current vacancies, or resident-level data.
- **2026–27 illustrative operating data:** Reproducibly generated **fictional** room inventory, residents, assignments, RA floor rosters, and move requests. Default seed `532` and reference date `2026-10-28`. The example includes 4 halls, 13 floors, 78 rooms, 144 beds, 111 fictional residents, and 16 pending change requests. It does **not** represent actual university occupancy.
- **Supplemental published references:** Official building profiles, room styles, and housing rates, with source links and reconciliation notes in [data sources](docs/data_sources.md) and [synthetic methodology](docs/synthetic_data.md).

## Repository guide

| Path | Purpose |
| --- | --- |
| [`sql/`](sql/README.md) | Schema, verification, four application-query scripts, CRUD and invalid-data tests |
| [`scripts/`](scripts/README.md) | Historical cleaning, seeded synthetic data generation, and PostgreSQL loading |
| [`tests/`](tests/README.md) | ETL and synthetic-data validation tests |
| [`docs/schema_erd.md`](docs/schema_erd.md) | Implemented 16-table ERD, keys, and cardinalities |
| [`docs/data_sources.md`](docs/data_sources.md) | Public-data provenance and historical totals |
| [`docs/synthetic_data.md`](docs/synthetic_data.md) | Synthetic rules, source limitations, and test scenarios |
| [`docs/evidence/`](docs/evidence/README.md) | Exported query results and Neon screenshots |
| [`app/`](app/README.md) | Read-only Streamlit dashboard prototype and setup |
| [`data/`](data/README.md) | Local source workbook and reproducibly generated CSV locations |
| [`docs/project_roadmap.md`](docs/project_roadmap.md) | Post-Milestone 2 feature roadmap and current prototype status |

## Prerequisites

- Python **3.11**, standard Windows distribution (other compatible Python versions may work but were not the tested setup).
- PostgreSQL **17 or newer**, local or hosted (tested with **Neon PostgreSQL 18**).
- Access to the original **`Project Data.xlsx`** workbook used for Milestone 1. This workbook is *not* committed to this repository; see [data instructions](data/README.md).
- A PostgreSQL connection URL with CREATE privileges, stored locally in `.env`.

## Reproduce the database on Windows (PowerShell)

Run all commands from the cloned HousingOps root folder.

**1. Install dependencies**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**2. Prepare public data**

Obtain the course-approved N.C. A&T workbook and save it as `data/raw/Project Data.xlsx`. Then:

```powershell
.\.venv\Scripts\python.exe scripts\clean_public_data.py
```

Expected: 25 properties, 6 terms, 150 observations; term totals 5,873 / 5,732 / 452 / 5,705 / 5,702 / 257 in chronological order.

**3. Generate fictional operational data**

```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic.py --seed 532 --as-of 2026-10-28
.\.venv\Scripts\python.exe -m pytest tests\test_public_data.py tests\test_synthetic_data.py -v
```

Expected: 13 synthetic CSVs plus a JSON manifest in `data/processed/synthetic/`; all pytest checks should pass.

**4. Create a fresh PostgreSQL schema**

On an **empty** PostgreSQL database, execute [`sql/01_schema.sql`](sql/01_schema.sql) in the Neon SQL Editor or a PostgreSQL client, followed by [`sql/01_verify_schema.sql`](sql/01_verify_schema.sql). This creates the 16 normalized tables, relationships, checks, and exclusion constraints. Do **not** use it as a migration script on a populated database.

**5. Configure the database connection privately**

Copy `.env.example` to `.env` and replace its placeholder with **your own** PostgreSQL URL:

```powershell
Copy-Item .env.example .env
```

Never commit `.env` or share a URL containing a password. The template itself contains no live credentials.

**6. Load and verify**

```powershell
.\.venv\Scripts\python.exe scripts\load_database.py
```

The loader checks all CSVs and relationships, verifies column compatibility, requires all destination tables to be empty, and inserts the 16 datasets **within one transaction**. Successful completion prints `Success: 16 tables loaded and verified. Transaction committed.` To repeat the import, use another **empty** database or Neon development branch. Do not rerun the loader against the already populated database.

## Run the application queries

Run each statement within a multi-query file **separately** in the SQL Editor.

| Script | Question answered | Expected demonstration |
| --- | --- | --- |
| [`01_ra_coverage.sql`](sql/01_ra_coverage.sql) | Which floors lack active RAs on a specified date? | Cooper floor 3; Pride floor 2 |
| [`02_bed_availability.sql`](sql/02_bed_availability.sql) | Which beds are free today, +7, +14, +30 days, or for an entire stay? | Snapshot totals: 34, 39, 45, 49 |
| [`03_room_change_matching.sql`](sql/03_room_change_matching.sql) | Which available beds satisfy a request's preferences and budget? | `REQ_0001` / 2 / 3 / 4 yield 7 / 10 / 0 / 0 complete-stay matches |
| [`04_historical_occupancy.sql`](sql/04_historical_occupancy.sql) | How do public occupied-space totals vary by property and term? | Six source totals; 150 detailed observations |

- [`05_crud_demo.sql`](sql/05_crud_demo.sql): Execute numbered sections separately. Creates a **fictional test request** and ranked preference, reads them, updates `draft / $3,500` to `pending / $3,900`, then deletes both safely.
- [`06_integrity_tests.sql`](sql/06_integrity_tests.sql): Execute each invalid insert separately; **SQLSTATE 23503** (bad foreign key) and **23P01** (overlapping confirmed assignment) are the expected rejections, not failures of the project.
- [`docs/evidence/`](docs/evidence/README.md) contains representative outputs and screenshots from the Neon demonstration. SQL and Python source files, not screenshots alone, are the reproducible implementation.

## Database design and limitations

The normalized model separates properties, terms, observations, buildings, floors, rooms, beds, rates, residents, dated assignments, RA staffing, and ranked room-change preferences. Half-open date intervals `[start_date, end_date)` allow sequential occupancy but reject overlapping confirmed assignments for the same bed or resident using PostgreSQL GiST exclusion constraints.

Availability at one point in time does **not** guarantee full-stay availability. The room-change SQL checks the entire proposed stay ending `2027-05-15` (exclusive). Matching queries make recommendations only; they do not assign beds. A final application must implement move approval as an atomic database transaction and enforce appropriate authorization.

No real student names, housing assignments, or RA rosters are included. Synthetic inventory is an intentionally partial demonstration, not institutional capacity. Historical term totals are not used to claim current vacancies or predictive accuracy.

## Attribution, AI use, and collaboration

Source URLs and data-reconciliation notes are in [`docs/data_sources.md`](docs/data_sources.md). The historical workbook must be acquired from the approved course/source location; a publicly accessible downloadable copy has **not** been verified in this repository.

ChatGPT (OpenAI) assisted with schema/code drafting, Python generator and tests, SQL query examples, debugging, and documentation. Sanchit executed the scripts in Neon and checked database counts, query outputs, CRUD before/after states, and expected constraint failures. Design decisions and responsibility remain with the team.

Milestone 2 implementation was led by **Sanchit Kumar**, following the team's ERD discussion with **Viswambhara Chinmaye Palaparthi**. Both members submit their own individual contribution statement per course instructions.

## Submission branch

`SanBranch` contains the Milestone 2 implementation. The repository default branch, `main`, should be updated through review/merge before the instructor accesses the top-level repository URL. Until then, link directly to [SanBranch](https://github.com/HenryTudor8/HousingOps/tree/SanBranch).

## Streamlit prototype on SanBranch

With the PostgreSQL database already populated and your private `DATABASE_URL` in `.env`, run:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/dashboard.py
```

The interface provides read-only vacancy snapshots, RA staffing gaps, fictional request matching and real historical occupied-space summaries. See the [app guide](app/README.md) and [development roadmap](docs/project_roadmap.md). **Its live Neon connection and rendered UI still need to be tested locally.**
