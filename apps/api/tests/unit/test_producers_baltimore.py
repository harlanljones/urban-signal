"""Contract tests for Baltimore's ArcGIS permits, 311, and liquor feeds."""

from datetime import date
from unittest.mock import patch

import pytest

from src.spatial.cities.baltimore import (
    BALTIMORE_DIVISION_BBOXES,
    BALTIMORE_DIVISIONS,
    BALTIMORE_METRO_BBOX,
    BALTIMORE_SUBMARKETS,
    is_in_baltimore_metro,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType, resolve_endpoint


def test_baltimore_geometry_is_self_consistent():
    assert is_in_baltimore_metro(39.290, -76.612)
    assert not is_in_baltimore_metro(42.355, -71.065)
    assert not is_in_baltimore_metro(None, None)
    for name, bbox in BALTIMORE_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= BALTIMORE_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= BALTIMORE_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= BALTIMORE_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= BALTIMORE_METRO_BBOX["max_lng"], name
    claimed = [name for division in BALTIMORE_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(BALTIMORE_SUBMARKETS)
    assert {meta.city_id for meta in BALTIMORE_SUBMARKETS.values()} == {"baltimore"}


def test_baltimore_registers_arcgis_feeds_plus_socrata_sdat_deeds():
    city = CityId.BALTIMORE
    assert REGISTRY[city].job_suffix == "baltimore"
    assert set(REGISTRY[city].datasets) == {
        FeedType.PERMITS,
        FeedType.COMPLAINTS_311,
        FeedType.SLA,
        FeedType.DEEDS,
    }
    for feed in (FeedType.PERMITS, FeedType.COMPLAINTS_311, FeedType.SLA):
        assert REGISTRY[city].datasets[feed].platform == "arcgis", feed
    assert REGISTRY[city].datasets[FeedType.DEEDS].platform == "socrata"
    assert REGISTRY[city].datasets[FeedType.DEEDS].ingestion_mode == "snapshot"


def test_baltimore_specs_pin_live_fields_and_311_rollover():
    reg = REGISTRY[CityId.BALTIMORE]
    permits = reg.datasets[FeedType.PERMITS]
    assert permits.endpoint.endswith("DHCD_Open_Baltimore_Datasets/FeatureServer/3")
    assert permits.watermark_col == "IssuedDate"
    assert permits.field_map["job_id"] == ["CaseNumber"]

    complaints = reg.datasets[FeedType.COMPLAINTS_311]
    assert complaints.endpoint_by_year["2026"].endswith(
        "311_Customer_Service_Requests_current/FeatureServer/0"
    )
    assert resolve_endpoint(complaints, date(2026, 8, 23)) == complaints.endpoint_by_year["2026"]
    assert complaints.field_map["incident_id"] == ["SRRecordID", "ServiceRequestNum", "RowID"]

    licenses = reg.datasets[FeedType.SLA]
    # `scope` was a free-form extra key; it has been dropped (US-186).
    assert licenses.field_map["license_id"] == ["LicenseNumber", "LLKey"]


def test_baltimore_permit_row_parses_with_arcgis_flattened_coordinates():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        producer = DOBPermitsProducer()
    event = producer.parse_socrata_row(
        {
            "OBJECTID": 1,
            "CaseNumber": "BCCM-25-000001",
            "IssuedDate": "2025-02-20T00:00:00+00:00",
            "Address": "401 W REDWOOD ST",
            "Cost": 61555.58,
            "latitude": 39.285,
            "longitude": -76.622,
        },
        city_id="baltimore",
    )
    assert event is not None
    assert event.job_id == "BCCM-25-000001"
    assert event.latitude == pytest.approx(39.285)


def test_baltimore_311_row_parses_with_current_layer_fields():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        from src.producers.complaints_311_producer import Complaints311Producer

        producer = Complaints311Producer()
    event = producer.parse_socrata_row(
        {
            "RowID": 42,
            "SRRecordID": "2026-000042",
            "SRType": "Pothole",
            "CreatedDate": "2026-01-10T12:00:00+00:00",
            "SRStatus": "Open",
            "Address": "100 N CHARLES ST",
            "ZipCode": "21201",
            "Latitude": "39.290",
            "Longitude": "-76.612",
        },
        city_id="baltimore",
    )
    assert event is not None
    assert event.incident_id == "2026-000042"
    assert event.latitude == pytest.approx(39.290)
    assert event.incident_address == "100 N CHARLES ST"


BALTIMORE_SDAT_DEED = {
    # Live shaped row from opendata.maryland.gov/resource/3x3p-xk2v (2026-08-25);
    # the point arrives as a WKT string and the native WGS84 columns are numbers.
    "account_id_mdp_field_acctid": "13113438055A",
    "sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89": "2026.07.24",
    "sales_segment_1_consideration_mdp_field_considr1_sdat_field_90": "215000",
    "sales_segment_1_grantor_name_mdp_field_grntnam1_sdat_field_80": "BALTIMORE HOLDINGS LLC",
    "sales_segment_1_transfer_number_mdp_field_transno1_sdat_field_79": "000123",
    "mdp_latitude_mdp_field_digycord_converted_to_wgs84": 39.311834646402595,
    "mdp_longitude_mdp_field_digxcord_converted_to_wgs84": -76.62346538375218,
    "mappable_latitude_and_longitude": "POINT (-76.62346538375218 39.311834646402595)",
    "county_name_mdp_field_cntyname": "Baltimore City",
}


class TestBaltimoreSdatDeeds:
    """US-128: MD SDAT real-property deeds for Baltimore City."""

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_live_shaped_row_parses_through_field_map(self, deeds):
        event = deeds.parse_socrata_row(dict(BALTIMORE_SDAT_DEED), city_id="baltimore")
        assert event is not None
        assert event.city_id == "baltimore"
        assert event.doc_id == "13113438055A"
        assert event.bbl == "13113438055A"
        assert event.document_amount == pytest.approx(215000.0)
        assert event.party1_grantor == "BALTIMORE HOLDINGS LLC"
        assert event.party2_grantee is None  # SDAT records grantor only
        assert event.latitude == pytest.approx(39.311834646402595)
        assert event.longitude == pytest.approx(-76.62346538375218)

    def test_dotted_watermark_parses_to_real_recorded_date(self, deeds):
        event = deeds.parse_socrata_row(dict(BALTIMORE_SDAT_DEED), city_id="baltimore")
        assert event is not None
        assert (event.recorded_date.year, event.recorded_date.month, event.recorded_date.day) == (
            2026,
            7,
            24,
        )

    def test_wkt_point_string_geocodes_when_native_columns_absent(self, deeds):
        row = dict(BALTIMORE_SDAT_DEED)
        row.pop("mdp_latitude_mdp_field_digycord_converted_to_wgs84")
        row.pop("mdp_longitude_mdp_field_digxcord_converted_to_wgs84")
        event = deeds.parse_socrata_row(row, city_id="baltimore")
        assert event is not None
        assert event.latitude == pytest.approx(39.311834646402595)
        assert event.longitude == pytest.approx(-76.62346538375218)

    def test_row_autodetects_baltimore_by_county_name(self, deeds):
        event = deeds.parse_socrata_row(dict(BALTIMORE_SDAT_DEED))
        assert event is not None
        assert event.city_id == "baltimore"

    def test_snapshot_mode_registered(self):
        spec = REGISTRY[CityId.BALTIMORE].datasets[FeedType.DEEDS]
        assert spec.ingestion_mode == "snapshot"
        assert spec.expected_cadence_days == 30
        assert spec.watermark_col == (
            "sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89"
        )
