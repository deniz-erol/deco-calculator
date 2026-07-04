"""Golden tests for the Table 9-8 two-pass repetitive chain and its edge
cases: `*` non-repetitive, `**` RNT-undeterminable, <10 min surface
interval, and NDL crossover via plan_series.

Values are transcribed from real US Navy Diving Manual Rev 7 Change A (2018)
Table 9-8 (surface-interval-credit diagonal + residual-nitrogen-time grid,
page 9-64). See engine/tables/repetitive_9-8.json meta.coverage_notes for
the transcription method and verification status.
"""

from __future__ import annotations

import copy

import pytest

import engine.repetitive as repetitive_module
from engine.lookup import load_table
from engine.planner import plan_dive, plan_series
from engine.repetitive import (
    NON_REPETITIVE_MARK,
    RNT_UNDETERMINABLE_MARK,
    REPETITIVE_FILE,
    chain_repetitive,
    credited_group,
    residual_nitrogen_time,
)
from engine.types import Dive, GasMix


def test_pass1_credited_group_within_seeded_window() -> None:
    # Group D, 60 min SI -> falls in the 53-107 window -> new group C
    # (Rev 7 Table 9-8 surface-interval-credit diagonal).
    result = credited_group("D", 60)
    assert result.is_repetitive is True
    assert result.new_group == "C"


def test_pass2_rnt_lookup() -> None:
    # Group C at 40 fsw -> RNT 29 min (Rev 7 Table 9-8 residual-nitrogen grid).
    result = residual_nitrogen_time("C", 40)
    assert result.rnt_min == 29


def test_full_chain() -> None:
    # Group D + 60 min SI -> new group C; C + 40 fsw -> RNT 29 min.
    result = chain_repetitive("D", 60, 40)
    assert result.new_group == "C"
    assert result.rnt_min == 29


def test_non_repetitive_interval_star() -> None:
    # Group D, SI >= 324 min -> '*' -> not repetitive, no RNT (D's last
    # tabulated window ends at 323 min -> A; beyond that is non-repetitive).
    result = credited_group("D", 400)
    assert result.is_repetitive is False
    assert result.new_group is None
    assert any("not a repetitive dive" in w for w in result.warnings)


def test_rnt_undeterminable_double_star(monkeypatch: pytest.MonkeyPatch) -> None:
    # The real Rev 7 RNT grid has no '**' (undeterminable) cells within the
    # 25-190 fsw range shipped here -- '**' cells live only at 10/15/20 fsw,
    # which are intentionally excluded (see meta.coverage_notes). To keep the
    # engine's '**'-handling code path under test, inject a synthetic '**'
    # cell into a copy of the loaded table and confirm the engine surfaces the
    # undeterminable warning rather than fabricating an RNT number.
    real = load_table(REPETITIVE_FILE)
    patched = copy.deepcopy(real)
    patched["rnt_pass"]["F"]["100"] = RNT_UNDETERMINABLE_MARK
    monkeypatch.setattr(repetitive_module, "load_table", lambda _fn: patched)

    result = residual_nitrogen_time("F", 100)
    assert result.rnt_min is None
    assert result.is_repetitive is True  # group is valid, RNT specifically undeterminable
    assert any("undeterminable" in w for w in result.warnings)


def test_surface_interval_below_10_min_not_credited() -> None:
    result = credited_group("D", 5)
    assert result.is_repetitive is False
    assert result.new_group is None
    assert any("credit floor" in w for w in result.warnings)


def test_plan_series_chains_group_and_rnt() -> None:
    dive1 = Dive(gas=GasMix(fo2=0.21), max_depth_fsw=60, bottom_time_min=25)
    dive2 = Dive(
        gas=GasMix(fo2=0.21),
        max_depth_fsw=40,
        bottom_time_min=30,
        surface_interval_before_min=60,
    )
    results = plan_series([dive1, dive2])
    assert len(results) == 2
    first, second = results
    assert first.repetitive_group == "E"  # 60fsw/25min -> E group (Rev 7 Table 9-7)
    # dive1 ends group E; 60 min SI -> new group D (E window 53-104); D @ 40fsw -> RNT
    assert second.residual_nitrogen_time_min is not None
    assert second.residual_nitrogen_time_min > 0


