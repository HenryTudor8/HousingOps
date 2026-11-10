# Room-change workflow: read-only preview and database handoff

This document separates the student team's work according to the **original Milestone 1 proposal**: Sanchit initially owns housing administrator workflows, Streamlit UX and dashboard; Viswambhara initially owns PostgreSQL joins, SQL query validation and database consistency. Both jointly review transaction behavior and final integration. These divisions are a suggested practical handoff, **not evidence of work already completed by Viswambhara**.

## Current work on SanBranch: Sanchit / administrator workflow

- `app/workflow.py`: pure `build_transfer_preview()` checks an existing **pending** request, chosen candidate from full-stay SQL matches, correct resident and budget, a single active source assignment that spans the move date, and a distinct destination bed. It proposes shortening the old assignment, opening a new assignment, and changing the request to `approved`. **It does not execute these operations.**
- `app/workflow_repository.py`: **SELECT-only** request and source assignment snapshots, using bound parameters and the read-only database accessor.
- `app/dashboard.py`: optional `Preview a possible transfer` expander in the existing matching view. It renders proposed changes without `INSERT`, `UPDATE`, or `DELETE`.
- `tests/test_workflow.py` and `tests/test_workflow_repository.py`: offline preflight and query contract tests. They do not require Neon or write to the database.

## Deliberately unimplemented: database-owned workstream for Viswambhara

The original proposal assigned SQL queries, schema consistency and database constraints to Viswambhara. A suitable independent next task to **discuss and confirm with her** is a transaction-safe room-transfer service with tests, such as `app/transfer_service.py` or a PostgreSQL function with a clearly documented Python caller.

Proposed acceptance criteria:

1. Use a **separate disposable Neon development branch** with fictional seed data, not the existing production/demo database.
2. Start an explicit PostgreSQL transaction. Lock the pending request and source assignment, validate its current status and effective dates, and recheck destination eligibility, prices, ranked preference and entire-stay availability **inside the transaction**. The read-only preview is not authoritative.
3. Prevent race conditions, including two approvals for the same destination. Existing GiST exclusion constraints must remain enabled. Account for concurrent request approvals using appropriate locks/serialization and deterministic tests.
4. Either commit the entire transfer (shorten/adjust source assignment, create destination assignment with a unique key, update request status) or roll back all changes. Handle invalid dates, one resident moving twice, and duplicate approval attempts. A future reservation/assignment and same-day edge cases should be treated explicitly.
5. Confirm schema business policy for how a room change affects an assignment extending beyond the chosen stay end. Do not silently truncate or discard valid existing future allocations.
6. Write **real PostgreSQL integration tests** for success and failure/rollback, including conflicting concurrent writes. Unit mocks alone are insufficient. Do not run the write tests in production.
7. Add an audit or change-history plan, and grant write privileges only to an appropriate authorized development role. A public read-only visitor must never see approval controls.

Once the database service has been independently developed and tested, both teammates integrate it with a protected administrator workflow and review the demonstration together. The Streamlit preview should remain read-only until that integration is explicitly reviewed.

## Why previews can be rejected

The current conservative preflight deliberately refuses requests without a single confirmed existing assignment overlapping the future stay, existing assignments starting exactly on the move date, multiple overlapping/future assignments, absent/stale candidate beds, and invalid budgets/dates. Such cases require stronger policies, not guessed SQL mutations.

A successful preview means only that **the values returned by these SELECT queries passed application checks at that moment**. It is not a lock, reservation, authorization decision or guarantee that the transaction will succeed.

## How to run locally

With current Neon credentials in an ignored `.env`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_workflow.py tests\test_workflow_repository.py -v
.\.venv\Scripts\python.exe -m streamlit run app/dashboard.py
```

Select **Room-change matching**, pick a pending request and a proposed stay end, then open **Preview a possible transfer** and choose a ranked candidate bed.

**No writes occur** in this development increment. All representative residents, staff, rooms and assignments are synthetic.
