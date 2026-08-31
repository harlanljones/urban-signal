"""Unit tests for the Long Beach, CA leaf (US-224): spatial module + field
maps + producer parse wiring.

Long Beach is a TWO-FEED PARTIAL metro on the city's hosted ArcGIS org
(``services6.arcgis.com``/``yCArG7wGXGyWLqav``, owner ``arcgis_clb``):
BusinessLicenses_DailyUpdate (SLA, Tier 1, daily) and LBPD CrimeData
(crime with native coordinates — the ADR-0004 gate is satisfied natively).
311 (``service-requests`` on data.longbeach.gov — the successor of the
dead ``datalongbeach.opendatasoft.com`` domain) is verified live but has
no in-repo client; PERMITS exist only as aggregates and LA County recorder
deeds publish no queryable API — all three stay unregistered.

Tests pass WITHOUT a spine registration (no CityId.LONG_BEACH;
``"long_beach"`` stays a plain string, including as the parse input).
Spine-stable per the leaf contract: no division/borough-resolution
assertions, no geocode-hook call-count assertions, and NO assertions on
``event.city_id`` — ``normalize_city("long_beach")`` currently resolves
to ``CityId.LOS_ANGELES`` through the pre-existing LA alias (city_registry
lines 798-799) and will flip to ``CityId.LONG_BEACH`` when the spine hold
lands, so either equality would be spine-volatile.

Fixtures captured byte-verbatim 2026-08-28 with ``outSR=4326``:
* SLA — newest three rows of ``Business_Licenses_Public_View/FeatureServer/0``
  via ``orderByFields=MILESTONEDATE DESC``; all three share the co-newest
  watermark ``1787817600000`` = 2026-08-27T08:00:00+00:00 (the live max).
* CRIME — newest three rows of ``Police_Crime_Mapping/FeatureServer/0`` via
  ``orderByFields=ReportedDateTimeDate DESC``; newest watermark
  ``1787106060000`` = 2026-08-19T02:21:00+00:00 (the live max).
Fixtures are RAW ArcGIS features (attributes + geometry); the tests run the
real ``ArcGISClient._flatten_feature`` lift — geometry to latitude/longitude,
epoch-ms to ISO — before parsing, exactly as the live producer path does.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from src.producers.acquisition import build_where, is_future_watermark
from src.producers.field_maps import first_mapped
from src.producers.field_maps_long_beach import (
    CRIME_FIELD_MAP,
    DROPPED_NONADDRESS_COLUMNS,
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    SLA_FIELD_MAP,
)
from src.spatial.cities.long_beach import (
    LONG_BEACH_CITY_ID,
    LONG_BEACH_CRIME_ENDPOINT,
    LONG_BEACH_DIVISION_BBOXES,
    LONG_BEACH_DIVISIONS,
    LONG_BEACH_FEED_SPECS,
    LONG_BEACH_GEOCODE_CONTEXT,
    LONG_BEACH_METRO_BBOX,
    LONG_BEACH_SLA_ENDPOINT,
    LONG_BEACH_SUBMARKETS,
    REGISTRATION,
    get_long_beach_dataset,
    is_in_greater_long_beach_metro,
    is_in_long_beach_metro,
)
from src.spatial.h3_indexer import H3SpatialIndexer
from src.spatial.submarkets import SubmarketMeta

# ---------------------------------------------------------------------------
# Live fixtures — SLA (byte-verbatim attributes from the 2026-08-28 probe;
# outSR=4326 geometry). All three share the co-newest MILESTONEDATE.
# ---------------------------------------------------------------------------

SLA_FEATURE_343 = {
    "attributes": {
        "OBJECTID": 343,
        "LICENSENO": "BU21523715",
        "LICCATDESC": "Business Office",
        "LICSTATUS": "Active",
        "DBANAME": "Martin Logistics",
        "ISSDTTM": 1441958400000,
        "INACTVDTTM": None,
        "MILESTONEDATE": 1787817600000,
        "MILESTONE": "Pre-Renew",
        "FULLNAME": "DIAMOND LANE TRANSPORTATION INC",
        "SITELOCATION": "2710 OREGON AVE ",
        "ZIP": "90806",
        "COMPANYTYPE": "CORP",
        "NUMEMP": 1,
        "NUMUNITS": 0,
        "PRINTPRODUCTTYPES": "Trucking Business Office Only",
        "HOMEBASED": "Yes",
        "INDCNTR": "No",
        "CLASSDESC": "Services",
        "BLLICEXEMPT": "No",
        "OUTSIDECITY": "No",
        "BID_NAME": None,
        "BID_NAME_1": None,
        "BID_NAME_12": None,
        "COUNCIL_NUMBER": 7,
        "TRACT": "572202",
        "CDBG": None,
        "MILESTONE_SIMPLE": "Active",
    },
    "geometry": {"x": -118.2010133737972, "y": 33.806526607179286},
}

SLA_FEATURE_7093 = {
    "attributes": {
        "OBJECTID": 7093,
        "LICENSENO": "BU21700669",
        "LICCATDESC": "Contracting – Building",
        "LICSTATUS": "Active",
        "DBANAME": None,
        "ISSDTTM": 1486454400000,
        "INACTVDTTM": None,
        "MILESTONEDATE": 1787817600000,
        "MILESTONE": "Renewed",
        "FULLNAME": "L. F. SCHROEDER CONSTRUCTION, INC",
        "SITELOCATION": "228 EUCLID AVE ",
        "ZIP": "90803",
        "COMPANYTYPE": "CORP",
        "NUMEMP": 1,
        "NUMUNITS": 0,
        "PRINTPRODUCTTYPES": "B",
        "HOMEBASED": "Yes",
        "INDCNTR": "No",
        "CLASSDESC": "Contractors",
        "BLLICEXEMPT": "No",
        "OUTSIDECITY": "No",
        "BID_NAME": None,
        "BID_NAME_1": None,
        "BID_NAME_12": None,
        "COUNCIL_NUMBER": 3,
        "TRACT": "577200",
        "CDBG": "Y",
        "MILESTONE_SIMPLE": "Active",
    },
    "geometry": {"x": -118.14885015726114, "y": 33.76487479004518},
}

SLA_FEATURE_7238 = {
    "attributes": {
        "OBJECTID": 7238,
        "LICENSENO": "BU21704484",
        "LICCATDESC": "Apartment House",
        "LICSTATUS": "Active",
        "DBANAME": None,
        "ISSDTTM": 1498896000000,
        "INACTVDTTM": None,
        "MILESTONEDATE": 1787817600000,
        "MILESTONE": "Renewed",
        "FULLNAME": "5318 CEDAR TRUST",
        "SITELOCATION": "5322 CEDAR AVE 5322-34 CEDAR/100 E PLYMOUTH",
        "ZIP": "90805",
        "COMPANYTYPE": "TRUST",
        "NUMEMP": 0,
        "NUMUNITS": 7,
        "PRINTPRODUCTTYPES": "Apartment House",
        "HOMEBASED": "No",
        "INDCNTR": "No",
        "CLASSDESC": "Rental – Residential Property",
        "BLLICEXEMPT": "No",
        "OUTSIDECITY": "No",
        "BID_NAME": None,
        "BID_NAME_1": None,
        "BID_NAME_12": None,
        "COUNCIL_NUMBER": 8,
        "TRACT": "571703",
        "CDBG": "Y",
        "MILESTONE_SIMPLE": "Active",
    },
    "geometry": {"x": -118.19349691716195, "y": 33.85301658907985},
}

SLA_MILESTONE_ISO = "2026-08-27T08:00:00+00:00"
SLA_ISSDTTM_ISO_343 = "2015-09-11T08:00:00+00:00"

# The live ISSDTTM maximum, byte-verbatim: a future-date sentinel row
# (year 3202). Shape-verbatim synthetic variant of FEATURE_343 — the
# watermark stays MILESTONEDATE and must never pin to this value.
SLA_SENTINEL_ISSDTTM = 38886854400000

SLA_DATE_FIELDS = {"MILESTONEDATE", "ISSDTTM", "INACTVDTTM"}

# ---------------------------------------------------------------------------
# Live fixtures — CRIME (byte-verbatim attributes from the 2026-08-28 probe;
# outSR=4326 geometry). Newest three rows of the rolling window.
# ---------------------------------------------------------------------------

CRIME_FEATURE_10616 = {
    "attributes": {
        "OBJECTID": 10616,
        "DR": "260037217",
        "Type": "CRIMES AGAINST PROPERTY",
        "Category": "MOTOR VEHICLE THEFT",
        "CrimeType": "MOTOR VEHICLE THEFT",
        "ReportedDateTime": "08/18/2026 07:21 PM",
        "ReportedDateTimeDate": 1787106060000,
        "Address": "3800 BLOCK WORSHAM AV",
        "Division": "EAST",
        "Beat": "16",
        "ReportingDistrict": "472",
        "DaysOld": 1,
        "DayOfWeek": "TUESDAY",
        "HourOfDay": 19,
    },
    "geometry": {"x": -118.14619536954173, "y": 33.82819274482639},
}

CRIME_FEATURE_10617 = {
    "attributes": {
        "OBJECTID": 10617,
        "DR": "260037216",
        "Type": "CRIMES AGAINST PROPERTY",
        "Category": "MOTOR VEHICLE THEFT",
        "CrimeType": "MOTOR VEHICLE THEFT",
        "ReportedDateTime": "08/18/2026 07:10 PM",
        "ReportedDateTimeDate": 1787105400000,
        "Address": "2000 BLOCK MARTIN LUTHER KING JR AV",
        "Division": "WEST",
        "Beat": "5",
        "ReportingDistrict": "312",
        "DaysOld": 1,
        "DayOfWeek": "TUESDAY",
        "HourOfDay": 19,
    },
    "geometry": {"x": -118.180638379231, "y": 33.793573100895394},
}

CRIME_FEATURE_10613 = {
    "attributes": {
        "OBJECTID": 10613,
        "DR": "260037193",
        "Type": "CRIMES AGAINST PROPERTY",
        "Category": "MOTOR VEHICLE THEFT",
        "CrimeType": "MOTOR VEHICLE THEFT",
        "ReportedDateTime": "08/18/2026 05:23 PM",
        "ReportedDateTimeDate": 1787098980000,
        "Address": "1300 BLOCK PETERSON AV",
        "Division": "WEST",
        "Beat": "5",
        "ReportingDistrict": "383",
        "DaysOld": 1,
        "DayOfWeek": "TUESDAY",
        "HourOfDay": 17,
    },
    "geometry": {"x": -118.17303650471678, "y": 33.783395277232756},
}

CRIME_NEWEST_ISO = "2026-08-19T02:21:00+00:00"

CRIME_DATE_FIELDS = {"ReportedDateTimeDate"}


def _flatten(feature: dict, date_fields: set) -> dict:
    """Flatten a raw ArcGIS feature exactly as the client does at fetch."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, date_fields)


