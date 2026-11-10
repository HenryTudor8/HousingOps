# HousingOps development roadmap after Milestone 2

**Planning document only.** This is not the official Milestone 3 rubric. Reassess scope when the instructor publishes the requirements.

## Milestone 2 foundation completed

- 16-table PostgreSQL schema, primary/foreign keys, checks, and date-range exclusion constraints.
- Historical aggregate public source (25 properties, six terms), plus deterministic fictional resident/RA/assignment data.
- Python ETL, generator, loader, 18 existing generator/public-data tests, and SQL queries.
- CRUD operations and two rejected invalid database writes.
- Evidence exports and documented relational diagram.

## New work on SanBranch

- `app/dashboard.py`: Streamlit navigation, metrics, availability chart, RA gaps, matching table, and public historical charts.
- `app/repository.py`: static parameterized read-only PostgreSQL queries.
- `app/logic.py`: date/summary functions.
- `tests/test_app_logic.py` and `tests/test_app_repository.py`: offline helper and SQL-access contract tests.

**Validation state:** Files are committed. Live Streamlit/Neon execution and a manual screenshot walkthrough remain outstanding. The interface is not yet finalized for Milestone 3.

## Next development priorities

1. **Run the app locally** against the populated Neon branch and compare its results to the Milestone 2 evidence.
2. **Create an isolated Neon development branch** for future write tests. Do not perform room-transfer experiments on the production dataset.
3. **Design a transaction-safe room transfer**: verify approved request/eligibility, confirm full-period availability, update assignments atomically, and test concurrency/rollback.
4. **Add authentication and roles**, including a dedicated database read-only account. No public exposure with the owner role.
5. **Improve usability**: meaningful empty states, filters, accessibility, exports, and a focused demonstration journey.
6. **Add integration tests** against a disposable database branch and UI tests beyond pure SQL mocks.
7. **Prepare for Milestone 3** once the assignment appears: map every new rubric item to code, evidence and owner.
8. **Prepare final delivery**: deployment approach, verified run instructions, source attributions, screenshots and demonstration script.

## Suggested collaboration discussion

Sanchit has started the dashboard data layer and UI on his own branch. Viswambhara should agree on an independent, substantive next workstream, such as UI functionality with tests, design/UX changes, or integration testing and documentation. **These are proposals, not statements about work already completed.** Track actual contributions in commits and project notes.

## Reproducible expected outcomes

At the fictional baseline date `2026-10-28`, the prior database demonstration returned 34 free beds, two uncovered floors (Cooper 3, Pride 2), and 7/10/0/0 full-stay room matches for the first four demo requests. Historical occupied-space totals were 5,873/5,732/452/5,705/5,702/257. A change from these results warrants checking the connected database branch, reference date, assignment intervals and request end date.

Data privacy: fictional residents only. Do not ingest actual student data.
