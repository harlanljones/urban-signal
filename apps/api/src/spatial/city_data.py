"""Declarative city-registration data loader.

The public registry objects stay in :mod:`city_registry` while definitions move
into YAML. During migration, a complete definition can be introduced and
validated without changing any consumer of the existing runtime objects.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import fields
from pathlib import Path
from typing import Any

import yaml

from src.spatial.submarkets import BoroughMeta, SubmarketMeta

DATA_DIR = Path(__file__).with_name("cities") / "data"
_REQUIRED_CITY_FIELDS = {"city_id", "name", "state", "center", "metro_bbox", "datasets"}
_REQUIRED_BBOX_FIELDS = {"min_lat", "max_lat", "min_lng", "max_lng"}


class _FeedKey(str):
    """String-compatible key for a declarative feed absent from ``FeedType``."""

    @property
    def value(self) -> str:
        return str(self)


def _as_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return dict(value)


def _validate_bbox(value: Any, label: str) -> dict[str, float]:
    bbox = _as_mapping(value, label)
    missing = _REQUIRED_BBOX_FIELDS - bbox.keys()
    if missing:
        raise ValueError(f"{label} missing fields: {sorted(missing)}")
    out = {key: float(bbox[key]) for key in _REQUIRED_BBOX_FIELDS}
    if out["min_lat"] >= out["max_lat"] or out["min_lng"] >= out["max_lng"]:
        raise ValueError(f"{label} bounds must increase")
    return out


def _dataclass_from_data(cls: type[Any], value: Any, label: str) -> Any:
    data = _as_mapping(value, label)
    allowed = {item.name for item in fields(cls)}
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"{label} has unknown fields: {sorted(unknown)}")
    return cls(**data)


def validate_definition(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one YAML city definition."""
    definition = _as_mapping(raw, "city definition")
    missing = _REQUIRED_CITY_FIELDS - definition.keys()
    if missing:
        raise ValueError(f"city definition missing fields: {sorted(missing)}")
    city_id = str(definition["city_id"])
    center = _as_mapping(definition["center"], f"{city_id}.center")
    if set(center) != {"lat", "lng"}:
        raise ValueError(f"{city_id}.center must contain only lat and lng")
    datasets = _as_mapping(definition["datasets"], f"{city_id}.datasets")
    # Feedless registrations are legitimate (partial-registration rule,
    # docs/agents/parallel-streams.md): a city may register geometry before
    # any feed is wired, and get_dataset() raises for the rest.
    normalized = dict(definition)
    normalized["city_id"] = city_id
    normalized["center"] = {"lat": float(center["lat"]), "lng": float(center["lng"])}
    normalized["metro_bbox"] = _validate_bbox(definition["metro_bbox"], f"{city_id}.metro_bbox")
    normalized["division_bboxes"] = {
        str(name): _validate_bbox(bbox, f"{city_id}.division_bboxes.{name}")
        for name, bbox in _as_mapping(
            definition.get("division_bboxes", {}), f"{city_id}.division_bboxes"
        ).items()
    }
    normalized["datasets"] = datasets
    normalized.setdefault("aliases", [])
    normalized.setdefault("job_suffix", "")
    normalized.setdefault("submarkets", {})
    normalized.setdefault("divisions", {})
    return normalized


