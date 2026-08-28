"""Unit tests for the Virginia Beach leaf (US-354): spatial module + field maps
+ PERMITS / SLA / DEEDS parse wiring.

Virginia Beach is an independent city on the city AGOL org CyVvlIiUfRBmMQuu
(data.virginiabeach.gov Hub). All three registered feeds are hosted ArcGIS
TABLES: permits (Building_Permits_Applications_view, text YYYY/MM/DD
watermark), business licenses (Business_Licenses_view, text MM/DD/YYYY
watermark with the lexical-sort trap), and property sales (Property_Sales_,
date watermark, batch cadence — 7d=0 at the 2026-08-27 re-probe). The probe's
"native points" note for Property_Sales_ is stale: the live service exposes
no geometry, so deeds are address-only like the other two feeds.

Tests pass WITHOUT a spine registration (no CityId.VIRGINIA_BEACH): the
producers resolve city_id="virginia_beach" as a plain string, the leaf-local
field maps are pinned via resolve_field_map patches, and geocoding is mocked
at src.spatial.geocoder.geocode_row_if_declared (Norfolk pattern).

Live fixtures captured from the 2026-08-27 re-probe (all watermarks match
docs/research/probe-virginia_beach.md; ≥2 rows per feed). Re-verified live
on the 2026-08-28 implementation re-probe — every fixture byte-matches the
service (OBJECTIDs, epoch-ms Sales_Date flattened to ISO, cohort counts).
SLA correction recorded in the leaf module docstring: typed-2026 total is
2,862, not the probe's "2026 YTD 77" (that was a newest-cohort window).
"""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.producers.field_maps_virginia_beach import (
    DEEDS_FIELD_MAP,
    DROPPED_PII_COLUMNS,
    FIELD_MAP,
    GEOCODE_CONTEXT,
    PERMITS_FIELD_MAP,
    SLA_FIELD_MAP,
)
from src.producers.watermarks import (
    compare_watermarks,
    newest_typed_watermark,
    typed_watermark_entry,
)
from src.spatial.cities.virginia_beach import (
    VIRGINIA_BEACH_CENTER,
    VIRGINIA_BEACH_CITY_ID,
    VIRGINIA_BEACH_DEEDS_ENDPOINT,
    VIRGINIA_BEACH_DIVISION_BBOXES,
    VIRGINIA_BEACH_DIVISIONS,
    VIRGINIA_BEACH_FEED_SPECS,
    VIRGINIA_BEACH_GEOCODE_CONTEXT,
    VIRGINIA_BEACH_METRO_BBOX,
    VIRGINIA_BEACH_PERMITS_ENDPOINT,
    VIRGINIA_BEACH_SLA_ENDPOINT,
    VIRGINIA_BEACH_SUBMARKETS,
    REGISTRATION,
    get_virginia_beach_dataset,
    is_in_virginia_beach_metro,
)
from src.spatial.city_registry import FeedType
from src.spatial.geocoder import _STATE_RE, normalize_address


# ---------------------------------------------------------------------------
# Live fixtures (2026-08-27 re-probe, services2.arcgis.com CyVvlIiUfRBmMQuu).
# ---------------------------------------------------------------------------

# Newest permits by IssueDate DESC — newest row 2026/08/21 (text, 7d=247).
PERMITS_ROW_HOOD_EXHAUST = {
    "PermitNumber": "2026-MECC-10572",
    "CreatedBy": "PUBLICUSER22688",
    "PermitType": "Mechanical",
    "ConstructionType": "Commercial",
    "WorkType": "",
    "ApplicationDate": "2026/04/21",
    "IssueDate": "2026/08/21",
    "FinalDate": None,
    "Status": "Active",
    "WorkDesc": "Installing a new six foot hood and exhaust fan",
    "GPIN": "24175575610000",
    "StreetAddress": "1085 VIRGINIA BEACH BLVD",
    "AddressUnit": "",
    "City": "Virginia Beach",
    "State": "VA",
    "Zip": "23451",
    "OBJECTID": 95180,
}

