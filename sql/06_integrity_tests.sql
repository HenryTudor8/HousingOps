-- HousingOps | DSCI-D 532 | Milestone 2
-- Database integrity demonstrations, each expected to FAIL.
-- Run each INSERT SEPARATELY. Do NOT run both in one transaction.
-- These use fake identifiers and existing synthetic rows, and should insert 0 rows.
-- Capture the PostgreSQL error as evidence. Do not remove database constraints.

-- TEST A: FK VIOLATION. Attempt to use a bed that does not exist.
-- Expected: SQLSTATE 23503 foreign_key_violation.
INSERT INTO bed_assignments (
    assignment_id, resident_id, bed_id, start_date, end_date,
    status, synthetic_record
)
SELECT
    'ASSIGN_INVALID_FK_TEST', r.resident_id, 'BED_NOT_REAL_999',
    DATE '2027-06-01', DATE '2027-06-15', 'confirmed', TRUE
FROM residents AS r
ORDER BY r.resident_id
LIMIT 1;

-- TEST B: DATE-OVERLAP VIOLATION. Reuse exactly the same bed and effective
-- date interval as an existing confirmed assignment.
-- Expected: SQLSTATE 23P01 exclusion_violation, due to overlapping bed
-- AND/OR resident assignments. (Both exclusions are enforced by the schema.)
INSERT INTO bed_assignments (
    assignment_id, resident_id, bed_id, start_date, end_date,
    status, synthetic_record
)
SELECT
    'ASSIGN_INVALID_OVERLAP_TEST', a.resident_id, a.bed_id,
    a.start_date, a.end_date, 'confirmed', TRUE
FROM bed_assignments AS a
WHERE a.status = 'confirmed'
ORDER BY a.assignment_id
LIMIT 1;

-- After running each failure separately, this check should return zero.
SELECT COUNT(*) AS invalid_rows_inserted
FROM bed_assignments
WHERE assignment_id IN ('ASSIGN_INVALID_FK_TEST', 'ASSIGN_INVALID_OVERLAP_TEST');
