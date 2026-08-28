# Stream log — west-medford — 2026-08-28

## Claim

- **Stream id:** `west-medford`
- **Leaf files I will create/edit:**
  - `apps/api/src/spatial/cities/medford.py`
  - `apps/api/src/producers/field_maps_medford.py`
  - `apps/api/tests/unit/test_producers_medford.py`
- **Spine files I expect to need:** NONE

## Intent

Live-probe Medford, OR (cityofmedford.org → `maps.medfordmaps.org` ArcGIS
Server 12.1) for 1-4 verifiable official municipal open-data feeds (permits /
311 / SLA licenses / deeds). None verified → REJECT with evidence; verified
→ build leaf `medford.py` + `field_maps_medford.py` +
`test_producers_medford.py` in the greenville/tucson style, spine-stable,
with live byte-verbatim fixtures.

## Decisions

- 2026-08-28T00:20Z — **PROBE VERIFIED (3 feeds, all on the city's ArcGIS
  Server `maps.medfordmaps.org`, ArcGIS 12.1), fed by the TRAKiT Community
  Development database.**
  1. **PERMITS** — `TRAKiTExport/TRAKiTPermits_service/FeatureServer/1`
     ("Permits from 2020 to Present"). **59,200 rows**; native point geometry
     (store SR WKID 2270 = OR State Plane North feet; client requests
     `outSR=4326` → WGS84; first 2000 live rows all carried geometry).
     Watermark **ISSUED**, max `1787788800000` = 2026-08-27T00:00Z
     (fresh/daily). Cols: PERMIT_NO, PermitType, PermitSubType, STATUS,
     APPLIED/APPROVED/ISSUED/FINALED/EXPIRED (all esri dates), JOBVALUE,
     SITE_ADDR/NUMBER/STREETNAME/UNIT/CITY/STATE/ZIP, SITE_APN,
     PARENT_PROJECT_NO. SITE_CITY ∈ {MEDFORD, CENTRAL POINT, UNINCORPORATED};
     SITE_ZIP ∈ {97501, 97502, 97504}. maxRecordCount 2000, Query-only.
  2. **SLA** — `MLI2/MLI_TRAKiT_Service/FeatureServer/14` (License2_Main,
     TRAKiT business-license table). **29,576 rows** (6,594 ACTIVE). TABLE —
     no geometry → `needs_geocode=True` on SITE_ADDR. Watermark **ISSUED**,
     max `1787875200000` = 2026-08-28T00:00Z (today). Cols: LICENSE_NO
     (BL26-xxxxx), LICENSE_TYPE (COMMERCIAL/HOME BASED/LIQUOR/MARIJUANA/
     RENTAL REGISTRATION/PAWNBROKERS/...), LICENSE_SUBTYPE, STATUS
     (ACTIVE/INACTIVE/REVOKED/...), APPLIED/ISSUED/EXPIRED, SITE_ADDR/CITY/
     STATE/ZIP, SITE_APN, COMPANY, SIC_1, RECORDID (SLC:...).
  3. **COMPLAINTS_311** — `MLI2/MLI_TRAKiT_Service/FeatureServer/12`
     (Case_Main, TRAKiT code-enforcement cases). **83,683 rows**. TABLE — no
     geometry → `needs_geocode=True` on SITE_ADDR. Watermark **STARTED**, max
     `1787875200000` = 2026-08-28T00:00Z (today). Cols: CASE_NO (CE26-xxxxx),
     CaseType (NUISANCE VIOLATION/WEED COMPLAINT/DOG COMPLAINT/GRAFFITI/SIGN
     VIOLATION/...), CaseSubType, STATUS (ACTIVE/CLOSED/...),
     STARTED/CLOSED/LASTACTION, SITE_ADDR/CITY/STATE/ZIP, SITE_APN, RECORDID
     (DMA:...). NOTE: **LASTACTION carries future-dated sentinels**
     (2026-09-01/02 on probe) → watermark is STARTED (clean), LASTACTION
     never a candidate.
- 2026-08-28T00:30Z — **HOST IS ANSI-DATE**: maps.medfordmaps.org rejects ISO
  date-string AND epoch-ms `where` (400 "Unable to complete operation") but
  accepts ANSI `timestamp 'YYYY-MM-DD'` and `CURRENT_TIMESTAMP`. Spine must
  add `maps.medfordmaps.org` to `ANSI_DATE_LITERAL_HOSTS` (watermarks.py).
  Future-date sentinels exist on cases.LASTACTION only; permits ISSUED/APPLIED
  clean (max 2026-08-27), licenses ISSUED clean (max 2026-08-28).
- 2026-08-28T00:40Z — **DEEDS Tier 3** (partial without deeds is fine per
  ticket): Jackson County recorder has no anonymous bulk API; city layers only
  carry taxlot polygons (no transaction records). **Crime Tier 3**: Police
  CADHistory is a Table with NO address/coord columns (only BEAT_OR_STATION)
  → unregistrable per ADR-0004. **HTE_CodeEnforcement (Police folder)** has
  point geometry but is STALE (newest real report 2019-03-02) + 2099
  sentinels → NOT registered; Case_Main (TRAKiT) supersedes it.
