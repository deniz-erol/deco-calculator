"""Plan Dive — single-dive planner: gas selector, depth/time inputs,
schedule table, key outputs, and a dive-profile chart.

Depth and bottom time are entered via draggable sliders (with a
user-adjustable step size) and can also be set by clicking/dragging on
the dive-profile chart itself. Both input paths write into the same
``st.session_state`` keys that back the sliders, so the sliders and the
chart stay in two-way sync.
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

import altair as alt
import streamlit as st

from app._chart import build_profile_chart
from app._i18n import t
from app._shared import (
    depth_label,
    depth_to_display,
    depth_to_fsw,
    format_depth_both,
    has_provenance_warning,
    render_disclaimer,
    render_provenance_banner,
    render_result_warnings,
    render_sidebar_toggles,
)
from engine.lookup import TableRangeError, load_table
from engine.planner import plan_dive
from engine.types import Dive, GasMix
from engine.units import fsw_to_m

st.set_page_config(page_title="Plan Dive", page_icon="🧭", layout="wide")

st.title(t("plan_dive_page_title"))
render_disclaimer()

units, _lang = render_sidebar_toggles(st.sidebar)

st.sidebar.divider()
st.sidebar.caption(t("plan_dive_sidebar_caption"))

# ---------------------------------------------------------------------------
# Session-state keys backing the depth/time sliders, plus the bookkeeping
# keys used to reconcile two other input sources (units toggle, chart
# drag) into those same slider keys *before* the widgets are created.
# Streamlit forbids writing to a widget's key after it has been
# instantiated in the same run, so every reconciliation below happens at
# the top of the script, ahead of `st.slider(...)`.
# ---------------------------------------------------------------------------
DEPTH_KEY = "plan_depth_display"
TIME_KEY = "plan_time_min"
STEP_KEY = "plan_step"
UNITS_SEEN_KEY = "plan_units_seen"
CHART_SEL_SIG_KEY = "plan_chart_sel_sig"
CHART_WIDGET_KEY = "plan_profile_chart"
# Staging keys for a pending chart-drag update: the chart is rendered at
# the bottom of the script, well after the depth/time sliders have
# already been instantiated with `key=DEPTH_KEY` / `key=TIME_KEY` for
# this run — Streamlit raises if you write to a widget's key after that
# widget has been created in the same run. So a chart selection is
# staged here instead, and only applied to the slider keys at the very
# top of the *next* run, before the sliders are (re)created.
PENDING_DEPTH_KEY = "plan_pending_depth_display"
PENDING_TIME_KEY = "plan_pending_time_min"

MAX_DEPTH_FSW = 190.0
MAX_TIME_MIN = 200.0

# ---------------------------------------------------------------------------
# Prefill support (a value pushed here from the Profiles page), read once.
# ---------------------------------------------------------------------------
prefill = st.session_state.pop("plan_dive_prefill", None) or {}

gas_options = ["air", "nitrox", "heliox"]
default_gas_index = gas_options.index(prefill.get("gas_kind", "air"))

# ---------------------------------------------------------------------------
# Seed the depth/time slider state once (first load, or a fresh prefill).
# ---------------------------------------------------------------------------
if "max_depth_fsw" in prefill:
    st.session_state[DEPTH_KEY] = depth_to_display(float(prefill["max_depth_fsw"]), units)
elif DEPTH_KEY not in st.session_state:
    st.session_state[DEPTH_KEY] = depth_to_display(100.0, units)

if "bottom_time_min" in prefill:
    st.session_state[TIME_KEY] = float(prefill["bottom_time_min"])
elif TIME_KEY not in st.session_state:
    st.session_state[TIME_KEY] = 25.0

# ---------------------------------------------------------------------------
# Apply a chart drag staged on the *previous* run. This must happen here,
# before the depth/time sliders are instantiated below, or Streamlit
# raises "cannot be modified after the widget ... is instantiated".
# ---------------------------------------------------------------------------
if PENDING_TIME_KEY in st.session_state:
    st.session_state[TIME_KEY] = st.session_state.pop(PENDING_TIME_KEY)
if PENDING_DEPTH_KEY in st.session_state:
    st.session_state[DEPTH_KEY] = st.session_state.pop(PENDING_DEPTH_KEY)

# ---------------------------------------------------------------------------
# Reconcile a units-toggle change: the slider key stores a *display-unit*
# number, so switching ft<->m must convert the stored value in place
# before the slider widget is built, or the same number gets silently
# reinterpreted in the new unit.
# ---------------------------------------------------------------------------
previous_units = st.session_state.get(UNITS_SEEN_KEY)
if previous_units is not None and previous_units != units:
    stored_fsw = depth_to_fsw(st.session_state[DEPTH_KEY], previous_units)
    st.session_state[DEPTH_KEY] = depth_to_display(stored_fsw, units)
st.session_state[UNITS_SEEN_KEY] = units


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


st.subheader(t("dive_parameters_header"))

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
        display_depth = st.slider(
            depth_label(units),
            min_value=0.0,
            max_value=round(max_depth_display, 1),
            step=float(step_size) if units == "ft" else round(float(step_size) / 3.28084, 2),
            key=DEPTH_KEY,
        )
        depth_fsw = depth_to_fsw(display_depth, units)
        # Live equivalent-unit caption: the slider's own unit is still
        # governed by the units toggle, but the other unit is always
        # shown alongside it so both are visible while dragging.
        if units == "ft":
            st.caption(f"≈ {fsw_to_m(depth_fsw):.1f} m")
        else:
            st.caption(f"≈ {round(depth_fsw):g} fsw")

with col_time:
    st.session_state[TIME_KEY] = _clamp(st.session_state[TIME_KEY], 1.0, MAX_TIME_MIN)
    bottom_time_min = st.slider(
        t("bottom_time_label"),
        min_value=1.0,
        max_value=MAX_TIME_MIN,
        step=float(step_size),
        key=TIME_KEY,
    )

st.divider()

# ---------------------------------------------------------------------------
# Plan the dive.
# ---------------------------------------------------------------------------
gas = GasMix(fo2=fo2, fhe=fhe)

try:
    dive = Dive(
        gas=gas,
        max_depth_fsw=depth_fsw,
        bottom_time_min=bottom_time_min,
        surface_interval_before_min=None,
    )
except ValueError as exc:
    st.error(t("invalid_dive_params_error", error=exc))
    st.stop()

try:
    result = plan_dive(dive)
except (ValueError, TableRangeError) as exc:
    st.error(t("plan_dive_engine_error", error=exc))
    st.stop()

# ---------------------------------------------------------------------------
# Results.
# ---------------------------------------------------------------------------
if has_provenance_warning(result):
    render_provenance_banner()
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

# ---------------------------------------------------------------------------
# Read back the chart's selection. Vega-Lite's interval-brush payload for
# each encoding channel is a bounds array (empirically 2-3 numbers,
# unordered) rather than a strict [lo, hi] pair, so bounds are derived
# with min()/max() rather than by position. An empty dict means "no
# selection yet" (first load, or a plain click with no drag) and is left
# untouched — never crash, never treat it as a zero-size selection.
#
# The new values are staged into PENDING_*_KEY rather than written
# directly to the slider keys: those sliders were already instantiated
# above in this same run, and Streamlit forbids writing to a widget's key
# after it's been created in the same run. The staged values are applied
# at the top of the *next* run, before the sliders are recreated (see
# above). The signature guard (comparing against the last-applied
# selection) is what prevents an infinite rerun loop: without it, every
# rerun would re-read the same unchanged selection and force another
# rerun forever.
# ---------------------------------------------------------------------------
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
            # The y-axis domain is pinned descending (surface at top), so
            # the deeper edge of the drag is the larger data value
            # regardless of its on-screen (pixel) position.
            max_depth_display = depth_to_display(MAX_DEPTH_FSW, units)
            new_depth = _clamp(max(depth_bounds), 0.0, max_depth_display)
            st.session_state[PENDING_DEPTH_KEY] = new_depth
            applied = True
        if applied:
            st.rerun()

st.caption(t("idealized_plan_caption"))
