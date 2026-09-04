"""Unit tests for the US-421 Texas state super-feed wiring across the six
southwest-probe TX metros with no municipal permit/SLA feed of their own
(``docs/research/southwest-mountain-expansion-probe-2026-08-30.md``):
Lubbock, Corpus Christi, Laredo, Rio Grande Valley (Cameron + Hidalgo
counties), College Station, and Killeen.

The county-parameterized spec builders (``tx_trec_broker_spec`` /
``tx_trec_app_spec`` / ``tx_tdlr_spec`` in ``tx_trec_specs.py``,
``tabc_active_spec`` in ``state_license_specs.py``) already generalize over
any Texas county — US-397/US-372 built them that way. This test proves each
one constructs a valid ``DatasetSpec`` and carries the right county-name
``where`` clause for every county behind this ticket's six metros, so the
"wire the super-feed for these metros" requirement is a verified fact rather
than an assumption about generic code.

County-name (Socrata ``where`` filter) mapping, with FIPS from the research
probe for traceability — TREC/TABC filter on ``county`` (title case);
TDLR filters on ``business_county`` (uppercase, per the live US-397 probe):

- Lubbock, TX -> Lubbock County (48303)
- Corpus Christi, TX -> Nueces County (48355)
- Laredo, TX -> Webb County (48479)
- Rio Grande Valley (Brownsville/McAllen) -> Cameron County (48061) +
  Hidalgo County (48215)
- College Station, TX -> Brazos County (48041)
- Killeen, TX -> Bell County (48027)
"""

import pytest

from src.producers import state_license_specs as sla_specs
from src.producers import tx_trec_specs as trec_specs
from src.spatial.city_registry import DatasetSpec

# metro label -> TREC/TABC county name(s)
_METRO_COUNTIES = {
    "Lubbock": ["Lubbock"],
    "Corpus Christi": ["Nueces"],
    "Laredo": ["Webb"],
    "Rio Grande Valley": ["Cameron", "Hidalgo"],
    "College Station": ["Brazos"],
    "Killeen": ["Bell"],
}

_ALL_COUNTIES = sorted({c for counties in _METRO_COUNTIES.values() for c in counties})


class TestTxTrecBrokerCoversEveryMetroCounty:
    @pytest.mark.parametrize("county", _ALL_COUNTIES)
    def test_spec_constructs_and_filters_the_county(self, county):
        spec = trec_specs.tx_trec_broker_spec(county)
        assert DatasetSpec(**spec) is not None
        assert spec["where"] == f"county = '{county}'"
        assert "s7ft-44qi" in spec["endpoint"]


class TestTxTrecAppCoversEveryMetroCounty:
    @pytest.mark.parametrize("county", _ALL_COUNTIES)
    def test_spec_constructs_and_filters_the_county(self, county):
        spec = trec_specs.tx_trec_app_spec(county)
        assert DatasetSpec(**spec) is not None
        assert spec["where"] == f"county = '{county}'"
        assert "bf5n-799f" in spec["endpoint"]


class TestTxTdlrCoversEveryMetroCounty:
    @pytest.mark.parametrize("county", _ALL_COUNTIES)
    def test_spec_constructs_and_filters_the_business_county(self, county):
        upper = county.upper()
        spec = trec_specs.tx_tdlr_spec(upper)
        assert DatasetSpec(**spec) is not None
        assert spec["where"] == f"business_county = '{upper}'"
        assert "7358-krk7" in spec["endpoint"]


class TestTabcActiveCoversEveryMetroCounty:
    @pytest.mark.parametrize("county", _ALL_COUNTIES)
    def test_spec_constructs_and_filters_the_county(self, county):
        spec = sla_specs.tabc_active_spec(county)
        assert DatasetSpec(**spec) is not None
        assert spec["where"] == f"county = '{county}'"
        assert "7hf9-qc9f" in spec["endpoint"]
        assert spec["needs_geocode"] is True
        assert spec["geocode_context"] == "TX"


class TestRioGrandeValleyIsTwoCounties:
    def test_rgv_maps_to_cameron_and_hidalgo(self):
        assert _METRO_COUNTIES["Rio Grande Valley"] == ["Cameron", "Hidalgo"]

    def test_every_metro_resolves_to_at_least_one_county(self):
        for metro, counties in _METRO_COUNTIES.items():
            assert counties, metro
