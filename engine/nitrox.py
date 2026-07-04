"""Nitrox dive planning via the Equivalent Air Depth (EAD) method.

The Navy has no dedicated open-circuit nitrox decompression table:
compute (or look up) the EAD, then run the air path (Table 9-7 / 9-9)
at that shallower depth. ppO2 is guarded at 1.4 ata; dives beyond that
ceiling are flagged and repetitive planning is blocked for them.
"""

from __future__ import annotations

from dataclasses import replace

from engine.air import plan_air_dive
from engine.gas import ppo2, validate_mix
from engine.lookup import load_table, round_up_depth, table_meta
from engine.types import DiveResult, GasMix

NITROX_EAD_FILE = "nitrox_ead_10-1.json"
PPO2_CEILING_ATA = 1.4
AIR_FN2 = 0.79


def compute_ead_formula(depth_fsw: float, fo2: float) -> float:
    """Algebraic EAD (fsw): EAD = (D + 33) * (FN2 / 0.79) - 33."""
    fn2 = 1.0 - fo2
    return (depth_fsw + 33.0) * (fn2 / AIR_FN2) - 33.0


def lookup_ead(depth_fsw: float, fo2: float) -> tuple[float, bool]:
    """Look up EAD from Table 10-1; fall back to the algebraic formula.

    Returns (ead_fsw, from_table). ``from_table`` is False when the
    seeded Table 10-1 subset doesn't cover this depth/fo2 combination
    and the algebraic fallback was used instead.
    """
    data = load_table(NITROX_EAD_FILE)
    depths = data["depths_fsw"]
    fo2_columns = data["fo2_columns"]

    depth_key = str(int(depth_fsw)) if float(depth_fsw) in {float(d) for d in depths} else None
    fo2_key = None
    for col in fo2_columns:
        if abs(col - fo2) < 1e-6:
            fo2_key = str(col)
            break

    if depth_key is not None and fo2_key is not None:
        row = data["rows"].get(depth_key, {})
        if fo2_key in row:
            return float(row[fo2_key]), True

    # Fallback: algebraic formula, then round up to the air-table depth ladder.
    ead_raw = compute_ead_formula(depth_fsw, fo2)
    air_ndl = load_table("air_ndl_9-7.json")
    rounded = round_up_depth(max(ead_raw, 0.0), air_ndl["depths_fsw"])
    return rounded, False


def plan_nitrox_dive(gas: GasMix, depth_fsw: float, bottom_time_min: float) -> DiveResult:
    """Plan a nitrox dive: EAD lookup, then the air path at the EAD.

    Validates fo2+fhe <= 1 and guards ppO2 <= 1.4 ata. Dives beyond the
    ppO2 ceiling are flagged (not raised) so the caller can still see a
    schedule, but repetitive planning must be blocked by the caller
    (planner.py) per the "repetitive not authorized beyond 1.4 ata" rule.
    """
    validate_mix(gas)
    warnings: list[str] = []

    measured_ppo2 = ppo2(gas, depth_fsw)
    if measured_ppo2 > PPO2_CEILING_ATA + 1e-9:
        warnings.append(
            f"ppO2 at {depth_fsw} fsw is {measured_ppo2} ata, exceeding the "
            f"{PPO2_CEILING_ATA} ata working limit — requires CO authorization "
            "and surface-supplied gear; repetitive dives are NOT authorized."
        )

    mod = gas.mod_fsw(ppo2_max=PPO2_CEILING_ATA)
    if depth_fsw > mod + 1e-9:
        warnings.append(
            f"Requested depth {depth_fsw} fsw exceeds MOD of {mod:.1f} fsw "
            f"for FO2={gas.fo2} at ppO2_max={PPO2_CEILING_ATA} ata"
        )

    ead_fsw, from_table = lookup_ead(depth_fsw, gas.fo2)
    if not from_table:
        warnings.append(
            f"EAD for {depth_fsw} fsw / FO2={gas.fo2} not in the seeded Table "
            "10-1 subset; computed via the algebraic EAD formula instead"
        )

    air_result = plan_air_dive(ead_fsw, bottom_time_min)

    combined_warnings = tuple(warnings) + air_result.warnings
    return replace(
        air_result,
        table_source=f"USN Rev7 Table 10-1 (EAD) -> {air_result.table_source}",
        warnings=combined_warnings,
        actual_depth_fsw=depth_fsw,
        ead_fsw=ead_fsw,
    )
