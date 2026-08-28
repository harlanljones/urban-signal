"""Unit tests for the Inland Empire leaf (US-222): spatial module, field
maps, and producer parse wiring.

The Inland Empire registration is anchored on Riverside County, CA (the
miami_dade county exception) and is a TWO-FEED PARTIAL metro:

* PERMITS — Riverside County Accela ``PLUS_ACTIVITIES``
  (``gis.countyofriverside.us/arcgis_mapping/rest/services/OpenData/General/
  MapServer/280``, ``where=CASE_MODULE = 'PERMIT'``, watermark
  ``APPLIED_DATE``, state-plane parcel polygons reprojected server-side via
  ``outSR=4326``).
* CRIME — City of Riverside ``View_CrimesRPD/FeatureServer/4`` (watermark
  ``offendate``, native WGS84 point geometry + BLOCK_ADDRESS per ADR 0004).

311, SLA, and DEEDS stay unregistered (none exist in either county or the
city org — see the city module docstring).

Tests pass WITHOUT a spine registration (no CityId.INLAND_EMPIRE, no REGISTRY
assertions — "inland_empire" stays a plain string). Spine-stable per the
wave-5 leaf contract: no division/borough-resolution assertions and no
geocode-hook call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28 from the live layers (newest rows
via ``orderByFields=<watermark> DESC`` at ``outSR=4326``; newest permit
watermark ``1787019074000`` = 2026-08-18T02:11:14+00:00, newest crime
watermark ``1787882766890`` = 2026-08-28T02:06:06.890000+00:00). Fixtures are
RAW ArcGIS features (attributes + geometry); the tests run the real
``ArcGISClient._flatten_feature`` lift — ring centroid / point to
latitude/longitude, epoch-ms to ISO — before parsing, exactly as the live
producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_inland_empire import (
    CRIME_FIELD_MAP,
    DROPPED_NOISE_COLUMNS,
    FIELD_MAP,
    PERMITS_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.inland_empire import (
    INLAND_EMPIRE_CITY_ID,
    INLAND_EMPIRE_CRIME_ENDPOINT,
    INLAND_EMPIRE_DIVISION_BBOXES,
    INLAND_EMPIRE_DIVISIONS,
    INLAND_EMPIRE_FEED_SPECS,
    INLAND_EMPIRE_METRO_BBOX,
    INLAND_EMPIRE_PERMITS_ENDPOINT,
    INLAND_EMPIRE_SUBMARKETS,
    REGISTRATION,
    get_inland_empire_dataset,
    is_in_greater_inland_empire_metro,
    is_in_inland_empire_metro,
)
from src.spatial.city_registry import FeedType


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _flatten_permits(feature):
    """Run the real ArcGIS flatten lift over a raw captured permit feature.

    ``date_fields`` is what the client discovers from the live layer's
    metadata: the four esriFieldTypeDate columns.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        feature, {"APPLIED_DATE", "APPROVED_DATE", "COMPLETED_DATE", "EXPIRED_DATE"}
    )


def _flatten_crime(feature):
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(
        feature, {"offendate", "offentime", "datecreated", "dateupdated"}
    )


