# US-137 — Spine Delta: Register Boston Licensing Board feed

**Implementation record.** The approved Path A spine change is complete. The
historical paste-ready draft below is retained for traceability; its ADR-0004
address-geocoding variant is superseded by the live EPSG:2249 transform.

**Status:** Boston Licensing Board is registered; State Plane transform and
focused tests pass.

---

## (a) REGISTRY block — add SLA feed to `CityId.BOSTON`

Paste into the `datasets={...}` dict of `CityId.BOSTON` (currently holds
`FeedType.PERMITS` and `FeedType.COMPLAINTS_311` at city_registry.py:1752).

```python
            # US-137: Boston Licensing Board register (CKAN 04dc653b-...).
            # Its only coordinate columns, gpsx/gpsy, are Massachusetts State
            # Plane METERS (EPSG:26986) — NOT WGS84 degrees — so mapping them to
            # latitude/longitude would inject meter-scale garbage. Per ADR-0004
            # the feed is registered ADDRESS-ONLY: gpsx/gpsy are intentionally
            # absent from the field map and rows geocode from business_address.
            FeedType.SLA: DatasetSpec(
                endpoint=settings.ckan_boston_licenses_endpoint,
                platform="ckan",
                watermark_col="licensetype_effective_date",
                id_keys=["license_id", "_id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                extra={
                    "expected_cadence_days": 7,
                    # needs_geocode is honored by SpatialEnrichmentWorker.process_record
                    # (ADR-0004): no lat/lon -> geocode from address_street.
                    "needs_geocode": True,
                    "geocode_context": "Boston, MA",
                    "field_map": BOSTON_LICENSING_FIELD_MAP,
                },
            ),
```

Add the import near the other `field_maps_*` imports (city_registry.py:13-19):

```python
from src.producers.field_maps_boston_licensing import FIELD_MAP as BOSTON_LICENSING_FIELD_MAP
```

> `FeedType.LICENSING` does NOT exist — the enum is `{PERMITS, COMPLAINTS_311,
> SLA}` (city_registry.py:377-379). Licenses/SLA feeds conventionally use
> `FeedType.SLA`, matching the leaf feed's `feed_type: "sla"`.

---

## (b) config.py setting line

The setting ALREADY EXISTS (config.py:370), so the orchestrator must NOT
duplicate it:

```python
    ckan_boston_licenses_endpoint: str = Field(
        default="ckan://data.boston.gov/04dc653b-1789-4374-9669-b07df7233344",
        ...
    )
```

(No new line required — endpoint resolves to `settings.ckan_boston_licenses_endpoint`.)

---

## (c) REQUIRED geocode / CRS-transform step (MUST be wired before registration)

**There is NO literal EPSG:26986 → WGS84 coordinate transform.** The source has
no WGS84 columns, so a coordinate reprojection is impossible. ADR-0004 resolves
the feed via **address geocoding**, and the State-Plane columns are dropped:

1. **Do NOT map gpsx/gpsy to latitude/longitude.** The leaf `FIELD_MAP`
   deliberately omits `latitude`/`longitude` keys and omits `gpsx`/`gpsy`
   entirely (verified by `test_feed_spec_is_address_only_ckan_resource`).
2. **Geocode from `address_street` (→ `business_address`)** at parse time via
   `SpatialEnrichmentWorker.process_record` → `geocode_row_if_declared`
   (ADR-0004). The worker fires only when a normalized event carries an address
   but no coordinate, so address-only rows resolve through the Postgres
   replay cache.
3. **Guard (interlock invariant):** any spine change that adds `gpsx`/`gpsy`
   to a `latitude`/`longitude` mapping for Boston SLA MUST be rejected — those
   values are meters (≈780k E, 2.95M N), not degrees, and would fail G5 by
   construction (~99.6% of rows). This is exactly why the feed was historically
   excluded.
4. The `extra` block carries `needs_geocode: True` + `geocode_context:
   "Boston, MA"` so the worker knows to geocode; downstream H3 indexing and G5
   pass once the address resolves (ADR-0004 confidence floor 0.9).

---

## (d) ENDPOINT VERIFICATION STATUS: UNVERIFIED (no network)

- Researched dataset id: **`04dc653b-1789-4374-9669-b07df7233344`** (Boston
  Licensing Board business-license register on data.boston.gov / CKAN).
- Live confirmation of the resource schema, the exact column spellings in
  `FIELD_MAP`, and that it is currently publishing is **REQUIRED before the
  spine hold is released**. The leaf column spellings are PROPOSED (pinned by
  the unit test) and mirror the Philadelphia field-map precedent.
- Until a live probe confirms the CKAN resource, the registration is
  conditional on endpoint verification; do not flip the orchestrator gate green
  on the basis of this delta alone.

---

## Notes / gap flagged for orchestrator

- The leaf `BOSTON_LICENSING_BOARD_FEED` declares `needs_geocode: True` and
  `geocode_context` but does **NOT** carry an explicit `source_crs:
  "EPSG:26986"` key. This is intentional: ADR-0004 geocodes from the ADDRESS
  string, so the State-Plane CRS is never interpreted — it is simply dropped.
  If a future requirement wants a true 26986→WGS84 reprojection instead of
  address geocoding, that needs a new ADR (out of scope for US-137).
- The Boston PERMITS feed (city_registry.py:1770-1771) DOES map `gpsx`/`gpsy`
  to longitude/latitude — but those are WGS84 degrees in that dataset. Do not
  conflate the two; the Licensing Board feed's same-named columns are meters.
