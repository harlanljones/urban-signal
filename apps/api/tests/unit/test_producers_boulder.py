"""Unit tests for the Boulder, CO leaf (US-245): spatial module + field maps
+ producer parse wiring.

Boulder is a TWO-FEED partial metro: PERMITS (Construction_Permits AGOL
FeatureServer/0 — non-spatial Table, address-only, needs_geocode) and SLA
(RentalHousingLicenses ArcGIS Server MapServer/0 — polygon parcel geometry,
outSR=4326 centroid lift, APPLIEDDATE watermark). 311, DEEDS, and other SLA
candidates are Tier 3 and stay unregistered.

Tests pass WITHOUT a spine registration (no CityId.BOULDER): the producer
resolves city_id="boulder" as a plain string, the leaf-local field map is
pinned via the resolve_field_map patch, and coordinates come from the
production ArcGIS flatten (outSR=4326 rings reduced to a centroid for SLA;
ADR-0004 geocode supplement for the non-spatial PERMITS feed).

Fixtures captured byte-verbatim 2026-08-28 from the live endpoints.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_boulder import (
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.spatial.cities.boulder import (
    BOULDER_CITY_ID,
    BOULDER_DIVISION_BBOXES,
    BOULDER_DIVISIONS,
    BOULDER_FEED_SPECS,
    BOULDER_GEOCODE_CONTEXT,
    BOULDER_METRO_BBOX,
    BOULDER_PERMITS_ENDPOINT,
    BOULDER_SLA_ENDPOINT,
    BOULDER_SUBMARKETS,
    REGISTRATION,
    get_boulder_dataset,
    is_in_boulder_metro,
    is_in_greater_boulder_metro,
)
from src.spatial.city_registry import FeedType


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


# ---------------------------------------------------------------------------
# PERMITS fixtures — Construction_Permits FeatureServer/0 (Table, non-spatial).
# Captured 2026-08-28 from the live AGOL service, newest by IssuedDate DESC.
# Byte-verbatim; no geometry returned (Table type). All dates are ANSI strings.
# ---------------------------------------------------------------------------

_PERMIT_SENTINEL = {
    "attributes": {
        "PermitID": "1ed892b9-fde8-46bd-a24b-57a5c9b6f429",
        "PermitNum": "MEC2026-01581",
        "MasterPermitNum": None,
        "Description": "40 galons atmosferic water heater.",
        "AppliedDate": "2026-08-27",
        "IssuedDate": "2026-08-27",
        "CompletedDate": None,
        "StatusCurrent": "Issued",
        "OriginalAddress": "3388 SENTINEL DR",
        "OriginalCity": "BOULDER",
        "OriginalState": "CO",
        "OriginalZip": "80301",
        "COBPIN": "172113000242",
        "BOCOPIN": "146321307040",
        "BOCOTAX": "R0087742",
        "ProjectName": None,
        "PermitType": "Mechanical Permit",
        "PermitWorkType": "Water Heat - Single Family Residential",
        "EstProjectCost": "1500.0",
        "EstPhotovoltaicCost": None,
        "EstSolarCost": None,
        "NewHousingUnits": None,
        "ExistingHousingUnits": None,
        "AffordableHousingUnits": None,
        "RemovedHousingUnits": None,
        "AddedSqFt": None,
        "RemodeledSqFt": None,
        "RemovedResSqFt": None,
        "RemovedNonResSqFt": None,
        "RemovedParkingStructureSqFt": None,
        "RemovedDescription": None,
        "PhotovoltaicKilowatt": None,
        "PhotovoltaicElecVehicleOffset": None,
        "ElecVehicleChargeStation": None,
        "SolarSystemDescription": None,
        "ContractorCompanyName": "CLEAR WINGS LTD",
        "ContractorTrade": "Contractor: Plumbing",
        "ObjectId": 185,
    },
    "geometry": None,
}

_PERMIT_UTILITY = {
    "attributes": {
        "PermitID": "08204099-2ccf-4c8a-bc0d-eb44ac17e4f6",
        "PermitNum": "UTL2026-00348",
        "MasterPermitNum": None,
        "Description": "*EMERGENCY REPAIR* Spot repair on the sewer line in the yard",
        "AppliedDate": "2026-08-27",
        "IssuedDate": "2026-08-27",
        "CompletedDate": None,
        "StatusCurrent": "Issued",
        "OriginalAddress": "4170 MONROE DR",
        "OriginalCity": "BOULDER",
        "OriginalState": "CO",
        "OriginalZip": "80303",
        "COBPIN": "173313000043",
        "BOCOPIN": "146333310036",
        "BOCOTAX": "R0066992",
        "ProjectName": None,
        "PermitType": "Utility Permit",
        "PermitWorkType": "Utility Permit",
        "EstProjectCost": "0.0",
        "EstPhotovoltaicCost": None,
        "EstSolarCost": None,
        "NewHousingUnits": None,
        "ExistingHousingUnits": None,
        "AffordableHousingUnits": None,
        "RemovedHousingUnits": None,
        "AddedSqFt": None,
        "RemodeledSqFt": None,
        "RemovedResSqFt": None,
        "RemovedNonResSqFt": None,
        "RemovedParkingStructureSqFt": None,
        "RemovedDescription": None,
        "PhotovoltaicKilowatt": None,
        "PhotovoltaicElecVehicleOffset": None,
        "ElecVehicleChargeStation": None,
        "SolarSystemDescription": None,
        "ContractorCompanyName": "AFFORD A ROOTER",
        "ContractorTrade": "Contractor: General",
        "ObjectId": 198,
    },
    "geometry": None,
}

_ISSUEDDATE_ISO = "2026-08-27"

# ---------------------------------------------------------------------------
# SLA fixtures — RentalHousingLicenses MapServer/0 (polygon parcel geometry).
# Captured 2026-08-28 from the live ArcGIS Server, newest by APPLIEDDATE DESC.
# Byte-verbatim attributes + rings at outSR=4326.
# ---------------------------------------------------------------------------

_SLA_DOVER_DR = {
    "attributes": {
        "OBJECTID": 12612920,
        "COBPIN": "230543000107",
        "BOCOTAX": "R0012905",
        "BOCOPIN": "157705325004",
        "LICENSENUMBER": "RHL-01006909",
        "MAINADDRESS": "3225 DOVER DR",
        "LICENSESTATUS": "Pending at Applicant",
        "APPLIEDDATE": 1787529600000,
        "ISSUEDDATE": 1787529600000,
        "EXPIRATIONDATE": None,
        "LASTRENEWALDATE": None,
        "SUBCOMMUNITY": "South Boulder",
        "RENTALTYPE": "Short Term Rental",
        "COMPLEXNAME": None,
        "BUILDINGTYPE": "Single Family Dwelling",
        "ENERGYCOMPLIANT": "Exempt - Short Term Rental",
        "BUILDINGIDENTIFICATION": "3225",
        "DWELLINGUNITSONCASE": 1.0,
        "ROOMINGUNITSONCASE": 0.0,
        "PROFESSIONALLICENSEHOLDERNAME": "TRICIA MEESE",
        "PROFESSIONALLICENSEHOLDERCMPNY": "",
        "PROFESSIONALLICENSEYEAR": 2026,
    },
    "geometry": {
        "rings": [
            [
                [-105.25430133709976, 39.987568740213234],
                [-105.25445822003067, 39.98727705069199],
                [-105.25467609521927, 39.98734972454894],
                [-105.25450288631491, 39.987655089362576],
                [-105.25430133709976, 39.987568740213234],
            ]
        ]
    },
}

_SLA_DOVER_CENTROID = (-105.2544846, 39.9874627)

_SLA_BURR_PL = {
    "attributes": {
        "OBJECTID": 12611218,
        "COBPIN": "173321000051",
        "BOCOTAX": "R0072601",
        "BOCOPIN": "146333209016",
        "LICENSENUMBER": "RHL-01006908",
        "MAINADDRESS": "4402 BURR PL",
        "LICENSESTATUS": "Pending at Applicant",
        "APPLIEDDATE": 1787356800000,
        "ISSUEDDATE": 1787356800000,
        "EXPIRATIONDATE": None,
        "LASTRENEWALDATE": None,
        "SUBCOMMUNITY": "Southeast Boulder",
        "RENTALTYPE": "Short Term Rental",
        "COMPLEXNAME": None,
        "BUILDINGTYPE": "Single Family Dwelling",
        "ENERGYCOMPLIANT": "Exempt - Short Term Rental",
        "BUILDINGIDENTIFICATION": "4402",
        "DWELLINGUNITSONCASE": 1.0,
        "ROOMINGUNITSONCASE": 0.0,
        "PROFESSIONALLICENSEHOLDERNAME": (
            "MICHAEL P KEARNEY REVOCABLE TRUST MICHAEL P KEARNEY REVOCABLE TRUST"
        ),
        "PROFESSIONALLICENSEHOLDERCMPNY": "MICHAEL P KEARNEY REVOCABLE TRUST",
        "PROFESSIONALLICENSEYEAR": 2026,
    },
    "geometry": {
        "rings": [
            [
                [-105.23863592630758, 40.011313479095314],
                [-105.2388951430322, 40.01131530379798],
                [-105.23888095291733, 40.01161780103609],
                [-105.23863453848372, 40.01161870367704],
                [-105.23863592630758, 40.011313479095314],
            ]
        ]
    },
}

_SLA_BURR_CENTROID = (-105.2387616, 40.0114663)

_APPLIEDDATE_ISO = "2026-08-24T00:00:00+00:00"  # DOVER DR (newest)
_APPLIEDDATE_BURR_ISO = "2026-08-22T00:00:00+00:00"  # BURR PL


def _flatten_permit(feature):
    """Flatten a Construction Permits fixture (Table, no geometry, no esri
    date fields — all dates are ANSI strings)."""
    from src.producers.arcgis_client import ArcGISClient
    return ArcGISClient()._flatten_feature(feature, date_fields=set())


def _flatten_sla(feature):
    """Flatten a RentalHousingLicenses fixture (polygon geometry, esri date
    fields: APPLIEDDATE/ISSUEDDATE/EXPIRATIONDATE/LASTRENEWALDATE)."""
    from src.producers.arcgis_client import ArcGISClient
    return ArcGISClient()._flatten_feature(
        feature,
        date_fields={"APPLIEDDATE", "ISSUEDDATE", "EXPIRATIONDATE", "LASTRENEWALDATE"},
    )


@patch("src.producers.dob_permits_producer.BaseKafkaProducer")
def _permits_producer(_):
    from src.producers.dob_permits_producer import DOBPermitsProducer
    return DOBPermitsProducer()


@patch("src.producers.sla_licenses_producer.BaseKafkaProducer")
def _sla_producer(_):
    from src.producers.sla_licenses_producer import SLALicensesProducer
    return SLALicensesProducer()


# ======================================================================
# Spatial tests
# ======================================================================


class TestBoulderSpatial:
    def test_metro_bbox_sanity(self):
        assert BOULDER_METRO_BBOX["min_lat"] < BOULDER_METRO_BBOX["max_lat"]
        assert BOULDER_METRO_BBOX["min_lng"] < BOULDER_METRO_BBOX["max_lng"]

    def test_is_in_boulder_metro_rejects_missing_coordinates(self):
        assert is_in_boulder_metro(None, None) is False
        assert is_in_boulder_metro(40.0150, None) is False
        assert is_in_boulder_metro(None, -105.2738) is False

    def test_is_in_boulder_metro_rejects_other_cities(self):
        assert is_in_boulder_metro(39.7392, -104.9903) is False  # Denver
        assert is_in_boulder_metro(40.1699, -105.1017) is False  # Longmont
        assert is_in_boulder_metro(39.9775, -105.1317) is False  # Louisville
        assert is_in_boulder_metro(39.9970, -105.0897) is False  # Lafayette

    def test_downtown_anchors_are_contained(self):
        assert is_in_boulder_metro(40.0193, -105.2738)  # Pearl Street
        assert is_in_boulder_metro(40.0076, -105.2708)  # CU Boulder
        assert is_in_boulder_metro(40.0160, -105.2810)  # County Courthouse

    def test_live_fixture_coordinates_are_contained(self):
        assert is_in_boulder_metro(
            _SLA_DOVER_CENTROID[1], _SLA_DOVER_CENTROID[0]
        )
        assert is_in_boulder_metro(
            _SLA_BURR_CENTROID[1], _SLA_BURR_CENTROID[0]
        )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in BOULDER_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= BOULDER_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= BOULDER_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= BOULDER_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= BOULDER_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in BOULDER_SUBMARKETS.items():
            bbox = BOULDER_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in BOULDER_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(BOULDER_SUBMARKETS)

    def test_submarkets_carry_the_boulder_city_id(self):
        assert {m.city_id for m in BOULDER_SUBMARKETS.values()} == {"boulder"}

    def test_city_id_and_registration_shape(self):
        assert BOULDER_CITY_ID == "boulder"
        assert REGISTRATION.metro_bbox is BOULDER_METRO_BBOX
        assert REGISTRATION.submarkets is BOULDER_SUBMARKETS
        assert REGISTRATION.division_bboxes is BOULDER_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_boulder_metro
        assert len(REGISTRATION.divisions) == 7
        assert len(BOULDER_SUBMARKETS) == 11

    def test_required_real_neighborhoods_present(self):
        assert set(BOULDER_SUBMARKETS) == {
            "Downtown",
            "Mapleton Hill",
            "University Hill",
            "Whittier",
            "Boulder Junction",
            "North Boulder",
            "Holiday",
            "Table Mesa",
            "Martin Acres",
            "Southeast Boulder",
            "Gunbarrel",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_boulder_metro is is_in_boulder_metro


# ======================================================================
# Feed spec tests
# ======================================================================


class TestBoulderFeedSpec:
    def test_registered_feed_set_is_permits_and_sla(self):
        assert set(BOULDER_FEED_SPECS) == {"permits", "sla"}

    def test_permits_spec_matches_live_layer(self):
        spec = get_boulder_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == BOULDER_PERMITS_ENDPOINT
        assert spec.watermark_col == "IssuedDate"
        assert spec.id_keys == ["PermitNum", "PermitID", "ObjectId"]
        assert spec.oid_field == "ObjectId"
        assert spec.max_record_count == 1000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "IssuedDate DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Boulder, CO"
        assert spec.topic == "raw.municipal.permits"
        assert spec.watermark_type == "text"
        assert spec.watermark_format == "%Y-%m-%d"

    def test_sla_spec_matches_live_layer(self):
        spec = get_boulder_dataset(FeedType.SLA)
        assert spec.platform == "arcgis"
        assert spec.endpoint == BOULDER_SLA_ENDPOINT
        assert spec.watermark_col == "APPLIEDDATE"
        assert spec.id_keys == ["LICENSENUMBER", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 7
        assert spec.order_by == "APPLIEDDATE DESC"
        assert spec.interval_seconds == 600.0
        assert spec.needs_geocode is False
        assert spec.geocode_context is None
        assert spec.topic == "raw.municipal.sla"
        assert spec.state_plane_crs == "EPSG:2876"
        assert spec.state_plane_units == "ftUS"

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_boulder_dataset("deeds")
        assert "boulder" in str(exc.value)
        assert "permits" in str(exc.value)
        assert "sla" in str(exc.value)

    def test_endpoints_are_the_probed_servers(self):
        assert "services.arcgis.com/ePKBjXrBZ2vEEgWd" in BOULDER_PERMITS_ENDPOINT
        assert "Construction_Permits" in BOULDER_PERMITS_ENDPOINT
        assert "RentalHousingLicenses" in BOULDER_SLA_ENDPOINT
        assert "gis.bouldercolorado.gov" in BOULDER_SLA_ENDPOINT


# ======================================================================
# Field map tests
# ======================================================================


class TestBoulderFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["PermitNum", "PermitID", "ObjectId"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["IssuedDate"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["AppliedDate"]
        assert PERMITS_FIELD_MAP["status"] == ["StatusCurrent"]
        assert PERMITS_FIELD_MAP["job_type"] == ["PermitType", "PermitWorkType"]
        assert PERMITS_FIELD_MAP["cost"] == ["EstProjectCost"]
        assert PERMITS_FIELD_MAP["address_street"] == ["OriginalAddress"]
        assert PERMITS_FIELD_MAP["zipcode"] == ["OriginalZip"]
        assert PERMITS_FIELD_MAP["borough"] == ["OriginalCity"]

    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["LICENSENUMBER"]
        assert SLA_FIELD_MAP["dba"] == ["COMPLEXNAME", "PROFESSIONALLICENSEHOLDERNAME"]
        assert SLA_FIELD_MAP["premises_name"] == ["COMPLEXNAME"]
        assert SLA_FIELD_MAP["license_type"] == ["RENTALTYPE"]
        assert SLA_FIELD_MAP["status"] == ["LICENSESTATUS"]
        assert SLA_FIELD_MAP["effective_date"] == ["APPLIEDDATE"]
        assert SLA_FIELD_MAP["expiration_date"] == ["EXPIRATIONDATE"]
        assert SLA_FIELD_MAP["address_street"] == ["MAINADDRESS"]
        assert SLA_FIELD_MAP["borough"] == ["SUBCOMMUNITY"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP["permits"] is PERMITS_FIELD_MAP
        assert FIELD_MAP["sla"] is SLA_FIELD_MAP
        assert GEOCODE_CONTEXT == "Boulder, CO"
        assert BOULDER_GEOCODE_CONTEXT == "Boulder, CO"

    def test_no_coordinate_candidates_in_permit_map(self):
        """Construction_Permits is a non-spatial Table — coordinates come
        from the ADR-0004 geocode only, never from the field map."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP

    def test_no_coordinate_candidates_in_sla_map(self):
        """RentalHousingLicenses has polygon geometry — coordinates come
        from the outSR=4326 centroid lift, never from the field map."""
        assert "latitude" not in SLA_FIELD_MAP
        assert "longitude" not in SLA_FIELD_MAP

    def test_first_mapped_permits(self):
        row = _PERMIT_SENTINEL["attributes"]
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "MEC2026-01581"
        assert first_mapped(row, PERMITS_FIELD_MAP, "issuance_date") == "2026-08-27"
        assert first_mapped(row, PERMITS_FIELD_MAP, "status") == "Issued"
        assert first_mapped(row, PERMITS_FIELD_MAP, "cost") == "1500.0"
        assert first_mapped(row, PERMITS_FIELD_MAP, "address_street") == "3388 SENTINEL DR"
        assert first_mapped(row, PERMITS_FIELD_MAP, "zipcode") == "80301"
        assert first_mapped(row, PERMITS_FIELD_MAP, "borough") == "BOULDER"

    def test_first_mapped_sla(self):
        row = _SLA_DOVER_DR["attributes"]
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "RHL-01006909"
        assert first_mapped(row, SLA_FIELD_MAP, "status") == "Pending at Applicant"
        assert first_mapped(row, SLA_FIELD_MAP, "license_type") == "Short Term Rental"
        assert first_mapped(row, SLA_FIELD_MAP, "address_street") == "3225 DOVER DR"
        assert first_mapped(row, SLA_FIELD_MAP, "borough") == "South Boulder"

    def test_sla_dba_falls_through_when_complexname_null(self):
        """COMPLEXNAME is null for single-family rentals; the fallback
        PROFESSIONALLICENSEHOLDERNAME is the licensee."""
        row = _SLA_DOVER_DR["attributes"]
        assert row["COMPLEXNAME"] is None
        assert first_mapped(row, SLA_FIELD_MAP, "dba") == "TRICIA MEESE"

    def test_permit_job_id_falls_back_to_objectid(self):
        row = dict(_PERMIT_SENTINEL["attributes"])
        row.pop("PermitNum")
        row.pop("PermitID")
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == 185

    def test_permit_est_project_cost_is_string(self):
        assert isinstance(_PERMIT_SENTINEL["attributes"]["EstProjectCost"], str)


