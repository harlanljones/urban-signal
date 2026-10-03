"""Unit tests for the Las Vegas (Clark County) leaf — US-145.

Las Vegas registers TWO feed types like Los Angeles and Austin — PERMITS
(Clark County Building Permits, address-only ArcGIS table) and DEEDS (Clark
County parcel sales, a table with no geometry: each sale takes its parcel's
centroid from the city's parcel polygons; the table's address columns are the
owner's mailing address and are never read). SLA / 311 are deliberately absent
for this ticket, so `get_dataset` raises for them once the spine lands.

Per the parallel-streams contract, this leaf test must pass WITHOUT the spine
registry being edited. Registration-dependent assertions therefore skip when
CityId.LAS_VEGAS is absent; everything else (bbox containment, submarket
geometry, field-map mapping, and producer row parsing) is verified against the
leaf modules directly.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.spatial.cities.las_vegas import FIELD_MAP
from src.spatial.cities.las_vegas import (
    LAS_VEGAS_DIVISION_BBOXES,
    LAS_VEGAS_DIVISIONS,
    LAS_VEGAS_METRO_BBOX,
    LAS_VEGAS_PARCEL_POLYGONS,
    LAS_VEGAS_SUBMARKETS,
    is_in_las_vegas_metro,
)
from src.spatial.city_registry import CityId, FeedType

# The spine adds CityId.LAS_VEGAS + REGISTRY entry; until then these tests skip
# rather than fail (the leaf is importable and the rest of the suite is green).
LV = getattr(CityId, "LAS_VEGAS", None)

# The deeds table's owner and mailing-address block, never the parcel's.
OWNER_COLUMNS = {"OWNER", "NAMETAG", "ADDRESS1", "ADDRESS2", "ADDRESS3", "ADDRESS4", "ADDRESS5", "ZIPCODE"}


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

    def test_registered_feed_set_includes_snap_sla(self):
        _skip_if_no_spine()
        assert set(_registry()[LV].datasets) == {
            FeedType.PERMITS,
            FeedType.DEEDS,
            FeedType.CRIME,
            FeedType.SLA,
        }

    def test_absent_feeds_raise_readable_errors(self):
        from src.spatial.city_registry import get_dataset

        _skip_if_no_spine()
        with pytest.raises(KeyError, match=r"'las_vegas'.*no.*feed.*available"):
            get_dataset(LV, FeedType.COMPLAINTS_311)

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
            "ZIP": 89108,
            "ADDRESS1": "REDACTED",
            "ZIPCODE": 913012345,
        }
        assert first_mapped(deed_row, fm, "doc_id") == 2016031102044
        assert first_mapped(deed_row, fm, "bbl") == 13824217021
        assert first_mapped(deed_row, fm, "document_amount") == 425000
        assert first_mapped(deed_row, fm, "recorded_date") == 20260801
        assert first_mapped(deed_row, fm, "zipcode") == 89108
        assert first_mapped(deed_row, fm, "address_street") is None

    def test_deeds_map_no_owner_or_mailing_column(self):
        mapped = {column for candidates in FIELD_MAP["deeds"].values() for column in candidates}
        assert not mapped & OWNER_COLUMNS


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
        # A sale as poll_job hands it over: the parcel join has added the
        # centroid of PARCEL's polygon.
        return {
            "PARCEL": 13824217021,
            "DOCNO": 2016031102044,
            "SALEPRICE": 425000,
            "SALEDATE": 20260801,
            "ZIP": 89108,
            "latitude": 36.1953,
            "longitude": -115.2231,
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

    @pytest.fixture
    def no_geocoding(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "src.producers.field_maps.resolve_field_map",
            lambda city, feed: FIELD_MAP[feed.value],
        )
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args: calls.append(args) or (36.1147, -115.1728),
        )
        return calls

    def test_deed_parses_with_field_map(self, deeds, deed_row, no_geocoding):
        ev = deeds.parse_socrata_row(deed_row, city_id="las_vegas")
        assert ev is not None
        assert ev.doc_id == "2016031102044"
        assert ev.bbl == "13824217021"
        assert ev.document_amount == 425000.0
        assert str(ev.recorded_date).startswith("2026-08-01")

    def test_deed_takes_its_parcel_centroid(self, deeds, deed_row, no_geocoding):
        ev = deeds.parse_socrata_row({**deed_row, "ADDRESS1": "REDACTED", "ZIPCODE": 913012345}, city_id="las_vegas")
        assert ev.latitude == pytest.approx(36.1953)
        assert ev.longitude == pytest.approx(-115.2231)
        assert ev.h3_res9 is not None
        assert no_geocoding == []

    def test_a_sale_the_join_missed_is_never_geocoded(self, deeds, deed_row, no_geocoding):
        """The table's address columns hold the owner's mailing address, so a
        sale whose parcel has no polygon stays unplaced rather than landing
        wherever its owner lives."""
        unplaced = {k: v for k, v in deed_row.items() if k not in ("latitude", "longitude")}
        ev = deeds.parse_socrata_row({**unplaced, "ADDRESS1": "REDACTED"}, city_id="las_vegas")
        assert ev is not None
        assert ev.latitude is None
        assert ev.h3_res9 is None
        assert no_geocoding == []

    def test_deeds_join_parcel_polygons_and_leave_the_owner_on_the_server(self):
        _skip_if_no_spine()
        from src.spatial.city_registry import get_dataset

        spec = get_dataset(LV, FeedType.DEEDS)
        assert not spec.needs_geocode
        assert spec.parcel_join == {
            "parcel_layer": LAS_VEGAS_PARCEL_POLYGONS,
            "join_key": "PARCEL",
            "geometry_source": "centroid",
        }
        assert not set(spec.select.split(",")) & OWNER_COLUMNS

    def test_deed_live_fixture_is_inside_the_metro_bbox(self, deed_row):
        assert is_in_las_vegas_metro(deed_row["latitude"], deed_row["longitude"])
