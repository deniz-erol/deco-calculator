"""Heliox dive lookup: Table 12-4, standalone (no repetitive-group system).

The Navy confirms no repetitive-group / residual-nitrogen system exists
for heliox — rep-group logic is nitrogen-based (9-7/9-8) and doesn't
apply. Every result here has repetitive_group=None plus a warning that
repetitive logic is not applicable. Stops carry their pre-baked gas
phase (bottom mix -> 50% O2 -> 100% O2) as printed in the table; no
gas-switching engine is implemented or needed.
"""

from __future__ import annotations

from engine.gas import validate_mix
from engine.lookup import (
    TableRangeError,
    load_table,
    round_up_depth,
    round_up_time,
    table_meta,
)
from engine.types import DecoStop, DiveResult, GasMix

HELIOX_FILE = "heliox_12-4.json"

REPETITIVE_NA_WARNING = (
    "Heliox has no repetitive-group / residual-nitrogen system in the Navy "
    "tables; repetitive logic is not applicable to this dive."
)


def plan_heliox_dive(gas: GasMix, depth_fsw: float, bottom_time_min: float) -> DiveResult:
    """Plan a standalone heliox dive via Table 12-4.

    Depth rounds up to the next tabulated depth; bottom time rounds up
    to the next tabulated time in that depth's row. Returns the printed
    stop schedule with pre-baked gas phases and chamber O2 periods.
    """
    validate_mix(gas)
    warnings: list[str] = [REPETITIVE_NA_WARNING]

    data = load_table(HELIOX_FILE)
    meta = table_meta(data)
    warnings.extend(meta.warnings())

    rounded_depth = round_up_depth(depth_fsw, data["depths_fsw"])
    if rounded_depth > depth_fsw:
        warnings.append(
            f"Depth rounded up from {depth_fsw} to {rounded_depth} fsw per table rules"
        )

    depth_key = str(int(rounded_depth))
    row = data["rows"][depth_key]

    max_o2 = row["max_o2_pct"]
    min_o2 = row["min_o2_pct"]
    if not (min_o2 / 100.0 <= gas.fo2 <= max_o2 / 100.0):
        warnings.append(
            f"Requested FO2={gas.fo2} is outside the Table 12-4 window for "
            f"{rounded_depth} fsw (Max {max_o2:.1f}% / Min {min_o2:.1f}%)"
        )

    times = [entry["bottom_time_min"] for entry in row["bottom_times_min"]]
    try:
        rounded_time = round_up_time(bottom_time_min, times)
    except TableRangeError as exc:
        raise TableRangeError(
            f"No Table 12-4 schedule available for {bottom_time_min} min at "
            f"{rounded_depth} fsw in the seeded data: {exc}"
        ) from exc

    entry = next(e for e in row["bottom_times_min"] if e["bottom_time_min"] == rounded_time)
    if entry.get("exceptional_exposure"):
        warnings.append("Exceptional exposure schedule — see manual cautions")

    stops = tuple(
        DecoStop(
            depth_fsw=float(s["depth_fsw"]),
            minutes=float(s["minutes"]),
            gas_phase=s.get("gas_phase", "bottom mix"),
        )
        for s in entry["stops"]
    )

    return DiveResult(
        stops=stops,
        total_stop_min=float(entry["total_stop_min"]),
        time_to_first_stop=float(entry["time_to_first_stop_min"]),
        no_decompression=False,
        ndl_min=None,
        repetitive_group=None,
        residual_nitrogen_time_min=None,
        table_source="USN Rev7 Table 12-4",
        warnings=tuple(warnings),
        actual_depth_fsw=depth_fsw,
    )
