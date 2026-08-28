"""Registry derivation aggregator (US-177).

Builds the same structures as the hand-written ``REGISTRY`` / ``ALIASES`` in
``city_registry`` by *merging*:

* geometry (``metro_bbox``, ``division_bboxes``, ``submarkets``,
  ``divisions``) from each leaf module's ``REGISTRATION`` object, and
* the non-geometry fields (``name``, ``state``, ``center``,
  ``job_suffix``, ``datasets``) plus the alias table from the existing
  hand-written registry (US-177 does NOT move those).

Object identity is preserved by construction: each leaf ``REGISTRATION``
references the exact same constant objects the hand-written registry imports
(e.g. ``cities.chicago.CHICAGO_METRO_BBOX`` is ``REGISTRY[CityId.CHICAGO].
metro_bbox``), so geometry fields compare equal with ``is``. NYC is handled
through ``cities.nyc.REGISTRATION``, which bridges the borough objects from
``submarkets``.

This module is READ-ONLY toward the 48 leaf modules and ``cities/nyc.py``;
it never mutates their ``REGISTRATION``. The hand-written registry remains
the authoritative export unless ``USE_DERIVED_REGISTRY`` is enabled by the
caller (``city_registry`` switches its own ``REGISTRY``/``ALIASES`` exports
based on that flag).
"""

import importlib
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path
from typing import Any

from src.spatial.registration import SpatialRegistration


def build_registry_from_data(
    definitions, endpoint_resolver=lambda name: name, *, allow_unknown_city_ids=False
):
    """Build registrations directly from validated declarative definitions.

    This factory is deliberately separate from the legacy fallback below so a
    caller can validate and promote a data migration in one interlock hold.
    """
    from src.spatial import city_registry
    from src.spatial.city_data import build_registration

    return {
        registration.city_id: registration
        for registration in (
            build_registration(
                definition,
                city_id_type=city_registry.CityId,
                feed_type=city_registry.FeedType,
                endpoint_resolver=endpoint_resolver,
                allow_unknown_city_ids=allow_unknown_city_ids,
            )
            for definition in definitions
        )
    }


def build_aliases_from_data(
    definitions: Iterable[dict[str, Any]], *, allow_unknown_city_ids=False
) -> dict[str, object]:
    from src.spatial import city_registry
    from src.spatial.city_data import validate_definition

    aliases: dict[str, object] = {}
    for raw in definitions:
        definition = validate_definition(raw)
        try:
            city_id = city_registry.CityId(definition["city_id"])
        except (TypeError, ValueError) as exc:
            if not allow_unknown_city_ids:
                raise ValueError(f"unknown city_id {definition['city_id']!r}") from exc
            city_id = definition["city_id"]
        for alias in [definition["city_id"], *definition.get("aliases", [])]:
            key = str(alias).strip().lower()
            if not key:
                raise ValueError(f"{getattr(city_id, 'value', city_id)} contains an empty alias")
            previous = aliases.setdefault(key, city_id)
            if previous != city_id:
                raise ValueError(
                    f"alias {key!r} maps to both {getattr(previous, 'value', previous)!r} "
                    f"and {getattr(city_id, 'value', city_id)!r}"
                )
    return aliases


def build_runtime_exports(endpoint_resolver=lambda name: name, *, allow_unknown_city_ids=False):
    from src.config import settings
    from src.spatial import city_registry
    from src.spatial.city_data import load_definitions

    try:
        definitions = load_definitions(
            Path(settings.city_data_dir), allow_unknown_city_ids=allow_unknown_city_ids
        )
        if not definitions:
            return None
        registry = build_registry_from_data(
            definitions,
            endpoint_resolver,
            allow_unknown_city_ids=allow_unknown_city_ids,
        )
        legacy_ids = set(city_registry._HANDWRITTEN_REGISTRY)
        if not legacy_ids.issubset(registry):
            return None
        canonical = build_registry_from_registrations()
        for city_id in legacy_ids:
            source = canonical[city_id]
            runtime = registry[city_id]
            registry[city_id] = replace(
                runtime,
                metro_bbox=source.metro_bbox,
                division_bboxes=source.division_bboxes,
                submarkets=source.submarkets,
                divisions=source.divisions,
            )
        aliases = build_aliases_from_registrations()
        aliases.update(
            build_aliases_from_data(definitions, allow_unknown_city_ids=allow_unknown_city_ids)
        )
        return registry, aliases
    except Exception:
        return None


def _leaf_registration(city_id):
    """Return the ``REGISTRATION`` object for a ``CityId`` leaf module.

    NYC resolves to ``src.spatial.cities.nyc``; every other city resolves to
    ``src.spatial.cities.<city_id.value>`` (the module file matches the enum
    value by construction).
    """
    module = importlib.import_module(f"src.spatial.cities.{city_id.value}")
    return module.REGISTRATION


def build_registry_from_registrations():
    """Assemble a ``Dict[CityId, CityRegistration]`` from leaf registrations.

    Geometry is taken verbatim from each leaf ``REGISTRATION``; the
    non-geometry fields are copied from the hand-written registry so that the
    shape and content match exactly. The hand-written registry is read from
    ``city_registry._HANDWRITTEN_REGISTRY`` so the result is stable regardless
    of whether the derived registry is currently the active export.
    """
    from src.spatial import city_registry

    handwritten = city_registry._HANDWRITTEN_REGISTRY
    out: dict[object, object] = {}
    for city_id, hand in handwritten.items():
        reg: SpatialRegistration = _leaf_registration(city_id)
        out[city_id] = city_registry.CityRegistration(
            city_id=city_id,
            name=hand.name,
            state=hand.state,
            center=hand.center,
            metro_bbox=reg.metro_bbox,
            division_bboxes=reg.division_bboxes,
            submarkets=reg.submarkets,
            divisions=reg.divisions,
            job_suffix=hand.job_suffix,
            datasets=hand.datasets,
        )
    return out


def build_aliases_from_registrations():
    """Return the alias table, derived/validated against the registrations.

    Aliases live in the hand-written registry (US-177 does not move them);
    this aggregator re-exposes that table while asserting every alias still
    resolves to a city that has a registration, so the derived output is
    guaranteed to equal the hand-written ``ALIASES``.
    """
    from src.spatial import city_registry

    handwritten = city_registry._HANDWRITTEN_ALIASES
    registrations = city_registry._HANDWRITTEN_REGISTRY
    derived: dict[str, object] = {}
    for alias, city_id in handwritten.items():
        assert city_id in registrations, f"alias {alias!r} -> {city_id!r} has no registration"
        derived[alias] = city_id
    return derived


def derived_supported_cities() -> list[object]:
    """Yield the same supported-city list as today (derived from ``CityId``)."""
    from src.spatial import city_registry

    return list(city_registry.CityId)
