"""Unit tests for the Gainesville leaf: spatial module + permits field map."""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_gainesville import FIELD_MAP as GAINESVILLE_PERMITS_FIELD_MAP
from src.spatial.cities.gainesville import (
    GAINESVILLE_DIVISION_BBOXES,
    GAINESVILLE_DIVISIONS,
    GAINESVILLE_METRO_BBOX,
    GAINESVILLE_SUBMARKETS,
    get_gainesville_dataset,
    is_in_gainesville_metro,
)
from src.spatial.city_registry import FeedType


class TestGainesvilleSpatial:
    def test_metro_contains_core_points(self):
        assert is_in_gainesville_metro(29.6516, -82.3248)  # downtown
        assert is_in_gainesville_metro(29.6530, -82.3380)  # midtown

    def test_metro_rejects_foreign(self):
        assert not is_in_gainesville_metro(27.9506, -82.4572)  # Tampa
        assert not is_in_gainesville_metro(None, None)

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in GAINESVILLE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= GAINESVILLE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= GAINESVILLE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= GAINESVILLE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= GAINESVILLE_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in GAINESVILLE_SUBMARKETS.items():
            bbox = GAINESVILLE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in GAINESVILLE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(GAINESVILLE_SUBMARKETS)

    def test_submarkets_carry_city_id(self):
        assert {m.city_id for m in GAINESVILLE_SUBMARKETS.values()} == {"gainesville"}


class TestFeedRegistration:
    def test_permits_spec_matches_live_dataset(self):
        spec = get_gainesville_dataset(FeedType.PERMITS)
        assert spec.platform == "socrata"
        assert spec.endpoint.endswith("/p798-x3nx.json")
        assert spec.watermark_col == "issue"
        assert spec.id_keys == ["permit"]
        assert spec.producer_key == "permits"
        # Field map attached for stable parse keys
        assert spec.field_map == GAINESVILLE_PERMITS_FIELD_MAP

    def test_field_map_reads_live_columns(self):
        row = {
            "permit": "BP-13-03005",
            "issue": "2013-05-22T00:00:00.000",
            "address": "4190 NW 85TH PL",
            "latitude": 29.63447,
            "longitude": -82.38533,
            "location_1": {"type": "Point", "coordinates": [-82.38533, 29.63447]},
        }
        assert first_mapped(row, GAINESVILLE_PERMITS_FIELD_MAP, "job_id") == "BP-13-03005"
        assert first_mapped(row, GAINESVILLE_PERMITS_FIELD_MAP, "issuance_date") == "2013-05-22T00:00:00.000"
        assert first_mapped(row, GAINESVILLE_PERMITS_FIELD_MAP, "address_street") == "4190 NW 85TH PL"
        # Prefer direct lat/lng, but accept location_1 fallback
        assert first_mapped(row, GAINESVILLE_PERMITS_FIELD_MAP, "latitude") == 29.63447
        assert first_mapped(row, GAINESVILLE_PERMITS_FIELD_MAP, "longitude") == -82.38533


@pytest.fixture
def permits_producer():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        yield DOBPermitsProducer()


@patch(
    "src.producers.field_maps.resolve_field_map",
    lambda city, feed: GAINESVILLE_PERMITS_FIELD_MAP if (city == "gainesville" and feed == FeedType.PERMITS) else {},
)
def test_permit_with_point_geometry_uses_native_coords(permits_producer):
    row = {
        "permit": "BP-13-03005",
        "issue": "2013-05-22T00:00:00.000",
        "address": "4190 NW 85TH PL",
        "location_1": {"type": "Point", "coordinates": [-82.38533, 29.63447]},
        "latitude": 29.63447,
        "longitude": -82.38533,
    }
    with patch("src.spatial.geocoder.geocode_row_if_declared", return_value=(0.0, 0.0)) as geocode:
        event = permits_producer.parse_socrata_row(row, city_id="gainesville")
    assert event is not None
    assert event.city_id == "gainesville"
    assert event.job_id == "BP-13-03005"
    assert event.latitude == pytest.approx(29.63447)
    assert event.longitude == pytest.approx(-82.38533)
    geocode.assert_not_called()

