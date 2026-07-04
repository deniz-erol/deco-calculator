"""Unit conversion helpers. fsw is canonical everywhere in the engine.

Only the geometric conversion factor (1 m = 3.28084 ft) is used, for
*display* purposes and for accepting metric depth input. The pressure
conversion factor (msw = bar/10, ~3.26336 fsw/m) is deliberately never
used here — mixing the two would silently corrupt table lookups.
"""

from __future__ import annotations

METERS_TO_FEET = 3.28084  # geometric conversion only — do not use 3.26336


def fsw_to_m(depth_fsw: float) -> float:
    """Convert a depth in fsw (feet of seawater) to meters, for display."""
    return depth_fsw / METERS_TO_FEET


def m_to_fsw(depth_m: float) -> float:
    """Convert a depth in meters to fsw. Used only when a user enters
    metric depth input; the result should still be rounded up to the
    next tabulated depth by the lookup layer.
    """
    return depth_m * METERS_TO_FEET
