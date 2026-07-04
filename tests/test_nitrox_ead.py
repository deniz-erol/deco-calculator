"""Golden tests for nitrox EAD computation, the 1.4 ata ppO2 guard, and MOD.

EAD formula and MOD formula are the two externally-verifiable anchors in
docs/research/usn-rev7-reference.md — asserted here against the raw
algebraic formula, independent of any seeded table cell.

Table 10-1 (engine/tables/nitrox_ead_10-1.json) is now a full deterministic
grid: the standard USN air depth ladder (40-190 fsw) crossed with the full
Navy-authorized nitrox O2 range (25%-40%). Every populated cell equals the
algebraic EAD formula rounded UP to the table's own depth ladder; cells
where ppO2 = FO2 * (D/33 + 1) exceeds the 1.4 ata working limit are omitted
(no key present), so lookup_ead() falls back to the live formula for those.
"""

from __future__ import annotations

import pytest

from engine.gas import mod_fsw, ppo2
from engine.lookup import load_table, round_up_depth
from engine.nitrox import compute_ead_formula, lookup_ead, plan_nitrox_dive
from engine.types import GasMix

PPO2_CEILING_ATA = 1.4


def test_ead_formula_matches_reference_doc() -> None:
    # EAD = (D + 33) * (FN2 / 0.79) - 33, from the reference doc verbatim.
    depth = 100.0
    fo2 = 0.32
    fn2 = 1.0 - fo2
    expected = (depth + 33.0) * (fn2 / 0.79) - 33.0
    assert compute_ead_formula(depth, fo2) == pytest.approx(expected)


def test_ead_formula_air_is_identity() -> None:
    # For air (FO2=0.21, FN2=0.79) EAD should equal the actual depth.
    assert compute_ead_formula(100.0, 0.21) == pytest.approx(100.0, abs=1e-6)


def test_table_populated_cells_match_formula_rounded_up() -> None:
    """Every populated Table 10-1 cell equals round_up(EAD_formula(D, FO2))
    against this table's own depth ladder, and respects the 1.4 ata ppO2
    ceiling (any cell present must have been within the authorized limit).
    """
    data = load_table("nitrox_ead_10-1.json")
    depths = data["depths_fsw"]
    fo2_columns = data["fo2_columns"]

    checked = 0
    for depth in depths:
        row = data["rows"][str(depth)]
        for fo2 in fo2_columns:
            key = str(fo2)
            measured_ppo2 = fo2 * (depth / 33.0 + 1.0)
            if key not in row:
                # Omitted: must genuinely exceed the 1.4 ata ceiling.
                assert measured_ppo2 > PPO2_CEILING_ATA + 1e-9
                continue
            assert measured_ppo2 <= PPO2_CEILING_ATA + 1e-9
            ead_raw = max(compute_ead_formula(depth, fo2), 0.0)
            expected = round_up_depth(ead_raw, depths)
            assert row[key] == pytest.approx(expected)
            checked += 1

    assert checked > 0


def test_lookup_ead_uses_seeded_table_when_available() -> None:
    # 100 fsw / EAN32: ppO2 = 0.32 * (100/33 + 1) = 1.2897 ata, within 1.4.
    # EAD formula = 81.48 -> rounds up to 90 on this table's ladder.
    ead, from_table = lookup_ead(100, 0.32)
    assert from_table is True
    assert ead == 90


def test_lookup_ead_falls_back_to_formula_beyond_ppo2_ceiling() -> None:
    # 130 fsw / EAN32: ppO2 = 0.32 * (130/33 + 1) = 1.5806 ata > 1.4,
    # so the cell is omitted from Table 10-1 and lookup falls back to the
    # live algebraic formula.
    ead, from_table = lookup_ead(130, 0.32)
    assert from_table is False
    assert ead > 0


def test_mod_formula_matches_reference_doc() -> None:
    # MOD_fsw = 33 * (ppo2_max / FO2 - 1)
    gas = GasMix(fo2=0.32)
    expected = 33.0 * (1.4 / 0.32 - 1.0)
    assert mod_fsw(gas, ppo2_max=1.4) == pytest.approx(expected)


def test_ppo2_guard_flags_dive_beyond_1_4_ata() -> None:
    # EAN32 at 130 fsw: ppO2 = 0.32 * (130+33)/33 = 1.58 ata > 1.4
    gas = GasMix(fo2=0.32)
    result = plan_nitrox_dive(gas, depth_fsw=130, bottom_time_min=20)
    assert any("exceeding the 1.4 ata working limit" in w for w in result.warnings)
    assert ppo2(gas, 130) > 1.4


def test_ppo2_within_guard_no_warning() -> None:
    # EAN32 at 60 fsw: ppO2 well under 1.4 ata.
    gas = GasMix(fo2=0.32)
    result = plan_nitrox_dive(gas, depth_fsw=60, bottom_time_min=20)
    assert not any("exceeding the 1.4 ata working limit" in w for w in result.warnings)


def test_nitrox_dive_runs_air_path_at_ead() -> None:
    gas = GasMix(fo2=0.32)
    result = plan_nitrox_dive(gas, depth_fsw=100, bottom_time_min=20)
    assert result.actual_depth_fsw == 100
    assert result.ead_fsw == 90  # seeded EAD cell for 100fsw/0.32 (rounded up)
    assert "Table 10-1 (EAD)" in result.table_source


def test_nitrox_shallower_ead_reduces_depth() -> None:
    # EAN36 at 80 fsw: ppO2 = 0.36 * (80/33 + 1) = 1.234 ata, within the 1.4
    # ata ceiling. EAD formula = 56.99 fsw -> rounds up to 60 fsw (seeded).
    ead, from_table = lookup_ead(80, 0.36)
    assert from_table is True
    assert ead == 60
    assert ead < 80  # EAD is shallower than actual depth for enriched O2


def test_invalid_mix_rejected() -> None:
    with pytest.raises(ValueError):
        plan_nitrox_dive(GasMix(fo2=0.9, fhe=0.5), depth_fsw=60, bottom_time_min=20)
