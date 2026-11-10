# HousingOps validation

## Local Python tests

Generate the public and synthetic CSVs first (see the root [README](../README.md)), then run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_public_data.py tests\test_synthetic_data.py -v
```

- `test_public_data.py`: 5 tests of historical counts, unique keys, references, nonnegative values, and published six-term totals.
- `test_synthetic_data.py`: 13 tests of seeded determinism, relationships, assignment overlaps, room-type/rate compatibility, request scenarios, RA gaps, and manifest output.

These Python tests validate generated datasets before loading. They are **not database constraint tests**.

## PostgreSQL integrity demonstrations

After loading the database, execute each statement in [`sql/06_integrity_tests.sql`](../sql/06_integrity_tests.sql) **individually** in a SQL Editor.

| Invalid operation | Expected PostgreSQL outcome |
| --- | --- |
| Assignment with nonexistent `bed_id` | Rejected, SQLSTATE `23503` (foreign key) |
| Overlapping confirmed assignment | Rejected, SQLSTATE `23P01` (exclusion constraint) |
| Final SELECT | Both invalid test assignment IDs absent |

Neon screenshots are archived in [`docs/evidence/screenshots/`](../docs/evidence/README.md). Expected SQL errors are evidence that the constraints work.

## Post-Milestone 2 workflow tests

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_workflow.py tests\test_workflow_repository.py -v
```

These are offline, read-only preview and parameterized SQL contract tests. They do **not** execute an approval transaction. PostgreSQL transaction/rollback/concurrency integration tests remain a separate task.
