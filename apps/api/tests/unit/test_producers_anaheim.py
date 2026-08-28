"""Unit tests for the Anaheim, CA leaf (US-249): spatial module + field
maps + producer parse wiring.

Anaheim is a TWO-FEED metro on the city AGOL org
(``services3.arcgis.com/hPs600I3X0RTaaaq``, listed on the official
``anaheim.opendata.arcgis.com`` Hub): Accela_Building_Permits (Tier 1,
191,477 rows) and the ActiveBusinessLicenses snapshot (15,263 rows). 311
(code-enforcement family only), crime (7-day rolling table), full-history
Business_Licenses (mislabeled-SR feet trap), and deeds (no OC bulk feed)
stay unregistered — rejection evidence lives in the city module docstring.

Tests pass WITHOUT a spine registration (no CityId.ANAHEIM, no REGISTRY
assertions — "anaheim" stays a plain string). Spine-stable per the leaf
contract: no division/borough-resolution assertions and no geocode-hook
call-count assertions (both change when the spine lands).

Fixtures captured byte-verbatim 2026-08-28:

* permits — ``Accela_Building_Permits/FeatureServer/0`` newest non-future
  rows (``where=permitissued < CURRENT_TIMESTAMP``,
  ``orderByFields=permitissued DESC``, ``outSR=4326``); newest watermark
  ``1785974400000`` = 2026-08-06T00:00:00+00:00. The host honors outSR, so
  geometry arrives as WGS84 degrees even though the store SR is WKID 2230
  state-plane feet.
* sla — ``ActiveBusinessLicenses/FeatureServer/0`` newest rows
  (``orderByFields=applicationdate DESC``, ``outSR=4326``); newest
  applicationdate "2026-06-02" (DateOnly string). Geometry is degrees or
  absent; objectid 29286 carries neither geometry nor address and rides the
  producer's null-coordinate tolerance (DC non-spatial-registry precedent).

Fixtures are RAW ArcGIS features (attributes + geometry); the tests run the
real ``ArcGISClient._flatten_feature`` lift — geometry to latitude/longitude,
epoch-ms to ISO (permits' esriFieldTypeDate set only; the license layer's
DateOnly strings are not date-discovered and pass through untouched) —
before parsing, exactly as the live producer path does.
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_anaheim import (
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.schemas.models import JobType
from src.spatial.cities.anaheim import (
    ANAHEIM_CITY_ID,
    ANAHEIM_DIVISION_BBOXES,
    ANAHEIM_DIVISIONS,
    ANAHEIM_FEED_SPECS,
    ANAHEIM_GEOCODE_CONTEXT,
    ANAHEIM_METRO_BBOX,
    ANAHEIM_PERMITS_ENDPOINT,
    ANAHEIM_SLA_ENDPOINT,
    ANAHEIM_SUBMARKETS,
    REGISTRATION,
    get_anaheim_dataset,
    is_in_anaheim_metro,
    is_in_greater_anaheim_metro,
)

PERMITS_DATE_FIELDS = {"permitissued", "applicationreceived", "permitfinalized"}


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


def _flatten_permits(feature):
    """Run the real ArcGIS flatten lift over a raw captured permit feature.

    ``date_fields`` is what the client discovers from the live layer's
    metadata: permitissued/applicationreceived/permitfinalized are
    esriFieldTypeDate.
    """
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, PERMITS_DATE_FIELDS)


def _flatten_sla(feature):
    """The license layer exposes NO esriFieldTypeDate columns (DateOnly
    strings), so the live discovery passes an empty date-field set."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, set())