- 2026-08-28T01:00Z — Created leaf files (field_maps_medford.py,
  medford.py, test_producers_medford.py). Metro bbox: 42.26–42.41,
  -122.99–-122.78 (excludes White City 42.4367 to the north and
  Talent/Phoenix/Ashland to the south). 8 divisions, 11 submarkets.
- 2026-08-28T01:30Z — Fixed ruff (unused `first_mapped` import) + two test
  assertions (EXPIRED = 2027-02-23; ELECTRICAL → JobType.A2 because it
  contains "ELECTRIC" — the shared producer's rule). All green.

## Current step

Complete — leaf built, all verification green.

## Next step

None (leaf worker). See **Outcome** / **Spine delta** below for the
spine-owner handoff.

---

## Outcome

**FEEDS VERIFIED: 3 of 3 (PERMITS, SLA, COMPLAINTS_311).**

| Feed | Endpoint | Platform | Rows | Watermark (col → newest value verbatim) |
|---|---|---|---|---|
| PERMITS | `TRAKiTExport/TRAKiTPermits_service/FeatureServer/1` | arcgis | 59,200 | `ISSUED` → `1787788800000` = 2026-08-27T00:00:00+00:00 (daily, co-newest rows incl. `BMEC26-02931`) |
| SLA | `MLI2/MLI_TRAKiT_Service/FeatureServer/14` | arcgis | 29,576 (6,594 ACTIVE) | `ISSUED` → `1787875200000` = 2026-08-28T00:00:00+00:00 (co-newest incl. `BL24-00951`) |
| COMPLAINTS_311 | `MLI2/MLI_TRAKiT_Service/FeatureServer/12` | arcgis | 83,683 | `STARTED` → `1787875200000` = 2026-08-28T00:00:00+00:00 (co-newest incl. `CE26-02274`) |

Geometry: PERMITS = native point (store SR WKID 2270 OR State Plane N feet →
client `outSR=4326` lift; no X/Y attributes exist). SLA + 311 = tables, no
geometry → `needs_geocode=True` on SITE_ADDR (ADR 0004), context "Medford, OR".

Rejected (evidence on file): DEEDS (Jackson County no bulk API), CRIME (CAD
table has no address/coords), HTE_CodeEnforcement (stale 2019 + 2099
sentinels). All are Tier 3.

Tests: `test_producers_medford.py` 39 passed; `-k medford` 41 passed;
`-m interlock` **24 passed** (green); `ruff` clean on all three leaf files.
Fixtures are byte-verbatim live captures through the real ArcGIS flatten path.

## Spine delta

Required registration work (spine-owned; NOT done by this leaf):

- **CityId member:** `MEDFORD = "medford"` in `src/spatial/city_registry.py`.
- **ALIASES:** `"medford"`, `"medford_or"`, `"medford-or"`, `"medford or"`,
  `"medford_oregon"`.
- **Registry entry** `CityId.MEDFORD`: name "Medford, OR", state "OR",
  center `{"lat": 42.3266, "lng": -122.8756}`, `metro_bbox`/`divisions`/
  `submarkets` from `src.spatial.cities.medford`, job_suffix "medford".
  datasets = the three `DatasetSpec`s from `MEDFORD_FEED_SPECS` (permits /
  sla / 311). Import the field maps in city_registry.py:
  `from src.producers.field_maps_medford import ...`.
- **Config endpoint settings** (`src/config.py`): the leaf hardcodes the
  three endpoints (greenville/tucson precedent); add optional
  `arcgis_medford_*` settings if the spine prefers. No endpoint settings are
  strictly required — the specs carry literal URLs.
- **ANSI date host (REQUIRED):** add `maps.medfordmaps.org` to
  `ANSI_DATE_LITERAL_HOSTS` in `src/producers/watermarks.py` — the host
  rejects ISO date-string literals (400), verified live.
- **Metro wiring per city-registration rule:** METRO_META entry + dashboard
  byte-sync etc. is the spine hold's job — do in the same hold as the
  registry entry.
- **Suggested Linear comment:** "Medford, OR (US-238): leaf verified 3 feeds
  on `maps.medfordmaps.org` ArcGIS 12.1 (TRAKiT) — permits (59.2k, native
  point geom, ISSUED 2026-08-27), SLA licenses (29.6k, table → geocode),
  code-enforcement 311 cases (83.7k, table → geocode, STARTED watermark;
  LASTACTION future-sentinels). Deeds/crime Tier 3. Host is ANSI-date —
  add `maps.medfordmaps.org` to ANSI_DATE_LITERAL_HOSTS. Ready for spine
  hold to register CityId.medford."