SLA_ROWS = [
    _flatten(f, SLA_DATE_FIELDS) for f in (SLA_FEATURE_343, SLA_FEATURE_7093, SLA_FEATURE_7238)
]
CRIME_ROWS = [
    _flatten(f, CRIME_DATE_FIELDS)
    for f in (CRIME_FEATURE_10616, CRIME_FEATURE_10617, CRIME_FEATURE_10613)
]

LIVE_FIXTURE_COORDS = (
    (SLA_ROWS[0]["latitude"], SLA_ROWS[0]["longitude"]),
    (SLA_ROWS[1]["latitude"], SLA_ROWS[1]["longitude"]),
    (SLA_ROWS[2]["latitude"], SLA_ROWS[2]["longitude"]),
    (CRIME_ROWS[0]["latitude"], CRIME_ROWS[0]["longitude"]),
    (CRIME_ROWS[1]["latitude"], CRIME_ROWS[1]["longitude"]),
    (CRIME_ROWS[2]["latitude"], CRIME_ROWS[2]["longitude"]),
)

# Downtown Long Beach WGS84 (geocoder stub for null-geometry rows).
_GEOCODED = (33.7695, -118.1930)

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


# ---------------------------------------------------------------------------
# Spatial invariants (no registry needed)
# ---------------------------------------------------------------------------