# ---------------------------------------------------------------------------
# Byte-verbatim permit fixtures — 2026-08-28 probe (newest non-future rows).
# jobvaluation is a source string; "-15536" is a real ADU garage-conversion
# credit row.
# ---------------------------------------------------------------------------
_PERMIT_188406 = {
    "attributes": {
        "OBJECTID": 188406,
        "casenumber": "BLD2026-00346",
        "casestatus": "Issued",
        "address": "724 S Plymouth Pl B Anaheim, Ca 92806",
        "description": "(Jadu) Residential Addition: Convert 456 Sq. Ft. Attached Garage Into An Accessory Dwelling Unit. (1bd/2ba) Ref: Bld2026-03480",
        "applicationreceived": 1769472000000,
        "permitissued": 1785974400000,
        "permitfinalized": None,
        "parcel": "25303126",
        "censuscode": "434 Additions, Alterations, and Conversions - Residential",
        "comres": "Residential - Single Family",
        "jobvaluation": "-15536",
        "ownerbuilder": "Yes",
        "plancheck": "Yes",
        "typeofwork": "Residential Addition",
        "globalid": "41433b3e-6399-4e55-8523-a560a33006a5",
        "contractorsname": "",
        "contractorsphone": "",
    },
    "geometry": {
        "x": -117.88741025000219,
        "y": 33.83167048000114,
    },
}

_PERMIT_191671 = {
    "attributes": {
        "OBJECTID": 191671,
        "casenumber": "BLD2026-03273",
        "casestatus": "Issued",
        "address": "6010 E Hillcrest Cir Anaheim, Ca 92807",
        "description": "Photovoltaic System: Install Residential Roof Mounted Solar (20) Modules, (23) Microinverters And A 125 Amp Sub Panel",
        "applicationreceived": 1784073600000,
        "permitissued": 1785888000000,
        "permitfinalized": None,
        "parcel": "36312131",
        "censuscode": "434 Additions, Alterations, and Conversions - Residential",
        "comres": "Residential - Single Family",
        "jobvaluation": "25000",
        "ownerbuilder": "No",
        "plancheck": "Yes",
        "typeofwork": "Photovoltaic System",
        "globalid": "08b2051f-d30b-4a36-8969-32c71d97a2f4",
        "contractorsname": "Unlimited Solar Energy",
        "contractorsphone": "(949) 374 1560",
    },
    "geometry": {
        "x": -117.77972190000216,
        "y": 33.84583501000117,
    },
}

_PERMIT_191940 = {
    "attributes": {
        "OBJECTID": 191940,
        "casenumber": "BLD2026-03526",
        "casestatus": "Issued",
        "address": "1313 S Harbor Blvd 7600 Anaheim, Ca 92802",
        "description": "Dlr - Matterhorn Bobsleds - Electrical: Install Disconnect Switch For Sump Pump Controller.",
        "applicationreceived": 1785369600000,
        "permitissued": 1785888000000,
        "permitfinalized": None,
        "parcel": "08219019",
        "censuscode": "",
        "comres": "Commercial",
        "jobvaluation": None,
        "ownerbuilder": "Yes",
        "plancheck": "Yes",
        "typeofwork": "Trade Only",
        "globalid": "089d9ef2-c60a-465b-bcb1-353cace5fba0",
        "contractorsname": "",
        "contractorsphone": "",
    },
    "geometry": {
        "x": -117.91787083000217,
        "y": 33.813015360001145,
    },
}

_NEWEST_ISSUED_ISO = "2026-08-06T00:00:00+00:00"

# ---------------------------------------------------------------------------
# Byte-verbatim license fixtures — 2026-08-28 probe (newest applicationdate
# rows on the Active snapshot). Dates are DateOnly strings; geometry is
# degrees or absent.
# ---------------------------------------------------------------------------
_LICENSE_29285 = {
    "attributes": {
        "objectid": 29285,
        "globalid": "134ee610-fc9c-467c-873a-e20b723a87f8",
        "casenumber": "BUS2026-01640",
        "businessname": "Tenco Solar Inc",
        "casestatus": "Active",
        "address": "8141 E Kaiser Blvd 106\nAnaheim, Ca 92808",
        "description": "Administrative Office For Electrical & Solar Equipment Contractor",
        "applicationdate": "2026-06-02",
        "opendate": "2025-05-01",
        "expirationdate": "2027-06-08",
        "ownership": "Corporation",
        "naicscode": "238210 Electrical Contractors And Other Wiring Installation",
        "ownername": "DANIEL MC INTYRE, PRESIDENT",
        "entityname": "Tenco Solar Inc",
    },
    "geometry": {
        "x": -117.74469120000217,
        "y": 33.866454430001184,
    },
}

