"""Contract tests for the Madison, WI registration (US-356)."""

from src.producers.accela_client import AccelaClient
from src.spatial.cities.madison import (
    MADISON_DIVISION_BBOXES,
    MADISON_METRO_BBOX,
    MADISON_SUBMARKETS,
    is_in_madison_metro,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType, normalize_city, snap_sla_spec


def test_madison_geometry_is_nested_and_representative():
    assert is_in_madison_metro(43.0747, -89.3844)
    assert not is_in_madison_metro(43.0747, -90.0)
    for bbox in MADISON_DIVISION_BBOXES.values():
        assert (
            MADISON_METRO_BBOX["min_lat"]
            <= bbox["min_lat"]
            <= bbox["max_lat"]
            <= MADISON_METRO_BBOX["max_lat"]
        )
        assert (
            MADISON_METRO_BBOX["min_lng"]
            <= bbox["min_lng"]
            <= bbox["max_lng"]
            <= MADISON_METRO_BBOX["max_lng"]
        )
    assert {meta.city_id for meta in MADISON_SUBMARKETS.values()} == {"madison"}


def test_madison_reads_snap_retailers_and_no_permits():
    """The Accela page registered as Madison's permits feed until 2026-09-30
    answered every API call with a redirect to an HTML error page."""
    assert normalize_city("madison wi") is CityId.MADISON
    datasets = REGISTRY[CityId.MADISON].datasets
    assert FeedType.PERMITS not in datasets
    assert datasets[FeedType.SLA] == snap_sla_spec("WI", MADISON_METRO_BBOX)


def test_accela_client_reuses_arcgis_rest_contract():
    assert isinstance(AccelaClient(), AccelaClient)
    assert (
        AccelaClient._normalize_layer_url("https://example.test/FeatureServer/0/query")
        == "https://example.test/FeatureServer/0"
    )
