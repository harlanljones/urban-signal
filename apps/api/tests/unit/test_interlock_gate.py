"""Agent Interlock invariant gate.

Fast, standalone spine checks run before releasing the interlock:
``pytest -m interlock``

Three invariant classes (see docs/adr/0001-agent-interlock.md):
  closure      -- every produced key resolves in its consuming structure
  completeness -- every registered entity has the fields consumers index unguarded
  containment  -- declared geographic hierarchies actually nest
"""

import importlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.config import Settings, settings
from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial import cities as cities_pkg
from src.spatial.city_registry import (
    ALIASES,
    REGISTRY,
    CityId,
    FeedType,
    get_dataset,
    get_job_name,
)
from src.spatial.submarkets import NYC_METRO_BBOX

REPO_ROOT = Path(__file__).resolve().parents[4]
MANIFEST_PATH = REPO_ROOT / "docs" / "agents" / "spine-manifest.txt"

FEED_TOPICS = {
    FeedType.PERMITS: settings.topic_permits,
    FeedType.COMPLAINTS_311: settings.topic_311,
    FeedType.SLA: settings.topic_sla,
    FeedType.DEEDS: settings.topic_deeds,
    # US-72 signal-survey members: unregistered until their own tickets, but
    # the topic mapping is fixed now so a future registration can't drift.
    FeedType.CRIME: settings.topic_crime,
    FeedType.VIOLATIONS: settings.topic_violations,
    FeedType.INSPECTIONS: settings.topic_inspections,
    FeedType.STREET_CUT: settings.topic_street_cut,
    FeedType.EVICTIONS: settings.topic_evictions,
    FeedType.STR: settings.topic_str,
    # US-363 context-measurement families. Both ride ONE topic: they share a
    # single ContextObservationEvent shape and are told apart by `source`,
    # so a second topic would buy nothing but a second consumer.
    FeedType.ENERGY_BENCHMARK: settings.topic_context_observations,
    FeedType.BIKE_PED: settings.topic_context_observations,
    FeedType.GBFS: settings.topic_station_change,
}

KNOWN_PLATFORMS = {"socrata", "arcgis", "accela", "carto", "ckan", "csv", "excel", "gbfs"}

# URI scheme each platform's endpoint must carry (carto/ckan use opaque
# client-parsed URIs; see the client modules).
PLATFORM_SCHEMES = {
    "socrata": "https://",
    "arcgis": "https://",
    "accela": "https://",
    "carto": "carto://",
    "ckan": "ckan://",
    "csv": "https://",
    "excel": "https://",
    # GBFS specs point at the system's auto-discovery root (`gbfs.json`); the
    # named feeds are resolved from it at poll time, not registered here.
    "gbfs": "https://",
}

# Which invariant class guards each spine file. A manifest path absent from
# this map is a torn write waiting to ship undetected.
SPINE_INVARIANTS = {
    "apps/api/src/config.py": ["endpoints declared in settings", "feed topics map to configured topics"],
    "apps/api/src/spatial/city_registry.py": [
        "alias closure",
        "dataset specs complete",
        "job names unique",
        "get_dataset readable errors",
    ],
    "apps/api/src/spatial/cities/__init__.py": ["package exports match registry"],
    "apps/api/src/spatial/geo_utils.py": ["division bboxes nest inside metro", "submarkets inside own division"],
    "apps/api/src/spatial/submarkets.py": ["submarket borough resolves", "division rosters reference declared submarkets"],
    "apps/api/src/producers/scheduler.py": ["producer keys resolve", "platform clients exposed"],
    "apps/api/src/producers/dob_permits_producer.py": ["producer keys resolve", "dataset specs complete"],
    "apps/api/src/producers/complaints_311_producer.py": ["producer keys resolve", "dataset specs complete"],
    "apps/api/src/producers/sla_licenses_producer.py": ["producer keys resolve", "dataset specs complete"],
    "apps/api/src/producers/deeds_acris_producer.py": ["producer keys resolve", "dataset specs complete"],
    "apps/api/src/producers/accela_client.py": ["Accela client reuses ArcGIS REST pagination"],
}

