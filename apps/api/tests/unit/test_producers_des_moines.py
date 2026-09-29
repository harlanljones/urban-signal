"""Unit tests for the Des Moines, IA leaf: spatial geometry + the Rental License (SLA) feed.

Des Moines registers ONE feed: SLA = the City of Des Moines "Rental License"
layer (maps.dsm.city External/EXTDynamicCodeCaseRentalLicense MapServer layer
1: native point geometry, IssuedDate watermark, LicenseNumber id). Permits
(Tyler EnerGov, no platform client), 311 (CitySourced / Tyler Portico, no
public row API), deeds (Polk County Auditor table with no geometry whose parcel
key is named differently from the point layer's, which the single-name
``parcel_join`` contract cannot express) and crime (cadence unproven) did not
qualify; the row-level evidence and the re-probe triggers are in
docs/research/probe-des_moines.md.

Fixtures are real features captured 2026-09-29 from the live layer with
outSR=4326 (attributes and point geometry exactly as served). ONE deliberate
edit: ContactName, ContactAddress, CityStateZip and ContactEmail identify
natural persons (landlords) and are replaced with "REDACTED" - the field map
never reads them, and a test below pins that. Every attribute the producer does
read, and every geometry, is byte-for-byte as served.
"""

import math
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.config import settings
from src.producers.scheduler import MunicipalIngestionScheduler, _is_future_watermark
from src.producers.watermarks import ANSI_DATE_LITERAL_HOSTS, watermark_comparison
from src.spatial.cities.des_moines import (
    DES_MOINES_CENTER,
    DES_MOINES_CITY_ID,
    DES_MOINES_DIVISION_BBOXES,
    DES_MOINES_DIVISIONS,
    DES_MOINES_METRO_BBOX,
    DES_MOINES_SUBMARKETS,
    REGISTRATION,
    is_in_des_moines_metro,
)
from src.spatial.city_registry import (
    REGISTRY,
    CityId,
    FeedType,
    get_dataset,
    get_job_name,
    normalize_city,
)
from src.spatial.geo_utils import get_division_for_coordinate
from src.spatial.submarkets import find_nearest_submarket

# Census TIGERweb place extents read 2026-09-29 (xmin, ymin, xmax, ymax, WGS84).
# The metro bbox is the union of these, rounded outward.
_TIGERWEB_EXTENTS = {
    "Des Moines": (-93.7096, 41.4796, -93.4938, 41.6586),
    "West Des Moines": (-93.8870, 41.4893, -93.6981, 41.6005),
    "Urbandale": (-93.8724, 41.6146, -93.6975, 41.6728),
    "Clive": (-93.8722, 41.5964, -93.7181, 41.6438),
    "Windsor Heights": (-93.7268, 41.5916, -93.7035, 41.6149),
    "Johnston": (-93.7851, 41.6527, -93.6646, 41.7539),
    "Ankeny": (-93.6728, 41.6521, -93.5413, 41.8024),
    "Altoona": (-93.5514, 41.6079, -93.4355, 41.6957),
    "Pleasant Hill": (-93.5322, 41.5517, -93.4303, 41.6151),
    "Norwalk": (-93.7320, 41.4462, -93.6445, 41.5140),
}

# Min/max over all 15,475 Rental License rows (every row carries a point),
# read 2026-09-29: (min_lng, min_lat, max_lng, max_lat).
_LAYER_ROW_EXTENT = (
    -93.70844449238979,
    41.50937182665762,
    -93.50155047687606,
    41.65817946137907,
)

_CITY_DIVISIONS = ("CENTRAL_CORE", "NORTH_SIDE", "SOUTH_SIDE", "EAST_SIDE")
_SUBURBAN_DIVISIONS = ("WEST_SUBURBS", "NORTH_SUBURBS")
_CONTACT_COLUMNS = ("ContactName", "ContactAddress", "CityStateZip", "ContactEmail")

# The layer's esriFieldTypeDate columns (what ArcGISClient.get_layer_metadata
# derives from the layer definition).
_DATE_FIELDS = {"IssuedDate", "ExpDate", "created_date", "last_edited_date"}

