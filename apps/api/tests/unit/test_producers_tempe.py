"""Unit tests for the Tempe, AZ leaf (US-229): spatial module + field maps +
producer parse wiring.

Tempe is a THREE-FEED PARTIAL metro on the city's ArcGIS Hub
(``data.tempe.gov``, org ``lQySeXwbBg53XWDi``; datasets live on
``services.arcgis.com`` FeatureServers — no Socrata exists): PERMITS
(``building_permits/FeatureServer/0``, Tier 1, daily), COMPLAINTS_311
(``code_complaints/FeatureServer/0``, the 311-family proxy; watermark
stopped 2026-06-12 on the probe day — quarterly publication suspected), and
CRIME (``General_Offenses_(Open_Data)/FeatureServer/0``, mixed-CRS layer).
SLA (no license feed exists — the ABOR stub has zero layers), deeds
(recorder.maricopa.gov is a 403 session-gated app), arrests and
calls-for-service (verified live, no FeedType slot / volume discipline) stay
unregistered.

Tests pass WITHOUT a spine registration (no CityId.TEMPE, no REGISTRY
assertions — "tempe" stays a plain string). Spine-stable per the wave leaf
contract: no division/borough-resolution assertions and no geocode-hook
call-count assertions (both change when the spine lands). Feeds are
requested by plain feed-name string (chandler convention), not by FeedType
enum.

Fixtures captured byte-verbatim 2026-08-28 from the live FeatureServers
(newest rows via ``orderByFields=<watermark> DESC`` at ``outSR=4326`` — the
SR ``ArcGISClient`` always requests). Watermarks on capture: permits
``AppliedDateDtm`` newest ``1787702400000`` = 2026-08-26T00:00:00+00:00
(IssuedDateDtm reached 1787788800000 = 2026-08-27); code_complaints
``CaseOpenDate`` newest ``1781247600000`` = 2026-06-12T07:00:00+00:00
(~11 weeks stale); general_offenses ``OccurrenceDatetime`` newest
``1787873460000`` = 2026-08-27T23:31:00+00:00 (same-day fresh). Fixtures are
RAW ArcGIS features (attributes + geometry); the tests run the real
``ArcGISClient._flatten_feature`` lift — geometry to latitude/longitude,
epoch-ms to ISO — before parsing, exactly as the live producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_tempe import (
    COMPLAINTS_311_FIELD_MAP,
    CRIME_FIELD_MAP,
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.tempe import (
    REGISTRATION,
    TEMPE_CITY_ID,
    TEMPE_COMPLAINTS_311_ENDPOINT,
    TEMPE_CRIME_ENDPOINT,
    TEMPE_DIVISION_BBOXES,
    TEMPE_DIVISIONS,
    TEMPE_FEED_SPECS,
    TEMPE_GEOCODE_CONTEXT,
    TEMPE_METRO_BBOX,
    TEMPE_PERMITS_ENDPOINT,
    TEMPE_STATE_PLANE_CRS,
    TEMPE_STATE_PLANE_UNITS,
    TEMPE_SUBMARKETS,
    get_tempe_dataset,
    is_in_greater_tempe_metro,
    is_in_tempe_metro,
)


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


# Full esriFieldTypeDate sets discovered from the live layer metadata
# (what ArcGISClient passes to _flatten_feature in production).
_PERMITS_DATE_FIELDS = {
    "AppliedDateDtm",
    "IssuedDateDtm",
    "CompletedDateDtm",
    "StatusDateDtm",
    "ExpiresDateDtm",
    "COIssuedDateDtm",
    "VoidDateDtm",
}
_COMPLAINTS_DATE_FIELDS = {"CaseStatusDate", "CaseOpenDate"}
_CRIME_DATE_FIELDS = {"OccurrenceDatetime"}


def _flatten(feature, date_fields):
    """Run the real ArcGIS flatten lift over a raw captured feature."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, date_fields)


# ---------------------------------------------------------------------------
# Byte-verbatim fixtures — permits (building_permits/FeatureServer/0), newest
# rows on AppliedDateDtm DESC at outSR=4326 (2026-08-28). Plain YYYY-MM-DD
# string date twins, esriFieldTypeDate *Dtm epoch-ms, WGS84 Latitude/
# Longitude attributes, future-dated ExpiresDateDtm sentinels, null
# contractor block.
# ---------------------------------------------------------------------------
_PERMIT_8597093 = {
    "attributes": {
        "OBJECTID": 8597093,
        "PermitNum": "BP261951",
        "Description": "UPGRADE OF EXISTING SES TO 200AMP",
        "AppliedDate": "2026-08-26",
        "AppliedDateDtm": 1787702400000,
        "IssuedDate": "2026-08-26",
        "IssuedDateDtm": 1787702400000,
        "CompletedDate": None,
        "CompletedDateDtm": None,
        "Type": "Residential Addition/Alteration/Remodel",
        "StatusCurrent": "Issued",
        "OriginalAddress1": "101 E ENCANTO DR",
        "OriginalAddress2": None,
        "OriginalCity": "TEMPE",
        "OriginalState": "AZ",
        "OriginalZip": "85281",
        "PermitClass": "997 - Electrical - No Value",
        "PermitType": "Building,Permit,Permit,NA",
        "PermitTypeDesc": "Building Permit",
        "StatusDate": "2026-08-26",
        "StatusDateDtm": 1787702400000,
        "TotalSqFt": 0,
        "Latitude": 33.40924937,
        "Longitude": -111.93800933,
        "EstProjectCost": 5500,
        "HousingUnits": 0,
        "ContractorCompanyName": None,
        "ContractorLicNum": None,
        "ExpiresDate": "2027-08-26",
        "ExpiresDateDtm": 1819238400000,
        "COIssuedDate": None,
        "COIssuedDateDtm": None,
        "VoidDate": None,
        "VoidDateDtm": None,
        "ProjectName": "NEIBERGALL LIVING TRUST RESIDENCE",
        "Fee": 201,
        "ContractorPhone": None,
        "ContractorAddress1": None,
        "ContractorAddress2": None,
        "ContractorCity": None,
        "ContractorState": None,
        "ContractorZip": None,
        "ContractorEmail": None,
        "Zone": "R1-6",
    },
    "geometry": {"x": -111.93800932999994, "y": 33.409249370000055},
}

