# Stream log — city-minneapolis — 2026-08-24

## Claim

- **Stream id:** `city-minneapolis`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/minneapolis.py` (new)
  - `apps/api/tests/unit/test_producers_minneapolis.py` (new)
  - `apps/api/tests/unit/test_feed_staleness_probe.py` (NYC count fix if needed — no)
  - `.streams/city-minneapolis.md`
- **Spine files I expect to need:**
  - `apps/api/src/config.py` (2 ArcGIS endpoints)
  - `apps/api/src/spatial/city_registry.py` (CityId, aliases, REGISTRY entry)
  - `apps/api/src/spatial/cities/__init__.py` (exports)
  - `apps/api/src/serving/dashboard.py` (selector + CITY_CONFIGS)
  - `apps/dashboard/public/index.html` (regenerate via export script)

## Intent

US-79: register Minneapolis MN — permits (`CCS_Permits`) + year-sliced 311
(`Public_311_2026`) via the existing ArcGIS client. Licenses and sales
deliberately out (narrow liquor feeds; stale+ungeocoded sales). 311 joins the
annual rollover drill via `endpoint_by_year`. Re-probed at claim time:
both feeds live (permits newest issueDate 2026-08-23, 21,967 permits issued in
2026; 311 newest opened 2026-08-22), geometry geocoded 100%. Acceptance = gates
G1–G11 incl. G10 dashboard wiring (selector + CITY_CONFIGS + static copy).

Done = city module + spine registration + dashboard wiring + producer tests,
interlock + full suite green, US-79 resolved.

## Decisions

- 2026-08-24 (re-probe) — Permits layer DCAT "modified 2025-07-02" was stale
  metadata; actual rows are fresh (21,967 issued in 2026). Public_311_2026
  fresh to 2026-08-22. Both 100% point-geocoded via outSR=4326.
- 2026-08-24 — ArcGIS client already flattens geometry → lowercase
  `latitude`/`longitude` and converts epoch-ms dates → ISO; no client work.
  Only per-city field maps are needed (camelCase spellings).
- 2026-08-24 — 311 status field `CASESTATUS` is a raw int with unclear
  semantics; leave it unmapped (status defaults "Open"; `closed_date` carries
  closure). The signal fields are type + timestamps.
- 2026-08-24 — Licenses (On/Off_Sale_Liquor) skipped: narrow liquor-only
  feeds, weak SLA fit (matches LA-style partial). Sales skipped: stale
  (max SALE_DATE 2025-09-30) + county-coordinate X/Y, not lat/lng.
- 2026-08-24 — 311 `endpoint_by_year` maps 2015–2026; the annual rollover
  drill will require a 2027 mapping (fails loudly until added), like DC/Boston.

## Current step

DONE. City module + spine registration + dashboard wiring + producer tests
all in place; interlock green; full suite green (760 passed, 0 failures).
Working tree NOT committed (awaiting instruction; Pierce + others uncommitted).

## Next step

Linear resolution on US-79. If resumed: commit; in December append the
`Public_311_2027` mapping (drill fails loudly until then).