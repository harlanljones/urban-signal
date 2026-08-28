"""US-175: every Metro leaf module exposes the canonical constant scheme.

Each leaf module in ``src.spatial.cities`` must expose the four canonical
constants named after its module basename:

    <BASENAME>_METRO_BBOX
    <BASENAME>_DIVISION_BBOXES
    <BASENAME>_SUBMARKETS
    <BASENAME>_DIVISIONS

This lets the registry aggregator (US-177) scan one predictable name per
module instead of guessing at abbreviations (ATX_, PHL_, DC_, ...).
"""

import importlib
import pkgutil

import pytest

from src.spatial import cities as cities_pkg

CANONICAL_SUFFIXES = ("METRO_BBOX", "DIVISION_BBOXES", "SUBMARKETS", "DIVISIONS")


def _leaf_module_names():
    names = []
    for mod in pkgutil.iter_modules(cities_pkg.__path__):
        if mod.name == "__init__":
            continue
        names.append(mod.name)
    return names


_LEAF_MODULES = _leaf_module_names()


@pytest.mark.parametrize("name", _LEAF_MODULES)
def test_leaf_has_canonical_constants(name):
    module = importlib.import_module(f"src.spatial.cities.{name}")
    canon = name.upper()
    for suffix in CANONICAL_SUFFIXES:
        attr = f"{canon}_{suffix}"
        assert hasattr(module, attr), f"{name} is missing canonical constant {attr}"


def test_all_expected_leaf_modules_present():
    # 62 hand-authored Metro leaf modules plus NYC (cities/nyc.py, US-176),
    # whose geometry still lives in src.spatial.submarkets.
    assert len(_LEAF_MODULES) == 63
