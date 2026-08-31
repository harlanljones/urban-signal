# Stream log — city-laredo — 2026-08-31

## Claim

- **Stream id:** city-laredo
- **Linear:** US-263 (Laredo, TX — South Central, pop ~320K, data.openlaredo.com OpenGov/CKAN, Fit High)
- **Leaf files I created/edited (leaf-only, no spine):**
  - `apps/api/src/spatial/cities/laredo.py`
  - `apps/api/src/producers/field_maps_laredo.py`
  - `apps/api/tests/unit/test_producers_laredo.py`
  - `docs/research/probe-laredo.md`
- **Spine files I expect to need (NOT edited in this leaf hold — delta spec below):**
  - `apps/api/src/spatial/city_registry.py` — CityId, ALIASES, REGISTRY
  - `apps/api/src/spatial/cities/__init__.py` — gather (no hand edit needed, leaf auto-picked)
  - `apps/api/src/config.py` — settings entry for Laredo CKAN endpoint
  - `apps/api/src/serving/dashboard.py` (METRO_META) + `apps/dashboard/public/index.html` (byte-sync via `python scripts/export_dashboard.py`)
  - `apps/product/public/facts.json` + `apps/product/public/cities/laredo.json` (via `bun run facts:export`)
  - `apps/api/src/export/snapshot_builder.py` / grid manifest wiring per interlock

## Intent

Onboard Laredo, TX as South Central metro. Live probe (2026-08-30 re-verified 2026-08-31) finds **Tier 2 permits** on CKAN OpenGov `data.openlaredo.com` (resource `61972510-7b8c-488a-9e88-b73b0112f496`, 91,198 rows, watermark `PERMIT ISS. DATE` = 2026-07-02T00:00:00, address-only `STREET NBR` + `STREET` 100%, needs_geocode=true). 311/SLA/deeds are Tier 3 (stale or absent). Register one feed (permits) with state super-feed SLA companion (TX TDLR/TREC/TABC Webb 48479) when spine hold lands. Keep leaf strictly additive.

## Live probe summary (2026-08-31 UTC re-probe, matches 2026-08-30 doc)

- **Socrata discovery:** `api.us.socrata.com/api/catalog/v1?domains=data.openlaredo.com` → `Domain not found` (not Socrata).
- **CKAN portal:** `data.openlaredo.com` CKAN 2.9.11 OpenGov, `package_search?rows=100` count 146, `package_search?q=permit` 6 hits; datastore_active true on live resource.
- **ArcGIS Hub:** `open-laredo.opendata.arcgis.com` DCAT collections 54 items; `q=permit` → 1 (OD 2014 Total Building Permits snapshot, FeatureServer `services3.arcgis.com/h9QEFLHkUI1SIRs7/.../OD_2014_Total_Building_Permits/FeatureServer/5` lastEditDate 1556720710918 = 2019-05-01, stale). `laredo-tx.opendata.arcgis.com` → 401 Unauthorized (non-canonical).
- **AGOL org sweep:** `services3.arcgis.com/h9QEFLHkUI1SIRs7/arcgis/rest/services` — ADDRESS_POINTS, traffic counts, flood zones, etc.; no permits/311/sales layer; Hub is the org surface.
- **ArcGIS Server rest/services:** no city `gis.laredo.tx.us` open directory beyond Hub hosted services; `cityoflaredo.com` / `lare-egov.aspgov.com/Click2GovBP` Akamai 403, intake UI only (CKAN is the bulk survivor).
- **Row-level family verification (CKAN `datastore_search_sql`):**
  - PERMITS canonical `61972510-7b8c-488a-9e88-b73b0112f496` ORDER BY "PERMIT ISS. DATE" DESC LIMIT 3 → 2026-07-02T00:00:00 (7036 CASTANO DR, 215 CANARIA DR, 19891 WEST PEAK RD); total 91,198; fields include timestamp PERMIT ISS. DATE + STREET NBR/STREET/VALUATION/Permit Group Type; WHERE >= '2026-07-31' 0, >= '2026-07-01' 86, >= '2026-06-02' 1,650, >= '2026-01-01' 9,481; address-complete 91,198/91,198 (100%) → Tier 2 address-geocodable.
  - 311 FY23-24 `af1a96fd-d5bb-47f9-b71c-cd937aa81c59` 37,468 rows ORDER BY "Close Date" DESC → 2024-06-26 00:00:00.000, fields no lat/lng no address (Assigned Dept, Create/Close Date, Request Type, Council District only) → Tier 3 stale ~430 days. 2014-2018 slices have lat/lng but newest 2018, 7y stale.
  - SLA `package_search?q=business license` 1 bid-tab PDF only, no business-license feed; Hub no license registry → Tier 3 (use TX state TDLR 7358-krk7 etc Webb 48479).
  - Deeds `q=deed` 0, `q=sale` 0 → Tier 3.

