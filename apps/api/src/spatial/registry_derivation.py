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
from typing import Dict, List

from src.spatial.registration import SpatialRegistration


def build_registry_from_data(definitions, endpoint_resolver=lambda name: name):
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
            )
            for definition in definitions
        )
    }


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
    out: Dict[object, object] = {}
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
    derived: Dict[str, object] = {}
    for alias, city_id in handwritten.items():
        assert city_id in registrations, (
            f"alias {alias!r} -> {city_id!r} has no registration"
        )
        derived[alias] = city_id
    return derived


def derived_supported_cities() -> List[object]:
    """Yield the same supported-city list as today (derived from ``CityId``)."""
    from src.spatial import city_registry

    return list(city_registry.CityId)
