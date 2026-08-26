# Stream log — us128-md-sdat-deeds — 2026-08-25

- **Stream id:** `us128-md-sdat-deeds` (Linear US-128, claimed via --assignee self).
- **Spine files I edit:** `apps/api/src/config.py`,
  `apps/api/src/spatial/city_registry.py`,
  `apps/api/src/producers/deeds_acris_producer.py`,
  `apps/api/src/producers/watermarks.py`,
  `apps/api/tests/unit/test_producers_baltimore.py`,
  `apps/api/tests/unit/test_producers_montgomery.py`,
  `apps/api/tests/unit/test_producers_prince_georges.py`,
  `apps/api/tests/unit/test_watermarks.py`,
  `README.md`. Spine manifest kept additive (no new spine path needed).
- **Interlock right:** held for this whole task. No other agent edits spine files.

## Live probe (before any edit) — all three SDAT per-county endpoints

Fetched live 2026-08-25 via direct HTTP to `opendata.maryland.gov` (NOT federated
under `data.maryland.gov`). Each returned a single `[ {...} ]` Socrata JSON row.

- Baltimore `3x3p-xk2v` — dataset "Baltimore City Real Property Assessments:
  Hidden Property Owner Names".
- Montgomery `kb22-is2w` — 220 columns.
- Prince George's `w3eb-4mzd` — 220 columns.

All three share the **same statewide SDAT schema** (nobody deviates: the three
target id/watermark/amount/grantor columns are byte-identical across counties).

### Confirmed column names (from `/api/views/<id>.json` metadata + live rows)

| Purpose | Socrata field name | type |
|---|---|---|
| parcel / doc_id / bbl | `account_id_mdp_field_acctid` | text |
| watermark (segment 1 transfer date) | `sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89` | text (`YYYY.MM.DD`) |
| transfer number / id-key 2 | `sales_segment_1_transfer_number_mdp_field_transno1_sdat_field_79` | text |
| consideration / amount | `sales_segment_1_consideration_mdp_field_considr1_sdat_field_90` | number |
| grantor | `sales_segment_1_grantor_name_mdp_field_grntnam1_sdat_field_80` | text |
| county | `county_name_mdp_field_cntyname` | text |
| native lat | `mdp_latitude_mdp_field_digycord_converted_to_wgs84` | number |
| native lng | `mdp_longitude_mdp_field_digxcord_converted_to_wgs84` | number |
| point | `mappable_latitude_and_longitude` | **point** |

### Point payload format (KEY live finding)

`mappable_latitude_and_longitude` arrives over `.json` as a **WKT string**, not a
nested dict and not a GeoJSON object:

```
"POINT (-76.62346538375218 39.311834646402595)"
```

Convention is WGS84 `POINT (lng lat)` (first coordinate = longitude). So the
ticket's field_map `"latitude": ["mappable_latitude_and_longitude.latitude"]`
(dotted dict access) cannot resolve a WKT string; the producer must parse the
WKT in its lat/lng chain. The duplicate native numeric columns
(`mdp_latitude_mdp_field_digycord_converted_to_wgs84` /
`mdp_longitude_mdp_field_digxcord_converted_to_wgs84`) are plain WGS84 numbers
and are the reliable field-map source.

### Watermark format / sentinel

Live values: real rows `2018.08.03`; no-sale rows the sentinel `0000.00.00`.
`datetime.strptime('0000.00.00', '%Y.%m.%d')` raises (month 0), so the sentinel
correctly stays None under `%Y.%m.%d`.

### Freshness / cadence

- `dataUpdatedAt` (Baltimore metadata) = **2026-08-05** → confirms the monthly
  snapshot cadence (`expected_cadence_days: 30`).
- Newest `sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89`
  (`$order=... DESC`): Baltimore **2026.07.24**, Montgomery **2026.07.06**,
  Prince George's **2026.07.13**. All July 2026 → per-county slicing holds the
  statewide `YYYY.MM.DD` watermark; freshest sale ~1 month back. The sweep doc's
  single "newest 2026.07.24" is the Baltimore/state figure; Montgomery and PG
  have their own newest.

### Per-parcel snapshot caveat (confirmed)

The dataset is an assessment snapshot, one row per parcel (segment 1 = most
recent sale; `_segment_2_`/`_3_` carry the prior two). No grantee column (SDAT
records grantor only). `ingestion_mode: "snapshot"` per the SF roll precedent.

## Decisions (deltas vs ticket, none block)

1. **lat/lng field_map uses the native numeric MDP columns** instead of the
   ticket's `mappable_latitude_and_longitude.latitude`/:longitude. Live, the
   point is a WKT string (dotted dict access cannot read it); the matched
   WGS84 numbers live in `mdp_latitude_mdp_field_digycord_converted_to_wgs84` /
   `mdp_longitude_mdp_field_digxcord_converted_to_wgs84`. The producer STILL
   parses the `mappable_latitude_and_longitude` WKT point in its lat/lng chain
   as a fallback (the ticket's required step-5 capability), so a row with a
   point but null MDP numbers still geocodes.
2. **`%Y.%m.%d` added to BOTH `parse_watermark` (watermarks.py) and the deeds
   producer's `_parse_datetime`.** The ticket names only watermarks.py, but the
   producer's own `_parse_datetime` already had a format list; without the
   addition the SDAT `recorded_date` falls back to `now()`.
3. **Production always passes `city_id` explicitly** (`run_stream` → `city_id=cid.value`),
   so the SDAT city-sniff is an autodetect fallback. To distinguish the three
   counties on autodetect it keys on the `county_name_mdp_field_cntyname`
   substring, defaulting to `baltimore` when a county name is absent. All three
   share an identical DEEDS field_map, so even a wrong city fallback parses
   correctly; the county-name branch just keeps the emitted `city_id`/borough
   honest.
4. **PG side-steps the held `qzrv-2tnv` parcel table entirely.** The SDAT
   dataset is Point-geocoded (WKT + numeric coordinate columns), so its
   geometry extraction parses cleanly and no MultiPolygon crash applies.
   The `TestPrinceGeorgesParcelSnapshotFinding` tests keep pinning the
   qzrv-2tnv deferral; only the registration assertion changes.
5. **No dashboard edits.** BALTIMORE / MONTGOMERY / PRINCE_GEORGES are already
   registered cities; verified their selector `<option>`, `CITY_CONFIGS` entries,
   and `apps/dashboard/public/index.html` static copy all carry the three ids
   (`TestDashboardWiring`). A FEED addition does not touch the city wiring.

## No STOP condition

The endpoints exist, are reachable anonymously, share the documented schema,
are point-geocoded, and the fresh-watermark/cadence facts hold. The only
deviations are the lat/lng field-map source (WKT/numeric vs dotted point) and
touching `_parse_datetime` in addition to `parse_watermark` — both handled, not
blockers.

## Verification (run from apps/api)

- `.venv/bin/python -m pytest tests/unit/test_producers_baltimore.py tests/unit/test_producers_montgomery.py tests/unit/test_producers_prince_georges.py tests/unit/test_watermarks.py` → pass.
- `.venv/bin/python -m pytest tests/unit/ -k "deeds or sdat or watermark"` → pass.
- `.venv/bin/ruff check <touched file>` → zero net-new findings vs pre-change baseline.
- `.venv/bin/python -m pytest -m interlock` runs at close-out by the orchestrator.
