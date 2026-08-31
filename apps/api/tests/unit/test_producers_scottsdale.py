"""Unit tests for the Scottsdale, AZ leaf (US-227): spatial module + field
maps + producer parse wiring.

Scottsdale is a TWO-FEED PARTIAL metro on the city ArcGIS Server 10.6
(``maps.scottsdaleaz.gov``): Building Permits (``OpenData_Tabular/
MapServer/12``, 288,121 rows, native WGS84 Latitude/Longitude attributes)
and Business Licenses (``OpenData_Tabular/MapServer/6``, 19,944 rows,
address-only with future-dated sentinels). ``data.scottsdaleaz.gov`` is an
ArcGIS Hub portal, not Socrata; 311-family (code-enforcement layers only)
and deeds (Maricopa recorder 403s anonymous probes) are rejected. Tests
pass WITHOUT a spine registration (no CityId.SCOTTSDALE; ``city_id=
"scottsdale"`` strings only).

Wave contract: these tests do NOT assert division/borough resolution
results or geocode-hook call counts (both change when the spine lands) —
they pin parse fields, source passthrough, H3 from fixture coordinates,
bbox containment, and field-map mappings.

Live fixtures captured byte-verbatim 2026-08-28 from the two probed
tables (newest rows via ``orderByFields`` DESC at the server default SR):
permits watermark 1787270400000 = 2026-08-21T00:00:00+00:00; licenses
newest guarded row shares that watermark. Fixtures are RAW ArcGIS table
features (attributes only — the registered endpoints carry no geometry);
the tests run the real ``ArcGISClient._flatten_feature`` lift — epoch-ms
to ISO — before parsing, exactly as the live producer path does.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from src.producers.acquisition import build_where, is_future_watermark
from src.producers.field_maps import first_mapped
from src.producers.field_maps_scottsdale import (
    DROPPED_NONADDRESS_COLUMNS,
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.producers.sla_licenses_producer import _parse_datetime
from src.producers.watermarks import ANSI_DATE_LITERAL_HOSTS, watermark_exclude_clause
from src.schemas.models import JobType
from src.spatial.cities.scottsdale import (
    REGISTRATION,
    SCOTTSDALE_CITY_ID,
    SCOTTSDALE_DIVISION_BBOXES,
    SCOTTSDALE_DIVISIONS,
    SCOTTSDALE_FEED_SPECS,
    SCOTTSDALE_GEOCODE_CONTEXT,
    SCOTTSDALE_METRO_BBOX,
    SCOTTSDALE_PERMITS_ENDPOINT,
    SCOTTSDALE_SLA_ENDPOINT,
    SCOTTSDALE_SLA_WHERE,
    SCOTTSDALE_SUBMARKETS,
    get_scottsdale_dataset,
    is_in_greater_scottsdale_metro,
    is_in_scottsdale_metro,
)
from src.spatial.city_registry import FeedType
from src.spatial.h3_indexer import H3SpatialIndexer
from src.spatial.submarkets import SubmarketMeta

# ---------------------------------------------------------------------------
# Live fixtures (byte-verbatim attributes from the 2026-08-28 probes).
# Raw features are {"attributes": {...}} only — both registered endpoints
# are standalone ArcGIS tables and return no geometry key.
# ---------------------------------------------------------------------------

# Newest permit (IssueDate 2026-08-21) — null Latitude/Longitude, north
# Scottsdale custom-home build.
PERMIT_A = {
    "attributes": {
        "APN": "212-10-004D",
        "Address": "27231 N 65TH PL",
        "AirConditionedSQFT": 3970,
        "Builder": "Vista Montana Builders",
        "CityOfScottsdaleMap": "http://eservices.scottsdaleaz.gov/dmc/mapframe.aspx?mapcmd=centroid&CentroidID=40182",
        "CoveredSQFT": 2127,
        "FenceFT": 260,
        "IssueDate": 1787270400000,
        "Latitude": None,
        "Longitude": None,
        "LotNumber": "",
        "LotSQFT": 59319,
        "Owner": "Christopher DeHerrera and Tim Vaudt",
        "PermitNumber": 324344,
        "PermitStatus": "ACTIVE",
        "PermitType": "SFR-CUSTOM IN SUBDIVISION",
        "QuarterSectionNumber": "49-43",
        "ResponsibleParty": "GREEN STUDIO",
        "Subdivision": "",
        "TotalFee": 6124.58,
        "Valuation": 812094.7,
        "Zone": "R1-43 ESL FO",
        "permit_id": 324348,
    }
}

# Newest geocoded permit (IssueDate 2026-08-20) — CAVASSON tenant
# improvement carrying native WGS84 attribute coordinates.
PERMIT_B = {
    "attributes": {
        "APN": "212-34-959A",
        "Address": "18700 N HAYDEN RD UNIT 250",
        "AirConditionedSQFT": 200,
        "Builder": None,
        "CityOfScottsdaleMap": "http://eservices.scottsdaleaz.gov/dmc/mapframe.aspx?mapcmd=centroid&CentroidID=1524575",
        "CoveredSQFT": None,
        "FenceFT": 0,
        "IssueDate": 1787184000000,
        "Latitude": 33.6564984,
        "Longitude": -111.90865983,
        "LotNumber": "",
        "LotSQFT": 0,
        "Owner": "Nationwide Reality Investors - Gregory J Williams",
        "PermitNumber": 324334,
        "PermitStatus": "ACTIVE",
        "PermitType": "TENANT IMPROVEMENT",
        "QuarterSectionNumber": "39-46",
        "ResponsibleParty": None,
        "Subdivision": "LOT 1A OF CAVASSON",
        "TotalFee": 488.4,
        "Valuation": 16753.8,
        "Zone": "",
        "permit_id": 324338,
    }
}

# Second-newest null-coordinate permit (IssueDate 2026-08-21) — south
# Scottsdale remodel.
PERMIT_C = {
    "attributes": {
        "APN": "129-32-135",
        "Address": "6708 E WILSHIRE DR",
        "AirConditionedSQFT": 480,
        "Builder": "OWNER BUILDER",
        "CityOfScottsdaleMap": "http://eservices.scottsdaleaz.gov/dmc/mapframe.aspx?mapcmd=centroid&CentroidID=18482",
        "CoveredSQFT": 0,
        "FenceFT": 0,
        "IssueDate": 1787270400000,
        "Latitude": None,
        "Longitude": None,
        "LotNumber": "134",
        "LotSQFT": 0,
        "Owner": "Weston  Warner",
        "PermitNumber": 324342,
        "PermitStatus": "ACTIVE",
        "PermitType": "SFR-REMODEL",
        "QuarterSectionNumber": "14-43",
        "ResponsibleParty": "Weston  Warner",
        "Subdivision": "OAK PARK UNIT THREE",
        "TotalFee": 372.36,
        "Valuation": 24348.96,
        "Zone": "R1-7",
        "permit_id": 324346,
    }
}

# Newest GUARDED license (BusinessStartDate 2026-08-21) — Old Town retail.
LIC_APEX = {
    "attributes": {
        "AcctNum": "2045469",
        "AcctStatus": "Active",
        "BusinessStartDate": 1787270400000,
        "Company": "APEX APPLIANCES",
        "ESRI_OID": 1,
        "LicType": "BRM",
        "MailAddrCityStateZipComp": "GILBERT AZ 85233",
        "MailAddrComp": "1235 S PUEBLO COURT C/O TODD L SPAIN",
        "OBJECTID": 19901,
        "ServAddrComp": "7901 E THOMAS RD STE 110",
        "ServCityStateZipComp": "SCOTTSDALE AZ 85251",
    }
}

# Second-newest guarded license (BusinessStartDate 2026-08-19).
LIC_STUDS = {
    "attributes": {
        "AcctNum": "2045499",
        "AcctStatus": "Active",
        "BusinessStartDate": 1787097600000,
        "Company": "STUDS INC",
        "ESRI_OID": 3,
        "LicType": "BRM",
        "MailAddrCityStateZipComp": "NEW YORK NY 10012",
        "MailAddrComp": "594 BROADWAY SUITE 200",
        "OBJECTID": 19911,
        "ServAddrComp": "7014 E CAMELBACK RD STE 2216",
        "ServCityStateZipComp": "SCOTTSDALE AZ 85251",
    }
}

# Newest UNGUARDED row on the live layer — the year-5202 garbage sentinel
# (epoch-ms 102014035200000; AcctStatus Inactive). This is why the spec
# where guard exists.
LIC_SENTINEL = {
    "attributes": {
        "AcctNum": "2045476",
        "AcctStatus": "Inactive",
        "BusinessStartDate": 102014035200000,
        "Company": "BOOTS AND BEER",
        "ESRI_OID": 5,
        "LicType": "BRM",
        "MailAddrCityStateZipComp": "AUSTIN TX 78738",
        "MailAddrComp": "2101 SEA EAGLE VIEW ",
        "OBJECTID": 19906,
        "ServAddrComp": "7014 E CAMELBACK RD STE 545",
        "ServCityStateZipComp": "SCOTTSDALE AZ 85251",
    }
}

# Forward-dated Active application (2026-11-19) — a rolling future sentinel
# the static NOT IN form can never pin.
LIC_QUIKTRIP = {
    "attributes": {
        "AcctNum": "2037670",
        "AcctStatus": "Active",
        "BusinessStartDate": 1795046400000,
        "Company": "QUIKTRIP 480",
        "ESRI_OID": 7,
        "LicType": "BRM",
        "MailAddrCityStateZipComp": "TULSA OK 74134-7005",
        "MailAddrComp": "4705 S 129TH EAST AVE ",
        "OBJECTID": 18141,
        "ServAddrComp": "19605 N SCOTTSDALE RD  ",
        "ServCityStateZipComp": "SCOTTSDALE AZ 85255",
    }
}


def _flatten(feature: dict) -> dict:
    """Flatten a raw ArcGIS table feature exactly as the client does at fetch."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, set(feature["attributes"].keys()) & {"IssueDate", "BusinessStartDate"})