_PERMIT_8597094 = {
    "attributes": {
        "OBJECTID": 8597094,
        "PermitNum": "BP261953",
        "Description": "REPLACEMENT OF 100AMP SES - EMERGENCY REPLACEMENT",
        "AppliedDate": "2026-08-26",
        "AppliedDateDtm": 1787702400000,
        "IssuedDate": "2026-08-26",
        "IssuedDateDtm": 1787702400000,
        "CompletedDate": None,
        "CompletedDateDtm": None,
        "Type": "Residential Addition/Alteration/Remodel",
        "StatusCurrent": "Issued",
        "OriginalAddress1": "1533 E HUDSON DR",
        "OriginalAddress2": None,
        "OriginalCity": "TEMPE",
        "OriginalState": "AZ",
        "OriginalZip": "85281",
        "PermitClass": "997 - Electrical - No Value",
        "PermitType": "Building,Permit,Permit,NA",
        "PermitTypeDesc": "Building Permit",
        "StatusDate": "2026-08-26",
        "StatusDateDtm": 1787702400000,
        "TotalSqFt": 0,
        "Latitude": 33.41351012,
        "Longitude": -111.91285884,
        "EstProjectCost": 4000,
        "HousingUnits": 0,
        "ContractorCompanyName": None,
        "ContractorLicNum": None,
        "ExpiresDate": "2027-08-26",
        "ExpiresDateDtm": 1819238400000,
        "COIssuedDate": None,
        "COIssuedDateDtm": None,
        "VoidDate": None,
        "VoidDateDtm": None,
        "ProjectName": "GREENE RESIDENCE",
        "Fee": 201,
        "ContractorPhone": None,
        "ContractorAddress1": None,
        "ContractorAddress2": None,
        "ContractorCity": None,
        "ContractorState": None,
        "ContractorZip": None,
        "ContractorEmail": None,
        "Zone": "R1-6",
    },
    "geometry": {"x": -111.91285883999996, "y": 33.41351012000007},
}

_PERMIT_8597091 = {
    "attributes": {
        "OBJECTID": 8597091,
        "PermitNum": "BP261945",
        "Description": "REPLACEMENT & UPGRADE OF SES PANEL",
        "AppliedDate": "2026-08-25",
        "AppliedDateDtm": 1787616000000,
        "IssuedDate": "2026-08-26",
        "IssuedDateDtm": 1787702400000,
        "CompletedDate": None,
        "CompletedDateDtm": None,
        "Type": "Residential Addition/Alteration/Remodel",
        "StatusCurrent": "Issued",
        "OriginalAddress1": "329 E FAIRMONT DR",
        "OriginalAddress2": None,
        "OriginalCity": "TEMPE",
        "OriginalState": "AZ",
        "OriginalZip": "85282",
        "PermitClass": "997 - Electrical - No Value",
        "PermitType": "Building,Permit,Permit,NA",
        "PermitTypeDesc": "Building Permit",
        "StatusDate": "2026-08-26",
        "StatusDateDtm": 1787702400000,
        "TotalSqFt": 0,
        "Latitude": 33.39609735,
        "Longitude": -111.93335196,
        "EstProjectCost": 5000,
        "HousingUnits": 0,
        "ContractorCompanyName": None,
        "ContractorLicNum": None,
        "ExpiresDate": "2027-08-26",
        "ExpiresDateDtm": 1819238400000,
        "COIssuedDate": None,
        "COIssuedDateDtm": None,
        "VoidDate": None,
        "VoidDateDtm": None,
        "ProjectName": "BUNTON RESIDENCE",
        "Fee": 201,
        "ContractorPhone": None,
        "ContractorAddress1": None,
        "ContractorAddress2": None,
        "ContractorCity": None,
        "ContractorState": None,
        "ContractorZip": None,
        "ContractorEmail": None,
        "Zone": "R1-6",
    },
    "geometry": {"x": -111.93335195999998, "y": 33.39609735000005},
}

_APPLIED_ISO = "2026-08-26T00:00:00+00:00"
_APPLIED_8597091_ISO = "2026-08-25T00:00:00+00:00"
_EXPIRES_ISO = "2027-08-26T00:00:00+00:00"