class TestLongBeachSpatial:
    def test_city_id_constant_is_the_leaf_string(self):
        assert LONG_BEACH_CITY_ID == "long_beach"

    def test_metro_bbox_sanity(self):
        assert LONG_BEACH_METRO_BBOX["min_lat"] < LONG_BEACH_METRO_BBOX["max_lat"]
        assert LONG_BEACH_METRO_BBOX["min_lng"] < LONG_BEACH_METRO_BBOX["max_lng"]

    def test_metro_contains_known_places(self):
        assert is_in_long_beach_metro(33.7695, -118.1930) is True  # Downtown Shoreline
        assert is_in_long_beach_metro(33.7590, -118.1525) is True  # Belmont Shore
        assert is_in_long_beach_metro(33.7560, -118.1670) is True  # Naples canals
        assert is_in_long_beach_metro(33.7810, -118.1745) is True  # Cambodia Town
        assert is_in_long_beach_metro(33.8195, -118.1900) is True  # Bixby Knolls
        assert is_in_long_beach_metro(33.8530, -118.1935) is True  # North Long Beach

    def test_metro_rejects_null_and_foreign(self):
        assert is_in_long_beach_metro(None, None) is False
        assert is_in_long_beach_metro(33.7695, None) is False
        assert is_in_long_beach_metro(None, -118.1930) is False
        assert is_in_long_beach_metro(34.0522, -118.2437) is False  # Los Angeles
        assert is_in_long_beach_metro(33.6603, -117.9988) is False  # Costa Mesa
        # junk off-map geocodes (observed x≈-138/y≈27 outside-city tail):
        assert is_in_long_beach_metro(27.196, -138.152) is False
        # the null-island shape served by failed source geocodes:
        assert is_in_long_beach_metro(-0.0000946, -0.0000946) is False

    def test_live_fixture_coords_sit_inside_the_metro_bbox(self):
        for lat, lng in LIVE_FIXTURE_COORDS:
            assert is_in_long_beach_metro(lat, lng), (lat, lng)

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in LONG_BEACH_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= LONG_BEACH_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= LONG_BEACH_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= LONG_BEACH_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= LONG_BEACH_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in LONG_BEACH_SUBMARKETS.items():
            bbox = LONG_BEACH_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in LONG_BEACH_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(LONG_BEACH_SUBMARKETS)

    def test_division_centers_sit_inside_their_bbox(self):
        assert 4 <= len(LONG_BEACH_DIVISION_BBOXES) <= 10
        assert set(LONG_BEACH_DIVISION_BBOXES) == set(LONG_BEACH_DIVISIONS)
        for name, meta in LONG_BEACH_DIVISIONS.items():
            assert meta.city_id == "long_beach"
            bbox = LONG_BEACH_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_submarket_count_in_leaf_band(self):
        assert 6 <= len(LONG_BEACH_SUBMARKETS) <= 10

    def test_required_real_neighborhoods_present(self):
        for name in (
            "Downtown Shoreline",
            "Belmont Shore",
            "Naples",
            "Cambodia Town",
            "Bixby Knolls",
            "Wrigley",
            "California Heights",
            "North Long Beach",
        ):
            assert name in LONG_BEACH_SUBMARKETS, name

    def test_submarkets_carry_the_long_beach_city_id_and_all_meta_fields(self):
        assert {m.city_id for m in LONG_BEACH_SUBMARKETS.values()} == {"long_beach"}
        for name, meta in LONG_BEACH_SUBMARKETS.items():
            assert isinstance(meta, SubmarketMeta), name
            for field in _SUBMARKET_FIELDS:
                value = getattr(meta, field)
                assert value is not None, f"{name}.{field}"
                if field == "description":
                    assert len(value) > 20, name

    def test_city_id_and_registration_shape(self):
        assert REGISTRATION.metro_bbox is LONG_BEACH_METRO_BBOX
        assert REGISTRATION.submarkets is LONG_BEACH_SUBMARKETS
        assert REGISTRATION.division_bboxes is LONG_BEACH_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_long_beach_metro

    def test_greater_metro_alias(self):
        assert is_in_greater_long_beach_metro is is_in_long_beach_metro


