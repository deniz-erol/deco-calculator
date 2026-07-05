"""Per-browser profile persistence via the visitor's own localStorage.

Replaces the old server-side ``app.store.JsonProfileStore`` (shared disk,
visible to every visitor on the public Streamlit Cloud instance) with
storage that lives entirely in the browser making the request. Nothing
here touches the filesystem or any shared/server-side state; every saved
profile is private to the one browser that saved it, and survives a page
refresh but not a different browser/device/incognito context — that is
the point.

All profiles for one browser are kept under a single namespaced
localStorage key (``_NAMESPACE_KEY``) holding one JSON object:
``{profile_name: {"label": str, "dives": [dive_dict, ...]}}``. Each
``dive_dict`` mirrors the exact shape the Planner's ``loaded_series``
prefill already expects (``gas_kind``, ``fo2``, ``fhe``, ``depth_fsw``,
``bottom_time_min``, ``surface_interval_before_min``), so loading a saved
profile back into the Planner needs no translation step.

Async hydration: the underlying ``streamlit_local_storage`` component
reads the browser's localStorage via a JS round-trip, which only
resolves on a rerun. ``LocalStorage.__init__`` already blocks (a short
``time.sleep`` poll against its own session-state key) until that first
hydration lands, so by the time any function below runs, the store is
either genuinely empty (``{}``) or fully hydrated — callers never see a
partial read. Every call below still defensively treats a non-dict
result as "not hydrated yet" and degrades to an empty collection rather
than raising, so a first-run hiccup shows an empty list instead of
crashing the page.

Rerun safety: writes only happen when the user explicitly clicks
Save/Delete (never on every script run), and each call site passes its
own stable ``key=`` to the underlying component so two writes in the
same run can't collide on Streamlit's default widget key.
"""

from __future__ import annotations

import json

import streamlit as st
from streamlit_local_storage import LocalStorage

_NAMESPACE_KEY = "deco_calculator.profiles"
_COMPONENT_INIT_KEY = "deco_calculator_ls_init"


class LocalStoreError(Exception):
    """Raised on malformed profile data. Never swallowed."""


def _store() -> LocalStorage:
    """One LocalStorage component instance per script run, cached in
    session_state so repeated calls within the same run (list, then
    load, then save) don't re-mount the component under the same key.
    """
    if "_local_storage_component" not in st.session_state:
        st.session_state["_local_storage_component"] = LocalStorage(key=_COMPONENT_INIT_KEY)
    return st.session_state["_local_storage_component"]


def _read_all() -> dict[str, dict]:
    """Return the whole ``{name: profile}`` map for this browser.

    Tolerates "not hydrated yet" (``None``) and any malformed/foreign
    value left under the key by returning an empty map rather than
    raising — a not-yet-loaded store must never crash the page.
    """
    raw = _store().getItem(_NAMESPACE_KEY)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _write_all(profiles: dict[str, dict], *, write_key: str) -> None:
    _store().setItem(_NAMESPACE_KEY, json.dumps(profiles), key=write_key)


def list_profiles() -> list[str]:
    """Names of profiles saved in THIS browser only, sorted for a stable
    dropdown order."""
    return sorted(_read_all().keys())


def save_profile(name: str, label: str, dives: list[dict], *, write_key: str = "ls_save") -> None:
    """Save (or overwrite) a named profile in this browser's localStorage.

    ``dives`` must already be plain JSON-serializable dicts in the same
    shape the Planner's ``loaded_series`` prefill consumes.
    """
    if not name or not name.strip():
        raise LocalStoreError("A profile name is required.")
    profiles = _read_all()
    profiles[name.strip()] = {"label": label, "dives": dives}
    _write_all(profiles, write_key=write_key)


def load_profile(name: str) -> dict:
    """Load one named profile's ``{"label": str, "dives": [...]}`` payload.

    Raises ``LocalStoreError`` if the name isn't present — callers should
    only call this after confirming ``name`` came from ``list_profiles()``.
    """
    profiles = _read_all()
    if name not in profiles:
        raise LocalStoreError(f"No saved profile named {name!r} in this browser.")
    payload = profiles[name]
    if not isinstance(payload, dict) or "dives" not in payload:
        raise LocalStoreError(f"Malformed saved profile {name!r}.")
    return payload


def delete_profile(name: str, *, write_key: str = "ls_delete") -> None:
    """Remove a named profile from this browser's localStorage, if present."""
    profiles = _read_all()
    if name in profiles:
        del profiles[name]
        _write_all(profiles, write_key=write_key)
