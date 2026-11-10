"""HousingOps read-only Streamlit dashboard. Run: python -m streamlit run app/dashboard.py."""
from __future__ import annotations
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from app import repository, workflow_repository
from app.workflow import TransferPreflightError, build_transfer_preview
from app.logic import DEMO_DATE, DEFAULT_STAY_END, as_currency, scenario_totals, sum_column

st.set_page_config(page_title="HousingOps | Decision Support", page_icon="🏠", layout="wide")
st.title("🏠 HousingOps")
st.caption("Student housing decision support | Read-only PostgreSQL prototype")

with st.sidebar:
    st.header("Explore")
    page = st.radio(
        "View",
        ("Overview", "Bed availability", "RA coverage", "Room-change matching", "Historical occupancy"),
    )
    as_of = st.date_input(
        "Operational reference date", value=DEMO_DATE,
        help="The fictional dataset was generated for 2026-10-28. Other dates query the same stored assignment intervals.",
    )
    st.divider()
    st.info("All residents, room layouts, assignments, RA schedules and requests are FICTIONAL. Only 2022–24 historical aggregate counts are observed public data.")

if not isinstance(as_of, date):
    st.error("Select one valid reference date.")
    st.stop()


def show_table(rows, empty_message="No matching rows."):
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info(empty_message)


def overview():
    st.subheader("Operational overview")
    st.write("Modeled beds and confirmed fictional assignments on the selected date, not real institutional vacancies.")
    rows = repository.inventory_on(as_of)
    if not rows:
        st.info("No modeled buildings are available.")
        return
    a, b, c = st.columns(3)
    a.metric("Modeled beds", sum_column(rows, "total_beds"))
    b.metric("Occupied", sum_column(rows, "occupied_beds"))
    c.metric("Available", sum_column(rows, "available_beds"))
    frame = pd.DataFrame(rows).set_index("building_name")
    st.bar_chart(frame[["occupied_beds", "available_beds"]], stack=True)
    show_table(rows)


def availability():
    st.subheader("Bed availability snapshots")
    st.write("Compare vacancies today, and 7, 14, and 30 days later. A snapshot is not a full-stay guarantee.")
    rows = repository.vacancy_checkpoints(as_of)
    if not rows:
        st.info("No modeled beds found.")
        return
    totals = scenario_totals(rows)
    cards = st.columns(4)
    for col, label in zip(cards, ("Today", "+7 days", "+14 days", "+30 days")):
        col.metric(label, totals.get(label, 0))
    chart = pd.DataFrame(rows).pivot(index="building_name", columns="checkpoint", values="available_beds")
    st.bar_chart(chart.reindex(columns=["Today", "+7 days", "+14 days", "+30 days"]))
    show_table(rows)


def ra_coverage():
    st.subheader("RA floor coverage")
    rows = repository.ra_coverage_on(as_of)
    gaps = [row for row in rows if not row["covered"]]
    a, b, c = st.columns(3)
    a.metric("Floors", len(rows))
    b.metric("Covered", len(rows) - len(gaps))
    c.metric("Uncovered", len(gaps))
    st.markdown("#### Uncovered floors")
    show_table(
        [{"building_name": r["building_name"], "floor_number": r["floor_number"]} for r in gaps],
        "Every modeled floor has active RA coverage on this date.",
    )
    with st.expander("All floor coverage records"):
        show_table(rows)
    st.caption("RA schedules and the coverage policy are deliberately fictional.")


def matching():
    st.subheader("Room-change recommendations")
    st.write("Select a pending fictional request. Candidates respect its preference rank, eligibility, room type, price ceiling and full proposed stay.")
    requests = repository.pending_requests()
    if not requests:
        st.info("No pending requests were found.")
        return
    by_id = {r["request_id"]: r for r in requests}
    selected = st.selectbox("Pending request", list(by_id))
    request = by_id[selected]
    st.caption(
        f"Scenario: {request['demo_scenario']} | Move date: {request['desired_move_date']} | "
        f"Room type: {request['room_type_name']} | Max semester price: {as_currency(request['max_semester_price_usd'])}"
    )
    end = st.date_input("Proposed stay end (exclusive)", value=DEFAULT_STAY_END, key="end_date")
    if not isinstance(end, date) or end <= request["desired_move_date"]:
        st.warning("The proposed stay end must follow the request's desired move date.")
        return
    rows = repository.matching_beds(selected, request["desired_move_date"], end)
    st.metric("Eligible candidate beds", len(rows))
    show_table(rows, "No candidate bed meets all constraints throughout this stay.")
    if rows:
        with st.expander("Preview a possible transfer (no database changes)"):
            st.caption(
                "This is a preflight review, not an approval. A separate transactional "
                "database implementation is still needed before any room can be transferred."
            )
            by_bed = {str(row["bed_id"]): row for row in rows}
            destination = st.selectbox(
                "Candidate bed", options=list(by_bed),
                format_func=lambda bed: (
                    f"{bed} | {by_bed[bed]['building_name']} "
                    f"room {by_bed[bed]['room_number']}"
                ), key="transfer_preview_bed",
            )
            if st.button("Build read-only transfer preview", key="preview_transfer"):
                current = workflow_repository.request_context_for_preview(selected)
                if current is None:
                    st.error("The request is no longer available. Refresh the request list.")
                else:
                    assignments = workflow_repository.resident_assignments_for_preview(selected, end)
                    try:
                        proposal = build_transfer_preview(
                            request=current,
                            candidate=by_bed[destination],
                            eligible_beds=rows,
                            intersecting_assignments=assignments,
                            stay_end=end,
                        )
                    except TransferPreflightError as exc:
                        st.warning(str(exc))
                    else:
                        st.success("Preflight checks passed for this read-only snapshot.")
                        st.write(
                            f"Resident {proposal.resident_id}: proposed move to "
                            f"{proposal.destination_building}, room {proposal.destination_room} "
                            f"({proposal.destination_bed_id})."
                        )
                        st.dataframe(
                            pd.DataFrame(proposal.as_rows()),
                            hide_index=True,
                            use_container_width=True,
                        )
                        st.info(
                            "No INSERT, UPDATE or DELETE occurred. A real approval must "
                            "recheck availability under appropriate transaction locking."
                        )
    st.warning("Read-only results: this page cannot reserve beds, approve moves or change resident records.")


def history():
    st.subheader("Historical occupancy (public 2022–24 data)")
    st.write("Observed occupied-space counts, not vacancy rates, forecasts or the fictional 2026–27 room inventory.")
    rows = repository.historical_totals()
    if not rows:
        st.info("No historical occupancy observations found.")
        return
    st.bar_chart(pd.DataFrame(rows).set_index("term_name")["total_occupied_spaces"])
    show_table(rows)
    with st.expander("Property-level records"):
        details = repository.historical_by_property()
        if details:
            property_name = st.selectbox("Property", sorted({r["property_name"] for r in details}))
            show_table([r for r in details if r["property_name"] == property_name])
        else:
            st.info("No property-level records.")


try:
    if page == "Overview":
        overview()
    elif page == "Bed availability":
        availability()
    elif page == "RA coverage":
        ra_coverage()
    elif page == "Room-change matching":
        matching()
    else:
        history()
except repository.DatabaseNotConfigured as exc:
    st.error(str(exc))
    st.stop()
except Exception:
    st.error(
        "Could not read the database. Check the private .env connection string, "
        "Neon branch status and schema. Raw database errors are hidden for security."
    )
    st.stop()
