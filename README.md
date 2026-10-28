# HousingOps

University housing operations and room-change decision support using **PostgreSQL, Python, and Streamlit**.

**DSCI-D 532 | Fall 2026 | Team project**

## Project goals

- Find current and upcoming vacancies from dated synthetic assignments.
- Identify floors missing RA coverage under an explicit simulation rule.
- Match room-change requests by ranked building preference, room type, price, desired move date, and optional floor.
- Analyze separately sourced public 2022-24 residence-property occupancy observations.

## Status and milestones

- **Milestone 2, November 8, 2026:** Implement actual normalized PostgreSQL database, imports, integrity constraints, CRUD, at least three SQL queries, and documentation.
- **Final target, December 13, 2026:** Working Streamlit application and project demonstration.
- **Current:** Public Excel ETL and synthetic generator exist. **The PostgreSQL schema, loading, SQL queries, and app are not completed by these scripts.**

## Source data and provenance

The source Excel workbook, `Project Data.xlsx` (N.C. A&T Exhibit C: Current Site Data), supplies aggregate historic property occupancy for Fall 2022 to Summer 2024. There are no real student assignments, RA floor rosters, or room-change requests in that source. The operational layer is fictional and explicitly marked as synthetic.

See [data sources](docs/data_sources.md) and [synthetic generation methodology](docs/synthetic_data.md) for published 2026-27 rate links, limitations, source discrepancies, the relation to Milestone 1's ERD, and the fixed demonstration scenarios.

## Getting started on Windows (VS Code)

Requires Python 3.11+ (standard build, not experimental free-threaded Python), and an isolated virtual environment is recommended.

```powershell
# From your cloned HousingOps directory:
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copy the original source workbook to **`data/raw/Project Data.xlsx`** locally. The data folders are intentionally excluded from version control. Then:

```powershell
# Extract the real public 25 x 6 historical observations:
.\.venv\Scripts\python.exe scripts\clean_public_data.py

# Generate a deterministic, entirely fictional operational scenario:
.\.venv\Scripts\python.exe scripts\generate_synthetic.py --seed 532 --as-of 2026-10-28

# Run public ETL and synthetic integrity tests:
.\.venv\Scripts\python.exe -m pytest tests\test_public_data.py tests\test_synthetic_data.py -v
```

The generator creates **13 CSV files plus `manifest.json`** under `data/processed/synthetic/`; these files are reproducible and should not be committed. For scenario design, options, current/future vacancies, room matching, and validation rules see [synthetic_data.md](docs/synthetic_data.md).

The synthetic generator outputs a **provisional canonical interface**, not final SQL tables. The database team will implement a loader/adapter once primary keys, table names, and ERD are agreed. In the final application a bed assignment must be checked for the intended stay interval and performed through a safe database transaction.

## Team workflow

- `main`: accepted integrated version, used for milestone and final demonstration.
- `SanBranch`: Sanchit's working branch for ETL, synthetic data, validation, and application logic.
- Partner's own branch: schema, SQL, and database integration.
- Review and test changes via pull requests before merging to `main`.
- Each member must participate in and understand database design, SQL operations, testing, and final presentation.

## Security and academic integrity

Never commit real resident records, personal information, credentials, `.env`, or local database dumps. Sources and all invented data are separately documented. AI assistance must be acknowledged and all scripts must be reviewed, tested, and understood by the team.