# Geometry attribute -> canonical leaf-constant suffix. The export name for a
# city is derived from the CityId -> cities/<id>.py naming convention (US-429):
# ``<CITY_ID_UPPER>_<SUFFIX>``. No per-city literal table.
GEOMETRY_EXPORT_SUFFIXES = {
    "metro_bbox": "METRO_BBOX",
    "division_bboxes": "DIVISION_BBOXES",
    "divisions": "DIVISIONS",
    "submarkets": "SUBMARKETS",
}


def _city_export_modules(cid: CityId) -> list[object]:
    """Modules carrying the city's registered geometry constants.

    Derived from the ``CityId -> cities/<id>.py`` naming convention. NYC is
    the one exception: its metro bbox and submarkets live in
    ``src.spatial.submarkets`` while its divisions live in ``cities/nyc.py``,
    so both are searched.
    """
    if cid is CityId.NYC:
        import src.spatial.cities.nyc as nyc_module
        from src.spatial import submarkets as submarkets_pkg

        return [nyc_module, submarkets_pkg]
    return [importlib.import_module(f"src.spatial.cities.{cid.value}")]


def _bbox_contains(outer: dict, inner: dict) -> bool:
    return (
        outer["min_lat"] <= inner["min_lat"]
        and inner["max_lat"] <= outer["max_lat"]
        and outer["min_lng"] <= inner["min_lng"]
        and inner["max_lng"] <= outer["max_lng"]
    )


def _point_inside(bbox: dict, lat: float, lng: float) -> bool:
    return bbox["min_lat"] <= lat <= bbox["max_lat"] and bbox["min_lng"] <= lng <= bbox["max_lng"]


def _declared_endpoint_defaults() -> set[str]:
    fields = Settings.model_fields
    schemes = tuple(PLATFORM_SCHEMES.values())
    return {
        f.default
        for f in fields.values()
        if isinstance(f.default, str) and f.default.startswith(schemes)
    }


@pytest.fixture(scope="module")
def scheduler() -> MunicipalIngestionScheduler:
    sched = MunicipalIngestionScheduler(dlq_producer=MagicMock(), rate_limit_delay_seconds=0.0)
    for p in sched.producers.values():
        p.producer = MagicMock()
    return sched


@pytest.mark.interlock
class TestClosure:
    def test_every_alias_resolves_to_a_registration(self):
        for alias, cid in ALIASES.items():
            assert cid in REGISTRY, f"alias {alias!r} resolves to unregistered {cid}"

    def test_every_submarket_borough_resolves_to_a_division(self):
        for cid, reg in REGISTRY.items():
            for name, meta in reg.submarkets.items():
                assert meta.borough in reg.divisions, (
                    f"{cid.value}: submarket {name!r} cites unknown division {meta.borough!r}"
                )

    def test_division_rosters_reference_declared_submarkets(self):
        for cid, reg in REGISTRY.items():
            listed: set[str] = set()
            for div_name, div in reg.divisions.items():
                for sm in div.submarkets:
                    assert sm in reg.submarkets, (
                        f"{cid.value}: division {div_name!r} lists unknown submarket {sm!r}"
                    )
                    listed.add(sm)
            missing = sorted(set(reg.submarkets) - listed)
            assert not missing, f"{cid.value}: submarkets absent from every division roster: {missing}"

    def test_feed_topics_map_to_configured_topics(self):
        for cid, reg in REGISTRY.items():
            for feed, spec in reg.datasets.items():
                assert spec.topic == FEED_TOPICS[feed], (
                    f"{cid.value}/{feed.value}: topic {spec.topic!r} does not match configured "
                    f"{FEED_TOPICS[feed]!r}"
                )


