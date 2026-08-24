"""Contract tests for Kansas City, MO (311 only, HJ-120)."""

from unittest.mock import patch

import pytest

from src.spatial.cities.kansas_city import (
    KANSAS_CITY_DIVISION_BBOXES,
    KANSAS_CITY_DIVISIONS,
    KANSAS_CITY_METRO_BBOX,
    KANSAS_CITY_SUBMARKETS,
    is_in_kansas_city_metro,
)
from src.spatial.city_registry import CityId, FeedType

# The exact field_map the HJ-120 registration carries. Parser tests below
# inject it via patch() so they pass before the spine lands; the
# registration test pins the registry to this same literal so the two can
# never drift.
KC_SPEC_FIELD_MAP = {
    "incident_id": ["reported_issue"],
    "complaint_type": ["issue_type"],
    "created_date": ["open_date_time"],
    "status": ["current_status"],
}


def test_kansas_city_geometry_is_self_consistent():
    assert is_in_kansas_city_metro(39.1000, -94.5800)  # downtown
    assert is_in_kansas_city_metro(39.1151, -94.5125)  # Northland live row
    assert is_in_kansas_city_metro(38.9220, -94.5400)  # south KC live row
    assert not is_in_kansas_city_metro(38.6270, -90.1994)  # St. Louis
    assert not is_in_kansas_city_metro(39.0473, -95.6752)  # Topeka
    assert not is_in_kansas_city_metro(None, None)
    for name, bbox in KANSAS_CITY_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= KANSAS_CITY_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= KANSAS_CITY_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= KANSAS_CITY_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= KANSAS_CITY_METRO_BBOX["max_lng"], name
    claimed = [name for division in KANSAS_CITY_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(KANSAS_CITY_SUBMARKETS)
    assert {meta.city_id for meta in KANSAS_CITY_SUBMARKETS.values()} == {"kansas_city"}
    # Every submarket anchor sits inside its claiming division bbox.
    for meta in KANSAS_CITY_SUBMARKETS.values():
        bbox = KANSAS_CITY_DIVISION_BBOXES[meta.borough]
        assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], meta.name
        assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], meta.name


def test_kansas_city_registers_311_only():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.KANSAS_CITY
    assert normalize_city("kcmo") is city
    assert normalize_city("kansas_city") is city
    assert normalize_city("kc_mo") is city
    assert REGISTRY[city].job_suffix == "kcmo"
    assert set(REGISTRY[city].datasets) == {FeedType.COMPLAINTS_311}

    c311 = REGISTRY[city].datasets[FeedType.COMPLAINTS_311]
    assert c311.watermark_col == "open_date_time"
    # G11: publishes every day (14/14 days with rows at the 2026-08-24 probe),
    # intraday timestamps -- daily-ish cadence, standard alarm window.
    assert c311.extra["expected_cadence_days"] == 7
    assert c311.extra["field_map"] == KC_SPEC_FIELD_MAP

    # HJ-120 exclusions: KC permits survive only as dead annual archives
    # (2019-2023), and the SLA table pnm4-68wg has no date column at all --
    # registering either would page G5 forever.
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.PERMITS)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.SLA)


KC_311_ROW = {
    # Live newest row via REST on 2026-08-24 ($order=open_date_time DESC).
    "reported_issue": "3391823",
    "workorder_": "NPD-2026-14488",
    "current_status": "new",
    "open_date_time": "2026-08-24T11:07:00.000",
    "days_to_close": "0",
    "report_source": "iOS",
    "issue_type": "Property Violations",
    "issue_sub_type": "Weeds",
    "department_work_group": "NHS Preservation",
    "incident_address": "11204 Kensington Ave Kansas City 64137",
    "latitude": "38.921979",
    "longitude": "-94.540024",
    "lat_long": {"type": "Point", "coordinates": [-94.540024, 38.921979]},
    "additional_questions": '{Is this private property (not owned by the City| Land Bank| or Homesteading Authority)?":"Yes"}"',
    "last_updated": "2026-08-24T11:07:39.000",
    "council_district": "6",
    "source_category": "Public (External)",
}

