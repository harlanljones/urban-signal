"""Unit tests for the Omaha leaf (US-358): spatial module + field maps.

Omaha is a ONE-FEED PARTIAL metro: the Mayor's Hotline (Omaha 311) Cityworks
extract on the DCGIS ArcGIS Server (same-day live, native WGS84 points).
Permits / SLA / deeds stay absent. Tests pass WITHOUT a spine registration
(no CityId.OMAHA; city_id strings only).

Live fixtures captured 2026-08-28 from
``dcgis.org/server/rest/services/Cityworks/Mayors_Hotline_Dashboard_Interactive/MapServer/0``
(outSR=4326; leaf re-stamp 2026-08-28: newest DATETIMEINIT same-day 2026-08-27,
648,608 rows total; fixtures OBJECTID 663169/663325 still on top of the
watermark window at re-probe).
"""

import importlib
from unittest.mock import patch

import h3
import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_omaha import (
    COMPLAINTS_311_FIELD_MAP,
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
)
from src.spatial.cities.omaha import (
    OMAHA_311_ENDPOINT,
    OMAHA_CITY_ID,
    OMAHA_DIVISION_BBOXES,
    OMAHA_DIVISIONS,
    OMAHA_FEED_SPECS,
    OMAHA_GEOCODE_CONTEXT,
    OMAHA_METRO_BBOX,
    OMAHA_SUBMARKETS,
    REGISTRATION,
    get_omaha_dataset,
    is_in_omaha_metro,
)
from src.spatial.city_registry import FeedType
from src.spatial.geocoder import _STATE_RE, normalize_address
from src.spatial.submarkets import SubmarketMeta

# Newest rows on the 2026-08-28 re-probe (orderByFields=DATETIMEINIT DESC,
# outFields=*, outSR=4326). DATETIMEINIT is DateOnly ("2026-08-27");
# DATETIMEINITFULL carries the epoch-ms truth. latitude/longitude are the
# ArcGISClient setdefault lifts of the outSR=4326 geometry.
_311_FIXTURE_A = {
    "OBJECTID": 663169,
    "REQUESTID": 663169,
    "PROBLEMCODE": "Tree/Shrub Issue",
    "DESCRIPTION": "Tree/Shrub Issue",
    "DETAILS": "",
    "PROBADDRESS": "15308 Wycliffe Dr, Omaha, NE, 68154",
    "INITIATEDBY": "Citizen, Reporter",
    "SUBMITTO": "PERKUMAS, JOSEPH M",
    "CLOSEDBY": "",
    "DATETIMEINIT": "2026-08-27",
    "DATETIMEINITFULL": 1787807235923,
    "DATETIMECLOSED": None,
    "WORKORDERID": None,
    "SRX": 2697636.96765334,
    "SRY": 543921.29075704,
    "STATUS": "IP",
    "REQCATEGORY": "PRPPCODEENF",
    "ORGANIZATION": "GIS",
    "Request_Init_byOrg": "GIS",
    "Submit_To_byOrg": "PRPPCODE",
    "InitiatedDept": "Omahahotline.com",
    "SubmitToDept": "Parks",
    "latitude": 41.26198229674503,
    "longitude": -96.15215047163026,
}

# Probe-headline row (Illegal Dumping, 6510 S 30th St) still on top of the
# window at the re-stamp.
_311_FIXTURE_B = {
    "OBJECTID": 663325,
    "REQUESTID": 663325,
    "PROBLEMCODE": "Illegal Dumping",
    "DESCRIPTION": "Illegal Dumping",
    "DETAILS": "",
    "PROBADDRESS": "6510 S 30th St, Omaha, NE, 68107",
    "INITIATEDBY": "Citizen, Reporter",
    "SUBMITTO": "Messier, Kirby",
    "CLOSEDBY": "",
    "DATETIMEINIT": "2026-08-27",
    "DATETIMEINITFULL": 1787843839300,
    "DATETIMECLOSED": None,
    "WORKORDERID": None,
    "SRX": 2752099.305277,
    "SRY": 521718.22367198,
    "STATUS": "IP",
    "REQCATEGORY": "PRPPCODEENF",
    "ORGANIZATION": "GIS",
    "Request_Init_byOrg": "GIS",
    "Submit_To_byOrg": "PRPPCODE",
    "InitiatedDept": "Omahahotline.com",
    "SubmitToDept": "Parks",
    "latitude": 41.1942690477236,
    "longitude": -95.95798647656409,
}