# RENT-2026-008550, 3831 40TH ST: newest IssuedDate (2026-09-25), north side.
_NORTH_SIDE = {
    "attributes": {
        "OBJECTID": 1306976,
        "LicenseNumber": "RENT-2026-008550",
        "ParcelNumber": "792420377017",
        "IssuedDate": 1790312400000,
        "ExpDate": 1899093600000,
        "RentalAddress": "3831 40TH ST",
        "Unit": "",
        "ContactType": "Property Owner",
        "ContactName": "REDACTED",
        "ContactAddress": "REDACTED",
        "CityStateZip": "REDACTED",
        "Remark": "",
        "DataOwner": "",
        "PKID": 0,
        "created_date": 1790506803000,
        "created_user": "CDMDOMAIN\\SVC-CDMSQLGISP1",
        "last_edited_date": 1790506803000,
        "last_edited_user": "CDMDOMAIN\\SVC-CDMSQLGISP1",
        "ExtID": 0.0,
        "GlobalID": "{63BD0BFC-E0F0-4B76-9801-5AAE68E059A9}",
        "Status": "Issued",
        "Hyperlink": "http://web.assess.co.polk.ia.us/cgi-bin/web/tt/infoqry.cgi?tt=card/card&gp=792420377017",
        "ContactEmail": "REDACTED"
    },
    "geometry": {
        "x": -93.67173528238007,
        "y": 41.6305346231229
    }
}

# RENT-2026-007423, 1200 LOCUST ST: downtown; ExpDate is the 2999-01-01 sentinel.
_DOWNTOWN_SENTINEL = {
    "attributes": {
        "OBJECTID": 1315309,
        "LicenseNumber": "RENT-2026-007423",
        "ParcelNumber": "782404362008",
        "IssuedDate": 1790226000000,
        "ExpDate": 32472165600000,
        "RentalAddress": "1200 LOCUST ST",
        "Unit": "",
        "ContactType": "Property Owner",
        "ContactName": "REDACTED",
        "ContactAddress": "REDACTED",
        "CityStateZip": "REDACTED",
        "Remark": "",
        "DataOwner": "",
        "PKID": 0,
        "created_date": 1790506803000,
        "created_user": "CDMDOMAIN\\SVC-CDMSQLGISP1",
        "last_edited_date": 1790506803000,
        "last_edited_user": "CDMDOMAIN\\SVC-CDMSQLGISP1",
        "ExtID": 0.0,
        "GlobalID": "{A5C7606D-5854-4E55-B09E-44C356EAD956}",
        "Status": "Issued",
        "Hyperlink": "http://web.assess.co.polk.ia.us/cgi-bin/web/tt/infoqry.cgi?tt=card/card&gp=782404362008",
        "ContactEmail": "REDACTED"
    },
    "geometry": {
        "x": -93.6326472801591,
        "y": 41.58503844220662
    }
}

# RENT-2025-015015, 119 E KIRKWOOD AVE: IssuedDate 2026-11-20 is in the future.
_FUTURE_DATED = {
    "attributes": {
        "OBJECTID": 1314367,
        "LicenseNumber": "RENT-2025-015015",
        "ParcelNumber": "782415151015",
        "IssuedDate": 1795154400000,
        "ExpDate": 1879304400000,
        "RentalAddress": "119 E KIRKWOOD AVE",
        "Unit": "",
        "ContactType": "Property Owner",
        "ContactName": "REDACTED",
        "ContactAddress": "REDACTED",
        "CityStateZip": "REDACTED",
        "Remark": "",
        "DataOwner": "",
        "PKID": 0,
        "created_date": 1790506803000,
        "created_user": "CDMDOMAIN\\SVC-CDMSQLGISP1",
        "last_edited_date": 1790506803000,
        "last_edited_user": "CDMDOMAIN\\SVC-CDMSQLGISP1",
        "ExtID": 0.0,
        "GlobalID": "{7D001109-AE2C-4982-87D6-F5F3B62DAE9D}",
        "Status": "Issued",
        "Hyperlink": "http://web.assess.co.polk.ia.us/cgi-bin/web/tt/infoqry.cgi?tt=card/card&gp=782415151015",
        "ContactEmail": "REDACTED"
    },
    "geometry": {
        "x": -93.61334002959188,
        "y": 41.56518679776351
    }
}

