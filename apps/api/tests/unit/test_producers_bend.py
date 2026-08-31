"""Unit tests for the Bend, OR leaf (US-237): spatial module + field
maps + producer parse wiring.

Bend is a FOUR-FEED metro on the city ArcGIS Server: PERMITS
(Permit_Applications_Point/FeatureServer/0, 165k rows), SLA
(License_Application_Points_Business_Registrations, 5.9k rows),
COMPLAINTS_311 (Code_Enforcement_Cases_Polygon, 17k rows), and CRIME
(Public_Calls, 451k rows). All four are ArcGIS FeatureServers on
services5.arcgis.com/JisFYcK2mIVg9ueP.

Tests pass WITHOUT a spine registration (no CityId.BEND, no REGISTRY
assertions — "bend" stays a plain string). Spine-stable per the leaf
contract: no division/borough-resolution assertions and no geocode-hook
call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from each FeatureServer/0
(newest rows via ``orderByFields=<watermark> DESC`` at ``outSR=4326``).
Fixtures are RAW ArcGIS features (attributes + geometry); the tests run the
real ``ArcGISClient._flatten_feature`` lift — geometry to latitude/longitude,
epoch-ms to ISO — before parsing, exactly as the live producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_bend import (
    COMPLAINTS_311_FIELD_MAP,
    CRIME_FIELD_MAP,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.spatial.cities.bend import (
    BEND_CITY_ID,
    BEND_COMPLAINTS_311_ENDPOINT,
    BEND_CRIME_ENDPOINT,
    BEND_DIVISION_BBOXES,
    BEND_DIVISIONS,
    BEND_FEED_SPECS,
    BEND_GEOCODE_CONTEXT,
    BEND_METRO_BBOX,
    BEND_PERMITS_ENDPOINT,
    BEND_SLA_ENDPOINT,
    BEND_SUBMARKETS,
    REGISTRATION,
    get_bend_dataset,
    is_in_bend_metro,
    is_in_greater_bend_metro,
)


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _flatten(feature, date_fields):
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, date_fields)


# =========================================================================
# PERMITS — Permit_Applications_Point (FeatureServer/0)
# Newest 3 rows by ApplicationDate DESC, outSR=4326.
# Watermark: ApplicationDate = 1787788800000 = 2026-08-27T00:00:00+00:00
# =========================================================================
_PERMIT_FEATURE_1 = {
    "attributes": {
        "OBJECTID": 338663,
        "ApplicationNumber": "PRMH202605802",
        "ApplicationDate": 1787788800000,
        "IssueDate": None,
        "DateFinaled": None,
        "ProjectValuation": None,
        "ApplicationStatus": "P",
        "ApplicationType": "MH",
        "TypeDesc": "Mechanical",
        "Address": "2485 NW AWBREY RD, BEND, OR 97703",
        "Units": 1,
        "SQFT": 1,
        "StatusDesc": "Pending",
    },
    "geometry": {
        "x": -121.31792856284218,
        "y": 44.07235302394858,
    },
}

_PERMIT_FEATURE_2 = {
    "attributes": {
        "OBJECTID": 338664,
        "ApplicationNumber": "PREL202605803",
        "ApplicationDate": 1787788800000,
        "IssueDate": None,
        "DateFinaled": None,
        "ProjectValuation": None,
        "ApplicationStatus": "P",
        "ApplicationType": "EL",
        "TypeDesc": "Electrical",
        "Address": "2626 NW ORDWAY AVE, BEND, OR 97703",
        "Units": 1,
        "SQFT": 1,
        "StatusDesc": "Pending",
    },
    "geometry": {
        "x": -121.35522061291539,
        "y": 44.05982624828546,
    },
}

_PERMIT_FEATURE_3 = {
    "attributes": {
        "OBJECTID": 338665,
        "ApplicationNumber": "PRFR202605805",
        "ApplicationDate": 1787788800000,
        "IssueDate": None,
        "DateFinaled": None,
        "ProjectValuation": 3770,
        "ApplicationStatus": "INPS",
        "ApplicationType": "FR",
        "TypeDesc": "Fire Sprinkler/Alarm",
        "Address": "1160 SW SIMPSON AVE, STE:100, BEND, OR 97702",
        "Units": None,
        "SQFT": 9,
        "StatusDesc": "Intake Pre-Screen",
    },
    "geometry": {
        "x": -121.32858776718815,
        "y": 44.048543509051704,
    },
}

_APPLICATIONDATE_ISO = "2026-08-27T00:00:00+00:00"

# =========================================================================
# SLA — License_Application_Points (Business_Registrations)
# Newest 3 rows by OBJECTID DESC, outSR=4326.
# Watermark: LicenseExpirationDate
# =========================================================================
_SLA_FEATURE_1 = {
    "attributes": {
        "OBJECTID": 150694,
        "BusinessNumber": "LCBR21-16240",
        "BusinessName": "WELL BUILT CONSTRUCTION LLC",
        "BusinessTypeCode": "BR",
        "BusinessTypeDesc": "Business Registration",
        "BusinessStatusCode": "A",
        "BusinessStatusDesc": "Active",
        "BusinessLocation": "2005 NW 6TH ST, BEND, OR 97703",
        "LicenseNumber": "0001202405401",
        "LicenseStatusCode": "EXP",
        "LicenseStatusDesc": "Expired",
        "LicenseExpirationDate": 1756710000000,
        "BR_BusinessOpenedDate": 1505199600000,
        "ClassDescription1": "For Profit Business",
        "ClassDescription2": "236115 - General Contractors",
    },
    "geometry": {
        "x": -121.32075454303641,
        "y": 44.06712833042855,
    },
}

_SLA_FEATURE_2 = {
    "attributes": {
        "OBJECTID": 150693,
        "BusinessNumber": "LCBR21-16240",
        "BusinessName": "WELL BUILT CONSTRUCTION LLC",
        "BusinessTypeCode": "BR",
        "BusinessTypeDesc": "Business Registration",
        "BusinessStatusCode": "A",
        "BusinessStatusDesc": "Active",
        "BusinessLocation": "2005 NW 6TH ST, BEND, OR 97703",
        "LicenseNumber": "0001202605726",
        "LicenseStatusCode": "ISS",
        "LicenseStatusDesc": "Issued",
        "LicenseExpirationDate": 1819782000000,
        "BR_BusinessOpenedDate": 1505199600000,
        "ClassDescription1": "For Profit Business",
        "ClassDescription2": "236115 - General Contractors",
    },
    "geometry": {
        "x": -121.32075454303641,
        "y": 44.06712833042855,
    },
}

_SLA_FEATURE_3 = {
    "attributes": {
        "OBJECTID": 150692,
        "BusinessNumber": "LCBR21-12748",
        "BusinessName": "CLIFF CRUSON FLOORING",
        "BusinessTypeCode": "BR",
        "BusinessTypeDesc": "Business Registration",
        "BusinessStatusCode": "A",
        "BusinessStatusDesc": "Active",
        "BusinessLocation": "60867 SAWTOOTH MOUNTAIN LN, BEND, OR 97702",
        "LicenseNumber": "0001202605737",
        "LicenseStatusCode": "ISS",
        "LicenseStatusDesc": "Issued",
        "LicenseExpirationDate": 1819782000000,
        "BR_BusinessOpenedDate": 1409814000000,
        "ClassDescription1": "For Profit Business",
        "ClassDescription2": "238330 - Flooring Contractors",
    },
    "geometry": {
        "x": -121.31989949982918,
        "y": 44.009774029222854,
    },
}

_SLA_EXPIRY_ISO = "2027-09-01T07:00:00+00:00"

# =========================================================================
# COMPLAINTS_311 — Code_Enforcement_Cases_Polygon_(Public) (FeatureServer/0)
# Newest 3 rows by CaseReportedDate DESC, outSR=4326.
# Watermark: CaseReportedDate = 1787868997000 = 2026-08-28T06:16:37+00:00
# =========================================================================
_311_FEATURE_1 = {
    "attributes": {
        "OBJECTID": 474710,
        "CaseNumber": "CESIGN202601226",
        "CaseReportedDate": 1787868997000,
        "TypeDescription": "Signage",
        "CaseStatus": "NOV",
        "StatusDesc": "Notice/Order Sent",
        "Address": "442 NW DELAWARE AVE, BEND, OR 97703",
    },
    "geometry": {
        "rings": [
            [
                [-121.313647984094, 44.053551810178],
                [-121.31364744526, 44.0532393746749],
                [-121.313878051752, 44.0532391950187],
                [-121.313878450738, 44.0535516288094],
                [-121.313647984094, 44.053551810178],
            ]
        ]
    },
}

_311_FEATURE_2 = {
    "attributes": {
        "OBJECTID": 474709,
        "CaseNumber": "CESIGN202601225",
        "CaseReportedDate": 1787866498000,
        "TypeDescription": "Signage",
        "CaseStatus": "NOV",
        "StatusDesc": "Notice/Order Sent",
        "Address": "443 NW DELAWARE AVE, BEND, OR 97703",
    },
    "geometry": {
        "rings": [
            [
                [-121.313647164818, 44.0530747886684],
                [-121.313646653469, 44.0527623547062],
                [-121.313877442816, 44.0527621737571],
                [-121.313877841808, 44.0530746085143],
                [-121.313647164818, 44.0530747886684],
            ]
        ]
    },
}

_311_FEATURE_3 = {
    "attributes": {
        "OBJECTID": 474708,
        "CaseNumber": "CEFW202601224",
        "CaseReportedDate": 1787864811000,
        "TypeDescription": "Flammable Vegetation ",
        "CaseStatus": "O",
        "StatusDesc": "Open",
        "Address": "61505 TANYA DR, BEND, OR 97702",
    },
    "geometry": {
        "rings": [
            [
                [-121.32534371227, 44.0338546183911],
                [-121.325342897983, 44.0333645157006],
                [-121.325951264968, 44.0333656985057],
                [-121.325952131877, 44.0338864834822],
                [-121.325481518506, 44.0338856504641],
                [-121.325405168069, 44.0338855156663],
                [-121.32534376226, 44.0338854005657],
                [-121.32534371227, 44.0338546183911],
            ]
        ]
    },
}

_CASE_REPORTED_ISO = "2026-08-27T22:16:37+00:00"

# =========================================================================
# CRIME — Public_Calls (FeatureServer/0)
# Newest 3 rows by CreateDateTime DESC, outSR=4326.
# Watermark: CreateDateTime = 1787830998000 = 2026-08-27T11:43:18+00:00
# =========================================================================
_CRIME_FEATURE_1 = {
    "attributes": {
        "OBJECTID": 879549,
        "IncidentNumber": "2026-00047504",
        "CreateDateTime": 1787830998000,
        "CallType": "UEMV Unauthorized Entry into Veh",
        "CallAddress": "300-399 NE THURSTON AVE",
        "Neighborhood": "Orchard District",
        "Hour": 4,
        "Day_of_Week": "Thursday",
    },
    "geometry": {
        "x": -121.30323761161092,
        "y": 44.06951471894193,
    },
}

_CRIME_FEATURE_2 = {
    "attributes": {
        "OBJECTID": 879537,
        "IncidentNumber": "2026-00047503",
        "CreateDateTime": 1787827690000,
        "CallType": "Suspicious Circumstances",
        "CallAddress": "1500-1599 NE 3RD ST",
        "Neighborhood": "Orchard District",
        "Hour": 3,
        "Day_of_Week": "Thursday",
    },
    "geometry": {
        "x": -121.30252750056536,
        "y": 44.06446762065013,
    },
}

_CRIME_FEATURE_3 = {
    "attributes": {
        "OBJECTID": 879564,
        "IncidentNumber": "2026-00047502",
        "CreateDateTime": 1787821887000,
        "CallType": "Suspicious Circumstances",
        "CallAddress": "2600-2699 NE DIVISION ST",
        "Neighborhood": "River West",
        "Hour": 2,
        "Day_of_Week": "Thursday",
    },
    "geometry": {
        "x": -121.30537707163096,
        "y": 44.07642100201256,
    },
}

_CREATED_ISO = "2026-08-27T11:43:18+00:00"


class TestBendSpatial:
    def test_city_id_constant_is_the_leaf_string(self):
        assert BEND_CITY_ID == "bend"

    def test_metro_bbox_sanity(self):
        assert BEND_METRO_BBOX["min_lat"] < BEND_METRO_BBOX["max_lat"]
        assert BEND_METRO_BBOX["min_lng"] < BEND_METRO_BBOX["max_lng"]

    def test_is_in_bend_metro_rejects_missing_coordinates(self):
        assert is_in_bend_metro(None, None) is False
        assert is_in_bend_metro(44.0575, None) is False
        assert is_in_bend_metro(None, -121.3150) is False

    def test_is_in_bend_metro_rejects_other_cities(self):
        assert is_in_bend_metro(44.2726, -121.1739) is False   # Redmond
        assert is_in_bend_metro(44.9429, -123.0351) is False   # Salem
        assert is_in_bend_metro(45.5152, -122.6784) is False   # Portland
        assert is_in_bend_metro(44.2900, -121.5500) is False   # Sisters

    def test_downtown_anchors_are_contained(self):
        assert is_in_bend_metro(44.0575, -121.3150)  # Downtown
        assert is_in_bend_metro(44.0480, -121.3270)  # Old Mill District
        assert is_in_bend_metro(44.0720, -121.3450)  # Northwest Crossing
        assert is_in_bend_metro(44.0690, -121.3030)  # Orchard District

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (
            _PERMIT_FEATURE_1, _PERMIT_FEATURE_2, _PERMIT_FEATURE_3,
            _SLA_FEATURE_1, _SLA_FEATURE_3,
            _311_FEATURE_1, _311_FEATURE_2, _311_FEATURE_3,
            _CRIME_FEATURE_1, _CRIME_FEATURE_2, _CRIME_FEATURE_3,
        ):
            geom = feature["geometry"]
            if "rings" in geom:
                ys = [pt[1] for part in geom["rings"] for pt in part]
                xs = [pt[0] for part in geom["rings"] for pt in part]
                assert is_in_bend_metro(
                    sum(ys) / len(ys), sum(xs) / len(xs)
                )
            else:
                assert is_in_bend_metro(geom["y"], geom["x"])

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in BEND_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= BEND_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= BEND_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= BEND_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= BEND_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in BEND_SUBMARKETS.items():
            bbox = BEND_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in BEND_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(BEND_SUBMARKETS)

    def test_submarkets_carry_the_bend_city_id(self):
        assert {m.city_id for m in BEND_SUBMARKETS.values()} == {"bend"}

    def test_registration_shape(self):
        assert REGISTRATION.metro_bbox is BEND_METRO_BBOX
        assert REGISTRATION.submarkets is BEND_SUBMARKETS
        assert REGISTRATION.division_bboxes is BEND_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_bend_metro
        assert len(REGISTRATION.divisions) == 6
        assert len(BEND_SUBMARKETS) == 10

    def test_required_real_neighborhoods_present(self):
        assert {"Downtown", "Old Mill District", "Westside & Century Drive",
                "Northwest Crossing", "Awbrey Butte", "Orchard District",
                "River West", "Old Farm District", "Southern Crossing",
                "Larkspur"} <= set(BEND_SUBMARKETS)

    def test_greater_metro_alias(self):
        assert is_in_greater_bend_metro is is_in_bend_metro


class TestBendFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["ApplicationNumber", "OBJECTID"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["IssueDate"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["ApplicationDate"]
        assert PERMITS_FIELD_MAP["cost"] == ["ProjectValuation"]
        assert PERMITS_FIELD_MAP["status"] == ["ApplicationStatus", "StatusDesc", "OverallStatus"]
        assert PERMITS_FIELD_MAP["job_type"] == ["TypeDesc", "ApplicationType", "BldgUse"]
        assert PERMITS_FIELD_MAP["address_street"] == ["Address"]
        assert PERMITS_FIELD_MAP["proposed_units"] == ["Units"]

    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["LicenseNumber", "BusinessNumber", "OBJECTID"]
        assert SLA_FIELD_MAP["license_type"] == ["BusinessTypeDesc", "ClassDescription1", "BusinessTypeCode"]
        assert SLA_FIELD_MAP["dba"] == ["BusinessName"]
        assert SLA_FIELD_MAP["premises_name"] == ["BusinessName"]
        assert SLA_FIELD_MAP["effective_date"] == ["BR_BusinessOpenedDate"]
        assert SLA_FIELD_MAP["expiration_date"] == ["LicenseExpirationDate"]
        assert SLA_FIELD_MAP["status"] == ["BusinessStatusDesc", "LicenseStatusDesc"]
        assert SLA_FIELD_MAP["address_street"] == ["BusinessLocation"]

    def test_311_map_reads_live_columns(self):
        assert COMPLAINTS_311_FIELD_MAP["incident_id"] == ["CaseNumber", "OBJECTID"]
        assert COMPLAINTS_311_FIELD_MAP["complaint_type"] == ["TypeDescription"]
        assert COMPLAINTS_311_FIELD_MAP["created_date"] == ["CaseReportedDate"]
        assert COMPLAINTS_311_FIELD_MAP["status"] == ["CaseStatus", "StatusDesc"]
        assert COMPLAINTS_311_FIELD_MAP["incident_address"] == ["Address"]

    def test_crime_map_reads_live_columns(self):
        assert CRIME_FIELD_MAP["incident_id"] == ["IncidentNumber", "OBJECTID"]
        assert CRIME_FIELD_MAP["offense_type"] == ["CallType"]
        assert CRIME_FIELD_MAP["reported_date"] == ["CreateDateTime"]
        assert CRIME_FIELD_MAP["address"] == ["CallAddress"]
        assert CRIME_FIELD_MAP["incident_address"] == ["CallAddress"]
        assert CRIME_FIELD_MAP["borough"] == ["Neighborhood"]

    def test_field_map_module_shape(self):
        assert set(FIELD_MAP) == {"permits", "sla", "311", "crime"}
        for feed in ("permits", "sla", "311", "crime"):
            assert isinstance(FIELD_MAP[feed], dict)
            for canonical, candidates in FIELD_MAP[feed].items():
                assert isinstance(canonical, str)
                assert isinstance(candidates, list)

    def test_geocode_context(self):
        assert GEOCODE_CONTEXT == "Bend, OR"
        assert BEND_GEOCODE_CONTEXT == "Bend, OR"

    def test_no_coordinate_candidates_geometry_lift_is_sole_source(self):
        """All four feeds rely on the outSR=4326 geometry lift. No
        latitude/longitude attribute candidates are declared — the
        State Plane attributes (store SR 2270) stay server-side."""
        for fm in (PERMITS_FIELD_MAP, SLA_FIELD_MAP, COMPLAINTS_311_FIELD_MAP, CRIME_FIELD_MAP):
            assert "latitude" not in fm
            assert "longitude" not in fm

    def test_permits_first_mapped_resolves_live_rows(self):
        for feature in (_PERMIT_FEATURE_1, _PERMIT_FEATURE_2):
            attrs = feature["attributes"]
            assert first_mapped(attrs, PERMITS_FIELD_MAP, "job_id") is not None
            assert first_mapped(attrs, PERMITS_FIELD_MAP, "address_street") is not None
            assert first_mapped(attrs, PERMITS_FIELD_MAP, "filing_date") is not None
            assert first_mapped(attrs, PERMITS_FIELD_MAP, "proposed_units") is not None

    def test_sla_first_mapped_resolves_live_rows(self):
        for feature in (_SLA_FEATURE_1, _SLA_FEATURE_2, _SLA_FEATURE_3):
            attrs = feature["attributes"]
            assert first_mapped(attrs, SLA_FIELD_MAP, "license_id") is not None
            assert first_mapped(attrs, SLA_FIELD_MAP, "dba") is not None
            assert first_mapped(attrs, SLA_FIELD_MAP, "expiration_date") is not None

    def test_311_first_mapped_resolves_live_rows(self):
        for feature in (_311_FEATURE_1, _311_FEATURE_2, _311_FEATURE_3):
            attrs = feature["attributes"]
            assert first_mapped(attrs, COMPLAINTS_311_FIELD_MAP, "incident_id") is not None
            assert first_mapped(attrs, COMPLAINTS_311_FIELD_MAP, "complaint_type") is not None
            assert first_mapped(attrs, COMPLAINTS_311_FIELD_MAP, "created_date") is not None
            assert first_mapped(attrs, COMPLAINTS_311_FIELD_MAP, "incident_address") is not None

    def test_crime_first_mapped_resolves_live_rows(self):
        for feature in (_CRIME_FEATURE_1, _CRIME_FEATURE_2, _CRIME_FEATURE_3):
            attrs = feature["attributes"]
            assert first_mapped(attrs, CRIME_FIELD_MAP, "incident_id") is not None
            assert first_mapped(attrs, CRIME_FIELD_MAP, "offense_type") is not None
            assert first_mapped(attrs, CRIME_FIELD_MAP, "borough") is not None
            assert first_mapped(attrs, CRIME_FIELD_MAP, "address") is not None


class TestBendPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_PERMIT_FEATURE_1, {"ApplicationDate", "IssueDate", "DateFinaled"})
        assert record["latitude"] == pytest.approx(44.07235302394858)
        assert record["longitude"] == pytest.approx(-121.31792856284218)

    def test_flatten_iso_normalizes_date_columns(self):
        record = _flatten(_PERMIT_FEATURE_1, {"ApplicationDate", "IssueDate", "DateFinaled"})
        assert record["ApplicationDate"] == _APPLICATIONDATE_ISO
        assert record["IssueDate"] is None
        assert record["ApplicationStatus"] == "P"

    def test_newest_fixture_parses_through_producer(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            _flatten(_PERMIT_FEATURE_1, {"ApplicationDate", "IssueDate", "DateFinaled"}),
            city_id="bend",
        )
        assert event is not None
        assert event.city_id == "bend"
        assert event.job_id == "PRMH202605802"
        assert event.address_street == "2485 NW AWBREY RD, BEND, OR 97703"
        assert event.latitude == pytest.approx(44.07235302394858)
        assert event.longitude == pytest.approx(-121.31792856284218)
        assert event.estimated_cost == 0.0
        assert event.proposed_dwelling_units == 1

    def test_second_fixture_h3_and_containment(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            _flatten(_PERMIT_FEATURE_2, {"ApplicationDate", "IssueDate", "DateFinaled"}),
            city_id="bend",
        )
        assert event is not None
        assert event.job_id == "PREL202605803"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_bend_metro(event.latitude, event.longitude)

    def test_third_fixture_valuation_and_containment(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            _flatten(_PERMIT_FEATURE_3, {"ApplicationDate", "IssueDate", "DateFinaled"}),
            city_id="bend",
        )
        assert event is not None
        assert event.job_id == "PRFR202605805"
        assert event.estimated_cost == pytest.approx(3770.0)
        assert event.proposed_dwelling_units is None
        assert is_in_bend_metro(event.latitude, event.longitude)

    def test_all_three_fixtures_share_the_co_newest_watermark(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        events = [
            permits.parse_socrata_row(
                _flatten(f, {"ApplicationDate", "IssueDate", "DateFinaled"}),
                city_id="bend",
            )
            for f in (_PERMIT_FEATURE_1, _PERMIT_FEATURE_2, _PERMIT_FEATURE_3)
        ]
        assert all(e is not None for e in events)
        assert {e.filing_date.isoformat() for e in events} == {_APPLICATIONDATE_ISO}

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_PERMIT_FEATURE_1, {"ApplicationDate", "IssueDate", "DateFinaled"})
        record.pop("ApplicationNumber")
        event = permits.parse_socrata_row(record, city_id="bend")
        assert event is not None
        assert event.job_id == "338663"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_PERMIT_FEATURE_1, {"ApplicationDate", "IssueDate", "DateFinaled"})
        record.pop("ApplicationNumber")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="bend") is None


class TestBendSLAParsing:
    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(
            _SLA_FEATURE_1,
            {"LicenseExpirationDate", "BR_BusinessOpenedDate"},
        )
        assert record["latitude"] == pytest.approx(44.06712833042855)
        assert record["longitude"] == pytest.approx(-121.32075454303641)

    def test_flatten_iso_normalizes_date_columns(self):
        record = _flatten(
            _SLA_FEATURE_1,
            {"LicenseExpirationDate", "BR_BusinessOpenedDate"},
        )
        assert record["LicenseExpirationDate"] == "2025-09-01T07:00:00+00:00"
        assert record["BR_BusinessOpenedDate"] == "2017-09-12T07:00:00+00:00"
        assert record["BusinessStatusCode"] == "A"

    def test_newest_fixture_parses_through_producer(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(
            _flatten(_SLA_FEATURE_1, {"LicenseExpirationDate", "BR_BusinessOpenedDate"}),
            city_id="bend",
        )
        assert event is not None
        assert event.city_id == "bend"
        assert event.license_id == "0001202405401"
        assert event.license_status == "Active"  # BusinessStatusDesc resolves first
        assert event.license_type == "Business Registration"
        assert event.dba == "WELL BUILT CONSTRUCTION LLC"
        assert event.premises_name == "WELL BUILT CONSTRUCTION LLC"
        assert event.address == "2005 NW 6TH ST, BEND, OR 97703"
        assert event.latitude == pytest.approx(44.06712833042855)
        assert event.longitude == pytest.approx(-121.32075454303641)

    def test_second_fixture_h3_and_containment(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(
            _flatten(_SLA_FEATURE_2, {"LicenseExpirationDate", "BR_BusinessOpenedDate"}),
            city_id="bend",
        )
        assert event is not None
        assert event.license_id == "0001202605726"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_bend_metro(event.latitude, event.longitude)

    def test_south_fringe_fixture_is_contained(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(
            _flatten(_SLA_FEATURE_3, {"LicenseExpirationDate", "BR_BusinessOpenedDate"}),
            city_id="bend",
        )
        assert event is not None
        assert event.dba == "CLIFF CRUSON FLOORING"
        assert event.address == "60867 SAWTOOTH MOUNTAIN LN, BEND, OR 97702"
        assert is_in_bend_metro(event.latitude, event.longitude)

    def test_license_id_falls_back_to_business_number(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten(
            _SLA_FEATURE_1, {"LicenseExpirationDate", "BR_BusinessOpenedDate"}
        )
        record.pop("LicenseNumber")
        event = sla.parse_socrata_row(record, city_id="bend")
        assert event is not None
        assert event.license_id == "LCBR21-16240"

    def test_row_without_any_id_is_dropped(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten(
            _SLA_FEATURE_1, {"LicenseExpirationDate", "BR_BusinessOpenedDate"}
        )
        record.pop("LicenseNumber")
        record.pop("BusinessNumber")
        record.pop("OBJECTID")
        assert sla.parse_socrata_row(record, city_id="bend") is None


class TestBend311Parsing:
    @pytest.fixture
    def complaints_311(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    def test_flatten_lifts_polygon_centroid_to_degrees(self):
        record = _flatten(_311_FEATURE_1, {"CaseReportedDate"})
        assert record["latitude"] == pytest.approx(44.053395, rel=1e-5)
        assert record["longitude"] == pytest.approx(-121.313763, rel=1e-5)

    def test_flatten_iso_normalizes_report_date(self):
        record = _flatten(_311_FEATURE_1, {"CaseReportedDate"})
        assert record["CaseReportedDate"] == _CASE_REPORTED_ISO
        assert record["CaseStatus"] == "NOV"

    def test_newest_fixture_parses_through_producer(self, complaints_311, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints_311.parse_socrata_row(
            _flatten(_311_FEATURE_1, {"CaseReportedDate"}),
            city_id="bend",
        )
        assert event is not None
        assert event.city_id == "bend"
        assert event.incident_id == "CESIGN202601226"
        assert event.complaint_type == "Signage"
        assert event.incident_address == "442 NW DELAWARE AVE, BEND, OR 97703"
        assert event.latitude == pytest.approx(44.053395, rel=1e-5)
        assert event.longitude == pytest.approx(-121.313763, rel=1e-5)

    def test_third_fixture_h3_and_containment(self, complaints_311, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        event = complaints_311.parse_socrata_row(
            _flatten(_311_FEATURE_3, {"CaseReportedDate"}),
            city_id="bend",
        )
        assert event is not None
        assert event.incident_id == "CEFW202601224"
        assert event.complaint_type == "Flammable Vegetation "
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert is_in_bend_metro(event.latitude, event.longitude)

    def test_incident_id_falls_back_to_objectid(self, complaints_311, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_311_FEATURE_1, {"CaseReportedDate"})
        record.pop("CaseNumber")
        event = complaints_311.parse_socrata_row(record, city_id="bend")
        assert event is not None
        assert event.incident_id == "474710"

    def test_row_without_any_id_is_dropped(self, complaints_311, monkeypatch):
        _patch_resolve(monkeypatch, "311")
        record = _flatten(_311_FEATURE_1, {"CaseReportedDate"})
        record.pop("CaseNumber")
        record.pop("OBJECTID")
        assert complaints_311.parse_socrata_row(record, city_id="bend") is None


class TestBendCrimeParsing:
    @pytest.fixture
    def crime(self):
        with patch("src.producers.crime_incidents_producer.BaseKafkaProducer"):
            from src.producers.crime_incidents_producer import CrimeIncidentsProducer

            return CrimeIncidentsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_CRIME_FEATURE_1, {"CreateDateTime"})
        assert record["latitude"] == pytest.approx(44.06951471894193)
        assert record["longitude"] == pytest.approx(-121.30323761161092)

    def test_flatten_iso_normalizes_create_datetime(self):
        record = _flatten(_CRIME_FEATURE_1, {"CreateDateTime"})
        assert record["CreateDateTime"] == _CREATED_ISO
        assert record["CallType"] == "UEMV Unauthorized Entry into Veh"

    def test_newest_fixture_parses_through_producer(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(
            _flatten(_CRIME_FEATURE_1, {"CreateDateTime"}),
            city_id="bend",
        )
        assert event is not None
        assert event.city_id == "bend"
        assert event.incident_id == "2026-00047504"
        assert event.offense_type == "UEMV Unauthorized Entry into Veh"
        assert event.source_neighborhood == "Orchard District"
        assert event.latitude == pytest.approx(44.06951471894193)
        assert event.longitude == pytest.approx(-121.30323761161092)

    def test_second_fixture_h3_and_containment(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(
            _flatten(_CRIME_FEATURE_2, {"CreateDateTime"}),
            city_id="bend",
        )
        assert event is not None
        assert event.incident_id == "2026-00047503"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_bend_metro(event.latitude, event.longitude)

    def test_third_fixture_offense_type_and_containment(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(
            _flatten(_CRIME_FEATURE_3, {"CreateDateTime"}),
            city_id="bend",
        )
        assert event is not None
        assert event.offense_type == "Suspicious Circumstances"
        assert event.source_neighborhood == "River West"
        assert is_in_bend_metro(event.latitude, event.longitude)

    def test_incident_id_falls_back_to_objectid(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        record = _flatten(_CRIME_FEATURE_1, {"CreateDateTime"})
        record.pop("IncidentNumber")
        event = crime.parse_socrata_row(record, city_id="bend")
        assert event is not None
        assert event.incident_id == "879549"

    def test_row_without_any_id_is_dropped(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        record = _flatten(_CRIME_FEATURE_1, {"CreateDateTime"})
        record.pop("IncidentNumber")
        record.pop("OBJECTID")
        assert crime.parse_socrata_row(record, city_id="bend") is None


class TestBendFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_bend_dataset("permits")
        assert spec.platform == "arcgis"
        assert spec.endpoint == BEND_PERMITS_ENDPOINT
        assert spec.watermark_col == "ApplicationDate"
        assert spec.id_keys == ["ApplicationNumber", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "ApplicationDate DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Bend, OR"
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"

    def test_sla_spec_matches_live_layer(self):
        spec = get_bend_dataset("sla")
        assert spec.platform == "arcgis"
        assert spec.endpoint == BEND_SLA_ENDPOINT
        assert spec.watermark_col == "LicenseExpirationDate"
        assert spec.id_keys == ["LicenseNumber", "BusinessNumber", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 7
        assert spec.order_by == "LicenseExpirationDate DESC"
        assert spec.ingestion_mode == "snapshot"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Bend, OR"
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.topic == "raw.municipal.sla"

    def test_311_spec_matches_live_layer(self):
        spec = get_bend_dataset("311")
        assert spec.platform == "arcgis"
        assert spec.endpoint == BEND_COMPLAINTS_311_ENDPOINT
        assert spec.watermark_col == "CaseReportedDate"
        assert spec.id_keys == ["CaseNumber", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "CaseReportedDate DESC"
        assert spec.interval_seconds == 300.0
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Bend, OR"
        assert spec.field_map == COMPLAINTS_311_FIELD_MAP
        assert spec.topic == "raw.municipal.311"

    def test_crime_spec_matches_live_layer(self):
        spec = get_bend_dataset("crime")
        assert spec.platform == "arcgis"
        assert spec.endpoint == BEND_CRIME_ENDPOINT
        assert spec.watermark_col == "CreateDateTime"
        assert spec.id_keys == ["IncidentNumber", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "CreateDateTime DESC"
        assert spec.interval_seconds == 300.0
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Bend, OR"
        assert spec.field_map == CRIME_FIELD_MAP
        assert spec.topic == "raw.municipal.crime"

    def test_registered_feed_set(self):
        assert set(BEND_FEED_SPECS) == {"permits", "sla", "311", "crime"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_bend_dataset("deeds")
        assert "bend" in str(exc.value)
        assert "permits" in str(exc.value)
        assert "sla" in str(exc.value)

    def test_endpoints_all_on_services5_arcgis(self):
        for ep in (BEND_PERMITS_ENDPOINT, BEND_SLA_ENDPOINT,
                   BEND_COMPLAINTS_311_ENDPOINT, BEND_CRIME_ENDPOINT):
            assert "services5.arcgis.com" in ep
            assert "FeatureServer/0" in ep