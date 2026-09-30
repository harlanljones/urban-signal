"""No deed event carries a grantor's or grantee's name (2026-09-30).

Sellers and buyers are often private people, and nothing downstream reads
their names. No registered spec maps them, the deeds producer reads none of
the columns that hold them, and a deeds spec that names its columns leaves
the owner's out of its ``select``.
"""

from unittest.mock import patch

import pytest

from src.spatial.city_registry import REGISTRY, CityId, FeedType, get_dataset

PARTY_FIELDS = {"party1_grantor", "party2_grantee"}

# Every column the producer used to read a party name from.
PARTY_COLUMNS = (
    "owner_name", "party1_grantor", "party1_type", "grantor", "seller", "seller_name",
    "Sellername", "OWNERNME1", "buyer", "buyername", "buyer_name", "party2_grantee",
    "party2_type", "grantee", "OWN1", "OWN2",
)


def test_no_registered_spec_maps_a_party_name():
    mapped = sorted(
        (city.value, feed.value)
        for city, registration in REGISTRY.items()
        for feed, spec in registration.datasets.items()
        if PARTY_FIELDS & set(spec.field_map or {})
    )
    assert mapped == []


@pytest.mark.parametrize(
    ("city", "owner_columns"),
    [
        (CityId.RENO, {"FIRSTNAME", "LASTNAME", "MAILING1", "MAILING2", "MAILCITY", "MAILSTATE", "MAILZIP"}),
        (CityId.WASHINGTON_DC, {"SALE_CURR_OWNER"}),
    ],
)
def test_owner_columns_stay_on_the_server(city, owner_columns):
    spec = get_dataset(city, FeedType.DEEDS)
    selected = set(spec.select.split(","))
    assert not selected & owner_columns


@pytest.fixture
def deeds(monkeypatch):
    import src.producers.field_maps as fm

    # A field map that still named the party columns would not bring them back.
    monkeypatch.setattr(
        fm,
        "resolve_field_map",
        lambda city_value, feed: {
            "doc_id": ["doc_id"],
            "party1_grantor": ["grantor"],
            "party2_grantee": ["grantee"],
        },
    )
    with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
        from src.producers.deeds_acris_producer import DeedsACRISProducer

        yield DeedsACRISProducer()


def test_no_party_column_reaches_an_event(deeds):
    row = {
        "doc_id": "DOC-2026-0001",
        "recorded_datetime": "2026-09-01T00:00:00",
        "latitude": "41.8830",
        "longitude": "-87.6450",
        **dict.fromkeys(PARTY_COLUMNS, "REDACTED"),
    }

    event = deeds.parse_socrata_row(row, city_id="chicago")

    assert event is not None
    assert event.doc_id == "DOC-2026-0001"
    assert event.party1_grantor is None
    assert event.party2_grantee is None
