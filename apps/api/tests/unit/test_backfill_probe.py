from unittest.mock import MagicMock

from scripts.backfill_probe import _drop_reason, probe_feed, probe_registry

from src.spatial.city_registry import DatasetSpec, FeedType


def _spec(watermark="IssuedDate"):
    return DatasetSpec(
        endpoint="https://data.example/resource/test.json",
        platform="arcgis",
        watermark_col=watermark,
        id_keys=["id"],
        producer_key="permits",
    )


def test_probe_feed_computes_parse_rate_and_drop_reasons(monkeypatch):
    client = MagicMock()
    client.paginate.return_value = [[
        {"id": "a", "latitude": 1, "longitude": 2, "IssuedDate": "2026-08-20"},
        {"id": "b", "latitude": 1, "longitude": 2, "IssuedDate": "2026-08-21"},
        {"IssuedDate": "2026-08-22"},          # no id -> missing_id
        {"id": "c", "IssuedDate": "2026-08-23"},  # no coords -> missing_geometry
    ]]

    producer = MagicMock()

    def fake_parse(row, city_id=None):
        if row.get("id") and row.get("latitude") and row.get("longitude"):
            return object()
        return None

    producer.parse_socrata_row.side_effect = fake_parse
    monkeypatch.setattr("scripts.backfill_probe.client_for", lambda spec: client)
    monkeypatch.setattr("scripts.backfill_probe.producer_for", lambda key: producer)

    result = probe_feed(
        "baltimore",
        FeedType.PERMITS,
        _spec(),
        max_records=500,
        want_count=False,
    )

    assert result.sampled == 4
    assert result.parsed == 2
    assert result.dropped == 2
    assert result.parse_rate == 0.5
    assert result.drop_reasons == {"missing_id": 1, "missing_geometry": 1}
    assert result.source_count is None
    assert result.error is None
    assert producer.parse_socrata_row.call_count == 4


def test_probe_feed_passes_through_source_count(monkeypatch):
    client = MagicMock()
    client.paginate.return_value = [[{"id": "a", "latitude": 1, "longitude": 2}]]
    producer = MagicMock()
    producer.parse_socrata_row.return_value = object()
    monkeypatch.setattr("scripts.backfill_probe.client_for", lambda spec: client)
    monkeypatch.setattr("scripts.backfill_probe.producer_for", lambda key: producer)
    monkeypatch.setattr("scripts.backfill_probe.source_count", lambda spec: 12345)

    result = probe_feed(
        "baltimore",
        FeedType.PERMITS,
        _spec(),
        max_records=500,
        want_count=True,
    )
    assert result.source_count == 12345
    assert result.parsed == 1
    assert result.parse_rate == 1.0


def test_probe_feed_samples_snapshot_feeds_without_watermark(monkeypatch):
    client = MagicMock()
    client.paginate.return_value = [[
        {"id": "a", "latitude": 1, "longitude": 2},
        {"id": "b", "latitude": 1, "longitude": 2},
    ]]
    producer = MagicMock()
    producer.parse_socrata_row.return_value = object()
    monkeypatch.setattr("scripts.backfill_probe.client_for", lambda spec: client)
    monkeypatch.setattr("scripts.backfill_probe.producer_for", lambda key: producer)

    result = probe_feed(
        "montgomery",
        FeedType.SLA,
        _spec(watermark=""),
        max_records=500,
        want_count=False,
    )

    # Snapshot feeds fetch without an order_by so each client's default
    # stable ordering applies.
    _, kwargs = client.paginate.call_args
    assert "order_by" not in kwargs
    assert result.sampled == 2
    assert result.parse_rate == 1.0
    assert result.order_by == ""


def test_probe_registry_scopes_to_requested_city(monkeypatch):
    captured = []

    def fake_probe_feed(city_id, feed, spec, **kwargs):
        captured.append((city_id, feed.value))
        return object()

    monkeypatch.setattr("scripts.backfill_probe.probe_feed", fake_probe_feed)
    results = probe_registry(city_ids={"baltimore"}, want_count=False)
    # Baltimore registers permits, 311, sla, and deeds (MD SDAT).
    assert len(results) == 4
    assert all(city == "baltimore" for city, _ in captured)
    assert {feed for _, feed in captured} == {"permits", "311", "sla", "deeds"}


def test_drop_reason_classification():
    assert _drop_reason({"latitude": 1, "longitude": 2}, {}) == "missing_id"
    assert _drop_reason({"id": "x"}, {}) == "missing_geometry"
    # Dotted field-map keys index nested containers.
    fm = {"incident_id": ["sr_id"], "latitude": ["geometry.latitude"], "longitude": ["geometry.longitude"]}
    assert _drop_reason(
        {"sr_id": "x", "geometry": {"latitude": 1, "longitude": 2}},
        fm,
    ) == "other"