# Raw pre-ArcGISClient shape: no lifted geometry, State Plane feet on SRX/SRY.
_311_STATE_PLANE_ONLY = {
    "OBJECTID": 663001,
    "REQUESTID": 663001,
    "PROBLEMCODE": "Pothole Repair",
    "DESCRIPTION": "Pothole Repair",
    "PROBADDRESS": "5001 Dodge St, Omaha, NE, 68132",
    "DATETIMEINIT": "2026-08-26",
    "DATETIMECLOSED": "2026-08-27",
    "STATUS": "CLOSED",
    "SRX": 2691400.0,
    "SRY": 545200.0,
    "SUBMITTO": "SHOULD NOT MAP",
}

_SUBMARKET_FIELDS = (
    "name",
    "borough",
    "lat",
    "lng",
    "zoom",
    "pitch",
    "base_lims",
    "capex",
    "permit_vel",
    "shift_ratio",
    "sla",
    "description",
    "city_id",
)


class TestOmahaSpatial:
    def test_city_id_constant(self):
        assert OMAHA_CITY_ID == "omaha"

    def test_metro_contains_centers_and_live_fixtures(self):
        assert is_in_omaha_metro(41.2580, -95.9370) is True  # Downtown/Old Market
        assert is_in_omaha_metro(41.2710, -96.1700) is True  # West Omaha
        assert is_in_omaha_metro(41.2290, -96.1230) is True  # Millard
        for fixture in (_311_FIXTURE_A, _311_FIXTURE_B):
            assert is_in_omaha_metro(fixture["latitude"], fixture["longitude"])

    def test_metro_rejects_null_foreign_and_iowa_side(self):
        assert is_in_omaha_metro(None, None) is False
        assert is_in_omaha_metro(40.8136, -96.7026) is False  # Lincoln, NE
        assert is_in_omaha_metro(41.5868, -93.6250) is False  # Des Moines, IA
        assert is_in_omaha_metro(41.2619, -95.8622) is False  # Council Bluffs, IA — across the river

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in OMAHA_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= OMAHA_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= OMAHA_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= OMAHA_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= OMAHA_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in OMAHA_SUBMARKETS.items():
            bbox = OMAHA_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in OMAHA_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(OMAHA_SUBMARKETS)

    def test_submarkets_carry_omaha_city_id_and_all_meta_fields(self):
        assert {m.city_id for m in OMAHA_SUBMARKETS.values()} == {"omaha"}
        for name, meta in OMAHA_SUBMARKETS.items():
            assert isinstance(meta, SubmarketMeta), name
            for field in _SUBMARKET_FIELDS:
                value = getattr(meta, field)
                assert value is not None, f"{name}.{field}"
                if field == "description":
                    assert len(value) > 20, name

    def test_division_count_and_centers(self):
        assert 4 <= len(OMAHA_DIVISIONS) <= 8
        for name, meta in OMAHA_DIVISIONS.items():
            assert meta.city_id == "omaha"
            bbox = OMAHA_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_spatial_registration_references_module_constants(self):
        assert REGISTRATION.metro_bbox is OMAHA_METRO_BBOX
        assert REGISTRATION.submarkets is OMAHA_SUBMARKETS
        assert REGISTRATION.divisions is OMAHA_DIVISIONS
        assert REGISTRATION.contains is is_in_omaha_metro

    def test_registration_geometry_fields_present(self):
        module = importlib.import_module("src.spatial.cities.omaha")
        assert hasattr(module, "OMAHA_METRO_BBOX")
        assert hasattr(module, "OMAHA_DIVISION_BBOXES")
        assert hasattr(module, "OMAHA_SUBMARKETS")
        assert hasattr(module, "OMAHA_DIVISIONS")


