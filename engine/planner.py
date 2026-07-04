"""Top-level orchestration: plan_dive() and plan_series().

Dispatches by gas kind (air / nitrox / heliox), chains repetitive dives
via Table 9-8 when a previous result + surface interval are supplied,
and applies boundary validation shared across all gas kinds.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from engine.air import plan_air_dive
from engine.gas import validate_mix
from engine.heliox import plan_heliox_dive
from engine.nitrox import PPO2_CEILING_ATA, plan_nitrox_dive
from engine.repetitive import chain_repetitive
from engine.types import Dive, DiveResult


def _is_nitrox_beyond_ceiling(dive: Dive) -> bool:
    """True if this nitrox dive's ppO2 at depth exceeds the 1.4 ata ceiling."""
    if dive.gas.kind != "nitrox":
        return False
    from engine.gas import ppo2

    return ppo2(dive.gas, dive.max_depth_fsw) > PPO2_CEILING_ATA + 1e-9


def plan_dive(dive: Dive, previous: DiveResult | None = None) -> DiveResult:
    """Plan a single dive, optionally chained after a previous dive's result.

    - If ``previous`` is None, this is the first dive of a series (or a
      standalone dive): planned at face value.
    - If ``previous`` is supplied, ``dive.surface_interval_before_min``
      must also be supplied; the two feed the Table 9-8 chain to derive
      Residual Nitrogen Time (RNT), which is added to this dive's bottom
      time before the underlying air/nitrox lookup. Heliox never chains
      (no repetitive-group system) and nitrox beyond 1.4 ata is blocked
      from chaining per the Navy's "repetitive not authorized" rule.
    """
    validate_mix(dive.gas)
    warnings: list[str] = []
    effective_bottom_time = dive.bottom_time_min
    rnt_min: float | None = None

    kind = dive.gas.kind

    if previous is not None:
        if dive.surface_interval_before_min is None:
            raise ValueError(
                "surface_interval_before_min is required when chaining a "
                "repetitive dive (previous result supplied)"
            )
        if kind == "heliox":
            warnings.append(
                "Heliox has no repetitive-group system; ignoring the previous "
                "dive's result and planning this dive standalone."
            )
        elif previous.repetitive_group is None:
            warnings.append(
                "Previous dive has no repetitive group (e.g. heliox or an "
                "already-non-repetitive dive); planning this dive standalone."
            )
        elif "repetitive dives are NOT authorized" in " ".join(previous.warnings):
            warnings.append(
                "Previous nitrox dive exceeded 1.4 ata ppO2; repetitive "
                "dives are not authorized — planning this dive standalone."
            )
        else:
            chain = chain_repetitive(
                previous.repetitive_group,
                dive.surface_interval_before_min,
                dive.max_depth_fsw,
            )
            warnings.extend(chain.warnings)
            if chain.is_repetitive and chain.rnt_min is not None:
                rnt_min = chain.rnt_min
                effective_bottom_time = dive.bottom_time_min + chain.rnt_min

    if kind == "heliox":
        result = plan_heliox_dive(dive.gas, dive.max_depth_fsw, effective_bottom_time)
    elif kind == "nitrox":
        if _is_nitrox_beyond_ceiling(dive) and previous is not None:
            warnings.append(
                "This nitrox dive itself exceeds 1.4 ata; any subsequent "
                "repetitive dive must not be chained from it."
            )
        result = plan_nitrox_dive(dive.gas, dive.max_depth_fsw, effective_bottom_time)
    else:
        result = plan_air_dive(dive.max_depth_fsw, effective_bottom_time)

    combined_warnings = tuple(warnings) + result.warnings
    return replace(
        result,
        residual_nitrogen_time_min=rnt_min,
        warnings=combined_warnings,
    )


def plan_series(dives: Sequence[Dive]) -> list[DiveResult]:
    """Plan an ordered series of dives, chaining repetitive-group logic.

    Each dive's ending repetitive group + the next dive's surface
    interval feed the Table 9-8 chain to produce RNT, added to the next
    dive's bottom time before its own lookup. The first dive is planned
    standalone (previous=None) regardless of whether it carries a
    surface_interval_before_min value.
    """
    if not dives:
        return []

    results: list[DiveResult] = []
    previous: DiveResult | None = None
    for i, dive in enumerate(dives):
        effective_previous = previous if i > 0 else None
        if i > 0 and dive.surface_interval_before_min is None:
            raise ValueError(
                f"Dive at index {i} is part of a series but has no "
                "surface_interval_before_min set"
            )
        result = plan_dive(dive, previous=effective_previous)
        results.append(result)
        previous = result
    return results
