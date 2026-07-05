"""Planner — unified single-dive / repetitive-series planner.

Opens as one dive: gas selector, depth + bottom-time **number inputs**
(steppers), the units toggle + both-units caption, the step control, live
result, and the realistic profile chart with chart-drag staging for that
active dive. A "+ Add repetitive dive" button commits the current dive
and opens a fresh one, gaining an editable surface-interval input before
it; each committed dive's surface interval stays editable in place and
each dive is individually removable. The result view adapts to the dive
count: exactly one dive renders the single-dive summary view; two or
more render the chained series view (each dive's result with Residual
Nitrogen Time applied from the prior dive + surface interval), reusing
the same ``plan_series`` chaining engine call either way.

Depth and bottom time are entered via ``st.number_input`` (with a
user-adjustable step size) and can also be set by clicking/dragging on
the active dive's profile chart. Both input paths write into the same
``st.session_state`` keys that back the number inputs, so the inputs and
the chart stay in two-way sync.
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

from dataclasses import replace as dc_replace

import altair as alt
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
from engine.lookup import TableRangeError, load_table
from engine.planner import plan_series
from engine.types import Dive, GasMix
from engine.units import fsw_to_m

st.set_page_config(page_title="Planner", page_icon="🧭", layout="wide")

st.title(t("planner_page_title"))
render_disclaimer()

units, _lang = render_sidebar_toggles(st.sidebar)

st.sidebar.divider()
st.sidebar.caption(t("planner_sidebar_caption"))

# ---------------------------------------------------------------------------
# Session-state keys.
#
# - PLANNER_DIVES_KEY holds *committed* dives (dive #1..N-1 once at least
#   one repetitive dive has been added) as plain dicts, each carrying a
#   stable "_id" assigned at commit time (PLANNER_NEXT_ID_KEY is the
#   monotonically increasing counter). The stable id — not the list
#   index — backs every per-row widget key, so removing a dive can never
#   cause a later dive's still-mounted surface-interval/remove widgets to
#   silently reattach to the wrong row (the old Dive Series builder had
#   no per-row identity at all, hence "remove and re-add").
# - The *active* dive being entered (the newest, not-yet-committed one)
#   reuses the single-dive-planner's widget keys below, exactly as the
#   original Plan Dive page did, so the chart-drag staging pattern is
#   unchanged.
# ---------------------------------------------------------------------------
PLANNER_DIVES_KEY = "planner_dives"
PLANNER_NEXT_ID_KEY = "planner_next_id"

DEPTH_KEY = "plan_depth_display"
TIME_KEY = "plan_time_min"
STEP_KEY = "plan_step"
UNITS_SEEN_KEY = "plan_units_seen"
CHART_SEL_SIG_KEY = "plan_chart_sel_sig"
CHART_WIDGET_KEY = "plan_profile_chart"
ACTIVE_GAS_KEY = "plan_active_gas_kind"
ACTIVE_O2_KEY = "plan_active_o2_pct"
ACTIVE_HELIOX_O2_KEY = "plan_active_heliox_o2_pct"
ACTIVE_SI_KEY = "plan_active_si_min"
# Plain (non-widget) key holding the active dive's resolved depth in fsw,
# refreshed every run right after the depth widget(s) resolve it — see the
# comment above its assignment below for why this can't just re-read
# DEPTH_KEY (heliox's depth-selectbox never writes DEPTH_KEY).
ACTIVE_DEPTH_FSW_KEY = "plan_active_depth_fsw"
# Staging keys for a pending chart-drag update: the chart is rendered at
# the bottom of the script, well after the depth/time number inputs have
# already been instantiated with `key=DEPTH_KEY` / `key=TIME_KEY` for
# this run — Streamlit raises if you write to a widget's key after that
# widget has been created in the same run. So a chart selection is
# staged here instead, and only applied to the number-input keys at the
# very top of the *next* run, before the inputs are (re)created.
PENDING_DEPTH_KEY = "plan_pending_depth_display"
PENDING_TIME_KEY = "plan_pending_time_min"

MAX_DEPTH_FSW = 190.0
MAX_TIME_MIN = 200.0

if PLANNER_DIVES_KEY not in st.session_state:
    st.session_state[PLANNER_DIVES_KEY] = []  # list[dict]: _id, gas_kind, fo2, fhe, depth_fsw, bottom_time_min, surface_interval_before_min
if PLANNER_NEXT_ID_KEY not in st.session_state:
    st.session_state[PLANNER_NEXT_ID_KEY] = 1

# ---------------------------------------------------------------------------
# Prefill support from the Profiles page: a whole loaded series replaces
# the committed-dives list (all but its last dive) and seeds the active
# dive from the last one; a single prefilled dive seeds the active dive
# only. Both are read (popped) once, at most one applies per run.
# ---------------------------------------------------------------------------
loaded_series = st.session_state.pop("loaded_series", None)
prefill = st.session_state.pop("plan_dive_prefill", None) or {}

if loaded_series:
    st.session_state[PLANNER_DIVES_KEY] = []
    for entry in loaded_series[:-1]:
        entry = dict(entry)
        entry["_id"] = st.session_state[PLANNER_NEXT_ID_KEY]
        st.session_state[PLANNER_NEXT_ID_KEY] += 1
        st.session_state[PLANNER_DIVES_KEY].append(entry)
    last = loaded_series[-1]
    prefill = {
        "gas_kind": last["gas_kind"],
        "o2_pct": last["fo2"] * 100.0,
        "max_depth_fsw": last["depth_fsw"],
        "bottom_time_min": last["bottom_time_min"],
    }
    if last.get("surface_interval_before_min") is not None:
        st.session_state[ACTIVE_SI_KEY] = float(last["surface_interval_before_min"])

gas_options = ["air", "nitrox", "heliox"]
default_gas_index = gas_options.index(prefill.get("gas_kind", "air"))

# ---------------------------------------------------------------------------
# Seed the depth/time/gas number-input state once (first load, or a fresh
# prefill). The gas selectbox and nitrox O2 input are keyed widgets
# (ACTIVE_GAS_KEY / ACTIVE_O2_KEY): once a keyed widget's key already
# exists in session_state, Streamlit ignores that widget's `index=`/
# `value=` argument on every later run, so a prefill arriving *after*
# the key was first created would otherwise be silently ignored. Seeding
# the key here — before the widgets are instantiated below — is what
# makes a prefill actually take effect. (Heliox's own O2 mix is a
# slider whose min/max bounds are derived from the selected heliox
# depth at render time, so it can't be safely pre-seeded here; a
# heliox prefill still correctly selects the "heliox" gas branch, just
# defaults to that depth's table-window midpoint O2 rather than the
# original dive's exact mix — the same tradeoff heliox depth itself
# already has, since heliox depth is a plain selectbox, not a
# session_state-backed slider like air/nitrox depth.)
# ---------------------------------------------------------------------------
if "gas_kind" in prefill:
    st.session_state[ACTIVE_GAS_KEY] = prefill["gas_kind"]
if "o2_pct" in prefill and prefill.get("gas_kind") == "nitrox":
    st.session_state[ACTIVE_O2_KEY] = float(prefill["o2_pct"])

if "max_depth_fsw" in prefill:
    st.session_state[DEPTH_KEY] = depth_to_display(float(prefill["max_depth_fsw"]), units)
elif DEPTH_KEY not in st.session_state:
    st.session_state[DEPTH_KEY] = depth_to_display(100.0, units)

if "bottom_time_min" in prefill:
    st.session_state[TIME_KEY] = float(prefill["bottom_time_min"])
elif TIME_KEY not in st.session_state:
    st.session_state[TIME_KEY] = 25.0

# ---------------------------------------------------------------------------
# Apply a chart drag staged on the *previous* run, or an "add repetitive
# dive" reset staged by the button's on_click callback. Both must happen
# here, before the depth/time number inputs are instantiated below, or
# Streamlit raises "cannot be modified after the widget ... is
# instantiated".
# ---------------------------------------------------------------------------
if PENDING_TIME_KEY in st.session_state:
    st.session_state[TIME_KEY] = st.session_state.pop(PENDING_TIME_KEY)
if PENDING_DEPTH_KEY in st.session_state:
    st.session_state[DEPTH_KEY] = st.session_state.pop(PENDING_DEPTH_KEY)

# ---------------------------------------------------------------------------
# Reconcile a units-toggle change: the number-input key stores a
# *display-unit* number, so switching ft<->m must convert the stored
# value in place before the widget is built, or the same number gets
# silently reinterpreted in the new unit.
# ---------------------------------------------------------------------------
previous_units = st.session_state.get(UNITS_SEEN_KEY)
if previous_units is not None and previous_units != units:
    stored_fsw = depth_to_fsw(st.session_state[DEPTH_KEY], previous_units)
    st.session_state[DEPTH_KEY] = depth_to_display(stored_fsw, units)
st.session_state[UNITS_SEEN_KEY] = units


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _commit_active_dive() -> None:
    """``on_click`` callback for "Add repetitive dive".

    Runs before the next script run's widgets are instantiated, so it is
    safe here (and only here) to write directly to the depth/time
    widget keys — appending the just-submitted dive as committed, then
    resetting the active-dive inputs to fresh defaults for the next one.
    """
    gas_kind = st.session_state[ACTIVE_GAS_KEY]
    fo2 = 0.21
    fhe = 0.0
    if gas_kind == "nitrox":
        fo2 = st.session_state.get(ACTIVE_O2_KEY, 32.0) / 100.0
    elif gas_kind == "heliox":
        fo2 = st.session_state.get(ACTIVE_HELIOX_O2_KEY, 20.0) / 100.0
        fhe = 1.0 - fo2

    depth_fsw = st.session_state[ACTIVE_DEPTH_FSW_KEY]
    is_first = not st.session_state[PLANNER_DIVES_KEY]
    si = None if is_first else float(st.session_state.get(ACTIVE_SI_KEY, 60.0))

    entry = {
        "_id": st.session_state[PLANNER_NEXT_ID_KEY],
        "gas_kind": gas_kind,
        "fo2": fo2,
        "fhe": fhe,
        "depth_fsw": depth_fsw,
        "bottom_time_min": float(st.session_state[TIME_KEY]),
        "surface_interval_before_min": si,
    }
    st.session_state[PLANNER_NEXT_ID_KEY] += 1
    st.session_state[PLANNER_DIVES_KEY].append(entry)

    # Reset the active dive to fresh defaults for the next entry.
    st.session_state[DEPTH_KEY] = depth_to_display(100.0, st.session_state[UNITS_SEEN_KEY])
    st.session_state[TIME_KEY] = 25.0
    st.session_state[ACTIVE_SI_KEY] = 60.0


st.subheader(t("dive_parameters_header"))

is_first_dive = not st.session_state[PLANNER_DIVES_KEY]
dive_number = len(st.session_state[PLANNER_DIVES_KEY]) + 1
st.markdown(f"**{t('active_dive_label', index=dive_number)}**")

step_col, _spacer = st.columns([1, 3])
with step_col:
    if hasattr(st, "segmented_control"):
        step_size = st.segmented_control(
            t("slider_step_label"),
            options=[1, 5, 10],
            default=st.session_state.get(STEP_KEY, 5),
            key=STEP_KEY,
            help=t("slider_step_help"),
        )
    else:
        step_size = st.radio(
            t("slider_step_label"),
            options=[1, 5, 10],
            index=[1, 5, 10].index(st.session_state.get(STEP_KEY, 5)),
            horizontal=True,
            key=STEP_KEY,
            help=t("slider_step_help"),
        )
    if not step_size:
        step_size = 5

col_gas, col_depth, col_time = st.columns([1, 1, 1])

with col_gas:
    gas_kind = st.selectbox(
        t("gas_label"),
        options=gas_options,
        index=default_gas_index,
        key=ACTIVE_GAS_KEY,
        format_func=lambda k: {"air": t("gas_air"), "nitrox": t("gas_nitrox"), "heliox": t("gas_heliox")}[k],
    )

fo2 = 0.21
fhe = 0.0
heliox_depth_options: list[float] = []

if gas_kind == "nitrox":
    with col_gas:
        o2_pct = st.number_input(
            t("o2_pct_nitrox_label"),
            min_value=21.0,
            max_value=40.0,
            value=float(prefill.get("o2_pct", 32.0)),
            step=1.0,
            key=ACTIVE_O2_KEY,
            help=t("o2_pct_nitrox_help"),
        )
        fo2 = o2_pct / 100.0
elif gas_kind == "heliox":
    try:
        heliox_data = load_table("heliox_12-4.json")
        heliox_depth_options = [float(d) for d in heliox_data["depths_fsw"]]
    except FileNotFoundError as exc:
        st.error(t("heliox_load_error", error=exc))
        st.stop()

with col_depth:
    if gas_kind == "heliox":
        depth_display_options = [
            depth_to_display(d, units) for d in heliox_depth_options
        ]
        chosen_display_depth = st.selectbox(
            t("heliox_depth_label", depth_label=depth_label(units)),
            options=depth_display_options,
            index=0,
            help=t("heliox_depth_help"),
        )
        depth_fsw = depth_to_fsw(chosen_display_depth, units)
        depth_key = str(int(depth_fsw))
        row = heliox_data["rows"][depth_key]
        max_o2, min_o2 = row["max_o2_pct"], row["min_o2_pct"]
        st.caption(t("heliox_o2_window_caption", min_o2=min_o2, max_o2=max_o2))
        default_o2_pct = (max_o2 + min_o2) / 2.0
        o2_pct = st.slider(
            t("heliox_o2_mix_label"),
            min_value=float(min_o2),
            max_value=float(max_o2),
            value=float(default_o2_pct),
            step=0.5,
            key=ACTIVE_HELIOX_O2_KEY,
        )
        fo2 = o2_pct / 100.0
        fhe = 1.0 - fo2
    else:
        max_depth_display = depth_to_display(MAX_DEPTH_FSW, units)
        # Clamp the stored value into range before the widget reads it —
        # protects against a stale value left over from a unit switch or
        # an out-of-range chart drag on a previous run.
        st.session_state[DEPTH_KEY] = _clamp(
            st.session_state[DEPTH_KEY], 0.0, max_depth_display
        )
        display_depth = st.number_input(
            depth_label(units),
            min_value=0.0,
            max_value=round(max_depth_display, 1),
            step=float(step_size) if units == "ft" else round(float(step_size) / 3.28084, 2),
            key=DEPTH_KEY,
        )
        depth_fsw = depth_to_fsw(display_depth, units)
        # Live equivalent-unit caption: the input's own unit is still
        # governed by the units toggle, but the other unit is always
        # shown alongside it so both are visible while adjusting.
        if units == "ft":
            st.caption(f"≈ {fsw_to_m(depth_fsw):.1f} m")
        else:
            st.caption(f"≈ {round(depth_fsw):g} fsw")

# Stash the resolved depth (correct for all three gas kinds — air/nitrox's
# number_input, or heliox's depth-selectbox, which never writes DEPTH_KEY)
# into a plain, non-widget session_state key every run, so the "Add
# repetitive dive" callback below can read the *actual* active depth
# instead of re-deriving it from DEPTH_KEY, which heliox never touches.
st.session_state[ACTIVE_DEPTH_FSW_KEY] = depth_fsw

with col_time:
    st.session_state[TIME_KEY] = _clamp(st.session_state[TIME_KEY], 1.0, MAX_TIME_MIN)
    bottom_time_min = st.number_input(
        t("bottom_time_label"),
        min_value=1.0,
        max_value=MAX_TIME_MIN,
        step=float(step_size),
        key=TIME_KEY,
    )

if not is_first_dive:
    st.session_state.setdefault(ACTIVE_SI_KEY, 60.0)
    active_si_min = st.number_input(
        t("surface_interval_before_label"),
        min_value=0.0,
        step=5.0,
        key=ACTIVE_SI_KEY,
        help=t("surface_interval_before_help"),
    )
else:
    active_si_min = None

st.button(
    t("add_repetitive_dive_button"),
    on_click=_commit_active_dive,
    help=t("add_repetitive_dive_help"),
)

st.divider()

# ---------------------------------------------------------------------------
# Render committed dives (if any) with in-place, per-row editable surface
# interval and a remove button — both keyed by the dive's stable "_id",
# not its list position, so removing a dive can never reattach another
# row's widget state to the wrong dive.
# ---------------------------------------------------------------------------
if st.session_state[PLANNER_DIVES_KEY]:
    st.subheader(t("committed_dives_header"))
    remove_id: int | None = None
    for i, entry in enumerate(st.session_state[PLANNER_DIVES_KEY]):
        row_id = entry["_id"]
        cols = st.columns([1.2, 1, 1, 1.2, 0.6])
        cols[0].write(f"**#{i + 1}** {gas_label(entry['gas_kind'])}")
        cols[1].write(format_depth_both(entry["depth_fsw"]))
        cols[2].write(t("series_entry_bottom_min", minutes=entry["bottom_time_min"]))
        if entry["surface_interval_before_min"] is None:
            cols[3].write(t("series_entry_first_no_si"))
        else:
            new_si = cols[3].number_input(
                t("surface_interval_before_label"),
                min_value=0.0,
                step=5.0,
                value=float(entry["surface_interval_before_min"]),
                key=f"planner_si_{row_id}",
                label_visibility="collapsed",
            )
            entry["surface_interval_before_min"] = new_si
        if cols[4].button(t("remove_button"), key=f"planner_remove_{row_id}"):
            remove_id = row_id
    if remove_id is not None:
        st.session_state[PLANNER_DIVES_KEY] = [
            e for e in st.session_state[PLANNER_DIVES_KEY] if e["_id"] != remove_id
        ]
        st.rerun()
    st.divider()

# ---------------------------------------------------------------------------
# Plan every committed dive plus the active dive as one chained series.
# A lone active dive (no committed dives) is a series of length 1, which
# is exactly the old single-dive behaviour (plan_series with one dive
# never chains).
# ---------------------------------------------------------------------------
gas = GasMix(fo2=fo2, fhe=fhe)

try:
    active_dive = Dive(
        gas=gas,
        max_depth_fsw=depth_fsw,
        bottom_time_min=bottom_time_min,
        surface_interval_before_min=active_si_min,
    )
except ValueError as exc:
    st.error(t("invalid_dive_params_error", error=exc))
    st.stop()

dives: list[Dive] = []
try:
    for entry in st.session_state[PLANNER_DIVES_KEY]:
        dives.append(
            Dive(
                gas=GasMix(fo2=entry["fo2"], fhe=entry["fhe"]),
                max_depth_fsw=entry["depth_fsw"],
                bottom_time_min=entry["bottom_time_min"],
                surface_interval_before_min=entry["surface_interval_before_min"],
            )
        )
except ValueError as exc:
    st.error(t("invalid_dive_params_error", error=exc))
    st.stop()
dives.append(active_dive)

try:
    results = plan_series(dives)
except (ValueError, TableRangeError) as exc:
    st.error(t("plan_series_engine_error", error=exc))
    st.stop()

# A single, translated provenance disclaimer for the whole page — rendered
# once here (not once per dive) even though a repetitive chain typically
# touches multiple seeded tables (9-7, 9-8, 9-9) that would otherwise
# each carry their own warning.
if any(has_provenance_warning(result) for result in results):
    render_provenance_banner()

# ---------------------------------------------------------------------------
# Results: a lone dive gets the clean single-result view; two or more
# dives get the chained per-dive expander view.
# ---------------------------------------------------------------------------
if len(results) == 1:
    result = results[0]
    render_result_warnings(result)

    st.subheader(t("result_summary_header"))
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        t("status_label"),
        t("status_no_deco") if result.no_decompression else t("status_deco_required"),
    )
    m2.metric(t("ndl_label"), f"{result.ndl_min:g}" if result.ndl_min is not None else "—")
    m3.metric(
        t("time_to_first_stop_label"),
        f"{result.time_to_first_stop:g}" if result.time_to_first_stop is not None else "—",
    )
    m4.metric(t("repetitive_group_label"), result.repetitive_group or t("not_applicable"))

    m5, m6, m7 = st.columns(3)
    m5.metric(t("total_stop_time_label"), f"{result.total_stop_min:g}")
    m6.metric(
        t("residual_nitrogen_time_label"),
        f"{result.residual_nitrogen_time_min:g}"
        if result.residual_nitrogen_time_min is not None
        else "—",
    )
    m7.metric(t("table_source_label"), result.table_source)

    if gas_kind == "nitrox":
        st.info(
            t(
                "nitrox_ead_info",
                actual_depth=format_depth_both(result.actual_depth_fsw),
                ead_depth=format_depth_both(result.ead_fsw),
            )
        )
    elif gas_kind == "heliox":
        phases = sorted({s.gas_phase for s in result.stops})
        if phases:
            st.info(t("heliox_gas_phases_info", phases=", ".join(phases)))

    st.subheader(t("decompression_schedule_header"))
    if result.stops:
        schedule_rows = [
            {
                t("col_stop_depth"): format_depth_both(stop.depth_fsw),
                t("col_minutes"): stop.minutes,
                t("col_gas_phase"): stop.gas_phase,
            }
            for stop in result.stops
        ]
        st.dataframe(schedule_rows, use_container_width=True, hide_index=True)
    else:
        st.success(t("no_deco_stops_success"))

    st.subheader(t("dive_profile_header"))
    depth_draggable = gas_kind != "heliox"
    drag_hint_key = "drag_hint_with_depth" if depth_draggable else "drag_hint_no_depth"
    st.caption(t(drag_hint_key))
    st.caption(t("chart_drag_tip"))
    st.caption(t("chart_units_caption", axis_unit=depth_label(units)))
    chart = build_profile_chart(
        max_depth_fsw=result.actual_depth_fsw or depth_fsw,
        bottom_time_min=bottom_time_min,
        result=result,
        units=units,
        depth_converter=lambda fsw: depth_to_display(fsw, units),
    )

    brush = alt.selection_interval(name="profile_brush", encodings=["x", "y"])
    interactive_chart = chart.add_params(brush)

    chart_state = st.altair_chart(
        interactive_chart,
        use_container_width=True,
        on_select="rerun",
        key=CHART_WIDGET_KEY,
    )

    # ---------------------------------------------------------------------
    # Read back the chart's selection. Vega-Lite's interval-brush payload
    # for each encoding channel is a bounds array (empirically 2-3
    # numbers, unordered) rather than a strict [lo, hi] pair, so bounds
    # are derived with min()/max() rather than by position. An empty dict
    # means "no selection yet" (first load, or a plain click with no
    # drag) and is left untouched — never crash, never treat it as a
    # zero-size selection.
    #
    # The new values are staged into PENDING_*_KEY rather than written
    # directly to the number-input keys: those inputs were already
    # instantiated above in this same run, and Streamlit forbids writing
    # to a widget's key after it's been created in the same run. The
    # staged values are applied at the top of the *next* run, before the
    # inputs are recreated (see above). The signature guard (comparing
    # against the last-applied selection) is what prevents an infinite
    # rerun loop: without it, every rerun would re-read the same
    # unchanged selection and force another rerun forever.
    # ---------------------------------------------------------------------
    selection: dict | None = None
    try:
        selection = chart_state["selection"]["profile_brush"]
    except (TypeError, KeyError):
        selection = None

    if selection:
        time_bounds = selection.get("time_min")
        depth_bounds = selection.get("depth_display")
        sig = (
            tuple(time_bounds) if time_bounds else None,
            tuple(depth_bounds) if depth_bounds else None,
        )
        if (time_bounds or depth_bounds) and sig != st.session_state.get(CHART_SEL_SIG_KEY):
            st.session_state[CHART_SEL_SIG_KEY] = sig
            applied = False
            if time_bounds:
                new_time = _clamp(max(time_bounds), 1.0, MAX_TIME_MIN)
                st.session_state[PENDING_TIME_KEY] = new_time
                applied = True
            if depth_bounds and depth_draggable:
                # The y-axis domain is pinned descending (surface at
                # top), so the deeper edge of the drag is the larger data
                # value regardless of its on-screen (pixel) position.
                max_depth_display = depth_to_display(MAX_DEPTH_FSW, units)
                new_depth = _clamp(max(depth_bounds), 0.0, max_depth_display)
                st.session_state[PENDING_DEPTH_KEY] = new_depth
                applied = True
            if applied:
                st.rerun()

    st.caption(t("idealized_plan_caption"))

else:
    st.subheader(t("chained_results_header"))
    all_entries = list(st.session_state[PLANNER_DIVES_KEY]) + [
        {
            "gas_kind": gas_kind,
            "fo2": fo2,
            "fhe": fhe,
            "depth_fsw": depth_fsw,
            "bottom_time_min": bottom_time_min,
            "surface_interval_before_min": active_si_min,
        }
    ]
    for i, (entry, result) in enumerate(zip(all_entries, results)):
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
# Save the current dives (committed + active) to a profile.
# ---------------------------------------------------------------------------
st.subheader(t("save_series_header"))

store = JsonProfileStore()
existing_users = store.list_users()

# Stable internal sentinel for "create a new user"; only the on-screen
# label is translated (format_func), so the `user_choice ==
# NEW_USER_SENTINEL` checks below keep working regardless of the active
# language.
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
            updated = dc_replace(data, series=data.series + (new_series,))
            store.save(updated)
            st.success(t("series_saved_success", label=series_label, user_id=user_id))
        except ProfileStoreError as exc:
            st.error(t("profile_save_error", error=exc))
