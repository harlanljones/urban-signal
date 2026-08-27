# Stream log — city-orlando — 2026-08-27

Phase-2 leaf stream for Linear US-194: Orlando, FL geocoder-unlocked
registration (SLA Business Tax Receipts + STR licenses). Spine is serial
after this stream; do not edit spine files here.

## Claim

- **Stream id:** `city-orlando`
- **Leaf files I will create/edit:**
  - `.streams/city-orlando.md` (this file)
  - `apps/api/src/spatial/cities/orlando.py` (NEW)
  - `apps/api/src/producers/field_maps_orlando.py` (NEW)
  - `apps/api/tests/unit/test_producers_orlando.py` (NEW)
- **Spine files I expect to need (do NOT edit in this stream):**
  - `apps/api/src/spatial/city_registry.py` (CityId.ORLANDO, ALIASES, REGISTRY)
  - `apps/api/src/spatial/cities/__init__.py`
  - `apps/api/src/config.py`
  - `apps/api/src/serving/dashboard.py` METRO_META
  - `apps/dashboard/public/index.html` (city registration rule)

## Intent

Leaf-complete a PARTIAL Orlando metro on `data.cityoforlando.net`: SLA
`7388-4re5` (Business Tax Receipts) and SLA `ssrj-rbua` (STR Licenses).
Keep STR on the existing SLA feed type — do not invent a new FeedType
(spine). Tests pass without a registry entry. Re-probe ≤72h required.

## Decisions

- 2026-08-27 12:15 PT — Orchestrator claimed Linear US-194 and dispatched
  this leaf stream. STR stays an SLA until a later signal-family decision.
  Spine hold deferred until leaf + live probe land.

## Live probe (2026-08-27 12:35 PT)

Portal `data.cityoforlando.net`. Trust live rows, not the sweep.

| Feed | 4x4 | Newest watermark | 60d / 7d | Geo | Verdict |
|---|---|---|---|---|---|
| SLA BTR | `7388-4re5` | `received_date` 2026-08-27; `last_licensed_issue_date` 2026-08-27 | received 250/15; issued 274/15 | `geocoded_column` on **archive** (107894/118802) but **0/250** of 60d-received rows; live window is address-only `business_address` + FL State Plane `gpsx`/`gpsy` | Tier 2, `needs_geocode=True` |
| SLA STR | `ssrj-rbua` | `last_action_date` 2026-08-26 | last_action 32/3; issued 11/1 | none; 525/525 have `property_address` (street-only, no city/state) | Tier 2, `needs_geocode=True` |
| PERMITS (out of scope) | `ryhf-m453` | `issue_permit_date` live, 5208/60d, native `geocoded_column` | — | live+geocoded | **skipped** — ticket scope is the two SLA feeds; both SLA IDs are live |

rowsUpdatedAt: BTR 2026-08-27T19:30:13Z; STR 2026-08-27T19:30:35Z.

Sweep `geocoded_column` on BTR is real but **stale relative to the live window**. Ticket "address-only" is correct for new rows.

## Decisions

- STR registers as **SLA** (existing FeedType). Do not use `FeedType.STR` even though the enum exists unused. New-signal-family observation only (investor-buyout / STR occupancy) — prototype behind ablation before LIMS; see stream log, not spine.
- Two SLA schemas cannot both occupy `datasets[FeedType.SLA]`. Leaf: primary SLA = BTR; STR = `companion_endpoints["str_licenses"]` (Minneapolis Off_Sale precedent). Scheduler does **not** poll companions today — spine hold must either grow companion polling or accept BTR-only ingest until then.
- Union field-map is unsafe (different id/address columns). Separate `SLA_FIELD_MAP` (BTR) and `STR_SLA_FIELD_MAP` (companion).
- Do not map `gpsx`/`gpsy` as lat/lng (Florida State Plane, not WGS84). Do not map BTR `geocoded_column` (shared SLA parser has no GeoJSON Point path; spine producer change would be needed). Address geocode is the live path.
- BTR addresses already carry `FL` so ADR-0004 will **not** append `geocode_context` on the raw string. STR street-only addresses **will** get `, Orlando, FL`.
- Geocoder `normalize_address` treats `FL` as a FLOOR unit token, so normalized BTR queries drop the state even though raw `_STATE_RE` already skipped the context suffix. Finding only — `geocoder.py` not edited.
- STR has no license-type column. Leaf maps `license_type` → `license_milestone` so rows do not inherit the producer default `"On-Premises Liquor"`.

