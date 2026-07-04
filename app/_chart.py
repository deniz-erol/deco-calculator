"""Dive-profile chart construction (Altair — the declared chart lib in
pyproject.toml).

Builds a schematic depth-vs-time profile: surface -> sloped descent ->
bottom time at max depth -> sloped ascent through any deco stops (flat
holds joined by sloped transits) -> surface. The slopes use conventional
US Navy depiction rates (75 ft/min descent, 30 ft/min ascent) purely to
make the chart *shape* look like a real dive; they are not part of, and
do not feed back into, the decompression calculation itself, which
remains the unchanged table-based square profile. This chart is
illustrative, not a precise dive-computer trace; it exists to make the
schedule legible at a glance.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from app._i18n import t
from engine.types import DiveResult


# Depiction-only transit rates (US Navy conventional planning rates).
# These shape the chart's line so it reads as a real dive profile; they
# are NOT used anywhere in the deco math, which stays table-based and
# unchanged (see engine/).
_DESCENT_RATE_FPM = 75.0
_ASCENT_RATE_FPM = 30.0


def _profile_points(
    max_depth_fsw: float, bottom_time_min: float, result: DiveResult
) -> list[dict]:
    """Build an ordered list of {time_min, depth_fsw, phase} points.

    Phases, in order:
      1. Descent   — sloped, surface -> max depth at 75 ft/min.
      2. Bottom    — flat hold at max depth. Navy bottom time is measured
         from leaving the surface, so the flat portion runs from the end
         of the descent to ``bottom_time_min`` (clamped so time never
         runs backwards for very shallow/short dives).
      3. Ascent to first stop (or surface, if no-deco) — sloped, using
         the table's ``time_to_first_stop`` when available, else a 30
         ft/min depiction slope.
      4. Stops     — flat holds at each stop's depth for its minutes.
      5. Ascents between stops, and the final ascent to the surface —
         sloped at 30 ft/min.
    """
    descent_time = max_depth_fsw / _DESCENT_RATE_FPM
    points: list[dict] = [
        {"time_min": 0.0, "depth_fsw": 0.0, "phase": "surface"},
        {"time_min": descent_time, "depth_fsw": max_depth_fsw, "phase": "descent"},
    ]
    # Guard the degenerate case (very shallow/short dive) so the bottom
    # point never lands before the descent finishes.
    t = max(bottom_time_min, descent_time)
    points.append({"time_min": t, "depth_fsw": max_depth_fsw, "phase": "bottom"})

    # Ascent to the first stop (or straight to the surface if none).
    if result.stops:
        first_stop = result.stops[0]
        time_to_first = result.time_to_first_stop
        if time_to_first is not None:
            t += time_to_first
        else:
            t += abs(max_depth_fsw - first_stop.depth_fsw) / _ASCENT_RATE_FPM
        points.append({"time_min": t, "depth_fsw": first_stop.depth_fsw, "phase": "ascent"})

        for stop in result.stops:
            # Arrive at this stop's depth (if not already there from ascent).
            if points[-1]["depth_fsw"] != stop.depth_fsw:
                prev_depth = points[-1]["depth_fsw"]
                t += abs(prev_depth - stop.depth_fsw) / _ASCENT_RATE_FPM
                points.append(
                    {"time_min": t, "depth_fsw": stop.depth_fsw, "phase": stop.gas_phase}
                )
            t += stop.minutes
            points.append(
                {"time_min": t, "depth_fsw": stop.depth_fsw, "phase": stop.gas_phase}
            )
        # Final sloped ascent from the last stop to the surface.
        t += points[-1]["depth_fsw"] / _ASCENT_RATE_FPM
        points.append({"time_min": t, "depth_fsw": 0.0, "phase": "surface"})
    else:
        # No-deco: single sloped ascent straight to the surface.
        t += max_depth_fsw / _ASCENT_RATE_FPM
        points.append({"time_min": t, "depth_fsw": 0.0, "phase": "ascent"})

    return points


def build_profile_chart(
    max_depth_fsw: float,
    bottom_time_min: float,
    result: DiveResult,
    units: str,
    depth_converter,
) -> alt.Chart:
    """Build an Altair depth-vs-time chart for one planned dive.

    ``depth_converter`` converts an fsw value to the active display unit
    (feet or meters) so the chart's axis matches the units toggle.
    """
    points = _profile_points(max_depth_fsw, bottom_time_min, result)
    df = pd.DataFrame(points)
    df["depth_display"] = df["depth_fsw"].apply(depth_converter)
    depth_unit_label = t("depth_label_m") if units == "m" else t("depth_label_ft")

    max_display_depth = df["depth_display"].max()
    # Guard the degenerate near-surface case so the domain is never
    # collapsed to [0, 0] (or similarly tiny) — always leave enough
    # headroom for the axis to render surface-at-top unambiguously.
    min_floor = 10.0 if units == "m" else 30.0
    axis_max = max(max_display_depth * 1.08, min_floor)

    line = (
        alt.Chart(df)
        .mark_line(point=True, interpolate="linear", color="#1f6feb")
        .encode(
            x=alt.X("time_min:Q", title=t("chart_time_axis")),
            y=alt.Y(
                "depth_display:Q",
                title=depth_unit_label,
                # Domain is pinned descending (surface/0 at top, depth
                # increasing downward). `clamp=True` keeps out-of-range
                # values pinned at the edges instead of expanding the
                # domain, and `nice=False` stops Vega from "rounding" the
                # domain outward. Combined with a static (non-interactive)
                # chart below, this domain can never be inverted.
                scale=alt.Scale(domain=[axis_max, 0], clamp=True, nice=False),
            ),
            tooltip=[
                alt.Tooltip("time_min:Q", title=t("chart_tooltip_time")),
                alt.Tooltip("depth_display:Q", title=depth_unit_label, format=".1f"),
                alt.Tooltip("phase:N", title=t("chart_tooltip_phase")),
            ],
        )
    )

    points_layer = (
        alt.Chart(df)
        .mark_circle(size=60, color="#1f6feb")
        .encode(
            x="time_min:Q",
            y="depth_display:Q",
            tooltip=[
                alt.Tooltip("time_min:Q", title=t("chart_tooltip_time")),
                alt.Tooltip("depth_display:Q", title=depth_unit_label, format=".1f"),
                alt.Tooltip("phase:N", title=t("chart_tooltip_phase")),
            ],
        )
    )

    # No `.interactive()`: this is a planned/idealized schematic, not a
    # trace meant for free zoom/pan. `.interactive()` binds zoom to BOTH
    # axes, and zooming out on a pinned *descending* y-domain caused Vega
    # to recompute (and invert) the domain — flipping the depth axis so
    # the surface appeared at the bottom. Keeping the chart static removes
    # the only trigger for that inversion.
    return (
        (line + points_layer)
        .properties(
            height=340,
            title=alt.TitleParams(
                text=t("chart_title"),
                subtitle=t("chart_subtitle"),
            ),
        )
    )
