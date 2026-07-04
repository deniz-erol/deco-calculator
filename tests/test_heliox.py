"""Golden tests for heliox standalone lookup (Table 12-4): stop schedule,
pre-baked gas phases, no repetitive-group system, and the O2% window check.

Data is transcribed from the official US Navy Rev 7 tables PDF (Table 12-4),
covering 60-380 fsw in 10-fsw steps. Assertions below are grounded in the
transcribed values, not the old seeded placeholders.
"""

from __future__ import annotations

import pytest

from engine.heliox import plan_heliox_dive
from engine.lookup import TableRangeError
from engine.types import GasMix


def test_heliox_standalone_lookup_matches_transcribed_schedule() -> None:
    # 150 fsw window is Max 23.4% / Min 14.0%; fo2=0.18 is inside it.
    # 150/60 schedule (p33): stops 60:7, 50:10, 40:10, 30:31, 20:56 (100% O2),
    # first stop time 3:00 = 3.0 min, total = 7+10+10+31+56 = 114.
    gas = GasMix(fo2=0.18, fhe=0.82)
    result = plan_heliox_dive(gas, depth_fsw=150, bottom_time_min=60)
    assert result.time_to_first_stop == 3.0
    assert result.total_stop_min == 114.0
    assert len(result.stops) == 5
    assert result.stops[0].gas_phase == "50% O2"
    assert result.stops[-1].depth_fsw == 20.0
    assert result.stops[-1].gas_phase == "100% O2"
    assert result.table_source == "USN Rev7 Table 12-4"


def test_heliox_deep_dive_starts_on_bottom_mix() -> None:
    # 250 fsw window is Max 15.2% / Min 10.0%; fo2=0.12 is inside it.
    # 250/60 (p36, exceptional) starts with a 110 fsw bottom-mix stop.
    gas = GasMix(fo2=0.12, fhe=0.88)
    result = plan_heliox_dive(gas, depth_fsw=250, bottom_time_min=60)
    assert result.stops[0].gas_phase == "bottom mix"
    assert result.stops[0].depth_fsw == 110.0
    # sanity: total equals the sum of the printed stop minutes
    assert result.total_stop_min == sum(s.minutes for s in result.stops)


def test_heliox_no_stops_for_short_shallow_dive() -> None:
    # 60 fsw / 30 min (p31) is a direct-ascent row: no decompression stops.
    gas = GasMix(fo2=0.30, fhe=0.70)  # inside 60 fsw window (Max 40.0 / Min 14.0)
    result = plan_heliox_dive(gas, depth_fsw=60, bottom_time_min=30)
    assert len(result.stops) == 0
    assert result.total_stop_min == 0.0


def test_heliox_has_no_repetitive_group() -> None:
    gas = GasMix(fo2=0.18, fhe=0.82)
    result = plan_heliox_dive(gas, depth_fsw=150, bottom_time_min=60)
    assert result.repetitive_group is None
    assert result.residual_nitrogen_time_min is None
    assert any("no repetitive-group" in w.lower() for w in result.warnings)


def test_heliox_exceptional_exposure_flagged() -> None:
    # 200/120 (p35) is below the Exceptional Exposure divider.
    gas = GasMix(fo2=0.18, fhe=0.82)  # inside 200 fsw window (Max 18.4 / Min 14.0)
    result = plan_heliox_dive(gas, depth_fsw=200, bottom_time_min=120)
    assert any("Exceptional exposure" in w for w in result.warnings)


def test_heliox_depth_rounds_up() -> None:
    # 140 and 150 are both tabulated now; use a non-multiple-of-10 depth.
    gas = GasMix(fo2=0.18, fhe=0.82)
    result = plan_heliox_dive(gas, depth_fsw=145, bottom_time_min=30)
    assert result.actual_depth_fsw == 145
    assert any("rounded up from 145 to 150" in w for w in result.warnings)


def test_heliox_gas_outside_o2_window_warns() -> None:
    # 250 fsw window is Max 15.2% / Min 10.0%; 0.30 fo2 is way outside it.
    gas = GasMix(fo2=0.30, fhe=0.70)
    result = plan_heliox_dive(gas, depth_fsw=250, bottom_time_min=15)
    assert any("outside the Table 12-4 window" in w for w in result.warnings)


def test_heliox_time_out_of_transcribed_range_raises() -> None:
    # Max tabulated bottom time in any row is 120 min.
    gas = GasMix(fo2=0.18, fhe=0.82)
    with pytest.raises(TableRangeError):
        plan_heliox_dive(gas, depth_fsw=150, bottom_time_min=999)


def test_heliox_depth_beyond_table_raises() -> None:
    # Max tabulated depth is 380 fsw.
    gas = GasMix(fo2=0.10, fhe=0.90)
    with pytest.raises(TableRangeError):
        plan_heliox_dive(gas, depth_fsw=400, bottom_time_min=10)