# Newest PERMIT-module rows on the 2026-08-28 probe (orderByFields=
# APPLIED_DATE DESC, outSR=4326). Byte-verbatim: ring geometry in WGS84,
# zero-valued characteristic columns, null approved/completed dates.
PERMITS_FEATURE_1 = {
    "attributes": {
        "OBJECTID": 1557681,
        "APN": "325030002",
        "CASE_ID": "OAPT2603552",
        "CASE_DESCR": "NEW SINGLE- FAMILY DWELLING",
        "CASE_MODULE": "PERMIT",
        "CASE_TYPE": "ONLINE APPLICATION (OAPT)",
        "CASE_WORK_CLASS": "OAPT - ONLINE APPLICATION",
        "DEPARTMENT": "GEN",
        "CASE_STATUS": "APPLIED ONLINE",
        "APPLIED_DATE": 1787019074000,
        "APPROVED_DATE": None,
        "COMPLETED_DATE": None,
        "EXPIRED_DATE": None,
        "RECORDED_PAGE": "",
        "SUBDIVISION_NAME": "",
        "LOT": "",
        "BLOCK": "",
        "BUILDING_COUNT": 0,
        "UNIT_COUNT": 0,
        "FLOOR_COUNT": 0,
        "HEIGHT": 0.0,
        "FCC_CODE": "",
        "SHAPE.STArea()": 377110.3808446574,
        "SHAPE.STLength()": 3214.6435228564083
    },
    "geometry": {"rings": [[[-117.29160065829471, 33.78094179370641], [-117.29165608915865, 33.78094110767762], [-117.29166299844829, 33.78094102208555], [-117.29595078750613, 33.780887910731224], [-117.29595260354257, 33.781672247802454], [-117.29594725094954, 33.78167231337813], [-117.29585390980043, 33.78167345319878], [-117.29170090642394, 33.78172410386112], [-117.2916639531724, 33.781724553707775], [-117.2916022136439, 33.78172530588786], [-117.29160214932394, 33.781692764172305], [-117.29160204605031, 33.78164099207994], [-117.29160082587481, 33.78102610663041], [-117.29160065829471, 33.78094179370641]]]}
}

PERMITS_FEATURE_2 = {
    "attributes": {
        "OBJECTID": 1307207,
        "APN": "255720015",
        "CASE_ID": "OAPT2603551",
        "CASE_DESCR": "INSTALLATION OF A 2 POLE 25A CIRCUIT FOR A MINI SPLIT UNIT. MINI SPLIT INSTALLED BY OTHERS.",
        "CASE_MODULE": "PERMIT",
        "CASE_TYPE": "ONLINE APPLICATION (OAPT)",
        "CASE_WORK_CLASS": "OAPT - ONLINE APPLICATION",
        "DEPARTMENT": "GEN",
        "CASE_STATUS": "APPLIED ONLINE",
        "APPLIED_DATE": 1787014086000,
        "APPROVED_DATE": None,
        "COMPLETED_DATE": None,
        "EXPIRED_DATE": None,
        "RECORDED_PAGE": "",
        "SUBDIVISION_NAME": "",
        "LOT": "",
        "BLOCK": "",
        "BUILDING_COUNT": 0,
        "UNIT_COUNT": 0,
        "FLOOR_COUNT": 0,
        "HEIGHT": 0.0,
        "FCC_CODE": "",
        "SHAPE.STArea()": 6063.480910151086,
        "SHAPE.STLength()": 328.8025397249387
    },
    "geometry": {"rings": [[[-117.31642009576377, 34.011865987210946], [-117.3164216686836, 34.01156769968375], [-117.31660645589554, 34.011568692312295], [-117.31660398243837, 34.011866855891896], [-117.31642009576377, 34.011865987210946]]]}
}

PERMITS_FEATURE_3 = {
    "attributes": {
        "OBJECTID": 162668,
        "APN": "273320004",
        "CASE_ID": "OAPT2603550",
        "CASE_DESCR": "ADD METAL BUILDING ON BACK OF PROPERTY",
        "CASE_MODULE": "PERMIT",
        "CASE_TYPE": "ONLINE APPLICATION (OAPT)",
        "CASE_WORK_CLASS": "OAPT - ONLINE APPLICATION",
        "DEPARTMENT": "GEN",
        "CASE_STATUS": "APPLIED ONLINE",
        "APPLIED_DATE": 1787012373000,
        "APPROVED_DATE": None,
        "COMPLETED_DATE": None,
        "EXPIRED_DATE": None,
        "RECORDED_PAGE": "",
        "SUBDIVISION_NAME": "",
        "LOT": "",
        "BLOCK": "",
        "BUILDING_COUNT": 0,
        "UNIT_COUNT": 0,
        "FLOOR_COUNT": 0,
        "HEIGHT": 0.0,
        "FCC_CODE": "",
        "SHAPE.STArea()": 1254674.3707046981,
        "SHAPE.STLength()": 5230.213787500341
    },
    "geometry": {"rings": [[[-117.35535717805607, 33.86532086482447], [-117.35427055770568, 33.86532087623282], [-117.35318225781175, 33.86532087859328], [-117.35212156423202, 33.86532093188492], [-117.35106739071995, 33.86532094938995], [-117.35100541533795, 33.86532080833715], [-117.35101233961254, 33.863493757052986], [-117.35344828502573, 33.863483262715256], [-117.35343191450953, 33.862452858335715], [-117.35371279786247, 33.86166252298161], [-117.35535285902395, 33.86166107915888], [-117.35535717805607, 33.86532086482447]]]}
}