_LICENSE_29286 = {
    "attributes": {
        "objectid": 29286,
        "globalid": "ce6a5bb3-3d86-4c55-915d-f5d4f7fe6e93",
        "casenumber": "BUS2026-01642",
        "businessname": "Kings Abrasive Blasting",
        "casestatus": "Active",
        "address": None,
        "description": "Home Office Only For Off-site Power Wahing Services  (No Employees)",
        "applicationdate": "2026-06-02",
        "opendate": "2026-06-02",
        "expirationdate": "2027-06-02",
        "ownership": "Sole Proprietor",
        "naicscode": "561110 Office Administrative Services",
        "ownername": "JULIAN HUERTA",
        "entityname": " ",
    },
}

_LICENSE_29287 = {
    "attributes": {
        "objectid": 29287,
        "globalid": "02c09f8f-15e9-4a17-b71e-a1c832b3177d",
        "casenumber": "BUS2026-01645",
        "businessname": "Level Up",
        "casestatus": "Active",
        "address": "940 E Orangethorpe Ave E\nAnaheim, Ca 92801",
        "description": "Warehouse And Storage With An Accessory Office For Contruction Materials Supplier (No Employees) ***sublease***",
        "applicationdate": "2026-06-02",
        "opendate": "2026-01-30",
        "expirationdate": "2027-01-30",
        "ownership": "Limited Liability Company",
        "naicscode": "444190 Other Building Material Dealers",
        "ownername": "ROGELIO SOLIS HERRERA, OPERATIONS MANAGER",
        "entityname": "Andrew Mishler Materials Llc",
    },
    "geometry": {
        "x": -117.90940901000218,
        "y": 33.85824396000116,
    },
}

_NEWEST_APPLICATION_NAIVE_ISO = "2026-06-02T00:00:00"


class TestAnaheimSpatial:
    def test_metro_bbox_sanity(self):
        assert ANAHEIM_METRO_BBOX["min_lat"] < ANAHEIM_METRO_BBOX["max_lat"]
        assert ANAHEIM_METRO_BBOX["min_lng"] < ANAHEIM_METRO_BBOX["max_lng"]

    def test_is_in_anaheim_metro_rejects_missing_coordinates(self):
        assert is_in_anaheim_metro(None, None) is False
        assert is_in_anaheim_metro(33.8355, None) is False
        assert is_in_anaheim_metro(None, -117.9140) is False

    def test_is_in_anaheim_metro_rejects_other_cities(self):
        assert is_in_anaheim_metro(34.0522, -118.2437) is False   # Los Angeles
        assert is_in_anaheim_metro(33.7456, -117.8833) is False   # Santa Ana
        assert is_in_anaheim_metro(33.9533, -117.3962) is False   # Riverside
        assert is_in_anaheim_metro(32.7157, -117.1611) is False   # San Diego

    def test_downtown_anchors_are_contained(self):
        assert is_in_anaheim_metro(33.8355, -117.9140)  # Center City Promenade
        assert is_in_anaheim_metro(33.8121, -117.9180)  # Disneyland
        assert is_in_anaheim_metro(33.8074, -117.8839)  # Honda Center
        assert is_in_anaheim_metro(33.8003, -117.8827)  # Angel Stadium
        assert is_in_anaheim_metro(33.8157, -117.7642)  # Anaheim Hills core

    def test_live_fixture_coordinates_are_contained(self):
        for feature in (_PERMIT_188406, _PERMIT_191671, _PERMIT_191940,
                        _LICENSE_29285, _LICENSE_29287):
            assert is_in_anaheim_metro(
                feature["geometry"]["y"], feature["geometry"]["x"]
            )

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in ANAHEIM_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= ANAHEIM_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= ANAHEIM_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= ANAHEIM_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= ANAHEIM_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in ANAHEIM_SUBMARKETS.items():
            bbox = ANAHEIM_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in ANAHEIM_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(ANAHEIM_SUBMARKETS)

    def test_submarkets_carry_the_anaheim_city_id(self):
        assert {m.city_id for m in ANAHEIM_SUBMARKETS.values()} == {"anaheim"}

    def test_city_id_and_registration_shape(self):
        assert ANAHEIM_CITY_ID == "anaheim"
        assert REGISTRATION.metro_bbox is ANAHEIM_METRO_BBOX
        assert REGISTRATION.submarkets is ANAHEIM_SUBMARKETS
        assert REGISTRATION.division_bboxes is ANAHEIM_DIVISION_BBOXES
        assert REGISTRATION.contains is is_in_anaheim_metro
        assert len(REGISTRATION.divisions) == 6
        assert len(ANAHEIM_SUBMARKETS) == 10

    def test_required_real_neighborhoods_present(self):
        assert set(ANAHEIM_SUBMARKETS) == {
            "Downtown Anaheim",
            "The Colony",
            "Disneyland Resort & Convention Center",
            "Harbor Boulevard Hotel Belt",
            "Honda Center & Angel Stadium",
            "West Anaheim Magnolia Belt",
            "Brookhurst Southwest",
            "Anaheim Canyon Industrial",
            "Nohl Ranch Hills",
            "Weir Canyon East",
        }

    def test_greater_metro_alias(self):
        assert is_in_greater_anaheim_metro is is_in_anaheim_metro


