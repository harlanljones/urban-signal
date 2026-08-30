"""Unit tests for the US-372 state liquor/contractor license registries.

Rebuilt 2026-08-30 after the original module was lost uncommitted; contracts
recovered from the stream log, the leaf modules themselves, and recovered
byte-verbatim TABC fixtures. The spec dicts must construct as ``DatasetSpec``
with zero massaging, and every registry must parse through the unmodified
``SLALicensesProducer`` row path (``resolve_field_map`` patched to return the
registry's map; ``needs_geocode`` is the spine's wiring).
"""

import json
from unittest.mock import patch

import pytest

from src.producers import field_maps_state_licenses as maps
from src.producers import state_license_specs as specs
from src.spatial.city_registry import DatasetSpec

_REGISTRY_KEYS = (
    "tabc_active", "tabc_pending", "wa_li", "wa_lcb",
    "or_ccb", "or_olcc", "co_liquor", "co_approved", "mo_new",
)

_NAMESPACES = {
    "tabc_active": "tabc:",
    "tabc_pending": "tabc:",
    "wa_li": "wa_li:",
    "wa_lcb": "wa_lcb:",
    "or_ccb": "or_ccb:",
    "or_olcc": "olcc:",
    "co_liquor": "co_liquor:",
    "co_approved": "co_approved:",
    "mo_new": "mo_liquor:",
}

_TICKET_4X4 = {
    "tabc_active": "7hf9-qc9f",
    "tabc_pending": "mxm5-tdpj",
    "wa_li": "m8qx-ubtq",
    "wa_lcb": "vgcw-qfjm",
    "or_ccb": "g77e-6bhs",
    "or_olcc": "qad4-bnxp",
    "co_liquor": "ier5-5ms2",
    "co_approved": "htyp-tqzh",
    "mo_new": "dymb-xy5c",
}

# Byte-verbatim rows captured live 2026-08-28 through the namespaced endpoints.
_CAPTURED_ROWS = {
    "tabc_active": (
        '{"master_file_id":"2100002765.0","license_type":"BG","license_id":"100001159.0","primary_status":"Active","license_status":"Active","current_issued_date":"2026-01-14T00:00:00.000","status_change_date":"2026-01-14T14:55:56.403","expiration_date":"2028-01-25T00:00:00.000","expiration_year":"2028","expiration_month":"1","expiration_day":"25","trade_name":"QUALITY SEAFOOD MARKET","owner":"QUALITY SEAFOOD INC.","wine_percent":"Upto 17%","gun_sign":"BLUE","original_issue_date":"2005-01-26T00:00:00.000","tier":"Retail","address":"5621 AIRPORT BOULEVARD","city":"Austin","state":"TX","zip":"787511412","county":"Travis","country":"UNITED STATES","mail_address":"5621 AIRPORT BLVD","mail_city":"Austin","mail_state":"TX","mail_zip":"787511412","mail_country":"United States","legacy_clp":"BG571927","license_type_ns":"tabc:BG"}',
        '{"master_file_id":"2100001196.0","license_type":"MB","license_id":"100002654.0","primary_status":"Expired - Original Required","license_status":"Expired - Original Required","current_issued_date":"2023-03-06T00:00:00.000","status_change_date":"2025-04-06T05:00:02.030","expiration_date":"2025-03-06T00:00:00.000","expiration_year":"2025","expiration_month":"3","expiration_day":"6","trade_name":"BABY ACAPULCO RESTAURANT","owner":"SANCHEZ ENTERPRISES INC.","gun_sign":"BLUE","original_issue_date":"1990-03-07T00:00:00.000","tier":"Retail","address":"1628 BARTON SPRINGS RD","city":"Austin","state":"TX","zip":"787041035","county":"Travis","country":"UNITED STATES","mail_address":"1912 E 7TH ST UNIT B","mail_city":"Austin","mail_state":"TX","mail_zip":"787023579","mail_country":"United States","legacy_clp":"MB213472","license_type_ns":"tabc:MB"}',
    ),
    "mo_new": (
        '{"license_number":"320796","licensee":"ZAVALACORP LLC","dbaname":"EL NOPALITO","businesstype":"Limited Liability Company","license_type":"Beer & Light Wine by Drink","current_status":"Active","original_date":"08/13/2026","county":"JACKSON COUNTY","street_number":"9928","street":"HOLMES","city":"KANSAS CITY","state":"Missouri","zip_code":"64131","license_type_ns":"mo_liquor:Beer & Light Wine by Drink","street_address_ns":"9928 HOLMES"}',
        '{"license_number":"282718","licensee":"T SHOTS INC.","dbaname":"ARTHUR\'S LOUNGE","businesstype":"Corporation","license_type":"Extended Hours","current_status":"Active","original_date":"08/24/2026","county":"PLATTE COUNTY","street_number":"8156","street":"& 8158 N.W. PRAIRIE VIEW RD.","city":"KANSAS CITY","state":"Missouri","zip_code":"64151","license_type_ns":"mo_liquor:Extended Hours","street_address_ns":"8156 & 8158 N.W. PRAIRIE VIEW RD."}',
    ),
}