KC_311_ROW_SECOND = {
    # Live third-newest row via REST on 2026-08-24.
    "reported_issue": "3391820",
    "current_status": "new",
    "open_date_time": "2026-08-24T11:06:00.000",
    "days_to_close": "0",
    "report_source": "Phone Answered",
    "issue_type": "Recycling Cart Program",
    "issue_sub_type": "Cart Needed - Did Not Receive A Recycling Cart",
    "department_work_group": "PW Solid Waste",
    "incident_address": "10805 Bennington Ave Kansas City 64134",
    "latitude": "38.9281968665192",
    "longitude": "-94.5131985555721",
    "lat_long": {"type": "Point", "coordinates": [-94.5131985555721, 38.9281968665192]},
    "additional_questions": '{Number of Carts - Each valid dwelling unit was to receive one cart":"1 cart"|'
    '"Is this a Multi-Family?":"NO"}',
    "last_updated": "2026-08-24T11:06:00.000",
    "council_district": "5",
    "source_category": "Staff (Internal)",
}


class TestKansasCity311Parsing:
    @pytest.fixture
    def complaints(self):
        with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
            from src.producers.complaints_311_producer import Complaints311Producer

            return Complaints311Producer()

    @pytest.fixture
    def field_map_active(self):
        """Stand in for the registry's field_map until the spine lands.

        parse_socrata_row resolves the map through city_registry at call
        time; pre-registration that lookup degrades to {}. Injecting the
        spec literal here keeps parser behavior identical pre- and
        post-spine, and test_kansas_city_registers_311_only pins the
        registered map to the same dict.
        """
        with patch(
            "src.producers.field_maps.resolve_field_map",
            return_value=dict(KC_SPEC_FIELD_MAP),
        ):
            yield

    def test_newest_live_row_parses_through_field_map(self, complaints, field_map_active):
        event = complaints.parse_socrata_row(dict(KC_311_ROW), city_id="kansas_city")
        assert event is not None
        assert event.city_id == "kansas_city"
        assert event.incident_id == "3391823"  # field_map incident_id <- reported_issue
        assert event.complaint_type == "Property Violations"  # complaint_type <- issue_type
        assert event.status == "new"  # status <- current_status
        # created_date <- open_date_time (naive ISO with millis, parsed as-is)
        assert event.created_date is not None
        assert (event.created_date.year, event.created_date.month, event.created_date.day) == (2026, 8, 24)
        assert (event.created_date.hour, event.created_date.minute) == (11, 7)
        # lat/lon passthrough: top-level strings float()ed by the chain
        assert event.latitude == pytest.approx(38.921979)
        assert event.longitude == pytest.approx(-94.540024)
        # address rides the generic incident_address chain; no zip column
        assert event.incident_address == "11204 Kensington Ave Kansas City 64137"
        assert event.zipcode == ""
        # issue_sub_type has no budget for a descriptor mapping: chains miss it
        assert event.descriptor is None

    def test_second_live_row_parses(self, complaints, field_map_active):
        event = complaints.parse_socrata_row(dict(KC_311_ROW_SECOND), city_id="kansas_city")
        assert event is not None
        assert event.incident_id == "3391820"
        assert event.complaint_type == "Recycling Cart Program"
        assert event.status == "new"
        assert event.latitude == pytest.approx(38.9281968665192)

    def test_missing_reported_issue_returns_none(self, complaints, field_map_active):
        row = dict(KC_311_ROW)
        row.pop("reported_issue")
        # No chain fallback spells reported_issue; without the map entry
        # every row would drop, which is why it leads the field_map.
        assert complaints.parse_socrata_row(row, city_id="kansas_city") is None

    def test_missing_coordinates_return_none_despite_lat_long_combo(
        self, complaints, field_map_active
    ):
        row = dict(KC_311_ROW)
        row.pop("latitude")
        row.pop("longitude")
        # The lat_long Point combo is NOT consulted by the geometry chains
        # (only point/location/the_geom containers are); geocode-less rows
        # must drop rather than file under a null island cell.
        assert complaints.parse_socrata_row(row, city_id="kansas_city") is None