PERMITS_ROW_SECOND_STORY = {
    "PermitNumber": "2026-BDRA-16146",
    "CreatedBy": "PUBLICUSER25035",
    "PermitType": "Building",
    "ConstructionType": "Residential",
    "WorkType": "Addition and or Alteration",
    "ApplicationDate": "2026/06/17",
    "IssueDate": "2026/08/21",
    "FinalDate": None,
    "Status": "Active",
    "WorkDesc": "ADDITION OF 2ND STORY TO RESIDENCE",
    "GPIN": "14692485820000",
    "StreetAddress": "5533 NORLINA RD",
    "AddressUnit": "",
    "City": "Virginia Beach",
    "State": "VA",
    "Zip": "23455",
    "OBJECTID": 100245,
}

PERMITS_ROW_NEW_SFR = {
    "PermitNumber": "2026-BDRN-17974",
    "CreatedBy": "PUBLICUSER295",
    "PermitType": "Building",
    "ConstructionType": "Residential",
    "WorkType": "New",
    "ApplicationDate": "2026/07/07",
    "IssueDate": "2026/08/21",
    "FinalDate": None,
    "Status": "Active",
    "WorkDesc": "NEW SF - 2021 USBC / USE R5 / CONSTRUCTION TYPE 5B/ NON-SPRINKLERED",
    "GPIN": "14999822310000",
    "StreetAddress": "2425 WINDWARD SHORE DR",
    "AddressUnit": "",
    "City": "Virginia Beach",
    "State": "VA",
    "Zip": "23451",
    "OBJECTID": 101931,
}

# Newest 2026 licenses (Begin_Date text MM/DD/YYYY — newest 07/31/2026).
SLA_ROW_HEADLIGHT = {
    "Begin_Date": "07/31/2026",
    "Owner_Name": " BEACON HEADLIGHT RESTORATION LLC",
    "Trade_Name": "BEACON HEADLIGHT RESTORATION LLC",
    "Business_Address": "749 WATERS DR",
    "Business_City": "VIRGINIA BEACH",
    "Business_State": "VA",
    "Business_ZipCode": 23462,
    "Business_ZipCode_Ext": 4870,
    "Telephone": "757-354-4526",
    "Mailing_Address": "749 WATERS DR",
    "Mailing_City": "VIRGINIA BEACH",
    "Mailing_State": "VA",
    "Mailing_Zip_Code": 23462,
    "Mailing_ZipCode_Ext": 4870,
    "NAICS": "811192-02",
    "Business_Classification": "Automobile Detailer",
    "OBJECTID": 411161,
}

SLA_ROW_BEAUTY = {
    "Begin_Date": "07/31/2026",
    "Owner_Name": " GLUCKLE, JENNI R",
    "Trade_Name": "JENNI R GLUCKLE",
    "Business_Address": "2201 E BERRIE CIR",
    "Business_City": "VIRGINIA BEACH",
    "Business_State": "VA",
    "Business_ZipCode": 23455,
    "Business_ZipCode_Ext": 1903,
    "Telephone": "757-729-5364",
    "Mailing_Address": "2201 E BERRIE CIR",
    "Mailing_City": "VIRGINIA BEACH",
    "Mailing_State": "VA",
    "Mailing_Zip_Code": 23455,
    "Mailing_ZipCode_Ext": 1903,
    "NAICS": "812112-01",
    "Business_Classification": "Beauty Salon",
    "OBJECTID": 412830,
}

