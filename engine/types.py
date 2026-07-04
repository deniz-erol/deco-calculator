"""Core immutable data types shared across the deco-calculator engine.

All types are frozen dataclasses. Nothing in this module imports from
``app`` or Streamlit — the engine must remain a pure, independently
testable library.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GasMix:
    """A breathing gas mixture: fraction O2 and fraction He (rest is N2)."""

    fo2: float
    fhe: float = 0.0

    @property
    def fn2(self) -> float:
        """Fraction of nitrogen, derived so fo2 + fhe + fn2 == 1."""
        return round(1.0 - self.fo2 - self.fhe, 6)

    @property
    def kind(self) -> str:
        """Classify the mix as "air" | "nitrox" | "heliox"."""
        if self.fhe > 0.0:
            return "heliox"
        if abs(self.fo2 - 0.21) < 1e-6:
            return "air"
        return "nitrox"

    def mod_fsw(self, ppo2_max: float = 1.4) -> float:
        """Maximum operating depth in fsw for a given ppO2 ceiling.

        MOD_fsw = 33 * (ppo2_max / FO2 - 1)
        """
        if self.fo2 <= 0.0:
            raise ValueError("fo2 must be > 0 to compute MOD")
        return 33.0 * (ppo2_max / self.fo2 - 1.0)


@dataclass(frozen=True)
class Dive:
    """A single dive segment: gas, depth, bottom time, and optional SI."""

    gas: GasMix
    max_depth_fsw: float
    bottom_time_min: float
    surface_interval_before_min: float | None = None  # None = first dive of series


@dataclass(frozen=True)
class DecoStop:
    """A single decompression (or chamber O2) stop."""

    depth_fsw: float
    minutes: float
    gas_phase: str = "back gas"  # heliox: "bottom mix" | "50% O2" | "100% O2"


@dataclass(frozen=True)
class DiveResult:
    """Result of planning a single dive against the Navy tables.

    Fields beyond the spec's §5.1 core set are documented extensions,
    appended at the end with defaults so the base shape stays a strict
    subset of what's specified:

    - ``actual_depth_fsw`` / ``ead_fsw``: nitrox stores both the real
      depth and the Equivalent Air Depth used for the air-table lookup.
    """

    stops: tuple[DecoStop, ...]
    total_stop_min: float
    time_to_first_stop: float | None
    no_decompression: bool
    ndl_min: float | None  # no-decompression limit for that depth
    repetitive_group: str | None  # None for heliox
    residual_nitrogen_time_min: float | None
    table_source: str  # e.g. "USN Rev7 Table 9-9"
    warnings: tuple[str, ...] = field(default_factory=tuple)
    # --- documented extensions (nitrox EAD display) ---
    actual_depth_fsw: float | None = None
    ead_fsw: float | None = None
