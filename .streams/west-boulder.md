# Stream log — west-boulder — 2026-08-28

## Claim

- **Stream id:** west-boulder
- **Leaf files I will create/edit:**
  - apps/api/src/spatial/cities/boulder.py
  - apps/api/src/producers/field_maps_boulder.py
  - apps/api/tests/unit/test_producers_boulder.py
- **Spine files I expect to need:** NONE

## Intent

Live-probe official City of Boulder (and Boulder County) municipal open-data
feeds (permits / 311 / SLA licenses / deeds), verify 1-4 feeds with
byte-verbatim evidence, and build the west-boulder leaf (spatial module +
field maps + spine-stable tests). No spine edits; recommend spine delta in
the stream log.

## Decisions

- 2026-08-28 — City ArcGIS Server found: maps.bouldercolorado.gov (ArcGIS
  Server 11.5). Folders: cv, finance, fire, general, housing, IT, locators,
  osmp, parks, pds, plan, police, raster, Utilities.
- 2026-08-28 — City open-data hub: open-data.bouldercolorado.gov (AGOL org
  BoulderCO, orgId ePKBjXrBZ2vEEgWd). AGOL hosted FeatureServers under
  services.arcgis.com/ePKBjXrBZ2vEEgWd.
- 2026-08-28 — CANDIDATE #1 PERMITS: Construction_Permits FeatureServer/0
  (Table, non-spatial) — 335,946 rows; all dates are STRING ANSI "YYYY-MM-DD"
  (AppliedDate/IssuedDate/CompletedDate); watermark IssuedDate, newest
  2026-08-27; address-only (OriginalAddress + City/State/Zip) => needs_geocode.
- 2026-08-28 — CANDIDATE #2 SLA: Licensed_Contractors FeatureServer/0 (Table,
  non-spatial) — 3,077 rows; LicenseStatus all "Issued" (current snapshot);
  ExpirationDate has future sentinel "5026-05-05"; address string includes
  city/state/zip; LicenseNumber unique.
- 2026-08-28 — REJECT SLA: Active_Business_Licenses FeatureServer/0 — 13,656
  rows but STALE (newest License_Effective_Date 2019-09-09); City/State/Zip
  only, NO street address (ungeocodable).
- 2026-08-28 — REJECT 311: Inquire_Boulder_Customer_Service_Portal_Requests_by_Topic
  — 62,265 rows but aggregate by Department/Topic, no addresses, no geometry.
  InquireBoulderIncidentAddress/RequesterAddress are address locators (no data).
- 2026-08-28 — CANDIDATE #3 DEEDS: Boulder County Recent Sales
  (services1.arcgis.com/Sb0rgSd67ecLKIvl/.../Boulder_County_Recent_Sales/FeatureServer/0)
  — 194,681 rows, PARCEL POLYGON geometry, native WKID 2876 (NAD83 CO North
  state-plane feet), outSR=4326 centroid lift; SaleDate esriFieldTypeDate,
  max 2025-03-28; UniqueID/AccountNo/ParcelNo/DeedReceptionNo/DeedType/SalePrice.
- 2026-08-28 — REJECT CRIME-for-this-leaf: Boulder_PD_Calls_For_Service
  (365,854 rows, point geometry WKID 4269) verified but ticket prefers
  permits/311/SLA/deeds; crime not in scope for this leaf.
- 2026-08-28 — FINAL FEED SET: PERMITS = Construction_Permits (verified, fresh
  2026-08-27, non-spatial → needs_geocode) + SLA = RentalHousingLicenses
  (verified, polygon WKID 2876 centroid, APPLIEDDATE watermark). DEEDS REJECTED
  (no fresh verifiable bulk feed — Recent Sales stale 2025-03-28 with null
  dates + non-queryable date ranges; PropSearch_SALES future-date sentinels +
  non-spatial). 311 REJECTED (aggregate, no addresses). Other SLA candidates
  rejected (Active_Business_Licenses stale 2019; Licensed_Contractors snapshot
  with no watermark).
