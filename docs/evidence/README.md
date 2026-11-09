# Milestone 2 evidence index

These files document a successful demonstration on a hosted Neon PostgreSQL database. **The executable code is in [`sql/`](../../sql/README.md) and [`scripts/`](../../scripts/README.md); evidence does not replace source code.**

## Query exports in `query_results/`

| File | Meaning |
| --- | --- |
| `query_02_availability.csv` | Four buildings at baseline, +7, +14, +30 days; total vacant beds 34 / 39 / 45 / 49 |
| `query_03a_matches.csv` | Seven complete-stay bed matches for `REQ_0001` in Pride Hall |
| `query_03b_scenarios.csv` | Four request test scenarios yield 7 / 10 / 0 / 0 matches |
| `query_04a_term_totals.csv` | Six historical term totals, originally exported as a **two-column summary** |
| `query_04b_property_detail.csv` | 150 property-term rows with prior-term comparison |
| `crud_03_read_before_update.csv` | Fictional test request **before** UPDATE: `draft`, $3,500 (despite its former misleading filename) |

**Export note:** The six totals in `query_04a_term_totals.csv` are correct, but the stored export is a two-column projection, whereas the committed `sql/04_historical_occupancy.sql` Query A produces six columns (term code, name, year, season, property count, total). To make file-to-code reproduction exact, rerun and export the committed statement when convenient.

**RA coverage:** The team ran `sql/01_ra_coverage.sql` successfully and identified Cooper floor 3 and Pride floor 2. A separate RA query-result CSV or screenshot is **not currently present** in this repository.

## Screenshots in `screenshots/`

### CRUD

1. `crud_00_before_request_absent.png`: initial check for absent test request (limited visibility of row count).
2. `crud_01_insert_demo_request_success.png`: CREATE test room-change request.
3. `crud_02_insert_ranked_preference_success.png`: CREATE linked preference.
4. `crud_04_update_request_budget_and_status.png`: UPDATE to pending, $3,900.
5. `crud_05_read_after_update_pending_3900.png`: READ confirms pending and $3,900.
6. `crud_06_delete_demo_request_success.png`: DELETE test request.
7. `crud_07_read_after_delete_zero_rows.png`: READ confirms request and preference were deleted.

The `crud_03_read_before_update.csv` export supplements the missing immediately-after-create screenshot.

### Integrity constraints

- `integrity_01_foreign_key_rejected_23503.png`: non-existent bed reference rejected, SQLSTATE `23503`.
- `integrity_02_overlapping_assignment_rejected_23P01.png`: overlapping confirmed assignment rejected, SQLSTATE `23P01`.
- `integrity_03_confirm_zero_invalid_assignments.png`: neither rejected test record was inserted.

All resident, room, RA and request evidence describes a **fictional 2026–27 demonstration**, not actual N.C. A&T residents or occupancy. Historical data refers only to public 2022–24 occupied-space counts.
