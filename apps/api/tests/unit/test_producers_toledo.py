"""Contract tests for Toledo, OH (ArcGIS Cityworks 311 — US-359).

The Engage Toledo / Cityworks extract is Toledo's only Tier-1 feed. Fixtures
are the newest-by-``INIT_DATE`` rows re-probed live on 2026-08-27 23:04 UTC
from ``Public/CityWorks_ServiceRequest_2022/MapServer/0`` (``outSR=4326``) and
flattened exactly as ``ArcGISClient._flatten_feature`` delivers them.

Toledo is NOT registered yet (spine lands the CityId/REGISTRY entry), so
every parse test uses the plain string ``city_id="toledo"`` and no test may
import ``CityId`` for it or assert REGISTRY contents.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_toledo import (
    COMPLAINTS_311_FIELD_MAP,
    DROPPED_PII_COLUMNS,
    GEOCODE_CONTEXT,
)
from src.spatial.cities.toledo import (
    TOLEDO_DIVISION_BBOXES,
    TOLEDO_DIVISIONS,
    TOLEDO_METRO_BBOX,
    TOLEDO_SUBMARKETS,
    is_in_toledo_metro,
)

# Live newest-by-INIT_DATE row (REQUEST_ID 796129) via REST on 2026-08-27:
# "Structure Concern (Property Maintenance, Vehicles)", 2550 Cherry St.
# INIT_DATE 1787869209000 = 2026-08-27 22:20:09 UTC. X_COORD/Y_COORD are
# Web Mercator meters — never to be read as degrees.
TOLEDO_311_ROW = {
    "TYPE": "REQUEST",
    "REQUEST_ID": 796129,
    "DESCRIPTION": "Structure Concern (Property Maintenance, Vehicles)",
    "INIT_DATE": 1787869209000,
    "INIT_BY": "SEECLICKFIX,",
    "PROBZIP": "43608",
    "SUBMITTO": "SUBMIT, CODENF",
    "DISPATCHTO": "CE, INSPECTOR",
    "INVT_DATE": None,
    "CLOSED_DATE": None,
    "STATUS": "CANCEL",
    "RESOLUTION": "Property Owner Responsible",
    "LOCATION": "2550 CHERRY ST,  TOLEDO,  OH,  43608",
    "X_COORD": -9300049.824,
    "Y_COORD": 5112091.638,
    "DISTRICT": "4",
}
TOLEDO_311_GEOMETRY = {"x": -83.54376899972264, "y": 41.67279899966971}

# Second live row (REQUEST_ID 796127), same-day 22:14:35 UTC: identical
# structure-concern family, clean in-city WGS84 geometry.
TOLEDO_311_ROW_2 = {
    "TYPE": "REQUEST",
    "REQUEST_ID": 796127,
    "DESCRIPTION": "Structure Concern (Property Maintenance, Vehicles)",
    "INIT_DATE": 1787868875000,
    "INIT_BY": "SEECLICKFIX,",
    "PROBZIP": "43609",
    "SUBMITTO": "SUBMIT, CODENF",
    "DISPATCHTO": "CE, INSPECTOR",
    "INVT_DATE": None,
    "CLOSED_DATE": None,
    "STATUS": "IP",
    "RESOLUTION": "",
    "LOCATION": "721 WILLIAMSVILLE AVE,  TOLEDO,  OH,  43609",
    "X_COORD": -9308501.144,
    "Y_COORD": 5105210.649,
    "DISTRICT": "1",
}
TOLEDO_311_GEOMETRY_2 = {"x": -83.6196884989925, "y": 41.62661099715801}

# The NEWEST watermark row (REQUEST_ID 796130, 2026-08-27 23:04:37 UTC). Its
# outSR=4326 geometry comes back as a corrupted non-geographic point
# (15.04, 6.67) while X_COORD/Y_COORD are Ohio State Plane FEET (1.67M/0.74M)
# — a different projection from the two rows above. Both facts are why the
# map never reads X_COORD/Y_COORD and why LOCATION is the needs_geocode path.
TOLEDO_311_ROW_BROKEN = {
    "TYPE": "REQUEST",
    "REQUEST_ID": 796130,
    "DESCRIPTION": "Blight Concern (Debris, Trash, or Dumping)",
    "INIT_DATE": 1787871877000,
    "INIT_BY": "SEECLICKFIX,",
    "PROBZIP": "43612",
    "SUBMITTO": "SUBMIT, CODENF",
    "DISPATCHTO": "CE, INSPECTOR",
    "INVT_DATE": None,
    "CLOSED_DATE": None,
    "STATUS": "IP",
    "RESOLUTION": "",
    "LOCATION": "1469 Bradmore Dr",
    "X_COORD": 1674098.70829158,
    "Y_COORD": 744532.24326187,
    "DISTRICT": None,
}
TOLEDO_311_GEOMETRY_BROKEN = {"x": 15.038684567830746, "y": 6.673109084720405}


def _flatten(row: dict, geometry: dict) -> dict:
    """Run a raw ArcGIS feature through the production flattener so parser tests
    see exactly what Complaints311Producer.parse_socrata_row sees after paginate."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        {"attributes": dict(row), "geometry": geometry},
        date_fields={"INIT_DATE", "INVT_DATE", "CLOSED_DATE"},
    )


