"""Unit tests for the Chandler, AZ leaf (US-228): spatial module + field
maps + producer parse wiring.

Chandler is a ONE-FEED PARTIAL metro: LIS.ACCELA_ALL_PERMITS_V_HARD
(``Tolemi/Building_Blocks/MapServer/0`` on ``gis.chandleraz.gov``
Enterprise 11.5, Tier 1, daily, 103,442 rows). 311 (GOGov SaaS, no bulk
feed), SLA (no municipal business licenses in AZ), deeds (Maricopa County
recorder has no bulk API — phoenix precedent), and crime (RAIDS SaaS /
aggregates) stay Tier 3 — only ``permits`` is registered.

Tests pass WITHOUT a spine registration (no CityId.CHANDLER, no REGISTRY
asserts — "chandler" stays a plain string; feeds are requested by plain
feed name). Spine-stable per the West-wave leaf contract: no division
resolution assertions and no geocode call-count assertions.

Fixtures captured byte-verbatim 2026-08-28 from MapServer/0 (newest rows
via ``orderByFields=CREATE_DT DESC, OBJECTID DESC`` at ``outSR=4326``;
co-newest watermark ``1787702401000`` = 2026-08-26T00:00:01+00:00, one
mobile-home-park permit batch). Fixtures are RAW ArcGIS features
(attributes + geometry); the tests run the real ``ArcGISClient._flatten_
feature`` lift — geometry to latitude/longitude, epoch-ms to ISO — before
parsing, exactly as the live producer path does.

PII redaction: the live rows carry PRI_CNTCT_*/PRI_CNTRCT_*/OWNER_*
personal names, phones, and emails. Those columns are DROPPED_PII_COLUMNS
and never field-map candidates, so their values are nulled in the fixtures
without affecting any parse outcome; every other byte is verbatim from the
probe.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_chandler import (
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.chandler import (
    CHANDLER_CITY_ID,
    CHANDLER_DIVISION_BBOXES,
    CHANDLER_DIVISIONS,
    CHANDLER_FEED_SPECS,
    CHANDLER_GEOCODE_CONTEXT,
    CHANDLER_METRO_BBOX,
    CHANDLER_PERMITS_ENDPOINT,
    CHANDLER_SUBMARKETS,
    REGISTRATION,
    get_chandler_dataset,
    is_in_chandler_metro,
    is_in_greater_chandler_metro,
)


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _flatten(feature):
    """Run the real ArcGIS flatten lift over a raw captured feature.

    ``date_fields`` is what the client discovers from the live layer's
    metadata: CREATE_DT is esriFieldTypeDate; every other column is a
    string/double and is correctly NOT a date field.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, {"CREATE_DT"})


# Newest rows on the 2026-08-28 probe (orderByFields=CREATE_DT DESC,
# OBJECTID DESC, outSR=4326) — three rows of one mobile-home-park batch
# share the co-newest watermark. Byte-verbatim except DROPPED_PII_COLUMNS
# values (see module docstring).
_FEATURE_102402 = {
    "attributes": {
        "OBJECTID": 102402,
        "FULL_ADDRESS": "301 N ITHICA ST #43",
        "ADDR_TYPE_DESC": "MOBILE HOME PARK",
        "RETIRED": "N",
        "INSP_ZONE": "6",
        "INSPECTOR": "Steve Thomas",
        "SUPERVISOR": "CASEY MARTIN",
        "PERMIT_NBR": "UTL26-0884",
        "CREATE_DT": 1787702401000,
        "PROJECT_NM": "Roots panel replacement 1",
        "B1_PER_TYPE": "Utility",
        "B1_PER_SUB_TYPE": "NA",
        "PERMIT_STATUS": "Awaiting Signature",
        "DETAIL_DESC": "storm ripped power out to 4 units on property. Setting two new power poles with two panels on each pole",
        "PERMIT_TYPE": "CLASS 7",
        "PARCEL_NBR": "30270065",
        "ADDR_EID": 111287957.0,
        "FMA": "27",
        "JOB_VALUE": None,
        "SQ_FOOT": None,
        "ECON_DEV_PRJ": None,
        "FULL_ADDR": "301 N ITHICA ST",
        "ZIP_CODE": "85225",
        "PRI_CNTCT_BUS_NM": None,
        "PRI_CNTCT_FULL_NM": None,
        "PRI_CNTCT_PHONE": None,
        "PRI_CNTCT_EMAIL": None,
        "PRI_CNTRCT_BUS_NM": None,
        "PRI_CNTRCT_FULL_NM": None,
        "PRI_CNTRCT_PHONE": None,
        "PRI_CNTRCT_EMAIL": None,
        "OWNER_NM": None,
        "OWNER_PHONE": None,
        "OWNER_EMAIL": None,
    },
    "geometry": {
        "x": -111.82942906952167,
        "y": 33.307391072239646,
    },
}

