# Table Data Sources & Verification Status

All tables target **US Navy Diving Manual, Revision 7, Change A (2018)**. The air tables
(9-7/9-8/9-9) and heliox (12-4) are **transcribed from the official US Navy Rev 7 tables PDF**;
nitrox (10-1) EAD values are **formula-derived** from the algebraic Equivalent Air Depth
formula. **None of the tables below are `verified: true` yet** — all are pending a final manual
cell-by-cell spot-check. Every JSON file's `meta.verified` flag reflects this, and the engine
surfaces an `unverified_warning` string into `DiveResult.warnings` on every lookup that touches
unverified data.

**Do not use any of this data for actual dive planning.** This is an academic prototype.

## Primary sources (see docs/research/usn-rev7-reference.md for the full list)
- Rev 7 tables — https://www.divetable.info/workshop/USN_Rev7_Tables.pdf
- Full manual (NAVSEA) — https://www.navsea.navy.mil/Portals/103/Documents/SUPSALV/Diving/US%20DIVING%20MANUAL_REV7.pdf
- UHMS Table 2A-1 (clean cell reference) — https://www.uhms.org/images/MEDFAQs/February-2017/2nd/US_DIVING_MANUALREV7_TT2A.pdf

## Per-table status

### `air_ndl_9-7.json` — Table 9-7 (No-Decompression Limits + Repetitive Group)
- **Verified:** No (`verified: false`) — pending a final manual cell-by-cell spot-check.
- **Coverage:** Full Rev 7 air ladder, depths 25-190 fsw (every tabulated depth: 25/30/35/40/45/
  50/55/60/70/80/90/100/110/120/130/140/150/160/170/180/190). Each row carries the real No-Stop
  Limit and the complete repetitive-group column (A-O plus Z where tabulated); each group's
  `max_time_min` is the manual's cumulative bottom-time value, and the highest group's max time
  equals the NDL. Transcribed by rendering the Rev 7 tables PDF at high DPI and cross-mapping every
  cell to its column by coordinate, then re-verifying against the rendered image.
- **Gaps:** The three shallowest manual rows (10/15/20 fsw) are deliberately omitted because their
  No-Stop Limit is "Unlimited", which cannot be represented as a finite float in this schema
  (shallow nitrox EAD lookups round up to 25 fsw instead). Not yet cross-checked against a second
  independent Rev 7 source, and not yet human spot-checked cell-by-cell.

### `air_deco_9-9.json` — Table 9-9 (Air Decompression Table)
- **Verified:** No (`verified: false`) — pending a final manual cell-by-cell spot-check.
- **Coverage:** Transcribed from the official US Navy Rev 7 tables PDF (page images
  `docs/tables/_render/page-06..24`), covering the standard air ladder 30-190 fsw (every 5 ft to
  60, then every 10 ft to 190). **AIR schedules only:** the manual prints two rows per bottom-time
  (AIR and AIR/O2 in-water-oxygen); the AIR/O2 in-water-O2 sub-rows exist in the source but are out
  of scope and **not modeled** here (this tool plans single-gas air with no gas switching, and the
  ending repetitive group is shared across both rows). Only bottom-times carrying a Navy-assigned
  ending repetitive group are included. Every row was cross-checked two ways arithmetically
  (time-to-first-stop vs. depth-to-deepest-stop, and summed stop minutes vs. total ascent time).
  **Depths 30-150 fsw were additionally re-verified cell-by-cell against the rendered page images
  with zero corrections** (their values matched the PDF exactly); **depths 160-190 fsw were newly
  transcribed** from the PDF (pages 21-24).
- **Gaps:** The AIR/O2 in-water-oxygen schedules and the 200-300 fsw exceptional-exposure block are
  out of scope and omitted. Pending a final human cell-by-cell spot-check before `verified` is
  flipped.

### `repetitive_9-8.json` — Table 9-8 (Surface Interval Credit + Residual Nitrogen Time, combined)
- **Verified:** No (`verified: false`) — pending a final manual cell-by-cell spot-check.
- **Coverage:** Full Rev 7 Table 9-8. Pass 1 (surface-interval credit): the diagonal Surface
  Interval Credit block for all starting groups A-O plus Z, with windows tiling contiguously down to
  group A and a final `*` row for intervals longer than the tabulated maximum (after which the next
  dive is not a repetitive dive). Pass 2 (RNT): the Residual Nitrogen Time grid for all
  end-of-SI groups A-O plus Z at every air-ladder depth 25-190 fsw. Transcribed by rendering the
  page at high DPI and mapping every cell to its column by coordinate; contiguity of the
  surface-interval windows was verified programmatically.