PERMIT_A_ROW = _flatten(PERMIT_A)
PERMIT_B_ROW = _flatten(PERMIT_B)
PERMIT_C_ROW = _flatten(PERMIT_C)
LIC_APEX_ROW = _flatten(LIC_APEX)
LIC_STUDS_ROW = _flatten(LIC_STUDS)
LIC_SENTINEL_ROW = _flatten(LIC_SENTINEL)
LIC_QUIKTRIP_ROW = _flatten(LIC_QUIKTRIP)

# Live WGS84 attribute coordinates on the CAVASSON fixture.
_CAVASSON = (33.6564984, -111.90865983)

# Downtown Scottsdale WGS84 (geocoder stub for null-coordinate rows).
_GEOCODED = (33.4926, -111.9253)

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


class TestScottsdaleSpatial:
    def test_city_id_constant_is_the_leaf_string(self):
        assert SCOTTSDALE_CITY_ID == "scottsdale"

    def test_metro_contains_known_places(self):
        assert is_in_scottsdale_metro(33.4926, -111.9253) is True   # Old Town
        assert is_in_scottsdale_metro(33.6229, -111.9103) is True   # Airpark
        assert is_in_scottsdale_metro(33.6562, -111.9168) is True   # DC Ranch
        assert is_in_scottsdale_metro(33.7060, -111.9090) is True   # Troon
        assert is_in_scottsdale_metro(33.4640, -111.9255) is True   # Los Arcos

    def test_metro_rejects_null_and_foreign(self):
        assert is_in_scottsdale_metro(None, None) is False
        assert is_in_scottsdale_metro(33.4484, None) is False
        assert is_in_scottsdale_metro(None, -111.9253) is False
        assert is_in_scottsdale_metro(33.4484, -112.0740) is False  # Phoenix
        assert is_in_scottsdale_metro(33.4255, -111.9400) is False  # Tempe
        assert is_in_scottsdale_metro(33.4152, -111.8315) is False  # Mesa
        assert is_in_scottsdale_metro(33.6117, -111.7258) is False  # Fountain Hills

    def test_live_fixture_coordinates_are_contained(self):
        assert is_in_scottsdale_metro(*_CAVASSON)

    def test_cavasson_fixture_lands_in_dc_ranch(self):
        bbox = SCOTTSDALE_DIVISION_BBOXES["DC_RANCH"]
        assert bbox["min_lat"] <= _CAVASSON[0] <= bbox["max_lat"]
        assert bbox["min_lng"] <= _CAVASSON[1] <= bbox["max_lng"]

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in SCOTTSDALE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= SCOTTSDALE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= SCOTTSDALE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= SCOTTSDALE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= SCOTTSDALE_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in SCOTTSDALE_SUBMARKETS.items():
            bbox = SCOTTSDALE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in SCOTTSDALE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(SCOTTSDALE_SUBMARKETS)

    def test_division_and_submarket_counts_in_leaf_bands(self):
        assert 4 <= len(SCOTTSDALE_DIVISION_BBOXES) <= 10
        assert 6 <= len(SCOTTSDALE_SUBMARKETS) <= 10
        assert len(SCOTTSDALE_DIVISIONS) == len(SCOTTSDALE_DIVISION_BBOXES)

    def test_required_real_districts_present(self):
        assert set(SCOTTSDALE_DIVISION_BBOXES) == {
            "OLD_TOWN",
            "SOUTH_SCOTTSDALE",
            "GAINEY_RANCH",
            "AIRPARK",
            "DC_RANCH",
            "NORTH_SCOTTSDALE",
        }
        for name in (
            "Old Town Scottsdale",
            "Arts District",
            "Los Arcos Corridor",
            "SkySong District",
            "Gainey Village",
            "Scottsdale Airpark",
            "DC Ranch / Market Street",
            "Cavasson Corridor",
            "Troon",
            "Desert Highlands / Happy Valley",
        ):
            assert name in SCOTTSDALE_SUBMARKETS, name

    def test_submarkets_carry_scottsdale_city_id_and_all_meta_fields(self):
        assert {m.city_id for m in SCOTTSDALE_SUBMARKETS.values()} == {"scottsdale"}
        for name, meta in SCOTTSDALE_SUBMARKETS.items():
            assert isinstance(meta, SubmarketMeta), name
            for field in _SUBMARKET_FIELDS:
                value = getattr(meta, field)
                assert value is not None, f"{name}.{field}"
                if field == "description":
                    assert len(value) > 20, name

    def test_division_centers_sit_inside_their_bbox(self):
        assert set(SCOTTSDALE_DIVISION_BBOXES) == set(SCOTTSDALE_DIVISIONS)
        for name, meta in SCOTTSDALE_DIVISIONS.items():
            assert meta.city_id == "scottsdale"
            bbox = SCOTTSDALE_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_spatial_registration_references_module_constants(self):
        assert REGISTRATION.metro_bbox is SCOTTSDALE_METRO_BBOX
        assert REGISTRATION.submarkets is SCOTTSDALE_SUBMARKETS
        assert REGISTRATION.division_bboxes is SCOTTSDALE_DIVISION_BBOXES
        assert REGISTRATION.divisions is SCOTTSDALE_DIVISIONS
        assert REGISTRATION.contains is is_in_scottsdale_metro

    def test_greater_metro_alias(self):
        assert is_in_greater_scottsdale_metro is is_in_scottsdale_metro


