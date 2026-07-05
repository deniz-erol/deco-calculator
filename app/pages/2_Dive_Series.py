"""Dive Series — build an ordered list of repetitive (consecutive) dives,
each with a surface interval before it (first dive = none), plan the
whole series via ``plan_series``, and optionally save it to a profile.
"""

from __future__ import annotations

import os as _os, sys as _sys
_root = _os.path.dirname(_os.path.abspath(__file__))
while _root != _os.path.dirname(_root) and not (
    _os.path.isdir(_os.path.join(_root, "app")) and _os.path.isdir(_os.path.join(_root, "engine"))
):
    _root = _os.path.dirname(_root)
if _root not in _sys.path:
    _sys.path.insert(0, _root)

from dataclasses import replace

import streamlit as st

from app._chart import build_profile_chart
from app._i18n import t
from app._shared import (
    depth_label,
    depth_to_display,
    depth_to_fsw,
    format_depth_both,
    gas_label,
    has_provenance_warning,
    render_disclaimer,
    render_provenance_banner,
    render_result_warnings,
    render_sidebar_toggles,
)
from app.store import DiveSeries, JsonProfileStore, ProfileStoreError, UserProfile, UserProfileData
from engine.lookup import TableRangeError
from engine.planner import plan_series
from engine.types import Dive, GasMix

st.set_page_config(page_title="Dive Series", page_icon="🔁", layout="wide")

st.title(t("dive_series_page_title"))
render_disclaimer()

units, _lang = render_sidebar_toggles(st.sidebar)
st.sidebar.divider()
st.sidebar.caption(t("dive_series_sidebar_caption"))

SERIES_KEY = "series_dives"
if SERIES_KEY not in st.session_state:
    st.session_state[SERIES_KEY] = []  # list[dict]: gas_kind, fo2, fhe, depth_fsw, bt, si

# A series loaded from a profile pre-populates the builder once.
loaded_series = st.session_state.pop("loaded_series", None)
if loaded_series is not None:
    st.session_state[SERIES_KEY] = loaded_series

st.subheader(t("build_series_header"))
st.caption(t("build_series_caption"))

with st.form("add_dive_form", clear_on_submit=True):
    is_first = len(st.session_state[SERIES_KEY]) == 0
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
    with c1:
        gas_kind = st.selectbox(
            t("gas_label"),
            options=["air", "nitrox", "heliox"],
            format_func=gas_label,
        )
    with c2:
        o2_pct = 21.0
        if gas_kind == "nitrox":
            o2_pct = st.number_input(
                t("o2_pct_label"), min_value=21.0, max_value=40.0, value=32.0, step=1.0
            )
        elif gas_kind == "heliox":
            o2_pct = st.number_input(
                t("o2_pct_heliox_label"), min_value=10.0, max_value=50.0, value=20.0, step=0.5
            )
        else:
            st.text_input(t("o2_pct_label"), value=t("o2_pct_air_display"), disabled=True)
    with c3:
        display_depth = st.number_input(f"{depth_label(units)}", min_value=0.0, value=80.0, step=1.0)
    with c4:
        bottom_time_min = st.number_input(t("bottom_time_label"), min_value=1.0, value=20.0, step=1.0)
    with c5:
        surface_interval_min = st.number_input(
            t("surface_interval_before_label"),
            min_value=0.0,
            value=60.0,
            step=5.0,
            disabled=is_first,
            help=t("surface_interval_before_help"),
        )

    submitted = st.form_submit_button(t("add_dive_button"))
    if submitted:
        depth_fsw = depth_to_fsw(display_depth, units)
        fo2 = o2_pct / 100.0
        fhe = 0.0
        if gas_kind == "heliox":
            fhe = 1.0 - fo2
        elif gas_kind == "air":
            fo2 = 0.21

        try:
            GasMix(fo2=fo2, fhe=fhe)  # validated fully when Dive is built for planning
        except ValueError as exc:
            st.error(t("invalid_gas_mix_error", error=exc))
        else:
            st.session_state[SERIES_KEY].append(
                {
                    "gas_kind": gas_kind,
                    "fo2": fo2,
                    "fhe": fhe,
                    "depth_fsw": depth_fsw,
                    "bottom_time_min": bottom_time_min,
                    "surface_interval_before_min": None if is_first else surface_interval_min,
                }
            )
            st.rerun()

# ---------------------------------------------------------------------------
# Render the current builder list with remove/clear controls.
# ---------------------------------------------------------------------------
if st.session_state[SERIES_KEY]:
    st.subheader(t("series_so_far_header"))
    for i, entry in enumerate(st.session_state[SERIES_KEY]):
        cols = st.columns([1, 1, 1, 1, 1, 0.6])
        cols[0].write(f"**#{i + 1}** {gas_label(entry['gas_kind'])}")
        cols[1].write(format_depth_both(entry["depth_fsw"]))
        cols[2].write(t("series_entry_bottom_min", minutes=entry["bottom_time_min"]))
        si = entry["surface_interval_before_min"]
        cols[3].write(
            t("series_entry_first_no_si") if si is None else t("series_entry_si", minutes=si)
        )
        cols[4].write(t("series_entry_o2", pct=entry["fo2"] * 100))
        if cols[5].button(t("remove_button"), key=f"remove_{i}"):
            st.session_state[SERIES_KEY].pop(i)
            st.rerun()

    if st.button(t("clear_series_button")):
        st.session_state[SERIES_KEY] = []
        st.rerun()