class TestFeedRegistration:
    def test_exactly_one_feed_type_is_registered(self):
        assert set(OMAHA_FEED_SPECS) == {"311"}

    def test_311_spec_matches_live_layer(self):
        spec = get_omaha_dataset(FeedType.COMPLAINTS_311)
        assert spec.platform == "arcgis"
        assert spec.endpoint == OMAHA_311_ENDPOINT
        assert "Mayors_Hotline_Dashboard_Interactive/MapServer/0" in spec.endpoint
        assert spec.watermark_col == "DATETIMEINIT"
        assert spec.watermark_col != "DATETIMECLOSED"
        assert spec.id_keys == ["OBJECTID", "REQUESTID"]
        assert spec.producer_key == "311"
        assert spec.expected_cadence_days == 1
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Omaha, NE"
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.order_by == "DATETIMEINIT DESC"
        assert spec.field_map is COMPLAINTS_311_FIELD_MAP

    @pytest.mark.parametrize(
        "absent_feed",
        [FeedType.PERMITS, FeedType.SLA, FeedType.DEEDS, FeedType.STR],
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'omaha'.*available"):
            get_omaha_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert set(FIELD_MAP) == {"311"}
        assert FIELD_MAP["311"] is COMPLAINTS_311_FIELD_MAP
        assert GEOCODE_CONTEXT == OMAHA_GEOCODE_CONTEXT == "Omaha, NE"


class TestOmahaFieldMaps:
    def test_311_map_reads_live_columns(self):
        row = _311_FIXTURE_A
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "incident_id") == 663169
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "complaint_type") == "Tree/Shrub Issue"
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "created_date") == "2026-08-27"
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "closed_date") is None
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "status") == "IP"
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "incident_address") == (
            "15308 Wycliffe Dr, Omaha, NE, 68154"
        )

    def test_311_incident_id_falls_back_to_requestid(self):
        row = {"OBJECTID": None, "REQUESTID": 663325}
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "incident_id") == 663325

    def test_311_does_not_map_srx_sry_state_plane_or_closed_as_created(self):
        mapped = {c for cols in COMPLAINTS_311_FIELD_MAP.values() for c in cols}
        assert "SRX" not in mapped
        assert "SRY" not in mapped
        assert "DATETIMEINITFULL" not in mapped
        assert COMPLAINTS_311_FIELD_MAP["created_date"] == ["DATETIMEINIT"]
        assert "latitude" not in COMPLAINTS_311_FIELD_MAP
        assert "longitude" not in COMPLAINTS_311_FIELD_MAP

    def test_311_drops_pii_columns(self):
        mapped = {c for cols in COMPLAINTS_311_FIELD_MAP.values() for c in cols}
        for col in DROPPED_PII_COLUMNS:
            assert col not in mapped, col
        assert first_mapped(_311_FIXTURE_A, COMPLAINTS_311_FIELD_MAP, "incident_address") != (
            "PERKUMAS, JOSEPH M"
        )

    def test_no_zipcode_or_borough_candidates_declared(self):
        # The live layer has no ZIP column (ZIP rides in PROBADDRESS) and no
        # neighborhood column. Declaring none keeps the partial honest.
        assert "zipcode" not in COMPLAINTS_311_FIELD_MAP
        assert "borough" not in COMPLAINTS_311_FIELD_MAP


def _patch_resolve(monkeypatch):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP["311"],
    )


@pytest.fixture
def complaints():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        from src.producers.complaints_311_producer import Complaints311Producer

        return Complaints311Producer()