@pytest.mark.interlock
class TestCompleteness:
    def test_registrations_carry_required_fields(self):
        for cid, reg in REGISTRY.items():
            assert reg.name and reg.state
            assert {"lat", "lng"} <= set(reg.center)
            for key in ("min_lat", "max_lat", "min_lng", "max_lng"):
                assert key in reg.metro_bbox, f"{cid.value}: metro bbox missing {key}"
            assert reg.metro_bbox["min_lat"] < reg.metro_bbox["max_lat"]
            assert reg.metro_bbox["min_lng"] < reg.metro_bbox["max_lng"]
            assert reg.division_bboxes and reg.submarkets and reg.divisions

    def test_dataset_specs_complete(self):
        for cid, reg in REGISTRY.items():
            for feed, spec in reg.datasets.items():
                label = f"{cid.value}/{feed.value}"
                assert spec.platform in KNOWN_PLATFORMS, label
                scheme = PLATFORM_SCHEMES[spec.platform]
                assert spec.endpoint.startswith(scheme), (
                    f"{label}: {spec.platform} endpoint must start with {scheme!r}"
                )
                assert spec.watermark_col or spec.ingestion_mode == "snapshot", label
                assert spec.id_keys and all(isinstance(k, str) and k for k in spec.id_keys), label
                assert spec.interval_seconds > 0, label
                assert spec.producer_key == feed.value, (
                    f"{label}: producer_key {spec.producer_key!r} != feed {feed.value!r}"
                )
                if spec.platform == "arcgis":
                    assert spec.oid_field is not None, f"{label}: arcgis spec missing oid_field"

    def test_endpoints_declared_in_settings(self):
        declared = _declared_endpoint_defaults()
        for cid, reg in REGISTRY.items():
            for feed, spec in reg.datasets.items():
                assert spec.endpoint in declared, (
                    f"{cid.value}/{feed.value}: endpoint {spec.endpoint!r} has no settings field"
                )

    def test_job_names_unique(self):
        seen: dict[str, tuple[str, str]] = {}
        for cid, reg in REGISTRY.items():
            for feed in reg.datasets:
                name = get_job_name(feed, cid)
                assert name not in seen, (
                    f"job name {name!r} collision: {(cid.value, feed.value)} vs {seen[name]}"
                )
                seen[name] = (cid.value, feed.value)

    def test_get_dataset_readable_error_for_unregistered_feeds(self):
        for cid, reg in REGISTRY.items():
            for feed in FeedType:
                if feed in reg.datasets:
                    continue
                with pytest.raises(KeyError) as excinfo:
                    get_dataset(cid, feed)
                message = str(excinfo.value)
                assert cid.value in message and feed.value in message

    def test_platform_clients_exposed(self, scheduler):
        keys_by_platform: dict[str, set[str]] = {}
        for reg in REGISTRY.values():
            for spec in reg.datasets.values():
                keys_by_platform.setdefault(spec.platform, set()).add(spec.producer_key)
        for key, wrapper in scheduler.producers.items():
            assert hasattr(wrapper, "socrata"), f"producer {key!r} lacks socrata client"
            for platform, keys in keys_by_platform.items():
                if key in keys:
                    assert getattr(wrapper, platform, None) is not None, (
                        f"producer {key!r} lacks a {platform} client instance but {platform} specs register against it"
                    )


@pytest.mark.interlock
class TestContainment:
    def test_center_inside_metro_bbox(self):
        for cid, reg in REGISTRY.items():
            assert _point_inside(reg.metro_bbox, reg.center["lat"], reg.center["lng"]), cid.value

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for cid, reg in REGISTRY.items():
            for name, bbox in reg.division_bboxes.items():
                assert _bbox_contains(reg.metro_bbox, bbox), f"{cid.value}: division {name!r} escapes metro bbox"

    def test_submarkets_inside_own_division_bbox(self):
        for cid, reg in REGISTRY.items():
            for name, meta in reg.submarkets.items():
                bbox = reg.division_bboxes[meta.borough]
                assert _point_inside(bbox, meta.lat, meta.lng), (
                    f"{cid.value}: submarket {name!r} outside {meta.borough!r} bbox"
                )


