# HousingOps SQL scripts

These scripts implement and demonstrate the 16-table PostgreSQL database in Milestone 2. They have been executed by the project team on Neon PostgreSQL. **Do not run creation or loading procedures against an existing populated schema.**

## Run order

| File | Purpose | Notes |
| --- | --- | --- |
| `01_schema.sql` | Creates the 16 normalized tables, constraints, GiST exclusion rules, and indexes | Run only on a **new empty database** |
| `01_verify_schema.sql` | Lists tables and their constraints; shows sample table counts | Run after schema creation. Its sample counts show **zero before loading**, nonzero afterward |
| `01_ra_coverage.sql` | Identifies uncovered RA floors and summarizes coverage by building | Baseline `2026-10-28` |
| `02_bed_availability.sql` | Point-in-time vacancy checkpoints, bed detail, and entire-stay availability | A/B/C are separate queries |
| `03_room_change_matching.sql` | Preference-ranked available destinations and four scenario counts | A/B are separate queries |
| `04_historical_occupancy.sql` | Public term totals and property-level term changes | A/B are separate queries |
| `05_crud_demo.sql` | CREATE, READ, UPDATE and DELETE of a fake room-change request and preference | Run sections **0 through 7 individually in order** |
| `06_integrity_tests.sql` | Intentionally rejected foreign-key and overlapping-assignment inserts | Run each INSERT separately and expect SQL errors |

The main [README](../README.md) covers the full Python → PostgreSQL reproduction procedure, while [evidence](../docs/evidence/README.md) contains exported results and screenshots.

## Verified demo outputs

- **RA coverage (Query 1A):** Cooper Hall floor 3 and Pride Hall floor 2 lack active RA coverage under the fictional staffing schedule.
- **Vacancy (Query 2A):** 34 vacant on Oct 28, 39 after 7 days, 45 after 14 days, and 49 after 30 days, counting across four fictional halls. These are *date snapshots*, not continuous-stay guarantees.
- **Room matching (Query 3B):** `REQ_0001` = 7, `REQ_0002` = 10, `REQ_0003` = 0, `REQ_0004` = 0 (entire intended stay).
- **Historical occupancy (Query 4A):** Fall 2022 = 5,873; Spring 2023 = 5,732; Summer 2023 = 452; Fall 2023 = 5,705; Spring 2024 = 5,702; Summer 2024 = 257. **These are public occupied-space counts**, not vacancy rates.
- **CRUD:** Test request changes from `draft` at $3,500 to `pending` at $3,900, then is deleted with its preference via `ON DELETE CASCADE`.
- **Integrity:** SQLSTATE `23503` rejects a missing referenced bed; `23P01` rejects an overlapping confirmed bed assignment.

## Key integrity choices

- Primary and foreign keys define relationships.
- `CHECK`, `NOT NULL` and `UNIQUE` constraints restrict invalid values, missing required fields and duplicates.
- `btree_gist` plus exclusion constraints prevent overlap for a confirmed bed or confirmed resident assignment. Intervals are half-open: `[start_date, end_date)`.
- Room-type/price compatibility and some operational policies receive additional validation in the Python generator/loader. Such application-side validation is **not** the same as universally enforcing that rule for arbitrary direct SQL writes.

**Important:** Scripts in the SQL Editor can contain several SELECT statements. Select and execute the intended statement, or execute one statement at a time and export that result. The CRUD test is deliberately destructive **only to its own fictional test record**.