class TestAnaheimFieldMaps:
    def test_permits_map_reads_live_columns(self):
        assert PERMITS_FIELD_MAP["job_id"] == ["casenumber", "OBJECTID"]
        assert PERMITS_FIELD_MAP["issuance_date"] == ["permitissued"]
        assert PERMITS_FIELD_MAP["filing_date"] == ["applicationreceived"]
        assert PERMITS_FIELD_MAP["status"] == ["casestatus"]
        assert PERMITS_FIELD_MAP["job_type"] == ["typeofwork"]
        assert PERMITS_FIELD_MAP["cost"] == ["jobvaluation"]
        assert PERMITS_FIELD_MAP["address_street"] == ["address"]

    def test_sla_map_reads_live_columns(self):
        assert SLA_FIELD_MAP["license_id"] == ["casenumber", "objectid"]
        assert SLA_FIELD_MAP["dba"] == ["businessname"]
        assert SLA_FIELD_MAP["premises_name"] == ["businessname"]
        assert SLA_FIELD_MAP["license_type"] == ["naicscode"]
        assert SLA_FIELD_MAP["status"] == ["casestatus"]
        assert SLA_FIELD_MAP["effective_date"] == ["applicationdate"]
        assert SLA_FIELD_MAP["expiration_date"] == ["expirationdate"]
        assert SLA_FIELD_MAP["address_street"] == ["address"]

    def test_field_map_alias_and_geocode_context(self):
        assert FIELD_MAP == {"permits": PERMITS_FIELD_MAP, "sla": SLA_FIELD_MAP}
        assert GEOCODE_CONTEXT == "Anaheim, CA"
        assert ANAHEIM_GEOCODE_CONTEXT == "Anaheim, CA"

    def test_no_coordinate_candidates_on_either_map(self):
        """Coordinates come only from the outSR=4326 geometry lift (permits
        host honors it; the Active layer stores real degrees) or the geocode
        supplement — no latitude/longitude candidates may exist."""
        for field_map in (PERMITS_FIELD_MAP, SLA_FIELD_MAP):
            assert "latitude" not in field_map
            assert "longitude" not in field_map
        for feature in (_PERMIT_188406, _LICENSE_29285):
            attrs = feature["attributes"]
            assert first_mapped(attrs, PERMITS_FIELD_MAP, "latitude") is None
            assert first_mapped(attrs, PERMITS_FIELD_MAP, "longitude") is None

    def test_opendate_is_never_a_candidate(self):
        """opendate carries year-3013/2204 future sentinels on live Active
        rows (BUS2014-01614 '3013-10-31'); effective_date maps the clean
        applicationdate instead."""
        mapped = {c for values in SLA_FIELD_MAP.values() for c in values}
        assert "opendate" not in mapped
        assert SLA_FIELD_MAP["effective_date"] == ["applicationdate"]
        assert first_mapped(_LICENSE_29285["attributes"], SLA_FIELD_MAP, "effective_date") == "2026-06-02"

    def test_pii_columns_never_become_candidates(self):
        mapped = {c for values in FIELD_MAP.values() for v in values for c in v}
        assert mapped
        for values in FIELD_MAP.values():
            for col in [c for v in values for c in v]:
                assert col not in DROPPED_PII_COLUMNS
        # The person/contractor/legal-entity name columns are exactly what is
        # dropped.
        assert {"ownername", "contractorsname", "contractorsphone",
                "entityname"} <= set(DROPPED_PII_COLUMNS)


class TestAnaheimPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_flatten_lifts_native_geometry_to_degrees(self):
        record = _flatten_permits(_PERMIT_188406)
        assert record["latitude"] == pytest.approx(33.83167048000114)
        assert record["longitude"] == pytest.approx(-117.88741025000219)

    def test_flatten_iso_normalizes_the_date_columns(self):
        record = _flatten_permits(_PERMIT_188406)
        assert record["permitissued"] == _NEWEST_ISSUED_ISO
        assert record["applicationreceived"] == "2026-01-27T00:00:00+00:00"
        assert record["permitfinalized"] is None

    def test_plymouth_negative_valuation_row_is_rejected(self, permits, monkeypatch):
        """jobvaluation is a source string and this real ADU garage-conversion
        row carries a NEGATIVE valuation ("-15536"). PermitEvent validates
        estimated_cost >= 0, so the producer rejects the row at parse — the
        honest outcome (no clamping, no fabrication)."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(_PERMIT_188406)
        assert permits.parse_socrata_row(record, city_id="anaheim") is None

    def test_hillcrest_fixture_parses_through_the_producer(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten_permits(_PERMIT_191671), city_id="anaheim")
        assert event is not None
        assert event.city_id == "anaheim"
        assert event.job_id == "BLD2026-03273"
        assert event.status == "Issued"
        assert event.estimated_cost == pytest.approx(25000.0)
        assert event.address_street == "6010 E Hillcrest Cir Anaheim, Ca 92807"
        assert event.latitude == pytest.approx(33.84583501000117)
        assert event.longitude == pytest.approx(-117.77972190000216)
        assert event.issuance_date is not None
        assert event.issuance_date.isoformat() == "2026-08-05T00:00:00+00:00"
        assert event.filing_date is not None
        assert event.source_neighborhood is None

    def test_hillcrest_fixture_indexes_h3_and_sits_in_metro(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten_permits(_PERMIT_191671), city_id="anaheim")
        assert event is not None
        assert event.estimated_cost == pytest.approx(25000.0)
        assert event.h3_res7 is not None
        assert event.h3_res8 is not None
        assert event.h3_res9 is not None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert is_in_anaheim_metro(event.latitude, event.longitude)

    def test_matterhorn_fixture_null_valuation_and_containment(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        event = permits.parse_socrata_row(_flatten_permits(_PERMIT_191940), city_id="anaheim")
        assert event is not None
        assert event.job_id == "BLD2026-03526"
        # jobvaluation null coerces to the producer's 0.0 cost convention.
        assert event.estimated_cost == 0.0
        assert event.address_street == "1313 S Harbor Blvd 7600 Anaheim, Ca 92802"
        assert is_in_anaheim_metro(event.latitude, event.longitude)

    def test_anaheim_work_types_stay_unclassified_at_the_leaf(
        self, permits, monkeypatch
    ):
        """typeofwork spellings ('Trade Only', 'Photovoltaic System',
        'Residential Addition') carry none of the producer's recognized
        codes, so they land on OT honestly. (The negative-valuation row is
        dropped before classification — see the dedicated test.)"""
        _patch_resolve(monkeypatch, "permits")
        for feature in (_PERMIT_191671, _PERMIT_191940):
            event = permits.parse_socrata_row(_flatten_permits(feature), city_id="anaheim")
            assert event is not None
            assert event.job_type == JobType.OT

    def test_job_id_falls_back_to_objectid(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(_PERMIT_191940)
        record.pop("casenumber")
        event = permits.parse_socrata_row(record, city_id="anaheim")
        assert event is not None
        assert event.job_id == "191940"

    def test_row_without_any_id_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(_PERMIT_191940)
        record.pop("casenumber")
        record.pop("OBJECTID")
        assert permits.parse_socrata_row(record, city_id="anaheim") is None

    def test_geometry_less_row_resolves_through_the_geocode_fallback(
        self, permits, monkeypatch
    ):
        """Rows arriving without geometry resolve via the ADR 0004 geocode
        supplement (needs_geocode=True). Call-args/counts are spine-volatile
        and not asserted — only the event outcome."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(_PERMIT_191671)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (33.8355, -117.9140),
        )
        event = permits.parse_socrata_row(record, city_id="anaheim")
        assert event is not None
        assert event.city_id == "anaheim"
        assert event.job_id == "BLD2026-03273"
        assert event.latitude == pytest.approx(33.8355)
        assert event.longitude == pytest.approx(-117.9140)
        assert event.h3_res7 is not None

    def test_geometry_less_row_dropped_when_geocode_fails(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(_PERMIT_191671)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="anaheim") is None

    def test_state_plane_feet_never_emit_as_degrees(self, permits, monkeypatch):
        """The store SR is WKID 2230 state-plane feet; if feet ever leaked
        into latitude/longitude (a bad future map edit or a host that stops
        honoring outSR — the full-history license layer already does this),
        the producer's projected-coordinate guard nulls them and the
        coordinate-less row falls to geocode. With geocode failing, the row
        must not carry fake degrees."""
        _patch_resolve(monkeypatch, "permits")
        record = _flatten_permits(_PERMIT_191671)
        record["latitude"] = 6090747.15     # WKID 2230 feet for this parcel
        record["longitude"] = 2235862.40
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: None,
        )
        assert permits.parse_socrata_row(record, city_id="anaheim") is None


