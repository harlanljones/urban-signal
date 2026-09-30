# Stream log — geocode-context — 2026-09-30

## Claim

- **Stream id:** `geocode-context`
- **Leaf files created/edited:**
  - `apps/api/src/spatial/geocoder.py` (a leaf module, ADR 0004)
  - the note on the state check in `bowling_green.py`
  - tests: `test_geocoder.py`, and the geocoding caveats in
    `test_producers_savannah.py`, `test_producers_orlando.py`,
    `test_producers_henderson.py`, `test_producers_memphis.py` and
    `test_producers_bowling_green.py`
  - `docs/research/feed-health-2026-09-30.md`,
    `docs/research/four-family-depth-2026-09-30.md`, this file,
    `.streams/dispatch-log.md`
- **Spine files touched:** none. The producers call
  `geocode_row_if_declared` as before.
- **Generated surfaces:** none. No spec, endpoint or feed changes.

## Intent

Keep each address's state, and its city, in the query the geocoder
receives. 2,326 of 16,918 live queries (14%) lost it: `FL` read as a floor,
`#` cutting the rest of the line, and street words such as `CT` or `NE`
taken for a state so the context was never appended.

## Decisions

- 2026-09-30 — `NORM_VERSION` moves to `v3`. ADR 0004 keys the cache on it,
  and the v2 misses frozen for these queries must not be reused.
- 2026-09-30 — A line names its place only at its end: a state after a
  comma or before a ZIP code, a ZIP code after a comma, or the context's own
  words. A bare trailing ZIP after a street is not enough ("PO BOX 12345",
  a `#` unit of five digits).
- 2026-09-30 — `_STATE_RE` stays exported (leaf tests pin it); the hook no
  longer uses it on its own.
- 2026-09-30 — State-only contexts (Austin `sla` and `childcare`, "TX") are
  left for their specs: the rows carry a city and ZIP code to send instead.

## Current step

Done.

## Next step

Compose Austin's street, city and ZIP code for the geocoder; consider
rejecting geocoded points outside the metro box.
