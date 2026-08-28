"""Unit tests for the Lynchburg leaf (US-318): spatial module + field maps
+ PERMITS / SLA / DEEDS parse wiring.

Lynchburg is an independent city on ONE ArcGIS Server open-data MapServer
(``mapviewer.lynchburgva.gov`` ``OpenData/ODPDynamic``): permits (/37 TRAKiT
tabular), business licenses (/33 tabular), and property transfers (/34
tabular — no address column, coordinates via the LRSN -> /41 Parcel
polygon-centroid ``parcel_join``). All three watermarks are date-typed, so
ArcGISClient flattens epoch-ms to ISO and no text-watermark declaration is
needed. Layer /34 publishes no objectIdField — ``ESRI_OID`` ordering is
mandatory (``orderByFields=OBJECTID`` 400s, verified live 2026-08-28).

Tests pass WITHOUT a spine registration (no CityId.LYNCHBURG): the
producers resolve city_id="lynchburg" as a plain string, the leaf-local
field maps are pinned via resolve_field_map patches, and geocoding is
mocked at src.spatial.geocoder.geocode_row_if_declared (Virginia Beach
pattern).

Live fixtures captured from the 2026-08-28 re-probe (all watermarks match
docs/research/probe-lynchburg_va.md; >=2 rows per feed, byte-verbatim
attribute values — padded fixed-width strings included). ArcGIS epoch-ms
dates are shown flattened to the ISO strings the client produces; the wire
value is noted per fixture.

Stability contract: these tests assert PARSE fields, source-neighborhood
passthrough, H3-from-fixture-coordinates, bbox containment, and field-map
mappings — deliberately NOT division/borough resolution results and NOT
geocode-hook call counts, both of which shift when the spine lands.
"""