def test_plan_series_requires_surface_interval_for_non_first_dive() -> None:
    dive1 = Dive(gas=GasMix(fo2=0.21), max_depth_fsw=60, bottom_time_min=25)
    dive2 = Dive(gas=GasMix(fo2=0.21), max_depth_fsw=40, bottom_time_min=30)  # missing SI
    with pytest.raises(ValueError):
        plan_series([dive1, dive2])


def test_plan_series_first_dive_ignores_previous() -> None:
    dive1 = Dive(gas=GasMix(fo2=0.21), max_depth_fsw=60, bottom_time_min=25)
    results = plan_series([dive1])
    assert len(results) == 1
    assert results[0].residual_nitrogen_time_min is None


def test_ndl_crossover_repetitive_dive_becomes_deco_dive() -> None:
    # dive1 shallow no-deco air dive ending group I (60fsw/50min per Rev 7 9-7:
    # 60fsw NDL is 63 min, and 50 min falls in the I column, max_time 51).
    dive1 = Dive(gas=GasMix(fo2=0.21), max_depth_fsw=60, bottom_time_min=50)
    result1 = plan_dive(dive1)
    assert result1.no_decompression is True
    assert result1.repetitive_group == "I"

    # Chain: group I + 15 min SI -> credited group I (I's own window is 10-52
    # min -> stays I); I @ 60fsw -> RNT 52 min (Rev 7 Table 9-8).
    dive2 = Dive(
        gas=GasMix(fo2=0.21),
        max_depth_fsw=60,
        bottom_time_min=20,
        surface_interval_before_min=15,
    )
    result2 = plan_dive(dive2, previous=result1)
    # RNT (52 min, I@60fsw) + 20 min actual bottom time = 72 min, which exceeds
    # the 60fsw NDL of 63 min, forcing a decompression dive via Table 9-9.
    assert result2.residual_nitrogen_time_min == 52
    assert result2.no_decompression is False
    assert result2.table_source == "USN Rev7 Table 9-9"


def test_plan_dive_dispatches_to_nitrox_path() -> None:
    dive = Dive(gas=GasMix(fo2=0.32), max_depth_fsw=100, bottom_time_min=20)
    result = plan_dive(dive)
    # EAD for EAN32 @ 100 fsw = (100+33)*(0.68/0.79)-33 ~= 81.5 fsw, which rounds
    # UP to 90 fsw on the full Rev 7 air ladder (the old placeholder ladder
    # lacked a 90 rung and so rounded to 100 -- fixing the ladder fixes this).
    assert result.ead_fsw == 90.0
    assert result.actual_depth_fsw == 100
    assert "Table 10-1 (EAD)" in result.table_source


def test_plan_dive_dispatches_to_heliox_path() -> None:
    dive = Dive(gas=GasMix(fo2=0.18, fhe=0.82), max_depth_fsw=150, bottom_time_min=30)
    result = plan_dive(dive)
    assert result.repetitive_group is None
    assert result.table_source == "USN Rev7 Table 12-4"


def test_plan_dive_blocks_repetitive_chain_after_nitrox_beyond_1_4_ata() -> None:
    # EAN32 at 130 fsw exceeds 1.4 ata ppO2 -> repetitive dives not authorized.
    dive1 = Dive(gas=GasMix(fo2=0.32), max_depth_fsw=130, bottom_time_min=10)
    result1 = plan_dive(dive1)
    assert any("exceeding the 1.4 ata working limit" in w for w in result1.warnings)

    dive2 = Dive(
        gas=GasMix(fo2=0.32),
        max_depth_fsw=60,
        bottom_time_min=20,
        surface_interval_before_min=60,
    )
    result2 = plan_dive(dive2, previous=result1)
    assert result2.residual_nitrogen_time_min is None
    assert any("not authorized" in w for w in result2.warnings)