## Verdict

**REGISTER — Tier 2 permits (marginal freshness, 58 days behind at 2026-08-30, 0 in 30d / 86 in July / 1,650 in 60d, monthly bulk replace, actively maintained 2026-01-08 creation, metadata_modified 2026-07-22).** All other families Tier 3. Leaf build authorized.

## Leaf artifacts (this hold)

- `apps/api/src/spatial/cities/laredo.py` — metro bbox 27.40/27.75/-99.65/-99.30, center 27.5306,-99.4803 (Santa Maria & Matamoros), 2 divisions (LAREDO_CORE 27.42-27.58/-99.60--99.38, LAREDO_NORTH 27.58-27.72/-99.62--99.32) strict subsets, 6 submarkets (Downtown & San Agustin, Heights & Del Mar, Zacate Creek & Washington, South Laredo & Santa Rita, Mines Road Corridor, North Laredo & Winfield) with containment/pinned watermark 2026-07-02T00:00:00, REGISTRATION.
- `apps/api/src/producers/field_maps_laredo.py` — PERMITS_FIELD_MAP over sanitized CKAN columns (dots/spaces → "_" via normalize_laredo_row), STREET NBR+STREET address concat "Laredo, TX", needs_geocode=true, DROPPED_PII CONTRACTOR NAME, GEOCODE_CONTEXT Laredo, TX.
- `apps/api/tests/unit/test_producers_laredo.py` — 43 tests (spatial bbox/division containment, feed spec, field-map first_mapped with fixtures 88449/88450/89084 byte-verbatim 2026-08-30, CKAN contract/staleness flag pinned). **43/43 green** leaf-only (no spine registration needed).
- `docs/research/probe-laredo.md` — Wave 3 Phase-0 probe document (platform table, headline tier table, per-family findings, hosts probed/rejected, recommendation + spine delta), structure mirrors `probe-little_rock.md`.

## Spine delta (for orchestrator's hold — NOT applied here)

