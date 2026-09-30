"""Contract tests for Richmond, VA DEEDS: the assessor's monthly property
transfers workbook, each sale placed at its parcel's centroid.

The workbook carries buyer and seller names (``GRANTEE``, ``GRANTOR``) and no
coordinates. The spec's ``select`` keeps the names inside the Excel client,
and the scheduler's parcel join reads each sale's ``pin`` against the city's
Parcels layer, whose field is ``PIN``.
"""

from unittest.mock import patch

import pytest

from src.spatial.cities.richmond import (
    DEEDS_FIELD_MAP,
    RICHMOND_DEEDS_ENDPOINT,
    RICHMOND_DIVISION_BBOXES,
    RICHMOND_DIVISIONS,
    RICHMOND_METRO_BBOX,
    RICHMOND_PARCEL_LAYER,
    RICHMOND_SUBMARKETS,
    get_richmond_dataset,
    is_in_richmond_metro,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType, get_dataset


def test_richmond_geometry_is_self_consistent():
    assert is_in_richmond_metro(37.5407, -77.4360)  # downtown
    assert is_in_richmond_metro(37.5175, -77.4440)  # Manchester, across the James
    assert not is_in_richmond_metro(38.0293, -78.4767)  # Charlottesville
    assert not is_in_richmond_metro(None, None)
    for name, bbox in RICHMOND_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= RICHMOND_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= RICHMOND_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= RICHMOND_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= RICHMOND_METRO_BBOX["max_lng"], name
    claimed = [name for division in RICHMOND_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(RICHMOND_SUBMARKETS)
    assert {meta.city_id for meta in RICHMOND_SUBMARKETS.values()} == {"richmond"}


def test_richmond_reads_deeds_from_the_newest_transfers_workbook():
    assert set(REGISTRY[CityId.RICHMOND].datasets) == {FeedType.DEEDS}
    deeds = get_dataset(CityId.RICHMOND, FeedType.DEEDS)
    assert deeds.platform == "excel"
    assert deeds.endpoint == RICHMOND_DEEDS_ENDPOINT
    assert deeds.link_pattern == r"Assessor_Transfers_[0-9-]+\.xlsx$"
    assert deeds.ingestion_mode == "snapshot"
    assert deeds.where == "transfer_date >= CURRENT_DATE - INTERVAL '365' DAY"
    assert deeds.order_by == "transfer_date DESC"
    assert deeds.interval_seconds == 86400.0
    # A sale is its parcel, date, deed book and page: a parcel sells again,
    # and one instrument can convey several parcels.
    assert deeds.id_keys == ["pin", "transfer_date", "deed_book", "deed_page"]
    assert deeds.composite_id is True
    assert deeds.parcel_join == {
        "parcel_layer": RICHMOND_PARCEL_LAYER,
        "join_key": "PIN",
        "row_key": "pin",
        "geometry_source": "centroid",
    }
    assert deeds.field_map == DEEDS_FIELD_MAP


def test_buyer_and_seller_names_never_leave_the_client():
    deeds = get_dataset(CityId.RICHMOND, FeedType.DEEDS)
    selected = set(deeds.select.split(","))
    assert not selected & {"grantee", "grantor"}
    assert "party1_grantor" not in deeds.field_map
    assert "party2_grantee" not in deeds.field_map
    # Every column the feed reads survives the select.
    read = {column for columns in deeds.field_map.values() for column in columns}
    read |= {*deeds.id_keys, deeds.watermark_col, deeds.parcel_join["row_key"]}
    assert read <= selected


def test_the_leaf_mirror_matches_the_registry():
    assert get_richmond_dataset(FeedType.DEEDS) == get_dataset(CityId.RICHMOND, FeedType.DEEDS)
    with pytest.raises(KeyError, match="richmond"):
        get_richmond_dataset(FeedType.PERMITS)


@pytest.fixture
def deeds_producer():
    with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
        from src.producers.deeds_acris_producer import DeedsACRISProducer

        yield DeedsACRISProducer()


def _transfer(**extra):
    """A synthetic transfer as the Excel client hands it over, with the
    centroid the parcel join adds."""
    return {
        "pin": "W0001234005",
        "transfer_date": "2026-09-22T00:00:00",
        "consideration": 285000,
        "deed_book": "ID2026",
        "deed_page": 21877,
        "deed_type": "Deed",
        "parcel_location": "1234 W Grace St",
        "latitude": 37.5530,
        "longitude": -77.4620,
        **extra,
    }


def test_a_transfer_parses_at_its_parcel(deeds_producer):
    event = deeds_producer.parse_socrata_row(_transfer(), city_id="richmond")

    assert event is not None
    assert event.city_id == "richmond"
    assert event.doc_id == "W0001234005"
    assert event.bbl == "W0001234005"
    assert event.doc_type == "DEED"
    assert event.document_amount == pytest.approx(285000.0)
    assert event.recorded_date.date().isoformat() == "2026-09-22"
    assert (event.latitude, event.longitude) == (37.5530, -77.4620)
    assert event.h3_res9 is not None
    assert event.borough == "THE_FAN"
    assert event.party1_grantor is None
    assert event.party2_grantee is None


def test_a_transfer_the_join_could_not_place_publishes_without_coordinates(deeds_producer):
    row = _transfer()
    del row["latitude"], row["longitude"]

    event = deeds_producer.parse_socrata_row(row, city_id="richmond")

    assert event is not None
    assert event.latitude is None
    assert event.h3_res9 is None
