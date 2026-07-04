# US Navy Diving Manual (Rev 7) — Decompression Reference

> Research reference for the deco-calculator project. Every table structure and rule below is
> sourced from the US Navy Diving Manual **Revision 7** (current release: **Change A, 2018**).
> **Do not trust scraped PDF text for individual cell values** — transcribe numbers directly from
> the manual PDF or the UHMS Table 2A-1 reference (links at the bottom).

## Scope of this tool

Table-**lookup only** (no algorithm/Bühlmann), **single gas per dive**, sea-level. Gases: air,
nitrox (via EAD), heliox. Repetitive dives for air/nitrox only. Presentation/demo tool.

---

## 1. Air

- **Table 9-7** — No-Decompression Limits (NDL) + Repetitive Group Designators for no-decompression
  air dives. Input `depth (fsw) × bottom time (min)` → **Repetitive Group letter** and NDL.
- **Table 9-9** — Air Decompression Table (for dives that exceed the NDL). Input `depth × bottom
  time` → time-to-first-stop, stop depths/times, and ending repetitive group.
- **Rounding rules:** round depth **up** to the next tabulated depth; round bottom time **up** to
  the next tabulated time.
- Descent/ascent assumptions and "exceptional exposure" rows are flagged in the tables.

## 2. Nitrox (Nitrogen-Oxygen) — EAD method ONLY

- The Navy has **no dedicated open-circuit nitrox decompression table.** Nitrox is handled by the
  **Equivalent Air Depth (EAD)** method: compute EAD, then use the **air** tables (9-7 / 9-9) at
  that shallower depth.
- **Table 10-1 "Equivalent Air Depth Table"** — lookup keyed by `actual depth (fsw) × O2 %`
  (range **25%–40%**) → EAD in feet (already rounded up to the next tabulated air depth).
- **EAD formula (backup / validation):**
  - fsw: `EAD = (D + 33) × (FN2 / 0.79) − 33`
  - msw: `EAD = (D + 10) × (FN2 / 0.79) − 10`
  - where `FN2 = 1 − FO2`, air N2 fraction `= 0.79`.
- **Constraints:**
  - Normal working limit **1.4 ata ppO2**. `MOD_fsw = 33 × (ppO2_max / FO2 − 1)`.
  - Beyond the 1.4-ata line: needs CO authorization + surface-supplied gear, and **repetitive dives
    are NOT authorized**. Parenthesized Table 10-1 values are max allowable exposure times.
  - Depths not listed are "beyond the safe limits of NITROX diving."
- **Note:** the "N2O2 tables with their own rep-groups / RNT" in **Chapter 15 are closed-circuit
  rebreather (EC-UBA)** tables — **out of scope** for a single-gas open-circuit tool.

## 3. Heliox (Helium-Oxygen) — standalone

- **Table 12-4 "Surface-Supplied Helium-Oxygen Decompression Table"** (Ch. 12, Surface-Supplied
  Mixed Gas). Descent 75 fpm, ascent 30 fpm.
- **Inputs:** depth (fsw), bottom time (min), gas mix as a **per-depth Max O2 % / Min O2 % window**
  (e.g., 60 fsw → Max 40.0% / Min 14.0%; 370 fsw → Max 10.6% / Min 10.0%).
- **Outputs:** time-to-first-stop, decompression stop times at fixed stop depths (190…20 fsw), the
  **gas breathed at each phase (Bottom Mix → 50% O2 → 100% O2)**, and chamber O2 periods. Deep/long
  rows flagged "Exceptional Exposure."
- **CONFIRMED: no repetitive-group / residual-nitrogen system for heliox.** Rep-group logic is
  nitrogen-based (9-7/9-8) and does not apply. The only post-heliox rule is altitude/flying-after
  (Table 9-6 Note 5: wait 12 h after a no-stop He-O2 dive, 24 h after a deco dive).
- The heliox table **already includes its own O2 gas switches** in the printed schedule — so the
  tool just displays them; no gas-switching engine is needed.

## 4. Repetitive (consecutive) dives — air / nitrox-via-EAD