# ---------------------------------------------------------------------------
# Byte-verbatim fixtures — code_complaints/FeatureServer/0, newest rows on
# CaseOpenDate DESC at outSR=4326 (2026-08-28). All three share the
# co-newest watermark 1781247600000 = 2026-06-12T07:00:00+00:00; X_COORD/
# Y_COORD are degree duplicates of the geometry; violation text is long
# code-citation prose.
# ---------------------------------------------------------------------------
_COMPLAINT_261 = {
    "attributes": {
        "OBJECTID": 261,
        "Id": "14453f11-2db2-4138-973c-851b9b650172",
        "CaseNo": "CM260999",
        "Address": "214 S ROCKFORD DR, TEMPE, AZ, 85281",
        "CaseStatus": "Under Investigation",
        "CaseStatusDate": 1781247600000,
        "CaseOpenDate": 1781247600000,
        "Violation": (
            "ZDC 4-903B - Sign Type Q- Sign Type Q- Any portable sign "
            "within three (3) feet of a building or outdoor approved patio "
            "shall adhere to size, location, and usage specifications."
        ),
        "ViolationType": "Sign",
        "X_COORD": -111.898017,
        "Y_COORD": 33.427881,
    },
    "geometry": {"x": -111.89801699999998, "y": 33.42788100000007},
}

_COMPLAINT_262 = {
    "attributes": {
        "OBJECTID": 262,
        "Id": "7ce05e96-b786-4006-8101-e27432d275d6",
        "CaseNo": "CM261001",
        "Address": "701 W GROVE PKWY, TEMPE, AZ, 85283",
        "CaseStatus": "Under Investigation",
        "CaseStatusDate": 1781247600000,
        "CaseOpenDate": 1781247600000,
        "Violation": "ZDC 4-706.F. - Outdoor storage without masonry screen wall",
        "ViolationType": "Zoning",
        "X_COORD": -111.94936328,
        "Y_COORD": 33.3547834,
    },
    "geometry": {"x": -111.94936327999994, "y": 33.35478340000003},
}

_COMPLAINT_264 = {
    "attributes": {
        "OBJECTID": 264,
        "Id": "3b630eb3-07a9-4bc7-8a5e-4b93416d4bc0",
        "CaseNo": "CE263400",
        "Address": "738 W 12TH PL, TEMPE, AZ, 85281",
        "CaseStatus": "Under Investigation",
        "CaseStatusDate": 1781247600000,
        "CaseOpenDate": 1781247600000,
        "Violation": (
            "CC 21-3.b.8 - Uncultivated weeds in gravel landscape, or a "
            "lawn higher than 12 inches"
        ),
        "ViolationType": "Nuisance",
        "X_COORD": -111.95094751,
        "Y_COORD": 33.41524105,
    },
    "geometry": {"x": -111.95094750999999, "y": 33.41524105000008},
}

_COMPLAINT_OPEN_ISO = "2026-06-12T07:00:00+00:00"

# ---------------------------------------------------------------------------
# Byte-verbatim fixtures — General_Offenses_(Open_Data)/FeatureServer/0,
# newest rows on OccurrenceDatetime DESC at outSR=4326 (2026-08-28). MIXED
# CRS: the live store SR is WKID 2223 (AZ State Plane Central, intl ft) and
# the XCoordinate/YCoordinate attributes carry the state-plane pair
# (697343/875784 on the probe) while Latitude/Longitude attributes and the
# outSR=4326 geometry are WGS84. PrimaryKey and OffenseCustom are
# CHAR-padded. Rows 380316 / 380290 / 380261 are the three newest offenses.
# ---------------------------------------------------------------------------
_OFFENSE_380316 = {
    "attributes": {
        "OBJECTID": 380316,
        "PrimaryKey": "TE202686976         ",
        "OccurrenceDatetime": 1787873460000,
        "OccurrenceYear": 2026,
        "OccurrenceMonth": 8,
        "OccurrenceHour": 23,
        "OccurrenceWeek": "35",
        "OccurrenceDatePart": "27",
        "OccurrenceWeekday": "Thursday",
        "ObfuscatedAddress": "MILL AVE / E GENEVA DR",
        "XCoordinate": 692990,
        "YCoordinate": 871431,
        "Disclaimer": "Point has not been altered",
        "PlaceName": None,
        "OffenseCustom": None,
        "LocationTranslation": None,
        "Latitude": 33.395506,
        "Longitude": -111.939635,
        "RucrComp": "C",
        "CharacterArea": "Alameda",
        "ReportDistrict": "S",
        "ReportBeat": "19",
        "PostalCode": "85282",
        "CensusTractID": "04013319600",
        "ParkName": None,
        "NeighborhoodName": None,
    },
    "geometry": {"x": -111.93964625660145, "y": 33.3955111585924},
}

_OFFENSE_380290 = {
    "attributes": {
        "OBJECTID": 380290,
        "PrimaryKey": "TE202686968         ",
        "OccurrenceDatetime": 1787871540000,
        "OccurrenceYear": 2026,
        "OccurrenceMonth": 8,
        "OccurrenceHour": 22,
        "OccurrenceWeek": "35",
        "OccurrenceDatePart": "27",
        "OccurrenceWeekday": "Thursday",
        "ObfuscatedAddress": "1XXX S COLLEGE AVE",
        "XCoordinate": 694521,
        "YCoordinate": 876751,
        "Disclaimer": "Point has not been altered",
        "PlaceName": "DALEY PARK                              ",
        "OffenseCustom": (
            "[SC-0] INFO - INFORMATION OTHER (NON-CRIMINAL)                  "
            "                "
        ),
        "LocationTranslation": "Parking/Drop Lot/Garage                                                        ",
        "Latitude": 33.410128,
        "Longitude": -111.934622,
        "RucrComp": "C",
        "CharacterArea": "Rio Salado/DT/ASU/NW Neighborhoods",
        "ReportDistrict": "N",
        "ReportBeat": "13",
        "PostalCode": "85281",
        "CensusTractID": "04013319002",
        "ParkName": "Daley Park",
        "NeighborhoodName": None,
    },
    "geometry": {"x": -111.93463286921688, "y": 33.41013351902738},
}

