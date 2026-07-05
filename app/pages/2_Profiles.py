"""Profiles — list, load, and delete this browser's saved dive series.

Profiles are stored entirely in the visitor's own browser localStorage
(see ``app._local_store``): private per device, never sent to or read
from the server, and never visible to any other visitor.
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
from app._local_store import LocalStoreError, delete_profile, list_profiles, load_profile
from app._shared import format_depth_both, gas_label, render_disclaimer, render_sidebar_toggles

st.set_page_config(page_title="Profiles", page_icon="👤", layout="wide")

st.title(t("profiles_page_title"))
render_disclaimer()

units, _lang = render_sidebar_toggles(st.sidebar)

# ---------------------------------------------------------------------------
# Deferred delete: the delete button below only stages a name and reruns —
# it never calls the localStorage component's setItem in the same script
# run that also calls st.rerun(). st.rerun() aborts the current run
# immediately, before the component's frontend iframe has had a chance to
# actually flush its write to the browser's real localStorage, so a
# "delete then rerun in one go" would silently not persist (the deleted
# profile would reappear on the next real page load). Applying the
# pending delete here, at the very top of the *next* run — with no
# st.rerun() after it — lets that run finish normally and the write land.
# ---------------------------------------------------------------------------
pending_delete = st.session_state.pop("_pending_delete_profile", None)
if pending_delete:
    try:
        delete_profile(pending_delete)
        st.success(t("profile_deleted_success", profile_name=pending_delete))
    except LocalStoreError as exc:
        st.error(t("profile_delete_error", error=exc))

st.subheader(t("saved_profiles_header"))
st.caption(t("profiles_privacy_caption"))

profile_names = list_profiles()

if not profile_names:
    st.info(t("no_profiles_info"))
else:
    for name in profile_names:
        try:
            payload = load_profile(name)
        except LocalStoreError as exc:
            st.error(t("profile_load_error", profile_name=name, error=exc))
            continue

        dives = payload.get("dives", [])
        label = payload.get("label") or name

        with st.expander(t("series_expander_title", label=f"{name} — {label}", count=len(dives))):
            for i, dive in enumerate(dives):
                st.write(
                    t(
                        "dive_summary_line",
                        index=i + 1,
                        gas=gas_label(dive["gas_kind"]),
                        depth=format_depth_both(dive["depth_fsw"]),
                        minutes=dive["bottom_time_min"],
                    )
                    + (
                        t("dive_summary_si", minutes=dive["surface_interval_before_min"])
                        if dive.get("surface_interval_before_min") is not None
                        else t("dive_summary_first_no_si")
                    )
                )

            load_col, load_first_col, delete_col = st.columns([1, 1, 1])
            with load_col:
                if st.button(t("load_into_series_button"), key=f"load_{name}"):
                    st.session_state["loaded_series"] = dives
                    st.success(t("series_loaded_success"))
            with load_first_col:
                if dives and st.button(t("load_first_into_plan_button"), key=f"load_first_{name}"):
                    first = dives[0]
                    st.session_state["plan_dive_prefill"] = {
                        "gas_kind": first["gas_kind"],
                        "o2_pct": first["fo2"] * 100.0,
                        "max_depth_fsw": first["depth_fsw"],
                        "bottom_time_min": first["bottom_time_min"],
                    }
                    st.success(t("first_dive_loaded_success"))
            with delete_col:
                if st.button(t("delete_profile_button"), key=f"delete_{name}"):
                    # Stage the delete for the top of the next run (see
                    # comment above) instead of writing and rerunning here.
                    st.session_state["_pending_delete_profile"] = name
                    st.rerun()