## Files written

- `apps/api/src/spatial/cities/orlando.py`
- `apps/api/src/producers/field_maps_orlando.py`
- `apps/api/tests/unit/test_producers_orlando.py`

## Tests

```
cd apps/api && .venv/bin/pytest tests/unit/test_producers_orlando.py -q
28 passed
```

No `CityId.ORLANDO`. No spine edits.

## Spine delta (do NOT apply in this stream)

Copy-paste for the serial interlock hold:

1. `CityId.ORLANDO = "orlando"` (after `FORT_WORTH`)
2. Aliases in `_HANDWRITTEN_ALIASES`:
   - `orlando`, `orlando_fl`, `orlando fl`, `mco`, `orange_county_fl`, `orange county fl`
3. `city_registry.py` imports:
   - `from src.spatial.cities.orlando import ORLANDO_DIVISION_BBOXES, ORLANDO_DIVISIONS, ORLANDO_METRO_BBOX, ORLANDO_SUBMARKETS`
   - `from src.producers.field_maps_orlando import SLA_FIELD_MAP as ORLANDO_SLA_FIELD_MAP, STR_SLA_FIELD_MAP as ORLANDO_STR_SLA_FIELD_MAP`
4. `cities/__init__.py` export block (same four constants + `is_in_orlando_metro`)
5. `config.py`:
   - `socrata_orlando_sla_endpoint = "https://data.cityoforlando.net/resource/7388-4re5.json"`
   - `socrata_orlando_str_endpoint = "https://data.cityoforlando.net/resource/ssrj-rbua.json"`
6. `REGISTRY[CityId.ORLANDO]`:
   - name `"Orlando / Orange County"`, state `"FL"`
   - center `{"lat": 28.5383, "lng": -81.3792}`
   - job_suffix `"orlando"`
   - datasets: **only** `FeedType.SLA` (partial). Do **not** register `FeedType.STR`.
   - endpoint `settings.socrata_orlando_sla_endpoint`
   - platform `socrata`, watermark `received_date`, id_keys `["case_number"]`
   - `needs_geocode=True`, `geocode_context="Orlando, FL"`
   - `field_map=ORLANDO_SLA_FIELD_MAP`
   - `companion_endpoints={"str_licenses": settings.socrata_orlando_str_endpoint}`
   - expected_cadence_days `1`
7. `METRO_META` in `apps/api/src/serving/dashboard.py` **and** byte-synced `apps/dashboard/public/index.html`:
   - `orlando: { name: 'Orlando / Orange County' }`
8. Scheduler does not poll `companion_endpoints` today. STR ingest is a follow-on: either grow companion polling (with `ORLANDO_STR_SLA_SPEC` watermark `last_action_date` / field map `ORLANDO_STR_SLA_FIELD_MAP`) or accept BTR-only until then.

## STR-as-SLA note

`FeedType.STR` already exists in the enum and is unused (`test_feedtype_taxonomy.py`: zero cities). US-194 does **not** register it. Orlando STR licenses are SLA (Nashville residential STR precedent). The investor-buyout / occupancy reading is a **new signal family** observation only — prototype behind an ablation before LIMS (`metro-expansion-and-new-signals.md` §2). Do not invent a FeedType in this hold.

## Current step

Spine applied 2026-08-27 ~13:05 PT (orchestrator, serial hold after Honolulu).
SLA BTR primary + STR companion. `pytest -m interlock` **22 passed**. Leaf
tests **28 passed**. METRO_META + `index.html` byte-synced. Companion
polling is still a follow-on (BTR-only ingest until then).

## Next step

Linear US-194 comment + Done. No further code in this stream.
