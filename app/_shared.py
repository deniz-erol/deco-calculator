"""Shared UI helpers: safety disclaimer, units toggle, and small
formatting utilities used across every Streamlit page.

Nothing here talks to the filesystem or the engine's table data — it
only formats values the engine already returned and manages display
preferences in ``st.session_state``. Keeping this in one module is what
keeps the disclaimer and the units toggle consistent page to page.
"""

from __future__ import annotations

import re

import streamlit as st

from app._i18n import DEFAULT_LANG, render_language_toggle, t
from engine.types import DiveResult
from engine.units import fsw_to_m, m_to_fsw

UNITS_KEY = "display_units"
FEET = "ft"
METERS = "m"

# Cross-page session-state keys, documented once here so pages interoperate
# instead of drifting:
#   display_units          -> "ft" | "m"                 (display preference)
#   series_dives            -> list[dict]                 (Dive Series builder rows)
#   active_user_id          -> str | None                  (Profiles page selection)
#   loaded_series           -> dict | None                 (series loaded from a profile)
#   plan_dive_prefill        -> dict | None                 (values pushed from Profiles)


def render_disclaimer(compact: bool = False) -> None:
    """Render the persistent safety disclaimer.

    Called at the top of every page (Home + every page in ``app/pages``)
    so the disclaimer is unmissable regardless of which page is active.

    ``compact=False`` (default) renders the full warning banner exactly
    as before — Home, Profiles, and About keep this untouched. Pages
    tight on vertical space above the fold (the Planner, whose inputs
    and chart must both stay visible without scrolling) can pass
    ``compact=True`` instead: a single bold one-line warning, with the
    full disclaimer text still reachable (never removed) inside an
    ``st.expander`` right below it.
    """
    if not compact:
        st.warning(t("disclaimer_text"), icon="⚠️")
        return
    st.warning(t("disclaimer_text_compact"), icon="⚠️")
    with st.expander(t("disclaimer_expander_label")):
        st.markdown(t("disclaimer_text"))


def init_units_toggle() -> str:
    """Ensure the units preference exists in session state; return it."""
    if UNITS_KEY not in st.session_state:
        st.session_state[UNITS_KEY] = FEET
    return st.session_state[UNITS_KEY]


def render_units_toggle(location=st.sidebar) -> str:
    """Render the feet/meters display toggle in the given container.

    Returns the current unit code ("ft" | "m"). This is a *display*
    preference only — engine calls always use fsw; conversion happens at
    the UI boundary via ``engine.units``.
    """
    init_units_toggle()
    choice = location.radio(
        t("units_label"),
        options=[FEET, METERS],
        format_func=lambda u: t("units_feet") if u == FEET else t("units_meters"),
        horizontal=True,
        key=UNITS_KEY,
    )
    return choice


def render_sidebar_toggles(location=st.sidebar) -> tuple[str, str]:
    """Render the units toggle and the language toggle together.

    Keeps the two display-preference controls adjacent in the sidebar on
    every page. Returns (units, lang) for callers that need the unit
    code; the language choice is read via ``t()`` elsewhere and doesn't
    need to be threaded through explicitly.
    """
    units = render_units_toggle(location)
    lang = render_language_toggle(location)
    return units, lang


def depth_to_display(depth_fsw: float, units: str) -> float:
    """Convert a canonical fsw depth to the display unit."""
    if units == METERS:
        return round(fsw_to_m(depth_fsw), 2)
    return round(depth_fsw, 1)


def depth_to_fsw(depth_display: float, units: str) -> float:
    """Convert a depth entered in the display unit back to canonical fsw.

    Rounded to a hundredth of a foot: the engine's table-rounding
    tolerance is 1e-9, but a display round-trip (fsw -> round to 2
    decimal meters -> back to fsw) can drift by several micro-feet from
    float arithmetic alone (e.g. 100 fsw -> "30.48" m -> 100.0000032
    fsw), which is enough to push a depth like 100 into the *next*
    tabulated row (130) instead of landing on 100. Rounding here keeps
    the display toggle a pure display concern, not an accidental
    table-selection change.
    """
    if units == METERS:
        return round(m_to_fsw(depth_display), 2)
    return float(depth_display)


