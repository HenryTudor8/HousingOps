-- HousingOps | DSCI-D 532 | Milestone 2
-- Query 3: Ranked room-change recommendations
-- Data disclaimer: Resident, assignment, room and request records are SYNTHETIC.
-- Semester rates are sourced separately. All assignment end_dates are exclusive.
-- Assumed end of proposed stay: 2027-05-15, exclusive (2026-27 demonstration year).
-- IMPORTANT: This SELECT only recommends candidates; it does NOT assign beds.

-- QUERY A: Ranked eligible destinations for a particular pending request.
-- Change 'REQ_0001' to 'REQ_0002', 'REQ_0003' or 'REQ_0004' to test scenarios.
WITH selected_request AS (
    SELECT
        q.request_id, q.resident_id, q.desired_move_date,
        q.room_type_id, q.max_semester_price_usd,
        q.preferred_floor_number, q.demo_scenario,
        res.eligibility_group, res.student_level
    FROM room_change_requests AS q
    JOIN residents AS res ON res.resident_id = q.resident_id
    WHERE q.request_id = 'REQ_0001'
      AND q.status = 'pending'
      AND q.desired_move_date < DATE '2027-05-15'
)
SELECT
    q.request_id,
    q.demo_scenario,
    q.desired_move_date,
    pref.rank AS preference_rank,
    b.building_name,
    f.floor_number,
    r.room_number,
    bed.bed_id,
    rt.room_type_name,
    rate.semester_rate_usd
FROM selected_request AS q
JOIN request_preferences AS pref ON pref.request_id = q.request_id
JOIN buildings AS b ON b.building_id = pref.building_id
JOIN floors AS f ON f.building_id = b.building_id
JOIN rooms AS r ON r.floor_id = f.floor_id
JOIN beds AS bed ON bed.room_id = r.room_id
JOIN room_types AS rt ON rt.room_type_id = r.room_type_id
JOIN housing_rates AS rate
    ON rate.building_id = b.building_id
   AND rate.room_type_id = r.room_type_id
   AND rate.academic_year = '2026-27'
WHERE r.room_type_id = q.room_type_id
  AND rate.semester_rate_usd <= q.max_semester_price_usd
  AND (q.preferred_floor_number IS NULL
       OR f.floor_number = q.preferred_floor_number)
  AND (b.eligible_group = 'coed'
       OR b.eligible_group = q.eligibility_group)
  AND b.eligible_level = q.student_level
  -- Bed must be unassigned for ALL of the proposed stay, not just move-in day.
  AND NOT EXISTS (
      SELECT 1
      FROM bed_assignments AS a
      WHERE a.bed_id = bed.bed_id
        AND a.status = 'confirmed'
        AND daterange(a.start_date, a.end_date, '[)') &&
            daterange(q.desired_move_date, DATE '2027-05-15', '[)')
  )
ORDER BY pref.rank, rate.semester_rate_usd,
         b.building_name, f.floor_number, r.room_number, bed.bed_id;

-- QUERY B: Diagnostic scenario counts for the four designed demonstration cases.
-- Expected with seed=532, as-of=2026-10-28: REQ_0001=7, REQ_0002=10,
-- REQ_0003=0, REQ_0004=0. These are complete-stay, not one-day, counts.
WITH scenario_requests AS (
    SELECT q.*, res.eligibility_group, res.student_level
    FROM room_change_requests AS q
    JOIN residents AS res ON res.resident_id = q.resident_id
    WHERE q.request_id IN ('REQ_0001','REQ_0002','REQ_0003','REQ_0004')
      AND q.status = 'pending'
      AND q.desired_move_date < DATE '2027-05-15'
)
SELECT
    q.request_id,
    q.demo_scenario,
    q.desired_move_date,
    COUNT(matches.bed_id) AS eligible_beds_for_entire_stay
FROM scenario_requests AS q
LEFT JOIN LATERAL (
    SELECT bed.bed_id
    FROM request_preferences AS pref
    JOIN buildings AS b ON b.building_id = pref.building_id
    JOIN floors AS f ON f.building_id = b.building_id
    JOIN rooms AS r ON r.floor_id = f.floor_id
    JOIN beds AS bed ON bed.room_id = r.room_id
    JOIN housing_rates AS rate
        ON rate.building_id = b.building_id
       AND rate.room_type_id = r.room_type_id
       AND rate.academic_year = '2026-27'
    WHERE pref.request_id = q.request_id
      AND r.room_type_id = q.room_type_id
      AND rate.semester_rate_usd <= q.max_semester_price_usd
      AND (q.preferred_floor_number IS NULL
           OR f.floor_number = q.preferred_floor_number)
      AND (b.eligible_group = 'coed'
           OR b.eligible_group = q.eligibility_group)
      AND b.eligible_level = q.student_level
      AND NOT EXISTS (
          SELECT 1
          FROM bed_assignments AS a
          WHERE a.bed_id = bed.bed_id
            AND a.status = 'confirmed'
            AND daterange(a.start_date, a.end_date, '[)') &&
                daterange(q.desired_move_date, DATE '2027-05-15', '[)')
      )
) AS matches ON TRUE
GROUP BY q.request_id, q.demo_scenario, q.desired_move_date
ORDER BY q.request_id;