# ---------------------------------------------------------------------------
# Field map mechanics
# ---------------------------------------------------------------------------


class TestLongBeachFieldMaps:
    def test_sla_map_reads_live_columns(self):
        row = SLA_ROWS[0]
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "BU21523715"
        assert first_mapped(row, SLA_FIELD_MAP, "dba") == "Martin Logistics"
        assert first_mapped(row, SLA_FIELD_MAP, "premises_name") == "Martin Logistics"
        assert first_mapped(row, SLA_FIELD_MAP, "license_type") == "Business Office"
        assert first_mapped(row, SLA_FIELD_MAP, "status") == "Active"
        assert first_mapped(row, SLA_FIELD_MAP, "effective_date") == SLA_ISSDTTM_ISO_343
        assert first_mapped(row, SLA_FIELD_MAP, "address_street") == "2710 OREGON AVE "
        assert first_mapped(row, SLA_FIELD_MAP, "zipcode") == "90806"
        assert first_mapped(row, SLA_FIELD_MAP, "borough") == 7

    def test_sla_license_type_falls_back_to_classdesc(self):
        row = dict(SLA_ROWS[1])
        row["LICCATDESC"] = ""
        assert first_mapped(row, SLA_FIELD_MAP, "license_type") == "Contractors"

    def test_sla_dba_falls_through_when_absent(self):
        # FEATURE_7093 carries DBANAME null (sole-holder rows publish no
        # trade name; FULLNAME is the person and is dropped PII).
        assert SLA_ROWS[1]["DBANAME"] is None
        assert first_mapped(SLA_ROWS[1], SLA_FIELD_MAP, "dba") is None

    def test_crime_map_reads_live_columns(self):
        row = CRIME_ROWS[0]
        assert first_mapped(row, CRIME_FIELD_MAP, "incident_id") == "260037217"
        assert first_mapped(row, CRIME_FIELD_MAP, "offense_type") == "MOTOR VEHICLE THEFT"
        assert first_mapped(row, CRIME_FIELD_MAP, "reported_date") == CRIME_NEWEST_ISO
        assert first_mapped(row, CRIME_FIELD_MAP, "borough") == "EAST"

    def test_crime_incident_id_falls_back_to_objectid(self):
        row = {"DR": "", "OBJECTID": 10616}
        assert first_mapped(row, CRIME_FIELD_MAP, "incident_id") == 10616

    def test_maps_declare_no_native_coordinate_candidates(self):
        # Coordinates come ONLY from the outSR=4326 geometry lift — the
        # layers publish no coordinate attribute columns, so none may be
        # mapped as degrees.
        for field_map in (SLA_FIELD_MAP, CRIME_FIELD_MAP):
            mapped = {c for cols in field_map.values() for c in cols}
            assert "latitude" not in mapped
            assert "longitude" not in mapped

    def test_pii_and_nonaddress_columns_never_become_candidates(self):
        mapped = {c for fm in (SLA_FIELD_MAP, CRIME_FIELD_MAP) for cols in fm.values() for c in cols}
        assert mapped
        for col in DROPPED_PII_COLUMNS:
            assert col not in mapped
        for col in DROPPED_NONADDRESS_COLUMNS:
            assert col not in mapped
        assert DROPPED_PII_COLUMNS == ("FULLNAME",)

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"sla": SLA_FIELD_MAP, "crime": CRIME_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Long Beach, CA"
        assert LONG_BEACH_GEOCODE_CONTEXT == "Long Beach, CA"


