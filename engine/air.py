"""Air dive lookup: Table 9-7 (no-decompression limits + repetitive group)
and Table 9-9 (air decompression schedule + ending group).

Selection rule: round depth up to the next tabulated depth, then round
bottom time up to the next tabulated time in that depth's row. If the
(rounded) bottom time is within the row's NDL, use Table 9-7 (no-stop
dive); otherwise the dive requires decompression and Table 9-9 is used.
"""

from __future__ import annotations

from engine.lookup import (
    TableRangeError,
    load_table,
    round_up_depth,
    round_up_time,
    table_meta,
)
from engine.types import DecoStop, DiveResult

AIR_NDL_FILE = "air_ndl_9-7.json"
AIR_DECO_FILE = "air_deco_9-9.json"


def get_ndl(depth_fsw: float) -> float:
    """Return the no-decompression limit (minutes) for a rounded depth."""
    data = load_table(AIR_NDL_FILE)
    rounded_depth = round_up_depth(depth_fsw, data["depths_fsw"])
    row = data["rows"][str(int(rounded_depth))]
    return float(row["ndl_min"])


def _lookup_group_9_7(rounded_depth: float, bottom_time_min: float) -> tuple[str, float]:
    """Return (group_letter, ndl_min) for a no-deco dive via Table 9-7."""
    data = load_table(AIR_NDL_FILE)
    row = data["rows"][str(int(rounded_depth))]
    ndl = float(row["ndl_min"])
    times = [g["max_time_min"] for g in row["groups"]]
    rounded_time = round_up_time(bottom_time_min, times)
    for g in row["groups"]:
        if g["max_time_min"] == rounded_time:
            return g["group"], ndl
    raise TableRangeError(
        f"No repetitive-group entry found for depth {rounded_depth} at "
        f"time {rounded_time}"
    )


def _lookup_schedule_9_9(rounded_depth: float, bottom_time_min: float) -> dict:
    """Return the raw schedule row dict for a deco dive via Table 9-9."""
    data = load_table(AIR_DECO_FILE)
    depth_key = str(int(rounded_depth))
    if depth_key not in data["rows"]:
        raise TableRangeError(
            f"No Table 9-9 schedule available for depth {rounded_depth} fsw "
            "in the seeded data"
        )
    row = data["rows"][depth_key]
    times = [entry["bottom_time_min"] for entry in row["bottom_times_min"]]
    rounded_time = round_up_time(bottom_time_min, times)
    for entry in row["bottom_times_min"]:
        if entry["bottom_time_min"] == rounded_time:
            return entry
    raise TableRangeError(
        f"No Table 9-9 entry found for depth {rounded_depth} at time {rounded_time}"
    )


def plan_air_dive(depth_fsw: float, bottom_time_min: float) -> DiveResult:
    """Plan a single air dive: choose Table 9-7 (no-deco) or 9-9 (deco).

    Depth is rounded up to the next tabulated depth in Table 9-7 first
    (both tables share the same depth ladder in the seeded data) to
    determine the NDL, then bottom time is rounded up to select the row.
    """
    ndl_data = load_table(AIR_NDL_FILE)
    rounded_depth = round_up_depth(depth_fsw, ndl_data["depths_fsw"])
    ndl = get_ndl(rounded_depth)

    warnings: list[str] = []
    if rounded_depth > depth_fsw:
        warnings.append(
            f"Depth rounded up from {depth_fsw} to {rounded_depth} fsw per table rules"
        )

    if bottom_time_min <= ndl + 1e-9:
        group, ndl_min = _lookup_group_9_7(rounded_depth, bottom_time_min)
        meta = table_meta(ndl_data)
        warnings.extend(meta.warnings())
        return DiveResult(
            stops=(),
            total_stop_min=0.0,
            time_to_first_stop=None,
            no_decompression=True,
            ndl_min=ndl_min,
            repetitive_group=group,
            residual_nitrogen_time_min=None,
            table_source="USN Rev7 Table 9-7",
            warnings=tuple(warnings),
            actual_depth_fsw=depth_fsw,
        )

    # Exceeds NDL: decompression dive, Table 9-9.
    warnings.append(
        f"Bottom time {bottom_time_min} min exceeds NDL of {ndl} min at "
        f"{rounded_depth} fsw; decompression required (Table 9-9)"
    )
    deco_data = load_table(AIR_DECO_FILE)
    entry = _lookup_schedule_9_9(rounded_depth, bottom_time_min)
    if entry.get("exceptional_exposure"):
        warnings.append("Exceptional exposure schedule — see manual cautions")
    meta = table_meta(deco_data)
    warnings.extend(meta.warnings())

    stops = tuple(
        DecoStop(depth_fsw=float(s["depth_fsw"]), minutes=float(s["minutes"]))
        for s in entry["stops"]
    )
    return DiveResult(
        stops=stops,
        total_stop_min=float(entry["total_stop_min"]),
        time_to_first_stop=float(entry["time_to_first_stop_min"]),
        no_decompression=False,
        ndl_min=ndl,
        repetitive_group=entry["ending_group"],
        residual_nitrogen_time_min=None,
        table_source="USN Rev7 Table 9-9",
        warnings=tuple(warnings),
        actual_depth_fsw=depth_fsw,
    )
