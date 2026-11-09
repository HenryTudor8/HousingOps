# HousingOps Python data pipeline

All commands are run from the repository root using Python 3.11 and packages from `requirements.txt`.

| Script | Input | Output and validation |
| --- | --- | --- |
| `clean_public_data.py` | `data/raw/Project Data.xlsx`, `Demographics` worksheet | 25 housing properties, 6 academic terms, 150 historical property-term observations; checks the six published totals |
| `generate_synthetic.py` | Cleaned `housing_properties.csv` | 13 fictional operational CSV tables and `manifest.json`; fixed seed, date-aware assignments, scenario checks |
| `load_database.py` | All 16 generated CSVs and `DATABASE_URL` | Validates CSV structure, types, relationships and schema columns; inserts into **empty** PostgreSQL in one transaction |

## Commands (Windows PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# First obtain the original public workbook.
# Save it as data/raw/Project Data.xlsx.
.\.venv\Scripts\python.exe scripts\clean_public_data.py

# The fictional 2026-27 test scenario:
.\.venv\Scripts\python.exe scripts\generate_synthetic.py --seed 532 --as-of 2026-10-28

# Validate output BEFORE loading:
.\.venv\Scripts\python.exe -m pytest tests\test_public_data.py tests\test_synthetic_data.py -v

# FIRST run sql/01_schema.sql in an empty PostgreSQL database,
# and configure DATABASE_URL in local .env (never commit it).
.\.venv\Scripts\python.exe scripts\load_database.py
```

The generated raw/processed data remain local and ignored by Git. The loader **refuses to insert into nonempty tables**; create a new empty database or development branch for repeat testing. If an error occurs during data loading, PostgreSQL rolls back the transaction.

See [data source guidance](../docs/data_sources.md), [synthetic methodology](../docs/synthetic_data.md), and [SQL notes](../sql/README.md).