# ---------------------------------------------------------------------------
# ArcGISClient flatten contract (real client code, no network)
# ---------------------------------------------------------------------------


class TestArcgisFlatten:
    def test_sla_geometry_lifts_to_wgs84_lat_lng_keys(self):
        row = SLA_ROWS[0]
        assert row["latitude"] == pytest.approx(33.806526607179286)
        assert row["longitude"] == pytest.approx(-118.2010133737972)

    def test_crime_geometry_lifts_to_wgs84_lat_lng_keys(self):
        row = CRIME_ROWS[1]
        assert row["latitude"] == pytest.approx(33.793573100895394)
        assert row["longitude"] == pytest.approx(-118.180638379231)

    def test_sla_epoch_ms_dates_flatten_to_iso(self):
        for row in SLA_ROWS:
            assert row["MILESTONEDATE"] == SLA_MILESTONE_ISO
        assert SLA_ROWS[0]["ISSDTTM"] == SLA_ISSDTTM_ISO_343
        assert SLA_ROWS[1]["ISSDTTM"] == "2017-02-07T08:00:00+00:00"
        assert SLA_ROWS[2]["ISSDTTM"] == "2017-07-01T08:00:00+00:00"

    def test_crime_epoch_ms_date_flattens_to_iso(self):
        assert CRIME_ROWS[0]["ReportedDateTimeDate"] == CRIME_NEWEST_ISO
        assert CRIME_ROWS[1]["ReportedDateTimeDate"] == "2026-08-19T02:10:00+00:00"
        assert CRIME_ROWS[2]["ReportedDateTimeDate"] == "2026-08-19T00:23:00+00:00"
        # ReportedDateTime is a plain string — untouched by the flatten.
        assert CRIME_ROWS[0]["ReportedDateTime"] == "08/18/2026 07:21 PM"

    def test_source_padding_is_preserved_verbatim(self):
        assert SLA_ROWS[0]["SITELOCATION"] == "2710 OREGON AVE "
        assert SLA_ROWS[0]["ZIP"] == "90806"