# RENT-2026-006646, 5825 URBANDALE AVE: first of two Property Owner rows.
_TWO_OWNER_A = {
    "attributes": {
        "OBJECTID": 1319041,
        "LicenseNumber": "RENT-2026-006646",
        "ParcelNumber": "792525280020",
        "IssuedDate": 1790312400000,
        "ExpDate": 1869368400000,
        "RentalAddress": "5825 URBANDALE AVE",
        "Unit": "",
        "ContactType": "Property Owner",
        "ContactName": "REDACTED",
        "ContactAddress": "REDACTED",
        "CityStateZip": "REDACTED",
        "Remark": "",
        "DataOwner": "",
        "PKID": 0,
        "created_date": 1790506803000,
        "created_user": "CDMDOMAIN\\SVC-CDMSQLGISP1",
        "last_edited_date": 1790506803000,
        "last_edited_user": "CDMDOMAIN\\SVC-CDMSQLGISP1",
        "ExtID": 0.0,
        "GlobalID": "{13EA2D42-CED4-4A97-82CF-847273D4496E}",
        "Status": "Issued",
        "Hyperlink": "http://web.assess.co.polk.ia.us/cgi-bin/web/tt/infoqry.cgi?tt=card/card&gp=792525280020",
        "ContactEmail": "REDACTED"
    },
    "geometry": {
        "x": -93.69902904530512,
        "y": 41.62240049889312
    }
}

# RENT-2026-006646: second Property Owner row, same license and point.
_TWO_OWNER_B = {
    "attributes": {
        "OBJECTID": 1319042,
        "LicenseNumber": "RENT-2026-006646",
        "ParcelNumber": "792525280020",
        "IssuedDate": 1790312400000,
        "ExpDate": 1869368400000,
        "RentalAddress": "5825 URBANDALE AVE",
        "Unit": "",
        "ContactType": "Property Owner",
        "ContactName": "REDACTED",
        "ContactAddress": "REDACTED",
        "CityStateZip": "REDACTED",
        "Remark": "",
        "DataOwner": "",
        "PKID": 0,
        "created_date": 1790506803000,
        "created_user": "CDMDOMAIN\\SVC-CDMSQLGISP1",
        "last_edited_date": 1790506803000,
        "last_edited_user": "CDMDOMAIN\\SVC-CDMSQLGISP1",
        "ExtID": 0.0,
        "GlobalID": "{EBE9A760-6540-451C-A0CE-9C6A15BD60C1}",
        "Status": "Issued",
        "Hyperlink": "http://web.assess.co.polk.ia.us/cgi-bin/web/tt/infoqry.cgi?tt=card/card&gp=792525280020",
        "ContactEmail": "REDACTED"
    },
    "geometry": {
        "x": -93.69902904530512,
        "y": 41.62240049889312
    }
}


_FIXTURES = (_NORTH_SIDE, _DOWNTOWN_SENTINEL, _FUTURE_DATED, _TWO_OWNER_A, _TWO_OWNER_B)

# The wall clock the future-dated fixture is judged against (a fixed instant,
# so the tests do not rot when the real clock passes 2026-11-20).
_NOW = datetime(2026, 9, 29, 5, 0, tzinfo=UTC)


def _flatten(feature):
    """Flatten a fixture exactly as the production ArcGIS client does."""
    from src.producers.arcgis_client import ArcGISClient

    return ArcGISClient()._flatten_feature(feature, date_fields=_DATE_FIELDS)


@patch("src.producers.sla_licenses_producer.BaseKafkaProducer")
def _sla_producer(_):
    from src.producers.sla_licenses_producer import SLALicensesProducer

    return SLALicensesProducer()


