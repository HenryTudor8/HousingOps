-- HousingOps | Milestone 2 | Application Query: Bed availability
-- PUBLIC reference data is separate; building/room/bed/assignment records are synthetic.
-- Dates are tied to the reproducible synthetic scenario: seed=532, as-of=2026-10-28.
-- Assignment date ranges are [start_date, end_date): end_date is exclusive.

-- QUERY A: Snapshot vacancy counts by building for baseline, +7, +14, +30 days.
-- This shows availability ON each checkpoint date, not a guaranteed full-term stay.
WITH checkpoints(label, days_ahead) AS (
    VALUES ('Baseline', 0), ('7 days', 7), ('14 days', 14), ('30 days', 30)
), available_beds AS (
    SELECT
        c.label,
        c.days_ahead,
        b.building_name,
        bed.bed_id
    FROM checkpoints AS c
    CROSS JOIN beds AS bed
    JOIN rooms AS r ON r.room_id = bed.room_id
    JOIN floors AS f ON f.floor_id = r.floor_id
    JOIN buildings AS b ON b.building_id = f.building_id
    WHERE NOT EXISTS (
        SELECT 1
        FROM bed_assignments AS a
        WHERE a.bed_id = bed.bed_id
          AND a.status = 'confirmed'
          AND a.start_date <= DATE '2026-10-28' + c.days_ahead
          AND a.end_date > DATE '2026-10-28' + c.days_ahead
    )
)
SELECT
    label,
    DATE '2026-10-28' + days_ahead AS check_date,
    building_name,
    COUNT(*) AS available_beds
FROM available_beds
GROUP BY label, days_ahead, building_name
ORDER BY days_ahead, building_name;

-- QUERY B: Individual beds open on a proposed move date, with room and semester rate.
-- No guarantee that the bed stays free after that date. See QUERY C.
SELECT
    b.building_name,
    f.floor_number,
    r.room_number,
    bed.bed_id,
    bed.bed_label,
    rt.room_type_name,
    hr.semester_rate_usd
FROM beds AS bed
JOIN rooms AS r ON r.room_id = bed.room_id
JOIN room_types AS rt ON rt.room_type_id = r.room_type_id
JOIN floors AS f ON f.floor_id = r.floor_id
JOIN buildings AS b ON b.building_id = f.building_id
LEFT JOIN housing_rates AS hr
    ON hr.building_id = b.building_id
   AND hr.room_type_id = r.room_type_id
   AND hr.academic_year = '2026-27'
WHERE NOT EXISTS (
    SELECT 1 FROM bed_assignments AS a
    WHERE a.bed_id = bed.bed_id
      AND a.status = 'confirmed'
      AND a.start_date <= DATE '2026-11-17'
      AND a.end_date > DATE '2026-11-17'
)
ORDER BY b.building_name, f.floor_number, r.room_number, bed.bed_label;

-- QUERY C: Beds free for the ENTIRE proposed occupancy period.
-- Use this stricter rule for recommending a bed for a full-term room change.
SELECT
    b.building_name,
    f.floor_number,
    r.room_number,
    bed.bed_id,
    rt.room_type_name,
    hr.semester_rate_usd
FROM beds AS bed
JOIN rooms AS r ON r.room_id = bed.room_id
JOIN room_types AS rt ON rt.room_type_id = r.room_type_id
JOIN floors AS f ON f.floor_id = r.floor_id
JOIN buildings AS b ON b.building_id = f.building_id
LEFT JOIN housing_rates AS hr
    ON hr.building_id = b.building_id
   AND hr.room_type_id = r.room_type_id
   AND hr.academic_year = '2026-27'
WHERE NOT EXISTS (
    SELECT 1 FROM bed_assignments AS a
    WHERE a.bed_id = bed.bed_id
      AND a.status = 'confirmed'
      AND daterange(a.start_date, a.end_date, '[)') &&
          daterange(DATE '2026-11-17', DATE '2027-05-15', '[)')
)
ORDER BY b.building_name, f.floor_number, r.room_number, bed.bed_id;
