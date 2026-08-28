"""Export the complete declarative city corpus from the legacy registry.

Run from the repository root with the API virtualenv, for example::

    apps/api/.venv/bin/python scripts/export_city_data.py
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
DATA_DIR = API_ROOT / "src" / "spatial" / "cities" / "data"


def _plain(value: Any) -> Any:
    """Convert runtime registry values into YAML-safe primitives."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: _plain(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, dict):
        return {_plain(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _definition(city_id: Any, registration: Any, aliases: dict[str, Any]) -> dict[str, Any]:
    datasets = {
        feed.value: _plain(dataset)
        for feed, dataset in registration.datasets.items()
    }
    return {
        "city_id": city_id.value,
        "name": registration.name,
        "state": registration.state,
        "center": _plain(registration.center),
        "metro_bbox": _plain(registration.metro_bbox),
        "division_bboxes": _plain(registration.division_bboxes),
        "submarkets": _plain(registration.submarkets),
        "divisions": _plain(registration.divisions),
        "datasets": datasets,
        "aliases": [alias for alias, target in aliases.items() if target == city_id and alias != city_id.value],
        "job_suffix": registration.job_suffix,
    }


def _export() -> tuple[int, list[Path]]:
    sys.path.insert(0, str(API_ROOT))
    from src.spatial import city_registry

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    expected = set()
    paths = []
    for city_id, registration in city_registry._HANDWRITTEN_REGISTRY.items():
        definition = _definition(city_id, registration, city_registry._HANDWRITTEN_ALIASES)
        path = DATA_DIR / f"{city_id.value}.yaml"
        path.write_text(
            yaml.safe_dump(definition, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )
        expected.add(path.name)
        paths.append(path)

    # Remove only generated city files that no longer correspond to the
    # current registry; README.md and underscore-prefixed examples remain.
    for path in DATA_DIR.glob("*.yaml"):
        if not path.name.startswith("_") and path.name not in expected:
            path.unlink()
    return len(expected), paths


def _validate(expected_count: int) -> None:
    sys.path.insert(0, str(API_ROOT))
    from src.spatial import city_registry
    from src.spatial.city_data import load_definitions
    from src.spatial.registry_derivation import build_registry_from_data

    definitions = load_definitions(DATA_DIR)
    if len(definitions) != expected_count:
        raise RuntimeError(f"expected {expected_count} definitions, loaded {len(definitions)}")
    registry = build_registry_from_data(definitions)
    legacy = city_registry._HANDWRITTEN_REGISTRY
    if set(registry) != set(legacy):
        raise RuntimeError("declarative city IDs do not match the legacy registry")
    if registry != legacy:
        raise RuntimeError("declarative definitions do not round-trip to the legacy registry")

    aliases = {}
    for definition in definitions:
        city_id = city_registry.CityId(definition["city_id"])
        for alias in [definition["city_id"], *definition.get("aliases", [])]:
            aliases[str(alias).strip().lower()] = city_id
    if aliases != city_registry._HANDWRITTEN_ALIASES:
        raise RuntimeError("declarative aliases do not match the legacy alias table")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-validate", action="store_true", help="write files without round-trip validation")
    args = parser.parse_args()
    count, _ = _export()
    if not args.no_validate:
        _validate(count)
    print(f"exported and validated {count} city definitions in {DATA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