```python
# apps/api/src/config.py
# Add one settings entry (mirrors ckan_san_antonio pattern):
# ckan_laredo_permits_endpoint: str = "https://data.openlaredo.com/api/3/action/datastore_search?resource_id=61972510-7b8c-488a-9e88-b73b0112f496"

# apps/api/src/spatial/city_registry.py
from src.spatial.cities.laredo import (
    LAREDO_CENTER,
    LAREDO_DIVISION_BBOXES,
    LAREDO_DIVISIONS,
    LAREDO_METRO_BBOX,
    LAREDO_SUBMARKETS,
)
from src.producers.field_maps_laredo import PERMITS_FIELD_MAP as LAREDO_PERMITS_FIELD_MAP

class CityId(str, Enum):
    # ...
    LAREDO = "laredo"

_HANDWRITTEN_ALIASES: Dict[str, CityId] = {
    # ...
    # Laredo, TX
    "laredo": CityId.LAREDO,
    "laredo_tx": CityId.LAREDO,
    "laredo-tx": CityId.LAREDO,
    "laredo tx": CityId.LAREDO,
}

_HANDWRITTEN_REGISTRY: Dict[CityId, CityRegistration] = {
    # ...
    CityId.LAREDO: CityRegistration(
        city_id=CityId.LAREDO,
        name="Laredo",
        state="TX",
        center=LAREDO_CENTER,  # {"lat": 27.5306, "lng": -99.4803}
        metro_bbox=LAREDO_METRO_BBOX,
        division_bboxes=LAREDO_DIVISION_BBOXES,
        submarkets=LAREDO_SUBMARKETS,
        divisions=LAREDO_DIVISIONS,
        job_suffix="laredo",
        # US-263: CKAN OpenGov permits — 91k rows, 2022-present, monthly bulk replace,
        # watermark PERMIT ISS. DATE newest 2026-07-02T00:00:00 (58d at probe, 60d window healthy).
        # Address-only STREET NBR+STREET, ADR-0004 geocode_cache Census/Nominatim, coord_source flag.
        # 311/SLA/deeds Tier 3; state super-feed SLA companion (TX TDLR/TREC/TABC Webb 48479) optional second feed.
        # CKAN dotted keys require normalize_laredo_row before first_mapped (see leaf field_maps_laredo.normalize_laredo_row).
        datasets={
            FeedType.PERMITS: DatasetSpec(
                endpoint="https://data.openlaredo.com/api/3/action/datastore_search?resource_id=61972510-7b8c-488a-9e88-b73b0112f496",
                # alt flat CSV: "https://data.openlaredo.com/dataset/9f3751a0-98ca-4c32-85a3-521dac8eb12b/resource/61972510-7b8c-488a-9e88-b73b0112f496/download/bpod1e.csv"
                platform="ckan",
                watermark_col="PERMIT ISS. DATE",
                id_keys=["APP NBR", "APP_NBR", "APP YR", "APP_YR", "_id"],
                topic=settings.topic_permits,
                interval_seconds=3600.0,  # monthly bulk; hourly poll is cheap, 60d tolerance covers staleness flag
                producer_key="permits",
                expected_cadence_days=30,
                needs_geocode=True,
                geocode_context="Laredo, TX",
                # ckan datastore_search_sql uses ORDER BY "PERMIT ISS. DATE" DESC; SOCRATA-style where/order_by still applies via CKAN client
                field_map=LAREDO_PERMITS_FIELD_MAP,
                # if adding state companion in same hold:
                # FeedType.SLA: DatasetSpec(**tx_tdlr_spec("Webb")) or tx_trec_broker_spec("Webb") / socrata_tabc filtered to Webb 48479
            ),
        },
    ),
}
# Note: apps/api/src/spatial/cities/__init__.py needs no hand edit — derived gather picks up laredo.py.
# Dashboard wiring in same spine hold (city-registration rule):
#   apps/api/src/serving/dashboard.py METRO_META["laredo"] = {"name": "Laredo, TX", "state": "TX", "lat": 27.5306, "lng": -99.4803, "county": "Webb", "pop": 320000, "region": "South Central"}
#   then python scripts/export_dashboard.py to byte-sync apps/dashboard/public/index.html
#   and product facts: bun run facts:export (apps/product) — interlock gate covers wiring.
```

## Verification

- Leaf tests: `python -m pytest apps/api/tests/unit/test_producers_laredo.py -v` → **43 passed** (30+ required; includes 16 spatial, 5 feed-spec, 15 field-map, 7 CKAN contract).
- No spine edits in this hold (`git status` clean on spine manifest paths).
- No Linear state change, no git commit per leaf-only instruction.

## Risk / re-probe trigger

Permits is marginal Tier 2 (monthly batch, 30d zero at probe). If next CKAN replace does not push watermark past 2026-07-31 at 60-day re-probe, soft-downgrade to Tier 3 and run Laredo as state-feed-only (SNAP/TDLR) metro per Waco precedent. The staleness contract is pinned in both the probe doc and `test_staleness_flag_is_pinned`.

## Current step

Leaf hold complete. Awaiting orchestrator spine hold to wire CityId.laredo + ALIASES + REGISTRY + config + METRO_META byte-sync + product facts. Then `pytest -m interlock` from `apps/api` must pass (24 tests, dashboard + snapshot + grid-tile coverage).

## Next step

Orchestrator: open spine hold, apply delta above additively, run `python scripts/verify_cicd_preflight.py` (or at minimum `pytest -m interlock` + `bun run facts:export` + `python scripts/export_dashboard.py`), then push/PR.