class TestAnaheimSlaParsing:
    @pytest.fixture
    def sla(self):
        with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
            from src.producers.sla_licenses_producer import SLALicensesProducer

            return SLALicensesProducer()

    def test_flatten_lifts_native_geometry_and_skips_dateonly_strings(self):
        record = _flatten_sla(_LICENSE_29285)
        assert record["latitude"] == pytest.approx(33.866454430001184)
        assert record["longitude"] == pytest.approx(-117.74469120000217)
        # DateOnly strings are not client-discovered date fields — untouched.
        assert record["applicationdate"] == "2026-06-02"
        assert record["opendate"] == "2025-05-01"

    def test_tenco_fixture_parses_through_the_producer(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_flatten_sla(_LICENSE_29285), city_id="anaheim")
        assert event is not None
        assert event.city_id == "anaheim"
        assert event.license_id == "BUS2026-01640"
        assert event.dba == "Tenco Solar Inc"
        assert event.license_status == "Active"
        assert event.license_type == (
            "238210 Electrical Contractors And Other Wiring Installation"
        )
        assert event.effective_date is not None
        assert event.effective_date.isoformat() == _NEWEST_APPLICATION_NAIVE_ISO
        assert event.address == "8141 E Kaiser Blvd 106\nAnaheim, Ca 92808"
        assert event.latitude == pytest.approx(33.866454430001184)
        assert event.longitude == pytest.approx(-117.74469120000217)
        assert event.h3_res7 is not None
        assert is_in_anaheim_metro(event.latitude, event.longitude)

    def test_level_up_fixture_indexes_h3_and_sits_in_metro(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_flatten_sla(_LICENSE_29287), city_id="anaheim")
        assert event is not None
        assert event.license_id == "BUS2026-01645"
        assert event.dba == "Level Up"
        assert event.license_type == "444190 Other Building Material Dealers"
        assert is_in_anaheim_metro(event.latitude, event.longitude)

    def test_effective_date_never_takes_the_sentinel_opendate(self, sla, monkeypatch):
        """The layer's opendate carries year-3013/2204 sentinels on live
        Active rows; the map pins effective_date to applicationdate, so the
        parsed event year is the application year, never a sentinel year."""
        _patch_resolve(monkeypatch, "sla")
        record = _flatten_sla(_LICENSE_29285)
        record["opendate"] = "3013-10-31"  # byte-verbatim sentinel shape (BUS2014-01614)
        event = sla.parse_socrata_row(record, city_id="anaheim")
        assert event is not None
        assert event.effective_date is not None
        assert event.effective_date.year == 2026

    def test_geometry_and_address_less_row_keeps_null_coord_event(self, sla, monkeypatch):
        """objectid 29286 carries neither geometry nor address — no locator
        exists. Unlike permits, the SLA producer tolerates coordinate-less
        rows (DC non-spatial-registry precedent): the event rides with null
        latitude/longitude and null H3 cells, keyed on the license id."""
        _patch_resolve(monkeypatch, "sla")
        event = sla.parse_socrata_row(_flatten_sla(_LICENSE_29286), city_id="anaheim")
        assert event is not None
        assert event.license_id == "BUS2026-01642"
        assert event.latitude is None
        assert event.longitude is None
        assert event.h3_res7 is None

    def test_geometry_less_row_resolves_through_the_geocode_fallback(
        self, sla, monkeypatch
    ):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten_sla(_LICENSE_29287)
        record.pop("latitude")
        record.pop("longitude")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda city_id, feed_value, address, context=None: (33.8582, -117.9094),
        )
        event = sla.parse_socrata_row(record, city_id="anaheim")
        assert event is not None
        assert event.license_id == "BUS2026-01645"
        assert event.latitude == pytest.approx(33.8582)
        assert event.longitude == pytest.approx(-117.9094)

    def test_license_id_falls_back_to_objectid(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        record = _flatten_sla(_LICENSE_29285)
        record.pop("casenumber")
        event = sla.parse_socrata_row(record, city_id="anaheim")
        assert event is not None
        assert event.license_id == "29285"


class TestAnaheimFeedSpec:
    def test_permits_spec_matches_live_layer(self):
        spec = get_anaheim_dataset("permits")
        assert spec.platform == "arcgis"
        assert spec.endpoint == ANAHEIM_PERMITS_ENDPOINT
        assert spec.watermark_col == "permitissued"
        assert spec.id_keys == ["casenumber", "OBJECTID"]
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 21
        assert spec.order_by == "permitissued DESC"
        assert spec.where == "permitissued <= CURRENT_TIMESTAMP"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Anaheim, CA"
        assert spec.field_map == PERMITS_FIELD_MAP
        assert spec.topic == "raw.municipal.permits"

    def test_sla_spec_matches_live_layer(self):
        spec = get_anaheim_dataset("sla")
        assert spec.platform == "arcgis"
        assert spec.endpoint == ANAHEIM_SLA_ENDPOINT
        assert spec.watermark_col == "applicationdate"
        assert spec.id_keys == ["casenumber", "objectid"]
        assert spec.oid_field == "objectid"
        assert spec.max_record_count == 10000
        assert spec.expected_cadence_days == 90
        assert spec.order_by == "applicationdate DESC"
        assert spec.interval_seconds == 300.0
        assert spec.ingestion_mode == "snapshot"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Anaheim, CA"
        assert spec.field_map == SLA_FIELD_MAP
        assert spec.topic == "raw.municipal.sla"

    def test_registered_feed_set_is_permits_and_sla(self):
        assert set(ANAHEIM_FEED_SPECS) == {"permits", "sla"}

    def test_unknown_feed_raises_keyerror_naming_available(self):
        with pytest.raises(KeyError) as exc:
            get_anaheim_dataset("311")
        assert "anaheim" in str(exc.value)
        assert "permits" in str(exc.value)
        assert "sla" in str(exc.value)

    def test_endpoints_are_the_probed_agol_layers(self):
        assert "services3.arcgis.com" in ANAHEIM_PERMITS_ENDPOINT
        assert "Accela_Building_Permits/FeatureServer/0" in ANAHEIM_PERMITS_ENDPOINT
        assert "ActiveBusinessLicenses/FeatureServer/0" in ANAHEIM_SLA_ENDPOINT