def depth_label(units: str) -> str:
    return t("depth_label_m") if units == METERS else t("depth_label_ft")


def format_depth_both(depth_fsw: float | None) -> str:
    """Human-readable depth string always showing both units at once,
    e.g. ``"20 fsw (6.1 m)"``.

    Depth is stored canonically in fsw everywhere in the engine; this is
    the single formatter every display site should call so fsw and
    meters never drift apart or require a second conversion constant.
    Meters reuse ``engine.units.fsw_to_m`` (the same geometric factor the
    units toggle and the slider already use) — never a hardcoded 0.3048.
    fsw is shown as the table's rounded integer; meters to one decimal.
    "fsw" and "m" are universal abbreviations and are not translated.
    """
    if depth_fsw is None:
        return "—"
    meters = fsw_to_m(depth_fsw)
    return f"{round(depth_fsw):g} fsw ({meters:.1f} m)"


# Every seeded table's `meta.unverified_warning` (see engine/tables/*.json)
# carries its own custom wording (transcription vs. formula-derivation,
# different phrasing per table), so detection can't key on one exact
# marker string — it must recognize any of the known provenance phrasings
# plus the engine's generic fallback (``TableMeta.warnings()`` in
# engine/lookup.py). Each substring below is chosen to be unique to
# provenance text and NOT appear in any operational warning template in
# this module (in particular, plain "manual" is avoided: the operational
# ``warn_rnt_undeterminable`` warning also mentions "against the manual").
UNVERIFIED_WARNING_MARKERS: tuple[str, ...] = (
    "not yet verified against the manual",  # engine/lookup.py generic fallback
    "Transcribed from",  # air 9-7/9-8/9-9, heliox 12-4
    "derived from the US Navy EAD formula",  # nitrox 10-1
)


def _is_provenance_warning(warning: str) -> bool:
    return any(marker in warning for marker in UNVERIFIED_WARNING_MARKERS)


def split_warnings(result: DiveResult) -> tuple[list[str], list[str]]:
    """Split a DiveResult's warnings into (data-provenance, operational).

    Every seeded table's data-provenance warning (no table is marked
    verified yet — see engine/tables/*.json ``meta.unverified_warning``)
    is collapsed into a single, translated, unmissable disclaimer,
    separate from operational warnings (MOD exceeded, rounding,
    exceptional exposure, non-repetitive, heliox-has-no-rep-group, etc).
    Split happens on the raw English engine strings — translation happens
    afterwards, at render time.
    """
    provenance: list[str] = []
    operational: list[str] = []
    for w in result.warnings:
        if _is_provenance_warning(w):
            provenance.append(w)
        else:
            operational.append(w)
    return provenance, operational


def has_provenance_warning(result: DiveResult) -> bool:
    """True if any of this result's warnings is a data-provenance warning.

    Used to gate a single, page-level provenance banner across multiple
    results (e.g. every dive in a Dive Series chain) instead of repeating
    it once per dive.
    """
    return any(_is_provenance_warning(w) for w in result.warnings)


# ---------------------------------------------------------------------------
# Best-effort Turkish translation of the engine's English warning strings.
#
# The engine (engine/air.py, nitrox.py, heliox.py, repetitive.py, lookup.py)
# emits plain English f-strings with interpolated numbers/labels. Rather
# than touch the engine, each KNOWN template is matched here with an
# anchored regex (``re.fullmatch``, most-specific first) and the captured
# text is re-inserted verbatim into the Turkish template — never
# reparsed/reformatted, so "100.0" doesn't drift to "100" etc. Any
# warning that doesn't match a known template is shown in English,
# unchanged: this must never raise.
# ---------------------------------------------------------------------------
_STATIC_WARNING_KEYS = {
    (
        "Heliox has no repetitive-group / residual-nitrogen system in the Navy "
        "tables; repetitive logic is not applicable to this dive."
    ): "warn_repetitive_na",
    "Exceptional exposure schedule — see manual cautions": "warn_exceptional_exposure",
}

