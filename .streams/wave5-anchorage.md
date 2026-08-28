# wave5-anchorage — US-330 Anchorage, AK (leaf implementation)

**Status: IN PROGRESS** — 2026-08-28, LEAF-IMPLEMENTATION agent.

## Scope (leaf contract)

- `apps/api/src/spatial/cities/anchorage.py` (new)
- `apps/api/src/producers/field_maps_anchorage.py` (new, if needed)
- `apps/api/tests/unit/test_producers_anchorage.py` (new)
- `.streams/wave5-anchorage.md` + one dispatch-log outcome row

**Forbidden (spine-held):** `city_registry.py`, `config.py`,
`serving/dashboard.py`, `cities/__init__.py`, existing test files,
`apps/product/**`. No git commit.

## Claim

- **Stream id:** wave5-anchorage
- **Leaf files I will create/edit:** the four paths above
- **Spine files I expect to need (orchestrator applies later):**
  `city_registry.py` (CityId.ANCHORAGE + aliases + CityRegistration with
  DEEDS DatasetSpec), `config.py` (`arcgis_anchorage_deeds_url` Field),
  `cities/__init__.py` re-exports, dashboard `METRO_META` "Anchorage, AK"
  + static index.html copy, `test_city_leaf_naming.py` count pin.

## Intent

DEEDS-only Tier-1 metro (per `docs/research/probe-anchorage.md`): assessor
`PropertyInformation_Hosted/FeatureServer/0` on
`services2.arcgis.com/Ce3DhLRthdwbHlfF`, watermark `Deed_Date` (max
non-future 2026-08-25 at probe stamp; daily `PUBDATE` republish; last-deed-
per-parcel snapshot grain; 5 future sentinels excluded from the high
watermark). Leaf ships `ANCHORAGE_*` constants, DEEDS spec + field map,
producer-parse tests through the real `DeedsACRISProducer` path with the
field map patched in (Durham precedent), geometry self-consistency checks,
and live re-probe fixtures captured byte-verbatim.

## Decisions

- 2026-08-28 — Ticket's reference analog `git show 2a70e39:...rochester.py`
  does not exist at that commit (rochester is a parallel wave-5 leaf,
  uncommitted). Closest committed deeds-led arcgis analog used instead:
  `durham.py` (+ `field_maps_durham.py`, test patching pattern).
- `document_amount` left UNMAPPED — the assessor property file carries no
  sale-price/consideration column; assessed values must not masquerade as
  deed amounts. Parses to 0.0 by design (NOLA sold-properties precedent).
- `party2_grantee: ["Owner_Name"]` (NOT party1): the file is last-deed-per-
  parcel, so the current owner is the last recorded deed's GRANTEE. Differs
  from Durham's owner→grantor mapping deliberately.
- Future `Deed_Date` sentinels (5 rows) noted in scope strings; no invented
  DatasetSpec keys (`watermark_exclude_future` does not exist; arcgis path
  ignores `watermark_exclude`, which is CSV-client-only).
- Test guidance honored: no assertions on division/borough resolution
  results or geocode-hook call counts (both move when the spine lands).
  Assert parse fields, source-neighborhood passthrough, H3 from fixture
  coords, bbox containment, field-map mappings.

## Current step

Live re-probe + fixture capture.

## Next step

Author `cities/anchorage.py` + `field_maps_anchorage.py`, then tests, then
gates (`-k anchorage`, `pytest -m interlock`, full suite).