# ---------------------------------------------------------------------------
# Field map mechanics
# ---------------------------------------------------------------------------


class TestScottsdaleFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["PermitNumber", "permit_id"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["IssueDate"]
        assert PERMITS_FIELD_MAP["status"] == ["PermitStatus"]
        assert PERMITS_FIELD_MAP["job_type"] == ["PermitType"]
        assert PERMITS_FIELD_MAP["cost"] == ["Valuation"]
        assert PERMITS_FIELD_MAP["address_street"] == ["Address"]
        assert PERMITS_FIELD_MAP["latitude"] == ["Latitude"]
        assert PERMITS_FIELD_MAP["longitude"] == ["Longitude"]

    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["AcctNum"]
        assert SLA_FIELD_MAP["dba"] == ["Company"]
        assert SLA_FIELD_MAP["premises_name"] == ["Company"]
        assert SLA_FIELD_MAP["license_type"] == ["LicType"]
        assert SLA_FIELD_MAP["status"] == ["AcctStatus"]
        assert SLA_FIELD_MAP["effective_date"] == ["BusinessStartDate"]
        assert SLA_FIELD_MAP["address_street"] == ["ServAddrComp"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP, "sla": SLA_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Scottsdale, AZ"
        assert SCOTTSDALE_GEOCODE_CONTEXT == "Scottsdale, AZ"

    def test_permit_latitude_candidates_are_native_wgs84_attributes(self):
        """Unlike the Tucson store-SR discipline, the permits table exposes
        real WGS84 Latitude/Longitude attribute columns (live: 33.6564984 /
        -111.90865983) — they are the primary locator and ARE candidates;
        nulls fall to the ADR-0004 geocode supplement."""
        row = PERMIT_B_ROW
        assert first_mapped(row, PERMITS_FIELD_MAP, "latitude") == pytest.approx(_CAVASSON[0])
        assert first_mapped(row, PERMITS_FIELD_MAP, "longitude") == pytest.approx(_CAVASSON[1])
        null_row = PERMIT_A_ROW
        assert first_mapped(null_row, PERMITS_FIELD_MAP, "latitude") is None
        assert first_mapped(null_row, PERMITS_FIELD_MAP, "longitude") is None

    def test_sla_declares_no_coordinate_candidates(self):
        mapped = {c for cols in SLA_FIELD_MAP.values() for c in cols}
        assert "latitude" not in mapped
        assert "longitude" not in mapped
        assert "Shape" not in mapped

    def test_mixed_zip_column_is_never_a_zipcode_candidate(self):
        """ServCityStateZipComp is 'SCOTTSDALE AZ 85251' — a combined
        city-state-zip string that must never emit as a zip; zipcode stays
        undeclared on both feeds."""
        assert "zipcode" not in PERMITS_FIELD_MAP
        assert "zipcode" not in SLA_FIELD_MAP
        assert "ServCityStateZipComp" in DROPPED_NONADDRESS_COLUMNS
        assert first_mapped(LIC_APEX_ROW, SLA_FIELD_MAP, "zipcode") is None

    def test_esri_oid_is_never_a_candidate(self):
        """The reported OID field is per-query unstable (OBJECTID 19901
        returned ESRI_OID 27 and 1 across two live probes) — the stable
        OBJECTID attribute carries the row key instead."""
        mapped = {c for cols in SLA_FIELD_MAP.values() for c in cols}
        assert "ESRI_OID" not in mapped
        assert "ESRI_OID" in DROPPED_NONADDRESS_COLUMNS
        spec = get_scottsdale_dataset(FeedType.SLA)
        assert spec.oid_field == "OBJECTID"

    def test_pii_columns_never_become_candidates(self):
        mapped = {c for values in FIELD_MAP.values() for c in values.values() for c in values}
        for values in FIELD_MAP.values():
            for col_candidates in values.values():
                for col in col_candidates:
                    assert col not in DROPPED_PII_COLUMNS, col
                    assert col not in DROPPED_NONADDRESS_COLUMNS, col
        # The dropped blocks are exactly the holder/mailing PII.
        assert {"Owner", "Builder", "ResponsibleParty",
                "MailAddrComp", "MailAddrCityStateZipComp"} <= set(DROPPED_PII_COLUMNS)
        assert mapped  # sanity: the maps are non-empty


# ---------------------------------------------------------------------------
# ArcGISClient flatten contract (real client code, no network)
# ---------------------------------------------------------------------------


class TestArcgisFlatten:
    def test_epoch_ms_dates_flatten_to_iso(self):
        assert PERMIT_A_ROW["IssueDate"] == "2026-08-21T00:00:00+00:00"
        assert PERMIT_B_ROW["IssueDate"] == "2026-08-20T00:00:00+00:00"
        assert LIC_APEX_ROW["BusinessStartDate"] == "2026-08-21T00:00:00+00:00"

    def test_table_rows_inject_no_geometry_coordinates(self):
        """Both registered endpoints are tables — features carry no geometry,
        so the flatten lift adds nothing and coordinates come only from the
        (permits) attribute columns / geocode supplement."""
        for row in (PERMIT_A_ROW, PERMIT_B_ROW, LIC_APEX_ROW):
            assert "latitude" not in row
            assert "longitude" not in row

    def test_sentinel_epoch_flattens_to_year_5202(self):
        assert LIC_SENTINEL_ROW["BusinessStartDate"] == "5202-09-12T00:00:00+00:00"

    def test_null_attribute_coordinates_stay_none(self):
        assert PERMIT_A_ROW["Latitude"] is None
        assert PERMIT_A_ROW["Longitude"] is None


# ---------------------------------------------------------------------------
# Sentinel guard (US-111 future-watermark discipline)
# ---------------------------------------------------------------------------


class TestSentinelGuard:
    def test_year_5202_garbage_row_is_future_dated(self):
        parsed = _parse_datetime(LIC_SENTINEL_ROW["BusinessStartDate"])
        assert parsed is not None
        assert is_future_watermark(parsed, datetime.now(UTC)) is True

    def test_forward_dated_application_is_future_dated(self):
        assert LIC_QUIKTRIP_ROW["BusinessStartDate"] == "2026-11-19T00:00:00+00:00"
        parsed = _parse_datetime(LIC_QUIKTRIP_ROW["BusinessStartDate"])
        assert is_future_watermark(parsed, datetime.now(UTC)) is True

    def test_newest_guarded_fixture_is_not_future_dated(self):
        parsed = _parse_datetime(LIC_APEX_ROW["BusinessStartDate"])
        assert parsed is not None
        assert is_future_watermark(parsed, datetime.now(UTC)) is False

    def test_where_guard_composes_with_the_us111_convention(self):
        spec = get_scottsdale_dataset(FeedType.SLA)
        where = build_where(
            base_where=spec.where,
            watermark_col=spec.watermark_col,
            high_watermark="2026-08-21T00:00:00+00:00",
            endpoint=spec.endpoint,
            incremental=True,
            snapshot=False,
        )
        assert where is not None
        assert f"({SCOTTSDALE_SLA_WHERE})" in where
        assert "BusinessStartDate >" in where

    def test_watermark_exclude_stays_empty_rolling_sentinels(self):
        spec = get_scottsdale_dataset(FeedType.SLA)
        assert spec.watermark_exclude == []
        assert watermark_exclude_clause("BusinessStartDate", spec.watermark_exclude) is None


# ---------------------------------------------------------------------------
# Feed spec (leaf-local get_dataset mirror)
# ---------------------------------------------------------------------------


class TestFeedRegistration:
    def test_exactly_the_verified_feed_set_is_registered(self):
        assert set(SCOTTSDALE_FEED_SPECS) == {"permits", "sla"}

    def test_permits_spec_matches_live_layer(self):
        spec = get_scottsdale_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == SCOTTSDALE_PERMITS_ENDPOINT
        assert spec.watermark_col == "IssueDate"
        assert spec.id_keys == ["PermitNumber", "permit_id"]
        assert spec.producer_key == "permits"
        assert spec.ingestion_mode == "incremental"
        assert spec.oid_field == "permit_id"
        assert spec.max_record_count == 1000
        assert spec.expected_cadence_days == 14
        assert spec.order_by == "IssueDate DESC"
        assert spec.interval_seconds == 300.0
        assert spec.where is None
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Scottsdale, AZ"
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic  # settings.topic_permits resolves

    def test_sla_spec_matches_live_layer(self):
        spec = get_scottsdale_dataset(FeedType.SLA)
        assert spec.platform == "arcgis"
        assert spec.endpoint == SCOTTSDALE_SLA_ENDPOINT
        assert spec.watermark_col == "BusinessStartDate"
        assert spec.id_keys == ["AcctNum", "OBJECTID"]
        assert spec.producer_key == "sla"
        assert spec.ingestion_mode == "incremental"
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 1000
        assert spec.expected_cadence_days == 14
        assert spec.order_by == "BusinessStartDate DESC"
        assert spec.where == SCOTTSDALE_SLA_WHERE == (
            "BusinessStartDate <= CURRENT_TIMESTAMP"
        )
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Scottsdale, AZ"
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.topic  # settings.topic_sla resolves

    def test_endpoints_are_the_probed_mapserver_tables(self):
        assert "maps.scottsdaleaz.gov" in SCOTTSDALE_PERMITS_ENDPOINT
        assert "maps.scottsdaleaz.gov" in SCOTTSDALE_SLA_ENDPOINT
        assert "OpenData_Tabular/MapServer/12" in SCOTTSDALE_PERMITS_ENDPOINT
        assert "OpenData_Tabular/MapServer/6" in SCOTTSDALE_SLA_ENDPOINT

    def test_host_is_not_an_ansi_date_literal_host(self):
        # Verified live 2026-08-28: `IssueDate > '2026-08-01'` returns real
        # date math (51 rows), so the shared ISO-literal watermark form
        # works — maps.scottsdaleaz.gov must NOT join ANSI_DATE_LITERAL_HOSTS.
        assert "maps.scottsdaleaz.gov" not in ANSI_DATE_LITERAL_HOSTS

    @pytest.mark.parametrize(
        "absent_feed", [FeedType.COMPLAINTS_311, FeedType.DEEDS]
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'scottsdale'.*available"):
            get_scottsdale_dataset(absent_feed)


# ---------------------------------------------------------------------------
# Producer path with the Scottsdale field maps injected (no spine registration)
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


def _patch_resolve(monkeypatch, geocode_point=None):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP["permits" if feed == FeedType.PERMITS else "sla"],
    )
    if geocode_point is not None:
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: geocode_point,
        )
    else:
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )


class TestScottsdalePermitParsing:
    def test_cavasson_fixture_parses_all_fields(self, permits, monkeypatch):
        _patch_resolve(monkeypatch)
        event = permits.parse_socrata_row(PERMIT_B_ROW, city_id="scottsdale")
        assert event is not None
        assert event.city_id == "scottsdale"
        assert event.job_id == "324334"
        assert event.status == "ACTIVE"
        assert event.job_type == JobType.OT  # TENANT IMPROVEMENT is unclassified
        assert event.estimated_cost == pytest.approx(16753.8)
        assert event.address_street == "18700 N HAYDEN RD UNIT 250"
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat() == "2026-08-20T00:00:00+00:00"
        assert event.latitude == pytest.approx(_CAVASSON[0])
        assert event.longitude == pytest.approx(_CAVASSON[1])

    def test_native_coordinates_index_h3_and_sit_in_metro(self, permits, monkeypatch):
        _patch_resolve(monkeypatch)
        event = permits.parse_socrata_row(PERMIT_B_ROW, city_id="scottsdale")
        assert event is not None
        expected = H3SpatialIndexer.get_multi_res_hierarchy(*_CAVASSON)
        assert event.h3_res7 == expected["h3_res7"]
        assert event.h3_res8 == expected["h3_res8"]
        assert event.h3_res9 == expected["h3_res9"]
        assert is_in_scottsdale_metro(event.latitude, event.longitude)

    def test_null_coordinate_row_resolves_through_geocode_fallback(
        self, permits, monkeypatch
    ):
        """Newest-window rows carry null Latitude/Longitude; the ADR-0004
        declaration resolves Address at parse time. Result-level assertions
        only — no hook-call counts."""
        _patch_resolve(monkeypatch, geocode_point=_GEOCODED)
        event = permits.parse_socrata_row(PERMIT_A_ROW, city_id="scottsdale")
        assert event is not None
        assert event.city_id == "scottsdale"
        assert event.job_id == "324344"
        assert event.estimated_cost == pytest.approx(812094.7)
        assert event.address_street == "27231 N 65TH PL"
        assert event.latitude == pytest.approx(_GEOCODED[0])
        assert event.longitude == pytest.approx(_GEOCODED[1])
        assert event.h3_res7 is not None

    def test_null_coordinate_row_dropped_when_geocode_fails(
        self, permits, monkeypatch
    ):
        _patch_resolve(monkeypatch)
        assert permits.parse_socrata_row(PERMIT_A_ROW, city_id="scottsdale") is None

    def test_second_null_coordinate_row_valuation_passthrough(
        self, permits, monkeypatch
    ):
        _patch_resolve(monkeypatch, geocode_point=(33.5011, -111.9430))
        event = permits.parse_socrata_row(PERMIT_C_ROW, city_id="scottsdale")
        assert event is not None
        assert event.job_id == "324342"
        assert event.estimated_cost == pytest.approx(24348.96)
        assert event.address_street == "6708 E WILSHIRE DR"
        assert event.status == "ACTIVE"

    def test_job_id_falls_back_to_the_stable_oid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, geocode_point=_GEOCODED)
        record = {k: v for k, v in PERMIT_A_ROW.items() if k != "PermitNumber"}
        event = permits.parse_socrata_row(record, city_id="scottsdale")
        assert event is not None
        assert event.job_id == "324348"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch)
        record = {
            k: v for k, v in PERMIT_A_ROW.items() if k not in ("PermitNumber", "permit_id")
        }
        assert permits.parse_socrata_row(record, city_id="scottsdale") is None

    def test_sfr_type_codes_stay_unclassified_at_the_leaf(
        self, permits, monkeypatch
    ):
        """Scottsdale PermitType codes (SFR-*, TENANT IMPROVEMENT, NATIVE
        PLANT) are not among the producer's recognized codes — they pass
        through job_type and land on OT honestly (Greenville discipline)."""
        _patch_resolve(monkeypatch, geocode_point=_GEOCODED)
        for feature in (PERMIT_A, PERMIT_C):
            event = permits.parse_socrata_row(_flatten(feature), city_id="scottsdale")
            assert event is not None
            assert event.job_type == JobType.OT