# Newest sales rows (Sales_Date date-typed → ISO after ArcGISClient flatten;
# newest batch landed 2026-08-10; 7d=0 — batch publication caveat).
DEEDS_ROW_PUNGO_ZERO = {
    "GPIN": "23098177880000",
    "Street_Address": "5701 Aura Dr",
    "City": "Virginia Beach",
    "State": "VA",
    "Zip_Code": "23457-1327      ",
    "Neighborhood": "Pungo",
    "Land_Value": 277800,
    "Improvement_Value": 514900,
    "Total_Value": 792700,
    "Land_USE_yes_or_no": "No",
    "Sale_Price": 0,
    "Document_Number": "2015014001001990",
    "Deed_Book": "",
    "Deed_Page": "",
    "OBJECTID": 21582,
    "Sales_Date": "2026-08-10T00:00:00+00:00",
}

DEEDS_ROW_BLVD_ZERO = {
    "GPIN": "14979570630000",
    "Street_Address": "2335 Virginia Beach Blvd",
    "City": "Virginia Beach",
    "State": "VA",
    "Zip_Code": "23454           ",
    "Neighborhood": "Va Beach Blvd",
    "Land_Value": 320600,
    "Improvement_Value": 101500,
    "Total_Value": 422100,
    "Land_USE_yes_or_no": "No",
    "Sale_Price": 0,
    "Document_Number": "2015104001001980",
    "Deed_Book": "",
    "Deed_Page": "",
    "OBJECTID": 210677,
    "Sales_Date": "2026-08-10T00:00:00+00:00",
}

DEEDS_ROW_ANDERSON = {
    "GPIN": "14563147900000",
    "Street_Address": "1028 Anderson Way",
    "City": "Virginia Beach",
    "State": "VA",
    "Zip_Code": "23464-3707      ",
    "Neighborhood": "College Park",
    "Land_Value": 130000,
    "Improvement_Value": 226900,
    "Total_Value": 356900,
    "Land_USE_yes_or_no": "No",
    "Sale_Price": 385000,
    "Document_Number": "202603038274",
    "Deed_Book": "",
    "Deed_Page": "",
    "OBJECTID": 394071,
    "Sales_Date": "2026-08-05T00:00:00+00:00",
}

# Mocked ADR-0004 geocodes (address-plausible, inside the metro):
PERMITS_GEOCODE_OCEANFRONT = (36.8510, -75.9820)   # 1085 Virginia Beach Blvd
SLA_GEOCODE_TOWN_CENTER = (36.8380, -76.1250)      # 749 Waters Dr
SLA_GEOCODE_BAYSIDE = (36.8850, -76.1450)          # 2201 E Berrie Cir

GEOCODE_TABLE = {
    "1085 VIRGINIA BEACH BLVD": PERMITS_GEOCODE_OCEANFRONT,
    "749 WATERS DR": SLA_GEOCODE_TOWN_CENTER,
    "2201 E BERRIE CIR": SLA_GEOCODE_BAYSIDE,
}


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