class TestToledoSpatial:
    def test_geometry_is_self_consistent(self):
        assert is_in_toledo_metro(41.6528, -83.5379)  # Downtown
        assert is_in_toledo_metro(41.7150, -83.4900)  # Point Place
        assert is_in_toledo_metro(41.6689, -83.6370)  # Ottawa Hills
        assert not is_in_toledo_metro(35.1495, -90.0490)  # Memphis, TN
        assert not is_in_toledo_metro(41.5030, -81.6944)  # Cleveland, OH
        assert not is_in_toledo_metro(None, None)

    def test_live_fixture_rows_sit_inside_the_metro_bbox(self):
        assert is_in_toledo_metro(TOLEDO_311_GEOMETRY["y"], TOLEDO_311_GEOMETRY["x"])
        assert is_in_toledo_metro(TOLEDO_311_GEOMETRY_2["y"], TOLEDO_311_GEOMETRY_2["x"])

    def test_corrupted_newest_row_geometry_is_outside_the_metro(self):
        # The newest watermark row (796130) served outSR=4326 as (15.04, 6.67):
        # a corrupted stored point, not Toledo. The producer's abs() guard only
        # clears >90/>180, so these in-range values pass parse — the metro
        # bbox is the corrective that drops them downstream.
        assert (
            is_in_toledo_metro(
                TOLEDO_311_GEOMETRY_BROKEN["y"], TOLEDO_311_GEOMETRY_BROKEN["x"]
            )
            is False
        )

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in TOLEDO_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= TOLEDO_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= TOLEDO_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= TOLEDO_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= TOLEDO_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in TOLEDO_SUBMARKETS.items():
            bbox = TOLEDO_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in TOLEDO_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(TOLEDO_SUBMARKETS)
        assert {m.city_id for m in TOLEDO_SUBMARKETS.values()} == {"toledo"}
        assert {m.borough for m in TOLEDO_SUBMARKETS.values()} == set(TOLEDO_DIVISIONS)


class TestFieldMap:
    def test_map_reads_live_columns(self):
        row = TOLEDO_311_ROW
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "incident_id") == 796129
        assert (
            first_mapped(row, COMPLAINTS_311_FIELD_MAP, "complaint_type")
            == "Structure Concern (Property Maintenance, Vehicles)"
        )
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "created_date") == 1787869209000
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "closed_date") is None
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "status") == "CANCEL"
        assert (
            first_mapped(row, COMPLAINTS_311_FIELD_MAP, "incident_address")
            == "2550 CHERRY ST,  TOLEDO,  OH,  43608"
        )
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "zipcode") == "43608"
        assert first_mapped(row, COMPLAINTS_311_FIELD_MAP, "borough") == "4"

    def test_watermark_is_init_date_only(self):
        # CLOSED_DATE is nullable on open rows — never a created/cadence anchor.
        assert COMPLAINTS_311_FIELD_MAP["created_date"] == ["INIT_DATE"]
        assert COMPLAINTS_311_FIELD_MAP["closed_date"] == ["CLOSED_DATE"]

    def test_map_never_reads_projected_or_pii_columns(self):
        mapped = {c for cols in COMPLAINTS_311_FIELD_MAP.values() for c in cols}
        assert "X_COORD" not in mapped
        assert "Y_COORD" not in mapped
        for col in DROPPED_PII_COLUMNS:
            assert col not in mapped, col
        assert "INIT_BY" in DROPPED_PII_COLUMNS
        # Native coordinates arrive via the outSR=4326 geometry lift, not attributes.
        assert "latitude" not in COMPLAINTS_311_FIELD_MAP
        assert "longitude" not in COMPLAINTS_311_FIELD_MAP
        assert "X_COORD" in TOLEDO_311_ROW and "Y_COORD" in TOLEDO_311_ROW

    def test_geocode_context_is_toledo_oh(self):
        assert GEOCODE_CONTEXT == "Toledo, OH"


def _patch_resolve(monkeypatch):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: COMPLAINTS_311_FIELD_MAP,
    )