def _bbox_area(bbox):
    return (bbox["max_lat"] - bbox["min_lat"]) * (bbox["max_lng"] - bbox["min_lng"])


# ======================================================================
# Spatial tests
# ======================================================================


class TestDesMoinesSpatial:
    def test_metro_bbox_sanity(self):
        assert DES_MOINES_METRO_BBOX["min_lat"] < DES_MOINES_METRO_BBOX["max_lat"]
        assert DES_MOINES_METRO_BBOX["min_lng"] < DES_MOINES_METRO_BBOX["max_lng"]

    def test_center_is_city_hall_and_inside_metro_bbox(self):
        # Census geocoder match for 400 Robert D Ray Dr: 41.588722, -93.616145.
        assert DES_MOINES_CENTER == {"lat": 41.5887, "lng": -93.6161}
        assert is_in_des_moines_metro(DES_MOINES_CENTER["lat"], DES_MOINES_CENTER["lng"])

    def test_is_in_des_moines_metro_rejects_missing_coordinates(self):
        assert is_in_des_moines_metro(None, None) is False
        assert is_in_des_moines_metro(41.5887, None) is False

    def test_metro_rejects_other_cities(self):
        assert is_in_des_moines_metro(41.2580, -95.9370) is False  # Omaha, NE
        assert is_in_des_moines_metro(41.6611, -91.5302) is False  # Iowa City area
        assert is_in_des_moines_metro(39.0997, -94.5786) is False  # Kansas City, MO

    def test_metro_bbox_contains_every_tigerweb_place_extent(self):
        for place, (xmin, ymin, xmax, ymax) in _TIGERWEB_EXTENTS.items():
            assert DES_MOINES_METRO_BBOX["min_lat"] <= ymin, place
            assert ymax <= DES_MOINES_METRO_BBOX["max_lat"], place
            assert DES_MOINES_METRO_BBOX["min_lng"] <= xmin, place
            assert xmax <= DES_MOINES_METRO_BBOX["max_lng"], place

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in DES_MOINES_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= DES_MOINES_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= DES_MOINES_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= DES_MOINES_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= DES_MOINES_METRO_BBOX["max_lng"], name

    def test_division_bboxes_tile_the_metro_bbox_without_overlap(self):
        names = list(DES_MOINES_DIVISION_BBOXES)
        total = sum(_bbox_area(b) for b in DES_MOINES_DIVISION_BBOXES.values())
        assert math.isclose(total, _bbox_area(DES_MOINES_METRO_BBOX), rel_tol=1e-9)
        for i, first in enumerate(names):
            for second in names[i + 1 :]:
                a, b = DES_MOINES_DIVISION_BBOXES[first], DES_MOINES_DIVISION_BBOXES[second]
                overlap_lat = min(a["max_lat"], b["max_lat"]) - max(a["min_lat"], b["min_lat"])
                overlap_lng = min(a["max_lng"], b["max_lng"]) - max(a["min_lng"], b["min_lng"])
                assert not (overlap_lat > 1e-9 and overlap_lng > 1e-9), (first, second)

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in DES_MOINES_SUBMARKETS.items():
            bbox = DES_MOINES_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in DES_MOINES_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(DES_MOINES_SUBMARKETS)

    def test_submarkets_and_divisions_carry_the_city_id(self):
        assert all(m.city_id == DES_MOINES_CITY_ID for m in DES_MOINES_SUBMARKETS.values())
        assert all(d.city_id == DES_MOINES_CITY_ID for d in DES_MOINES_DIVISIONS.values())

    def test_city_id_and_registration_shape(self):
        assert DES_MOINES_CITY_ID == "des_moines"
        assert REGISTRATION.metro_bbox is DES_MOINES_METRO_BBOX
        assert REGISTRATION.submarkets is DES_MOINES_SUBMARKETS
        assert len(DES_MOINES_DIVISIONS) == 6
        assert len(DES_MOINES_SUBMARKETS) == 14

    def test_layer_rows_lie_inside_the_metro_and_the_four_city_divisions(self):
        min_lng, min_lat, max_lng, max_lat = _LAYER_ROW_EXTENT
        assert is_in_des_moines_metro(min_lat, min_lng)
        assert is_in_des_moines_metro(max_lat, max_lng)
        city = [DES_MOINES_DIVISION_BBOXES[d] for d in _CITY_DIVISIONS]
        assert min(b["min_lat"] for b in city) <= min_lat
        assert max_lat <= max(b["max_lat"] for b in city)
        assert min(b["min_lng"] for b in city) <= min_lng
        assert max_lng <= max(b["max_lng"] for b in city)

    def test_suburban_divisions_hold_no_layer_rows(self):
        """The City feed covers the city only, so the suburban submarkets carry
        sla == 0 (no coverage), never a fabricated count."""
        min_lng, min_lat, max_lng, max_lat = _LAYER_ROW_EXTENT
        for name in _SUBURBAN_DIVISIONS:
            bbox = DES_MOINES_DIVISION_BBOXES[name]
            outside = (
                max_lat < bbox["min_lat"]
                or min_lat > bbox["max_lat"]
                or max_lng < bbox["min_lng"]
                or min_lng > bbox["max_lng"]
            )
            assert outside, name
            for sub in DES_MOINES_DIVISIONS[name].submarkets:
                assert DES_MOINES_SUBMARKETS[sub].sla == 0.0, sub

    def test_city_submarkets_carry_the_measured_90_day_license_count(self):
        """sla is the count of unique LicenseNumber values (ContactType =
        'Property Owner') issued 2026-07-01..2026-09-29, assigned to the nearest
        anchor: 742 licenses in total (live windowed count, 2026-09-29)."""
        city = [
            m
            for m in DES_MOINES_SUBMARKETS.values()
            if m.borough in _CITY_DIVISIONS
        ]
        assert all(m.sla > 0 for m in city)
        assert sum(m.sla for m in DES_MOINES_SUBMARKETS.values()) == 742.0

    def test_unmeasured_seeds_are_one_neutral_value(self):
        """No permits/311/scored feed is registered, so base_lims, capex,
        permit_vel and shift_ratio are identical everywhere: no ranking between
        submarkets is implied."""
        for attr in ("base_lims", "capex", "permit_vel", "shift_ratio"):
            assert len({getattr(m, attr) for m in DES_MOINES_SUBMARKETS.values()}) == 1, attr

    def test_required_real_neighborhoods_are_named(self):
        text = " ".join(m.description for m in DES_MOINES_SUBMARKETS.values())
        for neighborhood in (
            "Downtown",
            "Sherman Hill",
            "Historic East Village",
            "Drake",
            "Beaverdale",
            "Merle Hay",
            "Highland Park",
            "Indianola Hills",
            "Watrous",
            "Fairground",
            "Easter Lake",
        ):
            assert neighborhood in text, neighborhood

    def test_fixture_coordinates_are_contained(self):
        for feature in _FIXTURES:
            lat, lng = feature["geometry"]["y"], feature["geometry"]["x"]
            assert is_in_des_moines_metro(lat, lng), (lat, lng)
            assert get_division_for_coordinate(lat, lng, city_id="des_moines") in _CITY_DIVISIONS