_OFFENSE_380261 = {
    "attributes": {
        "OBJECTID": 380261,
        "PrimaryKey": "TE202686933         ",
        "OccurrenceDatetime": 1787865240000,
        "OccurrenceYear": 2026,
        "OccurrenceMonth": 8,
        "OccurrenceHour": 21,
        "OccurrenceWeek": "35",
        "OccurrenceDatePart": "27",
        "OccurrenceWeekday": "Thursday",
        "ObfuscatedAddress": "UNIVERSITY DR / S PRIEST DR",
        "XCoordinate": 686498,
        "YCoordinate": 881053,
        "Disclaimer": "Point has not been altered",
        "PlaceName": None,
        "OffenseCustom": (
            "[13B] ASSAULT [DV]                                              "
            "                "
        ),
        "LocationTranslation": "Parking/Drop Lot/Garage                                                        ",
        "Latitude": 33.421945,
        "Longitude": -111.96092,
        "RucrComp": "C",
        "CharacterArea": "Diablo/Double Butte",
        "ReportDistrict": "N",
        "ReportBeat": "12",
        "PostalCode": "85281",
        "CensusTractID": "04013319710",
        "ParkName": None,
        "NeighborhoodName": None,
    },
    "geometry": {"x": -111.9609310156315, "y": 33.42195055205157},
}

_OCCURRED_ISO = "2026-08-27T23:31:00+00:00"


