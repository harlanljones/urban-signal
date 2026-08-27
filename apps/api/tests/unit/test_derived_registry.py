"""US-177/US-178: registry aggregator derives REGISTRY / ALIASES from leaf REGISTRATION.

The aggregator (``registry_derivation``) reconstructs the registry the
hand-written blocks define, by merging leaf-module geometry with the
hand-written non-geometry fields. Geometry is the *same object* (``is``)
the registry already imports, so object identity is preserved by construction.

As of US-178 derivation is the DEFAULT: ``city_registry.REGISTRY`` / ``ALIASES``
are the derived exports, and ``_HANDWRITTEN_REGISTRY`` / ``_HANDWRITTEN_ALIASES``
preserve the source for equivalence checks.
"""

from src.spatial import city_registry as cr
from src.spatial import registry_derivation
from src.spatial.submarkets import NYC_METRO_BBOX

GEOMETRY_FIELDS = ("metro_bbox", "division_bboxes", "submarkets", "divisions")
NON_GEOMETRY_FIELDS = ("name", "state", "center", "job_suffix", "datasets")


def _leaf_registration(city_id):
    return registry_derivation._leaf_registration(city_id)


def test_build_matches_handwritten_field_by_field():
    handwritten = cr._HANDWRITTEN_REGISTRY
    derived = registry_derivation.build_registry_from_registrations()

    assert set(derived) == set(handwritten)
    for cid in handwritten:
        d = derived[cid]
        h = handwritten[cid]
        # Geometry now lives on the leaf REGISTRATION, not the hand-written
        # block (US-180): the derived builder must carry the leaf's exact
        # geometry objects, and the hand-written block is no longer expected to.
        for field in GEOMETRY_FIELDS:
            leaf = getattr(_leaf_registration(cid), field)
            assert getattr(d, field) == leaf, (
                f"{cid.value}.{field} not equal to leaf REGISTRATION"
            )
            assert getattr(d, field) is leaf, (
                f"{cid.value}.{field} not identical object to leaf REGISTRATION"
            )
        for field in NON_GEOMETRY_FIELDS:
            assert getattr(d, field) == getattr(h, field), (
                f"{cid.value}.{field} not equal"
            )
        # Shape must be the same dataclass, no extra/dropped fields.
        assert type(d) is type(h)


def test_nyc_object_identity_preserved():
    derived = registry_derivation.build_registry_from_registrations()
    assert derived[cr.CityId.NYC].metro_bbox is NYC_METRO_BBOX


def test_derived_aliases_equal_handwritten():
    handwritten = cr._HANDWRITTEN_ALIASES
    derived = registry_derivation.build_aliases_from_registrations()
    assert derived == handwritten


def test_supported_city_ids_match_cityid():
    assert registry_derivation.derived_supported_cities() == list(cr.CityId)


def test_active_exports_are_derived():
    assert cr.USE_DERIVED_REGISTRY is True
    assert cr.REGISTRY == registry_derivation.build_registry_from_registrations()
    assert cr.ALIASES == registry_derivation.build_aliases_from_registrations()
    # The active export must carry the leaf REGISTRATION geometry (US-180 moved
    # geometry out of the hand-written block).
    for cid in cr._HANDWRITTEN_REGISTRY:
        leaf = _leaf_registration(cid)
        for field in GEOMETRY_FIELDS:
            assert getattr(cr.REGISTRY[cid], field) is getattr(leaf, field)
