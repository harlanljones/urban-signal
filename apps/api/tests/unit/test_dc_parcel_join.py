"""Tests for DC CAMA-to-Owner Polygons centroid enrichment (US-139), condominium
units through CONDORELATE."""

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


def test_long_text_keys_split_below_the_url_limit():
    """Richmond's ArcGIS Online host answers 404 to a query URL past about
    2,000 characters: 100 quoted 11-character parcel ids ran to 2,155."""
    from urllib.parse import quote

    client = ArcGISClient()
    client.get_layer_metadata = _text_key_metadata
    client._fetch_page = MagicMock(return_value=([], False))
    pins = [f"W{n:010d}" for n in range(150)]

    client.fetch_centroid_index("https://example.test/FeatureServer/0", join_key="PIN", join_values=pins)

    wheres = [call.kwargs["where_clause"] for call in client._fetch_page.call_args_list]
    assert len(wheres) > 2
    assert all(len(quote(where)) <= 1_400 for where in wheres)
    sent = [value.strip("'") for where in wheres for value in where[len("PIN IN (") : -1].split(",")]
    assert sent == pins


def test_a_value_the_layer_lacks_takes_its_related_parcels_centroid():
    """DC's Owner Polygons layer holds no condominium unit; CONDORELATE names
    each unit's lot (MAT_SSL), and the unit takes that lot's centroid."""
    layer = "https://example.test/FeatureServer/40"
    table = "https://example.test/FeatureServer/52"
    pages = {
        (layer, "SSL IN ('0016    2033','6093    0808','0017    2001')"): [
            {"SSL": "6093    0808", "latitude": 38.9001, "longitude": -77.0102},
        ],
        (table, "SSL IN ('0016    2033','0017    2001')"): [
            {"SSL": "0016    2033", "MAT_SSL": "0016    0829"},
            {"SSL": "0016    2033", "MAT_SSL": "0016    0830"},
        ],
        (layer, "SSL IN ('0016    0829')"): [
            {"SSL": "0016    0829", "latitude": 38.9105, "longitude": -77.0431},
        ],
    }
    calls = []

    def fetch_page(endpoint_url, where_clause, order_by, limit, offset, select=None):
        calls.append((endpoint_url, where_clause, select))
        return (pages.get((endpoint_url, where_clause), []) if offset == 0 else []), False

    client = ArcGISClient()
    client.get_layer_metadata = _text_key_metadata
    client._fetch_page = fetch_page

    index = client.fetch_centroid_index(
        layer,
        join_key="SSL",
        join_values=["0016    2033", "6093    0808", "0017    2001"],
        via={"table": table, "key": "SSL", "to": "MAT_SSL"},
    )

    # The unit CONDORELATE does not know stays unplaced; a unit related to
    # two lots takes the first.
    assert index == {"6093 0808": (38.9001, -77.0102), "0016 2033": (38.9105, -77.0431)}
    assert (table, "SSL IN ('0016    2033','0017    2001')", "SSL,MAT_SSL") in calls


def test_no_via_table_is_read_when_the_layer_matches_every_value():
    client = ArcGISClient()
    client.get_layer_metadata = _text_key_metadata
    client._fetch_page = MagicMock(
        return_value=([{"SSL": "6093    0808", "latitude": 38.9001, "longitude": -77.0102}], False)
    )

    index = client.fetch_centroid_index(
        "https://example.test/FeatureServer/40",
        join_key="SSL",
        join_values=["6093    0808"],
        via={"table": "https://example.test/FeatureServer/52", "key": "SSL", "to": "MAT_SSL"},
    )

    assert index == {"6093 0808": (38.9001, -77.0102)}
    assert client._fetch_page.call_count == 1



def test_a_joins_filter_goes_with_every_request_to_the_layer():
    """Pierce County's parcels place Tacoma's sales only in the city's tax
    code areas. The filter joins each ``IN`` request to the layer, the lookup
    after a via table included, and a parcel it keeps out gets no centroid."""
    layer = "https://example.test/FeatureServer/0"
    table = "https://example.test/FeatureServer/1"
    where = "Tax_Area_Code IN ('005', '015')"
    pages = {
        (layer, f"(TaxParcelNumber IN ('2000000001','2000000002','2000000003')) AND ({where})"): [
            {"TaxParcelNumber": "2000000001", "latitude": 47.2529, "longitude": -122.4443},
        ],
        (table, "TaxParcelNumber IN ('2000000002','2000000003')"): [
            {"TaxParcelNumber": "2000000002", "Parent": "2000000009"},
        ],
        (layer, f"(TaxParcelNumber IN ('2000000009')) AND ({where})"): [
            {"TaxParcelNumber": "2000000009", "latitude": 47.2600, "longitude": -122.4500},
        ],
    }
    calls = []

    def fetch_page(endpoint_url, where_clause, order_by, limit, offset, select=None):
        calls.append((endpoint_url, where_clause))
        return (pages.get((endpoint_url, where_clause), []) if offset == 0 else []), False

    client = ArcGISClient()
    client.get_layer_metadata = _text_key_metadata
    client._fetch_page = fetch_page

    index = client.fetch_centroid_index(
        layer,
        join_key="TaxParcelNumber",
        join_values=["2000000001", "2000000002", "2000000003"],
        via={"table": table, "key": "TaxParcelNumber", "to": "Parent"},
        where=where,
    )

    assert index == {"2000000001": (47.2529, -122.4443), "2000000002": (47.26, -122.45)}
    assert calls == list(pages)

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
            assert kwargs["via"]["to"] == "MAT_SSL"
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