@pytest.mark.interlock
class TestPackageExportsMatchRegistry:
    def test_city_constants_importable_and_identical(self):
        for cid, reg in REGISTRY.items():
            for module in _city_export_modules(cid):
                for attr, suffix in GEOMETRY_EXPORT_SUFFIXES.items():
                    target = getattr(reg, attr)
                    bound = [
                        name
                        for name, value in vars(module).items()
                        if value is target
                    ]
                    assert bound, (
                        f"{module.__name__} binds no name to {cid.value}.{attr} — "
                        f"the leaf does not resolve its registered geometry"
                    )
                    if cid is CityId.NYC:
                        # Identity is covered by
                        # test_nyc_constants_live_in_submarkets_module; nyc.py
                        # also bridges non-suffix aliases (NYC_BOROUGH_BBOXES).
                        continue
                    canonical = f"{cid.value.upper()}_{suffix}"
                    assert canonical in bound, (
                        f"{module.__name__} binds {cid.value}.{attr} only under "
                        f"{bound}; canonical {canonical} is missing or a copy"
                    )
                    assert getattr(cities_pkg, canonical) is target, (
                        f"src.spatial.cities does not re-export {canonical}"
                    )

    def test_every_city_id_resolves_to_a_leaf_module(self):
        for cid in CityId:
            if cid is CityId.NYC:
                continue
            module = _city_export_modules(cid)[0]
            assert module.__name__ == f"src.spatial.cities.{cid.value}"
            assert hasattr(module, "REGISTRATION"), (
                f"cities/{cid.value}.py does not resolve to a registered leaf module"
            )

    def test_nyc_constants_live_in_submarkets_module(self):
        from src.spatial import submarkets as submarkets_pkg

        reg = REGISTRY[CityId.NYC]
        assert submarkets_pkg.NYC_METRO_BBOX is reg.metro_bbox is NYC_METRO_BBOX


@pytest.mark.interlock
class TestSpineCoverage:
    def test_manifest_paths_exist(self):
        assert MANIFEST_PATH.exists()
        for path in _manifest_paths():
            assert (REPO_ROOT / path).exists(), f"spine manifest lists missing file {path}"

    def test_every_spine_file_has_invariant_coverage(self):
        uncovered = sorted(set(_manifest_paths()) - set(SPINE_INVARIANTS))
        assert not uncovered, f"spine files with no invariant guarding them: {uncovered}"


def _manifest_paths() -> list[str]:
    lines = MANIFEST_PATH.read_text().splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


