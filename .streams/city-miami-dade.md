# Stream log — city-miami-dade — 2026-08-27

Phase-2 leaf stream for Linear US-199: Miami-Dade County partial
registration (PERMITS + SLA + DEEDS). Spine is serial after this stream;
do not edit spine files here.

## Claim

- **Stream id:** `city-miami-dade`
- **Leaf files I will create/edit:**
  - `.streams/city-miami-dade.md` (this file)
  - `apps/api/src/spatial/cities/miami_dade.py` (NEW)
  - `apps/api/src/producers/field_maps_miami_dade.py` (NEW)
  - `apps/api/tests/unit/test_producers_miami_dade.py` (NEW)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py`
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/dashboard/public/index.html`

## Intent

Leaf-complete a PARTIAL Miami-Dade County metro from
`docs/research/wave-3-probe-miami-dade.md`: permits (address-only table),
LBT SLA snapshot, PaGis last-sale deeds. No 311. City identity is the
county (`miami_dade`); do not fold Broward or City of Miami into this
CityId. Tests pass without `CityId.MIAMI_DADE`. Record an exact spine delta.

## Decisions

- 2026-08-27 ~13:00 PT — Orchestrator dispatched this leaf after Honolulu
  and Orlando spines landed. Probe US-199 / miami-dade split is Done.
- 2026-08-27 ~13:00 PT — Leaf build. County-scale bbox (25.13–25.98 N,
  80.88–80.11 W) so Homestead / Aventura / Doral sit inside; center is
  Downtown Miami 25.7617, -80.1918. Six divisions, 18 submarkets, all
  `city_id="miami_dade"`.
- Field maps use producer-canonical keys (`issuance_date`, `address_street`)
  plus the probe's NYC-flavored aliases (`issued_date`, `incident_address`).
  SLA companions `certificate_of_use` / `enterprise_twin` are
  `companion_endpoints` metadata only — not extra FEED_SPECS keys.
- Deeds `where=PRICE_1 >= 10000`, `watermark_type=text`,
  `watermark_format=%Y%m%d`. Permits `non_spatial=True`,
  `rolling_window_days=730`, `needs_geocode=True`,
  `geocode_context="Miami-Dade County, FL"`.
- No 311. No CityId.MIAMI_DADE. No spine edits.

## Current step

Spine applied 2026-08-27 ~13:15 PT (orchestrator, serial hold). PERMITS +
SLA + DEEDS. No 311. `pytest -m interlock` **22 passed**. Leaf tests
**36 passed**. METRO_META + `index.html` byte-synced. Aliases exclude
`miami` / `broward` / `fort_lauderdale`.

## Next step

Linear US-199 comment + Done. No further code in this stream.

## Spine delta (do not apply in this stream)

- `CityId.MIAMI_DADE = "miami_dade"`
- Aliases: `miami_dade`, `miami-dade`, `miami dade`, `miami_dade_county`,
  `miami-dade county`, `miami dade county`, `mdc`. Do **not** alias
  `miami` / `broward` / `fort_lauderdale` (ADR 0007 sibling streams).
- Import spatial constants + `FIELD_MAP` from the leaf modules into
  `city_registry.py` / `cities/__init__.py`.
- `REGISTRY[CityId.MIAMI_DADE]` datasets: PERMITS + SLA + DEEDS from
  `MIAMI_DADE_FEED_SPECS` (copy extra keys onto typed DatasetSpec).
  Center `{"lat": 25.7617, "lng": -80.1918}`. name
  `"Miami-Dade County"`. state `"FL"`. job_suffix `"miami_dade"`.
- config.py three ArcGIS endpoints (permits Hub table, LBT view, PaGis
  MapServer/5) plus optional companion URL settings.
- Dashboard `METRO_META`: `miami_dade: { name: 'Miami-Dade County' }`
  plus the byte-synced `apps/dashboard/public/index.html` copy, snapshot
  export coverage, and res-5 grid-tile coverage (city-registration rule).
