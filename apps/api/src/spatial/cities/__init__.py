"""City-specific spatial registry modules.

Derived gather (US-429): the package namespace is built from the leaf modules,
not from hand-maintained import blocks. Every ``src.spatial.cities.<city_id>``
leaf (named after its ``CityId`` by convention) defines its own geometry; this
package re-exports each leaf's public spatial names — the canonical
``<NAME>_METRO_BBOX`` / ``<NAME>_DIVISION_BBOXES`` / ``<NAME>_DIVISIONS`` /
``<NAME>_SUBMARKETS`` constants, the short-prefix aliases leaves define
(``SF_``, ``LA_``, ``NOLA_``, ``PHL_``, ``DC_``, ...) and the
``is_in_<city>_metro`` helpers.

Adding a city is a leaf edit only: create ``cities/<city_id>.py`` and the
gather picks it up. The interlock gate
(``tests/unit/test_interlock_gate.py``) asserts the gathered exports stay
identical to the objects registered in ``REGISTRY``.
"""

import importlib
import pkgutil
from types import ModuleType
from typing import Any

_GATHERED_SUFFIXES = ("METRO_BBOX", "DIVISION_BBOXES", "DIVISIONS", "SUBMARKETS")


def leaf_module_names() -> list[str]:
    """Every city leaf module in this package, sorted (mirrors the CityId set)."""
    return sorted(
        mod.name
        for mod in pkgutil.iter_modules(__path__)  # type: ignore[arg-type]
        if not mod.name.startswith("_") and not mod.ispkg
    )


def leaf_module(name: str) -> ModuleType:
    """Import one leaf module by name (``CityId.value``)."""
    return importlib.import_module(f"{__name__}.{name}")


def _is_gathered(attr: str) -> bool:
    return attr.endswith(_GATHERED_SUFFIXES) or (
        attr.startswith("is_in_") and attr.endswith("_metro")
    )


def _gather() -> dict[str, Any]:
    exports: dict[str, Any] = {}
    for leaf in leaf_module_names():
        for attr, value in vars(leaf_module(leaf)).items():
            if attr.startswith("_") or not _is_gathered(attr):
                continue
            previous = exports.get(attr)
            if previous is not None and previous is not value:
                raise ImportError(
                    f"{__name__}.{attr} is defined by more than one leaf module"
                )
            exports[attr] = value
    return exports


_GATHERED = _gather()
globals().update(_GATHERED)
__all__ = sorted(_GATHERED)  # noqa: PLE0605 -- derived; cannot be a literal
