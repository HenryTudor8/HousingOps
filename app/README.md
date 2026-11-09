# HousingOps Streamlit application (future milestone)

**Milestone 2 delivers the database, loader, SQL, integrity tests, and evidence, not a user interface.** A browser-based Streamlit application is planned for subsequent development and the December 13, 2026 final demonstration.

Planned administrator workflows:
1. View current and future bed vacancies using dated SQL assignments.
2. Find floors lacking active RA coverage.
3. Create and review room-change requests, ranked recommendations, and semester prices.
4. Approve room moves through a **single transaction** that updates both bed assignments and request status.
5. Visualize public historical occupancy separately from fictional 2026-27 operations.

The existing query implementations are under [`sql/`](../sql/README.md). Do not claim room moves are committed by `03_room_change_matching.sql`, which is a recommendation-only SELECT.