class TestVirginiaBeachSpatial:
    def test_city_id_constant(self):
        assert VIRGINIA_BEACH_CITY_ID == "virginia_beach"

    def test_metro_contains_registration_center(self):
        assert is_in_virginia_beach_metro(
            VIRGINIA_BEACH_CENTER["lat"], VIRGINIA_BEACH_CENTER["lng"]
        ) is True

    def test_metro_contains_known_landmarks(self):
        assert is_in_virginia_beach_metro(36.8529, -75.9780) is True  # Oceanfront
        assert is_in_virginia_beach_metro(36.8528, -76.1089) is True  # Town Center
        assert is_in_virginia_beach_metro(36.8200, -76.1750) is True  # Kempsville
        assert is_in_virginia_beach_metro(36.6468, -75.9290) is True  # Sandbridge
        assert is_in_virginia_beach_metro(36.7000, -76.0100) is True  # Pungo

    def test_metro_rejects_null_and_neighbors(self):
        assert is_in_virginia_beach_metro(None, None) is False
        assert is_in_virginia_beach_metro(36.9450, -76.3300) is False  # Norfolk Ocean View
        assert is_in_virginia_beach_metro(36.9500, -76.3300) is False  # Naval Station Norfolk
        assert is_in_virginia_beach_metro(36.8470, -76.3570) is False  # Portsmouth
        assert is_in_virginia_beach_metro(36.7180, -76.2300) is False  # Chesapeake (Great Bridge)
        assert is_in_virginia_beach_metro(37.5400, -77.4400) is False  # Richmond
        assert is_in_virginia_beach_metro(36.1000, -75.7000) is False  # NC Outer Banks

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in VIRGINIA_BEACH_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= VIRGINIA_BEACH_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= VIRGINIA_BEACH_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= VIRGINIA_BEACH_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= VIRGINIA_BEACH_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in VIRGINIA_BEACH_SUBMARKETS.items():
            bbox = VIRGINIA_BEACH_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in VIRGINIA_BEACH_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(VIRGINIA_BEACH_SUBMARKETS)

    def test_submarkets_carry_virginia_beach_city_id(self):
        assert {m.city_id for m in VIRGINIA_BEACH_SUBMARKETS.values()} == {"virginia_beach"}

    def test_division_centers_sit_inside_their_bbox(self):
        for name, meta in VIRGINIA_BEACH_DIVISIONS.items():
            bbox = VIRGINIA_BEACH_DIVISION_BBOXES[name]
            assert bbox["min_lat"] <= meta.center_lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.center_lng <= bbox["max_lng"], name

    def test_division_count(self):
        assert len(VIRGINIA_BEACH_DIVISIONS) == 5
        for div in VIRGINIA_BEACH_DIVISIONS.values():
            assert div.city_id == "virginia_beach"

    def test_registration_bundles_leaf_constants(self):
        assert REGISTRATION.metro_bbox is VIRGINIA_BEACH_METRO_BBOX
        assert REGISTRATION.submarkets is VIRGINIA_BEACH_SUBMARKETS
        assert REGISTRATION.contains is is_in_virginia_beach_metro


class TestFeedRegistration:
    def test_exactly_three_feed_types_are_registered(self):
        assert set(VIRGINIA_BEACH_FEED_SPECS) == {"permits", "sla", "deeds"}

    def test_permits_spec_matches_probe_contract(self):
        spec = get_virginia_beach_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == VIRGINIA_BEACH_PERMITS_ENDPOINT
        assert spec.watermark_col == "IssueDate"
        assert spec.watermark_type == "text"
        assert spec.watermark_format == "%Y/%m/%d"
        assert spec.id_keys == ["PermitNumber", "OBJECTID"]
        assert spec.producer_key == "permits"
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Virginia Beach, VA"
        assert spec.oid_field == "OBJECTID"
        assert spec.max_record_count == 2000
        assert spec.expected_cadence_days == 1
        assert spec.non_spatial is True
        assert spec.field_map is PERMITS_FIELD_MAP

    def test_sla_spec_declares_text_watermark_and_id_trio(self):
        spec = get_virginia_beach_dataset(FeedType.SLA)
        assert spec.platform == "arcgis"
        assert spec.endpoint == VIRGINIA_BEACH_SLA_ENDPOINT
        assert spec.watermark_col == "Begin_Date"
        assert spec.watermark_type == "text"
        assert spec.watermark_format == "%m/%d/%Y"
        assert spec.id_keys == ["Trade_Name", "Owner_Name", "Business_Address"]
        assert spec.producer_key == "sla"
        assert spec.needs_geocode is True
        assert spec.expected_cadence_days == 365
        assert spec.non_spatial is True
        assert spec.field_map is SLA_FIELD_MAP

    def test_deeds_spec_declares_batch_cadence_and_address_only_contract(self):
        spec = get_virginia_beach_dataset(FeedType.DEEDS)
        assert spec.platform == "arcgis"
        assert spec.endpoint == VIRGINIA_BEACH_DEEDS_ENDPOINT
        assert spec.watermark_col == "Sales_Date"
        assert spec.id_keys == ["Document_Number", "GPIN", "Sales_Date"]
        assert spec.producer_key == "deeds"
        # The live service is a TABLE: address-only with ADR-0004 geocoding.
        assert spec.needs_geocode is True
        assert spec.geocode_context == "Virginia Beach, VA"
        assert spec.non_spatial is True
        # Memphis monthly-cadence precedent: batch publication every ~2-3 weeks.
        assert spec.expected_cadence_days == 14
        assert "BATCH" in VIRGINIA_BEACH_FEED_SPECS["deeds"]["extra"]["scope"]
        assert "stalled" in VIRGINIA_BEACH_FEED_SPECS["deeds"]["extra"]["scope"]

    @pytest.mark.parametrize(
        "absent_feed",
        [FeedType.COMPLAINTS_311, FeedType.CRIME, FeedType.STR],
    )
    def test_absent_feeds_raise_readable_errors(self, absent_feed):
        with pytest.raises(KeyError, match=r"'virginia_beach'.*available"):
            get_virginia_beach_dataset(absent_feed)

    def test_field_map_export_keys(self):
        assert FIELD_MAP["permits"] is PERMITS_FIELD_MAP
        assert FIELD_MAP["sla"] is SLA_FIELD_MAP
        assert FIELD_MAP["deeds"] is DEEDS_FIELD_MAP
        assert GEOCODE_CONTEXT == VIRGINIA_BEACH_GEOCODE_CONTEXT == "Virginia Beach, VA"
        assert "311" not in FIELD_MAP


