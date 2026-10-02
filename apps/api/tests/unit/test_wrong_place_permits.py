"""Three permit feeds read somewhere else (2026-10-02).

- Ocala and Orlando read the statewide parcel layer sliced by county codes
  that name other counties: the Department of Revenue numbers counties
  alphabetically from Alachua at 11, so 42 is Jackson County and 48 is Levy
  County (Marion is 52 and Orange 58). A parcel roll is not a permit stream
  either. Orlando now reads the City's own permits; Ocala has no permit feed.
- Macon-Bibb read a layer whose 21,930 polygons all lie in St. Catharines,
  Ontario. The County's own permits layer was last edited on 2021-01-04.

Both retracted metros keep their SNAP retailers.
"""

import pytest

from src.config import settings
from src.spatial.city_registry import REGISTRY, CityId, FeedType


def _all_specs():
    return [(cid, feed, ds) for cid, reg in REGISTRY.items() for feed, ds in reg.datasets.items()]


def test_no_feed_reads_the_statewide_parcel_layer():
    readers = [
        (cid.value, feed.value)
        for cid, feed, ds in _all_specs()
        if ds.endpoint == settings.arcgis_fl_cadastral_url or "Florida_Statewide_Cadastral" in ds.endpoint
    ]
    assert readers == []


@pytest.mark.parametrize(
    ("city", "registered"),
    [
        # Ocala's deeds come from the County's parcels on the City's server.
        (CityId.OCALA, {FeedType.SLA, FeedType.DEEDS}),
        (CityId.MACON_BIBB, {FeedType.SLA}),
    ],
)
def test_retracted_metros_register_no_permits_and_keep_their_retailers(city, registered):
    feeds = REGISTRY[city].datasets
    assert FeedType.PERMITS not in feeds
    assert set(feeds) == registered
    assert feeds[FeedType.SLA].endpoint == settings.arcgis_snap_retailers_url


def test_no_setting_or_feed_reads_the_st_catharines_layer():
    layer_org = "services6.arcgis.com/Yx1h0qHJ9wIpQWuU"
    assert not [name for name, value in settings.model_dump().items() if layer_org in str(value)]
    assert not [(cid.value, feed.value) for cid, feed, ds in _all_specs() if layer_org in ds.endpoint]
