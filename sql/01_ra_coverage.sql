-- HousingOps | DSCI-D 532 | Milestone 2
-- APPLICATION QUERY 1: Uncovered RA floors
-- Works with the 16-table HousingOps schema on Neon PostgreSQL.
-- All operational/staffing records in this demonstration are SYNTHETIC.
-- Date intervals are half-open: [start_date, end_date).
-- Run QUERY A and QUERY B individually in Neon SQL Editor.

-- QUERY A: List floors that have no active RA coverage on Oct. 28, 2026.
-- Expected for the synthetic seed=532 dataset:
-- Cooper Hall floor 3, Pride Hall floor 2.
SELECT
    b.building_name,
    f.floor_number,
    'No active RA assigned' AS coverage_status
FROM floors AS f
JOIN buildings AS b
    ON b.building_id = f.building_id
WHERE NOT EXISTS (
    SELECT 1
    FROM staff_floor_assignments AS sfa
    JOIN staff AS s
        ON s.staff_id = sfa.staff_id
    WHERE sfa.floor_id = f.floor_id
      AND s.role = 'RA'
      AND sfa.status = 'active'
      AND sfa.start_date <= DATE '2026-10-28'
      AND sfa.end_date > DATE '2026-10-28'
)
ORDER BY b.building_name, f.floor_number;

-- QUERY B: Coverage summary by building for the same date.
-- Use this if you want an aggregate result in the report as well.
WITH floor_coverage AS (
    SELECT
        b.building_name,
        f.floor_id,
        EXISTS (
            SELECT 1
            FROM staff_floor_assignments AS sfa
            JOIN staff AS s
                ON s.staff_id = sfa.staff_id
            WHERE sfa.floor_id = f.floor_id
              AND s.role = 'RA'
              AND sfa.status = 'active'
              AND sfa.start_date <= DATE '2026-10-28'
              AND sfa.end_date > DATE '2026-10-28'
        ) AS has_active_ra
    FROM floors AS f
    JOIN buildings AS b ON b.building_id = f.building_id
)
SELECT
    building_name,
    COUNT(*) AS total_floors,
    COUNT(*) FILTER (WHERE has_active_ra) AS covered_floors,
    COUNT(*) FILTER (WHERE NOT has_active_ra) AS uncovered_floors
FROM floor_coverage
GROUP BY building_name
ORDER BY building_name;