class TestVirginiaBeachFieldMaps:
    def test_permits_map_reads_live_columns(self):
        row = PERMITS_ROW_HOOD_EXHAUST
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == "2026-MECC-10572"
        assert first_mapped(row, PERMITS_FIELD_MAP, "issuance_date") == "2026/08/21"
        assert first_mapped(row, PERMITS_FIELD_MAP, "filing_date") == "2026/04/21"
        assert first_mapped(row, PERMITS_FIELD_MAP, "address_street") == "1085 VIRGINIA BEACH BLVD"
        assert first_mapped(row, PERMITS_FIELD_MAP, "bbl") == "24175575610000"
        assert first_mapped(row, PERMITS_FIELD_MAP, "borough") == "Virginia Beach"
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_type") == "Mechanical"

    def test_permits_job_id_falls_back_when_permit_number_is_null(self):
        row = {"PermitNumber": None, "OBJECTID": 95180}
        assert first_mapped(row, PERMITS_FIELD_MAP, "job_id") == 95180

    def test_permits_feed_has_no_valuation_or_coordinates(self):
        assert "cost" not in PERMITS_FIELD_MAP
        assert "latitude" not in PERMITS_FIELD_MAP
        assert "longitude" not in PERMITS_FIELD_MAP

    def test_sla_map_reads_live_columns(self):
        row = SLA_ROW_HEADLIGHT
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == "BEACON HEADLIGHT RESTORATION LLC"
        assert first_mapped(row, SLA_FIELD_MAP, "dba") == "BEACON HEADLIGHT RESTORATION LLC"
        assert first_mapped(row, SLA_FIELD_MAP, "premises_name") == " BEACON HEADLIGHT RESTORATION LLC"
        assert first_mapped(row, SLA_FIELD_MAP, "license_type") == "Automobile Detailer"
        assert first_mapped(row, SLA_FIELD_MAP, "effective_date") == "07/31/2026"
        assert first_mapped(row, SLA_FIELD_MAP, "address_street") == "749 WATERS DR"
        assert first_mapped(row, SLA_FIELD_MAP, "zipcode") == 23462

    def test_sla_map_has_no_license_number_so_id_falls_back_to_owner(self):
        row = {"Trade_Name": None, "Owner_Name": " GLUCKLE, JENNI R"}
        assert first_mapped(row, SLA_FIELD_MAP, "license_id") == " GLUCKLE, JENNI R"

    def test_sla_pii_columns_are_never_candidates(self):
        candidates = {key for cands in SLA_FIELD_MAP.values() for key in cands}
        assert candidates.isdisjoint(DROPPED_PII_COLUMNS)
        for pii in DROPPED_PII_COLUMNS:
            assert pii in SLA_ROW_HEADLIGHT  # the live row carries them — we drop them

    def test_deeds_map_reads_live_columns(self):
        row = DEEDS_ROW_ANDERSON
        assert first_mapped(row, DEEDS_FIELD_MAP, "doc_id") == "202603038274"
        assert first_mapped(row, DEEDS_FIELD_MAP, "bbl") == "14563147900000"
        assert first_mapped(row, DEEDS_FIELD_MAP, "document_amount") == 385000
        assert first_mapped(row, DEEDS_FIELD_MAP, "recorded_date") == "2026-08-05T00:00:00+00:00"
        assert first_mapped(row, DEEDS_FIELD_MAP, "address_street") == "1028 Anderson Way"
        assert first_mapped(row, DEEDS_FIELD_MAP, "borough") == "College Park"

    def test_deeds_map_has_no_party_or_coordinate_candidates(self):
        assert "party1_grantor" not in DEEDS_FIELD_MAP
        assert "party2_grantee" not in DEEDS_FIELD_MAP
        assert "latitude" not in DEEDS_FIELD_MAP
        assert "longitude" not in DEEDS_FIELD_MAP


