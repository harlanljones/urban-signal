from src.producers.openfema_client import OpenFemaClient, odata_date_filter


def test_entity_name_and_date_filter_are_endpoint_agnostic():
    assert OpenFemaClient.entity_name("https://example.test/v3/NfipClaims") == "NfipClaims"
    assert odata_date_filter("dateOfLoss", "2026-08-03T12:00:00+00:00") == "dateOfLoss ge '2026-08-03'"


def test_paginate_uses_odata_top_skip_and_entity_key(monkeypatch):
    client = OpenFemaClient()
    calls = []
    payloads = iter([
        {"NfipClaims": [{"id": 1}, {"id": 2}]},
        {"NfipClaims": [{"id": 3}]},
    ])

    def fake_get(endpoint, params):
        calls.append((endpoint, params))
        return next(payloads)

    monkeypatch.setattr(client, "_get", fake_get)
    assert list(client.paginate("https://example.test/v3/NfipClaims", batch_size=2)) == [
        [{"id": 1}, {"id": 2}], [{"id": 3}]
    ]
    assert calls[0][1]["$top"] == 2 and calls[0][1]["$skip"] == 0
    assert calls[1][1]["$skip"] == 2
