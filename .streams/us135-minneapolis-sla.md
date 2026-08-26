# Stream log — us135-minneapolis-sla — 2026-08-25

- **Stream id:** `us135-minneapolis-sla` (Linear US-135, claimed via --assignee self).
- **Spine files I edit:** `apps/api/src/config.py`, `apps/api/src/spatial/city_registry.py`,
  `apps/api/src/producers/sla_licenses_producer.py` (one additive prepend),
  `apps/api/tests/unit/test_producers_minneapolis.py`, `README.md`. Spine manifest additive.
- **Scope:** Minneapolis row/city only. Deeds stays unregistered; other cities untouched.

## Live probe (before any edit) — On_Sale_Liquor/FeatureServer/0

Fetched 2026-08-25 via direct HTTP.

- **Layer metadata:** name `On_Sale_Liquor`, `geometryType` `esriGeometryPoint`,
  `objectIdField` **OBJECTID**, `maxRecordCount` **16000**. HTTP 200.
- **Companion layer live:** `Off_Sale_Liquor/FeatureServer/0` HTTP 200, **identical
  schema** (all 19 fields match). Row counts: On_Sale **646**, Off_Sale **188**.
- **Schema (as served):** `apn`, `OBJECTID`, `licenseNumber`, `licenseType`,
  `licenseStatus`, `liquorType`, `issueDate`(Date), `expirationYear`(Int),
  `expirationDate`(Date), `licenseName`, `address`, `endorsements`, `ward`,
  `neighborhood`, **`lat`/`long`**(Double), `xWebMercator`/`yWebMercator`,
  `lastUpdateDate`(Date).
- **lat/long spelling confirmed:** sample row `lat: 44.93383`, `long: -93.28474`
  (native attribute, WGS84). `query?f=json&outFields=*` returns all fields; the
  default (no `outFields`) returns **only `licenseName`** — the ArcGISClient passes
  `outFields=select or "*"`, so star is always used. Non-issue for the client.
- **Dates are epoch-ms** (esriFieldTypeDate): `issueDate` 1780324188000,
  `expirationDate` 1806623999000, `lastUpdateDate` 1780424126000 — converted to ISO
  by ArcGISClient (its `_flatten_feature` path), matching the research claim.
- **Freshness:** max `lastUpdateDate` = **1785521720000 → 2026-07-31** (On_Sale),
  newest `issueDate` = 2026-04-02. Research said "August 2026 lastEditDate" — the
  per-row `lastUpdateDate` max is 2026-07-31 (~25 days old as of the probe date).
  Actively maintained; G7/G11 fine. Minor freshness-value note, no STOP.

### Discrepancy vs ticket (does NOT block)

- The ticket's `field_map` lists `dba: ["licenseName"]`, but the shared
  `sla_licenses_producer.py` `dba` chain is a bare `row.get(...)` chain that never
  consulted the field map, so `licenseName` would never reach `event.dba`. **Fixed
  with one additive prepend** of `first_mapped(row, field_map, "dba")` to the chain
  (a no-op for every city whose map lacks a `dba` key; it also newly resolves NOLA's
  already-declared `dba:["businessname"]`, a latent-fix not a regression — no NOLA
  test pins dba=None).
- `incident_address: ["address"]` is inert in the SLA producer (its `address` chain
  reads `row["address"]` directly), but kept exactly per the ticket since the field
  still resolves.

## Decisions

- Register as ArcGIS FeatureServer, `watermark_col="issueDate"`, `id_keys=["licenseNumber","OBJECTID"]`.
- `oid_field="OBJECTID"`, `max_record_count=16000` (live cap), `expected_cadence_days=7`.
- `companion_endpoints={"off_sale": .../Off_Sale_Liquor/FeatureServer/0}` (Montgomery-partner precedent).
- Field map exactly per the ticket (`lat`/`long` → latitude/longitude via first_mapped).
- Producer change limited to the additive `first_mapped` prepend for `dba`; lat/long
  spelling is handled by the field map per the ticket (no `lat`/`long` fallback added).
- Minneapolis is an already-listed city (selector + CITY_CONFIGS + workers static copy
  all present). A FEED addition does not touch city wiring — verified mentally against
  `TestDashboardWiring` (checks per-city, not per-feed). No dashboard edit needed.
- README: Licenses cell → `ArcGIS (On/Off Sale liquor)`; Deeds cell was incorrectly
  labelled `— ArcGIS (On/Off Sale liquor; pending US-135)` → fixed to `— no verified
  sales feed` (liquor is the licenses feed; no deeds feed).

## Verification (from apps/api)

- `.venv/bin/python -m pytest tests/unit/test_producers_minneapolis.py` → pass.
- `.venv/bin/ruff check <touched file>` → zero net-new findings (baseline: existing
  findings on the shared files are pre-existing, not introduced).

## Next step

Orchestrator close-out: run `pytest -m interlock` + full suite; commit when the wave lands.
