# Stream log — platform-hunt — 2026-08-23

## Claim

- **Stream id:** `platform-hunt`
- **Leaf files I will create/edit:** `.streams/platform-hunt.md`, `docs/research/non-socrata-platforms.md`
- **Spine files I expect to need:** none (research-only; no source edits)

## Intent

Survey the non-Socrata open-data platforms named as out-of-scope in
`docs/research/city-expansion-candidates.md`: CKAN trio (Boston, Philadelphia,
San Diego), ArcGIS Hub group (Denver, DC, Minneapolis, Detroit), and the five
Socrata stragglers (Baltimore, Nashville, Louisville, Hartford, Tempe). Live-probe
every confirmed dataset for platform type, feed families (permits / 311 / sla /
deeds), geocoding, and recency. Deliverable: `docs/research/non-socrata-platforms.md`
with per-city findings tables and a client-cost matrix (SocrataClient vs
ArcGISClient vs missing CKAN client vs CSV-dump portals), ending in a ranked
recommendation positioned against New Orleans/Austin.

## Decisions

- 2026-08-23 (start) — Read context: city-expansion-candidates.md, socrata_client.py,
  arcgis_client.py, city_registry.py. ArcGIS client pages resultOffset/OBJECTID with
  maxRecordCount cap + exceededTransferLimit; flattens features to Socrata-shaped rows,
  lifts geometry to latitude/longitude, converts epoch-ms dates. CKAN has NO client;
  DatasetSpec.platform already accepts "ckan" string.
- Platform identification sweep: ALL nine ambiguous domains (incl. all five Socrata
  stragglers) are now ArcGIS Hub. Baltimore is NOT CKAN. Only Boston is real CKAN.
- Philadelphia is NOT CKAN — data hosted on CARTO (`phl.carto.com/api/v2/sql` live);
  opendataphilly.org is catalog only (CKAN paths 301).
- San Diego data.sandiego.gov is a custom DCAT/static portal; CSVs on seshat.datasd.org,
  daily refresh; no API → dump-only.
- Philadelphia field-probed: all four families on Carto, fresh to survey day
  (permits max 2026-08-22; 311 2026-08-23; licenses sane-max 2026-08-22 with year-3200
  sentinels; rtt_summary deeds-equivalent max 2026-08-10 with year-9798 sentinels;
  the_geom points). Best non-Socrata candidate.
- Boston field-probed via datastore_search(_sql): permits 660k rows geocoded, max
  issued_date 2026-08-22; 311 current-year slice w/ longitude/latitude; narrow liquor-
  board licenses; no sales. datastore_search_sql enabled (watermark-friendly).
- Detroit field-probed: all four families incl. assessor Property Sales (534k pts,
  sale_date through 2026-03, grantor/grantee/parcel/price); permits live in 2026;
  DateOnly fields return "YYYY-MM-DD" strings (epoch conversion no-op — fine).
- Denver: permits+311 strong (uppercase Longitude/Latitude attrs; non-spatial tables),
  licenses weak (no coords/issue date), sales ungeocoded (numeric yyyymmdd RECEPTION_DATE).
- DC: all four fresh (311 newest row survey day); layers year-sliced → watermark
  rollover caveat; server rejects returnCountOnly-with-where; uppercase coords.
- Minneapolis: CCS_Permits (maxRecordCount 16000) + Public_311_2026 live; liquor-only
  licenses; sales table stops 2025-09-30 despite Aug 2026 republish.
- Baltimore: permits + 311-2026 live (row created 2026-08-22); no market sales.
  Nashville: permits live (modified survey day), 311 stuck at 2025 slice. Louisville:
  partial, latest 311 slice 2025. Tempe: permits live only. Hartford: stale/dead.
- No token/auth required anywhere probed (incl. utility.arcgis.com premium-proxy URLs).

## Current step

Done. Deliverable written to `docs/research/non-socrata-platforms.md` (per-city tables,
client-cost matrix, ranked recommendation: NOLA first, Detroit second, Philadelphia
third pending ~150-line CARTO keyset client).

## Next step

None — stream complete. If acted on: implement CartoClient or register Detroit as the
first ArcGIS Hub city (parser fallbacks + cities/detroit.py only).