class TestWatermarkTyping:
    """All three VB watermarks per the probe contract (ADR 0005)."""

    def test_permits_yyyyslashmmdd_text_watermark(self):
        entry = typed_watermark_entry("2026/08/21", fmt="%Y/%m/%d")
        assert entry is not None
        assert entry[0] == "2026/08/21"
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 21)

    def test_sla_mmddyyyy_text_watermark(self):
        entry = typed_watermark_entry("07/31/2026", fmt="%m/%d/%Y")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 7, 31)

    def test_sla_typed_comparison_beats_lexical_order(self):
        """THE TRAP: "12/31/2025" sorts lexically ABOVE "07/31/2026" but is
        the older date. Typed comparison (declared %m/%d/%Y) must pick the
        true newest; a naive DESC first row would pin the watermark a year
        in the past."""
        assert compare_watermarks("12/31/2025", "07/31/2026") < 0
        newest = newest_typed_watermark(
            ["07/31/2026", "12/31/2025", "07/31/2026"], fmt="%m/%d/%Y"
        )
        assert newest is not None
        assert newest[0] == "07/31/2026"

    def test_deeds_iso_watermark_parses_under_default(self):
        entry = typed_watermark_entry("2026-08-10T00:00:00+00:00")
        assert entry is not None
        assert (entry[1].year, entry[1].month, entry[1].day) == (2026, 8, 10)

    def test_empty_watermark_values_are_dropped(self):
        assert typed_watermark_entry("", fmt="%Y/%m/%d") is None
        assert typed_watermark_entry(None, fmt="%m/%d/%Y") is None


