"""Unit tests for the Miami-Dade County leaf (US-199): spatial module +
PERMITS / SLA / DEEDS field maps.

Miami-Dade is a PARTIAL county metro: permits (address-only Hub table),
Local Business Tax SLA snapshot, PaGis last-sale deeds. COMPLAINTS_311 is
absent (year slices frozen; 2024 token-gated). Tests pass WITHOUT a spine
registration (no CityId.MIAMI_DADE).

Live fixtures captured from the 2026-08-27 probe contract
(docs/research/wave-3-probe-miami-dade.md). Do not fold Broward or City of
Miami into this city_id (ADR 0007).
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_miami_dade import (
    DEEDS_FIELD_MAP,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.producers.watermarks import typed_watermark_entry
from src.spatial.cities.miami_dade import (
    MIAMI_DADE_CENTER,
    MIAMI_DADE_CITY_ID,
    MIAMI_DADE_DEEDS_ENDPOINT,
    MIAMI_DADE_DIVISION_BBOXES,
    MIAMI_DADE_DIVISIONS,
    MIAMI_DADE_FEED_SPECS,
    MIAMI_DADE_GEOCODE_CONTEXT,
    MIAMI_DADE_METRO_BBOX,
    MIAMI_DADE_PERMITS_ENDPOINT,
    MIAMI_DADE_SLA_CERTIFICATE_OF_USE,
    MIAMI_DADE_SLA_ENDPOINT,
    MIAMI_DADE_SLA_ENTERPRISE_TWIN,
    MIAMI_DADE_SUBMARKETS,
    REGISTRATION,
    get_miami_dade_dataset,
    is_in_miami_dade_metro,
)
from src.spatial.city_registry import FeedType
from src.spatial.geocoder import _STATE_RE, normalize_address


# Probe-shaped fixtures (2026-08-27). Permits are a non-spatial table.
PERMITS_ROW = {
    "PermitNumber": "B-2026-081234",
    "ProcessNumber": "P2026-009988",
    "ObjectId": 881122,
    "PermitType": "BLDG",
    "ApplicationTypeDescription": "Residential Alteration",
    "EstimatedValue": "185000",
    "PermitIssuedDate": "2026-08-25",
    "ApplicationDate": "2026-07-12T00:00:00+00:00",
    "PropertyAddress": "1450 BRICKELL AVE",
    "City": "MIAMI",
    "State": "FL",
    "FolioNumber": "0141390012340",
    "StructureUnits": 1,
    "StructureFloors": 12,
}

SLA_ROW = {
    "ACCOUNTNO": "LBT-884421",
    "RECEIPTNO": "R2026-11002",
    "OBJECTID": 193001,
    "BUSNAME": "BRICKELL COFFEE ROASTERS LLC",
    "OWNERNAME": "MARIA SANTOS",
    "BUSADDR": "801 BRICKELL AVE",
    "BUSCITY": "MIAMI",
    "ZIPCODE": "33131",
    "CLASSDESC": "RETAIL FOOD",
    "CATGRYNAME": "FOOD SERVICE",
    "OCCDESC": "COFFEE SHOP",
    "BUSSDATE": "2026-03-15T00:00:00+00:00",
    "ACCSTATUS": "Active",
    "PAIDSTATUS": "Paid",
    "YEAR": 2026,
    "LAT": 25.7654,
    "LON": -80.1901,
}

DEEDS_ROW = {
    "FOLIO": "0141390012340",
    "OR_BK_1": "34821",
    "OR_PG_1": "1844",
    "OBJECTID": 550012,
    "PRICE_1": 700100,
    "DOS_1": "20260817",
    "GRANTOR_1": "RIVERA JOSE",
    "GRANTEE_1": "CHEN WEI",
    "TRUE_SITE_ADDR": "1450 BRICKELL AVE",
    "TRUE_SITE_ZIP_CODE": "33131",
    "QU_FLG_1": "Q",
    "latitude": 25.7580,
    "longitude": -80.1915,
}

PERMITS_GEOCODE = (25.7580, -80.1915)


class TestMiamiDadeSpatial:
    def test_city_id_constant(self):
        assert MIAMI_DADE_CITY_ID == "miami_dade"

    def test_metro_contains_county_center(self):
        assert is_in_miami_dade_metro(MIAMI_DADE_CENTER["lat"], MIAMI_DADE_CENTER["lng"]) is True
        assert is_in_miami_dade_metro(25.7617, -80.1918) is True  # Downtown Miami
        assert is_in_miami_dade_metro(25.4687, -80.4776) is True  # Homestead
        assert is_in_miami_dade_metro(25.9564, -80.1390) is True  # Aventura
        assert is_in_miami_dade_metro(25.8195, -80.3553) is True  # Doral

    def test_metro_rejects_null_and_foreign(self):
        assert is_in_miami_dade_metro(None, None) is False
        assert is_in_miami_dade_metro(26.1224, -80.1373) is False  # Fort Lauderdale / Broward
        assert is_in_miami_dade_metro(28.5383, -81.3792) is False  # Orlando
        assert is_in_miami_dade_metro(27.948, -82.458) is False  # Tampa

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in MIAMI_DADE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= MIAMI_DADE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= MIAMI_DADE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= MIAMI_DADE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= MIAMI_DADE_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in MIAMI_DADE_SUBMARKETS.items():
            bbox = MIAMI_DADE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in MIAMI_DADE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(MIAMI_DADE_SUBMARKETS)

    def test_submarkets_carry_miami_dade_city_id(self):
        assert {m.city_id for m in MIAMI_DADE_SUBMARKETS.values()} == {"miami_dade"}

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in MIAMI_DADE_DIVISIONS.items():
            bbox = MIAMI_DADE_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_division_count(self):
        assert len(MIAMI_DADE_DIVISIONS) == 6
        for div in MIAMI_DADE_DIVISIONS.values():
            assert div.city_id == "miami_dade"

    def test_registration_bundles_leaf_constants(self):
        assert REGISTRATION.metro_bbox is MIAMI_DADE_METRO_BBOX
        assert REGISTRATION.submarkets is MIAMI_DADE_SUBMARKETS
        assert REGISTRATION.contains is is_in_miami_dade_metro


class TestFeedRegistration:
    def test_exactly_three_feed_types_are_registered(self):
        assert set(MIAMI_DADE_FEED_SPECS) == {"permits", "sla", "deeds"}

    def test_permits_spec_matches_probe_contract(self):
        spec = get_miami_dade_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == MIAMI_DADE_PERMITS_ENDPOINT
        assert spec.watermark_col == "PermitIssuedDate"
        assert spec.id_keys == ["PermitNumber", "ProcessNumber", "ObjectId"]
        assert spec.producer_key == "permits"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Miami-Dade County, FL"
        assert spec.oid_field == "ObjectId"
        assert spec.max_record_count == 1000
        assert spec.non_spatial is True
        assert spec.rolling_window_days == 730
        assert spec.field_map == PERMITS_FIELD_MAP

    def test_sla_spec_is_snapshot_with_native_coords(self):
        spec = get_miami_dade_dataset(FeedType.SLA)
        assert spec.platform == "arcgis"
        assert spec.endpoint == MIAMI_DADE_SLA_ENDPOINT
        assert spec.watermark_col == "BUSSDATE"
        assert spec.ingestion_mode == "snapshot"
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 16000
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.companion_endpoints["certificate_of_use"] == MIAMI_DADE_SLA_CERTIFICATE_OF_USE
        assert spec.companion_endpoints["enterprise_twin"] == MIAMI_DADE_SLA_ENTERPRISE_TWIN

    def test_sla_companions_are_metadata_only(self):
        """Scheduler does not poll companion_endpoints; they stay off FEED_SPECS."""
        assert "certificate_of_use" not in MIAMI_DADE_FEED_SPECS
        assert "enterprise_twin" not in MIAMI_DADE_FEED_SPECS

    def test_deeds_spec_declares_text_watermark_and_market_filter(self):
        spec = get_miami_dade_dataset(FeedType.DEEDS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == MIAMI_DADE_DEEDS_ENDPOINT
        assert spec.watermark_col == "DOS_1"
        assert spec.watermark_type == "text"
        assert spec.watermark_format == "%Y%m%d"
        assert spec.where == "PRICE_1 >= 10000"
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 20000
        assert spec.field_map == DEEDS_FIELD_MAP

    @pytest.mark.parametrize("absent_feed", [FeedType.COMPLAINTS_311, FeedType.STR, FeedType.CRIME])
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'miami_dade'.*available"):
            get_miami_dade_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert FIELD_MAP["permits"] is PERMITS_FIELD_MAP
        assert FIELD_MAP["sla"] is SLA_FIELD_MAP
        assert FIELD_MAP["deeds"] is DEEDS_FIELD_MAP
        assert GEOCODE_CONTEXT == MIAMI_DADE_GEOCODE_CONTEXT == "Miami-Dade County, FL"
        assert "311" not in FIELD_MAP


class TestMiamiDadeFieldMaps:
    def test_permits_map_reads_live_columns(self):
        row = PERMITS_ROW
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "B-2026-081234"
        assert first_mapped(row, PERMITS_FIELD_MAP, "issuance_date") == "2026-08-25"
        assert first_mapped(row, PERMITS_FIELD_MAP, "filing_date") == "2026-07-12T00:00:00+00:00"
        assert first_mapped(row, PERMITS_FIELD_MAP, "address_street") == "1450 BRICKELL AVE"
        assert first_mapped(row, PERMITS_FIELD_MAP, "bbl") == "0141390012340"
        assert first_mapped(row, PERMITS_FIELD_MAP, "cost") == "185000"
        assert first_mapped(row, PERMITS_FIELD_MAP, "borough") == "MIAMI"

    def test_permits_job_id_falls_back_when_permit_number_is_null(self):
        row = {"PermitNumber": None, "ProcessNumber": "P2026-009988", "ObjectId": 881122}
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "P2026-009988"

    def test_permits_has_no_coordinate_candidates(self):
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP

    def test_sla_map_reads_live_columns_and_native_lat_lon(self):
        row = SLA_ROW
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "LBT-884421"
        assert first_mapped(row, SLA_FIELD_MAP, "dba") == "BRICKELL COFFEE ROASTERS LLC"
        assert first_mapped(row, SLA_FIELD_MAP, "premises_name") == "MARIA SANTOS"
        assert first_mapped(row, SLA_FIELD_MAP, "license_type") == "RETAIL FOOD"
        assert first_mapped(row, SLA_FIELD_MAP, "address_street") == "801 BRICKELL AVE"
        assert first_mapped(row, SLA_FIELD_MAP, "latitude") == 25.7654
        assert first_mapped(row, SLA_FIELD_MAP, "longitude") == -80.1901
        assert first_mapped(row, SLA_FIELD_MAP, "status") == "Active"

    def test_deeds_map_reads_live_columns(self):
        row = DEEDS_ROW
        assert first_mapped(row, DEEDS_FIELD_MAP, "doc_id") == "34821"
        assert first_mapped(row, DEEDS_FIELD_MAP, "bbl") == "0141390012340"
        assert first_mapped(row, DEEDS_FIELD_MAP, "document_amount") == 700100
        assert first_mapped(row, DEEDS_FIELD_MAP, "recorded_date") == "20260817"
        assert first_mapped(row, DEEDS_FIELD_MAP, "party1_grantor") == "RIVERA JOSE"
        assert first_mapped(row, DEEDS_FIELD_MAP, "party2_grantee") == "CHEN WEI"
        assert first_mapped(row, DEEDS_FIELD_MAP, "address_street") == "1450 BRICKELL AVE"


class TestGeocodingCaveats:
    def test_permit_street_has_no_state_token_so_context_appends(self):
        assert _STATE_RE.search("1450 BRICKELL AVE".upper()) is None

    def test_context_with_fl_is_a_state_token(self):
        assert _STATE_RE.search("1450 BRICKELL AVE, MIAMI-DADE COUNTY, FL".upper()) is not None

    def test_unit_designator_normalization_preserves_city(self):
        norm = normalize_address("801 BRICKELL AVE SUITE 200, MIAMI, FL")
        assert "SUITE" not in norm
        assert "MIAMI" in norm


class TestDeedsTypedWatermark:
    def test_yyyymmdd_parses_under_declared_format(self):
        entry = typed_watermark_entry("20260817", fmt="%Y%m%d")
        assert entry is not None
        assert entry[0] == "20260817"
        assert entry[1].year == 2026
        assert entry[1].month == 8
        assert entry[1].day == 17

    def test_empty_value_is_dropped(self):
        assert typed_watermark_entry("", fmt="%Y%m%d") is None
        assert typed_watermark_entry(None, fmt="%Y%m%d") is None


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


@pytest.fixture
def permits():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        return DOBPermitsProducer()


@pytest.fixture
def sla():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        return SLALicensesProducer()


@pytest.fixture
def deeds():
    with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
        from src.producers.deeds_acris_producer import DeedsACRISProducer

        return DeedsACRISProducer()


class TestMiamiDadePermitParsing:
    def test_address_only_permit_uses_declared_geocoder(self, permits, monkeypatch):
        captured = []
        _patch_resolve(monkeypatch, "permits")

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address, context))
            return PERMITS_GEOCODE

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        event = permits.parse_socrata_row(PERMITS_ROW, city_id="miami_dade")
        assert event is not None
        assert event.city_id == "miami_dade"
        assert event.job_id == "B-2026-081234"
        assert str(event.issuance_date).startswith("2026-08-25")
        assert event.latitude == pytest.approx(PERMITS_GEOCODE[0])
        assert event.longitude == pytest.approx(PERMITS_GEOCODE[1])
        assert event.h3_res7 is not None
        assert captured == [("miami_dade", "permits", "1450 BRICKELL AVE", None)]

    def test_permit_without_address_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        row = {**PERMITS_ROW, "PropertyAddress": ""}
        assert permits.parse_socrata_row(row, city_id="miami_dade") is None

    def test_permit_geocode_sits_inside_metro(self):
        assert is_in_miami_dade_metro(*PERMITS_GEOCODE)


class TestMiamiDadeSlaParsing:
    def test_native_lat_lon_parses_without_geocoder(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(SLA_ROW, city_id="miami_dade")
        assert event is not None
        assert event.city_id == "miami_dade"
        assert event.license_id == "LBT-884421"
        assert event.dba == "BRICKELL COFFEE ROASTERS LLC"
        assert event.license_type == "RETAIL FOOD"
        assert event.address == "801 BRICKELL AVE"
        assert event.license_status == "Active"
        assert event.latitude == pytest.approx(25.7654)
        assert event.longitude == pytest.approx(-80.1901)
        assert event.h3_res7 is not None
        assert str(event.effective_date).startswith("2026-03-15")

    def test_sla_fixture_sits_inside_metro(self):
        assert is_in_miami_dade_metro(float(SLA_ROW["LAT"]), float(SLA_ROW["LON"]))


class TestMiamiDadeDeedsParsing:
    def test_last_sale_parses_native_geometry_and_text_date(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW, city_id="miami_dade")
        assert event is not None
        assert event.city_id == "miami_dade"
        assert event.doc_id == "34821"
        assert event.bbl == "0141390012340"
        assert event.document_amount == 700100.0
        assert str(event.recorded_date).startswith("2026-08-17")
        assert event.party1_grantor == "RIVERA JOSE"
        assert event.party2_grantee == "CHEN WEI"
        assert event.latitude == pytest.approx(25.7580)
        assert event.longitude == pytest.approx(-80.1915)
        assert event.h3_res7 is not None

    def test_deeds_fixture_sits_inside_metro(self):
        assert is_in_miami_dade_metro(
            float(DEEDS_ROW["latitude"]), float(DEEDS_ROW["longitude"])
        )