def _rows(key):
    return tuple(json.loads(raw) for raw in _CAPTURED_ROWS[key])


def _build_specs():
    return {
        "tabc_active": specs.tabc_active_spec("Travis"),
        "tabc_pending": specs.tabc_pending_spec("Austin"),
        "wa_li": specs.wa_li_spec(),
        "wa_lcb": specs.WA_LCB_SPEC,
        "or_ccb": specs.OR_CCB_SPEC,
        "or_olcc": specs.OR_OLCC_SPEC,
        "co_liquor": specs.CO_LIQUOR_SPEC,
        "co_approved": specs.CO_APPROVED_SPEC,
        "mo_new": specs.mo_new_spec(),
    }


_SPECS = _build_specs()


@pytest.fixture(scope="module")
def sla_producer():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        yield SLALicensesProducer()


def _parse(sla_producer, key, row):
    with patch(
        "src.producers.field_maps.resolve_field_map",
        return_value=maps.FIELD_MAPS[key],
    ):
        return sla_producer.parse_socrata_row(row, city_id=key)


class TestSpecShape:
    @pytest.mark.parametrize("key", _REGISTRY_KEYS)
    def test_spec_constructs_as_dataset_spec(self, key):
        assert DatasetSpec(**_SPECS[key]) is not None

    @pytest.mark.parametrize("key", _REGISTRY_KEYS)
    def test_endpoint_carries_the_ticket_dataset_and_namespace(self, key):
        spec = _SPECS[key]
        assert _TICKET_4X4[key] in spec["endpoint"], key
        assert f"'{_NAMESPACES[key]}' ||" in spec["endpoint"], key

    def test_field_maps_cover_exactly_the_ticket_registries(self):
        assert set(maps.FIELD_MAPS) == set(_REGISTRY_KEYS)

    @pytest.mark.parametrize("key", _REGISTRY_KEYS)
    def test_every_map_namespaces_license_type(self, key):
        assert maps.FIELD_MAPS[key]["license_type"] == ["license_type_ns"]


class TestParseThroughRealProducer:
    def test_tabc_active_row(self, sla_producer):
        ev = _parse(sla_producer, "tabc_active", _rows("tabc_active")[0])
        assert ev is not None
        assert ev.license_id == "100001159.0"
        assert ev.license_type == "tabc:BG"
        assert ev.dba == "QUALITY SEAFOOD MARKET"
        assert ev.premises_name == "QUALITY SEAFOOD INC."
        assert ev.address == "5621 AIRPORT BOULEVARD"
        assert ev.license_status == "Active"
        assert ev.effective_date is not None
        assert ev.expiration_date is not None

    def test_tabc_classify_on_primary_status_not_compound_license_status(self, sla_producer):
        row = dict(_rows("tabc_active")[0], license_status="Active - Renewal Pending")
        ev = _parse(sla_producer, "tabc_active", row)
        assert ev.license_status == "Active"

    def test_tabc_expired_status_is_source_status(self, sla_producer):
        ev = _parse(sla_producer, "tabc_active", _rows("tabc_active")[1])
        assert ev.license_status == "Expired - Original Required"

    def test_mo_row_uses_composed_street_address(self, sla_producer):
        ev = _parse(sla_producer, "mo_new", _rows("mo_new")[0])
        assert ev is not None
        assert ev.license_id == "320796"
        assert ev.license_type == "mo_liquor:Beer & Light Wine by Drink"
        assert ev.address == "9928 HOLMES"
