"""Contract tests for Washoe County parcel sales used by Reno DEEDS."""

from unittest.mock import patch

import pytest

from src.spatial.cities.reno import (
    RENO_DIVISION_BBOXES,
    RENO_DIVISIONS,
    RENO_METRO_BBOX,
    RENO_SUBMARKETS,
    is_in_reno_metro,
)
from src.spatial.city_registry import CityId, FeedType, REGISTRY, get_dataset, normalize_city


RENO_DEEDS_FIELD_MAP = {
    "doc_id": ["PIN", "OBJECTID"],
    "bbl": ["PIN"],
    "document_amount": ["SALEPRICE"],
    "recorded_date": ["SALEDATE"],
    "borough": ["CITY", "SUBNAME"],
}


def test_reno_geometry_is_self_consistent():
    assert is_in_reno_metro(39.5296, -119.8138)
    assert is_in_reno_metro(39.5438, -119.8571)
    assert not is_in_reno_metro(36.1699, -115.1398)
    assert not is_in_reno_metro(None, None)
    for name, bbox in RENO_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= RENO_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= RENO_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= RENO_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= RENO_METRO_BBOX["max_lng"], name
    claimed = [name for division in RENO_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(RENO_SUBMARKETS)
    assert {meta.city_id for meta in RENO_SUBMARKETS.values()} == {"reno"}


def test_reno_registers_deeds_only():
    city = CityId.RENO
    assert normalize_city("reno nv") is city
    assert normalize_city("washoe county") is city
    assert set(REGISTRY[city].datasets) == {FeedType.DEEDS}

    deeds = get_dataset(city, FeedType.DEEDS)
    assert deeds.platform == "arcgis"
    assert deeds.endpoint.endswith("/OpenData/WashoeDataShare/MapServer/0")
    assert deeds.watermark_col == "SALEDATE"
    assert deeds.id_keys == ["PIN", "OBJECTID"]
    assert deeds.field_map == RENO_DEEDS_FIELD_MAP
    assert deeds.watermark_type == "text"
    assert deeds.watermark_format == "%m/%d/%Y"

    for feed in (FeedType.PERMITS, FeedType.COMPLAINTS_311, FeedType.SLA):
        with pytest.raises(KeyError, match="no.*feed"):
            get_dataset(city, feed)


def _flatten_feature(attributes: dict, geometry: dict) -> dict:
    """Shape a raw MapServer feature as the shared ArcGIS client does."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        {"attributes": attributes, "geometry": geometry}, date_fields=set()
    )


@pytest.fixture
def deeds():
    with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
        from src.producers.deeds_acris_producer import DeedsACRISProducer

        yield DeedsACRISProducer()


def test_reno_live_shaped_polygon_sale_parses(deeds):
    row = _flatten_feature(
        {
            "OBJECTID": 246,
            "PIN": "001-082-01",
            "SALEDATE": "08/05/2026",
            "SALEPRICE": 340000,
            "CITY": "RENO",
            "FullAddress": "1810 BALBOA DR",
        },
        {
            "rings": [[
                [-119.8571636466, 39.5438745149],
                [-119.8570140896, 39.5438116819],
                [-119.8570614255, 39.5437441373],
                [-119.8572421438, 39.5438200596],
                [-119.8571636466, 39.5438745149],
            ]]
        },
    )
    event = deeds.parse_socrata_row(row, city_id="reno")
    assert event is not None
    assert event.city_id == "reno"
    assert event.doc_id == "001-082-01"
    assert event.bbl == "001-082-01"
    assert event.document_amount == pytest.approx(340000.0)
    assert event.recorded_date is not None
    assert (event.recorded_date.year, event.recorded_date.month, event.recorded_date.day) == (2026, 8, 5)
    assert event.latitude == pytest.approx(39.5438, abs=0.001)
    assert event.longitude == pytest.approx(-119.8571, abs=0.001)
    assert event.h3_res7 is not None