else:
    st.info(t("no_dives_added_info"))

st.divider()

# ---------------------------------------------------------------------------
# Plan the series.
# ---------------------------------------------------------------------------
results = []
dives: list[Dive] = []
if st.session_state[SERIES_KEY]:
    st.subheader(t("chained_results_header"))
    try:
        for entry in st.session_state[SERIES_KEY]:
            dives.append(
                Dive(
                    gas=GasMix(fo2=entry["fo2"], fhe=entry["fhe"]),
                    max_depth_fsw=entry["depth_fsw"],
                    bottom_time_min=entry["bottom_time_min"],
                    surface_interval_before_min=entry["surface_interval_before_min"],
                )
            )
        results = plan_series(dives)
    except (ValueError, TableRangeError) as exc:
        st.error(t("plan_series_engine_error", error=exc))
        results = []

    # A single, translated provenance disclaimer for the whole series —
    # rendered once here (not once per dive) even though every dive in a
    # repetitive chain typically touches multiple seeded tables (9-7,
    # 9-8, 9-9) that would otherwise each carry their own warning.
    if any(has_provenance_warning(result) for result in results):
        render_provenance_banner()

    for i, (entry, result) in enumerate(zip(st.session_state[SERIES_KEY], results)):
        with st.expander(
            t(
                "dive_expander_title",
                index=i + 1,
                gas=gas_label(entry["gas_kind"]),
                depth=format_depth_both(entry["depth_fsw"]),
                minutes=entry["bottom_time_min"],
            ),
            expanded=(i == len(results) - 1),
        ):
            render_result_warnings(result)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric(
                t("status_label"),
                t("status_no_deco") if result.no_decompression else t("status_deco"),
            )
            m2.metric(t("ending_group_label"), result.repetitive_group or t("not_applicable"))
            m3.metric(
                t("rnt_applied_label"),
                f"{result.residual_nitrogen_time_min:g}"
                if result.residual_nitrogen_time_min is not None
                else "—",
            )
            m4.metric(t("total_stop_time_label"), f"{result.total_stop_min:g}")

            if result.stops:
                schedule_rows = [
                    {
                        t("col_stop_depth"): format_depth_both(s.depth_fsw),
                        t("col_minutes"): s.minutes,
                        t("col_gas_phase"): s.gas_phase,
                    }
                    for s in result.stops
                ]
                st.dataframe(schedule_rows, use_container_width=True, hide_index=True)
            else:
                st.success(t("no_deco_stops_success_short"))

            chart = build_profile_chart(
                max_depth_fsw=result.actual_depth_fsw or entry["depth_fsw"],
                bottom_time_min=entry["bottom_time_min"],
                result=result,
                units=units,
                depth_converter=lambda fsw: depth_to_display(fsw, units),
            )
            st.altair_chart(chart, use_container_width=True)
            st.caption(t("chart_units_caption", axis_unit=depth_label(units)))
            st.caption(t("idealized_plan_caption"))

st.divider()

# ---------------------------------------------------------------------------
# Save to a profile.
# ---------------------------------------------------------------------------
st.subheader(t("save_series_header"))
if not st.session_state[SERIES_KEY]:
    st.caption(t("save_series_need_dive_caption"))
else:
    store = JsonProfileStore()
    existing_users = store.list_users()

    # Stable internal sentinel for "create a new user"; only the
    # on-screen label is translated (format_func), so the
    # `user_choice == NEW_USER_SENTINEL` checks below keep working
    # regardless of the active language.
    NEW_USER_SENTINEL = "__new_user__"

    save_col1, save_col2, save_col3 = st.columns([1, 1, 1])
    with save_col1:
        user_choice = st.selectbox(
            t("user_label"),
            options=[NEW_USER_SENTINEL] + existing_users,
            format_func=lambda u: t("new_user_option") if u == NEW_USER_SENTINEL else u,
        )
    with save_col2:
        new_user_id = ""
        new_user_name = ""
        if user_choice == NEW_USER_SENTINEL:
            new_user_id = st.text_input(t("new_user_id_label"))
            new_user_name = st.text_input(t("new_user_display_name_label"))
    with save_col3:
        series_label = st.text_input(t("series_label_label"), value=t("series_label_default"))

    if st.button(t("save_series_button"), type="primary"):
        user_id = new_user_id.strip() if user_choice == NEW_USER_SENTINEL else user_choice
        user_name = new_user_name.strip() if user_choice == NEW_USER_SENTINEL else user_choice

        if not user_id:
            st.error(t("user_id_required_error"))
        else:
            try:
                if store.exists(user_id):
                    data = store.load(user_id)
                else:
                    data = UserProfileData(user=UserProfile(id=user_id, name=user_name or user_id))

                new_series = DiveSeries(
                    id=f"series-{len(data.series) + 1}",
                    label=series_label or t("series_label_default"),
                    dives=tuple(dives),
                )
                updated = replace(data, series=data.series + (new_series,))
                store.save(updated)
                st.success(t("series_saved_success", label=series_label, user_id=user_id))
            except ProfileStoreError as exc:
                st.error(t("profile_save_error", error=exc))