# Newest crime rows on the 2026-08-28 probe (orderByFields=offendate DESC,
# outSR=4326). Byte-verbatim: WGS84 point geometry, camelCase ObjectID OID,
# NIBRS fields, city community-planning-area names.
CRIME_FEATURE_1 = {
    "attributes": {
        "ObjectID": 1493857,
        "rpdunique": "260022868_13B_0",
        "InstanceID": "00f9c851-d24d-4306-a4c6-b72f5a558295",
        "offenseid": "260022868",
        "callid": "LPD26082700176857",
        "reporttype": "Case Report",
        "offendate": 1787882766890,
        "offentime": 1787882766890,
        "DowName": "Thu",
        "dayofweek": 5,
        "hourofday": 19,
        "HourBlock": "1900",
        "TimeBlock": "Evening (6pm - 9pm)",
        "datecreated": 1787882766890,
        "dateupdated": 1787927835553,
        "Subject": "243(E)(1) - PC - BATTERY:SPOUSE/EX SPOUSE/DATE/ETC - Simple Assault - M",
        "nibrsdesc": "Assault Offenses",
        "nibrscode": "13B",
        "IBRGroup": "A",
        "IBRCrimeAgainst": "Person",
        "rd": "PC01",
        "BLOCK_ADDRESS": "3900 BLOCK  5th St ",
        "WARD_NUMB": 1,
        "COMMUNITY": "Downtown",
        "NAME": "NORTH",
        "GlobalID": "6ae84556-684d-4cce-a593-385cfa13650e",
        "Statute": "243(E)(1)"
    },
    "geometry": {"x": -117.37501566966847, "y": 33.98599337773164}
}

CRIME_FEATURE_2 = {
    "attributes": {
        "ObjectID": 1493868,
        "rpdunique": "260022864_13B_0",
        "InstanceID": "d643a175-4776-48fa-b748-41784c8a9cdc",
        "offenseid": "260022864",
        "callid": "LPD26082700176828",
        "reporttype": "Case Report",
        "offendate": 1787879810790,
        "offentime": 1787879810790,
        "DowName": "Thu",
        "dayofweek": 5,
        "hourofday": 18,
        "HourBlock": "1800",
        "TimeBlock": "Evening (6pm - 9pm)",
        "datecreated": 1787879810790,
        "dateupdated": 1787927953097,
        "Subject": "243(E)(1) - PC - BATTERY:SPOUSE/EX SPOUSE/DATE/ETC - Simple Assault - M",
        "nibrsdesc": "Assault Offenses",
        "nibrscode": "13B",
        "IBRGroup": "A",
        "IBRCrimeAgainst": "Person",
        "rd": "PC01",
        "BLOCK_ADDRESS": "3900 BLOCK  5th St ",
        "WARD_NUMB": 1,
        "COMMUNITY": "Downtown",
        "NAME": "NORTH",
        "GlobalID": "98bda98b-686d-46af-adab-a366801a7544",
        "Statute": "243(E)(1)"
    },
    "geometry": {"x": -117.37501566966847, "y": 33.98599337773164}
}

