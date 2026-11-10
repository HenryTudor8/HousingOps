# HousingOps Streamlit dashboard prototype

This is the first **read-only application increment** after Milestone 2. The instructor's Milestone 3 rubric has not yet been incorporated, and this is not a production-grade housing system.

## Pages implemented

- Overview: modeled bed totals, confirmed occupancy and vacancy by hall at a selected date.
- Bed availability: 0/7/14/30-day vacancy snapshots, which do **not** guarantee an entire stay.
- RA coverage: active fictional RA assignments and floors lacking coverage.
- Room-change matching: preference-ranked candidate beds filtered by room type, ceiling, eligibility and *full proposed stay*. No reservation is made.
- Transfer preview: a **read-only** preflight review of a chosen candidate bed and a proposed assignment change. It does not authorize or execute a transfer.
- Historical occupancy: 2022–24 public occupied-space totals and property drilldown, distinct from synthetic operations.

The prototype reads the existing 16-table Neon/PostgreSQL database. It does **not** add tables, change Milestone 2 code, or perform CRUD.

## Run locally

From the HousingOps root folder in Windows PowerShell, with Python 3.11 and the existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app/dashboard.py
```

The database must already be populated, and the private local `.env` must contain your working `DATABASE_URL`. If the password was previously exposed in GitHub history, rotate it in Neon before running the app.

Streamlit will provide a localhost URL, generally `http://localhost:8501`.

## Offline test commands

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_app_logic.py tests\test_app_repository.py -v
```

The tests check pure helper functions and mocked database-query behavior. **They do not connect to Neon or prove that the Streamlit interface has been rendered successfully.** A manual walkthrough remains necessary.

## Expected demonstrations

For the original fictional baseline `2026-10-28`, previous Milestone 2 results were 144 modeled beds, 34 open beds, RA gaps at Cooper floor 3 and Pride floor 2, and 34/39/45/49 open beds at 0/7/14/30 days. The four request scenarios yielded 7/10/0/0 complete-stay matches for a stay ending `2027-05-15` (exclusive). Treat these as test expectations, not newly executed UI evidence.

## Security boundaries

- All queries use fixed SQL with bound psycopg parameters.
- Each read begins with `SET TRANSACTION READ ONLY`.
- Database credentials remain in ignored `.env`; connection errors are not shown raw to the user.
- This is not an authenticated administrator portal. Do **not** publicly deploy it with database owner credentials or real resident information.
- For deployment, create a separate database role with `SELECT` privileges only.
- A future approved move must be transactional, authorized and concurrency-safe. The current matching view is recommendation-only.

See the [project roadmap](../docs/project_roadmap.md) for additional work.
