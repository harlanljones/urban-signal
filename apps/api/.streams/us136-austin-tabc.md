# US-136 — Spine Delta: Register Austin TABC Liquor Licenses (FeedType.SLA)

**Ticket:** US-136
**Leaf modules (done, tested):** `src/spatial/cities/austin.py::AUSTIN_TABC_SLA_SPEC`,
`src/producers/field_maps_austin_tabc.py`, `tests/unit/test_producers_austin_tabc.py`
**Geocode path:** ADR 0004 (Postgres-replay geocoder) — `needs_geocode: True` + `geocode_context`
**Endpoint verification:** VERIFIED against the live Socrata resource on
2026-08-26; see §(d).

**Status:** Complete. The registry and tests have been applied; the original
paste-ready delta below is retained as an audit trail and is superseded by the
current source.

---

## (a) REGISTRY block to add — `src/spatial/city_registry.py`

Austin is currently a THREE-feed partial city (PERMITS + COMPLAINTS_311). This adds
FeedType.SLA. The leaf `AUSTIN_TABC_SLA_SPEC` in `cities/austin.py` is the source
of the field_map; paste the block below into `REGISTRY[CityId.AUSTIN].datasets`.

Also delete the stale comment that says "FeedType.SLA and FeedType.DEEDS stay
deliberately absent" (lines ~1564-1571 of city_registry.py) — SLA is now present.

```python
            # US-136: TABC statewide liquor-license feed (data.texas.gov
            # `7hf9-qc9f` "TABC License Information"). Address-only — no lat/lng
            # columns — so needs_geocode flips the coordinate requirement and the
            # ADR 0004 geocoder resolves coordinates at parse time.
            # watermark = current_issued_date, the published issuance cursor.
            FeedType.SLA: DatasetSpec(
                endpoint=settings.socrata_austin_tabc_endpoint,
                platform="socrata",
                watermark_col="current_issued_date",
                id_keys=["license_id", "master_file_id"],
                topic=settings.topic_sla,
                interval_seconds=600.0,
                producer_key="sla",
                extra={
                    "expected_cadence_days": 7,
                    "needs_geocode": True,
                    "geocode_context": "TX",
                    "where": "county = 'Travis'",
                    "field_map": {
                        "license_id": ["license_id"],
                        "license_type": ["license_type"],
                        "effective_date": ["current_issued_date"],
                        "expiration_date": ["expiration_date"],
                        "premises_name": ["owner"],
                        "dba": ["trade_name"],
                        "address_street": ["address"],
                        "status": ["license_status"],
                    },
                },
            ),
```

> Note: the orchestrator may instead import the ready-made `AUSTIN_TABC_SLA_SPEC`
> dict and rebuild the `DatasetSpec` from it; its `extra.field_map` is
> `_TABC_FIELD_MAPS["sla"]` (identical to the map above).

---

## (b) config.py setting to add — `src/config.py`

Add the Socrata endpoint setting next to the other `socrata_austin_*` settings:

```python
    # US-136: TABC statewide liquor-license feed (data.texas.gov 7hf9-qc9f).
    socrata_austin_tabc_endpoint: str = "https://data.texas.gov/resource/7hf9-qc9f.json"
```

---

## (c) Dashboard METRO_META note

**No dashboard change needed.** Austin already has a metro chip and `?city=austin`
deep link. The SLA feed attaches to the existing Austin registration; no new
METRO_META entry is required (it is not a new metro). Verify after the spine
interlock that the existing Austin chip still renders with the SLA layer present.

---

## (d) ENDPOINT VERIFICATION STATUS: VERIFIED

The live dataset id `7hf9-qc9f` ("TABC License Information") was confirmed on
2026-08-26 with the expected schema and no coordinate columns:

- [x] Hit `https://data.texas.gov/resource/7hf9-qc9f.json?$limit=1` and confirm
      a 200 with the expected columns (`license_id`, `license_type`,
      `current_issued_date`, `status_change_date`, `expiration_date`, `owner`,
      `trade_name`, `address`, `license_status`, ...).
- [x] Confirm `current_issued_date` is the published issuance cursor.
- [x] Confirm no `latitude`/`longitude` columns (geocode-required case).
- [ ] If the id has rotated, update BOTH this delta and
      `field_maps_austin_tabc.py`/`austin.py` to the new id.

**Researched dataset id:** `7hf9-qc9f` (data.texas.gov — "TABC License Information").
The legacy cross-reference `kguh-7q9z` ("TABCLicenses", 2021 AIMS migration
cross-walk with padded addresses and no authoritative status/issue dates) is
deliberately NOT a registration target.
