"""Tests for DC CAMA-to-Parcel Lots centroid enrichment (US-139)."""

from unittest.mock import MagicMock, patch

from src.producers.arcgis_client import ArcGISClient


def test_arcgis_client_builds_normalized_centroid_index_for_requested_keys():
    client = ArcGISClient()
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