class TestVirginiaBeachPermitParsing:
    def test_address_only_permit_uses_declared_geocoder(self, permits, monkeypatch):
        captured = []
        _patch_resolve(monkeypatch, "permits")

        def fake_geocode(city_id, feed_value, address, context=None):
            captured.append((city_id, feed_value, address, context))
            return GEOCODE_TABLE.get(address.strip(), PERMITS_GEOCODE_OCEANFRONT)

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        event = permits.parse_socrata_row(PERMITS_ROW_HOOD_EXHAUST, city_id="virginia_beach")
        assert event is not None
        assert event.city_id == "virginia_beach"
        assert event.job_id == "2026-MECC-10572"
        assert event.latitude == pytest.approx(PERMITS_GEOCODE_OCEANFRONT[0])
        assert event.longitude == pytest.approx(PERMITS_GEOCODE_OCEANFRONT[1])
        assert event.h3_res7 is not None
        assert captured == [
            ("virginia_beach", "permits", "1085 VIRGINIA BEACH BLVD", None)
        ]

    def test_permit_geocode_sits_inside_metro(self):
        assert is_in_virginia_beach_metro(*PERMITS_GEOCODE_OCEANFRONT)

    def test_text_yyyyslashmmdd_issue_date_does_not_parse_to_event_datetime(
        self, permits, monkeypatch
    ):
        """Honest gap: the producer's date chain has no %Y/%m/%d format, so
        the EVENT carries issuance_date=None while the WATERMARK machinery
        (declared format, tested above) keeps ordering correct. If the spine
        ever teaches the parser this format, tighten this assertion."""
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_OCEANFRONT,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_HOOD_EXHAUST, city_id="virginia_beach")
        assert event is not None
        assert event.issuance_date is None
        assert event.filing_date is None

    def test_permit_without_address_is_dropped(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        row = {**PERMITS_ROW_HOOD_EXHAUST, "StreetAddress": ""}
        assert permits.parse_socrata_row(row, city_id="virginia_beach") is None

    def test_permit_feeds_no_valuation_column(self, permits, monkeypatch):
        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_OCEANFRONT,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_HOOD_EXHAUST, city_id="virginia_beach")
        assert event is not None
        assert event.estimated_cost == 0.0

    def test_new_sfr_classifies_as_nb(self, permits, monkeypatch):
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_OCEANFRONT,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_NEW_SFR, city_id="virginia_beach")
        assert event is not None
        assert event.job_id == "2026-BDRN-17974"
        assert event.job_type == JobType.NB

    def test_second_story_addition_classifies_as_a2(self, permits, monkeypatch):
        from src.schemas.models import JobType

        _patch_resolve(monkeypatch, "permits")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: PERMITS_GEOCODE_OCEANFRONT,
        )
        event = permits.parse_socrata_row(PERMITS_ROW_SECOND_STORY, city_id="virginia_beach")
        assert event is not None
        assert event.job_type == JobType.A2


class TestVirginiaBeachSlaParsing:
    def test_address_only_license_uses_declared_geocoder(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")

        def fake_geocode(city_id, feed_value, address, context=None):
            return GEOCODE_TABLE.get(address.strip(), SLA_GEOCODE_TOWN_CENTER)

        monkeypatch.setattr("src.spatial.geocoder.geocode_row_if_declared", fake_geocode)
        event = sla.parse_socrata_row(SLA_ROW_HEADLIGHT, city_id="virginia_beach")
        assert event is not None
        assert event.city_id == "virginia_beach"
        assert event.license_id == "BEACON HEADLIGHT RESTORATION LLC"
        assert event.dba == "BEACON HEADLIGHT RESTORATION LLC"
        assert event.premises_name == " BEACON HEADLIGHT RESTORATION LLC"
        assert event.license_type == "Automobile Detailer"
        assert event.address == "749 WATERS DR"
        assert event.latitude == pytest.approx(SLA_GEOCODE_TOWN_CENTER[0])
        assert event.longitude == pytest.approx(SLA_GEOCODE_TOWN_CENTER[1])
        assert event.h3_res7 is not None and event.h3_res9 is not None
        assert str(event.effective_date).startswith("2026-07-31")

    def test_sla_geocode_sits_inside_metro(self):
        assert is_in_virginia_beach_metro(*SLA_GEOCODE_TOWN_CENTER)
        assert is_in_virginia_beach_metro(*SLA_GEOCODE_BAYSIDE)

    def test_license_without_trade_name_falls_back_to_owner(self, sla, monkeypatch):
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: SLA_GEOCODE_BAYSIDE,
        )
        row = {**SLA_ROW_BEAUTY, "Trade_Name": None}
        event = sla.parse_socrata_row(row, city_id="virginia_beach")
        assert event is not None
        assert event.license_id == "GLUCKLE, JENNI R"  # producer strips the id

    def test_geocode_failure_keeps_null_coord_event(self, sla, monkeypatch):
        """SLA producer tolerance: a row whose geocode fails still emits as a
        null-lat/lng/null-H3 event (DC precedent) rather than being dropped."""
        _patch_resolve(monkeypatch, "sla")
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: None,
        )
        event = sla.parse_socrata_row(SLA_ROW_HEADLIGHT, city_id="virginia_beach")
        assert event is not None
        assert event.latitude is None and event.longitude is None
        assert event.h3_res7 is None and event.h3_res9 is None