class TestTempeSpatial:
    def test_metro_bbox_sanity(self):
        assert TEMPE_METRO_BBOX["min_lat"] < TEMPE_METRO_BBOX["max_lat"]
        assert TEMPE_METRO_BBOX["min_lng"] < TEMPE_METRO_BBOX["max_lng"]

    def test_is_in_tempe_metro_rejects_missing_coordinates(self):
        assert is_in_tempe_metro(None, None) is False
        assert is_in_tempe_metro(33.4267, None) is False
        assert is_in_tempe_metro(None, -111.9398) is False

    def test_is_in_tempe_metro_rejects_other_cities(self):
        assert is_in_tempe_metro(33.4484, -112.0740) is False   # Phoenix
        assert is_in_tempe_metro(33.4152, -111.8287) is False   # Mesa downtown
        assert is_in_tempe_metro(33.4942, -111.9238) is False   # Scottsdale
        assert is_in_tempe_metro(33.3062, -111.8412) is False   # Chandler
        assert is_in_tempe_metro(33.3528, -111.7890) is False   # Gilbert

    def test_downtown_and_campus_anchors_are_contained(self):
        assert is_in_tempe_metro(33.4267, -111.9398)  # Mill Ave & University
        assert is_in_tempe_metro(33.4313, -111.9437)  # Hayden Ferry Lakeside
        assert is_in_tempe_metro(33.4245, -111.9285)  # ASU Memorial Union
        assert is_in_tempe_metro(33.4300, -111.9080)  # Escalante district
        assert is_in_tempe_metro(33.3820, -111.8747)  # Kiwanis Park
        assert is_in_tempe_metro(33.3400, -111.9200)  # South Tempe

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (
            _PERMIT_8597093,
            _PERMIT_8597094,
            _PERMIT_8597091,
            _COMPLAINT_261,
            _COMPLAINT_262,
            _COMPLAINT_264,
            _OFFENSE_380316,
            _OFFENSE_380290,
            _OFFENSE_380261,
        ):
            assert is_in_tempe_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in TEMPE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= TEMPE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= TEMPE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= TEMPE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= TEMPE_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in TEMPE_SUBMARKETS.items():
            bbox = TEMPE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in TEMPE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(TEMPE_SUBMARKETS)

    def test_submarkets_carry_the_tempe_city_id(self):
        assert {m.city_id for m in TEMPE_SUBMARKETS.values()} == {"tempe"}

    def test_city_id_and_registration_shape(self):
        assert TEMPE_CITY_ID == "tempe"
        assert REGISTRATION.metro_bbox is TEMPE_METRO_BBOX
        assert REGISTRATION.submarkets is TEMPE_SUBMARKETS
        assert REGISTRATION.division_bboxes is TEMPE_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_tempe_metro
        assert len(REGISTRATION.divisions) == 9
        assert len(TEMPE_SUBMARKETS) == 13

    def test_required_real_submarkets_present(self):
        assert set(TEMPE_SUBMARKETS) == {
            "Downtown Mill Avenue",
            "Hayden Ferry Lakeside",
            "ASU Campus & University Drive",
            "Escalante Historic District",
            "Papago Park & North Tempe",
            "Diablo Stadium Corridor",
            "Alameda Park & Hudson Manor",
            "Apache Boulevard Light Rail",
            "Mills Avenue & Emerald Park",
            "Kiwanis Park",
            "The Lakes",
            "Corona del Sol",
            "South Tempe Rural Corridor",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_tempe_metro is is_in_tempe_metro

    def test_state_plane_contract_documents_the_crime_store_sr(self):
        assert TEMPE_STATE_PLANE_CRS == "EPSG:2223"
        assert TEMPE_STATE_PLANE_UNITS == "ft"


class TestTempeFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["PermitNum", "OBJECTID"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["IssuedDateDtm", "IssuedDate"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["AppliedDateDtm", "AppliedDate"]
        assert PERMITS_FIELD_MAP["status"] == ["StatusCurrent"]
        assert PERMITS_FIELD_MAP["job_type"] == ["Type", "PermitClass"]
        assert PERMITS_FIELD_MAP["cost"] == ["EstProjectCost"]
        assert PERMITS_FIELD_MAP["address_street"] == ["OriginalAddress1"]
        assert PERMITS_FIELD_MAP["zipcode"] == ["OriginalZip"]
        assert PERMITS_FIELD_MAP["latitude"] == ["Latitude"]
        assert PERMITS_FIELD_MAP["longitude"] == ["Longitude"]

    def test_complaints_map_reads_live_columns(self):
        assert COMPLAINTS_311_FIELD_MAP["incident_id"] == ["CaseNo", "Id"]
        assert COMPLAINTS_311_FIELD_MAP["created_date"] == ["CaseOpenDate"]
        assert COMPLAINTS_311_FIELD_MAP["status"] == ["CaseStatus"]
        assert COMPLAINTS_311_FIELD_MAP["complaint_type"] == ["ViolationType"]
        assert COMPLAINTS_311_FIELD_MAP["incident_address"] == ["Address"]

    def test_case_status_date_is_never_a_closed_date(self):
        """CaseStatusDate is the last status-touch date, not a closure —
        mapping it to closed_date would fabricate resolutions."""
        assert "closed_date" not in COMPLAINTS_311_FIELD_MAP

    def test_crime_map_reads_live_columns(self):
        assert CRIME_FIELD_MAP["incident_id"] == ["PrimaryKey", "OBJECTID"]
        assert CRIME_FIELD_MAP["offense_type"] == ["OffenseCustom"]
        assert CRIME_FIELD_MAP["occurred_date"] == ["OccurrenceDatetime"]
        assert CRIME_FIELD_MAP["borough"] == ["CharacterArea"]
        assert CRIME_FIELD_MAP["latitude"] == ["Latitude"]
        assert CRIME_FIELD_MAP["longitude"] == ["Longitude"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {
            "permits": PERMITS_FIELD_MAP,
            "311": COMPLAINTS_311_FIELD_MAP,
            "crime": CRIME_FIELD_MAP,
        }
        assert GEOCODE_CONTEXT == "Tempe, AZ"
        assert TEMPE_GEOCODE_CONTEXT == "Tempe, AZ"

    def test_state_plane_coordinates_are_never_candidates(self):
        """CRIME XCoordinate/YCoordinate are AZ State Plane Central feet
        (WKID 2223 — probe sample 697343/875784); mapping them would emit
        projected feet as degrees. The WGS84 attribute pair is the fallback.
        COMPLAINTS X_COORD/Y_COORD are degree duplicates but stay unmapped
        (geometry primary, Greenville discipline)."""
        assert "XCoordinate" not in CRIME_FIELD_MAP["latitude"]
        assert "YCoordinate" not in CRIME_FIELD_MAP["longitude"]
        assert "latitude" not in COMPLAINTS_311_FIELD_MAP
        assert "longitude" not in COMPLAINTS_311_FIELD_MAP
        attrs = _OFFENSE_380316["attributes"]
        assert attrs["XCoordinate"] > 90 and attrs["YCoordinate"] > 90  # feet
        assert attrs["Latitude"] < 90 and attrs["Longitude"] < 0        # degrees

    def test_wgs84_attribute_pair_is_the_geometry_less_fallback(self):
        attrs = _OFFENSE_380316["attributes"]
        assert first_mapped(attrs, CRIME_FIELD_MAP, "latitude") == 33.395506
        assert first_mapped(attrs, CRIME_FIELD_MAP, "longitude") == -111.939635

    def test_crime_keeps_obfuscated_addresses_unmapped(self):
        """ObfuscatedAddress ("9XX E BROADWAY RD") is not geocodable;
        ADR-0004 is satisfied by coordinates and needs_geocode stays False —
        no address candidate is declared."""
        assert "address" not in CRIME_FIELD_MAP
        assert "incident_address" not in CRIME_FIELD_MAP

    def test_no_borough_candidate_on_permits_or_complaints(self):
        """No neighborhood/district column exists on either layer (Omaha
        discipline): division resolution is coordinate-based at ingest and
        source_neighborhood passes through as None."""
        assert "borough" not in PERMITS_FIELD_MAP
        assert "borough" not in COMPLAINTS_311_FIELD_MAP

    def test_pii_columns_never_become_candidates(self):
        mapped = {c for values in FIELD_MAP.values() for m in values.values() for c in m}
        assert mapped
        for values in FIELD_MAP.values():
            for cols in values.values():
                for col in cols:
                    assert col not in DROPPED_PII_COLUMNS
        # The contractor block + ProjectName (owner/trust names) are exactly
        # what is dropped.
        assert {
            "ContractorCompanyName",
            "ContractorLicNum",
            "ContractorPhone",
            "ContractorAddress1",
            "ContractorZip",
            "ContractorEmail",
            "ProjectName",
        } <= set(DROPPED_PII_COLUMNS)


class TestTempePermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_PERMIT_8597093, _PERMITS_DATE_FIELDS)
        assert record["latitude"] == pytest.approx(33.40924937)
        assert record["longitude"] == pytest.approx(-111.93800933)

    def test_flatten_iso_normalizes_every_esri_date(self):
        record = _flatten(_PERMIT_8597093, _PERMITS_DATE_FIELDS)
        assert record["AppliedDateDtm"] == _APPLIED_ISO
        assert record["IssuedDateDtm"] == _APPLIED_ISO
        # Future-date sentinels normalize too — they just never feed an
        # event date field (ExpiresDate is not an issuance candidate).
        assert record["ExpiresDateDtm"] == _EXPIRES_ISO
        # Plain string twins stay untouched (producer parses "YYYY-MM-DD").
        assert record["AppliedDate"] == "2026-08-26"
        assert record["IssuedDate"] == "2026-08-26"

    def test_encanto_fixture_parses_through_the_producer(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            _flatten(_PERMIT_8597093, _PERMITS_DATE_FIELDS), city_id="tempe"
        )
        assert event is not None
        assert event.city_id == "tempe"
        assert event.job_id == "BP261951"
        assert event.status == "Issued"
        assert event.estimated_cost == pytest.approx(5500.0)
        assert event.address_street == "101 E ENCANTO DR"
        assert event.zipcode == "85281"
        assert event.latitude == pytest.approx(33.40924937)
        assert event.longitude == pytest.approx(-111.93800933)
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat() == _APPLIED_ISO
        assert event.filing_date is not None
        assert event.filing_date.isoformat() == _APPLIED_ISO
        assert event.source_neighborhood is None
        assert event.bbl is None

    def test_hudson_fixture_indexes_h3_and_sits_in_metro(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            _flatten(_PERMIT_8597094, _PERMITS_DATE_FIELDS), city_id="tempe"
        )
        assert event is not None
        assert event.job_id == "BP261953"
        assert event.estimated_cost == pytest.approx(4000.0)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_tempe_metro(event.latitude, event.longitude)

    def test_fairmont_fixture_distinguishes_filing_from_issuance(
        self, permits, monkeypatch
    ):
        """Applied 2026-08-25 / issued 2026-08-26 — the map keeps the two
        event dates distinct."""
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            _flatten(_PERMIT_8597091, _PERMITS_DATE_FIELDS), city_id="tempe"
        )
        assert event is not None
        assert event.filing_date.isoformat() == _APPLIED_8597091_ISO
        assert event.issuance_date.isoformat() == _APPLIED_ISO

    def test_co_newest_watermark_rows_share_their_date(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        events = [
            permits.parse_socrata_row(
                _flatten(f, _PERMITS_DATE_FIELDS), city_id="tempe"
            )
            for f in (_PERMIT_8597093, _PERMIT_8597094)
        ]
        assert all(e is not None for e in events)
        assert {e.issuance_date.isoformat() for e in events} == {_APPLIED_ISO}
        # Distinct permits occupy distinct res-9 cells.
        assert len({e.h3_res9 for e in events}) == 2

    def test_alteration_type_text_classifies_as_a2(self, permits, monkeypatch):
        """'Residential Addition/Alteration/Remodel' contains ALTERATION —
        the shared classification lands it on A2 honestly."""
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            _flatten(_PERMIT_8597093, _PERMITS_DATE_FIELDS), city_id="tempe"
        )
        assert event is not None
        assert event.job_type == JobType.A2

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_PERMIT_8597093, _PERMITS_DATE_FIELDS)
        record.pop("PermitNum")
        event = permits.parse_socrata_row(record, city_id="tempe")
        assert event is not None
        assert event.job_id == "8597093"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_PERMIT_8597093, _PERMITS_DATE_FIELDS)
        record.pop("PermitNum")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="tempe") is None

    def test_status_falls_back_to_the_producer_default(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_PERMIT_8597093, _PERMITS_DATE_FIELDS)
        record.pop("StatusCurrent")
        event = permits.parse_socrata_row(record, city_id="tempe")
        assert event is not None
        assert event.status == "ISSUED"

    def test_geometry_less_row_resolves_through_the_geocode_fallback(
        self, permits, monkeypatch
    ):
        """3.0% of live permit rows carry no Latitude/Longitude. Rows
        arriving without geometry or attribute degrees resolve via the ADR
        0004 geocode supplement (needs_geocode=True). Call-args/counts are
        spine-volatile and not asserted — only the event outcome."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_PERMIT_8597093, _PERMITS_DATE_FIELDS)
        record.pop("latitude")
        record.pop("longitude")
        record.pop("Latitude")
        record.pop("Longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (33.4267, -111.9398),
        )
        event = permits.parse_socrata_row(record, city_id="tempe")
        assert event is not None
        assert event.city_id == "tempe"
        assert event.job_id == "BP261951"
        assert event.latitude == pytest.approx(33.4267)
        assert event.longitude == pytest.approx(-111.9398)
        assert event.h3_res7 is not None

    def test_geometry_less_row_dropped_when_geocode_fails(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_PERMIT_8597094, _PERMITS_DATE_FIELDS)
        record.pop("latitude")
        record.pop("longitude")
        record.pop("Latitude")
        record.pop("Longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="tempe") is None


class TestTempe311Parsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_COMPLAINT_261, _COMPLAINTS_DATE_FIELDS)
        assert record["latitude"] == pytest.approx(33.42788100000007)
        assert record["longitude"] == pytest.approx(-111.89801699999998)
        # X_COORD/Y_COORD degree duplicates ride along unmapped.
        assert record["X_COORD"] == -111.898017
        assert record["Y_COORD"] == 33.427881

    def test_sign_fixture_parses_through_the_producer(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints.parse_socrata_row(
            _flatten(_COMPLAINT_261, _COMPLAINTS_DATE_FIELDS), city_id="tempe"
        )
        assert event is not None
        assert event.city_id == "tempe"
        assert event.incident_id == "CM260999"
        assert event.complaint_type == "Sign"
        assert event.status == "Under Investigation"
        assert event.incident_address == "214 S ROCKFORD DR, TEMPE, AZ, 85281"
        assert event.created_date is not None
        assert event.created_date.isoformat() == _COMPLAINT_OPEN_ISO
        assert event.closed_date is None
        assert event.latitude == pytest.approx(33.42788100000007)
        assert event.longitude == pytest.approx(-111.89801699999998)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert event.zipcode == ""
        assert event.source_neighborhood is None

    def test_zoning_fixture_sits_in_metro(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints.parse_socrata_row(
            _flatten(_COMPLAINT_262, _COMPLAINTS_DATE_FIELDS), city_id="tempe"
        )
        assert event is not None
        assert event.incident_id == "CM261001"
        assert event.complaint_type == "Zoning"
        assert is_in_tempe_metro(event.latitude, event.longitude)

    def test_co_newest_cases_share_the_june_watermark(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        events = [
            complaints.parse_socrata_row(
                _flatten(f, _COMPLAINTS_DATE_FIELDS), city_id="tempe"
            )
            for f in (_COMPLAINT_261, _COMPLAINT_262, _COMPLAINT_264)
        ]
        assert all(e is not None for e in events)
        assert {e.created_date.isoformat() for e in events} == {_COMPLAINT_OPEN_ISO}
        # Distinct cases occupy distinct res-9 cells.
        assert len({e.h3_res9 for e in events}) == 3

    def test_incident_id_falls_back_to_the_uuid(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_COMPLAINT_262, _COMPLAINTS_DATE_FIELDS)
        record.pop("CaseNo")
        event = complaints.parse_socrata_row(record, city_id="tempe")
        assert event is not None
        assert event.incident_id == "7ce05e96-b786-4006-8101-e27432d275d6"

    def test_row_without_any_id_is_dropped(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_COMPLAINT_262, _COMPLAINTS_DATE_FIELDS)
        record.pop("CaseNo")
        record.pop("Id")
        assert complaints.parse_socrata_row(record, city_id="tempe") is None

    def test_zero_coordinate_sentinel_row_is_dropped(self, complaints, monkeypatch):
        """Two live rows carry (0,0) coordinates — the producer's 0/0 guard
        must drop them instead of filing them in the Gulf of Guinea."""
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_COMPLAINT_264, _COMPLAINTS_DATE_FIELDS)
        record["geometry"] = {"x": 0.0, "y": 0.0}
        record["X_COORD"] = 0
        record["Y_COORD"] = 0
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert complaints.parse_socrata_row(record, city_id="tempe") is None

    def test_geometry_less_row_resolves_through_the_geocode_fallback(
        self, complaints, monkeypatch
    ):
        """needs_geocode=True on the single-string Address (ADR 0004). The
        X_COORD/Y_COORD duplicates must NOT silently satisfy the coordinate
        chain — only the declared geocode supplement may fill the gap."""
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_COMPLAINT_261, _COMPLAINTS_DATE_FIELDS)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (33.4279, -111.8980),
        )
        event = complaints.parse_socrata_row(record, city_id="tempe")
        assert event is not None
        assert event.latitude == pytest.approx(33.4279)
        assert event.longitude == pytest.approx(-111.8980)
        assert event.h3_res7 is not None

    def test_geometry_less_row_dropped_when_geocode_fails(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_COMPLAINT_262, _COMPLAINTS_DATE_FIELDS)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert complaints.parse_socrata_row(record, city_id="tempe") is None


class TestTempeCrimeParsing:
    @pytest.fixture
    def crime(self):
        with patch("src.producers.crime_incidents_producer.BaseKafkaProducer"):
            from src.producers.crime_incidents_producer import CrimeIncidentsProducer

            return CrimeIncidentsProducer()

    def test_flatten_lifts_the_outsr4326_geometry_to_degrees(self):
        record = _flatten(_OFFENSE_380316, _CRIME_DATE_FIELDS)
        assert record["latitude"] == pytest.approx(33.3955111585924)
        assert record["longitude"] == pytest.approx(-111.93964625660145)
        # The State Plane attribute pair rides along unmapped — never degrees.
        assert record["XCoordinate"] == 692990
        assert record["YCoordinate"] == 871431

    def test_flatten_iso_normalizes_the_watermark_only(self):
        record = _flatten(_OFFENSE_380290, _CRIME_DATE_FIELDS)
        assert record["OccurrenceDatetime"] == "2026-08-27T22:59:00+00:00"

    def test_assault_fixture_parses_part1(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(
            _flatten(_OFFENSE_380261, _CRIME_DATE_FIELDS), city_id="tempe"
        )
        assert event is not None
        assert event.city_id == "tempe"
        assert event.incident_id == "TE202686933"  # CHAR padding stripped
        assert event.offense_type.strip() == "[13B] ASSAULT [DV]"
        assert event.offense_class == "PART1"
        assert event.occurred_date is not None
        assert event.occurred_date.isoformat() == "2026-08-27T21:14:00+00:00"
        assert event.source_neighborhood == "Diablo/Double Butte"
        # ADR-0004: no geocode supplement — coordinates only.
        assert event.latitude == pytest.approx(33.421945)
        assert event.longitude == pytest.approx(-111.96092)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None

    def test_info_fixture_classifies_part2(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(
            _flatten(_OFFENSE_380290, _CRIME_DATE_FIELDS), city_id="tempe"
        )
        assert event is not None
        assert event.incident_id == "TE202686968"
        assert event.offense_class == "PART2"
        assert event.source_neighborhood == "Rio Salado/DT/ASU/NW Neighborhoods"
        assert is_in_tempe_metro(event.latitude, event.longitude)

    def test_offense_null_row_falls_to_unknown_part2(self, crime, monkeypatch):
        """OffenseCustom null on the newest row (380316): offense_type lands
        on Unknown and classifies Part-2 honestly."""
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(
            _flatten(_OFFENSE_380316, _CRIME_DATE_FIELDS), city_id="tempe"
        )
        assert event is not None
        assert event.incident_id == "TE202686976"
        assert event.offense_type == "Unknown"
        assert event.offense_class == "PART2"
        assert event.occurred_date.isoformat() == _OCCURRED_ISO

    def test_geometry_less_row_falls_back_to_wgs84_attributes(
        self, crime, monkeypatch
    ):
        """61 live rows (0.016%) carry no Latitude/Longitude attributes and
        others lose geometry server-side. The declared WGS84 attribute pair
        must fill the gap WITHOUT any geocode call (ADR-0004 coordinates
        already present in the attribute pair)."""
        _patch_resolve(monkeypatch, "crime")
        feature = {
            "attributes": dict(_OFFENSE_380261["attributes"]),
            "geometry": None,
        }
        record = _flatten(feature, _CRIME_DATE_FIELDS)
        assert "latitude" not in record  # geometry was null
        event = crime.parse_socrata_row(record, city_id="tempe")
        assert event is not None
        assert event.latitude == pytest.approx(33.421945)
        assert event.longitude == pytest.approx(-111.96092)

    def test_row_without_any_coordinates_is_dropped(self, crime, monkeypatch):
        """Neither geometry nor attribute degrees: the row drops (no
        geocode on obfuscated addresses)."""
        _patch_resolve(monkeypatch, "crime")
        feature = {
            "attributes": dict(_OFFENSE_380261["attributes"]),
            "geometry": None,
        }
        record = _flatten(feature, _CRIME_DATE_FIELDS)
        record.pop("Latitude")
        record.pop("Longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert crime.parse_socrata_row(record, city_id="tempe") is None

    def test_row_without_any_id_is_dropped(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        record = _flatten(_OFFENSE_380261, _CRIME_DATE_FIELDS)
        record["PrimaryKey"] = "                    "  # padding-only id
        record.pop("OBJECTID")
        assert crime.parse_socrata_row(record, city_id="tempe") is None

    def test_zero_coordinate_row_is_dropped(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        record = _flatten(_OFFENSE_380261, _CRIME_DATE_FIELDS)
        record["Latitude"] = 0.0
        record["Longitude"] = 0.0
        record.pop("latitude")
        record.pop("longitude")
        assert crime.parse_socrata_row(record, city_id="tempe") is None


class TestTempeFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_tempe_dataset("permits")
        assert spec.platform == "arcgis"
        assert spec.endpoint == TEMPE_PERMITS_ENDPOINT
        assert spec.watermark_col == "AppliedDateDtm"
        assert spec.id_keys == ["PermitNum", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "AppliedDateDtm DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Tempe, AZ"
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"
        # Native WGS84 layer — no state-plane transform contract.
        assert spec.state_plane_crs is None

    def test_complaints_spec_matches_live_layer(self):
        spec = get_tempe_dataset("311")
        assert spec.platform == "arcgis"
        assert spec.endpoint == TEMPE_COMPLAINTS_311_ENDPOINT
        assert spec.watermark_col == "CaseOpenDate"
        assert spec.id_keys == ["CaseNo", "Id"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 30
        assert spec.order_by == "CaseOpenDate DESC"
        assert spec.interval_seconds == 180.0
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Tempe, AZ"
        assert spec.field_map == COMPLAINTS_311_FIELD_MAP
        assert spec.topic == "raw.municipal.311"
        assert spec.state_plane_crs is None

    def test_crime_spec_matches_live_layer(self):
        spec = get_tempe_dataset("crime")
        assert spec.platform == "arcgis"
        assert spec.endpoint == TEMPE_CRIME_ENDPOINT
        assert spec.watermark_col == "OccurrenceDatetime"
        assert spec.id_keys == ["PrimaryKey", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "OccurrenceDatetime DESC"
        assert spec.interval_seconds == 1800.0
        assert spec.needs_geocode is False
        assert spec.field_map == CRIME_FIELD_MAP
        assert spec.topic == "raw.municipal.crime"
        # Mixed-CRS layer: the transform contract documents the store SR.
        assert spec.state_plane_crs == "EPSG:2223"
        assert spec.state_plane_units == "ft"
        assert spec.state_plane_x_col == "XCoordinate"
        assert spec.state_plane_y_col == "YCoordinate"

    def test_registered_feed_set_is_the_verified_trio(self):
        assert set(TEMPE_FEED_SPECS) == {"permits", "311", "crime"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_tempe_dataset("sla")
        assert "tempe" in str(exc.value)
        assert "crime" in str(exc.value)

    def test_endpoints_are_the_probed_featureservers(self):
        assert "services.arcgis.com/lQySeXwbBg53XWDi" in TEMPE_PERMITS_ENDPOINT
        assert "building_permits/FeatureServer/0" in TEMPE_PERMITS_ENDPOINT
        assert "code_complaints/FeatureServer/0" in TEMPE_COMPLAINTS_311_ENDPOINT
        assert (
            "General_Offenses_(Open_Data)/FeatureServer/0" in TEMPE_CRIME_ENDPOINT
        )
