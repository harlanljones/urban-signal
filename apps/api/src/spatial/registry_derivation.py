"""Registry derivation aggregator (US-177 / US-428).

The single construction path for ``REGISTRY`` / ``ALIASES``. Each city's
registration is loaded once from its declarative YAML definition beside the
leaf module (``cities/data/<city_id>.yaml``), then geometry is re-bound to the
leaf ``REGISTRATION``'s exact objects so the interlock identity invariants hold
by construction.

There is no hand-written registry: the corpus satisfies the runtime. Building
fails loudly (rather than falling back) when the corpus does not cover every
``CityId`` or does not correspond to a leaf module — a registration missing its
definition is a torn write, not a degraded state. Onboarding a city means adding
``cities/<city_id>.py`` and ``cities/data/<city_id>.yaml`` (plus any endpoints in
settings); nothing here changes.

This module is READ-ONLY toward the leaf modules and the corpus; it never
mutates their ``REGISTRATION`` or their YAML files. NYC resolves to
``src.spatial.cities.nyc``, whose geometry lives in ``src.spatial.submarkets``.
"""

import importlib
from collections.abc import Iterable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from src.spatial import city_data


def build_registry_from_data(
    definitions, endpoint_resolver=lambda name: name, *, allow_unknown_city_ids=False
):
    """Build registrations directly from validated declarative definitions."""
    from src.spatial import city_registry

    return {
        registration.city_id: registration
        for registration in (
            city_data.build_registration(
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
    definitions: Iterable[Mapping[str, Any]], *, allow_unknown_city_ids=False
) -> dict[str, object]:
    from src.spatial import city_registry

    return city_data.aliases_from_definitions(
        definitions, city_registry.CityId, allow_unknown_city_ids=allow_unknown_city_ids
    )


def _leaf_registration(city_id):
    """Return the ``REGISTRATION`` object for a ``CityId`` leaf module.

    NYC resolves to ``src.spatial.cities.nyc``; every other city resolves to
    ``src.spatial.cities.<city_id.value>`` (the module file matches the enum
    value by construction).
    """
    module = importlib.import_module(f"src.spatial.cities.{city_id.value}")
    return module.REGISTRATION


def load_definitions(*, allow_unknown_city_ids=False) -> list[dict[str, Any]]:
    """Load the corpus definitions, raising if the directory is missing."""
    from src.config import settings

    directory = Path(settings.city_data_dir)
    if not directory.is_dir():
        raise ValueError(
            f"city-data directory {directory} does not exist — run "
            f"scripts/export_city_data.py to regenerate the corpus"
        )
    definitions = city_data.load_definitions(directory, allow_unknown_city_ids=allow_unknown_city_ids)
    if not definitions:
        raise ValueError(
            f"no city definitions found in {directory} — the corpus was deleted?"
        )
    return definitions


def build_runtime_exports(
    endpoint_resolver=lambda name: name, *, allow_unknown_city_ids=False
):
    """Build ``(REGISTRY, ALIASES)`` — the sole registry construction path.

    Non-geometry fields come from the corpus definitions; geometry is re-bound
    to each leaf ``REGISTRATION`` so object identity matches the leaves.
    """
    from src.config import settings
    from src.spatial import city_registry

    definitions = load_definitions(allow_unknown_city_ids=allow_unknown_city_ids)
    registry = build_registry_from_data(
        definitions, endpoint_resolver, allow_unknown_city_ids=allow_unknown_city_ids
    )
    missing = [
        cid.value for cid in city_registry.CityId if cid not in registry
    ]
    if missing:
        raise ValueError(
            f"city definitions missing from the corpus "
            f"({Path(settings.city_data_dir).resolve()}): {missing}. "
            f"Every CityId needs a data/<city_id>.yaml beside its leaf module."
        )
    for cid in city_registry.CityId:
        source = _leaf_registration(cid)
        registry[cid] = replace(
            registry[cid],
            metro_bbox=source.metro_bbox,
            division_bboxes=source.division_bboxes,
            submarkets=source.submarkets,
            divisions=source.divisions,
        )
    aliases = build_aliases_from_data(
        definitions, allow_unknown_city_ids=allow_unknown_city_ids
    )
    return registry, aliases


def derived_supported_cities() -> list[object]:
    """Yield the supported-city list (derived from ``CityId``)."""
    from src.spatial import city_registry

    return list(city_registry.CityId)
