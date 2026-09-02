"""Unit tests for the Salem, OR leaf (US-226 / US-426): spatial module + field
maps + producer parse wiring.

Salem, OR is a TWO-FEED PARTIAL metro: Structure_Permits (FeatureServer/0,
Tier 1, ~802 rows) on the City of Salem's AGOL org (``kIA6yS9KDGqZL7U3``)
and — since US-426 — the OR Secretary of State Active Businesses registry
(``tckn-sxa6``, ``data.oregon.gov``) as the metropolitan SLA. 311 is a stale
8-row 2017 demo and deeds are Tier 3 — only ``permits`` and ``sla`` are
registered.

Tests pass WITHOUT a spine registration (no CityId.SALEM_OR, no REGISTRY
assertions — ``city_id="salem_or"`` strings only). Spine-stable per the
wave-5 leaf contract: no division/borough-resolution assertions and no
geocode-hook call-count assertions (both change when the spine lands).

Permits fixtures captured byte-verbatim 2026-08-28 from FeatureServer/0
(``orderByFields=ISSUEDDATE DESC`` at ``outSR=4326``). SLA fixtures are
flat Socrata rows from the OR Active Businesses API (``tckn-sxa6``,
``data.oregon.gov``) captured 2026-08-31.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_salem_or import (
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.salem_or import (
    REGISTRATION,
    SALEM_CITY_ID,
    SALEM_DIVISION_BBOXES,
    SALEM_DIVISIONS,
    SALEM_FEED_SPECS,
    SALEM_GEOCODE_CONTEXT,
    SALEM_METRO_BBOX,
    SALEM_PERMITS_ENDPOINT,
    SALEM_SLA_ENDPOINT,
    SALEM_SUBMARKETS,
    get_salem_dataset,
    is_in_greater_salem_metro,
    is_in_salem_metro,
)
from src.spatial.city_registry import FeedType


def _patch_resolve_permits(monkeypatch):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: PERMITS_FIELD_MAP,
    )


def _patch_resolve_sla(monkeypatch):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: SLA_FIELD_MAP,
    )


def _flatten_permits(feature):
    """Run the real ArcGIS flatten lift over a raw captured permits feature."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, {"CREATEDDATE", "ISSUEDDATE"})


# ---------------------------------------------------------------------------
# Permits fixtures (byte-verbatim from 2026-08-28 probe, newest by ISSUEDDATE)
# ---------------------------------------------------------------------------

PERMIT_FEATURE_BLOSSOM = {
    "attributes": {
        "OBJECTID": 2093677,
        "FOLDERRSN": 1209880,
        "GISID": "28030",
        "FOLDERNUMBER": "26-104120-BP",
        "PROPERTYADDRESS": "3121 BLOSSOM DR NE",
        "CREATEDDATE": 1770992634000,
        "ISSUEDDATE": 1787844265000,
        "SUBDESCRIPTION": "Commercial-Civil site work only",
        "WORKDESCRIPTION": "New",
        "STATUS": "Issued",
        "FOLDERDESCRIPTION": "TAXLOT 073W01A001800 HAS BEEN A DEVELOPED LOT FOR MANY DECADES WITH GRAVEL STORAGE AND INDUSTRIAL USE IN THE EXISTING NORTH BUILDING AND RESIDENTIAL USE IN THE SOUTH PORTION OF THE LOT.  THE PROPOSED REDEVELOPMENT ON THIS LOT IS DEMOLITION OF THE RESIDENCE, MINOR GRADING AND APPLYING GRAVEL TO THE PERVIOUS AREA FOR USE AS A STORAGE YARD.\r\n\r\nTAXLOT 073W01A001900 RECENTLY HAD GRAVEL APPLIED OVER NATIVE GROUND AND IS PLANNED TO BE PARTIALLY REDEVELOPED TO CONSTRUCT A NEW DETENTION POND, CONVEYANCE DITCH AND TREATMENT SWALE.  \r\n\r\nTHE NEW DETENTION AND TREATMENT SYSTEM WILL BE DESIGNED ASSUMING FULLY PERVIOUS PRE-DEVELOPED CONDITIONS (LEWIS & CLARK) FOR BOTH TAX LOTS.  POST-DEVELOPED CONDITIONS WILL ACCOMMODATE FULL COVERAGE GRAVEL EXCEPT WHERE PAVING AND STRUCTURES WHICH WILL BE CONSIDERED IMPERVIOUS, EXISTING MINOR LANDSCAPING AND PERVIOUS AREA OF STORMWATER TREATMENT SWALE.",
        "X": 7556990,
        "Y": 494025,
        "NEIGHBORHOOD": "Northgate Neighborhood Association",
        "WARD": "5",
        "DAYS_FROM_DATE": 0,
        "FOLDERREVISION": "00",
        "MAPDESCRIPTION": "Commercial/Multi Family",
        "GlobalID": "43d940eb-7742-492f-8c44-b2c39d110df6",
    },
    "geometry": {
        "x": -122.99423605410927,
        "y": 44.994441445579,
    },
}

