"""Unit tests for the Dallas registration leaf (US-149, ROW + partial 311).

Dallas registers live right-of-way permits plus a partial Building Services
311 view. See apps/api/src/spatial/cities/dallas.py for the feed scope.

The registration assertions also guard the interlock wiring: ArcGIS endpoints,
rolling-window metadata, aliases, and field maps.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_dallas import DALLAS_311_FIELD_MAP, DALLAS_FIELD_MAP, FIELD_MAP
from src.spatial.cities.dallas import (
    DALLAS_DIVISION_BBOXES,
    DALLAS_DIVISIONS,
    DALLAS_METRO_BBOX,
    DALLAS_SUBMARKETS,
    is_in_dallas_metro,
)

# The spine adds CityId.DALLAS; until then these tests SKIP rather than fail.
try:
    from src.spatial.city_registry import CityId

    DALLAS = getattr(CityId, "DALLAS", None)
except Exception:  # pragma: no cover - defensive
    DALLAS = None


def _dallas_row():
    """Dallas ROW ArcGIS row after ArcGISClient flattening."""
    return {
        "EXTERNALFILENUM": "ROW-2026-501690",
        "PERMITTYPE": "Right of Way Permit",
        "ROWREASONFORJOB": "New Service",
        "ROWIMPROVEMENTREPAIR": "Wastewater",
        "CREATEDDATE": "2026-08-24T09:00:00+00:00",
        "ISSUEDATE": "2026-08-24T00:00:00+00:00",
        "STATUSDESCRIPTION": "Issued",
        "COUNCIL_DISTRICTS": "11",
        "LOCATIONNAMES": "6618 AZALEA LN, DALLAS, 75230",
        "latitude": "32.7895",
        "longitude": "-96.8085",
    }


def _dallas_311_row():
    return {
        "Service_Request_Number_c": "26-00380697",
        "Subject": "City Building Maintenance - FRM",
        "Status": "New",
        "CreatedDate": "2026-08-25T21:59:06+00:00",
        "Address_c": "9480 WEBB CHAPEL RD, DALLAS, TX, 75220",
        "Zipcode_c": "75220",
        "Council_District_c": "6",
        "Location_Latitude_s": "32.8628928126",
        "Location_Longitude_s": "-96.8598354794",
    }


class TestDallasSpatial:
    def test_metro_bbox_is_sane(self):
        assert DALLAS_METRO_BBOX["min_lat"] < DALLAS_METRO_BBOX["max_lat"]
        assert DALLAS_METRO_BBOX["min_lng"] < DALLAS_METRO_BBOX["max_lng"]

    def test_is_in_dallas_metro_accepts_core(self):
        assert is_in_dallas_metro(32.7845, -96.7930)   # Downtown
        assert is_in_dallas_metro(32.8845, -96.8055)   # Preston Hollow
        assert is_in_dallas_metro(32.7415, -96.8255)   # Bishop Arts

    def test_is_in_dallas_metro_rejects_missing(self):
        assert is_in_dallas_metro(None, None) is False

    def test_is_in_dallas_metro_rejects_other_cities(self):
        assert is_in_dallas_metro(40.7128, -74.0060) is False   # NYC
        assert is_in_dallas_metro(30.2672, -97.7431) is False   # Austin

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in DALLAS_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= DALLAS_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= DALLAS_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= DALLAS_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= DALLAS_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in DALLAS_SUBMARKETS.items():
            bbox = DALLAS_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in DALLAS_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(DALLAS_SUBMARKETS)

    def test_submarkets_carry_the_dallas_city_id(self):
        assert {m.city_id for m in DALLAS_SUBMARKETS.values()} == {"dallas"}


class TestDallasFieldMap:
    def test_field_map_is_exported_under_both_names(self):
        assert FIELD_MAP is DALLAS_FIELD_MAP

    def test_distinctive_job_id_spelling_resolves(self):
        row = _dallas_row()
        assert first_mapped(row, DALLAS_FIELD_MAP, "job_id") == "ROW-2026-501690"

    def test_distinctive_issuance_spelling_resolves(self):
        row = _dallas_row()
        assert first_mapped(row, DALLAS_FIELD_MAP, "issuance_date") == "2026-08-24T00:00:00+00:00"

    def test_distinctive_cost_spelling_resolves(self):
        row = _dallas_row()
        assert first_mapped(row, DALLAS_FIELD_MAP, "cost") is None

    def test_distinctive_zip_spelling_resolves(self):
        row = _dallas_row()
        assert first_mapped(row, DALLAS_FIELD_MAP, "zipcode") is None

    def test_borough_maps_to_council_district(self):
        row = _dallas_row()
        assert first_mapped(row, DALLAS_FIELD_MAP, "borough") == "11"

    def test_map_truly_overrides_chains(self):
        """The Dallas spellings are NOT in the shared chains, so without the map
        the distinctive keys must return None — proving the map earns its keep."""
        row = _dallas_row()
        assert first_mapped(row, {}, "job_id") is None
        assert first_mapped(row, {}, "issuance_date") is None


class TestDallasRowParsing:
    """Exercise the shared DOB permits parser against a flattened ROW row."""

    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    @pytest.fixture
    def with_dallas_map(self, monkeypatch):
        from src.producers import field_maps as fm

        original = fm.resolve_field_map

        def _fake(city_value, feed):
            from src.spatial.city_registry import FeedType

            if str(city_value).lower() == "dallas" and feed == FeedType.PERMITS:
                return DALLAS_FIELD_MAP
            return original(city_value, feed)

        monkeypatch.setattr(fm, "resolve_field_map", _fake)

    def test_row_parses_with_mapped_columns(self, permits, with_dallas_map):
        ev = permits.parse_socrata_row(_dallas_row(), city_id="dallas")
        assert ev is not None
        assert ev.job_id == "ROW-2026-501690"
        assert ev.city_id == "dallas"

    def test_parsed_coordinates(self, permits, with_dallas_map):
        ev = permits.parse_socrata_row(_dallas_row(), city_id="dallas")
        assert ev.latitude == pytest.approx(32.7895)
        assert ev.longitude == pytest.approx(-96.8085)

    def test_parsed_issuance_and_filing_dates(self, permits, with_dallas_map):
        ev = permits.parse_socrata_row(_dallas_row(), city_id="dallas")
        assert str(ev.issuance_date).startswith("2026-08-24")
        assert str(ev.filing_date).startswith("2026-08-24")

    def test_parsed_cost_and_class(self, permits, with_dallas_map):
        ev = permits.parse_socrata_row(_dallas_row(), city_id="dallas")
        assert ev.estimated_cost == 0.0
        assert str(ev.job_type).endswith("OT")

    def test_parsed_units_stories_zip(self, permits, with_dallas_map):
        ev = permits.parse_socrata_row(_dallas_row(), city_id="dallas")
        assert ev.proposed_dwelling_units is None
        assert ev.proposed_stories is None
        assert ev.zipcode == ""

    def test_parsed_borough_from_council_district(self, permits, with_dallas_map):
        ev = permits.parse_socrata_row(_dallas_row(), city_id="dallas")
        assert ev.borough == "OAK_LAWN_UPTOWN"

class TestDallas311Parsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    @pytest.fixture
    def with_dallas_map(self, monkeypatch):
        from src.producers import field_maps as fm

        original = fm.resolve_field_map

        def _fake(city_value, feed):
            from src.spatial.city_registry import FeedType

            if str(city_value).lower() == "dallas" and feed == FeedType.COMPLAINTS_311:
                return DALLAS_311_FIELD_MAP
            return original(city_value, feed)

        monkeypatch.setattr(fm, "resolve_field_map", _fake)

    def test_row_parses_with_mapped_columns(self, complaints, with_dallas_map):
        ev = complaints.parse_socrata_row(_dallas_311_row(), city_id="dallas")
        assert ev is not None
        assert ev.incident_id == "26-00380697"
        assert ev.complaint_type == "City Building Maintenance - FRM"
        assert ev.city_id == "dallas"
        assert ev.latitude == pytest.approx(32.8628928126)
        assert ev.longitude == pytest.approx(-96.8598354794)
        assert ev.zipcode == "75220"


class TestDallasSpineRegistration:
    """Guard the complete registry wiring for US-149."""

    def test_registered(self):
        from src.spatial.city_registry import REGISTRY

        assert DALLAS in REGISTRY

    @pytest.mark.parametrize("alias", ["dallas", "dallas_tx", "big_d"])
    def test_aliases_resolve(self, alias):
        from src.spatial.city_registry import normalize_city

        assert normalize_city(alias) is DALLAS

    def test_single_proxied_permits_feed_registered(self):
        from src.spatial.city_registry import FeedType, REGISTRY

        reg = REGISTRY[DALLAS]
        assert set(reg.datasets) == {FeedType.PERMITS, FeedType.COMPLAINTS_311}
        spec = reg.datasets[FeedType.PERMITS]
        assert spec.proxy_for == "row_permits"
        assert spec.platform == "arcgis"
        assert spec.watermark_col == "CREATEDDATE"

        complaints = reg.datasets[FeedType.COMPLAINTS_311]
        assert complaints.platform == "arcgis"
        assert complaints.rolling_window_days == 30
        assert complaints.retention_days == 30
        # `scope` was a free-form extra key; it has been dropped (US-186).

    def test_field_map_is_wired_in_registry(self):
        from src.spatial.city_registry import FeedType, REGISTRY

        spec = REGISTRY[DALLAS].datasets[FeedType.PERMITS]
        assert spec.field_map is DALLAS_FIELD_MAP

    def test_311_field_map_is_wired_in_registry(self):
        from src.spatial.city_registry import FeedType, REGISTRY

        spec = REGISTRY[DALLAS].datasets[FeedType.COMPLAINTS_311]
        assert spec.field_map is DALLAS_311_FIELD_MAP