@pytest.mark.interlock
class TestDashboardWiring:
    """A registration is done when the city appears on the map — not when
    REGISTRY accepts it (AGENTS.md, "City registration rule").

    The national map has three layers: the dashboard's METRO_META entry (chip
    label + deep-link validation), the snapshot manifest's metro_index/tile
    data the chips and viewport loader are driven from, and the synced workers
    static copy. A registry entry missing from any layer fails the gate in the
    same run.
    """

    DASHBOARD = REPO_ROOT / "apps" / "api" / "src" / "serving" / "dashboard.py"
    WORKER_STATIC = REPO_ROOT / "apps" / "dashboard" / "public" / "index.html"

    def _dashboard(self) -> str:
        assert self.DASHBOARD.exists(), f"{self.DASHBOARD} missing — the map was deleted?"
        return self.DASHBOARD.read_text()

    def _metro_meta_ids(self, text: str) -> set[str]:
        """Parse the city ids out of a rendered METRO_META block.

        Same shape the CI/CD pre-flight parser reads
        (scripts/verify_cicd_preflight.py::_metro_meta_ids). The block is
        generated from REGISTRY by get_dashboard_html() (US-427), so this is
        an interface check, not a source-text grep.
        """
        import re

        match = re.search(r"const METRO_META = \{(.*?)\n\s*\};", text, re.DOTALL)
        if not match:
            return set()
        return set(re.findall(r"^\s+(\w+): \{ name:", match.group(1), re.MULTILINE))

    def test_every_registered_city_has_a_metro_meta_entry(self):
        from src.serving.dashboard import get_dashboard_html

        on_map = self._metro_meta_ids(get_dashboard_html())
        registered = {cid.value for cid in REGISTRY}
        missing = sorted(registered - on_map)
        assert not missing, (
            f"registered but not on the map (no METRO_META entry): {missing}. "
            f"METRO_META is generated from REGISTRY (US-427) — a missing entry "
            f"means the dashboard generator is not seeing the registration."
        )
        stale = sorted(on_map - registered)
        assert not stale, (
            f"on the map but not registered: {stale}. Drop the stale entry."
        )

    def test_metro_chips_nav_is_present(self):
        src = self._dashboard()
        assert 'id="metro-chips"' in src, (
            "metro chip navigation missing — every registered city must be "
            "reachable on the all-metros map"
        )

    def test_worker_static_copy_is_in_sync_and_carries_every_city(self):

        from src.serving.dashboard import get_dashboard_html

        if not (REPO_ROOT / "apps" / "dashboard").exists():
            pytest.skip("apps/dashboard deployment surface removed from the tree — no static copy to keep in sync")
        assert self.WORKER_STATIC.exists(), (
            f"{self.WORKER_STATIC} missing while the rest of apps/dashboard exists — "
            f"regenerate it from get_dashboard_html()"
        )
        rendered = get_dashboard_html()
        assert self.WORKER_STATIC.read_text() == rendered, (
            f"{self.WORKER_STATIC} is a stale static copy. "
            f"Run python scripts/export_dashboard.py before closing the wave."
        )
        stale = sorted(self._metro_meta_ids(rendered) - {cid.value for cid in REGISTRY})
        assert not stale, (
            f"apps/dashboard/public/index.html carries metro metadata for "
            f"{stale} without a REGISTRY entry. Re-sync it from "
            f"get_dashboard_html() before closing the wave."
        )


@pytest.mark.interlock
class TestSnapshotWiring:
    """A registration is not done while the batch export skips the city: the KV
    snapshot is the map's only data source, so a city missing from the export
    list renders as an empty grid with "No active catalysts" (2026-08 prod
    incident — san_diego was wired into the dashboard but never exported).
    """

    def test_snapshot_export_covers_every_registered_city(self):
        from src.export.snapshot_builder import SUPPORTED_CITIES

        exported = set(SUPPORTED_CITIES)
        registered = {cid.value for cid in REGISTRY}
        missing = [cid for cid in registered if cid not in exported]
        extra = sorted(exported - registered)
        assert not missing, (
            f"registered but never exported to the KV snapshot: {missing}. "
            f"Derive SUPPORTED_CITIES from CityId in the same spine hold as the REGISTRY entry."
        )
        assert not extra, (
            f"exported to the KV snapshot but not registered: {extra}. "
            f"Drop the stale entry or register the city."
        )

    def test_grid_tiles_cover_every_registered_city(self, tmp_path):
        """The national map renders cities from res-5 viewport tiles: a metro
        with zero tiles is invisible no matter how far the user zooms."""
        import asyncio
        import json
        from typing import Any

        from src.export.snapshot_builder import (
            CATALYST_THRESHOLD,
            DEFAULT_RESOLUTION,
            build_snapshot,
        )

        class StubEngine:
            def predict_cell_features(
                self, h3_index: str, feature_dict: dict[str, Any], include_shap: bool = True
            ) -> dict[str, Any]:
                return {
                    "h3_index": h3_index,
                    "resolution": DEFAULT_RESOLUTION,
                    "lims_score": float(feature_dict.get("lims_score", 50.0)),
                    "delta_6m_p50": 0.05,
                    "delta_12m_spillover": 0.12,
                    "prob_18m_macro_outperformance": 0.5,
                    "is_catalyst": float(feature_dict.get("lims_score", 0.0)) >= CATALYST_THRESHOLD,
                }

        manifest = asyncio.run(build_snapshot(tmp_path / "dist", engine=StubEngine()))
        tiled = {
            city
            for meta in manifest["tile_index"].values()
            for city in meta["cities"]
        }
        registered = {cid.value for cid in REGISTRY}
        missing = sorted(registered - tiled)
        assert not missing, (
            f"registered but invisible on the national map (no grid tiles): {missing}. "
            f"A city without snapshot cells cannot lazy-load — check its submarkets "
            f"and export coverage in the same spine hold as the REGISTRY entry."
        )
        # The published manifest must be parseable and carry the tile index.
        assert json.loads(
            (tmp_path / "dist" / "manifest.json").read_text()
        )["tile_resolution"] == manifest["tile_resolution"]


