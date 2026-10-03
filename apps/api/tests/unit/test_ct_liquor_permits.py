"""Hartford, New Haven and Bridgeport read liquor permits, not every CT credential.

``data.ct.gov/resource/ngch-56tr`` holds every credential Connecticut's
Department of Consumer Protection issues. Filtered by city alone, the three
``sla`` feeds published pharmacists, locksmiths and nurses' aides under their
own names (Hartford: 247,564 rows, 1,554 of them liquor permits on
2026-09-30). ``src/producers/ct_liquor_specs.py`` holds the permit list, the
filter and the field map the registry uses for all three.
"""

import pytest

from src.producers.ct_liquor_specs import (
    CT_LIQUOR_CREDENTIAL_TYPES,
    CT_LIQUOR_SLA_FIELD_MAP,
    ct_liquor_where,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType

CT_SLA_CITIES = {"hartford": "HARTFORD", "new_haven": "NEW HAVEN", "bridgeport": "BRIDGEPORT"}


@pytest.mark.parametrize("city_id", sorted(CT_SLA_CITIES))
def test_registry_filters_each_city_to_liquor_permits(city_id):
    spec = REGISTRY[CityId(city_id)].datasets[FeedType.SLA]
    assert spec.endpoint == "https://data.ct.gov/resource/ngch-56tr.json"
    assert spec.where == ct_liquor_where(CT_SLA_CITIES[city_id])
    assert spec.id_keys == ["credentialid"]
    assert spec.field_map == CT_LIQUOR_SLA_FIELD_MAP


def test_the_permittee_name_is_never_a_field_candidate():
    """``name`` is a person on individually held permits (1,017 of Hartford's
    1,554); premises and trade names come from ``businessname`` and ``dba``."""
    candidates = {col for cols in CT_LIQUOR_SLA_FIELD_MAP.values() for col in cols}
    assert "name" not in candidates
    assert CT_LIQUOR_SLA_FIELD_MAP["premises_name"] == ["businessname", "dba"]
    assert CT_LIQUOR_SLA_FIELD_MAP["dba"] == ["dba", "businessname"]


def test_permit_list_has_no_repeats_and_leaves_out_non_premises_codes():
    assert len(CT_LIQUOR_CREDENTIAL_TYPES) == len(set(CT_LIQUOR_CREDENTIAL_TYPES))
    for code in (
        "LBD",  # brand label registrations (240,164 rows statewide)
        "LIQF",  # liquor filings
        "LIQ",  # applications, before a permit type is assigned
        "LTA",  # temporary liquor
        "LCO",  # temporary charitable organization liquor
        "LCT",  # caterer: serves at other people's premises
        "LSL",  # out-of-state shipper
        "LIW",  # wholesaler
        "LIB",  # boat
        "RGD",  # retail gasoline dealer (the old fixtures' credential)
    ):
        assert code not in CT_LIQUOR_CREDENTIAL_TYPES, code


def test_where_quotes_each_code_and_the_city():
    where = ct_liquor_where("NEW HAVEN")
    assert where.startswith("city = 'NEW HAVEN' AND credentialtype IN ('LIR', ")
    assert where.endswith("'LFO')")
    assert where.count("'") == 2 * (len(CT_LIQUOR_CREDENTIAL_TYPES) + 1)