import h3
from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_lynchburg import (
    DEEDS_FIELD_MAP,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.producers.watermarks import newest_typed_watermark, typed_watermark_entry
from src.spatial.cities.lynchburg import (
    LYNCHBURG_CENTER,
    LYNCHBURG_CITY_ID,
    LYNCHBURG_DEEDS_ENDPOINT,
    LYNCHBURG_DIVISION_BBOXES,
    LYNCHBURG_DIVISIONS,
    LYNCHBURG_FEED_SPECS,
    LYNCHBURG_GEOCODE_CONTEXT,
    LYNCHBURG_METRO_BBOX,
    LYNCHBURG_PARCEL_LAYER_ENDPOINT,
    LYNCHBURG_PERMITS_ENDPOINT,
    LYNCHBURG_SLA_ENDPOINT,
    LYNCHBURG_SUBMARKETS,
    REGISTRATION,
    get_lynchburg_dataset,
    is_in_lynchburg_metro,
)
from src.spatial.city_registry import FeedType
from src.spatial.geocoder import _STATE_RE, normalize_address


# ---------------------------------------------------------------------------
# Live fixtures (2026-08-28 re-probe, mapviewer.lynchburgva.gov ODPDynamic).
# ---------------------------------------------------------------------------

# Newest permits by StartDate DESC — wire epoch-ms 1787702400000 flattens to
# the fixture ISO. Newest row 2026-08-26; 7d=36, Aug=134, total=49,757.
PERMITS_ROW_AZDEL = {
    "OBJECTID": 13551,
    "GroupName": "PERMIT",
    "ParcelID": "24103002",
    "Address": "2000 ENTERPRISE DR",
    "RecordNo": "COM26-00293",
    "Name": "Azdel Inc. ~ Install of Steel Storage Building",
    "Type": "BUILDING",
    "SubType": "ADDITION",
    "StartDate": "2026-08-26T00:00:00+00:00",
    "EndDate": None,
    "Status": "APPROVED",
    "Neighborhood": "WYNDHURST INDUSTRIAL CORRIDOR",
    "Contact": "",
    "JobValue": 75000.0,
    "Owner_TRAKiT": "AZDEL INC",
}

PERMITS_ROW_SHINGLES = {
    "OBJECTID": 13628,
    "GroupName": "PERMIT",
    "ParcelID": "26105002",
    "Address": "110 MELINDA DR",
    "RecordNo": "COM26-00381",
    "Name": "Removing and replacing 195 SQ of laminate shingles and IWS",
    "Type": "BUILDING",
    "SubType": "REPAIR",
    "StartDate": "2026-08-26T00:00:00+00:00",
    "EndDate": None,
    "Status": "APPROVED",
    "Neighborhood": "WARDS RD COMMERCIAL CORRIDOR",
    "Contact": "",
    "JobValue": 150000.0,
    "Owner_TRAKiT": "CHURCH OF JESUS CHRIST OF LATTER-DAY",
}

PERMITS_ROW_NEW_SFD = {
    "OBJECTID": 47594,
    "GroupName": "PERMIT",
    "ParcelID": "00118004",
    "Address": "230 PATRICK ST",
    "RecordNo": "RES26-00798",
    "Name": "Single Family Dwelling",
    "Type": "BUILDING",
    "SubType": "NEW CONSTRUCTION",
    "StartDate": "2026-08-26T00:00:00+00:00",
    "EndDate": None,
    "Status": "APPROVED",
    "Neighborhood": "DEARINGTON PARK",
    "Contact": "",
    "JobValue": 150000.0,
    "Owner_TRAKiT": "KAE-REE ENTERPRISE LLC",
}

# Newest 2026 licenses by LicenseIssued DESC — 1787270400000 / 1787011200000
# flatten to the fixture ISOs. Newest row 2026-08-21; 7d=1, total=2,182.
# TradeName is empty on both live rows; the id falls through to Company.
SLA_ROW_NEEDLE_NINJA = {
    "OBJECTID": 4609,
    "LicenseNumber": "031386",
    "Company": "NEEDLE NINJA LLC",
    "TradeName": "",
    "ParcelID": "02449010",
    "Status": "ACTIVE",
    "LicenseIssued": "2026-08-21T00:00:00+00:00",
    "LicenseExpires": "2027-05-01T00:00:00+00:00",
    "MailAddress1": "924 MAIN ST",
    "MailAddress2": "",
    "MailCity": "LYNCHBURG",
    "MailState": "VA",
    "MailZip": "24504-1608",
    "BusinessType": "01 Retail Merchant",
    "FeeType": "Retail",
}

SLA_ROW_RIVERFRONT = {
    "OBJECTID": 4605,
    "LicenseNumber": "031382",
    "Company": "RIVERFRONT ENTERTAINMENT FOUNDATION",
    "TradeName": "",
    "ParcelID": "04631003",
    "Status": "ACTIVE",
    "LicenseIssued": "2026-08-18T00:00:00+00:00",
    "LicenseExpires": "2027-05-01T00:00:00+00:00",
    "MailAddress1": "1312 JEFFERSON ST",
    "MailAddress2": "",
    "MailCity": "LYNCHBURG",
    "MailState": "VA",
    "MailZip": "24504-1807",
    "BusinessType": "01 Retail Merchant",
    "FeeType": "",
}

# Newest transfers by SaleDate DESC — 1787702400000 / 1787616000000 flatten
# to the fixture ISOs. Newest row 2026-08-26; 7d=38, total=195,460. The
# newest instrument (260000257, a $0 will conveyance) is split across two
# LRSNs — DocumentNo repeats, fixed-width columns arrive space-padded.
DEEDS_ROW_DAVIS_WILL_X = {
    "LRSN": 8921,
    "SaleDate": "2026-08-26T00:00:00+00:00",
    "SaleAmount": 0.0,
    "DocumentNo": "260000257                       ",
    "DocumentRef": " ",
    "Seller": "DAVIS, WILLIAM H & NANCY E",
    "Buyer": "GILLEY, CAROLYN DAVIS, DAVIS, WILLIAM HINTO",
    "SaleType": "        ",
    "TransferType": "X ",
    "ConveyanceForm": "WILL                          ",
    "ESRI_OID": 27,
}

DEEDS_ROW_DAVIS_WILL_M = {
    "LRSN": 17439,
    "SaleDate": "2026-08-26T00:00:00+00:00",
    "SaleAmount": 0.0,
    "DocumentNo": "260000257                       ",
    "DocumentRef": " ",
    "Seller": "DAVIS, WILLIAM H & NANCY E",
    "Buyer": "GILLEY, CAROLYN DAVIS, WILLIAM HINTON DAVIS JR",
    "SaleType": "        ",
    "TransferType": "M ",
    "ConveyanceForm": "WILL                          ",
    "ESRI_OID": 28,
}

DEEDS_ROW_SHORT_SWEET = {
    "LRSN": 14196,
    "SaleDate": "2026-08-25T00:00:00+00:00",
    "SaleAmount": 180000.0,
    "DocumentNo": "260005545                       ",
    "DocumentRef": " ",
    "Seller": "SHORT AND SWEET VENTURES VA LLC",
    "Buyer": "JONES, ELIZABETH F",
    "SaleType": "        ",
    "TransferType": "S ",
    "ConveyanceForm": "DEED                          ",
    "ESRI_OID": 29,
}

# Mocked ADR-0004 geocodes (address-plausible, inside the metro bbox):
PERMITS_GEOCODE_ENTERPRISE = (37.3945, -79.1960)   # 2000 ENTERPRISE DR
PERMITS_GEOCODE_MELINDA = (37.4010, -79.1830)      # 110 MELINDA DR
SLA_GEOCODE_MAIN_ST = (37.4140, -79.1430)          # 924 MAIN ST
SLA_GEOCODE_JEFFERSON = (37.4125, -79.1400)        # 1312 JEFFERSON ST

# Parcel-join centroids as the deeds run_stream enrichment would set them
# (LRSN -> /41 Parcel polygon centroid):
DEEDS_CENTROID_14196 = (37.4100, -79.1500)
DEEDS_CENTROID_8921 = (37.4060, -79.1700)


def _h3_res7(lat: float, lng: float) -> str:
    return h3.cell_to_parent(h3.latlng_to_cell(lat, lng, 9), 7)


def _patch_resolve(monkeypatch, feed_key):
    monkeypatch.setattr(
        "src.producers.field_maps.resolve_field_map",
        lambda city, feed: FIELD_MAP[feed_key],
    )


@pytest.fixture
def permits():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        return DOBPermitsProducer()


@pytest.fixture
def sla():
    with patch("src.producers.sla_licenses_producer.BaseKafkaProducer"):
        from src.producers.sla_licenses_producer import SLALicensesProducer

        return SLALicensesProducer()


@pytest.fixture
def deeds():
    with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
        from src.producers.deeds_acris_producer import DeedsACRISProducer

        return DeedsACRISProducer()


class TestLynchburgSpatial:
    def test_city_id_constant(self):
        assert LYNCHBURG_CITY_ID == "lynchburg"

    def test_metro_contains_registration_center(self):
        assert is_in_lynchburg_metro(
            LYNCHBURG_CENTER["lat"], LYNCHBURG_CENTER["lng"]
        ) is True

    def test_metro_contains_known_landmarks(self):
        assert is_in_lynchburg_metro(37.4135, -79.1422) is True  # Downtown
        assert is_in_lynchburg_metro(37.4067, -79.2071) is True  # Liberty University
        assert is_in_lynchburg_metro(37.4190, -79.1520) is True  # Rivermont
        assert is_in_lynchburg_metro(37.4320, -79.1930) is True  # Peaks View Park
        assert is_in_lynchburg_metro(37.3860, -79.1850) is True  # Heritage / Wards Rd

    def test_metro_rejects_null_and_neighbors(self):
        assert is_in_lynchburg_metro(None, None) is False
        assert is_in_lynchburg_metro(37.2760, -79.1020) is False  # Rustburg (Campbell)
        assert is_in_lynchburg_metro(37.5850, -79.0500) is False  # Amherst
        assert is_in_lynchburg_metro(37.3320, -79.5220) is False  # Bedford
        assert is_in_lynchburg_metro(37.3690, -79.2870) is False  # Forest (Bedford)
        assert is_in_lynchburg_metro(37.3570, -78.8330) is False  # Appomattox
        assert is_in_lynchburg_metro(37.5400, -77.4400) is False  # Richmond

    def test_metro_bbox_grounded_in_parcel_extent(self):
        """Live /41 Parcel-layer extent (2026-08-28): lat 37.3326-37.4694,
        lng -79.2714 - -79.0850. The metro box must cover it with margin."""
        assert LYNCHBURG_METRO_BBOX["min_lat"] <= 37.3326
        assert LYNCHBURG_METRO_BBOX["max_lat"] >= 37.4694
        assert LYNCHBURG_METRO_BBOX["min_lng"] <= -79.2714
        assert LYNCHBURG_METRO_BBOX["max_lng"] >= -79.0850

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in LYNCHBURG_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= LYNCHBURG_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= LYNCHBURG_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= LYNCHBURG_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= LYNCHBURG_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in LYNCHBURG_SUBMARKETS.items():
            bbox = LYNCHBURG_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in LYNCHBURG_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(LYNCHBURG_SUBMARKETS)

    def test_submarkets_carry_lynchburg_city_id(self):
        assert {m.city_id for m in LYNCHBURG_SUBMARKETS.values()} == {"lynchburg"}

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in LYNCHBURG_DIVISIONS.items():
            bbox = LYNCHBURG_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_division_count(self):
        assert len(LYNCHBURG_DIVISIONS) == 3
        for div in LYNCHBURG_DIVISIONS.values():
            assert div.city_id == "lynchburg"

    def test_registration_bundles_leaf_constants(self):
        assert REGISTRATION.metro_bbox is LYNCHBURG_METRO_BBOX
        assert REGISTRATION.submarkets is LYNCHBURG_SUBMARKETS
        assert REGISTRATION.contains is is_in_lynchburg_metro


class TestFeedRegistration:
    def test_exactly_three_feed_types_are_registered(self):
        assert set(LYNCHBURG_FEED_SPECS) == {"permits", "sla", "deeds"}

    def test_all_endpoints_share_the_one_odpdynamic_mapservice(self):
        base = "https://mapviewer.lynchburgva.gov/arcgis/rest/services/OpenData/ODPDynamic/MapServer"
        assert LYNCHBURG_PERMITS_ENDPOINT == f"{base}/37"
        assert LYNCHBURG_SLA_ENDPOINT == f"{base}/33"
        assert LYNCHBURG_DEEDS_ENDPOINT == f"{base}/34"
        assert LYNCHBURG_PARCEL_LAYER_ENDPOINT == f"{base}/41"

    def test_permits_spec_matches_probe_contract(self):
        spec = get_lynchburg_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == LYNCHBURG_PERMITS_ENDPOINT
        assert spec.watermark_col == "StartDate"
        # True date column — client flattens to ISO; no ADR-0005 declaration.
        assert spec.watermark_type is None
        assert spec.watermark_format is None
        assert spec.id_keys == ["RecordNo", "OBJECTID"]
        assert spec.producer_key == "permits"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Lynchburg, VA"
        assert spec.order_by == "OBJECTID"
        assert spec.oid_field == "OBJECTID"
        assert spec.expected_cadence_days == 1
        assert spec.non_spatial is True
        assert spec.field_map is PERMITS_FIELD_MAP

    def test_sla_spec_declares_annual_trickle_cadence(self):
        spec = get_lynchburg_dataset(FeedType.SLA)
        assert spec.platform == "arcgis"
        assert spec.endpoint == LYNCHBURG_SLA_ENDPOINT
        assert spec.watermark_col == "LicenseIssued"
        assert spec.watermark_type is None
        assert spec.id_keys == ["LicenseNumber", "OBJECTID"]
        assert spec.producer_key == "sla"
        assert spec.needs_geocode is True
        assert spec.order_by == "OBJECTID"
        assert spec.expected_cadence_days == 365
        assert spec.non_spatial is True
        assert spec.field_map is SLA_FIELD_MAP

    def test_deeds_spec_declares_esri_oid_ordering_and_parcel_join(self):
        spec = get_lynchburg_dataset(FeedType.DEEDS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == LYNCHBURG_DEEDS_ENDPOINT
        assert spec.watermark_col == "SaleDate"
        assert spec.id_keys == ["LRSN", "DocumentNo"]
        assert spec.producer_key == "deeds"
        # Layer /34 publishes no objectIdField: OBJECTID ordering 400s.
        assert spec.order_by == "ESRI_OID"
        assert spec.oid_field == "ESRI_OID"
        # No address column: coordinates via LRSN -> /41 Parcel centroid join.
        assert spec.needs_geocode is True
        assert spec.non_spatial is True
        assert spec.parcel_join == {
            "parcel_layer": LYNCHBURG_PARCEL_LAYER_ENDPOINT,
            "join_key": "LRSN",
            "geometry_source": "centroid",
        }
        assert spec.expected_cadence_days == 1
        assert "ESRI_OID" in LYNCHBURG_FEED_SPECS["deeds"]["extra"]["scope"]

    @pytest.mark.parametrize(
        "absent_feed",
        [FeedType.COMPLAINTS_311, FeedType.CRIME, FeedType.STR],
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'lynchburg'.*available"):
            get_lynchburg_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert FIELD_MAP["permits"] is PERMITS_FIELD_MAP
        assert FIELD_MAP["sla"] is SLA_FIELD_MAP
        assert FIELD_MAP["deeds"] is DEEDS_FIELD_MAP
        assert GEOCODE_CONTEXT == LYNCHBURG_GEOCODE_CONTEXT == "Lynchburg, VA"
        assert "311" not in FIELD_MAP


class TestLynchburgFieldMaps:
    def test_permits_map_reads_live_columns(self):
        row = PERMITS_ROW_AZDEL
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "COM26-00293"
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_type") == "ADDITION"
        assert first_mapped(row, PERMITS_FIELD_MAP, "issuance_date") == "2026-08-26T00:00:00+00:00"
        assert first_mapped(row, PERMITS_FIELD_MAP, "address_street") == "2000 ENTERPRISE DR"
        assert first_mapped(row, PERMITS_FIELD_MAP, "bbl") == "24103002"
        assert first_mapped(row, PERMITS_FIELD_MAP, "borough") == "WYNDHURST INDUSTRIAL CORRIDOR"
        assert first_mapped(row, PERMITS_FIELD_MAP, "cost") == 75000.0
        assert first_mapped(row, PERMITS_FIELD_MAP, "status") == "APPROVED"

    def test_permits_job_id_falls_back_when_record_no_is_null(self):
        row = {"RecordNo": None, "OBJECTID": 13551}
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == 13551

    def test_permits_feed_has_no_application_date_or_coordinates(self):
        assert "filing_date" not in PERMITS_FIELD_MAP
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP

    def test_sla_map_reads_live_columns(self):
        row = SLA_ROW_NEEDLE_NINJA
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "031386"
        assert first_mapped(row, SLA_FIELD_MAP, "dba") == "NEEDLE NINJA LLC"
        assert first_mapped(row, SLA_FIELD_MAP, "premises_name") == "NEEDLE NINJA LLC"
        assert first_mapped(row, SLA_FIELD_MAP, "license_type") == "01 Retail Merchant"
        assert first_mapped(row, SLA_FIELD_MAP, "effective_date") == "2026-08-21T00:00:00+00:00"
        assert first_mapped(row, SLA_FIELD_MAP, "expiration_date") == "2027-05-01T00:00:00+00:00"
        assert first_mapped(row, SLA_FIELD_MAP, "address_street") == "924 MAIN ST"
        assert first_mapped(row, SLA_FIELD_MAP, "zipcode") == "24504-1608"

    def test_sla_empty_tradename_falls_through_to_company(self):
        """Live rows carry TradeName="" — falsy candidates must fall through
        to Company for both the id and the dba (first_mapped semantics)."""
        row = SLA_ROW_RIVERFRONT
        assert row["TradeName"] == ""
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "031382"
        assert first_mapped(row, SLA_FIELD_MAP, "dba") == "RIVERFRONT ENTERTAINMENT FOUNDATION"

    def test_deeds_map_reads_live_columns(self):
        row = DEEDS_ROW_SHORT_SWEET
        assert first_mapped(row, DEEDS_FIELD_MAP, "doc_id") == "260005545                       "
        assert first_mapped(row, DEEDS_FIELD_MAP, "bbl") == 14196
        assert first_mapped(row, DEEDS_FIELD_MAP, "document_amount") == 180000.0
        assert first_mapped(row, DEEDS_FIELD_MAP, "recorded_date") == "2026-08-25T00:00:00+00:00"
        assert first_mapped(row, DEEDS_FIELD_MAP, "party1_grantor") == "SHORT AND SWEET VENTURES VA LLC"
        assert first_mapped(row, DEEDS_FIELD_MAP, "party2_grantee") == "JONES, ELIZABETH F"

    def test_deeds_map_has_no_address_or_coordinate_candidates(self):
        """The Transfers table carries NO address column — coordinates come
        only from the parcel_join centroid enrichment, so the map declares
        neither address nor coordinate candidates."""
        assert "address_street" not in DEEDS_FIELD_MAP
        assert "incident_address" not in DEEDS_FIELD_MAP
        assert "latitude" not in DEEDS_FIELD_MAP
        assert "longitude" not in DEEDS_FIELD_MAP

    def test_deeds_doc_type_left_unmapped_because_of_padding(self):
        """ConveyanceForm/SaleType are space-padded fixed-width strings
        ("WILL...", "        "); leaving doc_type unmapped lets the producer
        default it to "DEED" instead of emitting a padded literal."""
        assert "doc_type" not in DEEDS_FIELD_MAP


class TestWatermarkTyping:
    """All three watermarks are true date columns — epoch-ms on the wire,
    ISO after ArcGISClient flatten, parsed under the default entry."""

    def test_permits_startdate_iso_parses(self):
        entry = typed_watermark_entry("2026-08-26T00:00:00+00:00")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 26)

    def test_sla_licenseissued_iso_parses(self):
        entry = typed_watermark_entry("2026-08-21T00:00:00+00:00")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 21)

    def test_deeds_saledate_iso_parses(self):
        entry = typed_watermark_entry("2026-08-26T00:00:00+00:00")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 26)

    def test_newest_across_all_three_feeds_is_2026_08_26(self):
        newest = newest_typed_watermark(
            [
                "2026-08-26T00:00:00+00:00",  # permits StartDate
                "2026-08-21T00:00:00+00:00",  # SLA LicenseIssued
                "2026-08-26T00:00:00+00:00",  # deeds SaleDate
                "2026-08-25T00:00:00+00:00",  # deeds runner-up
            ]
        )
        assert newest is not None
        assert newest[0].startswith("2026-08-26")

    def test_empty_watermark_values_are_dropped(self):
        assert typed_watermark_entry("") is None
        assert typed_watermark_entry(None) is None


