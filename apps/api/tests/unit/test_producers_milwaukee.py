"""Contract tests for Milwaukee, WI (ArcGIS liquor-license registry)."""

from unittest.mock import patch

import pytest

from src.spatial.cities.milwaukee import (
    MILWAUKEE_DIVISION_BBOXES,
    MILWAUKEE_DIVISIONS,
    MILWAUKEE_METRO_BBOX,
    MILWAUKEE_SUBMARKETS,
    is_in_milwaukee_metro,
)
from src.spatial.city_registry import CityId, FeedType

# Recommended DatasetSpec.extra["field_map"] for US-87. Every entry spells an
# uppercase column the shared producer fallback chains cannot reach;
# latitude/longitude need no entry because ArcGISClient lifts point geometry
# onto those exact keys (outSR=4326) before parsing.
MILWAUKEE_FIELD_MAP = {
    "license_id": ["LICENSE_ID"],
    "effective_date": ["EFFECTIVE_DATE"],
    "expiration_date": ["EXPIRATION_DATE"],
    "license_type": ["LIC_TYPE_ABBR", "PROFESSION_FULL_NAME"],
}


def test_milwaukee_geometry_is_self_consistent():
    assert is_in_milwaukee_metro(43.0389, -87.9065)  # downtown center
    assert is_in_milwaukee_metro(43.16444616767501, -88.06268420979835)  # observed live-row
    assert is_in_milwaukee_metro(43.05986566976713, -87.88682496415392)  # observed live-row
    assert not is_in_milwaukee_metro(43.0030, -88.1250)  # Waukesha, west of the county
    assert not is_in_milwaukee_metro(None, None)
    for name, bbox in MILWAUKEE_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= MILWAUKEE_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= MILWAUKEE_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= MILWAUKEE_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= MILWAUKEE_METRO_BBOX["max_lng"], name
    claimed = [name for division in MILWAUKEE_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(MILWAUKEE_SUBMARKETS)
    assert {meta.city_id for meta in MILWAUKEE_SUBMARKETS.values()} == {"milwaukee"}


def test_milwaukee_registers_sla_permits_and_deeds():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.MILWAUKEE
    assert normalize_city("milwaukee") is city
    assert normalize_city("mke") is city
    assert REGISTRY[city].job_suffix == "mke"
    assert set(REGISTRY[city].datasets) == {
        FeedType.SLA,
        FeedType.PERMITS,
        FeedType.DEEDS,
    }

    sla = REGISTRY[city].datasets[FeedType.SLA]
    assert sla.platform == "arcgis"
    # GIS_DATETIME is the layer-update timestamp (always current); expiry
    # dates are future-dated and would trip the future-watermark guard.
    assert sla.watermark_col == "GIS_DATETIME"
    assert sla.interval_seconds == 600.0
    assert sla.producer_key == "sla"
    assert sla.extra["expected_cadence_days"] == 7
    assert sla.extra["oid_field"] == "OBJECTID"
    assert sla.extra["max_record_count"] == 2000
    assert sla.extra["field_map"] == MILWAUKEE_FIELD_MAP

    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.COMPLAINTS_311)

    permits = get_dataset(city, FeedType.PERMITS)
    assert permits.platform == "csv"
    assert permits.watermark_col == "date_issued"
    assert permits.extra["needs_geocode"] is True

    deeds = get_dataset(city, FeedType.DEEDS)
    assert deeds.platform == "csv"
    assert deeds.watermark_col == "sale_date"
    assert deeds.extra["watermark_format"] == "%m/%d/%Y"
    assert deeds.extra["ingestion_mode"] == "snapshot"


MKE_LICENSE_ROW = {
    # Live newest GIS_DATETIME row via REST on 2026-08-24, flattened exactly as
    # ArcGISClient._flatten_feature delivers it: attributes dict, point
    # geometry lifted to latitude/longitude, epoch-ms date fields re-encoded
    # to ISO 8601 UTC strings.
    "OBJECTID": 635,
    "LICENSE_ID": 338024,
    "CORP_NAME": "Sam's East, INC.",
    "TRADE_NAME": None,
    "LICENSEE": None,
    "ENTITY_ADDRESS": "8100 N 124th ST",
    "ALD_DIST": 9,
    "LIC_TYPE_ABBR": "ALQML",
    "PROFESSION_FULL_NAME": "Class A Liquor Malt",
    "EFFECTIVE_DATE": "2025-08-01T00:00:00+00:00",
    "EXPIRATION_DATE": "2026-08-31T00:00:00+00:00",
    "ISSUED_DATE": "2025-08-01T00:00:00+00:00",
    "GIS_DATETIME": "2026-08-24T01:25:05+00:00",
    "longitude": -88.06268420979835,
    "latitude": 43.16444616767501,
}


class TestMilwaukeeSLAParsing:
    """Parse pins against the shared SLALicensesProducer (US-87)."""

    @pytest.fixture
    def producer(self):
        with (
            patch("src.producers.sla_licenses_producer.BaseKafkaProducer"),
            patch(
                "src.producers.field_maps.resolve_field_map",
                return_value=MILWAUKEE_FIELD_MAP,
            ),
        ):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            yield SLALicensesProducer()

    def test_live_row_parses_uppercase_schema(self, producer):
        event = producer.parse_socrata_row(dict(MKE_LICENSE_ROW), city_id="milwaukee")
        assert event is not None
        assert event.city_id == "milwaukee"
        assert event.license_id == "338024"
        assert event.license_type == "ALQML"
        assert event.license_status == "ACTIVE"
        assert event.effective_date is not None
        assert (event.effective_date.year, event.effective_date.month) == (2025, 8)
        assert event.expiration_date is not None
        assert event.expiration_date.year == 2026
        assert event.latitude == pytest.approx(43.16444616767501)
        assert event.longitude == pytest.approx(-88.06268420979835)

    def test_missing_license_id_returns_none(self, producer):
        row = dict(MKE_LICENSE_ROW)
        row.pop("LICENSE_ID")
        assert producer.parse_socrata_row(row, city_id="milwaukee") is None