- 2026-08-28 — Leaf files built: boulder.py, field_maps_boulder.py,
  test_producers_boulder.py. 45 boulder tests pass, 24 interlock pass, ruff clean.

## Current step

PHASE A + B complete — leaf files built and verified.

## Next step

Spine integration: register CityId.BOULDER.

## Outcome

**2 verified feeds, 1 REJECT (deeds):**

### PERMITS — Construction Permits ✅
- **Endpoint:** `https://services.arcgis.com/ePKBjXrBZ2vEEgWd/arcgis/rest/services/Construction_Permits/FeatureServer/0`
- **Platform:** arcgis (AGOL FeatureServer, Table — non-spatial)
- **Rows:** 335,946
- **Watermark:** IssuedDate (string ANSI `YYYY-MM-DD`), newest 2026-08-27
- **Columns:** PermitID, PermitNum, MasterPermitNum, Description, AppliedDate, IssuedDate, CompletedDate, StatusCurrent, OriginalAddress, OriginalCity, OriginalState, OriginalZip, COBPIN, BOCOPIN, BOCOTAX, ProjectName, PermitType, PermitWorkType, EstProjectCost, EstPhotovoltaicCost, EstSolarCost, NewHousingUnits, ExistingHousingUnits, AffordableHousingUnits, RemovedHousingUnits, AddedSqFt, RemodeledSqFt, RemovedResSqFt, RemovedNonResSqFt, RemovedParkingStructureSqFt, RemovedDescription, PhotovoltaicKilowatt, PhotovoltaicElecVehicleOffset, ElecVehicleChargeStation, SolarSystemDescription, ContractorCompanyName, ContractorTrade, ObjectId
- **Geometry:** None (Table) — needs_geocode=True; address from OriginalAddress + OriginalCity/OriginalState/OriginalZip
- **Dates:** all ANSI string `YYYY-MM-DD` — not esriFieldTypeDate; producer `_parse_datetime` handles `%Y-%m-%d`
- **Quirks:** OriginalCity has typos (BOUDER/BUOLDER) and out-of-city values (LONGMONT/GREELEY); bbox filters

### SLA — Rental Housing Licenses ✅
- **Endpoint:** `https://gis.bouldercolorado.gov/ags_svr1/rest/services/plan/RentalHousingLicenses/MapServer/0`
- **Platform:** arcgis (city ArcGIS Server MapServer)
- **Rows:** 11,720
- **Watermark:** APPLIEDDATE (esriFieldTypeDate), newest 2026-08-24
- **Columns:** OBJECTID, COBPIN, BOCOTAX, BOCOPIN, LICENSENUMBER, MAINADDRESS, LICENSESTATUS, APPLIEDDATE, ISSUEDDATE, EXPIRATIONDATE, LASTRENEWALDATE, SUBCOMMUNITY, RENTALTYPE, COMPLEXNAME, BUILDINGTYPE, ENERGYCOMPLIANT, BUILDINGIDENTIFICATION, DWELLINGUNITSONCASE, ROOMINGUNITSONCASE, PROFESSIONALLICENSEHOLDERNAME, PROFESSIONALLICENSEHOLDERCMPNY, PROFESSIONALLICENSEYEAR
- **Geometry:** Polygon (parcel), native WKID 2876 (NAD83 CO North state-plane ft), outSR=4326 centroid lift
- **Dates:** esriFieldTypeDate (epoch-ms → ISO via ArcGISClient)
- **geometry:** Polygon → centroid via shapely (ArcGISClient._geometry_to_lng_lat)
- **Quirks:** ISSUEDDATE carries future-dated license-period effective dates (e.g. 2027-04-20) — NOT the watermark; APPLIEDDATE is the clean watermark. EXPIRATIONDATE may be null for pending applications. SUBCOMMUNITY supplies source_neighborhood (South Boulder, Southeast Boulder, Palo Park, etc.)

### DEEDS — REJECTED ❌
- **Boulder County Recent Sales** (AGOL, 194,681 rows, polygon): max SaleDate 2025-03-28 (~17 months stale), item modified 2024-09-03, date-range where clauses return 400, many null SaleDate rows
- **PropSearch_SALES** (county ArcGIS Server, 752,488 rows, table): future-date sentinels on SaleDate (top rows 2057/2027), non-queryable date ranges, non-spatial