_NUM = r"[-+]?\d+(?:\.\d+)?"

_WARNING_PATTERNS: tuple[tuple[re.Pattern, str, tuple[str, ...]], ...] = (
    (
        re.compile(rf"Depth rounded up from ({_NUM}) to ({_NUM}) fsw per table rules"),
        "warn_depth_rounded",
        ("from_depth", "to_depth"),
    ),
    (
        re.compile(
            rf"Bottom time ({_NUM}) min exceeds NDL of ({_NUM}) min at "
            rf"({_NUM}) fsw; decompression required \(Table 9-9\)"
        ),
        "warn_bottom_time_exceeds_ndl",
        ("bottom_time", "ndl", "depth"),
    ),
    (
        re.compile(
            rf"ppO2 at ({_NUM}) fsw is ({_NUM}) ata, exceeding the "
            rf"({_NUM}) ata working limit — requires CO authorization "
            r"and surface-supplied gear; repetitive dives are NOT authorized\."
        ),
        "warn_ppo2_exceeds",
        ("depth", "ppo2", "ceiling"),
    ),
    (
        re.compile(
            rf"Requested depth ({_NUM}) fsw exceeds MOD of ({_NUM}) fsw "
            rf"for FO2=({_NUM}) at ppO2_max=({_NUM}) ata"
        ),
        "warn_mod_exceeded",
        ("depth", "mod", "fo2", "ceiling"),
    ),
    (
        re.compile(
            rf"EAD for ({_NUM}) fsw / FO2=({_NUM}) not in the seeded Table "
            r"10-1 subset; computed via the algebraic EAD formula instead"
        ),
        "warn_ead_fallback",
        ("depth", "fo2"),
    ),
    (
        re.compile(
            rf"Requested FO2=({_NUM}) is outside the Table 12-4 window for "
            rf"({_NUM}) fsw \(Max ({_NUM})% / Min ({_NUM})%\)"
        ),
        "warn_heliox_o2_window",
        ("fo2", "depth", "max_o2", "min_o2"),
    ),
    (
        re.compile(r"Table (.+) data not yet verified against the manual"),
        "warn_table_unverified",
        ("table",),
    ),
    (
        re.compile(
            rf"Surface interval ({_NUM}) min is below the "
            rf"({_NUM})-minute credit floor; tables do not credit "
            r"intervals this short — treating as a continuation dive "
            r"\(no RNT computed\)\."
        ),
        "warn_surface_interval_below_floor",
        ("si", "floor"),
    ),
    (
        re.compile(
            rf"Surface interval ({_NUM}) min exceeds the "
            r"non-repetitive threshold for group (\S+); the "
            r"next dive is not a repetitive dive \(no RNT added\)\."
        ),
        "warn_non_repetitive_interval",
        ("si", "group"),
    ),
    (
        re.compile(
            rf"RNT undeterminable for group (\S+) at ({_NUM}) fsw "
            r"\(manual para 9-9\.1 subpara 8, substitute-depth rule\) — verify "
            r"exact procedure against the manual before implementing; no RNT "
            r"value fabricated\."
        ),
        "warn_rnt_undeterminable",
        ("group", "depth"),
    ),
)


# Templates whose captured "depth" field is the ONLY fsw value in the
# sentence (every other captured number is a different unit — ata, %,
# minutes — or there is no other fsw field at all). Only these are safe
# to also show in meters: appending "(X m)" to a template that captures
# *two* fsw values (warn_depth_rounded's from/to, warn_mod_exceeded's
# depth/mod) would be ambiguous about which one the meters belong to, so
# those are deliberately left fsw-only here (best-effort, not attempted).
_SINGLE_DEPTH_WARNING_KEYS = frozenset(
    {
        "warn_bottom_time_exceeds_ndl",
        "warn_ppo2_exceeds",
        "warn_ead_fallback",
        "warn_heliox_o2_window",
        "warn_rnt_undeterminable",
    }
)


