"""Profiles — pick or create a user, list their saved series, and load
one back into the Plan Dive / Dive Series pages.
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

import streamlit as st

from app._i18n import t
from app._shared import format_depth, gas_label, render_disclaimer, render_sidebar_toggles
from app.store import JsonProfileStore, ProfileStoreError, UserProfile, UserProfileData

st.set_page_config(page_title="Profiles", page_icon="👤", layout="wide")

st.title(t("profiles_page_title"))
render_disclaimer()

units, _lang = render_sidebar_toggles(st.sidebar)

store = JsonProfileStore()

st.subheader(t("choose_user_header"))
existing_users = store.list_users()

# Mode is a stable internal value ("existing" | "new"); only the
# on-screen label is translated via format_func, so the `mode == ...`
# comparisons below keep working regardless of the active language.
MODE_EXISTING = "existing"
MODE_NEW = "new"

col1, col2 = st.columns([1, 2])
with col1:
    mode = st.radio(
        t("mode_label"),
        options=[MODE_EXISTING, MODE_NEW],
        format_func=lambda m: t("mode_existing_user") if m == MODE_EXISTING else t("mode_create_new_user"),
        horizontal=False,
    )

selected_user_id: str | None = None
if mode == MODE_EXISTING:
    with col1:
        if not existing_users:
            st.info(t("no_profiles_info"))
        else:
            selected_user_id = st.selectbox(t("user_label"), options=existing_users)
else:
    with col1:
        new_id = st.text_input(t("new_user_id_label"))
        new_name = st.text_input(t("display_name_label"))
        if st.button(t("create_profile_button")):
            if not new_id.strip():
                st.error(t("user_id_required_error2"))
            else:
                try:
                    if store.exists(new_id.strip()):
                        st.warning(t("profile_already_exists_warning", user_id=new_id.strip()))
                    else:
                        store.save(
                            UserProfileData(
                                user=UserProfile(id=new_id.strip(), name=new_name.strip() or new_id.strip())
                            )
                        )
                        st.success(t("profile_created_success", user_id=new_id.strip()))
                        st.rerun()
                except ProfileStoreError as exc:
                    st.error(t("profile_create_error", error=exc))

if selected_user_id:
    st.divider()
    try:
        data = store.load(selected_user_id)
    except ProfileStoreError as exc:
        st.error(t("profile_load_error", user_id=selected_user_id, error=exc))
    else:
        st.subheader(t("saved_series_header", name=data.user.name))
        if not data.series:
            st.info(t("no_series_saved_info"))
        else:
            for series in data.series:
                with st.expander(
                    t("series_expander_title", label=series.label, count=len(series.dives))
                ):
                    for i, dive in enumerate(series.dives):
                        st.write(
                            t(
                                "dive_summary_line",
                                index=i + 1,
                                gas=gas_label(dive.gas.kind),
                                depth=format_depth(dive.max_depth_fsw, units),
                                minutes=dive.bottom_time_min,
                            )
                            + (
                                t("dive_summary_si", minutes=dive.surface_interval_before_min)
                                if dive.surface_interval_before_min is not None
                                else t("dive_summary_first_no_si")
                            )
                        )

                    if st.button(t("load_into_series_button"), key=f"load_{series.id}"):
                        st.session_state["loaded_series"] = [
                            {
                                "gas_kind": dive.gas.kind,
                                "fo2": dive.gas.fo2,
                                "fhe": dive.gas.fhe,
                                "depth_fsw": dive.max_depth_fsw,
                                "bottom_time_min": dive.bottom_time_min,
                                "surface_interval_before_min": dive.surface_interval_before_min,
                            }
                            for dive in series.dives
                        ]
                        st.success(t("series_loaded_success"))

                    if series.dives:
                        first = series.dives[0]
                        if st.button(t("load_first_into_plan_button"), key=f"load_first_{series.id}"):
                            st.session_state["plan_dive_prefill"] = {
                                "gas_kind": first.gas.kind,
                                "o2_pct": first.gas.fo2 * 100.0,
                                "max_depth_fsw": first.max_depth_fsw,
                                "bottom_time_min": first.bottom_time_min,
                            }
                            st.success(t("first_dive_loaded_success"))