class TestLynchburgPermitParsing:
    def test_address_only_permit_parses_with_mocked_geocode(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_ENTERPRISE,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_AZDEL, city_id="lynchburg")
        assert event is not None
        assert event.city_id == "lynchburg"
        assert event.job_id == "COM26-00293"
        assert event.latitude == pytest.approx(PERMITS_GEOCODE_ENTERPRISE[0])
        assert event.longitude == pytest.approx(PERMITS_GEOCODE_ENTERPRISE[1])
        assert event.h3_res7 == _h3_res7(*PERMITS_GEOCODE_ENTERPRISE)
        assert is_in_lynchburg_metro(event.latitude, event.longitude)

    def test_permits_geocode_sits_inside_metro(self):
        assert is_in_lynchburg_metro(*PERMITS_GEOCODE_ENTERPRISE)
        assert is_in_lynchburg_metro(*PERMITS_GEOCODE_MELINDA)

    def test_date_typed_startdate_parses_to_event_issuance(self, permits, monkeypatch):
        """Unlike Virginia Beach's text %Y/%m/%d watermark, Lynchburg's
        StartDate is date-typed — the client flattens it to ISO and the
        producer's date chain parses it into the event."""
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_ENTERPRISE,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_AZDEL, city_id="lynchburg")
        assert event is not None
        assert str(event.issuance_date).startswith("2026-08-26")

    def test_neighborhood_passes_through_as_source_neighborhood(
        self, permits, monkeypatch
    ):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_MELINDA,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_SHINGLES, city_id="lynchburg")
        assert event is not None
        assert event.source_neighborhood == "WARDS RD COMMERCIAL CORRIDOR"

    def test_jobvalue_maps_to_estimated_cost(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_MELINDA,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_SHINGLES, city_id="lynchburg")
        assert event is not None
        assert event.estimated_cost == 150000.0

    def test_permit_without_geocode_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        assert permits.parse_socrata_row(PERMITS_ROW_AZDEL, city_id="lynchburg") is None

    def test_new_construction_classifies_as_nb(self, permits, monkeypatch):
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_MELINDA,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_NEW_SFD, city_id="lynchburg")
        assert event is not None
        assert event.job_id == "RES26-00798"
        assert event.job_type == JobType.NB

    def test_addition_subtype_classifies_as_a2(self, permits, monkeypatch):
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_ENTERPRISE,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_AZDEL, city_id="lynchburg")
        assert event is not None
        assert event.job_type == JobType.A2

    def test_building_type_without_sub_type_classifies_as_ot(self, permits, monkeypatch):
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_MELINDA,
        )
        row = {**PERMITS_ROW_NEW_SFD, "SubType": None}
        event = permits.parse_socrata_row(row, city_id="lynchburg")
        assert event is not None
        assert event.job_type == JobType.OT


