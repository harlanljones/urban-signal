from src.producers.nrel_afdc_client import NrelAfdcClient


def test_normalize_response_and_snapshot_diff():
    payload = {"fuel_stations": [{"id": 2}, {"id": "3"}]}
    assert NrelAfdcClient.rows(payload) == [{"id": 2}, {"id": "3"}]
    assert NrelAfdcClient.diff({"2": {"id": 2}}, {"2": {"id": 2}, "3": {"id": "3"}}) == [{"id": "3"}]


def test_paginate_uses_key_and_offset(monkeypatch):
    client = NrelAfdcClient(api_key="secret", page_size=2)
    calls = []
    payloads = iter([
        {"fuel_stations": [{"id": 1}, {"id": 2}]},
        {"fuel_stations": [{"id": 3}]},
    ])
    monkeypatch.setattr(client, "_get", lambda endpoint, params: (calls.append((endpoint, params)) or next(payloads)))
    assert list(client.paginate("https://example.test", fuel_type_code="ELEC")) == [
        [{"id": 1}, {"id": 2}], [{"id": 3}]
    ]
    assert calls[0][0] == "https://example.test"
    assert calls[0][1]["api_key"] == "secret"
    assert calls[0][1]["offset"] == 0 and calls[1][1]["offset"] == 2
