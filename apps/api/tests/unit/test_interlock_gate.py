"""Agent Interlock invariant gate.

Fast, standalone spine checks run before releasing the interlock:
``pytest -m interlock``

Three invariant classes (see docs/adr/0001-agent-interlock.md):
  closure      -- every produced key resolves in its consuming structure
  completeness -- every registered entity has the fields consumers index unguarded
  containment  -- declared geographic hierarchies actually nest
"""

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
    FeedType.STREET_CUT: settings.topic_street_cut,
    FeedType.EVICTIONS: settings.topic_evictions,
    FeedType.STR: settings.topic_str,
}

KNOWN_PLATFORMS = {"socrata", "arcgis", "carto", "ckan"}

# URI scheme each platform's endpoint must carry (carto/ckan use opaque
# client-parsed URIs; see the client modules).
PLATFORM_SCHEMES = {
    "socrata": "https://",
    "arcgis": "https://",
    "carto": "carto://",
    "ckan": "ckan://",
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
}

CITY_EXPORT_NAMES = {
    CityId.CHICAGO: ("CHICAGO_METRO_BBOX", "CHICAGO_DIVISION_BBOXES", "CHICAGO_DIVISIONS", "CHICAGO_SUBMARKETS"),
    CityId.SAN_FRANCISCO: ("SAN_FRANCISCO_METRO_BBOX", "SAN_FRANCISCO_DIVISION_BBOXES", "SAN_FRANCISCO_DIVISIONS", "SAN_FRANCISCO_SUBMARKETS"),
    CityId.SEATTLE: ("SEATTLE_METRO_BBOX", "SEATTLE_DIVISION_BBOXES", "SEATTLE_DIVISIONS", "SEATTLE_SUBMARKETS"),
    CityId.LOS_ANGELES: ("LA_METRO_BBOX", "LA_DIVISION_BBOXES", "LA_DIVISIONS", "LA_SUBMARKETS"),
    CityId.NEW_ORLEANS: ("NEW_ORLEANS_METRO_BBOX", "NOLA_DIVISION_BBOXES", "NOLA_DIVISIONS", "NOLA_SUBMARKETS"),
    CityId.NORFOLK: ("NORFOLK_METRO_BBOX", "NORFOLK_DIVISION_BBOXES", "NORFOLK_DIVISIONS", "NORFOLK_SUBMARKETS"),
    CityId.DETROIT: ("DETROIT_METRO_BBOX", "DETROIT_DIVISION_BBOXES", "DETROIT_DIVISIONS", "DETROIT_SUBMARKETS"),
    CityId.AUSTIN: ("AUSTIN_METRO_BBOX", "AUSTIN_DIVISION_BBOXES", "AUSTIN_DIVISIONS", "AUSTIN_SUBMARKETS"),
    CityId.CINCINNATI: ("CINCINNATI_METRO_BBOX", "CINCINNATI_DIVISION_BBOXES", "CINCINNATI_DIVISIONS", "CINCINNATI_SUBMARKETS"),
    CityId.BOSTON: ("BOSTON_METRO_BBOX", "BOSTON_DIVISION_BBOXES", "BOSTON_DIVISIONS", "BOSTON_SUBMARKETS"),
    CityId.BALTIMORE: ("BALTIMORE_METRO_BBOX", "BALTIMORE_DIVISION_BBOXES", "BALTIMORE_DIVISIONS", "BALTIMORE_SUBMARKETS"),
    CityId.MONTGOMERY: ("MONTGOMERY_METRO_BBOX", "MONTGOMERY_DIVISION_BBOXES", "MONTGOMERY_DIVISIONS", "MONTGOMERY_SUBMARKETS"),
    CityId.BATON_ROUGE: ("BATON_ROUGE_METRO_BBOX", "BATON_ROUGE_DIVISION_BBOXES", "BATON_ROUGE_DIVISIONS", "BATON_ROUGE_SUBMARKETS"),
    CityId.DENVER: ("DENVER_METRO_BBOX", "DENVER_DIVISION_BBOXES", "DENVER_DIVISIONS", "DENVER_SUBMARKETS"),
    CityId.PHILADELPHIA: ("PHILADELPHIA_METRO_BBOX", "PHL_DIVISION_BBOXES", "PHL_DIVISIONS", "PHL_SUBMARKETS"),
    CityId.WASHINGTON_DC: ("DC_METRO_BBOX", "DC_DIVISION_BBOXES", "DC_DIVISIONS", "DC_SUBMARKETS"),
    CityId.MINNEAPOLIS: ("MINNEAPOLIS_METRO_BBOX", "MINNEAPOLIS_DIVISION_BBOXES", "MINNEAPOLIS_DIVISIONS", "MINNEAPOLIS_SUBMARKETS"),
}