def load_definitions(
    directory: Path = DATA_DIR, *, allow_unknown_city_ids: bool = False
) -> list[dict[str, Any]]:
    """Load and validate every non-example YAML definition in ``directory``."""
    definitions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        definition = validate_definition(yaml.safe_load(path.read_text(encoding="utf-8")))
        if not allow_unknown_city_ids:
            from src.spatial.city_registry import CityId

            try:
                CityId(definition["city_id"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"unknown city_id {definition['city_id']!r}") from exc
        if definition["city_id"] in seen:
            raise ValueError(f"duplicate city_id {definition['city_id']!r}")
        seen.add(definition["city_id"])
        definitions.append(definition)
    return definitions


def _build_dataset(raw: Mapping[str, Any], resolve: Callable[[str], Any]) -> Any:
    from src.spatial.city_registry import DatasetSpec

    data = dict(raw)
    endpoint_setting = data.pop("endpoint_setting", None)
    if endpoint_setting is not None:
        setting_name = str(endpoint_setting)
        resolved = resolve(setting_name)
        if resolved == setting_name:
            from src.config import settings

            try:
                resolved = getattr(settings, setting_name)
            except AttributeError as exc:
                raise ValueError(f"unknown endpoint setting {setting_name!r}") from exc
        data["endpoint"] = resolved
    if "endpoint" not in data:
        raise ValueError("dataset is missing endpoint")
    allowed = {item.name for item in fields(DatasetSpec)}
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"dataset has unknown fields: {sorted(unknown)}")
    return DatasetSpec(**data)


def _feed_key(value: Any, feed_type: Any) -> Any:
    """Use the public enum where available and preserve newer YAML feeds."""
    try:
        return feed_type(value)
    except (TypeError, ValueError):
        return _FeedKey(str(value))


def build_registration(
    definition: Mapping[str, Any],
    *,
    city_id_type: Any,
    feed_type: Any,
    endpoint_resolver: Callable[[str], Any] = lambda name: name,
    allow_unknown_city_ids: bool = False,
) -> Any:
    """Build a ``CityRegistration`` from one validated definition."""
    from src.spatial.city_registry import CityRegistration

    data = validate_definition(definition)
    try:
        city_id = city_id_type(data["city_id"])
    except (TypeError, ValueError) as exc:
        if not allow_unknown_city_ids:
            raise ValueError(f"unknown city_id {data['city_id']!r}") from exc
        city_id = data["city_id"]
    city_label = getattr(city_id, "value", city_id)
    submarkets = {
        name: _dataclass_from_data(SubmarketMeta, value, f"{city_label}.submarkets.{name}")
        for name, value in _as_mapping(data["submarkets"], f"{city_label}.submarkets").items()
    }
    divisions = {
        name: _dataclass_from_data(BoroughMeta, value, f"{city_label}.divisions.{name}")
        for name, value in _as_mapping(data["divisions"], f"{city_label}.divisions").items()
    }
    datasets = {
        _feed_key(feed, feed_type): _build_dataset(value, endpoint_resolver)
        for feed, value in data["datasets"].items()
    }
    return CityRegistration(
        city_id=city_id,
        name=str(data["name"]),
        state=str(data["state"]),
        center=data["center"],
        metro_bbox=data["metro_bbox"],
        division_bboxes=data["division_bboxes"],
        submarkets=submarkets,
        divisions=divisions,
        datasets=datasets,
        job_suffix=str(data["job_suffix"]),
    )


def aliases_from_definitions(
    definitions: Iterable[Mapping[str, Any]],
    city_id_type: Any,
    *,
    allow_unknown_city_ids: bool = False,
) -> dict[str, Any]:
    """Create an alias map and reject aliases that collide across cities."""
    aliases: dict[str, Any] = {}
    for raw in definitions:
        definition = validate_definition(raw)
        try:
            city_id = city_id_type(definition["city_id"])
        except (TypeError, ValueError) as exc:
            if not allow_unknown_city_ids:
                raise ValueError(f"unknown city_id {definition['city_id']!r}") from exc
            city_id = definition["city_id"]
        city_label = getattr(city_id, "value", city_id)
        for alias in [definition["city_id"], *definition.get("aliases", [])]:
            key = str(alias).strip().lower()
            if not key:
                raise ValueError(f"{getattr(city_id, 'value', city_id)} contains an empty alias")
            previous = aliases.setdefault(key, city_id)
            if previous != city_id:
                raise ValueError(
                    f"alias {key!r} maps to both {getattr(previous, 'value', previous)!r} "
                    f"and {city_label!r}"
                )
    return aliases