@pytest.fixture
def complaints():
    with patch("src.producers.complaints_311_producer.BaseKafkaProducer"):
        from src.producers.complaints_311_producer import Complaints311Producer

        yield Complaints311Producer()


class TestToledo311Parsing:
    def test_native_outsr_geometry_used_not_mercator_xy(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        with patch(
            "src.spatial.geocoder.geocode_row_if_declared",
            return_value=(0.0, 0.0),
        ) as geocode:
            event = complaints.parse_socrata_row(
                _flatten(TOLEDO_311_ROW, TOLEDO_311_GEOMETRY), city_id="toledo"
            )
        assert event is not None
        assert event.city_id == "toledo"
        assert event.incident_id == "796129"
        assert event.complaint_type == "Structure Concern (Property Maintenance, Vehicles)"
        assert event.incident_address == "2550 CHERRY ST,  TOLEDO,  OH,  43608"
        assert event.zipcode == "43608"
        assert event.status == "CANCEL"
        assert event.latitude == pytest.approx(41.67279899966971)
        assert event.longitude == pytest.approx(-83.54376899972264)
        assert event.latitude != 5112091.638
        assert event.longitude != -9300049.824
        geocode.assert_not_called()

    def test_second_live_row_parses_same_day(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        event = complaints.parse_socrata_row(
            _flatten(TOLEDO_311_ROW_2, TOLEDO_311_GEOMETRY_2), city_id="toledo"
        )
        assert event is not None
        assert event.incident_id == "796127"
        assert event.complaint_type == "Structure Concern (Property Maintenance, Vehicles)"
        assert str(event.created_date).startswith("2026-08-27")

    def test_created_date_from_init_date_and_closed_nullable(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        event = complaints.parse_socrata_row(
            _flatten(TOLEDO_311_ROW, TOLEDO_311_GEOMETRY), city_id="toledo"
        )
        assert str(event.created_date) == "2026-08-27 22:20:09+00:00"
        assert event.closed_date is None

    def test_closed_date_parses_when_present(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        row = dict(TOLEDO_311_ROW, CLOSED_DATE=TOLEDO_311_ROW["INIT_DATE"] + 3_600_000)
        event = complaints.parse_socrata_row(
            _flatten(row, TOLEDO_311_GEOMETRY), city_id="toledo"
        )
        assert event is not None
        assert str(event.closed_date) == "2026-08-27 23:20:09+00:00"

    def test_address_only_row_geocodes_location_supplement(
        self, complaints, monkeypatch
    ):
        _patch_resolve(monkeypatch)
        row = _flatten(TOLEDO_311_ROW, {})
        row.pop("latitude", None)
        row.pop("longitude", None)
        captured = []

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address, context))
            return (41.67279899966971, -83.54376899972264)

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        event = complaints.parse_socrata_row(row, city_id="toledo")
        assert event is not None
        assert event.latitude == pytest.approx(41.67279899966971)
        assert event.longitude == pytest.approx(-83.54376899972264)
        assert captured == [
            ("toledo", "311", "2550 CHERRY ST,  TOLEDO,  OH,  43608", None)
        ]

    def test_mercator_xy_without_geometry_never_emitted_as_degrees(
        self, complaints, monkeypatch
    ):
        _patch_resolve(monkeypatch)
        row = _flatten(TOLEDO_311_ROW, {})
        row.pop("latitude", None)
        row.pop("longitude", None)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (41.6728, -83.5438),
        )
        event = complaints.parse_socrata_row(row, city_id="toledo")
        assert event is not None
        assert event.latitude == pytest.approx(41.6728)
        assert event.longitude == pytest.approx(-83.5438)
        assert event.latitude != 5112091.638
        assert event.longitude != -9300049.824

    def test_newest_row_broken_geometry_resolves_from_location_not_xy(
        self, complaints, monkeypatch
    ):
        # The newest watermark row (796130) has corrupted outSR=4326 geometry
        # AND State Plane FEET X_COORD/Y_COORD. The address-only path must be
        # the coordinate source; neither projected variant may surface.
        _patch_resolve(monkeypatch)
        row = _flatten(TOLEDO_311_ROW_BROKEN, TOLEDO_311_GEOMETRY_BROKEN)
        row.pop("latitude", None)
        row.pop("longitude", None)
        captured = []

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address, context))
            return (41.6654, -83.5304)

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        event = complaints.parse_socrata_row(row, city_id="toledo")
        assert event is not None
        assert event.incident_id == "796130"
        assert event.latitude == pytest.approx(41.6654)
        assert event.longitude == pytest.approx(-83.5304)
        assert event.latitude != 744532.24326187
        assert event.longitude != 1674098.70829158
        assert event.latitude != TOLEDO_311_GEOMETRY_BROKEN["y"]
        assert event.longitude != TOLEDO_311_GEOMETRY_BROKEN["x"]
        assert captured == [("toledo", "311", "1469 Bradmore Dr", None)]

    def test_h3_hierarchy_indexed(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        event = complaints.parse_socrata_row(
            _flatten(TOLEDO_311_ROW, TOLEDO_311_GEOMETRY), city_id="toledo"
        )
        assert event is not None
        assert event.h3_res7 == "872a94d23ffffff"
        assert event.h3_res8 == "882a94d23dfffff"
        assert event.h3_res9 == "892a94d23dbffff"

    def test_second_live_row_h3(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        event = complaints.parse_socrata_row(
            _flatten(TOLEDO_311_ROW_2, TOLEDO_311_GEOMETRY_2), city_id="toledo"
        )
        assert event is not None
        assert event.h3_res7 == "872a94d02ffffff"
        assert event.h3_res8 == "882a94d027fffff"
        assert event.h3_res9 == "892a94d026bffff"

    def test_classification_buckets(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        from src.schemas.models import ComplaintCategory

        def parse(description):
            row = dict(TOLEDO_311_ROW, DESCRIPTION=description)
            return complaints.parse_socrata_row(
                _flatten(row, TOLEDO_311_GEOMETRY), city_id="toledo"
            )

        assert parse("Structure Concern (Property Maintenance, Vehicles)").category is ComplaintCategory.OTHER
        assert parse("Blight Concern (Debris, Trash, or Dumping)").category is ComplaintCategory.OTHER
        assert parse("Noise Concern (barking dog, loud music)").category is ComplaintCategory.QOL
        assert parse("Street Pothole Concern").category is ComplaintCategory.NEGLECT
        assert parse("Water Leak Inside Concern").category is ComplaintCategory.NEGLECT

    def test_borough_falls_back_to_source_district(self, complaints, monkeypatch):
        # Post-spine: toledo is registered, so coordinate division resolution
        # is live. The Cityworks DISTRICT stays as source_neighborhood; the
        # coordinates resolve into the DOWNTOWN_RIVERFRONT division.
        _patch_resolve(monkeypatch)
        event = complaints.parse_socrata_row(
            _flatten(TOLEDO_311_ROW, TOLEDO_311_GEOMETRY), city_id="toledo"
        )
        assert event is not None
        assert event.source_neighborhood == "4"
        assert event.borough == "DOWNTOWN_RIVERFRONT"

    def test_null_district_stays_null_source(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (41.6654, -83.5304),
        )
        event = complaints.parse_socrata_row(
            _flatten(TOLEDO_311_ROW_BROKEN, {}), city_id="toledo"
        )
        assert event is not None
        assert event.source_neighborhood is None
        assert event.borough == "DOWNTOWN_RIVERFRONT"

    def test_missing_request_id_drops_the_row(self, complaints, monkeypatch):
        _patch_resolve(monkeypatch)
        row = {k: v for k, v in TOLEDO_311_ROW.items() if k != "REQUEST_ID"}
        assert complaints.parse_socrata_row(
            _flatten(row, TOLEDO_311_GEOMETRY), city_id="toledo"
        ) is None


class TestLeafFeedSpec:
    """The spec the spine copies into REGISTRY — pinned leaf-locally."""

    def test_311_spec_shape(self):
        from src.spatial.cities.toledo import get_toledo_dataset
        from src.spatial.city_registry import FeedType

        spec = get_toledo_dataset(FeedType.COMPLAINTS_311)
        assert spec.platform == "arcgis"
        assert spec.endpoint.endswith(
            "/Public/CityWorks_ServiceRequest_2022/MapServer/0"
        )
        assert spec.watermark_col == "INIT_DATE"
        assert spec.id_keys == ["REQUEST_ID"]
        assert spec.interval_seconds == 300.0
        assert spec.producer_key == "311"
        assert spec.expected_cadence_days == 1
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Toledo, OH"
        assert spec.oid_field == "REQUEST_ID"
        assert spec.max_record_count == 2000
        assert spec.order_by == "INIT_DATE DESC"
        assert spec.field_map == COMPLAINTS_311_FIELD_MAP

    def test_no_other_feeds_are_registered(self):
        from src.spatial.cities.toledo import get_toledo_dataset
        from src.spatial.city_registry import FeedType

        for feed in (FeedType.PERMITS, FeedType.SLA, FeedType.DEEDS):
            with pytest.raises(KeyError, match="no.*feed"):
                get_toledo_dataset(feed)