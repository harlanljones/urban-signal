"""Unit tests for the Aurora, CO leaf (US-326): spatial module + PERMITS /
SLA field maps and parse chains.

Aurora is a Tier-1 two-feed metro: Building Permits (OpenData/MapServer/44)
and SLA (Businesses-All-Non-Home MapServer/77 + liquor MapServer/34
companion). COMPLAINTS_311 / DEEDS are Tier 3 and stay unregistered. Tests
pass WITHOUT a spine registration (no CityId.AURORA; ``city_id="aurora"``
strings only).

Live fixtures captured 2026-08-27 from ags.auroragov.org (re-probe stamped
the same day as docs/research/probe-aurora_co.md; watermarks: L44 IssueDate
2026-08-26 18:30:01Z, L34 Issue_Date 2026-08-18, L77 Issue_Date 2026-08-22).

CRS quirk pinned here: SLA ``X``/``Y`` and permits ``PropX``/``PropY`` are
NAD83 Colorado South state plane, US survey feet (EPSG:2232) — never
degrees. Coordinates come from the outSR=4326 geometry lift; the declared
EPSG:2232 transform reproduces the geometry to ~1m.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_aurora import (
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.producers.sla_licenses_producer import _transform_state_plane
from src.schemas.models import JobType
from src.spatial.cities.aurora import (
    AURORA_CITY_ID,
    AURORA_DIVISION_BBOXES,
    AURORA_DIVISIONS,
    AURORA_FEED_SPECS,
    AURORA_GEOCODE_CONTEXT,
    AURORA_METRO_BBOX,
    AURORA_PERMITS_ENDPOINT,
    AURORA_SLA_ENDPOINT,
    AURORA_SLA_LIQUOR_ENDPOINT,
    AURORA_STATE_PLANE_CRS,
    AURORA_SUBMARKETS,
    REGISTRATION,
    get_aurora_dataset,
    is_in_aurora_metro,
)
from src.spatial.city_registry import FeedType
from src.spatial.geocoder import _STATE_RE, normalize_address
from src.spatial.submarkets import SubmarketMeta

# Newest Building Permits row on the 2026-08-27 re-probe
# (IssueDate 2026-08-26T18:30:01Z). Attributes as served; latitude/longitude
# are the ArcGISClient setdefault from outSR=4326 geometry. PropX/PropY stay
# in EPSG:2232 state-plane feet.
PERMITS_ROW_1 = {
    "OBJECTID": 552631118,
    "FolderRSN": 1998494,
    "Permit_": "26-2649763-000-00",
    "InDate": "2026-08-26T18:30:01+00:00",
    "FolderType": "CT",
    "FolderDesc": "Counter Permit",
    "FolderGroupDesc": "Building",
    "SubDesc": "Mechanical Permit",
    "FolderDescription": (
        "INSTALL 60000 BTU FURNACE WITH AC UNIT --|STATE ELECTRICAL "
        "LICENSE: 000000 |  -- |COMMENTS: 2.0 TONS AC, THE ELECTRICIAN IS "
        "NEW ENERGY POWER AND HE HAS A PERMIT FOR HIS PART OF THE JOB. | "
    ),
    "FolderCondition": (
        "PERMITSONLINE  | Scope of work will be field verified.  Any work "
        "completed that is not part of the original scope of work is "
        "subject to double permit fee.  Addl. Info for inspector: 2.0 Tons "
        "AC, The electrician is New Energy Power and he has a permit for "
        "his part of the job."
    ),
    "IssueDate": "2026-08-26T18:30:01+00:00",
    "valuation": "8000.00",
    "PropertyRSN": 6978,
    "PropX": 3176233.74346255,
    "PropY": 1699437.5927189,
    "Address": "2349 N ELMIRA ST ",
    "GlobalID": "{2DB88119-408E-455D-99D8-26AB933015E5}",
    "PropertyRoll": None,
    "latitude": 39.75209876436003,
    "longitude": -104.87322609757216,
}

PERMITS_ROW_2 = {
    "OBJECTID": 552636006,
    "FolderRSN": 1998244,
    "Permit_": "26-2649515-000-00",
    "InDate": "2026-08-26T17:55:05+00:00",
    "FolderType": "LT",
    "FolderDesc": "Limited Building Permit",
    "FolderGroupDesc": "Building",
    "SubDesc": "Electrical Permit",
    "FolderDescription": (
        "BUILDINGONLINE | TONY DECONINCK ESS BATTERY INSTALL **Solar PV "
        "installation on RSN #1997500 **"
    ),
    "FolderCondition": "",
    "IssueDate": "2026-08-26T17:55:05+00:00",
    "valuation": "10170",
    "PropertyRSN": 229948,
    "PropX": 3216536.71206905,
    "PropY": 1706269.44191606,
    "Address": "22133 E 38TH PL ",
    "GlobalID": "{573C1BB7-34CC-4C22-A72D-90E2BC6D65D8}",
    "PropertyRoll": None,
    "latitude": 39.77000229037668,
    "longitude": -104.72968677729655,
}

# Newest liquor-license row on the re-probe (Issue_Date 2026-08-18).
# X/Y are EPSG:2232 feet; latitude/longitude are the outSR=4326 geometry.
LIQUOR_ROW = {
    "License_Number": "S20135051-0001-LRS",
    "Business_Owner": "A & K LIQUOR LLC",
    "NAICS_Title": "445320 - Beer, Wine, and Liquor Retailers",
    "NAICS_Sector": "44 - Retail Trade",
    "NAICS_SubSector": "445 - Food and Beverage Retailers",
    "X": 3176769.63576995,
    "Y": 1695260.5016819,
    "Addr_type": "Feature",
    "ARC_SingleKey": "",
    "entity_key": 15000135085767.0,
    "TL_License_Number": None,
    "BusinessAddress_DirSuf": "",
    "Business_Name": "PAYLESS LIQUOR",
    "Business_Address": "1512 FLORENCE ST AURORA CO 80010-2128",
    "Start_Date": "2026-07-27T00:00:00+00:00",
    "End_Date": "9999-12-31T00:00:00+00:00",
    "Min_Date": "2026-07-27T00:00:00+00:00",
    "Issue_Date": "2026-08-18T00:00:00+00:00",
    "TaxText": "Liquor - Retail Liquor Store License",
    "GlobalID": "{75B45DC5-2B0E-4BA3-8837-5FE9B78666BF}",
    "OBJECTID": 9439714,
    "gis_tag": "367341736",
    "BusinessAddress_ZIP": "800102128",
    "naics_code": "445320",
    "home_based": 0,
    "latitude": 39.740621849578886,
    "longitude": -104.8714230197769,
}

# Newest non-home business row on the re-probe (Issue_Date 2026-08-22).
BUSINESS_ROW = {
    "OBJECTID": 9439724,
    "License_Number": "S20053057-0004",
    "Business_Name": "BEE LINE MEDICAL SUPPLY",
    "Business_Owner": "BEE LINE LLC",
    "Business_Address": "1411 S POTOMAC ST STE 190 AURORA CO 80012-4542",
    "naics_code": "456199",
    "NAICS_Title": "456199 - All Other Health and Personal Care Retailers",
    "NAICS_Sector": "45 - Retail Trade",
    "NAICS_SubSector": "456 - Health and Personal Care Retailers",
    "home_based": 0,
    "GlobalID": "{DBF4661F-6B39-412B-9797-5389641DE643}",
    "X": 3187796.50152986,
    "Y": 1677280.30991657,
    "entity_key": 15000138422185.0,
    "TL_License_Number": None,
    "BusinessAddress_DirSuf": "",
    "Start_Date": "2026-08-01T00:00:00+00:00",
    "End_Date": "9999-12-31T00:00:00+00:00",
    "Min_Date": "2026-08-01T00:00:00+00:00",
    "Issue_Date": "2026-08-22T00:00:00+00:00",
    "TaxText": "Business - Business License",
    "latitude": 39.69104710930661,
    "longitude": -104.83268285260195,
}

# State-plane-only rows: null geometry means ArcGISClient lifted no
# latitude/longitude; X/Y (and PropX/PropY) remain EPSG:2232 feet.
PERMITS_STATE_PLANE_ONLY = {
    k: v for k, v in PERMITS_ROW_2.items() if k not in {"latitude", "longitude"}
}
SLA_STATE_PLANE_ONLY = {
    k: v for k, v in LIQUOR_ROW.items() if k not in {"latitude", "longitude"}
}

LIVE_FIXTURE_COORDS = (
    (PERMITS_ROW_1["latitude"], PERMITS_ROW_1["longitude"]),
    (PERMITS_ROW_2["latitude"], PERMITS_ROW_2["longitude"]),
    (LIQUOR_ROW["latitude"], LIQUOR_ROW["longitude"]),
    (BUSINESS_ROW["latitude"], BUSINESS_ROW["longitude"]),
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


class TestAuroraSpatial:
    def test_city_id_constant(self):
        assert AURORA_CITY_ID == "aurora"

    def test_metro_contains_known_places(self):
        assert is_in_aurora_metro(39.7433, -104.8342) is True  # Anschutz
        assert is_in_aurora_metro(39.7405, -104.8680) is True  # Original Aurora
        assert is_in_aurora_metro(39.7740, -104.7460) is True  # Aurora Highlands
        assert is_in_aurora_metro(39.6000, -104.7300) is True  # Southlands
        assert is_in_aurora_metro(39.7866, -104.7952) is True  # Painted Prairie

    def test_metro_includes_county_fringe_context(self):
        # Probe contract: metro bbox is city + enough Arapahoe/Adams
        # county context, so Centennial sits inside while downtown Denver
        # does not.
        assert is_in_aurora_metro(39.5807, -104.8772) is True  # Centennial
        assert is_in_aurora_metro(39.7392, -104.9903) is False  # Denver
        assert is_in_aurora_metro(40.0150, -105.2705) is False  # Boulder
        assert is_in_aurora_metro(38.8339, -104.8214) is False  # Colo. Springs

    def test_metro_rejects_null(self):
        assert is_in_aurora_metro(None, None) is False

    def test_live_fixture_coords_sit_inside_the_metro_bbox(self):
        for lat, lng in LIVE_FIXTURE_COORDS:
            assert is_in_aurora_metro(lat, lng), (lat, lng)

    def test_live_fixture_coords_land_in_exactly_one_division(self):
        for lat, lng in LIVE_FIXTURE_COORDS:
            hits = [
                name
                for name, bbox in AURORA_DIVISION_BBOXES.items()
                if bbox["min_lat"] <= lat <= bbox["max_lat"]
                and bbox["min_lng"] <= lng <= bbox["max_lng"]
            ]
            assert len(hits) == 1, (lat, lng, hits)

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in AURORA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= AURORA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= AURORA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= AURORA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= AURORA_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in AURORA_SUBMARKETS.items():
            bbox = AURORA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in AURORA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(AURORA_SUBMARKETS)

    def test_submarkets_carry_aurora_city_id_and_all_meta_fields(self):
        assert {m.city_id for m in AURORA_SUBMARKETS.values()} == {"aurora"}
        assert 6 <= len(AURORA_SUBMARKETS) <= 10
        for name, meta in AURORA_SUBMARKETS.items():
            assert isinstance(meta, SubmarketMeta), name
            for field in _SUBMARKET_FIELDS:
                value = getattr(meta, field)
                assert value is not None, f"{name}.{field}"
                if field == "description":
                    assert len(value) > 20, name

    def test_division_count_and_centers(self):
        assert 4 <= len(AURORA_DIVISIONS) <= 8
        for name, meta in AURORA_DIVISIONS.items():
            assert meta.city_id == "aurora"
            bbox = AURORA_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_spatial_registration_references_module_constants(self):
        assert REGISTRATION.metro_bbox is AURORA_METRO_BBOX
        assert REGISTRATION.submarkets is AURORA_SUBMARKETS
        assert REGISTRATION.divisions is AURORA_DIVISIONS
        assert REGISTRATION.contains is is_in_aurora_metro


class TestFeedRegistration:
    def test_exactly_two_feed_types_are_registered(self):
        assert set(AURORA_FEED_SPECS) == {"permits", "sla"}

    def test_permits_spec_matches_live_layer(self):
        spec = get_aurora_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == AURORA_PERMITS_ENDPOINT
        assert spec.watermark_col == "IssueDate"
        assert spec.id_keys == ["Permit_", "FolderRSN", "OBJECTID"]
        assert spec.producer_key == "permits"
        assert spec.expected_cadence_days == 1
        assert spec.needs_geocode is False
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.order_by == "IssueDate DESC"
        assert spec.state_plane_crs == "EPSG:2232"
        assert spec.state_plane_x_col == "PropX"
        assert spec.state_plane_y_col == "PropY"
        assert spec.field_map is PERMITS_FIELD_MAP

    def test_sla_spec_is_snapshot_with_state_plane_declared(self):
        spec = get_aurora_dataset(FeedType.SLA)
        assert spec.platform == "arcgis"
        assert spec.endpoint == AURORA_SLA_ENDPOINT
        assert spec.watermark_col == "Issue_Date"
        assert spec.ingestion_mode == "snapshot"
        assert spec.id_keys == ["License_Number", "entity_key", "OBJECTID"]
        assert spec.producer_key == "sla"
        assert spec.expected_cadence_days == 1
        assert spec.needs_geocode is False
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.order_by == "Issue_Date DESC"
        assert spec.state_plane_crs == "EPSG:2232"
        assert spec.state_plane_units == "ftUS"
        assert spec.state_plane_x_col == "X"
        assert spec.state_plane_y_col == "Y"
        assert spec.field_map is SLA_FIELD_MAP
        assert spec.companion_endpoints["liquor"] == AURORA_SLA_LIQUOR_ENDPOINT

    def test_sla_companions_are_metadata_only(self):
        """Scheduler does not poll companion_endpoints; they stay off FEED_SPECS."""
        assert "liquor" not in AURORA_FEED_SPECS
        assert "all_businesses" not in AURORA_FEED_SPECS
        assert "marijuana" not in AURORA_FEED_SPECS

    @pytest.mark.parametrize(
        "absent_feed", [FeedType.COMPLAINTS_311, FeedType.DEEDS, FeedType.STR]
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'aurora'.*available"):
            get_aurora_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert FIELD_MAP["permits"] is PERMITS_FIELD_MAP
        assert FIELD_MAP["sla"] is SLA_FIELD_MAP
        assert GEOCODE_CONTEXT == AURORA_GEOCODE_CONTEXT == "Aurora, CO"
        assert "311" not in FIELD_MAP
        assert "deeds" not in FIELD_MAP


class TestAuroraFieldMaps:
    def test_permits_map_reads_live_columns(self):
        row = PERMITS_ROW_1
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "26-2649763-000-00"
        assert (
            first_mapped(row, PERMITS_FIELD_MAP, "issuance_date")
            == "2026-08-26T18:30:01+00:00"
        )
        assert (
            first_mapped(row, PERMITS_FIELD_MAP, "filing_date")
            == "2026-08-26T18:30:01+00:00"
        )
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_type") == "Counter Permit"
        assert first_mapped(row, PERMITS_FIELD_MAP, "status").startswith("PERMITSONLINE")
        assert first_mapped(row, PERMITS_FIELD_MAP, "cost") == "8000.00"
        assert first_mapped(row, PERMITS_FIELD_MAP, "address_street") == "2349 N ELMIRA ST "

    def test_permits_job_id_falls_back_when_permit_number_is_null(self):
        row = {"Permit_": None, "FolderRSN": 1998494, "OBJECTID": 552631118}
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == 1998494

    def test_permits_map_never_maps_state_plane_or_xy_as_coordinates(self):
        mapped = {c for cols in PERMITS_FIELD_MAP.values() for c in cols}
        for col in ("PropX", "PropY", "X", "Y", "latitude", "longitude"):
            assert col not in mapped, col

    def test_sla_map_reads_live_columns(self):
        row = LIQUOR_ROW
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "S20135051-0001-LRS"
        assert first_mapped(row, SLA_FIELD_MAP, "dba") == "PAYLESS LIQUOR"
        assert first_mapped(row, SLA_FIELD_MAP, "premises_name") == "A & K LIQUOR LLC"
        assert (
            first_mapped(row, SLA_FIELD_MAP, "license_type")
            == "Liquor - Retail Liquor Store License"
        )
        assert (
            first_mapped(row, SLA_FIELD_MAP, "effective_date")
            == "2026-07-27T00:00:00+00:00"
        )
        assert (
            first_mapped(row, SLA_FIELD_MAP, "expiration_date")
            == "9999-12-31T00:00:00+00:00"
        )
        assert (
            first_mapped(row, SLA_FIELD_MAP, "address_street")
            == "1512 FLORENCE ST AURORA CO 80010-2128"
        )

    def test_sla_license_id_falls_back_to_objectid(self):
        row = {"License_Number": None, "TL_License_Number": None, "OBJECTID": 9439714}
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == 9439714

    def test_sla_map_never_maps_xy_as_coordinates(self):
        """X/Y are EPSG:2232 feet — and the SLA parser has no out-of-range
        guard, so mapping them as degrees would poison every event."""
        mapped = {c for cols in SLA_FIELD_MAP.values() for c in cols}
        assert "X" not in mapped
        assert "Y" not in mapped
        assert "latitude" not in SLA_FIELD_MAP
        assert "longitude" not in SLA_FIELD_MAP

    def test_sla_license_type_prefers_taxtext(self):
        assert SLA_FIELD_MAP["license_type"][0] == "TaxText"
        assert first_mapped(BUSINESS_ROW, SLA_FIELD_MAP, "license_type") == (
            "Business - Business License"
        )


class TestStatePlaneCRS:
    """EPSG:2232 (NAD83 Colorado South ftUS) → EPSG:4326, live-verified.

    The declared transform reproduces each row's outSR=4326 geometry to
    ~1m, so the spine can wire a Boston-style fallback for null-geometry
    rows without a new transform path.
    """

    @pytest.mark.parametrize(
        "row", [PERMITS_ROW_1, PERMITS_ROW_2], ids=["permits-1", "permits-2"]
    )
    def test_permits_propxy_transform_reproduces_geometry(self, row):
        got = _transform_state_plane(
            row, AURORA_STATE_PLANE_CRS, x_col="PropX", y_col="PropY"
        )
        assert got is not None
        lng, lat = got
        assert lat == pytest.approx(row["latitude"], abs=2e-5)
        assert lng == pytest.approx(row["longitude"], abs=2e-5)
        assert is_in_aurora_metro(lat, lng)

    @pytest.mark.parametrize(
        "row", [LIQUOR_ROW, BUSINESS_ROW], ids=["liquor", "business"]
    )
    def test_sla_xy_transform_reproduces_geometry(self, row):
        got = _transform_state_plane(row, AURORA_STATE_PLANE_CRS, x_col="X", y_col="Y")
        assert got is not None
        lng, lat = got
        assert lat == pytest.approx(row["latitude"], abs=2e-5)
        assert lng == pytest.approx(row["longitude"], abs=2e-5)
        assert is_in_aurora_metro(lat, lng)

    def test_state_plane_only_row_yields_no_transform_degrees_in_row(self):
        # The raw flattened row keeps feet in the attribute pair; the
        # coordinates must come from the transform (or be absent), never
        # from the attributes read as degrees.
        assert abs(PERMITS_STATE_PLANE_ONLY["PropY"]) > 90
        assert abs(SLA_STATE_PLANE_ONLY["Y"]) > 90
        assert first_mapped(PERMITS_STATE_PLANE_ONLY, PERMITS_FIELD_MAP, "latitude") is None
        assert first_mapped(SLA_STATE_PLANE_ONLY, SLA_FIELD_MAP, "latitude") is None


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


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


class TestAuroraPermitParsing:
    def test_counter_permit_parses_geometry_without_geocoder(
        self, permits, monkeypatch
    ):
        _patch_resolve(monkeypatch, "permits")
        with patch(
            "src.spatial.geocoder.geocode_row_if_declared", return_value=(0.0, 0.0)
        ) as geocode:
            event = permits.parse_socrata_row(PERMITS_ROW_1, city_id="aurora")
        assert event is not None
        assert event.city_id == "aurora"
        assert event.job_id == "26-2649763-000-00"
        assert event.job_type == JobType.OT
        assert str(event.issuance_date).startswith("2026-08-26")
        assert str(event.filing_date).startswith("2026-08-26")
        assert event.estimated_cost == pytest.approx(8000.0)
        assert event.address_street == "2349 N ELMIRA ST "
        assert event.status.startswith("PERMITSONLINE")
        assert event.latitude == pytest.approx(39.75209876436003)
        assert event.longitude == pytest.approx(-104.87322609757216)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        geocode.assert_not_called()

    def test_limited_permit_parses_and_fixture_lands_in_metro(
        self, permits, monkeypatch
    ):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(PERMITS_ROW_2, city_id="aurora")
        assert event is not None
        assert event.city_id == "aurora"
        assert event.job_id == "26-2649515-000-00"
        assert event.estimated_cost == pytest.approx(10170.0)
        assert event.latitude == pytest.approx(39.77000229037668)
        assert event.longitude == pytest.approx(-104.72968677729655)
        assert is_in_aurora_metro(event.latitude, event.longitude)
        assert event.h3_res7 is not None

    def test_state_plane_only_permit_row_is_dropped_not_geocoded(
        self, permits, monkeypatch
    ):
        """Null-geometry rows (≈5.1% PropX nulls aside) have no coordinate
        path under needs_geocode=False — they must drop, never emit feet."""
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            PERMITS_STATE_PLANE_ONLY, city_id="aurora"
        )
        assert event is None

    def test_permit_event_h3_matches_fixture_location(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(PERMITS_ROW_1, city_id="aurora")
        assert event is not None
        # res-7 cell of the fixture coordinate is non-trivially the event's
        # own tag (same point, no snapping involved).
        from src.spatial.h3_indexer import H3SpatialIndexer

        expected = H3SpatialIndexer().get_multi_res_hierarchy(
            PERMITS_ROW_1["latitude"], PERMITS_ROW_1["longitude"]
        )
        assert event.h3_res7 == expected["h3_res7"]


class TestAuroraSlaParsing:
    def test_liquor_row_parses_geometry_without_geocoder(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        with patch(
            "src.spatial.geocoder.geocode_row_if_declared", return_value=(0.0, 0.0)
        ) as geocode:
            event = sla.parse_socrata_row(LIQUOR_ROW, city_id="aurora")
        assert event is not None
        assert event.city_id == "aurora"
        assert event.license_id == "S20135051-0001-LRS"
        assert event.dba == "PAYLESS LIQUOR"
        assert event.premises_name == "A & K LIQUOR LLC"
        assert event.license_type == "Liquor - Retail Liquor Store License"
        assert event.address == "1512 FLORENCE ST AURORA CO 80010-2128"
        assert event.license_status == "ACTIVE"
        assert event.latitude == pytest.approx(39.740621849578886)
        assert event.longitude == pytest.approx(-104.8714230197769)
        assert event.h3_res7 is not None
        assert str(event.effective_date).startswith("2026-07-27")
        assert event.expiration_date is not None
        assert event.expiration_date.year == 9999  # perpetual-license sentinel
        geocode.assert_not_called()

    def test_business_row_parses_and_fixture_lands_in_metro(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(BUSINESS_ROW, city_id="aurora")
        assert event is not None
        assert event.city_id == "aurora"
        assert event.license_id == "S20053057-0004"
        assert event.dba == "BEE LINE MEDICAL SUPPLY"
        assert event.license_type == "Business - Business License"
        assert str(event.effective_date).startswith("2026-08-01")
        assert event.latitude == pytest.approx(39.69104710930661)
        assert event.longitude == pytest.approx(-104.83268285260195)
        assert is_in_aurora_metro(event.latitude, event.longitude)
        assert event.h3_res7 is not None

    def test_state_plane_only_sla_row_emits_null_coords_never_feet(
        self, sla, monkeypatch
    ):
        """Snapshot grain: null-geometry license rows keep flowing as
        null-coordinate events; X/Y feet must never become coordinates."""
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(SLA_STATE_PLANE_ONLY, city_id="aurora")
        assert event is not None
        assert event.license_id == "S20135051-0001-LRS"
        assert event.latitude is None
        assert event.longitude is None
        assert event.latitude != LIQUOR_ROW["Y"]
        assert event.h3_res7 is None


class TestGeocodingCaveats:
    def test_permit_street_has_no_state_token_so_context_appends(self):
        # needs_geocode is False for aurora, so this path is dead in
        # production; pinned for ADR-0004 parity with sibling leaves.
        assert _STATE_RE.search("2349 N ELMIRA ST".upper()) is None

    def test_sla_address_carries_a_state_token(self):
        assert (
            _STATE_RE.search("1512 FLORENCE ST AURORA CO 80010-2128".upper())
            is not None
        )

    def test_unit_designator_normalization_preserves_city(self):
        norm = normalize_address("1411 S POTOMAC ST STE 190, AURORA, CO")
        assert "SUITE" not in norm
        assert "AURORA" in norm