class TestVirginiaBeachDeedsParsing:
    def test_table_row_parses_lossless_without_spec(self, deeds, monkeypatch):
        """The live Property_Sales_ service is a TABLE (no geometry), so
        coordinates/H3 are only populated through the ADR-0005 geocode hook.
        Post-spine the VB deeds spec has needs_geocode=True, so the hook IS
        invoked with the Street_Address; a None geocoder result leaves the
        row lossless (fields intact, coordinates/H3 null)."""
        _patch_resolve(monkeypatch, "deeds")
        calls = []
        monkeypatch.setattr(
            "src.spatial.geocoder.geocode_row_if_declared",
            lambda *args, **kwargs: calls.append(args) or None,
        )
        event = deeds.parse_socrata_row(DEEDS_ROW_ANDERSON, city_id="virginia_beach")
        assert event is not None
        assert calls == [("virginia_beach", "deeds", "1028 Anderson Way")]
        assert event.city_id == "virginia_beach"
        assert event.latitude is None and event.longitude is None
        assert event.h3_res7 is None and event.h3_res9 is None

    def test_doc_id_and_bbl_read_document_number_and_gpin(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW_ANDERSON, city_id="virginia_beach")
        assert event is not None
        assert event.doc_id == "202603038274"
        assert event.bbl == "14563147900000"

    def test_priced_sale_maps_amount_and_iso_recorded_date(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW_ANDERSON, city_id="virginia_beach")
        assert event is not None
        assert event.document_amount == 385000.0
        assert str(event.recorded_date).startswith("2026-08-05")
        assert event.doc_type == "DEED"

    def test_zero_price_transfer_is_kept(self, deeds, monkeypatch):
        """$0 transfers (quasi-judicial/split deeds) parse and stay in the
        register with a 0.0 amount — probe precedent for non-arms-length
        rows."""
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW_PUNGO_ZERO, city_id="virginia_beach")
        assert event is not None
        assert event.document_amount == 0.0
        assert str(event.recorded_date).startswith("2026-08-10")

    def test_neighborhood_becomes_source_neighborhood(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        event = deeds.parse_socrata_row(DEEDS_ROW_PUNGO_ZERO, city_id="virginia_beach")
        assert event is not None
        assert event.source_neighborhood == "Pungo"

    def test_both_newest_batch_rows_parse(self, deeds, monkeypatch):
        _patch_resolve(monkeypatch, "deeds")
        for row in (DEEDS_ROW_PUNGO_ZERO, DEEDS_ROW_BLVD_ZERO):
            assert deeds.parse_socrata_row(row, city_id="virginia_beach") is not None


class TestGeocodingCaveats:
    def test_vb_street_has_no_state_token_so_context_appends(self):
        assert _STATE_RE.search("1085 Virginia Beach Blvd".upper()) is None

    def test_context_with_va_is_a_state_token(self):
        assert _STATE_RE.search("1085 VIRGINIA BEACH BLVD, VA".upper()) is not None

    def test_unit_designator_normalization_preserves_city(self):
        norm = normalize_address("749 WATERS DR SUITE 200, VIRGINIA BEACH, VA")
        assert "SUITE" not in norm
        assert "VIRGINIA" in norm