# ======================================================================
# Permit parsing tests
# ======================================================================


class TestBoulderPermitParsing:
    @pytest.fixture
    def permits(self):
        return _permits_producer()

    def test_flatten_lifts_attributes_only_no_geometry(self, permits):
        """Construction_Permits is a Table — no geometry is returned."""
        record = _flatten_permit(_PERMIT_SENTINEL)
        assert record["PermitNum"] == "MEC2026-01581"
        assert record["IssuedDate"] == "2026-08-27"
        assert "latitude" not in record
        assert "longitude" not in record

    def test_sentinel_fixture_parses_through_geocode(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (40.0183, -105.2720),
        )
        event = permits.parse_socrata_row(
            _flatten_permit(_PERMIT_SENTINEL), city_id="boulder"
        )
        assert event is not None
        assert event.city_id == "boulder"
        assert event.job_id == "MEC2026-01581"
        assert event.estimated_cost == pytest.approx(1500.0)
        assert event.address_street == "3388 SENTINEL DR"
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat().startswith(_ISSUEDDATE_ISO)
        assert event.filing_date is not None
        assert event.status == "Issued"
        assert event.latitude == pytest.approx(40.0183)
        assert event.longitude == pytest.approx(-105.2720)

    def test_utility_fixture_parses_from_geocode(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (40.0050, -105.2630),
        )
        event = permits.parse_socrata_row(
            _flatten_permit(_PERMIT_UTILITY), city_id="boulder"
        )
        assert event is not None
        assert event.job_id == "UTL2026-00348"
        assert event.estimated_cost == pytest.approx(0.0)
        assert event.issuance_date is not None
        assert event.status == "Issued"

    def test_geometry_less_row_dropped_when_geocode_fails(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        event = permits.parse_socrata_row(
            _flatten_permit(_PERMIT_SENTINEL), city_id="boulder"
        )
        assert event is None

    def test_permits_share_the_co_newest_watermark(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (40.0150, -105.2700),
        )
        events = [
            permits.parse_socrata_row(_flatten_permit(f), city_id="boulder")
            for f in (_PERMIT_SENTINEL, _PERMIT_UTILITY)
        ]
        assert all(e is not None for e in events)
        assert {e.issuance_date.isoformat()[:10] for e in events} == {_ISSUEDDATE_ISO}

    def test_permits_parse_without_borough_candidate(self, permits, monkeypatch):
        """OriginalCity maps to the borough field; the source_neighborhood
        is the raw city name. Division resolution is a spine concern and
        is NOT asserted here."""
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (40.0200, -105.2700),
        )
        event = permits.parse_socrata_row(
            _flatten_permit(_PERMIT_SENTINEL), city_id="boulder"
        )
        assert event is not None
        assert event.source_neighborhood is not None


