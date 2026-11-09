# Implemented HousingOps relational model

**Milestone 2, 16 PostgreSQL tables.** This is the implemented structure in [`sql/01_schema.sql`](../sql/01_schema.sql), not only the provisional Milestone 1 diagram. Two diagrams separate historical/reference information from operational workflows for readability. Cardinalities below use one-to-many relationships; mandatory references are enforced by `NOT NULL` foreign keys.

## A. Public historical occupancy and physical inventory

```mermaid
erDiagram
    housing_properties ||--o{ occupancy_observations : records
    academic_terms ||--o{ occupancy_observations : measures
    housing_properties ||--o{ buildings : corresponds_to
    source_register ||--o{ buildings : profiles
    buildings ||--o{ floors : contains
    floors ||--o{ rooms : contains
    rooms ||--o{ beds : contains
    room_types ||--o{ rooms : identifies
    buildings ||--o{ housing_rates : has
    room_types ||--o{ housing_rates : priced_as
    source_register ||--o{ housing_rates : attributes
    housing_properties {
       string property_code PK
       string property_name
       string living_style
    }
    academic_terms {
       string term_code PK
       string term_name
       int calendar_year
       string season
    }
    occupancy_observations {
       string property_code PK,FK
       string term_code PK,FK
       int occupied_spaces
       string source_file
    }
    source_register {
       string source_id PK
       string source_name
       int source_year
    }
    buildings {
       string building_id PK
       string property_code FK
       string profile_source_id FK
       string building_name
    }
    floors {
       string floor_id PK
       string building_id FK
       int floor_number
    }
    room_types {
       string room_type_id PK
       string room_type_name
       int beds_per_room
    }
    rooms {
       string room_id PK
       string floor_id FK
       string room_type_id FK
       string room_number
    }
    beds {
       string bed_id PK
       string room_id FK
       string bed_label
    }
    housing_rates {
       string housing_rate_id PK
       string building_id FK
       string room_type_id FK
       string source_id FK
       decimal semester_rate_usd
       string academic_year
    }
```

The 25 historical housing properties and six terms form **150 observations**, keyed by `(property_code, term_code)`. Only four source-linked named buildings are included in the **synthetic** room/bed inventory. This separation avoids representing source-level occupied-space totals as detailed 2026 room assignments.

## B. Housing operations, RA coverage and requests

```mermaid
erDiagram
    residents ||--o{ bed_assignments : holds
    beds ||--o{ bed_assignments : is_assigned_in
    staff ||--o{ staff_floor_assignments : covers
    floors ||--o{ staff_floor_assignments : is_covered_in
    residents ||--o{ room_change_requests : creates
    room_types ||--o{ room_change_requests : asks_for
    room_change_requests ||--o{ request_preferences : ranks
    buildings ||--o{ request_preferences : is_preferred_in
    residents {
       string resident_id PK
       string display_name
       string eligibility_group
       string student_level
    }
    bed_assignments {
       string assignment_id PK
       string resident_id FK
       string bed_id FK
       date start_date
       date end_date
       string status
    }
    beds {
       string bed_id PK
       string room_id FK
    }
    staff {
       string staff_id PK
       string display_name
       string role
    }
    floors {
       string floor_id PK
       string building_id FK
    }
    staff_floor_assignments {
       string staff_floor_assignment_id PK
       string staff_id FK
       string floor_id FK
       date start_date
       date end_date
       string status
    }
    room_types {
       string room_type_id PK
       string room_type_name
    }
    room_change_requests {
       string request_id PK
       string resident_id FK
       string room_type_id FK
       date desired_move_date
       decimal max_semester_price_usd
       string status
    }
    request_preferences {
       string preference_id PK
       string request_id FK
       string building_id FK
       int rank
    }
    buildings {
       string building_id PK
       string building_name
    }
```

## Design choices

- **Normalization:** Historical observations reference property and term rather than repeating their labels. Room, bed, floor, and building records are distinct physical levels. A request's preferred buildings are **separate ranked rows**, not a comma-separated field. Semester rates are separate by building, room type, and academic year.
- **Primary keys and cardinalities:** An observation has composite PK `(property_code, term_code)`. All other tables have individual text identifiers. Each child points to one parent; a parent may have zero or many children. `UNIQUE` rules additionally protect one room number per floor, bed label per room, rank per request, and rate per combination.
- **Date integrity:** Confirmed bed assignments cannot overlap for the same bed **or resident**; active RA floor assignments cannot overlap for the same staff member, using `btree_gist` exclusion constraints on half-open date intervals `[start_date, end_date)`.
- **CRUD rules:** `request_preferences.request_id` references its request with `ON DELETE CASCADE`, enabling safe deletion of a fictional draft/test request and its preferences. A partial unique index permits at most one **pending** request per resident.
- **Scope/limitations:** The fictional staff-coverage policy allows multiple RAs to cover one floor but prevents one RA from serving overlapping floors. Cross-table hall/rate eligibility is validated by the Python generator/loader; it is not fully protected from arbitrary direct SQL writes. The matching SQL proposes candidate beds but does not perform a transactional room transfer.

For the complete field types, keys, and constraints, consult the executable [schema](../sql/01_schema.sql).