class TestOmaha311Parsing:
    def test_native_outsr_geometry_used_without_geocoder(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        with patch(
            "src.spatial.geocoder.geocode_row_if_declared",
            return_value=(0.0, 0.0),
        ) as geocode:
            event = complaints.parse_socrata_row(_311_FIXTURE_A, city_id="omaha")
        assert event is not None
        assert event.city_id == "omaha"
        assert event.incident_id == "663169"
        assert event.complaint_type == "Tree/Shrub Issue"
        assert event.incident_address == "15308 Wycliffe Dr, Omaha, NE, 68154"
        assert event.status == "IP"
        assert event.latitude == pytest.approx(41.26198229674503)
        assert event.longitude == pytest.approx(-96.15215047163026)
        geocode.assert_not_called()

    def test_second_fixture_parses_and_stays_inside_the_metro(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        event = complaints.parse_socrata_row(_311_FIXTURE_B, city_id="omaha")
        assert event is not None
        assert event.incident_id == "663325"
        assert event.complaint_type == "Illegal Dumping"
        assert event.latitude == pytest.approx(41.1942690477236)
        assert is_in_omaha_metro(event.latitude, event.longitude)

    def test_h3_hierarchy_is_consistent(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        event = complaints.parse_socrata_row(_311_FIXTURE_A, city_id="omaha")
        assert event is not None
        assert event.h3_res7 and event.h3_res8 and event.h3_res9
        assert h3.cell_to_parent(event.h3_res9, 8) == event.h3_res8
        assert h3.cell_to_parent(event.h3_res9, 7) == event.h3_res7
        latlng = h3.cell_to_latlng(event.h3_res9)
        assert latlng[0] == pytest.approx(41.26198229674503, abs=0.01)
        assert latlng[1] == pytest.approx(-96.15215047163026, abs=0.01)

    def test_state_plane_srx_sry_never_become_degrees(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        captured = []

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address, context))
            return (41.2565, -95.9680)

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        event = complaints.parse_socrata_row(_311_STATE_PLANE_ONLY, city_id="omaha")
        assert event is not None
        assert event.latitude == pytest.approx(41.2565)
        assert event.longitude == pytest.approx(-95.9680)
        assert event.latitude != 545200.0
        assert event.longitude != 2691400.0
        assert captured == [("omaha", "311", "5001 Dodge St, Omaha, NE, 68132", None)]

    def test_probaddress_is_the_geocode_supplement(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        row = {k: v for k, v in _311_FIXTURE_B.items() if k not in {"latitude", "longitude"}}
        with patch(
            "src.spatial.geocoder.geocode_row_if_declared",
            return_value=(41.1942690477236, -95.95798647656409),
        ) as geocode:
            event = complaints.parse_socrata_row(row, city_id="omaha")
        assert event is not None
        assert event.latitude == pytest.approx(41.1942690477236)
        geocode.assert_called_once_with("omaha", "311", "6510 S 30th St, Omaha, NE, 68107")

    def test_created_date_is_datetimeinit_not_datetimeclosed(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        row = {
            **_311_FIXTURE_A,
            "DATETIMECLOSED": "2026-08-28",
        }
        event = complaints.parse_socrata_row(row, city_id="omaha")
        assert event is not None
        assert event.created_date is not None
        assert (event.created_date.year, event.created_date.month, event.created_date.day) == (
            2026,
            8,
            27,
        )
        assert event.closed_date is not None
        assert (event.closed_date.year, event.closed_date.month, event.closed_date.day) == (
            2026,
            8,
            28,
        )

    def test_dateonly_watermark_parses_to_calendar_day(self, complaints, monkeypatch):
        # Leaf finding (spine-delta note): DATETIMEINIT is esriFieldTypeDateOnly
        # and the shared _parse_datetime returns a NAIVE midnight datetime for
        # date-only strings — Omaha is the first DateOnly feed. The UTC
        # coercion fix is spine-owned (complaints_311_producer is not a leaf
        # file), so this test pins the calendar day, not the tzinfo.
        _patch_resolve(monkeypatch)
        event = complaints.parse_socrata_row(_311_FIXTURE_B, city_id="omaha")
        assert event is not None
        assert (event.created_date.year, event.created_date.month, event.created_date.day) == (
            2026,
            8,
            27,
        )
        assert event.closed_date is None  # open row: DATETIMECLOSED null

    def test_pii_never_becomes_address_or_complaint(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        event = complaints.parse_socrata_row(_311_FIXTURE_B, city_id="omaha")
        assert event is not None
        assert "Messier" not in (event.incident_address or "")
        assert "Messier" not in (event.complaint_type or "")
        assert "Citizen, Reporter" not in (event.incident_address or "")

    @pytest.mark.parametrize(
        ("problem_code", "expected"),
        [
            ("Sewage Backup", "NEGLECT"),
            ("Noise Complaint", "QOL"),
            ("Tree/Shrub Issue", "OTHER"),
            ("Illegal Dumping", "OTHER"),
        ],
    )
    def test_category_classification_sanity(
        self, complaints, monkeypatch, problem_code, expected
    ):
        _patch_resolve(monkeypatch)
        row = {**_311_FIXTURE_A, "PROBLEMCODE": problem_code}
        event = complaints.parse_socrata_row(row, city_id="omaha")
        assert event is not None
        assert event.category.value == expected

    def test_zipcode_absent_on_live_layer(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        event = complaints.parse_socrata_row(_311_FIXTURE_A, city_id="omaha")
        assert event is not None
        assert event.zipcode == ""


class TestGeocodingCaveats:
    def test_probaddress_carries_state_token_so_no_context_append(self):
        # PROBADDRESS embeds ", Omaha, NE," so ADR-0004 appends no context —
        # the raw string is already geocoder-complete.
        assert _STATE_RE.search("15308 Wycliffe Dr, Omaha, NE, 68154".upper()) is not None
        assert _STATE_RE.search("6510 S 30th St, Omaha, NE, 68107".upper()) is not None

    def test_normalize_address_preserves_city_and_zip(self):
        norm = normalize_address("15308 Wycliffe Dr, Omaha, NE, 68154")
        assert "OMAHA" in norm
        assert "NE" in norm
        assert "68154" in norm
