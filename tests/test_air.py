"""Golden tests for air lookup: rounding rules, no-deco (9-7) vs deco (9-9)
selection, and exceptional-exposure flagging.

Fixtures in tests/fixtures/air_cases.json are transcribed from real US Navy
Diving Manual Rev 7 Change A (2018) Tables 9-7 and 9-9 (see
engine/tables/SOURCES.md and each table's meta.coverage_notes for the
transcription method and verification status).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.air import get_ndl, plan_air_dive
from engine.lookup import TableRangeError, round_up_depth, round_up_time

FIXTURES = Path(__file__).parent / "fixtures" / "air_cases.json"


def _load_fixtures() -> dict:
    with FIXTURES.open("r", encoding="utf-8") as fh:
        return json.load(fh)


FIXTURE_DATA = _load_fixtures()


@pytest.mark.parametrize("case", FIXTURE_DATA["no_deco_cases"], ids=lambda c: c["description"])
def test_no_deco_air_dive(case: dict) -> None:
    result = plan_air_dive(case["depth_fsw"], case["bottom_time_min"])
    assert result.no_decompression is True
    assert result.repetitive_group == case["expected_group"]
    assert result.ndl_min == case["expected_ndl_min"]
    assert result.stops == ()
    assert result.total_stop_min == 0.0
    assert result.time_to_first_stop is None
    assert result.table_source == "USN Rev7 Table 9-7"


@pytest.mark.parametrize("case", FIXTURE_DATA["deco_cases"], ids=lambda c: c["description"])
def test_deco_air_dive(case: dict) -> None:
    result = plan_air_dive(case["depth_fsw"], case["bottom_time_min"])
    assert result.no_decompression is False
    assert result.repetitive_group == case["expected_ending_group"]
    assert result.total_stop_min == case["expected_total_stop_min"]
    assert result.time_to_first_stop == case["expected_time_to_first_stop_min"]
    assert result.table_source == "USN Rev7 Table 9-9"
    if case.get("expected_exceptional_exposure"):
        assert any("Exceptional exposure" in w for w in result.warnings)


def test_rounding_depth_up() -> None:
    assert round_up_depth(55, [40, 50, 60, 80]) == 60
    assert round_up_depth(60, [40, 50, 60, 80]) == 60  # exact match, no rounding needed


def test_rounding_time_up() -> None:
    assert round_up_time(12, [10, 15, 20, 25]) == 15
    assert round_up_time(25, [10, 15, 20, 25]) == 25


def test_rounding_depth_out_of_range_raises() -> None:
    with pytest.raises(TableRangeError):
        round_up_depth(999, [30, 40, 50])


def test_rounding_time_out_of_range_raises() -> None:
    with pytest.raises(TableRangeError):
        round_up_time(999, [10, 20, 30])


def test_get_ndl_rounds_depth_up() -> None:
    # 52 fsw isn't tabulated; should round up to 55 fsw's NDL (74 min per Rev 7 Table 9-7).
    assert get_ndl(52) == 74.0


def test_get_ndl_deep_ladder_no_gap() -> None:
    # Regression: the old placeholder ladder skipped 140->150, so ~138 fsw rounded
    # wrong. The full Rev 7 air ladder tabulates every 10 ft; 137.8 must round up
    # to 140 fsw (NDL 10 min), not jump past it.
    assert get_ndl(137.8) == 10.0
    assert get_ndl(140) == 10.0
    assert get_ndl(190) == 5.0


def test_unverified_data_surfaces_warning() -> None:
    result = plan_air_dive(60, 25)
    assert any("verify before any real use" in w for w in result.warnings)


def test_depth_round_up_warns_on_no_deco_dive() -> None:
    # 52 fsw is not tabulated; rounds up to 55 fsw. At 55/20 the group is D
    # (55 fsw row: 20 min falls in the D column, max_time 25) per Rev 7 Table 9-7.
    result = plan_air_dive(52, 20)
    assert result.repetitive_group == "D"
    assert any("rounded up from 52 to 55" in w for w in result.warnings)
