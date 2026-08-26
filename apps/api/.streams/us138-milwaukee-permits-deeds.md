# US-138 Spine Delta — Milwaukee PERMITS + DEEDS

**Ticket:** US-138 (Register Milwaukee permits + deeds)
**Leaf status:** COMPLETE (registered and verified)
**Spine owner:** interlock orchestrator
**City:** `CityId.MILWAUKEE` (SLA + permits + deeds)

> The approved implementation uses the verified `data.milwaukee.gov` CKAN CSV
> resources; the provisional ArcGIS paths below are superseded.

---

## Policy question — resolved

Milwaukee was deliberately SLA-only under US-87. The user approved adding
PERMITS + DEEDS on 2026-08-26, including ADR-0004 address geocoding and ADR-0005
typed text watermarks.

**The orchestrator MUST confirm with the user whether adding PERMITS + DEEDS
(relying on the ADR-0004 geocoder for address-only rows, and the ADR-0005 typed
text watermark for yearly-archive deed dates) is actually desired before
lifting these into `city_registry.REGISTRY`.** This is a scope change from a
deliberate prior decision, not a routine leaf addition. Do not apply if the
user declines.

---

## (a) REGISTRY block — add to `CityId.MILWAUKEE.datasets` in `apps/api/src/spatial/city_registry.py`

```python
            FeedType.PERMITS: DatasetSpec(
                endpoint=settings.arcgis_milwaukee_permits_url,
                platform="arcgis",
                watermark_col="ISSUE_DATE",
                id_keys=["PERMIT_NO", "OBJECTID"],
                topic=settings.topic_permits,
                interval_seconds=300.0,
                producer_key="permits",
                extra={
                    "expected_cadence_days": 7,
                    "oid_field": "OBJECTID",
                    "max_record_count": 1000,
                    # ADR-0004: permits arrive address-only; geocode at parse time.
                    "needs_geocode": True,
                    "geocode_context": "Milwaukee, WI",
                    "scope": "Milwaukee building permits (address-only coords; geocoded per ADR-0004)",
                    "field_map": {
                        "job_id": ["PERMIT_NO", "PERMIT_NUMBER"],
                        "address_street": ["ADDRESS", "SITE_ADDRESS", "PROP_ADDRESS"],
                        "issuance_date": ["ISSUE_DATE"],
                        "filing_date": ["APPLICATION_DATE", "PERMIT_APPLICATION_DATE"],
                        "job_type": ["PERMIT_TYPE", "WORK_TYPE", "CONSTRUCTION_TYPE"],
                        "cost": ["ESTIMATED_COST", "TOTAL_PROJECT_COST", "EST_COST"],
                        "borough": ["NEIGHBORHOOD", "NBHD"],
                        "zipcode": ["ZIP_CODE", "ZIP"],
                    },
                },
            ),
            FeedType.DEEDS: DatasetSpec(
                endpoint=settings.arcgis_milwaukee_deeds_url,
                platform="arcgis",
                watermark_col="RECORDING_DATE",
                id_keys=["DOCUMENT_NO", "OBJECTID"],
                topic=settings.topic_deeds,
                interval_seconds=600.0,
                producer_key="deeds",
                extra={
                    "expected_cadence_days": 30,
                    "oid_field": "OBJECTID",
                    "max_record_count": 1000,
                    # ADR-0005: yearly-archive text dates — declare the watermark
                    # type so the scheduler tracks recency from the raw string and
                    # can exclude any sentinel spellings discovered live.
                    "watermark_type": "text",
                    "watermark_format": "%Y-%m-%d",
                    "watermark_exclude": [],  # append discovered sentinels live (ADR-0005)
                    "scope": "Milwaukee County recorded deeds / property sales (text watermark per ADR-0005)",
                    "field_map": {
                        "doc_id": ["DOCUMENT_NO", "DOC_NO", "INSTRUMENT_NO"],
                        "bbl": ["PARCEL_NO", "PIN", "TAXKEY"],
                        "document_amount": ["SALE_PRICE", "CONSIDERATION", "TOTAL_CONSIDERATION"],
                        "recorded_date": ["RECORDING_DATE", "REC_DATE", "DATE_RECORDED"],
                        "party1_grantor": ["GRANTOR", "SELLER", "FROM_PARTY"],
                        "party2_grantee": ["GRANTEE", "BUYER", "TO_PARTY"],
                        "borough": ["NEIGHBORHOOD", "NBHD"],
                    },
                },
            ),
```

> Note: the leaf module `src/spatial/cities/milwaukee.py` carries the identical
> data as `MILWAUKEE_PERMITS_SPEC` / `MILWAUKEE_DEEDS_SPEC` (plain dicts, not
> `DatasetSpec`, to avoid a circular import). The endpoint there is hardcoded;
> the spine **must** bind `endpoint=settings.arcgis_milwaukee_*` instead. The
> field maps above are the canonical source of truth.

---

## (b) config.py setting lines to add — in `apps/api/src/config.py` (Settings class)