# ======================================================================
# SLA parsing tests
# ======================================================================


class TestBoulderSLAParsing:
    @pytest.fixture
    def sla(self):
        return _sla_producer()

    def test_dover_dr_flatten_lifts_polygon_centroid(self, sla):
        """Polygon rings reduce to WGS84 (lng, lat) via shapely centroid."""
        record = _flatten_sla(_SLA_DOVER_DR)
        assert record["LICENSENUMBER"] == "RHL-01006909"
        assert record["latitude"] == pytest.approx(_SLA_DOVER_CENTROID[1], abs=1e-4)
        assert record["longitude"] == pytest.approx(_SLA_DOVER_CENTROID[0], abs=1e-4)

    def test_flatten_converts_epoch_ms_to_iso(self, sla):
        record = _flatten_sla(_SLA_DOVER_DR)
        assert record["APPLIEDDATE"] == _APPLIEDDATE_ISO
        assert record["ISSUEDDATE"] == _APPLIEDDATE_ISO
        record2 = _flatten_sla(_SLA_BURR_PL)
        assert record2["APPLIEDDATE"] == _APPLIEDDATE_BURR_ISO

    def test_sla_dover_dr_parses_through_producer(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(
            _flatten_sla(_SLA_DOVER_DR), city_id="boulder"
        )
        assert event is not None
        assert event.city_id == "boulder"
        assert event.license_id == "RHL-01006909"
        assert event.license_type == "Short Term Rental"
        assert event.license_status == "Pending at Applicant"
        assert event.address == "3225 DOVER DR"
        assert event.source_neighborhood == "South Boulder"
        assert event.latitude == pytest.approx(_SLA_DOVER_CENTROID[1], abs=1e-4)
        assert event.longitude == pytest.approx(_SLA_DOVER_CENTROID[0], abs=1e-4)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None

    def test_sla_burr_pl_parses_and_has_h3(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(
            _flatten_sla(_SLA_BURR_PL), city_id="boulder"
        )
        assert event is not None
        assert event.license_id == "RHL-01006908"
        assert event.source_neighborhood == "Southeast Boulder"
        assert event.latitude == pytest.approx(_SLA_BURR_CENTROID[1], abs=1e-4)
        assert event.longitude == pytest.approx(_SLA_BURR_CENTROID[0], abs=1e-4)
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3

    def test_both_sla_fixtures_parse(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        for attrs, geom in (
            (_SLA_DOVER_DR["attributes"], _SLA_DOVER_DR["geometry"]),
            (_SLA_BURR_PL["attributes"], _SLA_BURR_PL["geometry"]),
        ):
            record = _flatten_sla({"attributes": attrs, "geometry": geom})
            assert sla.parse_socrata_row(record, city_id="boulder") is not None

    def test_sla_effective_date_parses_correctly(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(
            _flatten_sla(_SLA_DOVER_DR), city_id="boulder"
        )
        assert event is not None
        assert event.effective_date is not None
        assert event.effective_date.isoformat().startswith("2026-08-24")

    def test_sla_expiration_is_none_for_pending(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(
            _flatten_sla(_SLA_DOVER_DR), city_id="boulder"
        )
        assert event is not None
        assert event.expiration_date is None

    def test_sla_geometry_less_row_falls_back_to_geocode(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten_sla(_SLA_DOVER_DR)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (39.9875, -105.2545),
        )
        event = sla.parse_socrata_row(record, city_id="boulder")
        assert event is not None
        assert event.latitude == pytest.approx(39.9875)
        assert event.longitude == pytest.approx(-105.2545)

    def test_sla_dba_falls_back_to_licensee_name(self, sla, monkeypatch):
        """COMPLEXNAME is null -> producer falls back to
        PROFESSIONALLICENSEHOLDERNAME for dba."""
        _patch_resolve(monkeypatch, "sla")
        row = _flatten_sla(_SLA_DOVER_DR)
        event = sla.parse_socrata_row(row, city_id="boulder")
        assert event is not None
        assert event.dba == "TRICIA MEESE"

    def test_fixtures_contained_by_leaf_bboxes(self):
        for lat, lng in (
            (_SLA_DOVER_CENTROID[1], _SLA_DOVER_CENTROID[0]),
            (_SLA_BURR_CENTROID[1], _SLA_BURR_CENTROID[0]),
        ):
            assert is_in_boulder_metro(lat, lng), f"({lat}, {lng})"
            contained = False
            for bbox in BOULDER_DIVISION_BBOXES.values():
                if bbox["min_lat"] <= lat <= bbox["max_lat"] and bbox["min_lng"] <= lng <= bbox["max_lng"]:
                    contained = True
                    break
            assert contained, f"({lat}, {lng}) not in any division"