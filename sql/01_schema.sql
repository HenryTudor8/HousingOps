-- HousingOps | DSCI-D 532 | Milestone 2
-- Initial PostgreSQL schema aligned with the Milestone 1 proposed ERD and
-- the existing Python-generated CSV files on SanBranch.
-- Compatible with PostgreSQL 17+ (including Neon PostgreSQL 18).
--
-- All historical counts are PUBLIC and term-level. All room-level inventory,
-- residents, assignments, RA coverage and requests are FICTIONAL demonstration data.
--
-- Safe to run on a NEW, EMPTY database. CREATE IF NOT EXISTS does not migrate
-- or reconcile existing incompatible tables. Never run destructive DROP commands
-- on a shared/project database without coordinating with the team.

BEGIN;

-- Gives GiST indexes equality support for TEXT, alongside date-range overlap.
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- =============================================================
-- A. PUBLIC HISTORICAL REFERENCE DATA (3 TABLES)
-- =============================================================
CREATE TABLE IF NOT EXISTS housing_properties (
    property_code           TEXT PRIMARY KEY,
    property_name           TEXT NOT NULL,
    living_style            TEXT NOT NULL
                                CHECK (living_style IN ('Traditional', 'Suite', 'Apartment')),
    meal_plan_required      BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS academic_terms (
    term_code               TEXT PRIMARY KEY,
    term_name               TEXT NOT NULL UNIQUE,
    calendar_year           INTEGER NOT NULL CHECK (calendar_year BETWEEN 2000 AND 2100),
    season                  TEXT NOT NULL CHECK (season IN ('Fall', 'Spring', 'Summer')),
    UNIQUE (calendar_year, season)
);

CREATE TABLE IF NOT EXISTS occupancy_observations (
    property_code           TEXT NOT NULL
                                REFERENCES housing_properties(property_code),
    term_code               TEXT NOT NULL
                                REFERENCES academic_terms(term_code),
    occupied_spaces         INTEGER NOT NULL CHECK (occupied_spaces >= 0),
    source_file             TEXT NOT NULL,
    source_sheet            TEXT NOT NULL,
    PRIMARY KEY (property_code, term_code)
);

-- =============================================================
-- B. SOURCES, ROOM TYPES AND PRICES (3 TABLES)
-- =============================================================
CREATE TABLE IF NOT EXISTS source_register (
    source_id               TEXT PRIMARY KEY,
    source_name             TEXT NOT NULL,
    source_url              TEXT NOT NULL DEFAULT '',
    source_year             INTEGER NOT NULL CHECK (source_year BETWEEN 2000 AND 2100),
    source_kind             TEXT NOT NULL,
    quality_notes           TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS room_types (
    room_type_id            TEXT PRIMARY KEY,
    room_type_name          TEXT NOT NULL UNIQUE,
    beds_per_room           INTEGER NOT NULL CHECK (beds_per_room BETWEEN 1 AND 8)
);

-- =============================================================
-- C. PHYSICAL INVENTORY (4 TABLES)
-- HousingProperty -> Building -> Floor -> Room -> Bed
-- The sample layout is synthetic, not the university's actual layout.
-- =============================================================
CREATE TABLE IF NOT EXISTS buildings (
    building_id                 TEXT PRIMARY KEY,
    property_code               TEXT NOT NULL
                                    REFERENCES housing_properties(property_code),
    building_name               TEXT NOT NULL UNIQUE,
    historical_living_style     TEXT NOT NULL
                                    CHECK (historical_living_style IN ('Traditional', 'Suite', 'Apartment')),
    living_style_current        TEXT NOT NULL
                                    CHECK (living_style_current IN ('Traditional', 'Suite', 'Apartment')),
    eligible_group              TEXT NOT NULL
                                    CHECK (eligible_group IN ('male', 'female', 'coed')),
    eligible_level              TEXT NOT NULL
                                    CHECK (eligible_level IN ('first_year', 'upperclass')),
    published_floor_count       INTEGER NOT NULL CHECK (published_floor_count > 0),
    simulation_rooms_per_floor  INTEGER NOT NULL CHECK (simulation_rooms_per_floor > 0),
    profile_url                 TEXT NOT NULL,
    profile_source_id           TEXT NOT NULL
                                    REFERENCES source_register(source_id),
    synthetic_inventory         BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS floors (
    floor_id                TEXT PRIMARY KEY,
    building_id             TEXT NOT NULL REFERENCES buildings(building_id),
    floor_number            INTEGER NOT NULL CHECK (floor_number > 0),
    synthetic_inventory     BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT unique_floor_per_building UNIQUE (building_id, floor_number)
);

CREATE TABLE IF NOT EXISTS rooms (
    room_id                 TEXT PRIMARY KEY,
    floor_id                TEXT NOT NULL REFERENCES floors(floor_id),
    room_number             TEXT NOT NULL,
    room_type_id            TEXT NOT NULL REFERENCES room_types(room_type_id),
    synthetic_inventory     BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT unique_room_per_floor UNIQUE (floor_id, room_number)
);

CREATE TABLE IF NOT EXISTS beds (
    bed_id                  TEXT PRIMARY KEY,
    room_id                 TEXT NOT NULL REFERENCES rooms(room_id),
    bed_label               TEXT NOT NULL,
    synthetic_inventory     BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT unique_bed_label_per_room UNIQUE (room_id, bed_label)
);

CREATE TABLE IF NOT EXISTS housing_rates (
    housing_rate_id         TEXT PRIMARY KEY,
    building_id             TEXT NOT NULL REFERENCES buildings(building_id),
    room_type_id            TEXT NOT NULL REFERENCES room_types(room_type_id),
    academic_year           TEXT NOT NULL,
    semester_rate_usd       NUMERIC(10,2) NOT NULL CHECK (semester_rate_usd > 0),
    source_url              TEXT NOT NULL,
    source_id               TEXT NOT NULL REFERENCES source_register(source_id),
    provenance              TEXT NOT NULL,
    CONSTRAINT unique_housing_rate UNIQUE (building_id, room_type_id, academic_year)
);

-- =============================================================
-- D. FICTIONAL RESIDENTS AND BED ASSIGNMENTS (2 TABLES)
-- =============================================================
CREATE TABLE IF NOT EXISTS residents (
    resident_id             TEXT PRIMARY KEY,
    display_name            TEXT NOT NULL,
    eligibility_group       TEXT NOT NULL CHECK (eligibility_group IN ('male', 'female')),
    student_level           TEXT NOT NULL CHECK (student_level IN ('first_year', 'upperclass')),
    synthetic_record        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS bed_assignments (
    assignment_id           TEXT PRIMARY KEY,
    resident_id             TEXT NOT NULL REFERENCES residents(resident_id),
    bed_id                  TEXT NOT NULL REFERENCES beds(bed_id),
    start_date              DATE NOT NULL,
    end_date                DATE NOT NULL,
    status                  TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled', 'draft')),
    synthetic_record        BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT bed_assignment_dates_valid CHECK (end_date > start_date),
    -- The same bed can be reused at another time, but cannot be double booked.
    CONSTRAINT no_overlapping_confirmed_bed_assignments
        EXCLUDE USING gist (
            bed_id WITH =,
            daterange(start_date, end_date, '[)') WITH &&
        ) WHERE (status = 'confirmed'),
    -- A resident cannot have two confirmed beds at overlapping times.
    CONSTRAINT no_overlapping_confirmed_resident_assignments
        EXCLUDE USING gist (
            resident_id WITH =,
            daterange(start_date, end_date, '[)') WITH &&
        ) WHERE (status = 'confirmed')
);

-- =============================================================
-- E. STAFFING / EFFECTIVE-DATED RA FLOOR COVERAGE (2 TABLES)
-- =============================================================
CREATE TABLE IF NOT EXISTS staff (
    staff_id                TEXT PRIMARY KEY,
    display_name            TEXT NOT NULL,
    role                    TEXT NOT NULL,
    synthetic_record        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS staff_floor_assignments (
    staff_floor_assignment_id TEXT PRIMARY KEY,
    staff_id                  TEXT NOT NULL REFERENCES staff(staff_id),
    floor_id                  TEXT NOT NULL REFERENCES floors(floor_id),
    start_date                DATE NOT NULL,
    end_date                  DATE NOT NULL,
    status                    TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'cancelled')),
    synthetic_record          BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT staff_coverage_dates_valid CHECK (end_date > start_date),
    -- A single RA cannot cover multiple floors at overlapping effective dates
    -- under our simplified demo coverage policy. Multiple different RAs can
    -- cover one floor if the housing team decides that is legitimate.
    CONSTRAINT no_overlapping_active_staff_assignments
        EXCLUDE USING gist (
            staff_id WITH =,
            daterange(start_date, end_date, '[)') WITH &&
        ) WHERE (status = 'active')
);

-- =============================================================
-- F. ROOM-CHANGE REQUESTS AND RANKED PREFERENCES (2 TABLES)
-- =============================================================
CREATE TABLE IF NOT EXISTS room_change_requests (
    request_id                  TEXT PRIMARY KEY,
    resident_id                 TEXT NOT NULL REFERENCES residents(resident_id),
    created_date                DATE NOT NULL,
    desired_move_date           DATE NOT NULL,
    room_type_id                TEXT NOT NULL REFERENCES room_types(room_type_id),
    max_semester_price_usd      NUMERIC(10,2) NOT NULL CHECK (max_semester_price_usd >= 0),
    preferred_floor_number     INTEGER CHECK (preferred_floor_number > 0),
    status                      TEXT NOT NULL
                                    CHECK (status IN ('draft', 'pending', 'approved', 'rejected', 'cancelled')),
    demo_scenario               TEXT NOT NULL DEFAULT '',
    synthetic_record            BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT request_dates_valid CHECK (desired_move_date >= created_date)
);

-- Our V1 generator creates at most one pending request per resident.
CREATE UNIQUE INDEX IF NOT EXISTS unique_pending_request_per_resident
    ON room_change_requests (resident_id) WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS request_preferences (
    preference_id           TEXT PRIMARY KEY,
    request_id              TEXT NOT NULL
                                REFERENCES room_change_requests(request_id) ON DELETE CASCADE,
    building_id             TEXT NOT NULL REFERENCES buildings(building_id),
    rank                    INTEGER NOT NULL CHECK (rank > 0),
    synthetic_record        BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT unique_preference_rank UNIQUE (request_id, rank),
    CONSTRAINT unique_preferred_building UNIQUE (request_id, building_id)
);

-- =============================================================
-- G. BASIC LOOKUP INDEXES
-- =============================================================
CREATE INDEX IF NOT EXISTS idx_occupancy_term ON occupancy_observations(term_code);
CREATE INDEX IF NOT EXISTS idx_buildings_property ON buildings(property_code);
CREATE INDEX IF NOT EXISTS idx_floors_building ON floors(building_id);
CREATE INDEX IF NOT EXISTS idx_rooms_floor ON rooms(floor_id);
CREATE INDEX IF NOT EXISTS idx_beds_room ON beds(room_id);
CREATE INDEX IF NOT EXISTS idx_rates_building_type ON housing_rates(building_id, room_type_id);
CREATE INDEX IF NOT EXISTS idx_assignments_resident ON bed_assignments(resident_id);
CREATE INDEX IF NOT EXISTS idx_staff_floor ON staff_floor_assignments(floor_id);
CREATE INDEX IF NOT EXISTS idx_requests_resident ON room_change_requests(resident_id);
CREATE INDEX IF NOT EXISTS idx_preferences_building ON request_preferences(building_id);

COMMIT;

-- IMPORTANT:
-- (1) This creates the schema ONLY, not the data. The next task is loading CSVs.
-- (2) The Python generator additionally validates bed capacity and valid room
--     type/rate per building. Those cross-table business rules require database
--     triggers or carefully controlled application procedures if they must be
--     enforced on every direct database write.
-- (3) Empty CSV fields, e.g. preferred_floor_number = '', must become SQL NULL
--     during loading. Loading raw CSV fields into integer columns without an
--     adapter can fail. Do not assume all CSVs can be COPY'd directly.