class TestLynchburgSlaParsing:
    def test_address_only_license_parses_with_mocked_geocode(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: SLA_GEOCODE_MAIN_ST,
        )
        event = sla.parse_socrata_row(SLA_ROW_NEEDLE_NINJA, city_id="lynchburg")
        assert event is not None
        assert event.city_id == "lynchburg"
        assert event.license_id == "031386"
        assert event.dba == "NEEDLE NINJA LLC"
        assert event.license_type == "01 Retail Merchant"
        assert event.address == "924 MAIN ST"
        assert event.latitude == pytest.approx(SLA_GEOCODE_MAIN_ST[0])
        assert event.longitude == pytest.approx(SLA_GEOCODE_MAIN_ST[1])
        assert event.h3_res7 == _h3_res7(*SLA_GEOCODE_MAIN_ST)
        assert event.h3_res9 is not None
        assert is_in_lynchburg_metro(event.latitude, event.longitude)

    def test_sla_geocode_sits_inside_metro(self):
        assert is_in_lynchburg_metro(*SLA_GEOCODE_MAIN_ST)
        assert is_in_lynchburg_metro(*SLA_GEOCODE_JEFFERSON)

    def test_license_number_keeps_leading_zero(self, sla, monkeypatch):
        """LicenseNumber is a zero-padded 6-digit string; the producer's
        float-normalize branch is scoped to san_diego only, so "031386"
        must survive intact as the id."""
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: SLA_GEOCODE_JEFFERSON,
        )
        event = sla.parse_socrata_row(SLA_ROW_RIVERFRONT, city_id="lynchburg")
        assert event is not None
        assert event.license_id == "031382"
        assert not event.license_id.startswith("31382")

    def test_date_typed_licenseissued_parses_to_effective_date(
        self, sla, monkeypatch
    ):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: SLA_GEOCODE_MAIN_ST,
        )
        event = sla.parse_socrata_row(SLA_ROW_NEEDLE_NINJA, city_id="lynchburg")
        assert event is not None
        assert str(event.effective_date).startswith("2026-08-21")

    def test_geocode_failure_keeps_null_coord_event(self, sla, monkeypatch):
        """SLA producer tolerance: a row whose geocode fails still emits as a
        null-lat/lng/null-H3 event (DC precedent) rather than being dropped."""
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        event = sla.parse_socrata_row(SLA_ROW_NEEDLE_NINJA, city_id="lynchburg")
        assert event is not None
        assert event.latitude is None and event.longitude is None
        assert event.h3_res7 is None and event.h3_res9 is None


