-- HousingOps | DSCI-D 532 | Milestone 2
-- APPLICATION QUERY 4: Historical occupied-space counts from the public workbook.
-- These are counts of occupied spaces, NOT occupancy percentages or current vacancies.
-- Run QUERY A and QUERY B individually in Neon SQL Editor.

-- QUERY A: Public occupied-space totals by academic term.
-- Expected data: Fall 2022=5873; Spring 2023=5732; Summer 2023=452;
-- Fall 2023=5705; Spring 2024=5702; Summer 2024=257.
SELECT
    t.term_code,
    t.term_name,
    t.calendar_year,
    t.season,
    COUNT(DISTINCT o.property_code) AS properties_reported,
    SUM(o.occupied_spaces) AS total_occupied_spaces
FROM occupancy_observations AS o
JOIN academic_terms AS t ON t.term_code = o.term_code
JOIN housing_properties AS p ON p.property_code = o.property_code
GROUP BY t.term_code, t.term_name, t.calendar_year, t.season
ORDER BY t.calendar_year,
         CASE t.season
             WHEN 'Spring' THEN 1
             WHEN 'Summer' THEN 2
             WHEN 'Fall' THEN 3
         END;

-- QUERY B: Each property's occupancy and change from its preceding term.
-- A term-to-term change is not necessarily comparable when summer enrollment is
-- different from fall/spring. This is descriptive, not a forecast.
WITH occupancy_by_property AS (
    SELECT
        p.property_name,
        t.term_name,
        t.calendar_year,
        t.season,
        o.occupied_spaces,
        LAG(o.occupied_spaces) OVER (
            PARTITION BY o.property_code
            ORDER BY t.calendar_year,
                     CASE t.season
                         WHEN 'Spring' THEN 1
                         WHEN 'Summer' THEN 2
                         WHEN 'Fall' THEN 3
                     END
        ) AS previous_term_occupied_spaces
    FROM occupancy_observations AS o
    JOIN housing_properties AS p ON p.property_code = o.property_code
    JOIN academic_terms AS t ON t.term_code = o.term_code
)
SELECT
    property_name,
    term_name,
    occupied_spaces,
    previous_term_occupied_spaces,
    occupied_spaces - previous_term_occupied_spaces AS change_from_previous_term
FROM occupancy_by_property
ORDER BY property_name,
         calendar_year,
         CASE season WHEN 'Spring' THEN 1 WHEN 'Summer' THEN 2 WHEN 'Fall' THEN 3 END;
