"""Export registry-derived site facts for the product site.

The city registry (``apps/api/src/spatial/city_registry.py::REGISTRY``) is the
authoritative source for metro coverage. This script projects it into the
static artifacts the product site serves, so hand-edited coverage facts can
never drift from the registry:

    apps/product/public/facts.json         (schema_version 2)
    apps/product/public/cities/<id>.json   (per-metro detail)

Usage:
    python scripts/export_site_facts.py            # write artifacts
    python scripts/export_site_facts.py --check    # exit 1 on drift, write nothing

Optional runtime freshness overlay (``--freshness <path>``, default:
``apps/product/freshness.json`` when that file exists). Schema::

    {"<city_id>": {"<feed_key>": {"last_synced_at": "<iso>", "age_hours": <number>}}}

When the overlay is present, facts.json gains a top-level ``freshness`` key
mirroring it verbatim; when absent, no key is emitted. ``--check`` applies the
same rule, so drift detection covers freshness whenever the file exists.

Run with the API virtualenv interpreter (``apps/api/.venv/bin/python``) so the
registry's settings imports resolve.

Product copy (``product``, ``limitations``, ``pipeline``, horizons) is owned by
``PRODUCT.md`` and mirrored here verbatim; everything metro-specific is derived.
Submarket dashboard-demo baselines (``base_lims``, ``capex``, ``permit_vel``,
``shift_ratio``, ``sla``, ``zoom``, ``pitch``) are deliberately EXCLUDED: they
are illustrative interface seeds, not site facts, and publishing them unlabeled
would violate the claims discipline in ``PRODUCT.md``.
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
API_ROOT = REPO / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from src.spatial.city_registry import REGISTRY, CityId, FeedType  # noqa: E402

SCHEMA_VERSION = 2
FEED_ORDER = [FeedType.PERMITS, FeedType.COMPLAINTS_311, FeedType.SLA, FeedType.DEEDS]

PRODUCT = {
    "name": "Urban Signal",
    "summary": "Open-source spatial intelligence that turns municipal permits, 311 requests, licenses, deeds, and related public records into explainable H3-based signals.",
    "positioning": "Leading municipal telemetry is treated as evidence of change before conventional transaction-based indicators.",
    "repository": "https://github.com/harlanljones/urban-signal",
    "dashboard": "/dashboard",
}

LIMITATIONS = [
    "Feed coverage varies by metro and must not be treated as uniform.",
    "The hero cell and the 68/100 score composition are illustrative interface examples, not live forecast-performance claims.",
    "No customer, adoption, or independently validated model-performance claims are published.",
]

PIPELINE = [
    {"id": "ingest", "label": "Ingest", "source_path": "apps/api/src/producers"},
    {"id": "normalize", "label": "Normalize", "source_path": "apps/api/src/schemas/models.py"},
    {"id": "spatial", "label": "Spatialize", "source_path": "apps/api/src/spatial/h3_indexer.py"},
    {"id": "features", "label": "Features", "source_path": "apps/api/src/features/lims_calculator.py"},
    {"id": "serve", "label": "Serve", "source_path": "apps/api/src/export/snapshot_builder.py"},
]

MODEL_HORIZONS_MONTHS = [6, 12, 18]


def evidence_path_for(city_id: CityId) -> str:
    """Per-metro evidence path: the city module when one exists, else the registry."""
    relative = f"apps/api/src/spatial/cities/{city_id.value}.py"
    if (REPO / relative).exists():
        return relative
    return "apps/api/src/spatial/city_registry.py"


def divisions_string(city_id: CityId, division_count: int) -> str:
    """Legacy facts.json prose: NYC counts boroughs, everyone else divisions."""
    noun = "boroughs" if city_id == CityId.NYC else "divisions"
    if division_count == 1:
        return f"1 {noun[:-1]}"
    return f"{division_count} {noun}"


def feed_entry(reg, feed: FeedType):
    """Feed projection, or None when the metro does not publish that feed."""
    spec = reg.datasets.get(feed)
    if spec is None:
        return None
    return {
        "platform": spec.platform,
        "watermark_col": spec.watermark_col,
        "interval_seconds": spec.interval_seconds,
        "topic": spec.topic,
    }


def build_facts(freshness: dict | None = None) -> dict:
    metros = []
    for city_id, reg in REGISTRY.items():
        metros.append(
            {
                "id": city_id.value,
                "name": reg.name,
                "state": reg.state,
                "divisions": divisions_string(city_id, len(reg.divisions)),
                "division_count": len(reg.divisions),
                "submarket_count": len(reg.submarkets),
                "feeds": [feed in reg.datasets for feed in FEED_ORDER],
                "platforms": [feed_entry(reg, feed) for feed in FEED_ORDER],
                "center": dict(reg.center),
                "evidence_path": evidence_path_for(city_id),
            }
        )
    facts = {
        "schema_version": SCHEMA_VERSION,
        "product": PRODUCT,
        "limitations": LIMITATIONS,
        "feed_labels": [feed.value for feed in FEED_ORDER],
        "metros": metros,
        "pipeline": PIPELINE,
        "model_horizons_months": MODEL_HORIZONS_MONTHS,
    }
    if freshness is not None:
        facts["freshness"] = freshness
    return facts


FRESHNESS_DEFAULT = REPO / "apps" / "product" / "freshness.json"


def load_freshness(path):
    """Read the optional freshness overlay; None when no file applies."""
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"FRESHNESS_INVALID ({path}): {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"FRESHNESS_INVALID ({path}): expected an object keyed by city id")
    for city_id, feeds in payload.items():
        if not isinstance(feeds, dict):
            raise SystemExit(f"FRESHNESS_INVALID ({path}): {city_id} must map feed keys to entries")
        for feed_key, entry in feeds.items():
            valid = (
                isinstance(entry, dict)
                and isinstance(entry.get("last_synced_at"), str)
                and isinstance(entry.get("age_hours"), (int, float))
                and not isinstance(entry.get("age_hours"), bool)
            )
            if not valid:
                raise SystemExit(
                    f"FRESHNESS_INVALID ({path}): {city_id}/{feed_key} needs "
                    "last_synced_at (string) and age_hours (number)"
                )
    return payload


def freshness_arg(value: str) -> Path:
    return Path(value)


def resolve_freshness_path(explicit) -> Path | None:
    """Explicit --freshness path wins; else the default file when it exists."""
    if explicit is not None:
        return freshness_arg(explicit)
    return FRESHNESS_DEFAULT if FRESHNESS_DEFAULT.exists() else None


def build_city_detail(city_id: CityId, reg) -> dict:
    divisions = {
        key: {
            "name": meta.name,
            "center": {"lat": meta.center_lat, "lng": meta.center_lng},
            "bbox": dict(meta.bbox),
            "submarkets": list(meta.submarkets),
        }
        for key, meta in reg.divisions.items()
    }
    submarkets = {
        key: {
            "name": meta.name,
            "division": meta.borough,
            "center": {"lat": meta.lat, "lng": meta.lng},
            "description": meta.description,
        }
        for key, meta in reg.submarkets.items()
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "id": city_id.value,
        "name": reg.name,
        "state": reg.state,
        "center": dict(reg.center),
        "metro_bbox": dict(reg.metro_bbox),
        "divisions": divisions,
        "submarkets": submarkets,
        "feeds": {feed.value: feed_entry(reg, feed) for feed in FEED_ORDER},
        "evidence_path": evidence_path_for(city_id),
        "generated_from": "apps/api/src/spatial/city_registry.py REGISTRY",
    }


def render(payload: dict) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify artifacts match the registry; write nothing")
    parser.add_argument(
        "--freshness",
        default=None,
        metavar="PATH",
        help="optional freshness overlay JSON (default: apps/product/freshness.json when present)",
    )
    args = parser.parse_args()

    product_dir = REPO / "apps" / "product" / "public"
    cities_dir = product_dir / "cities"
    facts_path = product_dir / "facts.json"

    freshness_path = resolve_freshness_path(args.freshness)
    freshness = load_freshness(freshness_path)
    facts = render(build_facts(freshness))
    details = {city_id.value: render(build_city_detail(city_id, reg)) for city_id, reg in REGISTRY.items()}

    if args.check:
        drift = []
        if not facts_path.exists() or facts_path.read_text(encoding="utf-8") != facts:
            drift.append(str(facts_path.relative_to(REPO)))
        existing = {p.stem for p in cities_dir.glob("*.json")} if cities_dir.exists() else set()
        expected = set(details)
        for stale in sorted(existing - expected):
            drift.append(f"stale {cities_dir.relative_to(REPO)}/{stale}.json")
        for city_id in sorted(expected):
            path = cities_dir / f"{city_id}.json"
            if not path.exists() or path.read_text(encoding="utf-8") != details[city_id]:
                drift.append(str(path.relative_to(REPO)))
        if drift:
            print("FACTS_DRIFT — artifacts differ from REGISTRY; run: bun run facts:export")
            for item in drift:
                print(f"  {item}")
            return 1
        print(f"FACTS_FRESH ({len(details)} metros match REGISTRY)")
        return 0

    cities_dir.mkdir(parents=True, exist_ok=True)
    facts_path.write_text(facts, encoding="utf-8")
    for stale in cities_dir.glob("*.json"):
        if stale.stem not in details:
            stale.unlink()
    for city_id, payload in details.items():
        (cities_dir / f"{city_id}.json").write_text(payload, encoding="utf-8")
    print(f"SITE_FACTS_OK ({len(details)} metros: facts.json + cities/*.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