# ---------------------------------------------------------------------------
# Producer path with the Long Beach field maps injected (no spine registration)
# ---------------------------------------------------------------------------


@pytest.fixture
def sla():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        return SLALicensesProducer()


@pytest.fixture
def crime():
    with patch("src.producers.crime_incidents_producer.BaseKafkaProducer"):
        from src.producers.crime_incidents_producer import CrimeIncidentsProducer

        return CrimeIncidentsProducer()


def _patch_resolve_sla(monkeypatch, geocode_point=None):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP["sla"],
    )
    monkeypatch.setattr(
        "src.spatial.geocoder.geocode_row_if_declared",
        lambda *args, **kwargs: geocode_point,
    )


def _patch_resolve_crime(monkeypatch):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP["crime"],
    )


class TestLongBeachSlaParsing:
    def test_martin_logistics_row_parses_all_fields(self, sla, monkeypatch):
        _patch_resolve_sla(monkeypatch)
        event = sla.parse_socrata_row(SLA_ROWS[0], city_id="long_beach")
        assert event is not None
        assert event.license_id == "BU21523715"
        assert event.dba == "Martin Logistics"
        assert event.premises_name == "Martin Logistics"
        assert event.license_type == "Business Office"
        assert event.license_status == "Active"
        assert event.address == "2710 OREGON AVE "
        assert event.effective_date is not None
        assert event.effective_date.isoformat() == SLA_ISSDTTM_ISO_343
        assert event.expiration_date is None
        assert event.source_neighborhood == "7"

    def test_geometry_row_carries_wgs84_coords_h3_and_metro_containment(
        self, sla, monkeypatch
    ):
        _patch_resolve_sla(monkeypatch)
        event = sla.parse_socrata_row(SLA_ROWS[0], city_id="long_beach")
        assert event is not None
        assert event.latitude == pytest.approx(33.806526607179286)
        assert event.longitude == pytest.approx(-118.2010133737972)
        expected = H3SpatialIndexer.get_multi_res_hierarchy(event.latitude, event.longitude)
        assert event.h3_res7 == expected["h3_res7"]
        assert event.h3_res8 == expected["h3_res8"]
        assert event.h3_res9 == expected["h3_res9"]
        assert is_in_long_beach_metro(event.latitude, event.longitude) is True

    def test_schroeder_row_parses_with_native_geometry(self, sla, monkeypatch):
        _patch_resolve_sla(monkeypatch)
        event = sla.parse_socrata_row(SLA_ROWS[1], city_id="long_beach")
        assert event is not None
        assert event.license_id == "BU21700669"
        assert event.license_type == "Contracting – Building"
        assert event.address == "228 EUCLID AVE "
        assert event.latitude == pytest.approx(33.76487479004518)
        assert event.longitude == pytest.approx(-118.14885015726114)
        assert event.h3_res7 is not None
        assert is_in_long_beach_metro(event.latitude, event.longitude) is True

    def test_all_three_fixtures_share_the_co_newest_watermark(self, sla, monkeypatch):
        _patch_resolve_sla(monkeypatch)
        events = [
            sla.parse_socrata_row(row, city_id="long_beach") for row in SLA_ROWS
        ]
        assert all(e is not None for e in events)
        assert {e.license_id for e in events} == {
            "BU21523715",
            "BU21700669",
            "BU21704484",
        }
        # Distinct sites occupy distinct res-9 cells.
        assert len({e.h3_res9 for e in events}) == 3
        # North Long Beach (5322 Cedar Ave) apartment-house license.
        assert events[2].license_type == "Apartment House"
        assert events[2].latitude == pytest.approx(33.85301658907985)

    def test_row_without_any_id_is_dropped(self, sla, monkeypatch):
        _patch_resolve_sla(monkeypatch)
        row = {k: v for k, v in SLA_ROWS[0].items() if k != "LICENSENO"}
        assert sla.parse_socrata_row(row, city_id="long_beach") is None

    def test_null_geometry_row_resolves_through_the_geocode_fallback(
        self, sla, monkeypatch
    ):
        """The layer serves a ~0.1% null-geometry tail (2/2000 sampled).
        Shape-verbatim synthetic variant of FEATURE_343; the ADR-0004
        geocode supplement on SITELOCATION resolves it. Result-level
        assertions only — no hook-call counts."""
        _patch_resolve_sla(monkeypatch, geocode_point=_GEOCODED)
        raw = {**SLA_FEATURE_343, "geometry": None}
        row = _flatten(raw, SLA_DATE_FIELDS)
        assert "latitude" not in row and "longitude" not in row
        event = sla.parse_socrata_row(row, city_id="long_beach")
        assert event is not None
        assert event.license_id == "BU21523715"
        assert event.latitude == pytest.approx(_GEOCODED[0])
        assert event.longitude == pytest.approx(_GEOCODED[1])
        assert event.h3_res7 is not None
        assert is_in_long_beach_metro(event.latitude, event.longitude) is True

    def test_null_geometry_row_with_geocode_failure_keeps_null_coords(
        self, sla, monkeypatch
    ):
        _patch_resolve_sla(monkeypatch)
        raw = {**SLA_FEATURE_343, "geometry": None}
        row = _flatten(raw, SLA_DATE_FIELDS)
        event = sla.parse_socrata_row(row, city_id="long_beach")
        assert event is not None
        assert event.license_id == "BU21523715"
        assert event.latitude is None and event.longitude is None
        assert event.h3_res7 is None and event.h3_res8 is None and event.h3_res9 is None

    def test_future_issdttm_sentinel_never_becomes_the_watermark(
        self, sla, monkeypatch
    ):
        """ISSDTTM is future-date sentinel-poisoned live (max
        38886854400000 = year 3202). The event honestly carries the parsed
        effective_date, and the feed's watermark stays MILESTONEDATE —
        the scheduler's future guard pins to the sane column."""
        _patch_resolve_sla(monkeypatch)
        raw = {
            "attributes": {
                **SLA_FEATURE_343["attributes"],
                "ISSDTTM": SLA_SENTINEL_ISSDTTM,
            },
            "geometry": SLA_FEATURE_343["geometry"],
        }
        row = _flatten(raw, SLA_DATE_FIELDS)
        event = sla.parse_socrata_row(row, city_id="long_beach")
        assert event is not None
        assert event.effective_date is not None
        assert event.effective_date.year == 3202
        assert is_future_watermark(event.effective_date, datetime.now(UTC)) is True
        spec = get_long_beach_dataset("sla")
        assert spec.watermark_col == "MILESTONEDATE"
        where = build_where(
            base_where=spec.where,
            watermark_col=spec.watermark_col,
            high_watermark=SLA_MILESTONE_ISO,
            endpoint=spec.endpoint,
            incremental=True,
            snapshot=False,
        )
        assert where is not None
        assert "MILESTONEDATE >" in where
        assert "ISSDTTM" not in where


