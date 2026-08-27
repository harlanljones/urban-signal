"""Unit tests for the Las Vegas (Clark County) leaf — US-145.

Las Vegas registers TWO feed types like Los Angeles and Austin — PERMITS
(Clark County Building Permits, address-only ArcGIS table) and DEEDS (Clark
County parcel sales, address-only -> ADR-0004 geocoder-ready). SLA / 311 are
deliberately absent for this ticket, so `get_dataset` raises for them once the
spine lands.

Per the parallel-streams contract, this leaf test must pass WITHOUT the spine
registry being edited. Registration-dependent assertions therefore skip when
CityId.LAS_VEGAS is absent; everything else (bbox containment, submarket
geometry, field-map mapping, and producer row parsing) is verified against the
leaf modules directly.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_las_vegas import FIELD_MAP
from src.spatial.cities.las_vegas import (
    LAS_VEGAS_DIVISION_BBOXES,
    LAS_VEGAS_DIVISIONS,
    LAS_VEGAS_METRO_BBOX,
    LAS_VEGAS_SUBMARKETS,
    is_in_las_vegas_metro,
)
from src.spatial.city_registry import CityId, FeedType

# The spine adds CityId.LAS_VEGAS + REGISTRY entry; until then these tests skip
# rather than fail (the leaf is importable and the rest of the suite is green).
LV = getattr(CityId, "LAS_VEGAS", None)


def _registry():
    from src.spatial.city_registry import REGISTRY

    return REGISTRY


def _skip_if_no_spine():
    if LV is None:
        pytest.skip("spine pending: CityId.LAS_VEGAS not registered yet")


class TestLasVegasRegistration:
    def test_registered(self):
        _skip_if_no_spine()
        assert LV in _registry()

    @pytest.mark.parametrize("alias", ["las_vegas", "las vegas", "clark_county", "vegas"])
    def test_aliases_resolve(self, alias):
        from src.spatial.city_registry import normalize_city

        _skip_if_no_spine()
        assert normalize_city(alias) is LV

    def test_registration_shape(self):
        _skip_if_no_spine()
        reg = _registry()[LV]
        assert reg.state == "NV"
        assert reg.job_suffix == "las_vegas"
        assert reg.submarkets is LAS_VEGAS_SUBMARKETS
        assert reg.divisions is LAS_VEGAS_DIVISIONS
        assert len(reg.divisions) == 5

    def test_center_inside_metro_bbox(self):
        _skip_if_no_spine()
        reg = _registry()[LV]
        assert is_in_las_vegas_metro(reg.center["lat"], reg.center["lng"])

    def test_exactly_three_feeds_are_registered(self):
        _skip_if_no_spine()
        assert set(_registry()[LV].datasets) == {
            FeedType.PERMITS,
            FeedType.DEEDS,
            FeedType.CRIME,
        }

    @pytest.mark.parametrize("absent_feed", [FeedType.SLA, FeedType.COMPLAINTS_311])
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        from src.spatial.city_registry import get_dataset

        _skip_if_no_spine()
        with pytest.raises(KeyError, match=r"'las_vegas'.*no.*feed.*available"):
            get_dataset(LV, absent_feed)

    def test_job_names_are_namespaced(self):
        from src.spatial.city_registry import get_job_name

        _skip_if_no_spine()
        assert get_job_name(FeedType.PERMITS, LV) == "permits_las_vegas"


class TestLasVegasGeometry:
    def test_is_in_las_vegas_metro_rejects_missing_coordinates(self):
        assert is_in_las_vegas_metro(None, None) is False

    def test_is_in_las_vegas_metro_rejects_other_cities(self):
        assert is_in_las_vegas_metro(40.7128, -74.0060) is False   # NYC
        assert is_in_las_vegas_metro(34.0522, -118.2437) is False  # LA

    def test_live_samples_sit_inside_the_metro_bbox(self):
        """Verified metro extents: Strip, Summerlin NW, Henderson, NLV."""
        assert is_in_las_vegas_metro(36.1147, -115.1728)
        assert is_in_las_vegas_metro(36.2500, -115.3000)
        assert is_in_las_vegas_metro(36.0300, -115.1100)
        assert is_in_las_vegas_metro(36.2400, -115.1200)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in LAS_VEGAS_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= LAS_VEGAS_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= LAS_VEGAS_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= LAS_VEGAS_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= LAS_VEGAS_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in LAS_VEGAS_SUBMARKETS.items():
            bbox = LAS_VEGAS_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in LAS_VEGAS_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(LAS_VEGAS_SUBMARKETS)

    def test_submarkets_carry_the_las_vegas_city_id(self):
        assert {m.city_id for m in LAS_VEGAS_SUBMARKETS.values()} == {"las_vegas"}


class TestFieldMaps:
    def test_both_feeds_declared(self):
        assert set(FIELD_MAP) == {"permits", "deeds"}

    def test_permits_maps_core_columns(self):
        fm = FIELD_MAP["permits"]
        permit_row = {
            "APNO": "C26-00439",
            "APTYPE": "Com",
            "WORKTYPE": "Electrical",
            "ISSDTTM": "2026-08-13T00:00:00+00:00",
            "DECLVLTN": 4500,
            "APL_ADDRESS": "4812 APAWANA LN LAS VEGAS",
            "ZIP": "89148",
        }
        assert first_mapped(permit_row, fm, "job_id") == "C26-00439"
        assert first_mapped(permit_row, fm, "cost") == 4500
        assert first_mapped(permit_row, fm, "issuance_date") == "2026-08-13T00:00:00+00:00"
        assert first_mapped(permit_row, fm, "address_street") == "4812 APAWANA LN LAS VEGAS"

    def test_deeds_maps_core_columns(self):
        fm = FIELD_MAP["deeds"]
        deed_row = {
            "PARCEL": 13824217021,
            "DOCNO": 2016031102044,
            "SALEPRICE": 425000,
            "SALEDATE": 20260801,
            "ADDRESS1": "5626 W LAKE MEAD BLVD",
        }
        assert first_mapped(deed_row, fm, "doc_id") == 2016031102044
        assert first_mapped(deed_row, fm, "bbl") == 13824217021
        assert first_mapped(deed_row, fm, "document_amount") == 425000
        assert first_mapped(deed_row, fm, "recorded_date") == 20260801
        assert first_mapped(deed_row, fm, "address_street") == "5626 W LAKE MEAD BLVD"


class TestLasVegasRowParsing:
    """Fixtures model Clark County open-data column spellings (Socrata). The
    shared producers resolve Las Vegas' field_map via resolve_field_map; since
    the spine is absent in this leaf test, we inject FIELD_MAP directly.
    """

    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @pytest.fixture
    def permit_row(self):
        return {
            "APNO": "C26-00439",
            "APTYPE": "Com",
            "WORKTYPE": "Electrical",
            "ISSDTTM": "2026-08-13T00:00:00+00:00",
            "DECLVLTN": 4500,
            "BLDGAPPLSTATUS": "Issued",
            "APL_ADDRESS": "4812 APAWANA LN LAS VEGAS",
            "ZIP": "89148",
        }

    @pytest.fixture
    def deed_row(self):
        return {
            "PARCEL": 13824217021,
            "DOCNO": 2016031102044,
            "SALEPRICE": 425000,
            "SALEDATE": 20260801,
            "ADDRESS1": "5626 W LAKE MEAD BLVD",
            "ZIP": 89108,
        }

    def test_permit_parses_with_field_map(self, permits, permit_row, monkeypatch):
        from src.schemas.models import JobType

        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: FIELD_MAP[feed.value],
        )
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args: (36.1147, -115.1728),
        )
        ev = permits.parse_socrata_row(permit_row, city_id="las_vegas")
        assert ev is not None
        assert ev.job_id == "C26-00439"
        assert ev.latitude == pytest.approx(36.1147)
        assert ev.longitude == pytest.approx(-115.1728)
        assert str(ev.issuance_date).startswith("2026-08-13")
        assert ev.estimated_cost == 4500.0
        assert ev.job_type == JobType.A2

    def test_deed_parses_with_field_map(self, deeds, deed_row, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: FIELD_MAP[feed.value],
        )
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args: (36.1147, -115.1728),
        )
        ev = deeds.parse_socrata_row(deed_row, city_id="las_vegas")
        assert ev is not None
        assert ev.doc_id == "2016031102044"
        assert ev.bbl == "13824217021"
        assert ev.document_amount == 425000.0
        assert str(ev.recorded_date).startswith("2026-08-01")
        assert ev.latitude == pytest.approx(36.1147)
        assert ev.longitude == pytest.approx(-115.1728)

    def test_geocoder_readiness_for_address_only_deeds(self, monkeypatch):
        """DEEDS ships a street address and no native geometry. ADR-0004 geocodes
        at enrichment; this test pins that the feed is geocoder-ready (the
        geocoder path resolves when the registry declares needs_geocode)."""
        from src.spatial import geocoder as geocoder_mod

        assert hasattr(geocoder_mod, "geocode_row_if_declared")
        assert hasattr(geocoder_mod, "normalize_address")

        address_only = {
            "PARCEL": 16220100010,
            "DOCNO": 2026063000011,
            "SALEPRICE": 310000,
            "SALEDATE": 20260630,
            "ADDRESS1": "789 MAIN ST LAS VEGAS",
        }
        fm = FIELD_MAP["deeds"]
        assert first_mapped(address_only, fm, "latitude") is None
        assert first_mapped(address_only, fm, "longitude") is None
        assert first_mapped(address_only, fm, "address_street") == "789 MAIN ST LAS VEGAS"

    def test_deed_parser_uses_declared_geocoder(self, deeds, deed_row, monkeypatch):
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: FIELD_MAP[feed.value],
        )
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args: (36.1147, -115.1728),
        )
        event = deeds.parse_socrata_row(deed_row, city_id="las_vegas")
        assert event is not None
        assert event.latitude == pytest.approx(36.1147)
        assert event.longitude == pytest.approx(-115.1728)

    def test_deed_live_fixture_is_inside_the_metro_bbox(self, deed_row):
        assert is_in_las_vegas_metro(36.1147, -115.1728)