def _translate_warning(warning: str) -> str:
    """Best-effort Turkish translation of one engine warning string.

    Falls back to the original English string, unchanged, for anything
    that doesn't match a known static message or regex template — this
    function must never raise.
    """
    if st.session_state.get("lang", DEFAULT_LANG) != "tr":
        return warning

    static_key = _STATIC_WARNING_KEYS.get(warning)
    if static_key is not None:
        return t(static_key)

    for pattern, key, field_names in _WARNING_PATTERNS:
        match = pattern.fullmatch(warning)
        if match:
            values = dict(zip(field_names, match.groups()))
            if "depth" in values and key in _SINGLE_DEPTH_WARNING_KEYS:
                try:
                    values["depth_m"] = f"{fsw_to_m(float(values['depth'])):.1f}"
                except (TypeError, ValueError):
                    pass
            return t(key, **values)

    return warning


def render_provenance_banner() -> None:
    """Render the single, translated data-provenance disclaimer.

    Deliberately quieter than the operational warnings below (``st.info``
    instead of ``st.warning``/``st.error``) so the important, per-dive
    operational callouts (deco required, NDL exceeded, ppO2 over ceiling,
    etc.) visually stand out instead of being buried under provenance
    notices. Callers are responsible for calling this at most once per
    page/result — see ``has_provenance_warning`` for aggregating across
    multiple results (e.g. a Dive Series chain) before deciding whether
    to render it.
    """
    st.info(t("provenance_banner"), icon="🗂️")


def has_o2_deco(result: DiveResult) -> bool:
    """True if any stop in this result breathes an oxygen gas phase.

    Matches ``DecoStop.gas_phase`` values like ``"50% O2"`` / ``"100% O2"``
    (case-insensitive substring match on "o2"); air/back-gas-only
    schedules (``"back gas"``, ``"bottom mix"``) are excluded. Used to
    gate the air-break advisory note — US Navy O2-breathing procedure
    requires periodic air breaks during O2 decompression stops, which are
    a procedural detail not represented in the stop-time table cells
    themselves.
    """
    return any("o2" in stop.gas_phase.lower() for stop in result.stops)


def render_air_break_note() -> None:
    """Render the O2-decompression air-break advisory.

    Call once per result whenever ``has_o2_deco(result)`` is True, right
    next to that result's decompression schedule. Styled as
    ``st.warning`` (matching ``render_result_warnings``' operational
    warnings) rather than the quieter provenance ``st.info``, since this
    is a real safety caveat about a procedure the table cells don't show.
    """
    st.warning(t("air_break_note"), icon="⚠️")


def render_result_warnings(result: DiveResult) -> None:
    """Render a DiveResult's *operational* warnings only (deco required,
    NDL exceeded, ppO2 over ceiling, rounding, RNT edge cases, etc.), each
    as its own ``st.warning`` callout. Warnings are best-effort translated
    to Turkish via ``_translate_warning`` when the active language is
    "tr"; unmatched templates fall back to English.

    Data-provenance warnings are intentionally excluded here — render
    ``render_provenance_banner()`` once per page/result instead, so the
    same "table data not verified" disclaimer is never duplicated when a
    dive touches more than one seeded table (e.g. a repetitive dive that
    consults the 9-7 NDL table, the 9-8 repetitive table, and the 9-9
    deco table all at once).
    """
    _, operational = split_warnings(result)
    seen: dict[str, None] = {}
    for w in operational:
        translated = _translate_warning(w)
        seen.setdefault(translated, None)
    for translated in seen:
        st.warning(translated, icon="⚠️")


def gas_label(gas_kind: str) -> str:
    return {"air": t("gas_air"), "nitrox": t("gas_nitrox"), "heliox": t("gas_heliox")}.get(
        gas_kind, gas_kind.title()
    )