class TestLongBeachCrimeParsing:
    def test_worsham_row_parses_all_fields(self, crime, monkeypatch):
        _patch_resolve_crime(monkeypatch)
        event = crime.parse_socrata_row(CRIME_ROWS[0], city_id="long_beach")
        assert event is not None
        assert event.incident_id == "260037217"
        assert event.offense_type == "MOTOR VEHICLE THEFT"
        assert event.offense_class == "PART1"
        assert event.reported_date is not None
        assert event.reported_date.isoformat() == CRIME_NEWEST_ISO
        assert event.source_neighborhood == "EAST"
        assert event.latitude == pytest.approx(33.82819274482639)
        assert event.longitude == pytest.approx(-118.14619536954173)

    def test_geometry_row_carries_h3_and_metro_containment(self, crime, monkeypatch):
        _patch_resolve_crime(monkeypatch)
        event = crime.parse_socrata_row(CRIME_ROWS[0], city_id="long_beach")
        assert event is not None
        expected = H3SpatialIndexer.get_multi_res_hierarchy(event.latitude, event.longitude)
        assert event.h3_res7 == expected["h3_res7"]
        assert event.h3_res8 == expected["h3_res8"]
        assert event.h3_res9 == expected["h3_res9"]
        assert is_in_long_beach_metro(event.latitude, event.longitude) is True

    def test_ml_king_row_parses_with_native_geometry(self, crime, monkeypatch):
        _patch_resolve_crime(monkeypatch)
        event = crime.parse_socrata_row(CRIME_ROWS[1], city_id="long_beach")
        assert event is not None
        assert event.incident_id == "260037216"
        assert event.source_neighborhood == "WEST"
        assert event.latitude == pytest.approx(33.793573100895394)
        assert event.longitude == pytest.approx(-118.180638379231)
        assert event.h3_res7 is not None

    def test_peterson_row_lands_in_the_cambodia_town_band(self, crime, monkeypatch):
        _patch_resolve_crime(monkeypatch)
        event = crime.parse_socrata_row(CRIME_ROWS[2], city_id="long_beach")
        assert event is not None
        assert event.incident_id == "260037193"
        # 1300 BLOCK PETERSON AV sits inside the Cambodia Town division bbox
        # (asserted on the bbox, not on ingest-time division resolution).
        bbox = LONG_BEACH_DIVISION_BBOXES["CAMBODIA_TOWN"]
        assert bbox["min_lat"] <= event.latitude <= bbox["max_lat"]
        assert bbox["min_lng"] <= event.longitude <= bbox["max_lng"]

    def test_three_fixtures_carry_distinct_cells_and_report_numbers(
        self, crime, monkeypatch
    ):
        _patch_resolve_crime(monkeypatch)
        events = [
            crime.parse_socrata_row(row, city_id="long_beach") for row in CRIME_ROWS
        ]
        assert all(e is not None for e in events)
        assert {e.incident_id for e in events} == {
            "260037217",
            "260037216",
            "260037193",
        }
        assert len({e.h3_res9 for e in events}) == 3

    def test_row_without_any_id_is_dropped(self, crime, monkeypatch):
        _patch_resolve_crime(monkeypatch)
        row = {k: v for k, v in CRIME_ROWS[0].items() if k not in ("DR", "OBJECTID")}
        assert crime.parse_socrata_row(row, city_id="long_beach") is None