- **Gaps:** The manual's shallow depths 10/15/20 fsw are omitted to match the 9-7 ladder (25+ fsw).
  Two `**`/undeterminable cells at 25 fsw (groups O and Z) are deliberately omitted rather than
  mis-encoded; the engine surfaces a clean "no RNT cell seeded" warning for them. No `**`
  (RNT-undeterminable) cells fall within the 25-190 fsw range included here, so the
  para 9-9.1 subpara 8 substitute-depth procedure is not exercised by the shipped data. Pending a
  final human cell-by-cell spot-check.

### `nitrox_ead_10-1.json` — Table 10-1 (Equivalent Air Depth)
- **Verified:** No (`verified: false`) — pending a final manual cell-by-cell spot-check.
- **Coverage:** The full standard USN air depth ladder (40-190 fsw in the tabulated increments)
  crossed with the full Navy-authorized nitrox O2 range (25%-40% O2, in 2% steps). Values are
  **formula-derived, not transcribed:** every cell is computed deterministically from the algebraic
  EAD formula `EAD = (D + 33) * (FN2 / 0.79) - 33` (FN2 = 1 - FO2) and rounded up to the nearest
  depth in this table's own ladder — mirroring how the printed Table 10-1 rounds EAD to the next
  air-table depth. This grid has not been checked cell-by-cell against the manual PDF.
- **Gaps:** Cells where ppO2 = FO2 * (D/33 + 1) exceeds the 1.4 ata working ppO2 limit are omitted
  (the Navy does not authorize normal nitrox use beyond 1.4 ata, so no EAD is tabulated there). Any
  depth/FO2 combination not present in the grid falls back to the algebraic formula directly in
  `engine/nitrox.py`, which still carries the ppO2 guard/warning.

### `heliox_12-4.json` — Table 12-4 (Surface-Supplied Helium-Oxygen Decompression Table)
- **Verified:** No.
- **Coverage:** Transcribed cell-by-cell from the official US Navy Rev 7 tables PDF (pages 31-40,
  pre-rendered in `docs/tables/_render/`). Covers the full tabulated depth range 60-380 fsw in
  10-fsw increments (33 depths), each with its printed bottom-time schedules, gas-phase progression
  (bottom mix -> 50% O2 -> 100% O2), chamber O2 periods, and Max/Min O2% windows. Exceptional-exposure
  rows are flagged.
- **Gaps:** Pending a final manual cell-by-cell spot-check (still `verified: false`). Deep dense
  multi-stop rows (260-380 fsw) carry the highest transcription risk. No repetitive-group system
  exists for heliox (confirmed in the reference doc) — this is intentional, not a gap.

## Verification checklist (for whoever completes this against the manual)
- [ ] Spot-check the transcribed Table 9-7 NDLs and repetitive-group breakpoints cell-by-cell,
      all depths.
- [ ] Spot-check the transcribed Table 9-9 AIR stop schedules and ending groups cell-by-cell, all
      depths/times (30-150 were re-verified against the page images; give 160-190 extra attention as
      the newly transcribed block).
- [ ] Spot-check the transcribed Table 9-8 surface-interval breakpoints and RNT minutes
      cell-by-cell, all groups.
- [ ] Confirm the exact para 9-9.1 subpara 8 substitute-depth procedure before relying on it (the
      `**`/undeterminable cells are outside the shipped 25-190 fsw range, so it is not exercised by
      the current data).
- [ ] Spot-check the Table 10-1 EAD grid; confirm the formula-derived cells match the manual's
      printed values across the full 25%-40% O2 range.
- [ ] Spot-check the transcribed Table 12-4 stop schedules, O2 windows, and exceptional-exposure
      flags.
- [ ] Confirm all snapshots are Rev 7 **Change A** (2018), not the 2016 base release.
- [ ] Flip each file's `meta.verified` to `true` only after the above is done for that table.