Chain (Chapter 9):
1. **Dive → Repetitive Group letter** via Table 9-7 (no-deco dives) or Table 9-9 (deco dives).
2. **Surface interval → new (credited) group:** enter **Table 9-8** on the diagonal at the group
   letter, read across to the surface-interval window, then down to the **new group**.
3. **New group + repetitive-dive depth → Residual Nitrogen Time (RNT)** in minutes: continue down
   the same column to the depth row.
4. **Add RNT to the next dive's actual bottom time** → equivalent single-dive bottom time, used
   against 9-7 / 9-9 for the repetitive dive.

- **Repetitive group scheme (Rev 7):** letters **A–O plus special Z** (`Z` = highest group at that
  depth regardless of bottom time). **Unchanged from Rev 6** — only the underlying algorithm changed
  (Rev 7 uses **VVal-79**, a Thalmann exponential-linear model), which recomputed the numeric limits.
- **Terminology mapping:** what recreational agencies (PADI/NAUI) split into a "Surface Interval
  Credit Table" + a "Residual Nitrogen Time Table" is **ONE combined Table 9-8** in the Navy manual,
  read in two passes. Build one 9-8 lookup with two read-passes.

### Edge cases the calculator must handle
- **`*` = non-repetitive interval:** surface interval longer than the tabulated max → the next dive
  is **not** a repetitive dive; use its actual bottom time (no RNT added).
- **`**` = RNT undeterminable:** routes to manual para **9-9.1 subpara 8** (substitute-depth rule —
  verify exact text against the manual before implementing).
- **Minimum surface interval:** intervals < **10 minutes** are not credited (tables start at `:10`);
  treat as a continuation/single dive.
- **NDL:** beyond a depth's no-stop limit (Table 9-7) the dive becomes a decompression dive (9-9).
- **Exceptional exposure** rows carry separate handling.
- **Nitrox beyond 1.4 ata:** repetitive dives not authorized.

## 5. Units — fsw vs msw

- **Keep fsw canonical.** Convert depth for **display only** with `1 m = 3.28084 ft` (geometric).
- Pressure-unit nuance (msw = bar/10 ≈ 32.6336 fsw vs 33 fsw ≈ 1 atm) **does not matter** as long as
  fsw stays canonical and you only convert depth for display. **Do not mix** the 3.28084 (geometric)
  and 3.26336 (pressure) factors.
- If users *enter* meters: treat as geometric depth (`fsw = m × 3.28084`), then round up to the
  table depth. Document this single convention.
- Navy tables assume **sea level (surface = 1 atm)**. Altitude diving needs separate correction
  tables (9-4/9-5) — **out of scope**, add a one-line disclaimer.

---

## Verify against the manual before hard-coding
- Exact numeric cell values (NDLs, RNT minutes, heliox stop times) — transcribe from the manual PDF
  or **UHMS Table 2A-1**, not scraped text.
- `**` handling — confirm para 9-9.1 subpara 8 full text.
- Confirm table snapshots are **Rev 7 Change A (2018)**, not the 2016 base.
- Decide whether to expose nitrox rows above 1.4 ata at all (recommend: restrict / flag).
- Heliox mix input model: pick table row by depth+bottom time vs. free O2 entry.

## Primary sources
- Rev 7 tables — https://www.divetable.info/workshop/USN_Rev7_Tables.pdf
- Rev 6 tables (for comparison) — https://www.divetable.info/workshop/USN_Rev6.pdf
- Full manual (NAVSEA) — https://www.navsea.navy.mil/Portals/103/Documents/SUPSALV/Diving/US%20DIVING%20MANUAL_REV7.pdf
- UHMS Table 2A-1 (clean cell reference) — https://www.uhms.org/images/MEDFAQs/February-2017/2nd/US_DIVING_MANUALREV7_TT2A.pdf
- VVal-79 validation — https://pmc.ncbi.nlm.nih.gov/articles/PMC7276270/
- EAD / MOD formulas — https://en.wikipedia.org/wiki/Equivalent_air_depth , https://en.wikipedia.org/wiki/Maximum_operating_depth
- fsw/msw units — https://en.wikipedia.org/wiki/Metre_sea_water