_FEATURE_35896 = {
    "attributes": {
        "OBJECTID": 35896,
        "FULL_ADDRESS": "301 N ITHICA ST #54",
        "ADDR_TYPE_DESC": "MOBILE HOME PARK",
        "RETIRED": "N",
        "INSP_ZONE": "6",
        "INSPECTOR": "Steve Thomas",
        "SUPERVISOR": "CASEY MARTIN",
        "PERMIT_NBR": "BLD26-2139",
        "CREATE_DT": 1787702401000,
        "PROJECT_NM": "Roots panel replacement 4",
        "B1_PER_TYPE": "Building",
        "B1_PER_SUB_TYPE": "NA",
        "PERMIT_STATUS": "Accepted",
        "DETAIL_DESC": "storm knocked out power to 4 units. Installing two new power poles with two panels on each pole.",
        "PERMIT_TYPE": "ADDITION RESIDENTIAL",
        "PARCEL_NBR": "30270065",
        "ADDR_EID": 111287971.0,
        "FMA": "27",
        "JOB_VALUE": "4000",
        "SQ_FOOT": None,
        "ECON_DEV_PRJ": None,
        "FULL_ADDR": "301 N ITHICA ST",
        "ZIP_CODE": "85225",
        "PRI_CNTCT_BUS_NM": None,
        "PRI_CNTCT_FULL_NM": None,
        "PRI_CNTCT_PHONE": None,
        "PRI_CNTCT_EMAIL": None,
        "PRI_CNTRCT_BUS_NM": None,
        "PRI_CNTRCT_FULL_NM": None,
        "PRI_CNTRCT_PHONE": None,
        "PRI_CNTRCT_EMAIL": None,
        "OWNER_NM": None,
        "OWNER_PHONE": None,
        "OWNER_EMAIL": None,
    },
    "geometry": {
        "x": -111.82912435551434,
        "y": 33.307431260146544,
    },
}

_FEATURE_35895 = {
    "attributes": {
        "OBJECTID": 35895,
        "FULL_ADDRESS": "301 N ITHICA ST #53",
        "ADDR_TYPE_DESC": "MOBILE HOME PARK",
        "RETIRED": "N",
        "INSP_ZONE": "6",
        "INSPECTOR": "Steve Thomas",
        "SUPERVISOR": "CASEY MARTIN",
        "PERMIT_NBR": "BLD26-2138",
        "CREATE_DT": 1787702401000,
        "PROJECT_NM": "Roots panel replacement 3",
        "B1_PER_TYPE": "Building",
        "B1_PER_SUB_TYPE": "NA",
        "PERMIT_STATUS": "Accepted",
        "DETAIL_DESC": "storm knocked out power to 4 units. Installing two new power poles with two panels on each pole.",
        "PERMIT_TYPE": "ADDITION RESIDENTIAL",
        "PARCEL_NBR": "30270065",
        "ADDR_EID": 111287970.0,
        "FMA": "27",
        "JOB_VALUE": "4000",
        "SQ_FOOT": None,
        "ECON_DEV_PRJ": None,
        "FULL_ADDR": "301 N ITHICA ST",
        "ZIP_CODE": "85225",
        "PRI_CNTCT_BUS_NM": None,
        "PRI_CNTCT_FULL_NM": None,
        "PRI_CNTCT_PHONE": None,
        "PRI_CNTCT_EMAIL": None,
        "PRI_CNTRCT_BUS_NM": None,
        "PRI_CNTRCT_FULL_NM": None,
        "PRI_CNTRCT_PHONE": None,
        "PRI_CNTRCT_EMAIL": None,
        "OWNER_NM": None,
        "OWNER_PHONE": None,
        "OWNER_EMAIL": None,
    },
    "geometry": {
        "x": -111.82912245954496,
        "y": 33.30752701478167,
    },
}