class TestScottsdaleSlaParsing:
    def test_apex_fixture_parses_all_fields(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, geocode_point=(33.4978, -111.9215))
        event = sla.parse_socrata_row(LIC_APEX_ROW, city_id="scottsdale")
        assert event is not None
        assert event.city_id == "scottsdale"
        assert event.license_id == "2045469"
        assert event.dba == "APEX APPLIANCES"
        assert event.premises_name == "APEX APPLIANCES"
        assert event.license_type == "BRM"
        assert event.license_status == "Active"
        assert event.address == "7901 E THOMAS RD STE 110"
        assert event.effective_date is not None
        assert event.effective_date.year == 2026
        assert event.effective_date.month == 8
        assert event.effective_date.day == 21

    def test_address_only_row_geocodes_into_h3_and_metro(
        self, sla, monkeypatch
    ):
        _patch_resolve(monkeypatch, geocode_point=(33.4978, -111.9215))
        event = sla.parse_socrata_row(LIC_APEX_ROW, city_id="scottsdale")
        assert event is not None
        assert event.latitude == pytest.approx(33.4978)
        assert event.longitude == pytest.approx(-111.9215)
        assert event.h3_res7 is not None
        assert is_in_scottsdale_metro(event.latitude, event.longitude)

    def test_studs_fixture_geocodes_through_the_same_path(
        self, sla, monkeypatch
    ):
        _patch_resolve(monkeypatch, geocode_point=(33.5305, -111.9055))
        event = sla.parse_socrata_row(LIC_STUDS_ROW, city_id="scottsdale")
        assert event is not None
        assert event.license_id == "2045499"
        assert event.dba == "STUDS INC"
        assert event.license_type == "BRM"
        assert event.address == "7014 E CAMELBACK RD STE 2216"
        assert event.effective_date is not None
        assert event.effective_date.day == 19
        assert event.h3_res9 is not None

    def test_geocode_failure_keeps_null_coords_and_the_event(
        self, sla, monkeypatch
    ):
        """Every SLA row is address-only; with the geocoder failing the
        event still parses (coordinate-less registry discipline)."""
        _patch_resolve(monkeypatch)
        event = sla.parse_socrata_row(LIC_APEX_ROW, city_id="scottsdale")
        assert event is not None
        assert event.license_id == "2045469"
        assert event.latitude is None and event.longitude is None
        assert event.h3_res7 is None and event.h3_res8 is None and event.h3_res9 is None

    def test_city_id_string_is_accepted_verbatim_without_enum(
        self, sla, monkeypatch
    ):
        _patch_resolve(monkeypatch, geocode_point=_GEOCODED)
        row = {**LIC_APEX_ROW, "AcctNum": "2099999"}
        event = sla.parse_socrata_row(row, city_id="scottsdale")
        assert event is not None
        assert event.city_id == "scottsdale"
        assert event.license_id == "2099999"

    def test_row_without_any_id_is_dropped(self, sla, monkeypatch):
        _patch_resolve(monkeypatch)
        row = {k: v for k, v in LIC_APEX_ROW.items() if k != "AcctNum"}
        assert sla.parse_socrata_row(row, city_id="scottsdale") is None