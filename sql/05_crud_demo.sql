-- HousingOps | DSCI-D 532 | Milestone 2
-- CRUD demonstration on a synthetic TEST room-change request.
-- IMPORTANT: Execute each numbered section SEPARATELY in Neon SQL Editor.
-- Capture results before and after UPDATE, and after DELETE.
-- Do not use a real resident or an existing project request ID.
-- If you re-run the demo, DELETE the old test request first.

-- 0. BEFORE: Check that the demo request does not exist. Expect zero rows.
SELECT * FROM room_change_requests WHERE request_id = 'REQ_CRUD_DEMO_01';

-- 1. CREATE: Insert a NEW draft request for an existing synthetic resident
-- who does not currently have a pending request. Expect INSERT 0 1.
INSERT INTO room_change_requests (
    request_id, resident_id, created_date, desired_move_date,
    room_type_id, max_semester_price_usd, preferred_floor_number,
    status, demo_scenario, synthetic_record
)
SELECT
    'REQ_CRUD_DEMO_01', r.resident_id,
    DATE '2026-10-28', DATE '2026-11-20',
    rt.room_type_id, 3500.00, NULL,
    'draft', 'crud_demo', TRUE
FROM residents AS r
CROSS JOIN room_types AS rt
WHERE rt.room_type_name = 'Double'
  AND NOT EXISTS (
      SELECT 1 FROM room_change_requests AS existing
      WHERE existing.resident_id = r.resident_id
        AND existing.status = 'pending'
  )
ORDER BY r.resident_id
LIMIT 1;

-- 2. CREATE A PREFERENCE linked to the same request. Expect INSERT 0 1.
INSERT INTO request_preferences (
    preference_id, request_id, building_id, rank, synthetic_record
)
SELECT
    'PREF_CRUD_DEMO_01', q.request_id, b.building_id, 1, TRUE
FROM room_change_requests AS q
JOIN buildings AS b ON b.building_name = 'Pride Hall'
WHERE q.request_id = 'REQ_CRUD_DEMO_01';

-- 3. READ: Capture this result BEFORE the update.
SELECT
    q.request_id, r.display_name AS synthetic_resident,
    q.status, q.desired_move_date, q.max_semester_price_usd,
    p.rank, b.building_name
FROM room_change_requests AS q
JOIN residents AS r ON r.resident_id = q.resident_id
LEFT JOIN request_preferences AS p ON p.request_id = q.request_id
LEFT JOIN buildings AS b ON b.building_id = p.building_id
WHERE q.request_id = 'REQ_CRUD_DEMO_01';

-- 4. UPDATE: Increase budget and change the request from draft to pending.
-- The schema permits at most one pending request per resident.
UPDATE room_change_requests
SET max_semester_price_usd = 3900.00,
    status = 'pending'
WHERE request_id = 'REQ_CRUD_DEMO_01';

-- 5. READ AFTER UPDATE: Capture and compare with step 3.
SELECT
    request_id, status, desired_move_date, max_semester_price_usd
FROM room_change_requests
WHERE request_id = 'REQ_CRUD_DEMO_01';

-- 6. DELETE: Remove ONLY the demo request (its preference cascades).
DELETE FROM room_change_requests
WHERE request_id = 'REQ_CRUD_DEMO_01';

-- 7. READ AFTER DELETE: Both counts should be zero.
SELECT
    (SELECT COUNT(*) FROM room_change_requests
     WHERE request_id = 'REQ_CRUD_DEMO_01') AS remaining_test_requests,
    (SELECT COUNT(*) FROM request_preferences
     WHERE preference_id = 'PREF_CRUD_DEMO_01') AS remaining_test_preferences;
