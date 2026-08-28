# wave5 — US-352 Syracuse, NY (LEAF)

**Claimed:** 2026-08-27 by LEAF-IMPLEMENTATION agent (US-352).
**Scope:** `apps/api/src/spatial/cities/syracuse.py` (new),
`apps/api/src/producers/field_maps_syracuse.py` (only if needed),
`apps/api/tests/unit/test_producers_syracuse.py` (new),
this file, + one dispatch-log outcome row. Spine untouched.
**Basis:** `docs/research/probe-syracuse.md` (SLA T1: Rental Registry,
`services6.arcgis.com/bdPqSfflsdgFRVVM .../Syracuse_Rental_Registry/FeatureServer/0`).
Watermark `RR_app_received` = 2026-08-26 at probe; native lat/lng 500/500.
Permits frozen 2025-08-16 (T3), 311/deeds absent (T3) — SLA only.

## Status: done

## Outcome (2026-08-27)

- `apps/api/src/spatial/cities/syracuse.py` — SYRACUSE_* leaf: metro bbox
  (42.99–43.13 / -76.24–-76.05), 6 divisions / 8 submarkets (Downtown,
  Armory Square, University Area, Westcott, Eastwood, Strathmore,
  North Side, Outer Comstock), `is_in_syracuse_metro`, FEED_SPECS (sla
  only), `get_syracuse_dataset`, `REGISTRATION`, canonical `__all__`.
- `apps/api/src/producers/field_maps_syracuse.py` — SYRACUSE_SLA_FIELD_MAP
  (SBL, RR_app_received, valid_until, RRisValid, PropertyAddress,
  capitalized Latitude/Longitude; PII RR_contact_name/pc_owner dropped).
- `apps/api/tests/unit/test_producers_syracuse.py` — 28 tests; 4 live
  fixtures captured byte-verbatim 2026-08-27 (2 fresh apps incl. the
  watermark row ObjectId 1424 @ 2026-08-26; 2 granted cards). Spine-stable:
  no borough-division or geocode-call-count assertions.

## Gates

- `pytest tests/unit/test_producers_syracuse.py`: 28 passed.
- `pytest -k syracuse`: 30 passed.
- `pytest -m interlock`: 24/24 passed (gate grew 22→24 from in-flight
  spine edits by siblings; zero failures).
- Full suite: 1848 passed / 3 skipped / **1 failed = the spine-owned
  leaf-count pin** (`test_city_leaf_naming.py::test_all_expected_leaf_modules_present`,
  asserts `len(_LEAF_MODULES) == 62`; syracuse.py makes 63 — orchestrator
  bumps to 63 with the spine hold).

## THE SPINE DELTA (for the orchestrator hold)

- **CityId enum:** add `SYRACUSE = "syracuse"` (leaf passes city_id strings;
  no CityId import in the leaf).
- **Aliases:** `_HANDWRITTEN_ALIASES` += "syracuse".
- **CityRegistration:** new `CityRegistration(city_id=CityId.SYRACUSE,
  name="Syracuse", state="NY", center={"lat": 43.0481, "lng": -76.1474},
  metro_bbox=SYRACUSE_METRO_BBOX, division_bboxes=SYRACUSE_DIVISION_BBOXES,
  submarkets=SYRACUSE_SUBMARKETS, divisions=SYRACUSE_DIVISIONS,
  feeds={"sla": ...})` importing from `src.spatial.cities.syracuse`.
- **DatasetSpec (SLA):** endpoint
  `https://services6.arcgis.com/bdPqSfflsdgFRVVM/arcgis/rest/services/Syracuse_Rental_Registry/FeatureServer/0`;
  config settings names: `syracuse_sla_endpoint` (that URL) — no other
  settings needed (single feed, no companions);
  platform="arcgis"; watermark_col="RR_app_received"; id_keys=["SBL"];
  topic=settings.topic_sla; interval_seconds=600.0; producer_key="sla";
  ingestion_mode="incremental" (watermark is event-driven; NOT snapshot);
  expected_cadence_days=1; needs_geocode=False (native WGS84
  Latitude/Longitude 500/500 — no ADR 0004); oid_field="ObjectId";
  max_record_count=1000; order_by="RR_app_received DESC";
  field_map=SYRACUSE_SLA_FIELD_MAP (copy verbatim from
  field_maps_syracuse.py so `resolve_field_map` post-spine matches the
  tests' patched map).
- **cities/__init__.py:** export SYRACUSE_* block (mirrors HENDERSON_*).
- **serving/dashboard.py METRO_META:** add "Syracuse, NY" metro chip +
  `?city=syracuse` deep link; then dashboard wiring gate
  (TestDashboardWiring/TestSnapshotWiring) + byte-synced
  apps/dashboard/public/index.html regen + snapshot/res-5 coverage —
  registration is not done until the city shows on the map (AGENTS.md
  city-registration rule).
- **test_city_leaf_naming.py:** bump leaf-count pin 62 → 63.
- **snap_sla_spec:** Syracuse HAS an SLA feed — no SLA-less exemption needed.
- **Do NOT register:** Permit_Requests (frozen 2025-08-16, weak geocode),
  311 (absent), deeds (assessment-only parcel maps).