```python
    # Milwaukee, WI (ArcGIS): building permits + recorded deeds / property sales.
    # Host milwaukeemaps.milwaukee.gov is an ANSI-date-literal server (US-87):
    # the shared watermark_comparison renders the incremental where as
    # `col >= date 'YYYY-MM-DD'`. Address-only coords on PERMITS/DEEDS are
    # geocoded at parse time via ADR-0004; DEEDS declares an ADR-0005 typed text
    # watermark (RECORDING_DATE, "%Y-%m-%d"). Endpoint service-layer IDs are
    # UNVERIFIED live — see ENDPOINT VERIFICATION STATUS below.
    arcgis_milwaukee_permits_url: str = Field(
        default=(
            "https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/"
            "permits/building/MapServer/0"
        ),
        description="Milwaukee building permits MapServer layer URL",
    )
    arcgis_milwaukee_deeds_url: str = Field(
        default=(
            "https://milwaukeemaps.milwaukee.gov/arcgis/rest/services/"
            "assessor/property_sales/MapServer/0"
        ),
        description="Milwaukee County recorded deeds / property sales MapServer layer URL",
    )
```

---

## (c) Geocode dependency (address-only → ADR-0004)

- **PERMITS** ships `extra["needs_geocode"]: True` and
  `extra["geocode_context"]: "Milwaukee, WI"`. Rows arrive with an address
  string only (no `latitude`/`longitude`). Enrichment invokes
  `src/spatial/geocoder.py` (the one sanctioned spine touch in
  `SpatialEnrichmentWorker.process_record`) only when an event has an address
  but no coordinate, per ADR-0004. Coordinate resolution is frozen in the
  Postgres replay cache (`geocode_cache`), so backfill parity (gate G6) is
  byte-stable. Below `settings.geocode_confidence_floor` (default 0.9) a
  geocoded coordinate resolves to `None` → null H3 rather than a wrong cell.
- **DEEDS** also arrives address-only (PARCEL/address); if the property-sales
  layer exposes no geometry, it likewise requires `needs_geocode` at parse time.
  The current leaf spec does NOT set `needs_geocode` on DEEDS — **the orchestrator
  must confirm DEEDS geometry at verification and add `"needs_geocode": True` to
  the DEEDS `extra` if the layer is address/PARCEL-only** (consistent with the
  PERMITS handling and ADR-0004).
- **DEEDS watermark (ADR-0005):** `watermark_type: "text"`,
  `watermark_format: "%Y-%m-%d"`, `watermark_exclude: []` — yearly-archive text
  dates; any discovered sentinel spellings are appended to `watermark_exclude`
  live (degradation, not corruption).

---

## (d) POLICY QUESTION FLAG (repeated for the orchestrator checklist)

- [ ] User confirmed: add PERMITS + DEEDS to Milwaukee despite the deliberate
      SLA-only decision in US-87, relying on ADR-0004 geocoding.
- [ ] User confirmed: DEEDS address-only handling (add `needs_geocode` if the
      layer lacks geometry) is acceptable.

**Do NOT apply the REGISTRY/config delta until both are checked.**

---

## (e) ENDPOINT VERIFICATION STATUS: UNVERIFIED (no network)

The host `milwaukeemaps.milwaukee.gov` is confirmed as Milwaukee's ArcGIS
server (same host as the registered `arcgis_milwaukee_licenses_url`, US-87).
The **service-layer IDs are researched, not live-confirmed**:

| Feed   | Proposed endpoint (service / layer)                                  | Status  |
|--------|----------------------------------------------------------------------|---------|
| PERMITS| `permits/building/MapServer/0`                                       | UNVERIFIED — researched service path; confirm layer 0 exists and exposes `ISSUE_DATE` / `PERMIT_NO` |
| DEEDS  | `assessor/property_sales/MapServer/0`                                | UNVERIFIED — researched service path; confirm layer 0 exposes `RECORDING_DATE` / `DOCUMENT_NO` and decide geometry vs `needs_geocode` |

Before the registry edit lands, a human (or a network-enabled verification
pass) must open each URL's `?f=json` and confirm:
1. the layer exists and is queryable,
2. the `watermark_col` and `id_keys` fields are present in the layer schema,
3. whether the layer carries point geometry (→ no geocode) or is address/PARCEL-only
   (→ set `needs_geocode` on DEEDS).

The default URLs above are the researched best-guess service paths; treat the
layer IDs as provisional until confirmed.

---

## Source references (leaf, already in place — do not re-edit)

- `apps/api/src/spatial/cities/milwaukee.py` — `MILWAUKEE_PERMITS_SPEC`,
  `MILWAUKEE_DEEDS_SPEC`, `MILWAUKEE_PERMITS_FIELD_MAP`,
  `MILWAUKEE_DEEDS_FIELD_MAP`.
- `apps/api/src/producers/field_maps_milwaukee_permits_deeds.py` — `FIELD_MAP`
  keyed by `FeedType.PERMITS` / `FeedType.DEEDS`.
- `apps/api/tests/unit/test_producers_milwaukee_permits_deeds.py` — contract
  tests (10 passing).
- `docs/adr/0004-address-geocoding.md` — address → coordinate via replay cache.
- `docs/adr/0005-typed-text-watermarks.md` — typed text watermark for DEEDS.