@pytest.mark.interlock
class TestNationalWiring:
    """US-383: the national hex layer is not servable until the snapshot
    publishes its chunks and the worker route reads them. A national build
    without a matching publish + route leaves US-384 rendering nothing.
    """

    WORKER_SRC = REPO_ROOT / "apps" / "dashboard" / "src" / "index.ts"
    WORKER_SNAPSHOT_SRC = REPO_ROOT / "apps" / "dashboard" / "src" / "snapshot.ts"

    @staticmethod
    def _national_fixture(root: Path) -> Path:
        import polars as pl

        frame = pl.DataFrame(
            [{"h3_index": "892a10708b7ffff", "jobs_c000": 1200, "workers_c000": 900,
              "jobs_c000_national_pct": 71.5, "workers_c000_national_pct": 66.25,
              "year": 2023, "signal_source": "census_lehd_lodes8"}],
            schema={
                "h3_index": pl.String,
                "jobs_c000": pl.Int64,
                "workers_c000": pl.Int64,
                "jobs_c000_national_pct": pl.Float64,
                "workers_c000_national_pct": pl.Float64,
                "year": pl.Int64,
                "signal_source": pl.String,
            },
        )
        res_dir = root / "national" / "res6"
        res_dir.mkdir(parents=True, exist_ok=True)
        frame.write_parquet(res_dir / "832830fffffffff.parquet")
        return root

    def test_national_layers_published_with_manifest_block(self, tmp_path):
        import asyncio

        from src.export.snapshot_builder import NATIONAL_MAX_CHUNK_BYTES, build_snapshot

        class StubEngine:
            def predict_cell_features(self, h3_index, feature_dict, include_shap=True):
                return {"h3_index": h3_index, "lims_score": 50.0}

        manifest = asyncio.run(
            build_snapshot(
                tmp_path / "dist",
                engine=StubEngine(),
                cities=["nyc"],
                national_dir=self._national_fixture(tmp_path / "national-out"),
            )
        )
        block = manifest.get("national", {}).get("resolutions", {})
        assert block.get("6", {}).get("count") == 1, (
            "national builder data was not published into the snapshot manifest "
            "national block — the national hex layer cannot boot"
        )
        assert "national/index" in manifest["keys"], (
            "national/index integrity key missing from the publish"
        )
        for key, meta in manifest["keys"].items():
            if key.startswith("national/"):
                assert meta["bytes"] <= NATIONAL_MAX_CHUNK_BYTES, (
                    f"{key} is {meta['bytes']:,} bytes, over the US-383 "
                    f"{NATIONAL_MAX_CHUNK_BYTES:,}-byte national chunk budget"
                )

    def test_worker_route_serves_national_chunks(self):
        if not self.WORKER_SRC.exists():
            pytest.skip("apps/dashboard deployment surface removed — no worker route to check")
        src = self.WORKER_SRC.read_text()
        assert "/api/v1/national/" in src, (
            "worker has no /api/v1/national/{res} route — national chunks are "
            "published to KV but unreachable"
        )
        assert "fetchNationalIndex" in src, (
            "worker route does not read the national/index document — clients "
            "cannot discover which res-3 parents to fetch"
        )
        snapshot_src = self.WORKER_SNAPSHOT_SRC.read_text()
        assert 'kvJson(env, "national/index")' in snapshot_src, (
            "snapshot query module no longer reads the national/index key — the "
            "worker cannot serve the national layer index"
        )
