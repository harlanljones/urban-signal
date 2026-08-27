"""Unit tests for the US-182 AcquisitionSpec + AcquisitionEngine.

These tests are oracle-driven against the *existing* acquisition logic the
engine consolidates, so US-182 is provably behavior-preserving:

* endpoint resolution   -> src.spatial.city_registry.resolve_endpoint
* WHERE construction    -> src.producers.watermarks + scheduler.poll_job
* backfill WHERE shape  -> scripts.backfill_loader.build_query_shape
* watermark bookkeeping -> scheduler.poll_job (live) and the watermark helpers
* pagination kwargs     -> the scheduler's own client_kwargs assembly (live)

No caller is routed through the engine; these only assert equivalence.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from src.producers.acquisition import (
    AcquisitionSpec,
    AcquisitionEngine,
    advance_event_watermark,
    advance_text_watermark,
    build_pagination_kwargs,
    build_where,
    is_future_watermark,
    load_state_watermark,
    newest_valid_watermark,
    resolve_endpoint,
)
from src.producers.scheduler import MunicipalIngestionScheduler
from src.producers.watermarks import (
    watermark_comparison,
    watermark_exclude_clause,
)
from src.spatial.city_registry import CityId, DatasetSpec, FeedType, REGISTRY, get_dataset


REPRESENTATIVE_FIELDS = {
    "endpoint_by_year": {"2025": "https://x/2025", "2026": "https://x/2026"},
    "watermark_type": "text",
    "watermark_format": "%Y%m%d",
    "watermark_exclude": ["ZZZZZZZZ"],
    "order_by": "sale_date ASC",
    "id_col": "propertyid",
    "select": "a,b,c",
    "fallback_endpoints": ["https://fb1", "https://fb2"],
    "where": "status = 'ISSUED'",
    "needs_geocode": True,
    "geocode_context": "Milwaukee, WI",
    "field_map": {"job_id": ["record_id"], "issuance_date": ["date_issued"]},
    "ingestion_mode": "incremental",
    # formerly "dead-but-referenced" keys (now typed)
    "oid_field": "OBJECTID",
    "max_record_count": 2000,
    "expected_cadence_days": 7,
    "alarm_exempt": False,
}


def _scheduler() -> MunicipalIngestionScheduler:
    s = MunicipalIngestionScheduler()
    for p in s.producers.values():
        p.producer = MagicMock()
    return s


# --------------------------------------------------------------------------- #
# 1. AcquisitionSpec.from_dataset_spec round-trips (incl. dead keys)          #
# --------------------------------------------------------------------------- #
def test_from_dataset_spec_roundtrip_including_dead_keys():
    ds = DatasetSpec(
        endpoint="https://data.example/resource/x.json",
        platform="csv",
        watermark_col="sale_date",
        id_keys=["propertyid"],
        topic="raw.municipal.deeds",
        interval_seconds=600.0,
        producer_key="deeds",
        **REPRESENTATIVE_FIELDS,
    )
    spec = AcquisitionSpec.from_dataset_spec(ds)

    # Typed attributes reflect the meaningful keys.
    assert spec.endpoint == ds.endpoint
    assert spec.platform == "csv"
    assert spec.watermark_col == "sale_date"
    assert spec.endpoint_by_year == {"2025": "https://x/2025", "2026": "https://x/2026"}
    assert spec.watermark_type == "text"
    assert spec.watermark_format == "%Y%m%d"
    assert spec.watermark_exclude == ["ZZZZZZZZ"]
    assert spec.order_by == "sale_date ASC"
    assert spec.id_col == "propertyid"
    assert spec.select == "a,b,c"
    assert spec.fallback_endpoints == ["https://fb1", "https://fb2"]
    assert spec.where == "status = 'ISSUED'"
    assert spec.needs_geocode is True
    assert spec.geocode_context == "Milwaukee, WI"
    assert spec.field_map == {"job_id": ["record_id"], "issuance_date": ["date_issued"]}
    assert spec.ingestion_mode == "incremental"
    # Formerly dead-but-referenced keys are now typed.
    assert spec.oid_field == "OBJECTID"
    assert spec.max_record_count == 2000

    # Round-trip: the reconstructed DatasetSpec carries the same typed fields.
    rebuilt = spec.to_dataset_spec()
    assert rebuilt.endpoint == ds.endpoint
    assert rebuilt.platform == ds.platform
    assert rebuilt.watermark_col == ds.watermark_col
    assert rebuilt.id_keys == ds.id_keys
    assert rebuilt.topic == ds.topic
    assert rebuilt.interval_seconds == ds.interval_seconds
    assert rebuilt.producer_key == ds.producer_key
    assert rebuilt.endpoint_by_year == ds.endpoint_by_year
    assert rebuilt.watermark_type == ds.watermark_type
    assert rebuilt.watermark_format == ds.watermark_format
    assert rebuilt.watermark_exclude == ds.watermark_exclude
    assert rebuilt.order_by == ds.order_by
    assert rebuilt.id_col == ds.id_col
    assert rebuilt.select == ds.select
    assert rebuilt.fallback_endpoints == ds.fallback_endpoints
    assert rebuilt.where == ds.where
    assert rebuilt.needs_geocode == ds.needs_geocode
    assert rebuilt.geocode_context == ds.geocode_context
    assert rebuilt.field_map == ds.field_map
    assert rebuilt.ingestion_mode == ds.ingestion_mode
    assert rebuilt.oid_field == ds.oid_field
    assert rebuilt.max_record_count == ds.max_record_count
    assert rebuilt.expected_cadence_days == ds.expected_cadence_days
    assert rebuilt.alarm_exempt == ds.alarm_exempt


def test_from_dataset_spec_defaults_when_extra_sparse():
    ds = DatasetSpec(
        endpoint="https://x/y.json",
        platform="socrata",
        watermark_col="created_date",
        id_keys=["id"],
        topic="t",
        producer_key="311",
    )
    spec = AcquisitionSpec.from_dataset_spec(ds)
    assert spec.watermark_type is None
    assert spec.watermark_exclude == []
    assert spec.ingestion_mode == "incremental"
    assert spec.oid_field is None
    assert spec.max_record_count is None


# --------------------------------------------------------------------------- #
# 2. Endpoint resolution vs city_registry.resolve_endpoint                    #
# --------------------------------------------------------------------------- #
def test_resolve_endpoint_matches_registry():
    from src.spatial.city_registry import resolve_endpoint as registry_resolve

    # Year-sliced spec.
    ds = DatasetSpec(
        endpoint="https://base/resource/latest.json",
        endpoint_by_year={"2024": "https://e/2024", "2025": "https://e/2025"},
    )
    spec = AcquisitionSpec.from_dataset_spec(ds)
    for today in (datetime(2024, 6, 1).date(), datetime(2025, 1, 5).date(), datetime(2026, 3, 1).date()):
        assert resolve_endpoint(spec, today) == registry_resolve(ds, today)

    # Non-year-sliced spec always returns the base endpoint.
    ds2 = DatasetSpec(endpoint="https://base/only.json")
    spec2 = AcquisitionSpec.from_dataset_spec(ds2)
    assert resolve_endpoint(spec2, datetime(2025, 1, 1).date()) == "https://base/only.json"


# --------------------------------------------------------------------------- #
# 3. WHERE construction: (a) base only, (b) base + comparison, (c) exclude    #
# --------------------------------------------------------------------------- #
def test_where_base_only():
    assert (
        build_where(
            base_where="status = 'ISSUED'",
            watermark_col="issuance_date",
            high_watermark=None,
            endpoint="https://data.example/resource/x.json",
        )
        == "(status = 'ISSUED')"
    )


def test_where_base_and_watermark_comparison():
    endpoint = "https://data.example/resource/x.json"
    got = build_where(
        base_where="status = 'ISSUED'",
        watermark_col="issuance_date",
        high_watermark="2026-01-01T00:00:00",
        endpoint=endpoint,
    )
    expected = "(status = 'ISSUED') AND " + watermark_comparison(
        "issuance_date", ">", "2026-01-01T00:00:00", endpoint
    )
    assert got == expected
    assert got == "(status = 'ISSUED') AND issuance_date > '2026-01-01T00:00:00'"


def test_where_exclude_guard():
    endpoint = "https://data.example/resource/x.json"
    # exclude only (no high watermark)
    got = build_where(
        base_where="status = 'ISSUED'",
        watermark_col="issuance_date",
        high_watermark=None,
        endpoint=endpoint,
        watermark_exclude=["ZZZZZZZZ"],
    )
    expected = "(status = 'ISSUED') AND " + watermark_exclude_clause(
        "issuance_date", ["ZZZZZZZZ"]
    )
    assert got == expected

    # combined: base + comparison + exclude (the ADR-0005 text shape)
    got2 = build_where(
        base_where=None,
        watermark_col="issuance_date",
        high_watermark="20260810",
        endpoint=endpoint,
        watermark_type="text",
        watermark_format="%Y%m%d",
        watermark_exclude=["ZZZZZZZZ"],
    )
    assert got2 == "issuance_date > '20260810' AND issuance_date NOT IN ('ZZZZZZZZ')"


def test_where_ansi_host_literal():
    endpoint = "https://milwaukeemaps.milwaukee.gov/arcgis/rest/.../0"
    got = build_where(
        base_where=None,
        watermark_col="GIS_DATETIME",
        high_watermark="2026-01-01T00:00:00",
        endpoint=endpoint,
    )
    assert got == "GIS_DATETIME > date '2026-01-01'"


def test_where_ckan_text_literal():
    endpoint = "ckan://example/resource/x"
    got = build_where(
        base_where=None,
        watermark_col="filed_date",
        high_watermark="8/9/2026 12:00:00 AM",
        endpoint=endpoint,
        watermark_type="text",
        watermark_format="%m/%d/%Y %I:%M:%S %p",
    )
    assert got == watermark_comparison(
        "filed_date", ">", "8/9/2026 12:00:00 AM", endpoint,
        watermark_type="text", watermark_format="%m/%d/%Y %I:%M:%S %p",
    )


def test_where_snapshot_suppresses_comparison():
    got = build_where(
        base_where=None,
        watermark_col="issuance_date",
        high_watermark="2026-01-01T00:00:00",
        endpoint="https://x/y.json",
        snapshot=True,
    )
    assert got is None


def test_where_matches_backfill_shape():
    from scripts.backfill_loader import build_query_shape

    meta = {
        "watermark_col": "IssuedDate",
        "endpoint": "https://data.example/resource/x.json",
        "watermark_exclude": ["ZZZZZZZZ"],
    }
    since_dt = datetime(2026, 5, 1, tzinfo=UTC)
    backfill_where, _ = build_query_shape(meta, since_dt)

    engine_where = build_where(
        base_where=None,
        watermark_col="IssuedDate",
        high_watermark=since_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        endpoint="https://data.example/resource/x.json",
        watermark_op=">=",
        watermark_exclude=["ZZZZZZZZ"],
    )
    assert engine_where == backfill_where
    assert engine_where == "IssuedDate >= '2026-05-01T00:00:00' AND IssuedDate NOT IN ('ZZZZZZZZ')"


# --------------------------------------------------------------------------- #
# 4. High-watermark bookkeeping (US-111) — matches the scheduler live          #
# --------------------------------------------------------------------------- #
def test_text_watermark_high_watermark_tracking():
    ds = get_dataset(CityId.NYC, FeedType.PERMITS)
    spec = AcquisitionSpec.from_dataset_spec(ds)
    spec.watermark_type = "text"
    spec.watermark_format = "%Y%m%d"
    spec.watermark_exclude = ["ZZZZZZZZ"]
    spec.watermark_col = "issuance_date"

    rows = [
        {"issuance_date": "ZZZZZZZZ"},
        {"issuance_date": "20260815"},
        {"issuance_date": "20260801"},
    ]
    now = datetime.now(UTC)
    result = advance_text_watermark(spec, rows, high_watermark="20260810", now_dt=now)
    assert result == "20260815"


def test_text_watermark_tracking_matches_scheduler_poll():
    s = _scheduler()
    job_name = "permits"
    s.job_metadata[job_name].update(
        watermark_type="text",
        watermark_format="%Y%m%d",
        watermark_exclude=["ZZZZZZZZ"],
    )
    s.metrics[job_name].high_watermark = "20260810"
    rows = [
        {"job__": "M010", "latitude": "40.7", "longitude": "-73.9", "issuance_date": "ZZZZZZZZ"},
        {"job__": "M011", "latitude": "40.7", "longitude": "-73.9", "issuance_date": "20260815"},
        {"job__": "M012", "latitude": "40.7", "longitude": "-73.9", "issuance_date": "20260801"},
    ]
    s.producers[job_name].socrata.paginate = MagicMock(return_value=[rows])
    scheduler_result = s.poll_job(job_name, limit=100)["high_watermark"]

    ds = get_dataset(CityId.NYC, FeedType.PERMITS)
    spec = AcquisitionSpec.from_dataset_spec(ds)
    spec.watermark_type = "text"
    spec.watermark_format = "%Y%m%d"
    spec.watermark_exclude = ["ZZZZZZZZ"]
    spec.watermark_col = "issuance_date"
    engine_result = advance_text_watermark(
        spec, rows, high_watermark="20260810", now_dt=datetime.now(UTC)
    )
    assert engine_result == scheduler_result == "20260815"


def test_event_watermark_skips_future():
    now = datetime(2026, 8, 26, tzinfo=UTC)
    # future row first, current row second
    high = None
    high = advance_event_watermark(high, datetime(2028, 2, 26, tzinfo=UTC), now)
    assert high is None
    high = advance_event_watermark(high, datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC), now)
    assert high == "2026-08-01T10:00:00"


def test_event_watermark_tracking_matches_scheduler_poll():
    s = _scheduler()
    job_name = "permits"
    s.metrics[job_name].high_watermark = None
    rows = [
        {
            "job__": "M001", "latitude": "40.725", "longitude": "-73.997",
            "job_type": "A1", "initial_cost": "100000",
            "issuance_date": "2028-02-26T00:00:00.000",
        },
        {
            "job__": "M002", "latitude": "40.725", "longitude": "-73.997",
            "job_type": "A1", "initial_cost": "100000",
            "issuance_date": "2026-08-01T10:00:00.000",
        },
    ]
    s.producers[job_name].socrata.paginate = MagicMock(return_value=[rows])
    scheduler_result = s.poll_job(job_name, limit=100)["high_watermark"]

    now = datetime.now(UTC)
    high = None
    for row in rows:
        # Mirror the scheduler's event-attr priority chain.
        val = (
            row.get("issuance_date") or row.get("created_date")
            or row.get("effective_date") or row.get("recorded_date")
        )
        high = advance_event_watermark(high, val, now)
    assert high == scheduler_result == "2026-08-01T10:00:00"


def test_load_state_watermark_guard():
    now = datetime(2026, 8, 26, tzinfo=UTC)
    # future persisted watermark is dropped
    assert load_state_watermark("2028-02-26T00:00:00", None, now) is None
    # valid persisted watermark is kept
    assert load_state_watermark("2026-08-01T00:00:00", None, now) == "2026-08-01T00:00:00"
    # unparseable is kept (only *future* parsed values are dropped)
    assert load_state_watermark("garbage", None, now) == "garbage"


def test_newest_valid_watermark_drops_future():
    entries = [
        ("20260801", datetime(2026, 8, 1, tzinfo=UTC)),
        ("20280226", datetime(2028, 2, 26, tzinfo=UTC)),
        ("20260815", datetime(2026, 8, 15, tzinfo=UTC)),
    ]
    now = datetime(2026, 8, 26, tzinfo=UTC)
    best = newest_valid_watermark(entries, now)
    assert best is not None
    assert best[0] == "20260815"


# --------------------------------------------------------------------------- #
# 5. Per-platform pagination-key translation matches what adapters receive    #
# --------------------------------------------------------------------------- #
def test_pagination_kwargs_match_scheduler_for_every_job():
    s = _scheduler()
    for job_name, meta in s.job_metadata.items():
        spec = AcquisitionSpec(
            endpoint=meta["endpoint_base"],
            platform=meta["platform"],
            watermark_col=meta["watermark_col"],
            order_by=meta.get("order_by"),
            id_col=meta.get("id_col"),
            select=meta.get("select"),
            fallback_endpoints=meta.get("fallback_endpoints") or [],
            watermark_format=meta.get("watermark_format"),
            watermark_exclude=meta.get("watermark_exclude") or [],
        )
        engine_kwargs = build_pagination_kwargs(meta["platform"], spec)
        expected = {
            k: meta[k]
            for k in (
                "order_by",
                "id_col",
                "select",
                "fallback_endpoints",
                "watermark_col",
                "watermark_format",
                "watermark_exclude",
            )
            if meta.get(k)
        }
        assert engine_kwargs == expected, f"job {job_name} diverged: {engine_kwargs} vs {expected}"


def test_pagination_kwargs_includes_declared_keys_for_csv():
    spec = AcquisitionSpec.from_dataset_spec(
        DatasetSpec(
            endpoint="https://x/y.csv",
            platform="csv",
            watermark_col="sale_date",
            id_keys=["propertyid"],
            producer_key="deeds",
            order_by="sale_date ASC",
            id_col="propertyid",
            select="a,b",
            fallback_endpoints=["https://fb1"],
        )
    )
    kwargs = build_pagination_kwargs("csv", spec)
    assert kwargs == {
        "order_by": "sale_date ASC",
        "id_col": "propertyid",
        "select": "a,b",
        "fallback_endpoints": ["https://fb1"],
        "watermark_col": "sale_date",
    }


def test_pagination_kwargs_uniform_across_platforms():
    # The scheduler forwards the same dict to every platform today; the engine
    # reproduces that (the latent per-platform bug is documented, not changed).
    spec = AcquisitionSpec.from_dataset_spec(
        DatasetSpec(
            endpoint="https://x/y.json",
            platform="socrata",
            watermark_col="issuance_date",
            id_keys=["id"],
            producer_key="permits",
            watermark_format="%Y%m%d",
            watermark_exclude=["ZZZZZZZZ"],
        )
    )
    for platform in ("socrata", "arcgis", "carto", "ckan", "csv"):
        kwargs = build_pagination_kwargs(platform, spec)
        assert kwargs == {
            "watermark_col": "issuance_date",
            "watermark_format": "%Y%m%d",
            "watermark_exclude": ["ZZZZZZZZ"],
        }


def test_acquisition_engine_wrapper_matches_functions():
    spec = AcquisitionSpec.from_dataset_spec(
        DatasetSpec(
            endpoint="https://x/y.json",
            platform="socrata",
            watermark_col="issuance_date",
            id_keys=["id"],
            producer_key="permits",
            where="status = 'ISSUED'",
        )
    )
    engine = AcquisitionEngine(spec)
    assert engine.build_where(high_watermark="2026-01-01T00:00:00") == build_where(
        base_where="status = 'ISSUED'",
        watermark_col="issuance_date",
        high_watermark="2026-01-01T00:00:00",
        endpoint="https://x/y.json",
    )
    assert engine.build_pagination_kwargs() == build_pagination_kwargs("socrata", spec)
    assert engine.resolve_endpoint() == resolve_endpoint(spec)