PERMIT_FEATURE_CLARENCE = {
    "attributes": {
        "OBJECTID": 2093956,
        "FOLDERRSN": 1222904,
        "GISID": "82859",
        "FOLDERNUMBER": "26-116702-DW",
        "PROPERTYADDRESS": "4785 CLARENCE CT SE",
        "CREATEDDATE": 1787061153000,
        "ISSUEDDATE": 1787843113000,
        "SUBDESCRIPTION": "Single Family",
        "WORKDESCRIPTION": "Solar Array",
        "STATUS": "Issued",
        "FOLDERDESCRIPTION": "Installation of solar panels on existing residential roof. 8.8 kW. Addition of (1) 0-60A circuits. 20 panels.\r\n",
        "X": 7539870,
        "Y": 455927,
        "NEIGHBORHOOD": "Faye Wright Neighborhood Association",
        "WARD": "7",
        "DAYS_FROM_DATE": 0,
        "FOLDERREVISION": "00",
        "MAPDESCRIPTION": "Residential",
        "GlobalID": "e49b827d-264b-4ee4-b459-8696d3db3660",
    },
    "geometry": {
        "x": -123.05572624759341,
        "y": 44.888522796365116,
    },
}

PERMIT_FEATURE_WALN = {
    "attributes": {
        "OBJECTID": 2093954,
        "FOLDERRSN": 1222516,
        "GISID": "88701",
        "FOLDERNUMBER": "26-116325-DW",
        "PROPERTYADDRESS": "1938 WALN CREEK DR S",
        "CREATEDDATE": 1786613812000,
        "ISSUEDDATE": 1787842303000,
        "SUBDESCRIPTION": "Single Family",
        "WORKDESCRIPTION": "Solar Array",
        "STATUS": "Issued",
        "FOLDERDESCRIPTION": "Installation of solar panels on existing residential roof. 4.4 kW. Addition of (1) 0-60A circuits. 10 panels. Upgrade Electrical Service from Existing 200/200A to New 200/200A 120/240V Single Phase. Temporary Disconnect / Reconnect Required for Installation.",
        "X": 7535724,
        "Y": 451276,
        "NEIGHBORHOOD": "Sunnyslope Neighborhood Association",
        "WARD": "7",
        "DAYS_FROM_DATE": 0,
        "FOLDERREVISION": "00",
        "MAPDESCRIPTION": "Residential",
        "GlobalID": "9f6203ea-3418-42e7-bfe5-2de2473dc148",
    },
    "geometry": {
        "x": -123.07114490109016,
        "y": 44.87541073604682,
    },
}

BLOSSOM_ROW = _flatten_permits(PERMIT_FEATURE_BLOSSOM)
CLARENCE_ROW = _flatten_permits(PERMIT_FEATURE_CLARENCE)
WALN_ROW = _flatten_permits(PERMIT_FEATURE_WALN)

_ISSUEDATE_ISO = "2026-08-27T15:24:25+00:00"

# ---------------------------------------------------------------------------
# SLA fixtures (flat Socrata rows from OR Active Businesses API, 2026-08-31)
# ---------------------------------------------------------------------------

SLA_ROW_TALOS = {
    "registry_number": "262244792",
    "business_name": "TALOS VENTURES LLC",
    "entity_type": "DOMESTIC LIMITED LIABILITY COMPANY",
    "registry_date": "2026-08-31T16:56:42.000",
    "address": "942 WINDEMERE DR NW",
    "city": "SALEM",
    "state": "OR",
    "zip": "97304",
}

