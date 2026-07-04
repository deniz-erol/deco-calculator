# Table Data — Verification Checklist

**Read this before trusting or presenting any number from the tool.**

The table values are now **transcribed from the official US Navy Rev 7 tables PDF** you provided
(`docs/tables/USN_Rev7_Tables.pdf`), read cell-by-cell from rendered page images and cross-checked —
except nitrox, which is formula-derived. They are still marked `verified: false` because an automated
visual read can still make a transcription slip, so a **final human spot-check against a physical
manual is recommended** before any real use. Every result in the app already carries this warning.

> ⚠️ **The automated tests do NOT prove the numbers are correct.** They prove the *engine reads the
> tables correctly* (structure, rounding, lookup). Only a human cross-check against the manual proves
> the cell values are right. This checklist is that cross-check, in priority order (highest residual
> risk first).

To clear a table's warning banner after you've verified it: set `"verified": true` in that table's
`meta` block in `engine/tables/<file>.json`.

---

## ✅ Resolved (was a false alarm)
An earlier automated audit flagged that all Air 9-9 schedules bottom out at a **20 fsw** stop with no
10-fsw stop, and I suspected a column-shift error. **Reading your PDF confirmed this is CORRECT for
Rev 7** — Table 9-9's stop columns are 100→20 fsw; there is no 10-fsw column. The 30–150 fsw data was
also re-checked cell-by-cell against the PDF: **zero corrections needed.** Not a bug.

---

## Priority 1 — Heliox deep grids, 260–380 fsw (Table 12-4)
`engine/tables/heliox_12-4.json`
- Transcribed from PDF pages 31–40. 60–250 fsw is high-confidence; **260–380 fsw has dense adjacent
  single-digit cells** and is the most error-prone visual read. Spot-check a few deep schedules.

## Priority 2 — Air 9-9 new depths 160–190 fsw
`engine/tables/air_deco_9-9.json`
- 30–150 fsw is verified accurate against the PDF. **160–190 fsw was newly added** — spot-check a
  couple (e.g. 170/25 → group O, 190/35 → group Z) against the manual.

## Priority 3 — Air NDL + Repetitive Groups (Table 9-7) & Repetitive/RNT (Table 9-8)
`engine/tables/air_ndl_9-7.json`, `engine/tables/repetitive_9-8.json`
- These were transcribed in an **earlier pass and have NOT yet been re-verified against the PDF**
  (pages 4 and 5). Medium confidence. Spot-check: NDLs per depth; the fine rows 25/35/45/55 fsw in
  9-7; a few 9-8 surface-interval breakpoints and RNT values. *(I can do this cross-check from the
  rendered PDF pages on request.)*

## Low risk — verified or derived
- **Air 9-9, 30–150 fsw** — verified cell-by-cell against the PDF (accurate).
- **Heliox 12-4, 60–250 fsw** — high-confidence PDF transcription.
- **Nitrox 10-1** — formula-derived (`EAD = (D+33)·(FN2/0.79) − 33`, rounded up). Just confirm the
  O2% increments / 1.4-ata cutoff match the manual.

---

## Known coverage gaps / scope (not errors)
- **Air 9-9 covers 30–190 fsw.** 200–300 fsw (exceptional-exposure) schedules are omitted — deeper
  air deco dives show a clean "no schedule available" message, not a wrong number.
- **AIR/O2 in-water-oxygen schedules** (the AIR/O2 sub-rows in Table 9-9) are **not modeled** — the
  tool uses the plain AIR schedule only.
- **Heliox** has no repetitive-dive system (correct per the manual); heliox dives are standalone.
- All tables assume **sea level**; altitude diving is out of scope.
