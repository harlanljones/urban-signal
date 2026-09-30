"""Tests for DC CAMA-to-Parcel Lots centroid enrichment (US-139)."""

from unittest.mock import MagicMock, patch

from src.producers.arcgis_client import ArcGISClient


def _text_key_metadata(url):
    return {"date_fields": set(), "numeric_fields": set(), "oid_field": "OBJECTID", "max_record_count": 1000}


def test_arcgis_client_builds_normalized_centroid_index_for_requested_keys():
    client = ArcGISClient()
    client.get_layer_metadata = _text_key_metadata
    client._fetch_page = MagicMock(
        return_value=(
            [
                {
                    "SSL": "6093    0808",
                    "latitude": 38.9001,
                    "longitude": -77.0102,
                },
                {"SSL": "NO-GEOMETRY"},
            ],
            False,
        )
    )

    index = client.fetch_centroid_index(
        "https://example.test/FeatureServer/33",
        join_key="SSL",
        join_values=["6093 0808", "NO-GEOMETRY"],
    )

    assert index == {"6093 0808": (38.9001, -77.0102)}
    kwargs = client._fetch_page.call_args.kwargs
    assert kwargs["where_clause"] == "SSL IN ('6093 0808','NO-GEOMETRY')"
    assert kwargs["select"] == "SSL"


def test_a_numeric_join_key_takes_bare_numbers():
    """Roanoke's parcel layer answers ``lrsn IN ('1116')`` with "Invalid data
    type for expression", and Lynchburg's Double LRSN reads back as 1116.0."""
    client = ArcGISClient()
    client.get_layer_metadata = lambda url: {**_text_key_metadata(url), "numeric_fields": {"lrsn"}}
    client._fetch_page = MagicMock(
        return_value=([{"lrsn": 1116.0, "latitude": 37.27, "longitude": -79.94}], False)
    )

    index = client.fetch_centroid_index(
        "https://example.test/FeatureServer/0",
        join_key="lrsn",
        join_values=[1116, "1116", 2204.0, "not-a-number"],
    )

    assert index == {"1116": (37.27, -79.94)}
    assert client._fetch_page.call_args.kwargs["where_clause"] == "lrsn IN (1116,2204)"


def test_dc_deed_stream_enriches_cama_row_before_parsing():
    from src.producers.deeds_acris_producer import DeedsACRISProducer

    class FakeArcGISClient:
        def paginate(self, **kwargs):
            yield [
                {
                    "ROW_NUMBER": "414660",
                    "SSL": "6093    0808",
                    "SALE_DATE": "2026-08-12T00:00:00+00:00",
                    "SALE_PRICE": 496000,
                    "QUALIFIED": "Q",
                }
            ]

        def fetch_centroid_index(self, **kwargs):
            assert kwargs["join_values"] == ["6093    0808"]
            return {"6093 0808": (38.9001, -77.0102)}

    with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
        producer = DeedsACRISProducer()
    client = FakeArcGISClient()
    producer._client_for = lambda platform: client

    streamed = producer.run_stream(city_id="washington_dc", limit=1)

    assert streamed == 1
    payload = producer.producer.produce.call_args.kwargs["payload"]
    assert payload.city_id == "washington_dc"
    assert payload.latitude == 38.9001
    assert payload.longitude == -77.0102