SLA_ROW_HEART = {
    "registry_number": "262242598",
    "business_name": "HEART OF SALEM MARKET PLACE COLLECTIVE",
    "entity_type": "ASSUMED BUSINESS NAME",
    "registry_date": "2026-08-31T16:54:58.000",
    "address": "357 COURT STREET NORTHEAST",
    "city": "SALEM",
    "state": "OR",
    "zip": "97301",
}

SLA_ROW_EMPOWER = {
    "registry_number": "261783394",
    "business_name": "EMPOWER BROKERAGE, INC.",
    "entity_type": "FOREIGN BUSINESS CORPORATION",
    "registry_date": "2026-08-31T14:56:20.000",
    "address": "780 COMMERCIAL ST SE STE 100",
    "city": "SALEM",
    "state": "OR",
    "zip": "97301",
}

_LIVE_FIXTURE_COORDS = (
    (BLOSSOM_ROW["latitude"], BLOSSOM_ROW["longitude"]),
    (CLARENCE_ROW["latitude"], CLARENCE_ROW["longitude"]),
    (WALN_ROW["latitude"], WALN_ROW["longitude"]),
)

_SUBMARKET_FIELDS = (
    "name",
    "borough",
    "lat",
    "lng",
    "zoom",
    "pitch",
    "base_lims",
    "capex",
    "permit_vel",
    "shift_ratio",
    "sla",
    "description",
    "city_id",
)


# ---------------------------------------------------------------------------
# Spatial invariants (no registry needed)
# ---------------------------------------------------------------------------


class TestSalemSpatial:
    def test_city_id_constant_is_the_leaf_string(self):
        assert SALEM_CITY_ID == "salem_or"

    def test_metro_bbox_sanity(self):
        assert SALEM_METRO_BBOX["min_lat"] < SALEM_METRO_BBOX["max_lat"]
        assert SALEM_METRO_BBOX["min_lng"] < SALEM_METRO_BBOX["max_lng"]

    def test_metro_contains_known_places(self):
        assert is_in_salem_metro(44.9429, -123.0351) is True  # Downtown
        assert is_in_salem_metro(44.9944, -122.9942) is True  # Northgate
        assert is_in_salem_metro(44.9350, -123.0650) is True  # West Salem
        assert is_in_salem_metro(44.8760, -123.0710) is True  # South Salem

    def test_metro_rejects_null_and_foreign(self):
        assert is_in_salem_metro(None, None) is False
        assert is_in_salem_metro(45.0200, -123.0240) is False  # Keizer
        assert is_in_salem_metro(44.0000, -123.0000) is False  # Eugene
        assert is_in_salem_metro(45.5200, -122.6800) is False  # Portland

    def test_live_fixture_coords_sit_inside_metro_bbox(self):
        for lat, lng in _LIVE_FIXTURE_COORDS:
            assert is_in_salem_metro(lat, lng), (lat, lng)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in SALEM_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= SALEM_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= SALEM_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= SALEM_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= SALEM_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in SALEM_SUBMARKETS.items():
            bbox = SALEM_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in SALEM_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(SALEM_SUBMARKETS)

    def test_submarkets_carry_salem_city_id_and_all_meta_fields(self):
        from src.spatial.submarkets import SubmarketMeta

        assert {m.city_id for m in SALEM_SUBMARKETS.values()} == {"salem_or"}
        for name, meta in SALEM_SUBMARKETS.items():
            assert isinstance(meta, SubmarketMeta), name
            for field in _SUBMARKET_FIELDS:
                value = getattr(meta, field)
                assert value is not None, f"{name}.{field}"
                if field == "description":
                    assert len(value) > 20, name

    def test_submarket_count_in_leaf_band(self):
        assert 6 <= len(SALEM_SUBMARKETS) <= 10

    def test_required_real_neighborhoods_present(self):
        for name in (
            "Downtown Salem",
            "Northgate",
            "Grant-Highland",
            "Mill Creek",
            "West Salem",
            "South Salem",
            "East Lancaster",
        ):
            assert name in SALEM_SUBMARKETS, name

    def test_division_centers_sit_inside_their_bbox(self):
        assert 4 <= len(SALEM_DIVISION_BBOXES) <= 8
        assert set(SALEM_DIVISION_BBOXES) == set(SALEM_DIVISIONS)
        for name, meta in SALEM_DIVISIONS.items():
            assert meta.city_id == "salem_or"
            bbox = SALEM_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_spatial_registration_references_module_constants(self):
        assert REGISTRATION.metro_bbox is SALEM_METRO_BBOX
        assert REGISTRATION.submarkets is SALEM_SUBMARKETS
        assert REGISTRATION.divisions is SALEM_DIVISIONS
        assert REGISTRATION.contains is is_in_salem_metro

    def test_greater_metro_alias(self):
        assert is_in_greater_salem_metro is is_in_salem_metro

    def test_divisions_count(self):
        assert len(SALEM_DIVISIONS) == 6

    def test_submarkets_count(self):
        assert len(SALEM_SUBMARKETS) == 9