class TestLynchburgDeedsParsing:
    def test_unenriched_row_parses_lossless_without_coordinates(
        self, deeds, monkeypatch
    ):
        """The Transfers table has no address column and "lynchburg" is not
        yet a registered city, so the parse is lossless: fields intact,
        coordinates/H3 null (the parcel_join enrichment runs at the
        run_stream layer, post-spine for the scheduler path)."""
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW_SHORT_SWEET, city_id="lynchburg")
        assert event is not None
        assert event.city_id == "lynchburg"
        assert event.latitude is None and event.longitude is None
        assert event.h3_res7 is None and event.h3_res9 is None

    def test_document_number_strips_fixed_width_padding(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW_DAVIS_WILL_X, city_id="lynchburg")
        assert event is not None
        assert event.doc_id == "260000257"
        assert event.doc_id == event.doc_id.strip()

    def test_lrsn_maps_to_bbl(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW_SHORT_SWEET, city_id="lynchburg")
        assert event is not None
        assert event.bbl == "14196"

    def test_priced_sale_maps_amount_and_iso_recorded_date(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW_SHORT_SWEET, city_id="lynchburg")
        assert event is not None
        assert event.document_amount == 180000.0
        assert str(event.recorded_date).startswith("2026-08-25")
        assert event.doc_type == "DEED"

    def test_zero_price_will_transfer_is_kept(self, deeds, monkeypatch):
        """$0 non-arms-length conveyances (the will split across LRSN 8921 /
        17439) parse and stay in the register with a 0.0 amount."""
        _patch_resolve(monkeypatch, "deeds")
        for row in (DEEDS_ROW_DAVIS_WILL_X, DEEDS_ROW_DAVIS_WILL_M):
            event = deeds.parse_socrata_row(row, city_id="lynchburg")
            assert event is not None
            assert event.document_amount == 0.0
            assert str(event.recorded_date).startswith("2026-08-26")
            assert event.party1_grantor == "DAVIS, WILLIAM H & NANCY E"

    def test_parcel_centroid_enrichment_drives_h3_from_fixture_coords(
        self, deeds, monkeypatch
    ):
        """run_stream enriches rows with the LRSN->Parcel centroid before
        parsing; the event then derives its H3 cells from those fixture
        coordinates and the point lands inside the metro bbox."""
        _patch_resolve(monkeypatch, "deeds")
        row = {
            **DEEDS_ROW_SHORT_SWEET,
            "latitude": DEEDS_CENTROID_14196[0],
            "longitude": DEEDS_CENTROID_14196[1],
        }
        event = deeds.parse_socrata_row(row, city_id="lynchburg")
        assert event is not None
        assert event.latitude == pytest.approx(DEEDS_CENTROID_14196[0])
        assert event.longitude == pytest.approx(DEEDS_CENTROID_14196[1])
        assert event.h3_res7 == _h3_res7(*DEEDS_CENTROID_14196)
        assert event.h3_res8 is not None and event.h3_res9 is not None
        assert is_in_lynchburg_metro(event.latitude, event.longitude)

    def test_both_newest_batch_rows_parse(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        for row in (DEEDS_ROW_DAVIS_WILL_X, DEEDS_ROW_DAVIS_WILL_M):
            assert deeds.parse_socrata_row(row, city_id="lynchburg") is not None

    def test_no_party_or_coordinate_candidates_in_deeds_map(self):
        assert "latitude" not in DEEDS_FIELD_MAP
        assert "longitude" not in DEEDS_FIELD_MAP


class TestGeocodingCaveats:
    def test_lynchburg_street_has_no_state_token_so_context_appends(self):
        assert _STATE_RE.search("924 Main St".upper()) is None

    def test_context_with_va_is_a_state_token(self):
        assert _STATE_RE.search("924 MAIN ST, LYNCHBURG, VA".upper()) is not None

    def test_unit_designator_normalization_preserves_city(self):
        norm = normalize_address("1312 JEFFERSON ST APT 3, LYNCHBURG, VA")
        assert "APT" not in norm
        assert "LYNCHBURG" in norm