# ======================================================================
# Registry / feed-spec tests
# ======================================================================


class TestDesMoinesRegistry:
    def test_registered_in_city_id_enum(self):
        assert CityId.DES_MOINES.value == "des_moines"

    def test_registered_in_registry(self):
        reg = REGISTRY[CityId.DES_MOINES]
        assert reg.name == "Des Moines, IA"
        assert reg.state == "IA"
        assert reg.job_suffix == "des_moines"
        assert reg.center == DES_MOINES_CENTER

    def test_only_the_sla_feed_is_registered(self):
        assert set(REGISTRY[CityId.DES_MOINES].datasets) == {FeedType.SLA}
        for feed in (FeedType.PERMITS, FeedType.COMPLAINTS_311, FeedType.DEEDS, FeedType.CRIME):
            with pytest.raises(KeyError, match="des_moines"):
                get_dataset(CityId.DES_MOINES, feed)

    def test_aliases_resolve(self):
        for alias in ("des_moines", "Des Moines", "des moines ia", "des_moines_ia", "DSM"):
            assert normalize_city(alias) is CityId.DES_MOINES, alias

    def test_job_name(self):
        assert get_job_name(FeedType.SLA, CityId.DES_MOINES) == "sla_des_moines"

    def test_sla_spec_matches_live_layer(self):
        spec = get_dataset(CityId.DES_MOINES, FeedType.SLA)
        assert spec.endpoint == settings.arcgis_des_moines_rental_licenses_url
        assert spec.endpoint.endswith("EXTDynamicCodeCaseRentalLicense/MapServer/1")
        assert spec.platform == "arcgis"
        assert spec.topic == "raw.municipal.sla"
        assert spec.producer_key == "sla"
        assert spec.watermark_col == "IssuedDate"
        assert spec.ingestion_mode == "incremental"
        assert spec.needs_geocode is False
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        # Newest Rental License IssuedDate gap over the trailing 12 months is 6
        # days, and the layer is a full reload, so 7 keeps the alarm at 14 days.
        assert spec.expected_cadence_days == 7
        assert spec.id_keys == ["LicenseNumber", "OBJECTID"]

    def test_sla_spec_pages_under_a_total_order(self):
        """Many rows share one IssuedDate (midnight local), and the server's
        tie order under `IssuedDate DESC` alone is arbitrary, so paging needs the
        OBJECTID tiebreak to be deterministic."""
        spec = get_dataset(CityId.DES_MOINES, FeedType.SLA)
        assert spec.order_by == "IssuedDate DESC, OBJECTID DESC"

    def test_sla_spec_filters_to_the_property_owner_contact_rows(self):
        """license_type is mapped from ContactType; the filter makes the label
        deterministic ('Property Owner') instead of a mix with 'Management Agent'."""
        spec = get_dataset(CityId.DES_MOINES, FeedType.SLA)
        assert spec.where == "ContactType = 'Property Owner'"

    def test_field_map_reads_live_columns(self):
        spec = get_dataset(CityId.DES_MOINES, FeedType.SLA)
        record = _flatten(_NORTH_SIDE)
        for canonical, columns in spec.field_map.items():
            assert columns, canonical
            for column in columns:
                assert column in record, (canonical, column)
        assert spec.field_map["license_id"] == ["LicenseNumber"]
        assert spec.field_map["effective_date"] == ["IssuedDate"]
        assert spec.field_map["expiration_date"] == ["ExpDate"]
        assert spec.field_map["address_street"] == ["RentalAddress"]
        assert spec.field_map["status"] == ["Status"]

    def test_field_map_never_reads_contact_columns(self):
        spec = get_dataset(CityId.DES_MOINES, FeedType.SLA)
        mapped = {column for columns in spec.field_map.values() for column in columns}
        assert mapped.isdisjoint(_CONTACT_COLUMNS)
        assert not set(spec.id_keys) & set(_CONTACT_COLUMNS)

    def test_host_uses_ansi_date_literals(self):
        """`IssuedDate > '2026-09-25T05:00:00'` returns 400 on maps.dsm.city;
        `date '...'` works, so the host is an ANSI-literal host."""
        spec = get_dataset(CityId.DES_MOINES, FeedType.SLA)
        assert "maps.dsm.city" in ANSI_DATE_LITERAL_HOSTS
        assert (
            watermark_comparison(spec.watermark_col, ">", "2026-09-25T05:00:00", spec.endpoint)
            == "IssuedDate > date '2026-09-25'"
        )