_CREATE_ISO = "2026-08-26T00:00:01+00:00"


class TestChandlerSpatial:
    def test_metro_bbox_sanity(self):
        assert CHANDLER_METRO_BBOX["min_lat"] < CHANDLER_METRO_BBOX["max_lat"]
        assert CHANDLER_METRO_BBOX["min_lng"] < CHANDLER_METRO_BBOX["max_lng"]

    def test_is_in_chandler_metro_rejects_missing_coordinates(self):
        assert is_in_chandler_metro(None, None) is False
        assert is_in_chandler_metro(33.3060, None) is False
        assert is_in_chandler_metro(None, -111.8412) is False

    def test_is_in_chandler_metro_rejects_far_cities(self):
        assert is_in_chandler_metro(33.4484, -112.0740) is False  # Phoenix downtown
        assert is_in_chandler_metro(32.2226, -110.9723) is False  # Tucson
        assert is_in_chandler_metro(35.2271, -80.8431) is False   # Charlotte
        assert is_in_chandler_metro(33.7490, -84.3880) is False   # Atlanta

    def test_anchors_across_the_city_are_contained(self):
        assert is_in_chandler_metro(33.3060, -111.8412)   # Downtown Historic Core
        assert is_in_chandler_metro(33.2120, -111.7640)   # Sun Groves (SE corner)
        assert is_in_chandler_metro(33.3480, -111.8918)   # Marlborough Estates plat
        assert is_in_chandler_metro(33.2495, -111.8355)   # Ocotillo Lakes
        assert is_in_chandler_metro(33.2906, -111.7968)   # Municipal Airport

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_FEATURE_102402, _FEATURE_35896, _FEATURE_35895):
            assert is_in_chandler_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in CHANDLER_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= CHANDLER_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= CHANDLER_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= CHANDLER_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= CHANDLER_METRO_BBOX["max_lng"], name

    def test_division_bboxes_never_interior_overlap(self):
        boxes = list(CHANDLER_DIVISION_BBOXES.values())
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                lat_overlap = a["min_lat"] < b["max_lat"] and b["min_lat"] < a["max_lat"]
                lng_overlap = a["min_lng"] < b["max_lng"] and b["min_lng"] < a["max_lng"]
                assert not (lat_overlap and lng_overlap)

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in CHANDLER_SUBMARKETS.items():
            bbox = CHANDLER_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in CHANDLER_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(CHANDLER_SUBMARKETS)

    def test_submarkets_carry_the_chandler_city_id(self):
        assert {m.city_id for m in CHANDLER_SUBMARKETS.values()} == {"chandler"}

    def test_city_id_constant_and_registration_shape(self):
        assert CHANDLER_CITY_ID == "chandler"
        assert REGISTRATION.metro_bbox is CHANDLER_METRO_BBOX
        assert REGISTRATION.submarkets is CHANDLER_SUBMARKETS
        assert REGISTRATION.division_bboxes is CHANDLER_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_chandler_metro
        assert len(REGISTRATION.divisions) == 6
        assert len(CHANDLER_SUBMARKETS) == 10

    def test_required_real_submarkets_present(self):
        assert set(CHANDLER_SUBMARKETS) == {
            "Downtown Historic Core",
            "Andersen Springs & Chandler Blvd",
            "Intel Ocotillo Tech Belt",
            "Marlborough Park Estates",
            "West Chandler Kyrene Belt",
            "Chandler Municipal Airport",
            "Ocotillo Lakes",
            "Fulton Ranch",
            "Sun Groves",
            "Springfield, Cooper Commons & Circle G",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_chandler_metro is is_in_chandler_metro


class TestChandlerFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["PERMIT_NBR", "OBJECTID"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["CREATE_DT"]
        assert PERMITS_FIELD_MAP["status"] == ["PERMIT_STATUS"]
        assert PERMITS_FIELD_MAP["job_type"] == ["B1_PER_TYPE", "PERMIT_TYPE"]
        assert PERMITS_FIELD_MAP["cost"] == ["JOB_VALUE"]
        assert PERMITS_FIELD_MAP["address_street"] == ["FULL_ADDRESS", "FULL_ADDR"]
        assert PERMITS_FIELD_MAP["zipcode"] == ["ZIP_CODE"]
        assert PERMITS_FIELD_MAP["bbl"] == ["PARCEL_NBR"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Chandler, AZ"
        assert CHANDLER_GEOCODE_CONTEXT == "Chandler, AZ"

    def test_geometry_is_the_only_coordinate_source(self):
        """The store SR is StatePlane Arizona Central (HARN) intl feet; the
        layer exposes no X/Y attribute pair, so coordinates come only from
        the outSR=4326 geometry lift and no coordinate candidates exist."""
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP
        attrs = _FEATURE_102402["attributes"]
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "latitude") is None
        assert first_mapped(attrs, PERMITS_FIELD_MAP, "longitude") is None

    def test_no_issuance_date_candidate_application_date_only(self):
        """CREATE_DT is the Accela record-creation date (2,307 pending
        permits older than 90d prove it is not a status stamp), so it maps
        to filing_date and issuance_date stays undeclared — the view
        publishes no issue timestamp."""
        assert "issuance_date" not in PERMITS_FIELD_MAP
        assert PERMITS_FIELD_MAP["filing_date"] == ["CREATE_DT"]

    def test_no_borough_candidate_so_source_neighborhood_passes_none(self):
        assert "borough" not in PERMITS_FIELD_MAP
        assert "neighborhood" not in PERMITS_FIELD_MAP

    def test_pii_columns_never_become_candidates(self):
        mapped = {c for values in PERMITS_FIELD_MAP.values() for c in values}
        assert mapped
        for values in PERMITS_FIELD_MAP.values():
            for col in values:
                assert col not in DROPPED_PII_COLUMNS
        assert {
            "PRI_CNTCT_FULL_NM", "PRI_CNTCT_PHONE", "PRI_CNTCT_EMAIL",
            "PRI_CNTRCT_FULL_NM", "PRI_CNTRCT_PHONE", "PRI_CNTRCT_EMAIL",
            "OWNER_NM", "OWNER_PHONE", "OWNER_EMAIL",
        } <= set(DROPPED_PII_COLUMNS)

    def test_bbl_maps_the_maricopa_parcel(self):
        """PARCEL_NBR is the Maricopa APN (30270065) — parcel-id-into-bbl
        follows the Las Vegas PRCLID / Savannah PIN precedent."""
        assert PERMITS_FIELD_MAP["bbl"] == ["PARCEL_NBR"]
        assert first_mapped(_FEATURE_35896["attributes"], PERMITS_FIELD_MAP, "bbl") == "30270065"


class TestChandlerPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten(_FEATURE_102402)
        assert record["latitude"] == pytest.approx(33.307391072239646)
        assert record["longitude"] == pytest.approx(-111.82942906952167)

    def test_flatten_iso_normalizes_the_watermark_only(self):
        record = _flatten(_FEATURE_35896)
        assert record["CREATE_DT"] == _CREATE_ISO
        # PARCEL_NBR and JOB_VALUE are strings — untouched by the date lift.
        assert record["PARCEL_NBR"] == "30270065"
        assert record["JOB_VALUE"] == "4000"

    def test_utility_fixture_parses_through_the_producer(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_102402), city_id="chandler")
        assert event is not None
        assert event.city_id == "chandler"
        assert event.job_id == "UTL26-0884"
        assert event.status == "Awaiting Signature"
        assert event.estimated_cost == 0.0
        assert event.address_street == "301 N ITHICA ST #43"
        assert event.latitude == pytest.approx(33.307391072239646)
        assert event.longitude == pytest.approx(-111.82942906952167)
        assert event.filing_date is not None
        assert event.filing_date.isoformat() == _CREATE_ISO
        # CREATE_DT is the application date; no issuance timestamp exists
        # on the view, so issuance_date stays None (honest handling).
        assert event.issuance_date is None
        assert event.source_neighborhood is None
        assert event.zipcode == "85225"
        assert event.bbl == "30270065"

    def test_building_fixture_cost_chain_and_addition_fallback(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten(_FEATURE_35896), city_id="chandler")
        assert event is not None
        # JOB_VALUE is a string ("4000"); the cost chain strips and floats it.
        assert event.estimated_cost == pytest.approx(4000.0)
        assert event.job_type == JobType.OT  # "Building" is not a NYC code
        # B1_PER_TYPE is null on no rows live, but the PERMIT_TYPE fallback
        # ("ADDITION …" -> A2) must still resolve when the head is absent.
        record = _flatten(_FEATURE_35896)
        record.pop("B1_PER_TYPE")
        event = permits.parse_socrata_row(record, city_id="chandler")
        assert event is not None
        assert event.job_type == JobType.A2

    def test_all_three_fixtures_share_the_co_newest_watermark(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        events = [
            permits.parse_socrata_row(_flatten(f), city_id="chandler")
            for f in (_FEATURE_102402, _FEATURE_35896, _FEATURE_35895)
        ]
        assert all(e is not None for e in events)
        assert {e.filing_date.isoformat() for e in events} == {_CREATE_ISO}
        assert {e.issuance_date for e in events} == {None}
        assert len({e.job_id for e in events}) == 3
        for e in events:
            assert e.h3_res7 is not None
            assert e.h3_res8 is not None
            assert e.h3_res9 is not None
            assert is_in_chandler_metro(e.latitude, e.longitude)

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_102402)
        record.pop("PERMIT_NBR")
        event = permits.parse_socrata_row(record, city_id="chandler")
        assert event is not None
        assert event.job_id == "102402"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_102402)
        record.pop("PERMIT_NBR")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="chandler") is None

    def test_geometry_less_row_is_dropped_geocode_not_declared(self, permits, monkeypatch):
        """needs_geocode is False (0 of 103,442 live rows carry null
        geometry), so a geometry-less row has no locator and is dropped —
        no fake degrees, no geocode-call-count assertions."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten(_FEATURE_35895)
        record.pop("latitude")
        record.pop("longitude")
        assert permits.parse_socrata_row(record, city_id="chandler") is None


class TestChandlerFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_chandler_dataset("permits")
        assert spec.platform == "arcgis"
        assert spec.endpoint == CHANDLER_PERMITS_ENDPOINT
        assert spec.watermark_col == "CREATE_DT"
        assert spec.id_keys == ["PERMIT_NBR", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.order_by == "CREATE_DT DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"

    def test_registered_feed_set_is_permits_only(self):
        assert set(CHANDLER_FEED_SPECS) == {"permits"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_chandler_dataset("sla")
        assert "chandler" in str(exc.value)
        assert "permits" in str(exc.value)

    def test_endpoint_is_the_probed_mapserver(self):
        assert "gis.chandleraz.gov" in CHANDLER_PERMITS_ENDPOINT
        assert (
            "Tolemi/Building_Blocks/MapServer/0" in CHANDLER_PERMITS_ENDPOINT
        )
