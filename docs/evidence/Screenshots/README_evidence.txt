HousingOps Milestone 2 screenshot evidence

INTEGRITY:
integrity_01_foreign_key_rejected_23503.png - Invalid bed ID rejected (SQLSTATE 23503).
integrity_02_overlapping_assignment_rejected_23P01.png - Confirmed bed double booking rejected by exclusion constraint (SQLSTATE 23P01).
integrity_03_confirm_zero_invalid_assignments.png - Both rejected test assignment IDs absent (0).

CRUD:
crud_00_before_request_absent.png - Initial SELECT for test request returns no rows (editor shows statement executed successfully but no table output; this is weaker evidence than a COUNT(*) query).
crud_01_insert_demo_request_success.png - Insertion of test request completed.
crud_02_insert_ranked_preference_success.png - Insertion of linked ranked building preference completed.
crud_04_update_request_budget_and_status.png - UPDATE statement completed (sets pending, budget 3900).
crud_05_read_after_update_pending_3900.png - Query returns pending request with budget 3900 and move date 2026-11-20.
crud_06_delete_demo_request_success.png - DELETE completed.
crud_07_read_after_delete_zero_rows.png - Test request and preference both absent, counts 0 and 0.

