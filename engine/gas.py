"""Gas-mix helper computations: fN2, MOD, ppO2, and mix classification.

These are thin, pure functions over :class:`engine.types.GasMix`. Most of
the logic already lives on the dataclass itself (``fn2``, ``kind``,
``mod_fsw``); this module adds the remaining physics (ppO2 at depth) and
boundary validation used by the nitrox/heliox lookup paths.
"""

from __future__ import annotations

from engine.types import GasMix

FSW_PER_ATA = 33.0  # sea-level: 33 fsw of seawater ~= 1 atmosphere


def fn2(gas: GasMix) -> float:
    """Nitrogen fraction of the mix."""
    return gas.fn2


def ppo2(gas: GasMix, depth_fsw: float) -> float:
    """Partial pressure of O2 (ata) at a given depth in fsw."""
    if depth_fsw < 0:
        raise ValueError("depth_fsw must be >= 0")
    ata = (depth_fsw + FSW_PER_ATA) / FSW_PER_ATA
    return round(gas.fo2 * ata, 4)


def mod_fsw(gas: GasMix, ppo2_max: float = 1.4) -> float:
    """Maximum operating depth (fsw) for a ppO2 ceiling. See GasMix.mod_fsw."""
    return gas.mod_fsw(ppo2_max=ppo2_max)


def kind(gas: GasMix) -> str:
    """Classify a gas mix as "air" | "nitrox" | "heliox"."""
    return gas.kind


def exceeds_ppo2(gas: GasMix, depth_fsw: float, ppo2_max: float = 1.4) -> bool:
    """True if ppO2 at depth_fsw exceeds the ppo2_max ceiling."""
    return ppo2(gas, depth_fsw) > ppo2_max + 1e-9


def validate_mix(gas: GasMix) -> None:
    """Raise ValueError if the mix is physically invalid.

    Boundary validation: fo2 and fhe must each be in (0, 1], and their
    sum must not exceed 1 (nitrogen fraction cannot be negative).
    """
    if gas.fo2 <= 0.0 or gas.fo2 > 1.0:
        raise ValueError(f"fo2 must be in (0, 1], got {gas.fo2}")
    if gas.fhe < 0.0 or gas.fhe > 1.0:
        raise ValueError(f"fhe must be in [0, 1], got {gas.fhe}")
    if gas.fo2 + gas.fhe > 1.0 + 1e-9:
        raise ValueError(
            f"fo2 + fhe must be <= 1, got fo2={gas.fo2} fhe={gas.fhe}"
        )
