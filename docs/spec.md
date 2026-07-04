# Deco Calculator — Design Spec

**Status:** draft for review · **Date:** 2026-07-04
**Companion reference:** [`docs/research/usn-rev7-reference.md`](research/usn-rev7-reference.md)

---

> ⚠️ **SAFETY / SCOPE DISCLAIMER**
> This is an **academic prototype for a thesis presentation**. It is **NOT** a certified dive-planning
> tool and must never be used for operational dive planning. Decompression errors cause injury or
> death. Every screen must display this disclaimer.

## 1. Purpose

A web tool that reproduces **US Navy Diving Manual (Rev 7)** decompression **tables** for:
- **Air**, **Nitrox** (via Equivalent Air Depth), and **Heliox** dives.
- **Repetitive (consecutive) dives** for air/nitrox.
- Saving dives under **user profiles**.

It is a **faithful table-lookup calculator** — no decompression *algorithm*, no gas-switching engine.

## 2. Scope

**In scope**
- Air deco schedules + no-decompression limits (Tables 9-7, 9-9).
- Nitrox via EAD lookup (Table 10-1 → air tables), restricted to ≤ 1.4 ata ppO2.
- Heliox schedules (Table 12-4), treated as standalone single dives.
- Repetitive dives (Tables 9-7 → 9-8) for air/nitrox only.
- Feet/meters display toggle (fsw canonical).
- Profiles: save/load dives and dive series (local JSON).

**Out of scope (non-goals)**
- Any decompression algorithm (Bühlmann/VVAL-18) or table-vs-algorithm comparison.
- Mid-dive gas switching engine (heliox O2 switches come pre-baked in Table 12-4).
- Repetitive heliox dives (the Navy has no such system).
- Altitude diving, closed-circuit rebreather (EC-UBA) tables, cloud hosting, authentication.

## 3. Architecture

Two layers, cleanly separated. The **engine is pure Python** with zero UI/storage dependencies —
it is independently testable, which is what makes the numbers trustworthy for the presentation.

```
┌──────────────────────────────────────────────┐
│  UI  — Streamlit website                       │  input forms · schedule + profile chart · toggles
├──────────────────────────────────────────────┤
│  App — profile store (local JSON)              │  save/load users, dives, series
├──────────────────────────────────────────────┤
│  ENGINE — pure, tested table lookup            │  ← the core
│    air · nitrox(EAD) · heliox · repetitive     │
├──────────────────────────────────────────────┤
│  DATA — tables as versioned JSON + citations   │  transcribed from the manual / UHMS 2A-1
└──────────────────────────────────────────────┘
```

The engine imports nothing from the app or UI. The entire calculation set can run headless from a
script or a test — Streamlit is only a viewer.

## 4. Project structure

```
deco-calculator/
├── engine/
│   ├── types.py            # frozen dataclasses: GasMix, Dive, DecoStop, DiveResult
│   ├── gas.py              # GasMix helpers: fN2, MOD, ppO2, classification
│   ├── units.py            # fsw<->m display conversion (1 m = 3.28084 ft)
│   ├── tables/             # digitized data + provenance
│   │   ├── air_ndl_9-7.json
│   │   ├── air_deco_9-9.json
│   │   ├── repetitive_9-8.json
│   │   ├── nitrox_ead_10-1.json
│   │   ├── heliox_12-4.json
│   │   └── SOURCES.md      # revision (Rev7 Change A) + table/page citation per file
│   ├── lookup.py           # rounding rules + table selection
│   ├── air.py              # air lookup (NDL, deco schedule, ending group)
│   ├── nitrox.py           # EAD transform -> air lookup + 1.4 ata guard
│   ├── heliox.py           # Table 12-4 lookup (standalone)
│   ├── repetitive.py       # 9-7 -> 9-8 chain (group, SI credit, RNT)
│   └── planner.py          # plan_dive() / plan_series() orchestration
├── app/
│   ├── Home.py             # disclaimer + entry
│   ├── pages/
│   │   ├── 1_Plan_Dive.py
│   │   ├── 2_Dive_Series.py     # repetitive dives
│   │   ├── 3_Profiles.py
│   │   └── 4_About.py           # sources, disclaimer, method notes
│   └── store.py            # JSON profile store (atomic write, validate on load)
├── tests/
│   ├── fixtures/           # golden cases lifted from the manual's worked examples
│   ├── test_air.py
│   ├── test_nitrox_ead.py
│   ├── test_heliox.py
│   └── test_repetitive.py
├── data/profiles/          # user JSON files (gitignored)
└── docs/
    ├── spec.md
    └── research/usn-rev7-reference.md
```

## 5. Engine design

### 5.1 Core types (all frozen / immutable)

```python
@dataclass(frozen=True)
class GasMix:
    fo2: float
    fhe: float = 0.0
    @property
    def fn2(self) -> float: return round(1.0 - self.fo2 - self.fhe, 6)
    @property
    def kind(self) -> str:  # "air" | "nitrox" | "heliox"
        ...
    def mod_fsw(self, ppo2_max: float = 1.4) -> float: ...

@dataclass(frozen=True)
class Dive:
    gas: GasMix
    max_depth_fsw: float
    bottom_time_min: float
    surface_interval_before_min: float | None = None   # None = first dive of a series

@dataclass(frozen=True)
class DecoStop:
    depth_fsw: float
    minutes: float
    gas_phase: str = "back gas"    # heliox: "bottom mix" | "50% O2" | "100% O2"

@dataclass(frozen=True)
class DiveResult:
    stops: tuple[DecoStop, ...]
    total_stop_min: float
    time_to_first_stop: float | None
    no_decompression: bool
    ndl_min: float | None            # no-decompression limit for that depth
    repetitive_group: str | None     # None for heliox
    residual_nitrogen_time_min: float | None
    table_source: str                # e.g. "USN Rev7 Table 9-9"
    warnings: tuple[str, ...]         # MOD exceeded, exceptional exposure, non-repetitive, etc.
```