### 311 — REJECTED ❌
- Inquire_Boulder_Customer_Service_Portal_Requests_by_Topic: aggregate by Department/Topic, no addresses, no geometry
- InquireBoulderIncidentAddress/RequesterAddress: address locators (no data)

### SLA (other) — REJECTED ❌
- Active_Business_Licenses: stale (2019), City/State/Zip only, no street address
- Licensed_Contractors: current snapshot, no usable watermark (only future-dated ExpirationDate), PO box addresses

### Tests
- 45 boulder-specific tests pass
- 24 interlock tests pass (leaf-naming count pin failure is spine-owned, ignore)
- ruff check: 0 errors

## Spine delta

Recommended additions to `src/spatial/city_registry.py` in a spine hold:

**CityId member:**
```python
BOULDER = "boulder"
```

**Aliases:**
```python
"boulder": CityId.BOULDER,
"boulder_co": CityId.BOULDER,
"boulder-co": CityId.BOULDER,
"boulder co": CityId.BOULDER,
```

**REGISTRY entry:**
```python
CityId.BOULDER: CityRegistration(
    city_id=CityId.BOULDER,
    name="Boulder",
    state="CO",
    center={"lat": 40.0150, "lng": -105.2700},
    metro_bbox=BOULDER_METRO_BBOX,
    division_bboxes=BOULDER_DIVISION_BBOXES,
    submarkets=BOULDER_SUBMARKETS,
    divisions=BOULDER_DIVISIONS,
    datasets={
        FeedType.PERMITS: DatasetSpec(
            endpoint=settings.boulder_permits_endpoint,  # new config key
            platform="arcgis",
            watermark_col="IssuedDate",
            id_keys=["PermitNum", "PermitID", "ObjectId"],
            topic=settings.topic_permits,
            interval_seconds=300.0,
            producer_key="permits",
            expected_cadence_days=1,
            needs_geocode=True,
            geocode_context="Boulder, CO",
            oid_field="ObjectId",
            max_record_count=1000,
            order_by="IssuedDate DESC",
            watermark_type="text",
            watermark_format="%Y-%m-%d",
            field_map=PERMITS_FIELD_MAP,
        ),
        FeedType.SLA: DatasetSpec(
            endpoint=settings.boulder_sla_endpoint,  # new config key
            platform="arcgis",
            watermark_col="APPLIEDDATE",
            id_keys=["LICENSENUMBER", "OBJECTID"],
            topic=settings.topic_sla,
            interval_seconds=600.0,
            producer_key="sla",
            expected_cadence_days=7,
            needs_geocode=False,
            oid_field="OBJECTID",
            max_record_count=2000,
            order_by="APPLIEDDATE DESC",
            state_plane_crs="EPSG:2876",
            state_plane_units="ftUS",
            field_map=SLA_FIELD_MAP,
        ),
    },
)
```

**Config entries** (in `src/config.py`):
```python
boulder_permits_endpoint: str = (
    "https://services.arcgis.com/ePKBjXrBZ2vEEgWd/arcgis/rest/services/"
    "Construction_Permits/FeatureServer/0"
)
boulder_sla_endpoint: str = (
    "https://gis.bouldercolorado.gov/ags_svr1/rest/services/"
    "plan/RentalHousingLicenses/MapServer/0"
)
```

**Imports to add** (in `city_registry.py`):
```python
from src.producers.field_maps_boulder import PERMITS_FIELD_MAP, SLA_FIELD_MAP
from src.spatial.cities.boulder import (
    BOULDER_DIVISION_BBOXES, BOULDER_DIVISIONS, BOULDER_METRO_BBOX, BOULDER_SUBMARKETS,
)
```

**METRO_META** (dashboard): add `"boulder"` to the `METRO_META` dict with `?city=boulder` deep link, snapshot export coverage, and byte-synced `apps/dashboard/public/index.html`.