EXPORT_ATTR_MAP = {
    0: "metro_bbox",
    1: "division_bboxes",
    2: "divisions",
    3: "submarkets",
}


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
                assert spec.watermark_col or spec.extra.get("ingestion_mode") == "snapshot", label
                assert spec.id_keys and all(isinstance(k, str) and k for k in spec.id_keys), label
                assert spec.interval_seconds > 0, label
                assert spec.producer_key == feed.value, (
                    f"{label}: producer_key {spec.producer_key!r} != feed {feed.value!r}"
                )
                if spec.platform == "arcgis":
                    assert "oid_field" in spec.extra, f"{label}: arcgis spec missing oid_field"

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
        for cid, export_names in CITY_EXPORT_NAMES.items():
            reg = REGISTRY[cid]
            for idx, export_name in enumerate(export_names):
                exported = getattr(cities_pkg, export_name, None)
                assert exported is not None, f"src.spatial.cities does not export {export_name}"
                attr = EXPORT_ATTR_MAP[idx]
                assert exported is getattr(reg, attr), (
                    f"{export_name} is not the object registered as {cid.value}.{attr}"
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

    The map is three layers: the dashboard's selector option, its CITY_CONFIGS
    entry (divisions/presets), and the synced workers static copy. A registry
    entry missing from any layer fails the gate in the same run.
    """

    DASHBOARD = REPO_ROOT / "apps" / "api" / "src" / "serving" / "dashboard.py"
    WORKER_STATIC = REPO_ROOT / "apps" / "dashboard" / "public" / "index.html"

    def _dashboard(self) -> str:
        assert self.DASHBOARD.exists(), f"{self.DASHBOARD} missing — the map was deleted?"
        return self.DASHBOARD.read_text()

    def test_every_registered_city_has_a_selector_option(self):
        src = self._dashboard()
        missing = [
            cid.value
            for cid in REGISTRY
            if f'<option value="{cid.value}"' not in src
        ]
        assert not missing, (
            f"registered but not on the map selector: {missing}. "
            f"Wire dashboard options in the same spine hold as the REGISTRY entry."
        )

    def test_every_registered_city_has_a_config_entry(self):
        import re

        src = self._dashboard()
        missing = [
            cid.value
            for cid in REGISTRY
            if not re.search(rf"(?m)^\s+{re.escape(cid.value)}: \{{", src)
        ]
        assert not missing, (
            f"registered but missing from CITY_CONFIGS: {missing}. "
            f"A city without center/divisions/presets cannot render."
        )

    def test_worker_static_copy_carries_every_city(self):
        if not (REPO_ROOT / "apps" / "dashboard").exists():
            pytest.skip("apps/dashboard deployment surface removed from the tree — no static copy to keep in sync")
        assert self.WORKER_STATIC.exists(), (
            f"{self.WORKER_STATIC} missing while the rest of apps/dashboard exists — "
            f"regenerate it from get_dashboard_html()"
        )
        static = self.WORKER_STATIC.read_text()
        stale = [cid.value for cid in REGISTRY if f'"{cid.value}"' not in static]
        assert not stale, (
            f"apps/dashboard/public/index.html is a stale static copy — missing {stale}. "
            f"Re-sync it from get_dashboard_html() before closing the wave."
        )
