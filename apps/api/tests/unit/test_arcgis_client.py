"""ArcGISClient page reads, and the registry's ArcGIS endpoints.

A FeatureServer service root answers ``/query`` at HTTP 200 with its own
description instead of features. Five feeds (Boise crime, Las Vegas crime and
three Louisville feeds) were registered at a service root and reported SUCCESS
with zero rows until 2026-09-30.
"""

import re

import pytest

from src.producers.arcgis_client import ArcGISClient
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