# ---------------------------------------------------------------------------
# Feed spec (leaf-local get_dataset mirror)
# ---------------------------------------------------------------------------


class TestFeedRegistration:
    def test_exactly_two_feed_types_are_registered(self):
        assert set(SALEM_FEED_SPECS) == {"permits", "sla"}

    def test_permits_spec_matches_live_layer(self):
        spec = get_salem_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == SALEM_PERMITS_ENDPOINT
        assert spec.watermark_col == "ISSUEDDATE"
        assert spec.id_keys == ["FOLDERNUMBER"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "ISSUEDDATE DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"

    def test_sla_spec_matches_live_layer(self):
        spec = get_salem_dataset(FeedType.SLA)
        assert spec.platform == "socrata"
        assert spec.endpoint == SALEM_SLA_ENDPOINT
        assert spec.watermark_col == "registry_date"
        assert spec.id_keys == ["registry_number", "business_name"]
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "registry_date DESC"
        assert spec.interval_seconds == 21600.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is True
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.topic == "raw.municipal.sla"

    @pytest.mark.parametrize(
        "absent_feed", [FeedType.COMPLAINTS_311, FeedType.DEEDS]
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'salem_or'.*available"):
            get_salem_dataset(absent_feed)


# ---------------------------------------------------------------------------
# Field map mechanics
# ---------------------------------------------------------------------------


class TestSalemFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["FOLDERNUMBER"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["ISSUEDDATE"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["CREATEDDATE"]
        assert PERMITS_FIELD_MAP["status"] == ["STATUS"]
        assert PERMITS_FIELD_MAP["job_type"] == ["SUBDESCRIPTION", "MAPDESCRIPTION"]
        assert PERMITS_FIELD_MAP["address_street"] == ["PROPERTYADDRESS"]
        assert PERMITS_FIELD_MAP["borough"] == ["NEIGHBORHOOD"]

    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["registry_number"]
        assert SLA_FIELD_MAP["dba"] == ["business_name"]
        assert SLA_FIELD_MAP["premises_name"] == ["business_name"]
        assert SLA_FIELD_MAP["license_type"] == ["entity_type"]
        assert SLA_FIELD_MAP["effective_date"] == ["registry_date"]
        assert SLA_FIELD_MAP["address_street"] == ["address"]
        assert SLA_FIELD_MAP["city"] == ["city"]
        assert SLA_FIELD_MAP["zipcode"] == ["zip"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP, "sla": SLA_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Salem, OR"
        assert SALEM_GEOCODE_CONTEXT == "Salem, OR"

    def test_state_plane_coordinates_are_never_candidates(self):
        """X/Y and POINT_X/POINT_Y are integer State Plane feet (OR South,
        WKID 2913, ≈7.5e6/0.5e6) — mapping them would emit feet as degrees.
        Coordinates come only from the outSR=4326 geometry lift (permits)
        or the ADR-0004 geocode supplement (SLA super-feed)."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP
        assert "latitude" not in SLA_FIELD_MAP
        assert "longitude" not in SLA_FIELD_MAP
        attrs = PERMIT_FEATURE_BLOSSOM["attributes"]
        assert attrs["X"] > 90 and attrs["Y"] > 90  # feet, not degrees
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "latitude") is None
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "longitude") is None

    def test_pii_columns_never_become_candidates(self):
        mapped = {c for cols in PERMITS_FIELD_MAP.values() for c in cols} | {
            c for cols in SLA_FIELD_MAP.values() for c in cols
        }
        assert mapped
        assert "OWNER" not in mapped
        assert "ISSUEUSER" not in mapped

    def test_zipcode_only_declared_for_the_geocoded_sla_feed(self):
        """The OR Active Businesses super-feed declares a zipcode candidate
        (its rows carry a state zip); the permits layer has no site-zip
        column, so permits stays zipcode-free."""
        assert "zipcode" not in PERMITS_FIELD_MAP
        assert "zipcode" in SLA_FIELD_MAP

    def test_permit_field_map_reads_from_flattened_fixture(self):
        row = BLOSSOM_ROW
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "26-104120-BP"
        assert (
            first_mapped(row, PERMITS_FIELD_MAP, "address_street")
            == "3121 BLOSSOM DR NE"
        )
        assert first_mapped(row, PERMITS_FIELD_MAP, "status") == "Issued"
        assert (
            first_mapped(row, PERMITS_FIELD_MAP, "borough")
            == "Northgate Neighborhood Association"
        )


# ---------------------------------------------------------------------------
# ArcGISClient flatten contract (real client code, no network)
# ---------------------------------------------------------------------------


class TestArcgisFlatten:
    def test_permits_geometry_lifts_to_wgs84(self):
        assert BLOSSOM_ROW["latitude"] == pytest.approx(44.994441445579)
        assert BLOSSOM_ROW["longitude"] == pytest.approx(-122.99423605410927)
        assert CLARENCE_ROW["latitude"] == pytest.approx(44.888522796365116)
        assert CLARENCE_ROW["longitude"] == pytest.approx(-123.05572624759341)

    def test_permits_epoch_ms_dates_flatten_to_iso(self):
        assert BLOSSOM_ROW["ISSUEDDATE"] == _ISSUEDATE_ISO
        assert BLOSSOM_ROW["CREATEDDATE"] == "2026-02-13T14:23:54+00:00"
        assert CLARENCE_ROW["ISSUEDDATE"] == "2026-08-27T15:05:13+00:00"


# ---------------------------------------------------------------------------
# Producer path with the Salem field map injected (no spine registration)
# ---------------------------------------------------------------------------


@pytest.fixture
def permits():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        return DOBPermitsProducer()


@pytest.fixture
def sla():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        return SLALicensesProducer()


class TestSalemPermitParsing:
    def test_blossom_row_parses_all_fields(self, permits, monkeypatch):
        _patch_resolve_permits(monkeypatch)
        event = permits.parse_socrata_row(BLOSSOM_ROW, city_id="salem_or")
        assert event is not None
        assert event.city_id == "salem_or"
        assert event.job_id == "26-104120-BP"
        assert event.status == "Issued"
        assert event.address_street == "3121 BLOSSOM DR NE"
        assert event.latitude == pytest.approx(44.994441445579)
        assert event.longitude == pytest.approx(-122.99423605410927)
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat() == _ISSUEDATE_ISO
        assert event.filing_date is not None
        assert event.source_neighborhood == "Northgate Neighborhood Association"
        assert event.job_type == JobType.OT
        assert event.zipcode == ""
        assert event.bbl is None
        assert event.estimated_cost == 0.0
        assert event.h3_res7 is not None

    def test_clarence_row_indexes_h3_and_sits_in_metro(self, permits, monkeypatch):
        _patch_resolve_permits(monkeypatch)
        event = permits.parse_socrata_row(CLARENCE_ROW, city_id="salem_or")
        assert event is not None
        assert event.job_id == "26-116702-DW"
        assert event.estimated_cost == 0.0
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_salem_metro(event.latitude, event.longitude)

    def test_waln_creek_fixture_parses_south_salem(self, permits, monkeypatch):
        _patch_resolve_permits(monkeypatch)
        event = permits.parse_socrata_row(WALN_ROW, city_id="salem_or")
        assert event is not None
        assert event.job_id == "26-116325-DW"
        assert event.status == "Issued"
        assert event.address_street == "1938 WALN CREEK DR S"
        assert is_in_salem_metro(event.latitude, event.longitude)

    def test_all_three_fixtures_share_the_watermark_band(self, permits, monkeypatch):
        _patch_resolve_permits(monkeypatch)
        events = [
            permits.parse_socrata_row(f, city_id="salem_or")
            for f in (BLOSSOM_ROW, CLARENCE_ROW, WALN_ROW)
        ]
        assert all(e is not None for e in events)
        iso_dates = {e.issuance_date.isoformat() for e in events}
        assert _ISSUEDATE_ISO in iso_dates

    def test_state_plane_values_never_emit_as_degrees(self, permits, monkeypatch):
        """If State Plane feet ever leaked into latitude/longitude (a bad
        future map edit), the producer's projected-coordinate guard nulls
        them; the coordinate-less row then falls to geocode and must not
        carry fake degrees."""
        _patch_resolve_permits(monkeypatch)
        record = dict(BLOSSOM_ROW)
        record["latitude"] = 7556990.0  # State Plane X feet
        record["longitude"] = 494025.0  # State Plane Y feet
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="salem_or") is None

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve_permits(monkeypatch)
        row = {k: v for k, v in BLOSSOM_ROW.items() if k != "FOLDERNUMBER"}
        assert permits.parse_socrata_row(row, city_id="salem_or") is None

    def test_city_id_string_is_accepted_verbatim_without_enum(
        self, permits, monkeypatch
    ):
        _patch_resolve_permits(monkeypatch)
        event = permits.parse_socrata_row(
            {**BLOSSOM_ROW, "FOLDERNUMBER": "99-999999-BP"},
            city_id="salem_or",
        )
        assert event is not None
        assert event.city_id == "salem_or"
        assert event.job_id == "99-999999-BP"


class TestSalemSlaParsing:
    def test_talos_fixture_parses_all_fields(self, sla, monkeypatch):
        _patch_resolve_sla(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city, feed, addr: (44.94, -123.01),
        )
        event = sla.parse_socrata_row(SLA_ROW_TALOS, city_id="salem_or")
        assert event is not None
        assert event.city_id == "salem_or"
        assert event.license_id == "262244792"
        assert event.license_type == "DOMESTIC LIMITED LIABILITY COMPANY"
        assert event.premises_name == "TALOS VENTURES LLC"
        assert event.dba == "TALOS VENTURES LLC"
        assert event.address == "942 WINDEMERE DR NW"
        assert event.license_status == "ACTIVE"
        assert event.effective_date is not None
        assert event.effective_date.year == 2026
        assert event.effective_date.month == 8
        assert event.effective_date.day == 31
        assert event.expiration_date is None
        assert event.latitude == pytest.approx(44.94)
        assert event.longitude == pytest.approx(-123.01)
        assert event.h3_res7 is not None

    def test_heart_fixture_force_of_business_name(self, sla, monkeypatch):
        _patch_resolve_sla(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city, feed, addr: (44.94, -123.01),
        )
        event = sla.parse_socrata_row(SLA_ROW_HEART, city_id="salem_or")
        assert event is not None
        assert event.license_id == "262242598"
        assert event.license_type == "ASSUMED BUSINESS NAME"
        assert event.address == "357 COURT STREET NORTHEAST"
        assert event.dba == "HEART OF SALEM MARKET PLACE COLLECTIVE"
        assert event.premises_name == "HEART OF SALEM MARKET PLACE COLLECTIVE"
        assert event.license_status == "ACTIVE"
        assert event.effective_date is not None
        assert event.h3_res7 is not None

    def test_empower_fixture_registry_date_watermark(self, sla, monkeypatch):
        _patch_resolve_sla(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city, feed, addr: (44.94, -123.01),
        )
        event = sla.parse_socrata_row(SLA_ROW_EMPOWER, city_id="salem_or")
        assert event is not None
        assert event.license_id == "261783394"
        assert event.license_type == "FOREIGN BUSINESS CORPORATION"
        assert event.address == "780 COMMERCIAL ST SE STE 100"
        assert event.effective_date is not None
        assert event.effective_date.isoformat().startswith("2026-08-31")
        assert event.h3_res7 is not None

    def test_row_without_license_id_is_dropped(self, sla, monkeypatch):
        _patch_resolve_sla(monkeypatch)
        row = {k: v for k, v in SLA_ROW_TALOS.items() if k != "registry_number"}
        assert sla.parse_socrata_row(row, city_id="salem_or") is None

    def test_city_id_string_is_accepted_verbatim(self, sla, monkeypatch):
        _patch_resolve_sla(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city, feed, addr: (44.94, -123.01),
        )
        event = sla.parse_socrata_row(
            {**SLA_ROW_TALOS, "registry_number": "99-999999"},
            city_id="salem_or",
        )
        assert event is not None
        assert event.city_id == "salem_or"
        assert event.license_id == "99-999999"
