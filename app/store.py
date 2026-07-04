"""Local JSON profile persistence.

One file per user under ``data/profiles/<user_id>.json``. Writes are
atomic (temp file + os.replace) to avoid corruption; loads validate the
JSON shape against the engine's dataclasses and fail loud on malformed
data, per spec §7.

This module is the only place in the ``app`` layer that touches the
filesystem for profile data; it depends on ``engine.types`` for the
dive shape but never the other way around.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

from engine.gas import validate_mix
from engine.types import Dive, GasMix

DEFAULT_PROFILES_DIR = Path(__file__).parent.parent / "data" / "profiles"


class ProfileStoreError(Exception):
    """Raised on malformed profile data or I/O failures. Never swallowed."""


@dataclass(frozen=True)
class UserProfile:
    id: str
    name: str


@dataclass(frozen=True)
class DiveSeries:
    id: str
    label: str
    dives: tuple[Dive, ...]


@dataclass(frozen=True)
class UserProfileData:
    user: UserProfile
    series: tuple[DiveSeries, ...] = field(default_factory=tuple)


class ProfileStore(Protocol):
    """Storage interface so SQLite (or anything else) could be swapped in
    later with no engine changes."""

    def load(self, user_id: str) -> UserProfileData: ...

    def save(self, data: UserProfileData) -> None: ...

    def list_users(self) -> list[str]: ...

    def exists(self, user_id: str) -> bool: ...


def _dive_to_dict(dive: Dive) -> dict:
    return {
        "order": None,  # set by caller before serialization; placeholder here
        "max_depth_fsw": dive.max_depth_fsw,
        "bottom_time_min": dive.bottom_time_min,
        "fo2": dive.gas.fo2,
        "fhe": dive.gas.fhe,
        "surface_interval_before_min": dive.surface_interval_before_min,
    }


def _dive_from_dict(payload: dict) -> Dive:
    required = {"max_depth_fsw", "bottom_time_min", "fo2"}
    missing = required - payload.keys()
    if missing:
        raise ProfileStoreError(f"Dive entry missing required fields: {sorted(missing)}")
    try:
        gas = GasMix(fo2=float(payload["fo2"]), fhe=float(payload.get("fhe", 0.0)))
        validate_mix(gas)
        dive = Dive(
            gas=gas,
            max_depth_fsw=float(payload["max_depth_fsw"]),
            bottom_time_min=float(payload["bottom_time_min"]),
            surface_interval_before_min=(
                float(payload["surface_interval_before_min"])
                if payload.get("surface_interval_before_min") is not None
                else None
            ),
        )
    except (TypeError, ValueError) as exc:
        raise ProfileStoreError(f"Malformed dive entry: {payload!r}: {exc}") from exc
    return dive


def _series_to_dict(series: DiveSeries) -> dict:
    dives_payload = []
    for order, dive in enumerate(series.dives):
        entry = _dive_to_dict(dive)
        entry["order"] = order
        dives_payload.append(entry)
    return {"id": series.id, "label": series.label, "dives": dives_payload}


def _series_from_dict(payload: dict) -> DiveSeries:
    if "id" not in payload or "label" not in payload:
        raise ProfileStoreError(f"Series entry missing 'id' or 'label': {payload!r}")
    raw_dives = payload.get("dives", [])
    if not isinstance(raw_dives, list):
        raise ProfileStoreError(f"Series 'dives' must be a list: {payload!r}")
    ordered = sorted(raw_dives, key=lambda d: d.get("order", 0))
    dives = tuple(_dive_from_dict(d) for d in ordered)
    return DiveSeries(id=payload["id"], label=payload["label"], dives=dives)


def _profile_to_dict(data: UserProfileData) -> dict:
    return {
        "user": asdict(data.user),
        "series": [_series_to_dict(s) for s in data.series],
    }


def _profile_from_dict(payload: dict) -> UserProfileData:
    if "user" not in payload:
        raise ProfileStoreError("Profile JSON missing required 'user' key")
    user_payload = payload["user"]
    if "id" not in user_payload or "name" not in user_payload:
        raise ProfileStoreError(f"'user' object missing 'id' or 'name': {user_payload!r}")
    user = UserProfile(id=user_payload["id"], name=user_payload["name"])
    raw_series = payload.get("series", [])
    if not isinstance(raw_series, list):
        raise ProfileStoreError("Profile JSON 'series' must be a list")
    series = tuple(_series_from_dict(s) for s in raw_series)
    return UserProfileData(user=user, series=series)


class JsonProfileStore:
    """File-per-user JSON profile store with atomic writes."""

    def __init__(self, base_dir: Path | str = DEFAULT_PROFILES_DIR):
        self._base_dir = Path(base_dir)

    def _path_for(self, user_id: str) -> Path:
        if not user_id or "/" in user_id or "\\" in user_id or user_id in {".", ".."}:
            raise ProfileStoreError(f"Invalid user_id: {user_id!r}")
        return self._base_dir / f"{user_id}.json"

    def exists(self, user_id: str) -> bool:
        return self._path_for(user_id).exists()

    def list_users(self) -> list[str]:
        if not self._base_dir.exists():
            return []
        return sorted(p.stem for p in self._base_dir.glob("*.json"))

    def load(self, user_id: str) -> UserProfileData:
        path = self._path_for(user_id)
        if not path.exists():
            raise ProfileStoreError(f"No profile found for user_id={user_id!r} at {path}")
        try:
            with path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ProfileStoreError(f"Malformed JSON in profile {path}: {exc}") from exc
        return _profile_from_dict(raw)

    def save(self, data: UserProfileData) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for(data.user.id)
        payload = _profile_to_dict(data)

        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._base_dir), prefix=f".{data.user.id}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