CRIME_FEATURE_3 = {
    "attributes": {
        "ObjectID": 1493882,
        "rpdunique": "260022836_120_0",
        "InstanceID": "a3782329-3bb3-48d7-89f4-35e88a15ef06",
        "offenseid": "260022836",
        "callid": "LPD26082700176634",
        "reporttype": "Case Report",
        "offendate": 1787864081307,
        "offentime": 1787864081307,
        "DowName": "Thu",
        "dayofweek": 5,
        "hourofday": 13,
        "HourBlock": "1300",
        "TimeBlock": "Mid-Day (10am - 1pm)",
        "datecreated": 1787864081307,
        "dateupdated": 1787930399007,
        "Subject": "664/211 Bank Robbery",
        "nibrsdesc": "Robbery",
        "nibrscode": "120",
        "IBRGroup": "A",
        "IBRCrimeAgainst": "Property",
        "rd": "PJ18",
        "BLOCK_ADDRESS": "10200 BLOCK  Magnolia Ave",
        "WARD_NUMB": 6,
        "COMMUNITY": "La Sierra",
        "NAME": "WEST",
        "GlobalID": "45afaf86-1b99-470c-9978-3063f347cc81",
        "Statute": "211"
    },
    "geometry": {"x": -117.45941398961268, "y": 33.91288867903887}
}

_NEWEST_APPLIED_ISO = "2026-08-18T02:11:14+00:00"
_NEWEST_OFFENSE_ISO = "2026-08-28T02:06:06.890000+00:00"


