"""ArcGISClient page reads, and the registry's ArcGIS endpoints.

A FeatureServer service root answers ``/query`` at HTTP 200 with its own
description instead of features. Five feeds (Boise crime, Las Vegas crime and
three Louisville feeds) were registered at a service root and reported SUCCESS
with zero rows until 2026-09-30.
"""

import re
from urllib.parse import parse_qs

import httpx
import pytest

from src.producers import arcgis_client
from src.producers.arcgis_client import ArcGISClient, layer_time_zone
from src.spatial.city_registry import REGISTRY

_LAYER = "https://example.test/arcgis/rest/services/Crimes/FeatureServer/0"
_ROOT = "https://example.test/arcgis/rest/services/Crimes/FeatureServer"


def _client_answering(monkeypatch, payload):
    client = ArcGISClient()
    monkeypatch.setattr(
        client,
        "get_layer_metadata",
        lambda url: {"date_fields": set(), "oid_field": "OBJECTID", "max_record_count": 1000},
    )
    monkeypatch.setattr(client, "_request_json", lambda url, params: payload)
    return client


def test_a_service_root_answer_raises_instead_of_reading_as_empty(monkeypatch):
    client = _client_answering(monkeypatch, {"layers": []})

    with pytest.raises(RuntimeError, match="service root"):
        list(client.paginate(endpoint_url=_ROOT, max_records=10))


def test_a_layer_with_no_matching_rows_is_still_an_empty_page(monkeypatch):
    client = _client_answering(monkeypatch, {"features": []})

    assert client._fetch_page(_LAYER, "1=1", "", 10, 0) == ([], False)
    assert list(client.paginate(endpoint_url=_LAYER, max_records=10)) == []


_LAYER_INDEX = re.compile(r"/(FeatureServer|MapServer)/\d+/?$")


def test_every_registered_arcgis_endpoint_names_a_layer():
    missing = []
    for city_id, registration in REGISTRY.items():
        for feed, spec in registration.datasets.items():
            if spec.platform != "arcgis":
                continue
            urls = [
                spec.endpoint,
                *(spec.endpoint_by_year or {}).values(),
                *(spec.fallback_endpoints or []),
            ]
            missing += [
                (city_id.value, feed.value, url)
                for url in urls
                if url and "/rest/services/" in url and not _LAYER_INDEX.search(url)
            ]
    assert not missing, missing


def test_select_is_sent_as_out_fields(monkeypatch):
    client = _client_answering(monkeypatch, {"features": []})
    sent = []

    def answer(url, params):
        sent.append(params["outFields"])
        return {"features": []}

    monkeypatch.setattr(client, "_request_json", answer)
    list(client.paginate(endpoint_url=_LAYER, max_records=10, select="OBJECTID,SaleDate"))
    list(client.paginate(endpoint_url=_LAYER, max_records=10))

    assert sent == ["OBJECTID,SaleDate", "*"]


def test_every_arcgis_select_names_the_columns_a_poll_reads():
    """``select`` becomes ``outFields``, and a column left out of it arrives
    missing: the field map, id keys, watermark, object id and sort columns must
    all be selected."""
    gaps = []
    for city_id, registration in REGISTRY.items():
        for feed, spec in registration.datasets.items():
            if spec.platform != "arcgis" or not spec.select:
                continue
            selected = {column.strip() for column in spec.select.split(",")}
            needed = {
                column
                for columns in spec.field_map.values()
                for column in (columns if isinstance(columns, list) else [columns])
            }
            needed |= set(spec.id_keys) | {spec.watermark_col, spec.oid_field or ""}
            needed |= {term.split()[0] for term in (spec.order_by or "").split(",") if term.strip()}
            if needed - selected - {""}:
                gaps.append((city_id.value, feed.value, sorted(needed - selected - {""})))
    assert not gaps, gaps


def test_layer_time_zone_reads_the_date_fields_reference():
    """A layer reads ``where`` literals in the zone its reference names."""
    assert layer_time_zone(
        {"timeZone": "Eastern Standard Time", "timeZoneIANA": "America/New_York", "respectsDaylightSaving": True}
    ) == "America/New_York"
    # Servers before 11.x give only a Windows name (Des Moines, Durham).
    assert layer_time_zone({"timeZone": "Central Standard Time", "respectsDaylightSaving": True}) == "America/Chicago"
    assert layer_time_zone({"timeZone": "Central Standard Time", "respectsDaylightSaving": False}) == "Etc/GMT+6"
    assert layer_time_zone({"timeZone": "US Mountain Standard Time"}) == "America/Phoenix"
    assert layer_time_zone({"timeZoneIANA": "Etc/GMT+7"}) == "Etc/GMT+7"
    for utc in (None, {}, {"timeZone": "UTC"}, {"timeZoneIANA": "Etc/UTC"}):
        assert layer_time_zone(utc) is None


def test_layer_metadata_carries_the_time_zone_and_numeric_fields(monkeypatch):
    client = ArcGISClient()
    monkeypatch.setattr(
        client,
        "_request_json",
        lambda url, params: {
            "fields": [
                {"name": "ADDDATE", "type": "esriFieldTypeDate"},
                {"name": "LRSN", "type": "esriFieldTypeDouble"},
                {"name": "SSL", "type": "esriFieldTypeString"},
            ],
            "objectIdField": "OBJECTID",
            "maxRecordCount": 1000,
            "dateFieldsTimeReference": {"timeZone": "Eastern Standard Time", "timeZoneIANA": "America/New_York"},
        },
    )

    meta = client.get_layer_metadata(_LAYER)

    assert meta["time_zone"] == "America/New_York"
    assert meta["date_fields"] == {"ADDDATE"}
    assert meta["numeric_fields"] == {"LRSN"}


def test_a_query_too_long_for_a_url_is_posted(monkeypatch):
    """ArcGIS Online answers 404 to a GET past about 2,000 characters, which a
    text watermark's list of dates can pass; the query goes as a form POST."""
    seen = []

    def answer(request):
        form = parse_qs(request.content.decode()) if request.method == "POST" else {}
        seen.append((request.method, form.get("where", [request.url.params.get("where")])[0]))
        return httpx.Response(200, json={"features": []})

    real_client = httpx.Client
    monkeypatch.setattr(
        arcgis_client.httpx, "Client",
        lambda **kw: real_client(transport=httpx.MockTransport(answer), **kw),
    )
    dates = ", ".join(f"'{month:02d}/{day:02d}/2026'" for month in (5, 6, 7, 8) for day in range(1, 31))
    long_where = f"SALEDATE IN ({dates})"
    client = ArcGISClient()

    client._request_json(f"{_LAYER}/query", {"where": "1=1", "f": "json"})
    client._request_json(f"{_LAYER}/query", {"where": long_where, "resultOffset": 0, "f": "json"})

    assert seen == [("GET", "1=1"), ("POST", long_where)]
