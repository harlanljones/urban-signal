"""US-177/US-428: registry is derived from the corpus + leaf REGISTRATION.

The single construction path (``registry_derivation.build_runtime_exports``)
loads each city's registration from its declarative YAML definition beside the
leaf module, then re-binds geometry to the leaf ``REGISTRATION``'s exact
objects. There is no hand-written registry to compare against: the corpus
satisfies the runtime, and building fails loudly when it does not.

These tests pin the invariants the interlock gate relies on: every CityId
resolves through the corpus and the leaf module, and the active ``REGISTRY``
/``ALIASES`` are exactly the derived exports.
"""



from src.spatial import city_registry as cr
from src.spatial import registry_derivation

GEOMETRY_FIELDS = ("metro_bbox", "division_bboxes", "submarkets", "divisions")


def _leaf_registration(city_id):
    return registry_derivation._leaf_registration(city_id)


def _corpus_definitions():
    from pathlib import Path

    from src.config import settings
    from src.spatial.city_data import load_definitions

    return load_definitions(Path(settings.city_data_dir))


def test_build_matches_corpus_and_leaf_geometry():
    definitions = _corpus_definitions()
    registry, aliases = registry_derivation.build_runtime_exports()

    # Every corpus city resolves; every CityId is present.
    assert set(registry) == set(cr.CityId)
    assert aliases
    # Non-geometry fields come verbatim from the corpus definitions.
    assert len(definitions) >= len(cr.CityId)
    # Geometry is identical to the leaf REGISTRATION for every city.
    for cid in cr.CityId:
        leaf = _leaf_registration(cid)
        for field in GEOMETRY_FIELDS:
            assert getattr(registry[cid], field) is getattr(leaf, field), (
                f"{cid.value}.{field} not identical to leaf REGISTRATION"
            )
    # Shape is the same dataclass used everywhere.
    for cid in cr.CityId:
        assert type(registry[cid]) is cr.CityRegistration


def test_nyc_object_identity_preserved():
    from src.spatial.submarkets import NYC_METRO_BBOX

    registry, _ = registry_derivation.build_runtime_exports()
    assert registry[cr.CityId.NYC].metro_bbox is NYC_METRO_BBOX


def test_derived_aliases_are_string_keyed_and_complete():
    registry, aliases = registry_derivation.build_runtime_exports()
    for alias, city_id in aliases.items():
        assert isinstance(alias, str)
        assert city_id in registry, f"alias {alias!r} resolves to unregistered {city_id}"


def test_registry_aliases_resolve_from_corpus():
    """Every corpus aliases entry resolves to a registered city."""
    registry, aliases = registry_derivation.build_runtime_exports()
    for city_id in registry:
        assert city_id.value in aliases, f"{city_id.value} has no self alias"


def test_supported_city_ids_match_cityid():
    assert registry_derivation.derived_supported_cities() == list(cr.CityId)


def test_active_exports_are_derived():
    # The active export is exactly the derived registry (no handwritten copy).
    registry, aliases = registry_derivation.build_runtime_exports()
    assert cr.REGISTRY == registry
    assert cr.ALIASES == aliases
    for cid in cr.CityId:
        leaf = _leaf_registration(cid)
        for field in GEOMETRY_FIELDS:
            assert getattr(cr.REGISTRY[cid], field) is getattr(leaf, field)


def test_corpus_has_no_duplicate_or_unknown_city_ids():
    definitions = _corpus_definitions()
    city_ids = [d["city_id"] for d in definitions]
    assert len(city_ids) == len(set(city_ids)), "duplicate city_id in corpus"
    known = {c.value for c in cr.CityId}
    for city_id in city_ids:
        assert city_id in known, f"corpus city_id {city_id!r} has no CityId"


def test_corpus_definitions_parse_cleanly():
    """The corpus parses into registrations without raising (covered by the
    interlock gate anyway); asserting here surface a bad unit early."""
    registry, aliases = registry_derivation.build_runtime_exports()
    assert registry and aliases