# ---------------------------------------------------------------------------
# Feed specs (leaf-local get_dataset mirror)
# ---------------------------------------------------------------------------


class TestLongBeachFeedSpec:
    def test_exactly_the_two_verified_feeds_are_registered(self):
        assert set(LONG_BEACH_FEED_SPECS) == {"crime", "sla"}

    def test_sla_spec_matches_live_layer(self):
        spec = get_long_beach_dataset("sla")
        assert spec.platform == "arcgis"
        assert spec.endpoint == LONG_BEACH_SLA_ENDPOINT
        assert spec.watermark_col == "MILESTONEDATE"
        assert spec.id_keys == ["LICENSENO", "OBJECTID"]
        assert spec.producer_key == "sla"
        assert spec.ingestion_mode == "incremental"
        assert spec.where == "OUTSIDECITY='No'"
        assert spec.order_by == "MILESTONEDATE DESC"
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 3
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Long Beach, CA"
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.topic == "raw.municipal.sla"
        assert spec.interval_seconds == 600.0

    def test_crime_spec_matches_live_layer(self):
        spec = get_long_beach_dataset("crime")
        assert spec.platform == "arcgis"
        assert spec.endpoint == LONG_BEACH_CRIME_ENDPOINT
        assert spec.watermark_col == "ReportedDateTimeDate"
        assert spec.id_keys == ["DR", "OBJECTID"]
        assert spec.producer_key == "crime"
        assert spec.order_by == "ReportedDateTimeDate DESC"
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 14
        # Native coordinates satisfy the ADR-0004 crime gate — no geocode.
        assert spec.needs_geocode is False
        assert spec.field_map == CRIME_FIELD_MAP
        assert spec.topic == "raw.municipal.crime"
        assert spec.interval_seconds == 1800.0

    def test_specs_accept_the_string_input_without_any_enum(self):
        # Spine-stable: the leaf-local mirror accepts the plain feed string.
        assert get_long_beach_dataset("sla").producer_key == "sla"
        assert get_long_beach_dataset("crime").producer_key == "crime"

    @pytest.mark.parametrize("absent_feed", ["permits", "311", "deeds"])
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'long_beach'.*available"):
            get_long_beach_dataset(absent_feed)

    def test_endpoints_are_the_probed_services6_layers(self):
        assert "services6.arcgis.com/yCArG7wGXGyWLqav" in LONG_BEACH_SLA_ENDPOINT
        assert "Business_Licenses_Public_View/FeatureServer/0" in LONG_BEACH_SLA_ENDPOINT
        assert "services6.arcgis.com/yCArG7wGXGyWLqav" in LONG_BEACH_CRIME_ENDPOINT
        assert "Police_Crime_Mapping/FeatureServer/0" in LONG_BEACH_CRIME_ENDPOINT