# ======================================================================
# Producer parse tests (real captured rows)
# ======================================================================


class TestDesMoinesRentalLicenseParsing:
    @pytest.fixture
    def sla(self):
        return _sla_producer()

    def test_flatten_lifts_point_geometry_and_iso_dates(self):
        record = _flatten(_NORTH_SIDE)
        assert record["LicenseNumber"] == "RENT-2026-008550"
        assert record["latitude"] == pytest.approx(41.6305346231229)
        assert record["longitude"] == pytest.approx(-93.67173528238007)
        assert record["IssuedDate"] == "2026-09-25T05:00:00+00:00"
        assert record["ExpDate"] == "2030-03-07T06:00:00+00:00"

    def test_north_side_row_parses_through_producer(self, sla):
        event = sla.parse_socrata_row(_flatten(_NORTH_SIDE), city_id="des_moines")
        assert event is not None
        assert event.city_id == "des_moines"
        assert event.license_id == "RENT-2026-008550"
        # Mapped from ContactType; the unmapped fallback would be the wrong
        # label "On-Premises Liquor".
        assert event.license_type == "Property Owner"
        assert event.license_status == "Issued"
        assert event.address == "3831 40TH ST"
        assert event.latitude == pytest.approx(41.6305346231229)
        assert event.longitude == pytest.approx(-93.67173528238007)
        assert event.effective_date == datetime(2026, 9, 25, 5, 0, tzinfo=UTC)
        assert event.expiration_date == datetime(2030, 3, 7, 6, 0, tzinfo=UTC)
        assert event.borough == "NORTH_SIDE"
        assert event.source_neighborhood is None
        assert len({event.h3_res7, event.h3_res8, event.h3_res9}) == 3
        assert None not in {event.h3_res7, event.h3_res8, event.h3_res9}

    def test_divisions_resolve_from_the_registered_geometry(self, sla):
        expected = {
            "RENT-2026-008550": "NORTH_SIDE",
            "RENT-2026-007423": "CENTRAL_CORE",
            "RENT-2025-015015": "SOUTH_SIDE",
            "RENT-2026-006646": "NORTH_SIDE",
        }
        for feature in _FIXTURES:
            record = _flatten(feature)
            event = sla.parse_socrata_row(record, city_id="des_moines")
            assert event is not None
            assert event.borough == expected[record["LicenseNumber"]], record["LicenseNumber"]

    def test_fixture_snaps_to_its_nearest_submarket(self):
        feature = _NORTH_SIDE
        name, dist_km = find_nearest_submarket(
            feature["geometry"]["y"], feature["geometry"]["x"], city_id="des_moines"
        )
        assert name == "Beaverdale / Merle Hay"
        assert dist_km < 2.0

    def test_watermark_comes_from_effective_date_and_drives_the_ansi_filter(self, sla):
        spec = get_dataset(CityId.DES_MOINES, FeedType.SLA)
        event = sla.parse_socrata_row(_flatten(_NORTH_SIDE), city_id="des_moines")
        assert event is not None
        # poll_job reads issuance_date, then created_date, then effective_date.
        assert getattr(event, "issuance_date", None) is None
        assert getattr(event, "created_date", None) is None
        stored = event.effective_date.strftime("%Y-%m-%dT%H:%M:%S")
        assert stored == "2026-09-25T05:00:00"
        assert (
            watermark_comparison(spec.watermark_col, ">", stored, spec.endpoint)
            == "IssuedDate > date '2026-09-25'"
        )

    def test_2999_expiry_sentinel_parses_to_a_valid_datetime(self, sla):
        event = sla.parse_socrata_row(_flatten(_DOWNTOWN_SENTINEL), city_id="des_moines")
        assert event is not None
        assert event.license_id == "RENT-2026-007423"
        assert event.address == "1200 LOCUST ST"
        assert event.effective_date == datetime(2026, 9, 24, 5, 0, tzinfo=UTC)
        assert event.expiration_date == datetime(2999, 1, 1, 6, 0, tzinfo=UTC)
        assert event.borough == "CENTRAL_CORE"

    def test_future_dated_row_parses_but_cannot_pin_the_watermark(self, sla):
        event = sla.parse_socrata_row(_flatten(_FUTURE_DATED), city_id="des_moines")
        assert event is not None
        assert event.license_id == "RENT-2025-015015"
        assert event.effective_date == datetime(2026, 11, 20, 6, 0, tzinfo=UTC)
        assert _is_future_watermark(event.effective_date, _NOW) is True

    def test_two_owner_rows_share_one_id_and_one_location(self, sla):
        spec = get_dataset(CityId.DES_MOINES, FeedType.SLA)
        first, second = _flatten(_TWO_OWNER_A), _flatten(_TWO_OWNER_B)
        assert first["OBJECTID"] != second["OBJECTID"]
        assert first[spec.id_keys[0]] == second[spec.id_keys[0]] == "RENT-2026-006646"
        event_a = sla.parse_socrata_row(first, city_id="des_moines")
        event_b = sla.parse_socrata_row(second, city_id="des_moines")
        assert event_a is not None and event_b is not None
        assert event_a.license_id == event_b.license_id
        assert (event_a.latitude, event_a.longitude) == (event_b.latitude, event_b.longitude)
        assert event_a.h3_res9 == event_b.h3_res9

    def test_contact_columns_never_reach_the_event(self, sla):
        for feature in _FIXTURES:
            event = sla.parse_socrata_row(_flatten(feature), city_id="des_moines")
            assert event is not None
            assert event.premises_name is None
            assert event.dba is None
            assert "REDACTED" not in event.model_dump_json()


