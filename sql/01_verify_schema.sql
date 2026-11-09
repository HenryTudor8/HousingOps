-- HousingOps schema verification, read-only.
-- Run AFTER sql/01_schema.sql in Neon SQL Editor.

-- 1. Expect 16 application tables.
SELECT COUNT(*) AS application_tables
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
  AND table_name IN (
    'housing_properties', 'academic_terms', 'occupancy_observations',
    'source_register', 'room_types', 'buildings', 'floors', 'rooms', 'beds',
    'housing_rates', 'residents', 'bed_assignments', 'staff',
    'staff_floor_assignments', 'room_change_requests', 'request_preferences'
  );

-- 2. Show the 16 table names.
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- 3. Show key constraints. Expect both no_overlapping_confirmed_*.
SELECT t.relname AS table_name,
       c.conname AS constraint_name,
       CASE c.contype
           WHEN 'p' THEN 'PRIMARY KEY'
           WHEN 'f' THEN 'FOREIGN KEY'
           WHEN 'u' THEN 'UNIQUE'
           WHEN 'c' THEN 'CHECK'
           WHEN 'x' THEN 'EXCLUSION'
           ELSE c.contype::text
       END AS constraint_type
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace ns ON ns.oid = t.relnamespace
WHERE ns.nspname = 'public'
ORDER BY t.relname, c.contype, c.conname;

-- 4. New schemas are empty until loaded: expect three zeros.
SELECT 'housing_properties' AS table_name, COUNT(*) AS records FROM housing_properties
UNION ALL
SELECT 'academic_terms', COUNT(*) FROM academic_terms
UNION ALL
SELECT 'occupancy_observations', COUNT(*) FROM occupancy_observations;
