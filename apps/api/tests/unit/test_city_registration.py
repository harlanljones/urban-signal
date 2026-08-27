"""US-176: every Metro leaf module (incl. NYC) exposes a canonical REGISTRATION.

Each leaf bundles its existing canonical constants into one ``REGISTRATION``
object of type ``SpatialRegistration``. NYC's module additionally must preserve
the interlock identity invariant: its ``metro_bbox`` is the very same object the
registry imports from ``src.spatial.submarkets``.
"""

import importlib
import pkgutil

import pytest

from src.spatial import cities as cities_pkg
from src.spatial.city_registry import REGISTRY, CityId
from src.spatial.registration import SpatialRegistration
from src.spatial.submarkets import NYC_METRO_BBOX

GEOMETRY_FIELDS = ("metro_bbox", "division_bboxes", "submarkets", "divisions")


def _leaf_module_names():
    names = []
    for mod in pkgutil.iter_modules(cities_pkg.__path__):
        if mod.name == "__init__":
            continue
        names.append(mod.name)
    return names


_LEAF_MODULES = _leaf_module_names()


@pytest.mark.parametrize("name", _LEAF_MODULES)
def test_leaf_exposes_registration(name):
    module = importlib.import_module(f"src.spatial.cities.{name}")
    assert hasattr(module, "REGISTRATION"), f"{name} is missing REGISTRATION"
    reg = module.REGISTRATION
    assert isinstance(reg, SpatialRegistration), f"{name}.REGISTRATION wrong type"
    for field in GEOMETRY_FIELDS:
        assert getattr(reg, field) is not None, f"{name}.REGISTRATION.{field} unset"
    assert callable(reg.contains), f"{name}.REGISTRATION.contains not callable"


def test_nyc_registration_metro_bbox_is_submarkets_object():
    from src.spatial.cities import nyc

    assert nyc.REGISTRATION.metro_bbox is NYC_METRO_BBOX


def test_nyc_registration_metro_bbox_matches_registry():
    from src.spatial.cities import nyc

    assert nyc.REGISTRATION.metro_bbox is REGISTRY[CityId.NYC].metro_bbox