class TestInlandEmpireSpatial:
    def test_metro_bbox_sanity(self):
        assert INLAND_EMPIRE_METRO_BBOX["min_lat"] < INLAND_EMPIRE_METRO_BBOX["max_lat"]
        assert INLAND_EMPIRE_METRO_BBOX["min_lng"] < INLAND_EMPIRE_METRO_BBOX["max_lng"]

    def test_is_in_inland_empire_metro_rejects_missing_coordinates(self):
        assert is_in_inland_empire_metro(None, None) is False
        assert is_in_inland_empire_metro(33.9803, None) is False
        assert is_in_inland_empire_metro(None, -117.3769) is False

    def test_is_in_inland_empire_metro_rejects_other_metros(self):
        assert is_in_inland_empire_metro(34.0522, -118.2437) is False   # Los Angeles
        assert is_in_inland_empire_metro(32.7157, -117.1611) is False   # San Diego
        assert is_in_inland_empire_metro(33.7455, -117.8677) is False   # Santa Ana / Orange County
        assert is_in_inland_empire_metro(36.1699, -115.1398) is False   # Las Vegas
        assert is_in_inland_empire_metro(34.0633, -117.6507) is False   # Ontario (SW San Bernardino County)
        assert is_in_inland_empire_metro(34.1083, -117.2898) is False   # San Bernardino (county seat)

    def test_landmark_anchors_are_contained(self):
        assert is_in_inland_empire_metro(33.9803, -117.3769)  # Mission Inn, Riverside
        assert is_in_inland_empire_metro(33.8754, -117.5662)  # Corona City Hall
        assert is_in_inland_empire_metro(33.9410, -117.2720)  # Moreno Valley Mall
        assert is_in_inland_empire_metro(33.4903, -117.1486)  # Old Town Temecula
        assert is_in_inland_empire_metro(33.8295, -116.5454)  # Downtown Palm Springs

    def test_live_fixture_coordinates_are_contained(self):
        permit_centroids = [
            (33.781306814673385, -117.2937769489947),
            (34.01171718722489, -117.31651304536966),
            (33.86386460392234, -117.35355361418132),
        ]
        for lat, lng in permit_centroids:
            assert is_in_inland_empire_metro(lat, lng)
        for feature in (CRIME_FEATURE_1, CRIME_FEATURE_2, CRIME_FEATURE_3):
            assert is_in_inland_empire_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in INLAND_EMPIRE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= INLAND_EMPIRE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= INLAND_EMPIRE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= INLAND_EMPIRE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= INLAND_EMPIRE_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in INLAND_EMPIRE_SUBMARKETS.items():
            bbox = INLAND_EMPIRE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in INLAND_EMPIRE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(INLAND_EMPIRE_SUBMARKETS)

    def test_submarkets_carry_the_inland_empire_city_id(self):
        assert {m.city_id for m in INLAND_EMPIRE_SUBMARKETS.values()} == {"inland_empire"}

    def test_city_id_and_registration_shape(self):
        assert INLAND_EMPIRE_CITY_ID == "inland_empire"
        assert REGISTRATION.metro_bbox is INLAND_EMPIRE_METRO_BBOX
        assert REGISTRATION.submarkets is INLAND_EMPIRE_SUBMARKETS
        assert REGISTRATION.division_bboxes is INLAND_EMPIRE_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_inland_empire_metro
        assert len(REGISTRATION.divisions) == 7
        assert len(INLAND_EMPIRE_SUBMARKETS) == 14

    def test_required_real_submarkets_present(self):
        assert set(INLAND_EMPIRE_SUBMARKETS) == {
            "Downtown Riverside",
            "UCR Eastside",
            "Corona",
            "Norco",
            "Moreno Valley Central",
            "Perris",
            "Menifee",
            "Old Town Temecula",
            "Murrieta",
            "Hemet",
            "San Jacinto",
            "Palm Springs",
            "Palm Desert",
            "Indio",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_inland_empire_metro is is_in_inland_empire_metro


class TestInlandEmpireFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["CASE_ID", "OBJECTID"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["APPLIED_DATE"]
        assert PERMITS_FIELD_MAP["status"] == ["CASE_STATUS"]
        assert PERMITS_FIELD_MAP["job_type"] == ["CASE_WORK_CLASS", "CASE_TYPE"]
        assert PERMITS_FIELD_MAP["bbl"] == ["APN"]
        assert PERMITS_FIELD_MAP["proposed_units"] == ["UNIT_COUNT"]
        assert PERMITS_FIELD_MAP["proposed_stories"] == ["FLOOR_COUNT"]

    def test_crime_map_reads_live_columns(self):
        assert CRIME_FIELD_MAP["incident_id"] == ["offenseid", "ObjectID"]
        assert CRIME_FIELD_MAP["offense_type"] == ["nibrsdesc"]
        assert CRIME_FIELD_MAP["occurred_date"] == ["offendate"]
        assert CRIME_FIELD_MAP["reported_date"] == ["datecreated"]
        assert CRIME_FIELD_MAP["borough"] == ["COMMUNITY"]

    def test_field_map_alias_covers_both_registered_feeds(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP, "crime": CRIME_FIELD_MAP}

    def test_no_latitude_longitude_candidates_coordinates_come_from_geometry(self):
        """Coordinates are the outSR=4326 geometry lift (ring centroid for
        permits, native points for crime) — no attribute column is a
        coordinate candidate on either feed."""
        for field_map in (PERMITS_FIELD_MAP, CRIME_FIELD_MAP):
            assert "latitude" not in field_map
            assert "longitude" not in field_map

    def test_permit_columns_that_do_not_exist_stay_unmapped(self):
        """No address, valuation, or zip column exists on PLUS_ACTIVITIES —
        cost stays 0.0, no geocode is declared, and address stays None."""
        for key in ("address_street", "cost", "zipcode", "borough"):
            assert key not in PERMITS_FIELD_MAP

    def test_subdivision_name_is_not_a_borough_candidate(self):
        """SUBDIVISION_NAME is tract metadata, not a neighborhood (Omaha
        discipline): source_neighborhood passes through as None on permits."""
        assert "borough" not in PERMITS_FIELD_MAP

    def test_apn_reachable_through_the_generic_parcel_slot(self):
        assert first_mapped(PERMITS_FEATURE_1["attributes"], PERMITS_FIELD_MAP, "bbl") == "325030002"
        assert first_mapped(PERMITS_FEATURE_2["attributes"], PERMITS_FIELD_MAP, "bbl") == "255720015"

    def test_noise_columns_never_become_candidates(self):
        mapped = {c for values in FIELD_MAP.values() for c in values}
        assert mapped
        for col in DROPPED_NOISE_COLUMNS:
            assert col not in mapped
        assert "SHAPE.STArea()" in PERMITS_FEATURE_1["attributes"]  # live but unmapped
        assert "dateupdated" in CRIME_FEATURE_1["attributes"]

    def test_borough_candidate_only_on_the_crime_feed(self):
        assert first_mapped(CRIME_FEATURE_1["attributes"], CRIME_FIELD_MAP, "borough") == "Downtown"
        assert first_mapped(CRIME_FEATURE_3["attributes"], CRIME_FIELD_MAP, "borough") == "La Sierra"


class TestInlandEmpirePermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_ring_centroid_to_degrees(self):
        record = _flatten_permits(PERMITS_FEATURE_1)
        assert record["latitude"] == pytest.approx(33.781306814673385)
        assert record["longitude"] == pytest.approx(-117.2937769489947)
        # Raw ring points ride along unmapped; no state-plane attributes exist.
        assert "latitude" in record and "longitude" in record
        assert record["CASE_ID"] == "OAPT2603552"

    def test_flatten_iso_normalizes_the_date_columns_only(self):
        record = _flatten_permits(PERMITS_FEATURE_2)
        assert record["APPLIED_DATE"] == "2026-08-18T00:48:06+00:00"
        # Null date columns stay null.
        assert record["APPROVED_DATE"] is None

    def test_online_application_fixture_parses_through_the_producer(
        self, permits, monkeypatch
    ):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            _flatten_permits(PERMITS_FEATURE_1), city_id="inland_empire"
        )
        assert event is not None
        assert event.city_id == "inland_empire"
        assert event.job_id == "OAPT2603552"
        assert event.status == "APPLIED ONLINE"
        assert event.bbl == "325030002"
        assert event.estimated_cost == 0.0
        assert event.latitude == pytest.approx(33.781306814673385)
        assert event.longitude == pytest.approx(-117.2937769489947)
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat() == _NEWEST_APPLIED_ISO
        assert event.filing_date is None
        assert event.source_neighborhood is None
        assert event.zipcode == ""
        assert event.address_street is None
        # UNIT_COUNT/FLOOR_COUNT are 0 on live online applications -> None.
        assert event.proposed_dwelling_units is None
        assert event.proposed_stories is None

    def test_mini_split_fixture_indexes_h3_and_sits_in_metro(
        self, permits, monkeypatch
    ):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            _flatten_permits(PERMITS_FEATURE_2), city_id="inland_empire"
        )
        assert event is not None
        assert event.job_id == "OAPT2603551"
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_inland_empire_metro(event.latitude, event.longitude)

    def test_metal_building_fixture_valuation_and_watermark(
        self, permits, monkeypatch
    ):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            _flatten_permits(PERMITS_FEATURE_3), city_id="inland_empire"
        )
        assert event is not None
        assert event.job_id == "OAPT2603550"
        assert event.bbl == "273320004"
        assert event.issuance_date.isoformat() == "2026-08-18T00:19:33+00:00"
        assert is_in_inland_empire_metro(event.latitude, event.longitude)

    def test_all_three_fixtures_parse_with_distinct_h3_cells(
        self, permits, monkeypatch
    ):
        _patch_resolve(monkeypatch, "permits")
        events = [
            permits.parse_socrata_row(
                _flatten_permits(f), city_id="inland_empire"
            )
            for f in (PERMITS_FEATURE_1, PERMITS_FEATURE_2, PERMITS_FEATURE_3)
        ]
        assert all(e is not None for e in events)
        # Distinct cases occupy distinct res-9 cells.
        assert len({e.h3_res9 for e in events}) == 3

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(PERMITS_FEATURE_1)
        record.pop("CASE_ID")
        event = permits.parse_socrata_row(record, city_id="inland_empire")
        assert event is not None
        assert event.job_id == "1557681"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(PERMITS_FEATURE_1)
        record.pop("CASE_ID")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="inland_empire") is None

    def test_geometry_less_row_drops_without_a_geocode_declaration(
        self, permits, monkeypatch
    ):
        """PLUS_ACTIVITIES has no address column, so no geocode is declared:
        a geometry-less row has nothing to geocode and drops honestly."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(PERMITS_FEATURE_1)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="inland_empire") is None

    def test_state_plane_values_never_emit_as_degrees(self, permits, monkeypatch):
        """If the layer's native State Plane feet (wkid 102646) ever leaked
        into latitude/longitude, the producer's projected-coordinate guard
        nulls them and the coordinate-less row drops (no geocode declared)."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(PERMITS_FEATURE_1)
        record["latitude"] = 2_149_891.51     # State Plane VI feet, northing-ish
        record["longitude"] = 6_641_017.36    # State Plane VI feet, easting-ish
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="inland_empire") is None

    def test_work_class_codes_stay_unclassified_at_the_leaf(
        self, permits, monkeypatch
    ):
        """CASE_WORK_CLASS ('OAPT - ONLINE APPLICATION', …) passes through as
        job_type candidates; finer classification (CASE_DESCR carries 'NEW
        SINGLE- FAMILY DWELLING' etc.) is analytics-side. The OAPT code is
        not among the producer's recognized codes, so it lands on OT
        honestly."""
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(
            _flatten_permits(PERMITS_FEATURE_1), city_id="inland_empire"
        )
        assert event is not None
        assert event.job_type == JobType.OT
        record = _flatten_permits(PERMITS_FEATURE_3)
        record["CASE_WORK_CLASS"] = "BLD01 - NEW COMMERCIAL BUILDING"
        event = permits.parse_socrata_row(record, city_id="inland_empire")
        assert event is not None
        assert event.job_type == JobType.OT


