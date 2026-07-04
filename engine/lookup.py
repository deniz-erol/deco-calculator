"""Shared table-lookup mechanics: rounding rules, table loading, and the
data-provenance signal.

Rounding rules (per the reference doc): depth rounds UP to the next
tabulated depth; bottom time rounds UP to the next tabulated time.
Both raise if the requested value exceeds the table's range, since a
silent fallback would misrepresent the schedule.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

TABLES_DIR = Path(__file__).parent / "tables"


class TableRangeError(ValueError):
    """Raised when a requested depth/time falls outside the table's range."""


@dataclass(frozen=True)
class TableMeta:
    """Provenance info surfaced from a table's JSON `meta` block."""

    table: str
    verified: bool
    unverified_warning: str | None

    def warnings(self) -> tuple[str, ...]:
        if self.verified:
            return ()
        msg = self.unverified_warning or (
            f"Table {self.table} data not yet verified against the manual"
        )
        return (msg,)


@lru_cache(maxsize=None)
def load_table(filename: str) -> dict[str, Any]:
    """Load and cache a JSON table file from engine/tables/."""
    path = TABLES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Table file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def table_meta(data: dict[str, Any]) -> TableMeta:
    """Extract a TableMeta from a loaded table's `meta` block."""
    meta = data.get("meta", {})
    return TableMeta(
        table=meta.get("table", "unknown"),
        verified=bool(meta.get("verified", False)),
        unverified_warning=meta.get("unverified_warning"),
    )


def round_up_depth(requested_fsw: float, tabulated_depths: list[float]) -> float:
    """Round a requested depth UP to the next tabulated depth.

    Raises TableRangeError if the requested depth exceeds the table's
    maximum tabulated depth.
    """
    if requested_fsw < 0:
        raise ValueError("requested_fsw must be >= 0")
    candidates = sorted(tabulated_depths)
    for depth in candidates:
        if depth >= requested_fsw - 1e-9:
            return depth
    raise TableRangeError(
        f"Requested depth {requested_fsw} fsw exceeds table range "
        f"(max tabulated depth {candidates[-1]} fsw)"
    )


def round_up_time(requested_min: float, tabulated_times: list[float]) -> float:
    """Round a requested bottom time UP to the next tabulated time.

    Raises TableRangeError if the requested time exceeds the table's
    maximum tabulated time for that row.
    """
    if requested_min < 0:
        raise ValueError("requested_min must be >= 0")
    candidates = sorted(tabulated_times)
    for time_val in candidates:
        if time_val >= requested_min - 1e-9:
            return time_val
    raise TableRangeError(
        f"Requested bottom time {requested_min} min exceeds table range "
        f"(max tabulated time {candidates[-1]} min)"
    )
