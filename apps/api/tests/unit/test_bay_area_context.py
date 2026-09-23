"""Unit tests for the Bay Area context-layer builder (src/export/bay_area_context.py).

Every layer's network step is stubbed; these tests cover the orchestration the
builder adds on top of the US-439..443 pipelines: per-layer isolation, the
merged per-hex table, and the meta file the snapshot builder reads back.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import h3
import polars as pl
import pytest
from shapely.geometry import box

from src.export import bay_area_context as ctx
from src.export.bay_area_context import (
    CONTEXT_META,
    CONTEXT_METRIC_KEYS,
    CONTEXT_TABLE,
    BuildConfig,
    LayerSkipped,
    bay_area_permit_cities,
    build_context,
    latest_per_zcta,
    load_context,
    market_hex_values,
    merge_layers,
    permit_hex_values,
)
from src.spatial.city_registry import CityId

SF_CELL = h3.latlng_to_cell(37.7793, -122.4193, 9)  # Civic Center
SF_CELL_2 = h3.latlng_to_cell(37.7952, -122.4028, 9)  # Financial District
AS_OF = datetime(2026, 9, 1, tzinfo=UTC)


def _cfg(tmp_path: Path, env: dict[str, str] | None = None) -> BuildConfig:
    return BuildConfig(cache_dir=tmp_path / "cache", as_of=AS_OF, env=env or {})


# --------------------------------------------------------------------------- #
# merge + build_context                                                       #
# --------------------------------------------------------------------------- #
def test_merge_layers_keeps_nulls_and_drops_unknown_keys():
    frame = merge_layers(
        {
            "lodes": {SF_CELL: {"jobs_total": 120.0, "jobs_to_residents": None}},
            "overture": {SF_CELL_2: {"building_count": 7.0, "not_a_metric": 1.0}},
        }
    )
    assert frame.columns == ["h3_index", *CONTEXT_METRIC_KEYS]
    rows = {row["h3_index"]: row for row in frame.iter_rows(named=True)}
    assert rows[SF_CELL]["jobs_total"] == 120.0
    assert rows[SF_CELL]["jobs_to_residents"] is None
    assert rows[SF_CELL]["building_count"] is None
    assert rows[SF_CELL_2]["building_count"] == 7.0
    assert "not_a_metric" not in frame.columns


def test_build_context_isolates_failed_and_skipped_layers(tmp_path: Path):
    def ok(_cfg: BuildConfig) -> dict[str, dict[str, Any]]:
        return {SF_CELL: {"jobs_total": 50.0, "jobs_to_residents": 2.5}}

    def skipped(_cfg: BuildConfig) -> dict[str, dict[str, Any]]:
        raise LayerSkipped("BAY_511_API_KEY is not set")

    def broken(_cfg: BuildConfig) -> dict[str, dict[str, Any]]:
        raise ConnectionError("tigerweb.geo.census.gov unreachable")

    def empty(_cfg: BuildConfig) -> dict[str, dict[str, Any]]:
        return {}

    out = tmp_path / "context"
    meta = build_context(
        out,
        _cfg(tmp_path),
        builders={"lodes": ok, "transit": skipped, "market": broken, "overture": empty},
    )

    assert meta["layers"]["lodes"]["status"] == "ok"
    assert meta["layers"]["lodes"]["hexes"] == 1
    assert meta["layers"]["transit"] == {
        **meta["layers"]["transit"],
        "status": "skipped",
        "reason": "BAY_511_API_KEY is not set",
    }
    assert meta["layers"]["market"]["status"] == "failed"
    assert "unreachable" in meta["layers"]["market"]["reason"]
    assert meta["layers"]["overture"]["status"] == "failed"
    # Attribution travels with every layer, including ones that did not run.
    assert "LODES" in meta["layers"]["lodes"]["attribution"]
    assert "ODbL" in meta["layers"]["overture"]["attribution"]
    # Only metrics from layers that produced data are offered to the map.
    assert [m["key"] for m in meta["metrics"]] == ["jobs_total", "jobs_to_residents"]

    assert (out / CONTEXT_TABLE).is_file()
    assert json.loads((out / CONTEXT_META).read_text()) == meta


def test_build_context_raises_and_writes_nothing_when_no_layer_has_data(tmp_path: Path):
    def broken(_cfg: BuildConfig) -> dict[str, dict[str, Any]]:
        raise RuntimeError("down")

    out = tmp_path / "context"
    with pytest.raises(RuntimeError, match="No Bay Area context layer produced data"):
        build_context(out, _cfg(tmp_path), builders={"lodes": broken})
    assert not (out / CONTEXT_TABLE).exists()


def test_load_context_round_trip_omits_nulls(tmp_path: Path):
    out = tmp_path / "context"
    build_context(
        out,
        _cfg(tmp_path),
        builders={
            "lodes": lambda _c: {SF_CELL: {"jobs_total": 10.0, "jobs_to_residents": None}},
            "overture": lambda _c: {SF_CELL_2: {"building_count": 3.0, "poi_density": 4.0}},
        },
    )
    loaded = load_context(out)
    assert loaded is not None
    values, meta = loaded
    assert values == {
        SF_CELL: {"jobs_total": 10.0},
        SF_CELL_2: {"building_count": 3.0, "poi_density": 4.0},
    }
    assert meta["rows"] == 2


def test_load_context_absent_returns_none(tmp_path: Path):
    assert load_context(tmp_path) is None


# --------------------------------------------------------------------------- #
# Layer builders                                                              #
# --------------------------------------------------------------------------- #
def test_transit_layer_skips_without_511_key(tmp_path: Path):
    with pytest.raises(LayerSkipped, match="BAY_511_API_KEY"):
        ctx.build_transit_layer(_cfg(tmp_path, env={}))


def test_transit_layer_scores_the_merged_feed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.producers import bay_area_511_client

    feed = {
        "stops": [("s1", 37.7793, -122.4193, "Civic Center")],
        "routes": [{"route_id": "r1", "route_type": "1"}],
        "trips": [{"trip_id": f"t{i}", "route_id": "r1", "service_id": "wk"} for i in range(6)],
        "stop_times": [
            {"trip_id": f"t{i}", "stop_id": "s1", "arrival_time": f"07:{i * 10:02d}:00"}
            for i in range(6)
        ],
        "calendar": [
            {"service_id": "wk", "monday": "1", "tuesday": "1", "wednesday": "1",
             "thursday": "1", "friday": "1", "saturday": "0", "sunday": "0"}
        ],
    }
    seen_keys: list[str] = []

    class FakeClient:
        def __init__(self, api_key: str):
            seen_keys.append(api_key)

        def fetch_all_operator_feeds(self) -> dict[str, Any]:
            return feed

    monkeypatch.setattr(bay_area_511_client, "Bay511Client", FakeClient)
    values = ctx.build_transit_layer(_cfg(tmp_path, env={"BAY_511_API_KEY": " k "}))
    assert seen_keys == ["k"]
    assert values[SF_CELL]["transit_score"] > 0
    # k-ring propagation reaches neighbors with a lower, decayed score.
    neighbor = next(c for c in h3.grid_ring(SF_CELL, 1))
    assert 0 < values[neighbor]["transit_score"] < values[SF_CELL]["transit_score"]


def test_lodes_layer_maps_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.spatial import lodes_bay_area_pipeline as lodes

    record = SimpleNamespace(h3_index=SF_CELL, total_jobs=900, jobs_to_residents_ratio=4.5)
    seen: list[Path] = []

    def fake_run(config):
        seen.append(config.cache_dir)
        return SimpleNamespace(records=[record], report={"wac_status": "ok", "rac_status": "ok"})

    monkeypatch.setattr(lodes, "run_bay_area_lodes_pipeline", fake_run)
    values = ctx.build_lodes_layer(_cfg(tmp_path))
    assert values == {SF_CELL: {"jobs_total": 900.0, "jobs_to_residents": 4.5}}
    assert seen == [tmp_path / "cache" / "lodes"]


def test_lodes_layer_fails_when_both_measures_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.spatial import lodes_bay_area_pipeline as lodes

    monkeypatch.setattr(
        lodes,
        "run_bay_area_lodes_pipeline",
        lambda config: SimpleNamespace(
            records=[],
            report={"wac_status": "no_data", "rac_status": "no_data", "wac_error": "404"},
        ),
    )
    with pytest.raises(RuntimeError, match="WAC and RAC both unavailable"):
        ctx.build_lodes_layer(_cfg(tmp_path))


def test_overture_layer_merges_buildings_and_places(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from src.spatial import overture_pipeline

    result = SimpleNamespace(
        building_metrics=[SimpleNamespace(h3_index=SF_CELL, building_count=12)],
        poi_metrics=[
            SimpleNamespace(h3_index=SF_CELL, poi_density=30),
            SimpleNamespace(h3_index=SF_CELL_2, poi_density=5),
        ],
    )
    monkeypatch.setattr(overture_pipeline, "run_overture_density_pipeline", lambda: result)
    assert ctx.build_overture_layer(_cfg(tmp_path)) == {
        SF_CELL: {"building_count": 12.0, "poi_density": 30.0},
        SF_CELL_2: {"poi_density": 5.0},
    }


def test_bay_area_permit_cities_are_the_registered_bay_area_permit_feeds():
    cities = bay_area_permit_cities()
    assert CityId.SAN_FRANCISCO in cities
    assert CityId.SAN_JOSE in cities
    assert CityId.NYC not in cities


def test_permit_hex_values_compute_momentum_per_hex():
    def event(cell: str, days_ago: int, cost: float, proposed=None, existing=None) -> dict[str, Any]:
        return {
            "h3_res9": cell,
            "issuance_date": AS_OF - timedelta(days=days_ago),
            "estimated_cost": cost,
            "proposed_dwelling_units": proposed,
            "existing_dwelling_units": existing,
        }

    values = permit_hex_values(
        [
            event(SF_CELL, 10, 1_000_000, proposed=12, existing=2),
            event(SF_CELL, 100, 500_000),
            event(SF_CELL, 150, 0),
            event(SF_CELL_2, 400, 9_000_000),  # outside the 180d window
        ],
        AS_OF,
    )
    assert set(values) == {SF_CELL}
    cell = values[SF_CELL]
    assert cell["permit_velocity_60_180"] == pytest.approx(1.0)  # 1 / (3 / 3)
    assert cell["permit_capex_60d"] > 0
    assert cell["residential_unit_delta"] == 10.0
    assert permit_hex_values([], AS_OF) == {}


def test_permits_layer_survives_one_city_failing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fake_fetch(city_id, since):
        assert since == AS_OF - timedelta(days=ctx.PERMIT_LOOKBACK_DAYS)
        if city_id is CityId.SAN_JOSE:
            raise ConnectionError("ckan down")
        return [{
            "h3_res9": SF_CELL,
            "issuance_date": AS_OF - timedelta(days=5),
            "estimated_cost": 100.0,
            "proposed_dwelling_units": None,
            "existing_dwelling_units": None,
        }]

    monkeypatch.setattr(ctx, "fetch_recent_permits", fake_fetch)
    values = ctx.build_permits_layer(_cfg(tmp_path))
    assert set(values) == {SF_CELL}


def test_permits_layer_fails_when_every_city_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fail(city_id, since):
        raise ConnectionError(f"{city_id.value} down")

    monkeypatch.setattr(ctx, "fetch_recent_permits", fail)
    with pytest.raises(RuntimeError, match="san_francisco: san_francisco down"):
        ctx.build_permits_layer(_cfg(tmp_path))


def test_fetch_recent_permits_formats_text_watermark_and_keeps_geocoded(monkeypatch: pytest.MonkeyPatch):
    calls: list[dict[str, Any]] = []

    class FakeClient:
        def paginate(self, **kwargs):
            calls.append(kwargs)
            yield [{"id": "a"}, {"id": "b"}]

    class FakeParser:
        def _client_for(self, platform: str) -> FakeClient:
            assert platform == "ckan"
            return FakeClient()

        def parse_socrata_row(self, row: dict[str, Any], city_id: str | None = None):
            if row["id"] == "b":  # un-geocodable row
                return SimpleNamespace(h3_res9=None, model_dump=dict)
            return SimpleNamespace(h3_res9=SF_CELL, model_dump=lambda: {"h3_res9": SF_CELL})

    monkeypatch.setattr(ctx, "_kafka_free_permit_parser", FakeParser)
    events = ctx.fetch_recent_permits(CityId.SAN_JOSE, datetime(2026, 3, 5, 14, 0, tzinfo=UTC))
    assert events == [{"h3_res9": SF_CELL}]
    # San Jose's M/D/YYYY text watermark is compared in its own format.
    assert "03/05/2026 02:00:00 PM" in calls[0]["where_clause"]
    assert calls[0]["max_records"] == ctx.PERMIT_MAX_RECORDS


def test_latest_per_zcta_relabels_current_and_drops_stale():
    table = {
        "94103": {date(2026, 6, 30): 1.0, date(2026, 7, 31): 2.0},
        "94110": {date(2026, 6, 30): 3.0},
        "94501": {date(2025, 1, 31): 9.0},  # stale
    }
    current, newest = latest_per_zcta(table)
    assert newest == date(2026, 7, 31)
    assert current == {
        "94103": {date(2026, 7, 31): 2.0},
        "94110": {date(2026, 7, 31): 3.0},
    }
    assert latest_per_zcta({}) == ({}, None)


def test_market_hex_values_blend_and_area_weight():
    lat, lng = h3.cell_to_latlng(SF_CELL)
    square = box(lng - 0.01, lat - 0.01, lng + 0.01, lat + 0.01)
    july = date(2026, 7, 31)
    values = market_hex_values(
        redfin_sale={"94103": {july: 1_000_000.0}},
        zillow_sale={"94103": {july: 1_500_000.0}},
        zillow_rent={"94103": {july: 3_000.0}},
        polygon_fn=lambda zctas: {z: square for z in zctas},
    )
    assert SF_CELL in values
    # Redfin 0.6 / Zillow 0.4 precedence, then a single-ZCTA area average.
    assert values[SF_CELL]["median_sale_price"] == pytest.approx(1_200_000.0)
    assert values[SF_CELL]["rent_index"] == pytest.approx(3_000.0)
    assert market_hex_values({}, {}, {}, polygon_fn=lambda z: {}) == {}


def test_written_table_schema_is_float_columns(tmp_path: Path):
    out = tmp_path / "context"
    build_context(
        out,
        _cfg(tmp_path),
        builders={"lodes": lambda _c: {SF_CELL: {"jobs_total": 1.0}}},
    )
    frame = pl.read_parquet(out / CONTEXT_TABLE)
    assert frame.schema["h3_index"] == pl.Utf8
    assert all(frame.schema[key] == pl.Float64 for key in CONTEXT_METRIC_KEYS)
