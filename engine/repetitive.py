"""Repetitive-dive chain: Table 9-8, read in two passes.

Pass 1 — repetitive group + surface interval -> new (credited) group.
Pass 2 — new group + next dive's depth -> Residual Nitrogen Time (RNT).

Edge cases handled explicitly (see docs/research/usn-rev7-reference.md §4):
- ``*``  non-repetitive interval: SI exceeds the tabulated max for that
  starting group -> next dive is NOT repetitive; no RNT is added.
- ``**`` RNT undeterminable: routes to manual para 9-9.1 subpara 8. The
  exact substitute-depth procedure is NOT implemented (unverified) —
  this surfaces a clear warning instead of fabricating a number.
- Surface interval < 10 minutes: not credited by the tables (which start
  at :10); treated as effectively a continuation, so RNT is not
  computed and a warning is raised instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.lookup import load_table, table_meta

REPETITIVE_FILE = "repetitive_9-8.json"

NON_REPETITIVE_MARK = "*"
RNT_UNDETERMINABLE_MARK = "**"


@dataclass(frozen=True)
class RepetitiveResult:
    """Outcome of chaining one repetitive-dive transition."""

    new_group: str | None
    rnt_min: float | None
    is_repetitive: bool
    warnings: tuple[str, ...]


def credited_group(prior_group: str, surface_interval_min: float) -> RepetitiveResult:
    """Pass 1: prior repetitive group + surface interval -> new group.

    Returns a RepetitiveResult with is_repetitive=False (and new_group /
    rnt_min = None) when the interval is non-repetitive (``*``) or below
    the 10-minute credit floor.
    """
    data = load_table(REPETITIVE_FILE)
    meta = table_meta(data)
    warnings: list[str] = list(meta.warnings())
    min_credited = float(data["meta"]["min_credited_surface_interval_min"])

    if surface_interval_min < min_credited:
        warnings.append(
            f"Surface interval {surface_interval_min} min is below the "
            f"{min_credited:g}-minute credit floor; tables do not credit "
            "intervals this short — treating as a continuation dive "
            "(no RNT computed)."
        )
        return RepetitiveResult(
            new_group=None, rnt_min=None, is_repetitive=False, warnings=tuple(warnings)
        )

    if prior_group not in data["surface_interval_pass"]:
        warnings.append(
            f"No Table 9-8 surface-interval row seeded for group '{prior_group}' "
            "in this representative data subset"
        )
        return RepetitiveResult(
            new_group=None, rnt_min=None, is_repetitive=False, warnings=tuple(warnings)
        )

    rows = data["surface_interval_pass"][prior_group]
    for row in rows:
        lo = row["min_min"]
        hi = row["max_min"]
        if hi is None:
            in_range = surface_interval_min >= lo
        else:
            in_range = lo <= surface_interval_min <= hi
        if in_range:
            new_group = row["new_group"]
            if new_group == NON_REPETITIVE_MARK:
                warnings.append(
                    f"Surface interval {surface_interval_min} min exceeds the "
                    f"non-repetitive threshold for group {prior_group}; the "
                    "next dive is not a repetitive dive (no RNT added)."
                )
                return RepetitiveResult(
                    new_group=None,
                    rnt_min=None,
                    is_repetitive=False,
                    warnings=tuple(warnings),
                )
            return RepetitiveResult(
                new_group=new_group, rnt_min=None, is_repetitive=True, warnings=tuple(warnings)
            )

    warnings.append(
        f"Surface interval {surface_interval_min} min out of seeded range "
        f"for group {prior_group}"
    )
    return RepetitiveResult(
        new_group=None, rnt_min=None, is_repetitive=False, warnings=tuple(warnings)
    )


def residual_nitrogen_time(new_group: str, next_depth_fsw: float) -> RepetitiveResult:
    """Pass 2: new (credited) group + next dive's depth -> RNT (minutes).

    Returns rnt_min=None with a warning if the cell is marked ``**``
    (RNT undeterminable — manual para 9-9.1 subpara 8, not fabricated
    here) or missing from the seeded data subset.
    """
    data = load_table(REPETITIVE_FILE)
    meta = table_meta(data)
    warnings: list[str] = list(meta.warnings())

    rnt_rows = data["rnt_pass"]
    if new_group not in rnt_rows:
        warnings.append(
            f"No Table 9-8 RNT row seeded for group '{new_group}' in this "
            "representative data subset"
        )
        return RepetitiveResult(
            new_group=new_group, rnt_min=None, is_repetitive=True, warnings=tuple(warnings)
        )

    depth_key = str(int(next_depth_fsw))
    row = rnt_rows[new_group]
    if depth_key not in row:
        warnings.append(
            f"No Table 9-8 RNT cell seeded for group '{new_group}' at "
            f"{next_depth_fsw} fsw in this representative data subset"
        )
        return RepetitiveResult(
            new_group=new_group, rnt_min=None, is_repetitive=True, warnings=tuple(warnings)
        )

    cell = row[depth_key]
    if cell == RNT_UNDETERMINABLE_MARK:
        warnings.append(
            f"RNT undeterminable for group {new_group} at {next_depth_fsw} fsw "
            "(manual para 9-9.1 subpara 8, substitute-depth rule) — verify "
            "exact procedure against the manual before implementing; no RNT "
            "value fabricated."
        )
        return RepetitiveResult(
            new_group=new_group, rnt_min=None, is_repetitive=True, warnings=tuple(warnings)
        )

    return RepetitiveResult(
        new_group=new_group, rnt_min=float(cell), is_repetitive=True, warnings=tuple(warnings)
    )


def chain_repetitive(
    prior_group: str, surface_interval_min: float, next_depth_fsw: float
) -> RepetitiveResult:
    """Full two-pass chain: prior group + SI -> new group -> RNT at next depth."""
    pass1 = credited_group(prior_group, surface_interval_min)
    if not pass1.is_repetitive or pass1.new_group is None:
        return pass1
    pass2 = residual_nitrogen_time(pass1.new_group, next_depth_fsw)
    return RepetitiveResult(
        new_group=pass2.new_group,
        rnt_min=pass2.rnt_min,
        is_repetitive=True,
        warnings=tuple(pass1.warnings) + tuple(pass2.warnings),
    )