class TestInlandEmpireCrimeParsing:
    @pytest.fixture
    def crime(self):
        with patch("src.producers.crime_incidents_producer.BaseKafkaProducer"):
            from src.producers.crime_incidents_producer import CrimeIncidentsProducer

            return CrimeIncidentsProducer()

    def test_flatten_lifts_native_points_to_degrees(self):
        record = _flatten_crime(CRIME_FEATURE_1)
        assert record["latitude"] == pytest.approx(33.98599337773164)
        assert record["longitude"] == pytest.approx(-117.37501566966847)
        assert record["offenseid"] == "260022868"

    def test_flatten_iso_normalizes_the_epoch_dates(self):
        record = _flatten_crime(CRIME_FEATURE_3)
        assert record["offendate"] == "2026-08-27T20:54:41.307000+00:00"
        assert record["dateupdated"] == "2026-08-28T15:19:59.007000+00:00"

    def test_assault_fixture_parses_through_the_producer(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(
            _flatten_crime(CRIME_FEATURE_1), city_id="inland_empire"
        )
        assert event is not None
        assert event.city_id == "inland_empire"
        assert event.incident_id == "260022868"
        assert event.offense_type == "Assault Offenses"
        assert event.offense_class == "PART1"
        assert event.source_neighborhood == "Downtown"
        assert event.latitude == pytest.approx(33.98599337773164)
        assert event.longitude == pytest.approx(-117.37501566966847)
        assert event.occurred_date.isoformat() == _NEWEST_OFFENSE_ISO
        assert event.h3_res7 is not None
        assert is_in_inland_empire_metro(event.latitude, event.longitude)

    def test_block_address_does_not_reach_the_event_address_field(
        self, crime, monkeypatch
    ):
        """BLOCK_ADDRESS is the ADR 0004 address evidence, but the crime
        producer's address chain reads lowercase spellings only — the event
        address stays None honestly (coordinates are the primary locator)."""
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(
            _flatten_crime(CRIME_FEATURE_1), city_id="inland_empire"
        )
        assert event is not None
        assert event.address is None
        assert "BLOCK_ADDRESS" in _flatten_crime(CRIME_FEATURE_1)

    def test_robbery_fixture_classifies_part1_and_la_sierra(
        self, crime, monkeypatch
    ):
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(
            _flatten_crime(CRIME_FEATURE_3), city_id="inland_empire"
        )
        assert event is not None
        assert event.incident_id == "260022836"
        assert event.offense_type == "Robbery"
        assert event.offense_class == "PART1"
        assert event.source_neighborhood == "La Sierra"
        assert event.reported_date is not None
        assert event.reported_date.isoformat() == "2026-08-27T20:54:41.307000+00:00"
        assert is_in_inland_empire_metro(event.latitude, event.longitude)

    def test_second_assault_fixture_shares_the_block_but_differs_by_offense_id(
        self, crime, monkeypatch
    ):
        _patch_resolve(monkeypatch, "crime")
        event = crime.parse_socrata_row(
            _flatten_crime(CRIME_FEATURE_2), city_id="inland_empire"
        )
        assert event is not None
        assert event.incident_id == "260022864"

    def test_incident_id_falls_back_to_objectid(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        record = _flatten_crime(CRIME_FEATURE_1)
        record.pop("offenseid")
        event = crime.parse_socrata_row(record, city_id="inland_empire")
        assert event is not None
        assert event.incident_id == "1493857"

    def test_row_without_any_id_is_dropped(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        record = _flatten_crime(CRIME_FEATURE_1)
        record.pop("offenseid")
        record.pop("ObjectID")
        assert crime.parse_socrata_row(record, city_id="inland_empire") is None

    def test_geometry_less_row_drops_without_a_geocode_declaration(
        self, crime, monkeypatch
    ):
        """The feed carries native coordinates, so no geocode is declared:
        a geometry-less row drops rather than geocoding a block address."""
        _patch_resolve(monkeypatch, "crime")
        record = _flatten_crime(CRIME_FEATURE_1)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert crime.parse_socrata_row(record, city_id="inland_empire") is None

    def test_zero_zero_coordinates_are_dropped(self, crime, monkeypatch):
        _patch_resolve(monkeypatch, "crime")
        record = _flatten_crime(CRIME_FEATURE_1)
        record["latitude"] = 0.0
        record["longitude"] = 0.0
        assert crime.parse_socrata_row(record, city_id="inland_empire") is None


class TestInlandEmpireFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_inland_empire_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == INLAND_EMPIRE_PERMITS_ENDPOINT
        assert spec.watermark_col == "APPLIED_DATE"
        assert spec.id_keys == ["CASE_ID", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 14
        assert spec.where == "CASE_MODULE = 'PERMIT'"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"

    def test_crime_spec_matches_live_layer(self):
        spec = get_inland_empire_dataset(FeedType.CRIME)
        assert spec.platform == "arcgis"
        assert spec.endpoint == INLAND_EMPIRE_CRIME_ENDPOINT
        assert spec.watermark_col == "offendate"
        assert spec.id_keys == ["offenseid", "ObjectID"]
        assert spec.oid_field == "ObjectID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 7
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.field_map == CRIME_FIELD_MAP
        assert spec.topic == "raw.municipal.crime"

    def test_registered_feed_set_is_permits_and_crime_only(self):
        assert set(INLAND_EMPIRE_FEED_SPECS) == {"permits", "crime"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_inland_empire_dataset("sla")
        assert "inland_empire" in str(exc.value)
        assert "permits" in str(exc.value)
        assert "crime" in str(exc.value)

    def test_endpoints_are_the_probed_official_hosts(self):
        assert "gis.countyofriverside.us" in INLAND_EMPIRE_PERMITS_ENDPOINT
        assert "OpenData/General/MapServer/280" in INLAND_EMPIRE_PERMITS_ENDPOINT
        assert "services.arcgis.com/Fu2oOWg1Aw7azh41" in INLAND_EMPIRE_CRIME_ENDPOINT
        assert "View_CrimesRPD/FeatureServer/4" in INLAND_EMPIRE_CRIME_ENDPOINT