### 5.2 Engine interface

```python
def plan_dive(dive: Dive, previous: DiveResult | None = None) -> DiveResult: ...
def plan_series(dives: Sequence[Dive]) -> list[DiveResult]: ...
```

`plan_series` chains dives: each dive's ending group + the next surface interval feed the repetitive
lookup to produce RNT, which is added to the next dive's bottom time before its lookup.

### 5.3 Per-gas behavior

- **Air** — round depth/time up to next tabulated values; if within NDL use Table 9-7 (group + NDL);
  else use Table 9-9 (schedule + ending group).
- **Nitrox** — guard `ppO2 ≤ 1.4 ata` (else warning + block repetitive); look up EAD (Table 10-1),
  then run the air path at the EAD. Store both actual depth and EAD in the result for display.
- **Heliox** — look up Table 12-4 by depth + bottom time; return stops with their pre-baked O2 gas
  phases and chamber O2 periods; `repetitive_group = None` + warning that repetitive logic is N/A.
- **Repetitive (air/nitrox)** — Table 9-8 two-pass: (group + surface interval → new group), then
  (new group + next depth → RNT). Handle edge cases: `*` non-repetitive, `**` undeterminable,
  < 10 min interval, NDL crossover.

### 5.4 Validation at boundaries
Reject / warn on: depth or time outside table range, `fo2 + fhe > 1`, MOD exceeded, nitrox > 1.4 ata,
missing surface interval on a repetitive dive. Warnings surface in `DiveResult.warnings`, never crash.

## 6. Tables (data) — the credibility risk

Tables are **versioned JSON**, each with a `SOURCES.md` citation (Rev 7 Change A + table number).
**Cell values are transcribed from the manual PDF / UHMS Table 2A-1**, never from scraped text
(columns misalign). Every table ships with **golden test cases from the manual's worked examples**;
the engine must reproduce them exactly. This validation *is* the tool's credibility.

## 7. Persistence — local JSON (no database)

One file per user, e.g. `data/profiles/<user>.json`:

```json
{
  "user": { "id": "alex", "name": "Alex" },
  "series": [
    { "id": "2026-07-04-1", "label": "Day 1",
      "dives": [
        { "order": 0, "max_depth_fsw": 100, "bottom_time_min": 25,
          "fo2": 0.21, "fhe": 0.0, "surface_interval_before_min": null },
        { "order": 1, "max_depth_fsw": 60, "bottom_time_min": 30,
          "fo2": 0.32, "fhe": 0.0, "surface_interval_before_min": 90 }
      ] }
  ]
}
```

- **Atomic write** (temp file + `os.replace`) to avoid corruption.
- **Validate on load** with the same dataclasses (fail loud on malformed data).
- Behind a small `ProfileStore` interface, so SQLite could be swapped in later with no engine changes
  (not needed for the presentation).

## 8. UI (Streamlit)

- **Home** — disclaimer + navigation.
- **Plan Dive** — gas selector (air/nitrox/heliox), depth, bottom time, units toggle → deco schedule
  table + a dive-profile chart (Altair/Plotly). Shows EAD for nitrox, gas phases for heliox, warnings.
- **Dive Series** — build an ordered list of dives with surface intervals → chained repetitive results
  (group, RNT, schedule per dive). Save to a profile.
- **Profiles** — pick/create a user, list saved series, load one back into the planner.
- **About** — method notes, table sources, and the safety disclaimer.

Units toggle is a per-user display preference; storage is always fsw.

## 9. Build order

1. `types` + `gas` + `units` + input validation.
2. **Air tables (verified) + air lookup + golden tests** ← credibility milestone.
3. Repetitive chain (9-8) + golden tests.
4. Nitrox EAD (Table 10-1 → air path) + 1.4 ata guard + tests.
5. Heliox (Table 12-4) standalone + tests.
6. JSON `ProfileStore`.
7. Streamlit pages + charts + units toggle.
8. About page, disclaimers, polish for the presentation.

## 10. Open decisions (defaults chosen — easy to flip)

- **Nitrox above 1.4 ata:** default = **restrict / flag as not authorized**. (Alt: expose with big
  warnings.)
- **Heliox gas input:** default = **pick the table row by depth + bottom time** (mix shown as the
  table's Max/Min O2 window). (Alt: free O2 % entry validated against the window.)
- **Meters input:** default = **display-only toggle**; input stays in feet. (Alt: allow metric input,
  converting `fsw = m × 3.28084` then rounding up to the table depth.)

## 11. Tech stack

Python · Streamlit (web UI) · stdlib `json` + dataclasses (persistence) · Altair or Plotly (charts) ·
pytest (validation) · `uv` or Poetry (env). All Python, reproducible, presentation-friendly.