# ======================================================================
# Scheduler wiring (registered spec -> poll_job)
# ======================================================================


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return _NOW if tz is None else _NOW.astimezone(tz)


@pytest.fixture
def scheduler():
    with patch("src.producers.base_producer.BaseKafkaProducer"):
        sched = MunicipalIngestionScheduler(
            dlq_producer=MagicMock(),
            rate_limit_delay_seconds=0.0,
            dedup_capacity=1000,
        )
    sla = sched.producers["sla"]
    sla.producer = MagicMock()
    sla.arcgis.paginate = MagicMock(return_value=[])
    return sched


class TestDesMoinesSchedulerWiring:
    JOB = "sla_des_moines"

    def test_job_is_registered_from_the_spec(self, scheduler):
        meta = scheduler.job_metadata[self.JOB]
        assert meta["platform"] == "arcgis"
        assert meta["producer_key"] == "sla"
        assert meta["watermark_col"] == "IssuedDate"
        assert meta["city_id"] == "des_moines"
        assert meta["base_where"] == "ContactType = 'Property Owner'"
        assert scheduler._extract_record_id(self.JOB, _flatten(_NORTH_SIDE)) == (
            "sla_des_moines:RENT-2026-008550"
        )

    def test_poll_dedups_two_owner_rows_and_ignores_the_future_watermark(
        self, scheduler, monkeypatch
    ):
        monkeypatch.setattr("src.producers.scheduler.datetime", _FrozenDatetime)
        sla = scheduler.producers["sla"]
        batch = [_flatten(feature) for feature in _FIXTURES]
        sla.arcgis.paginate = MagicMock(return_value=[batch])

        result = scheduler.poll_job(self.JOB, limit=100)

        assert result["status"] == "SUCCESS"
        assert result["records_fetched"] == 5
        assert result["records_published"] == 4  # the two owners of one license dedup on id
        assert result["duplicates_skipped"] == 1
        assert scheduler.dlq_producer.route_to_dlq.call_count == 0
        # The 2026-11-20 row is published but cannot pin the watermark; the
        # newest current row (2026-09-25) sets it.
        assert result["high_watermark"] == "2026-09-25T05:00:00"

        _, first_call = sla.arcgis.paginate.call_args
        assert first_call["where_clause"] == "(ContactType = 'Property Owner')"
        assert first_call["endpoint_url"] == settings.arcgis_des_moines_rental_licenses_url
        assert first_call["order_by"] == "IssuedDate DESC, OBJECTID DESC"

        # Next poll: incremental filter rendered as an ANSI date literal.
        sla.arcgis.paginate = MagicMock(return_value=[])
        scheduler.poll_job(self.JOB, limit=100)
        _, second_call = sla.arcgis.paginate.call_args
        assert second_call["where_clause"] == (
            "(ContactType = 'Property Owner') AND IssuedDate > date '2026-09-25'"
        )
