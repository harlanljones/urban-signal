"""Contract tests for Columbus, OH (ArcGIS building permits + deeds)."""

from unittest.mock import patch

import pytest

from src.spatial.cities.columbus import (
    COLUMBUS_DIVISION_BBOXES,
    COLUMBUS_DIVISIONS,
    COLUMBUS_METRO_BBOX,
    COLUMBUS_SUBMARKETS,
    is_in_columbus_metro,
)
from src.spatial.city_registry import CityId, FeedType

# Recommended DatasetSpec.field_map for HJ-118. Every entry spells a
# column the shared producer fallback chains cannot reach (uppercase Accela
# schema); latitude/longitude need no entry because ArcGISClient lifts point
# geometry onto those exact keys before parsing.
COLUMBUS_FIELD_MAP = {
    "job_id": ["B1_ALT_ID"],
    "issuance_date": ["ISSUED_DT"],
    "cost": ["G3_VALUE_TTL"],
    "address_street": ["SITE_ADDRESS"],
    "zipcode": ["B1_SITUS_ZIP"],
    "status": ["PERMIT_STATUS"],
    "job_type": ["B1_PER_TYPE"],
}

# Recommended DatasetSpec.field_map for US-127 (Franklin County
# Auditor sales points). Dual old/new schema: Sale_Price + OWN1/OWN2 populate
# every row (1568/1568) while SALEPRICE (1543) and Instrument_Number/
# MUNINAME/NHBDNAME (0) are partial/empty layer-wide — hence the fully
# populated "new" side first on the price/parties candidates.
COLUMBUS_DEEDS_FIELD_MAP = {
    "doc_id": ["Instrument_Number", "PARCELID"],
    "bbl": ["PARCELID"],
    "document_amount": ["Sale_Price", "SALEPRICE"],
    "recorded_date": ["SALEDATE"],
    "party1_grantor": ["OWNERNME1"],
    "party2_grantee": ["OWN1", "OWN2"],
    "incident_address": ["SITEADDRESS"],
    "zipcode": ["ZIPCD"],
    "borough": ["MUNINAME", "NHBDNAME"],
}


def test_columbus_geometry_is_self_consistent():
    assert is_in_columbus_metro(39.9612, -83.0007)
    assert is_in_columbus_metro(40.1553, -82.7928)  # observed live-row corner
    assert not is_in_columbus_metro(39.1031, -84.5120)  # Cincinnati
    assert not is_in_columbus_metro(None, None)
    for name, bbox in COLUMBUS_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= COLUMBUS_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= COLUMBUS_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= COLUMBUS_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= COLUMBUS_METRO_BBOX["max_lng"], name
    claimed = [name for division in COLUMBUS_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(COLUMBUS_SUBMARKETS)
    assert {meta.city_id for meta in COLUMBUS_SUBMARKETS.values()} == {"columbus"}


def test_columbus_registers_arcgis_permits_and_deeds():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.COLUMBUS
    assert normalize_city("columbus") is city
    assert normalize_city("columbus_oh") is city
    assert REGISTRY[city].job_suffix == "cmoh"
    assert set(REGISTRY[city].datasets) == {FeedType.PERMITS, FeedType.DEEDS}

    permits = REGISTRY[city].datasets[FeedType.PERMITS]
    assert permits.platform == "arcgis"
    # Actual layer casing: the FeatureServer column is uppercase ISSUED_DT.
    assert permits.watermark_col == "ISSUED_DT"
    assert permits.interval_seconds == 300.0
    assert permits.producer_key == "permits"
    # HJ-118 quirk: B1_ALT_ID identifies the permit; OBJECTID must never join
    # the job-id chain (it is an edit counter, not a business key).
    assert "B1_ALT_ID" in permits.id_keys
    assert "OBJECTID" not in permits.id_keys
    assert permits.expected_cadence_days == 7
    assert permits.oid_field == "OBJECTID"
    assert permits.max_record_count == 2000
    assert permits.field_map == COLUMBUS_FIELD_MAP

    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.COMPLAINTS_311)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.SLA)


def test_columbus_deeds_spec_pins_arcgis_annual_snapshot():
    from src.spatial.city_registry import get_dataset

    spec = get_dataset(CityId.COLUMBUS, FeedType.DEEDS)
    assert spec.platform == "arcgis"
    assert spec.endpoint == (
        "https://services1.arcgis.com/7r2Wl09a1Apy459r/arcgis/rest/services/"
        "FCAO_Sales_Dashboard_Last_Years_Sales_Points/FeatureServer/0"
    )
    # Actual layer casing: SALEDATE is the sale-date field on the wire.
    assert spec.watermark_col == "SALEDATE"
    assert spec.id_keys == ["PARCELID", "Instrument_Number", "OBJECTID"]
    assert spec.topic == "raw.municipal.deeds"
    assert spec.producer_key == "deeds"
    # Annual snapshot (lastEditDate 2026-07-31); the layer caps a page at 2000.
    assert spec.expected_cadence_days == 365
    assert spec.oid_field == "OBJECTID"
    assert spec.max_record_count == 2000
    assert spec.field_map == COLUMBUS_DEEDS_FIELD_MAP


CB_PERMIT_ROW = {
    # Live newest nonzero-valuation row via REST on 2026-08-24
    # (orderByFields=ISSUED_DT DESC), flattened exactly as
    # ArcGISClient._flatten_feature delivers it: attributes dict, point
    # geometry lifted to latitude/longitude, epoch-ms date fields re-encoded
    # to ISO 8601 UTC strings.
    "OBJECTID": 399023,
    "B1_ALT_ID": "RSWDR2633792",
    "B1_PER_GROUP": "Building",
    "B1_PER_TYPE": "1,2,3 Family",
    "B1_PER_SUB_TYPE": "Structural",
    "B1_PER_CATEGORY": "Roof, Siding, Windows, Doors",
    "GENERAL_TYPE": "1,2,3 Family - Other",
    "B1_PARCEL_NBR": "010267526",
    "COLS_KEY": 1209889,
    "SITE_ADDRESS": "5504 OCONNELL ST",
    "B1_SITUS_ZIP": "43110",
    "PERMIT_STATUS": "Permit Issued",
    "APPLICANT_BUS_NAME": "ROOF DETECTIVE",
    "SQFT": 2163,
    "G3_VALUE_TTL": 12630.05,
    "ISSUED_YEAR": 2026,
    "ISSUED_DT": "2026-08-22T00:00:00+00:00",
    "LAST_STATUS_DT": "2026-08-22T14:49:17+00:00",
    "CONST_TYPE_CODE": "434",
    "VALUE_DESC": "Additions, Alterations and Conversions - Residential",
    "UNITS": 1,
    "latitude": 39.893814520648746,
    "longitude": -82.84871670417796,
}

CB_ZERO_VALUATION_ROW = {
    # Live newest zero-valuation row via REST on 2026-08-24. G3_VALUE_TTL = 0
    # is legitimate and common (~63% of the newest 300 since 2026-07-01):
    # mechanical trade tickets carry no declared project cost.
    "OBJECTID": 104385,
    "B1_ALT_ID": "MMLSR2633793",
    "B1_PER_GROUP": "Building",
    "B1_PER_TYPE": "1,2,3 Family",
    "B1_PER_SUB_TYPE": "MEP",
    "B1_PER_CATEGORY": "Mechanical",
    "GENERAL_TYPE": "1,2,3 Family - Other",
    "B1_PARCEL_NBR": "010041404",
    "COLS_KEY": 160300,
    "SITE_ADDRESS": "1180 ELLSWORTH AVE",
    "B1_SITUS_ZIP": "43206",
    "PERMIT_STATUS": "Permit Issued",
    "APPLICANT_BUS_NAME": "AIRWAYS HEATING & COOLING LLC",
    "SQFT": None,
    "G3_VALUE_TTL": 0,
    "ISSUED_YEAR": 2026,
    "ISSUED_DT": "2026-08-22T00:00:00+00:00",
    "LAST_STATUS_DT": "2026-08-22T00:00:00+00:00",
    "CONST_TYPE_CODE": None,
    "VALUE_DESC": None,
    "UNITS": None,
    "latitude": 39.94206671489354,
    "longitude": -82.96107831565743,
}


class TestColumbusPermitParsing:
    """Parse pins against the shared DOBPermitsProducer.

    ``resolve_field_map`` is patched with the exact map recommended for the
    registration because the registry entry itself lands with the spine; the
    registration test above asserts the spec carries this same literal, so the
    two cannot drift once HJ-118 is wired.
    """

    @pytest.fixture
    def producer(self):
        with (
            patch("src.producers.dob_permits_producer.BaseKafkaProducer"),
            patch(
                "src.producers.field_maps.resolve_field_map",
                return_value=COLUMBUS_FIELD_MAP,
            ),
        ):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            yield DOBPermitsProducer()

    def test_live_newest_row_parses_uppercase_schema(self, producer):
        event = producer.parse_socrata_row(dict(CB_PERMIT_ROW), city_id="columbus")
        assert event is not None
        assert event.city_id == "columbus"
        assert event.job_id == "RSWDR2633792"  # B1_ALT_ID, never str(OBJECTID)
        assert event.status == "Permit Issued"
        assert event.address_street == "5504 OCONNELL ST"
        assert event.zipcode == "43110"
        assert event.estimated_cost == pytest.approx(12630.05)
        assert event.issuance_date is not None
        assert (event.issuance_date.year, event.issuance_date.month, event.issuance_date.day) == (
            2026,
            8,
            22,
        )
        assert event.latitude == pytest.approx(39.893814520648746)
        assert event.longitude == pytest.approx(-82.84871670417796)

    def test_zero_valuation_is_legitimate_not_a_parse_failure(self, producer):
        event = producer.parse_socrata_row(dict(CB_ZERO_VALUATION_ROW), city_id="columbus")
        assert event is not None
        assert event.job_id == "MMLSR2633793"
        assert event.estimated_cost == 0.0

    def test_objectid_never_rescues_a_missing_b1_alt_id(self, producer):
        # With B1_ALT_ID removed the id chain must come up empty even though
        # OBJECTID is present: the OID field stays out of the job-id chain.
        row = dict(CB_PERMIT_ROW)
        row.pop("B1_ALT_ID")
        assert producer.parse_socrata_row(row, city_id="columbus") is None


# Live newest-by-SALEDATE row captured 2026-08-25 from the FCAO sales points
# layer via query?where=1=1&orderByFields=SALEDATE DESC&outSR=4326, flattened
# exactly as ArcGISClient._flatten_feature delivers it: attributes dict, point
# geometry lifted to latitude/longitude, epoch-ms date fields re-encoded to
# ISO 8601 UTC strings.
CB_DEED_ROW = {
    "OBJECTID": 128,
    "PARCELID": "010-054436",
    "SALEPRICE": 360000,
    "Sale_Price": 360000,
    "OWNERNME1": "REESE JAMES M",
    "OWN1": "REESE JAMES M",
    "OWN2": "& REESE MICHELLE",
    "Instrument_Number": None,
    "Transfer_Date": None,
    "SITEADDRESS": "348 W FIRST AVE",
    "ZIPCD": "43201",
    "MUNINAME": None,
    "NHBDNAME": None,
    "SALEDATE": "2025-07-16T05:00:00+00:00",
    "latitude": 39.980748333568215,
    "longitude": -83.01376102795739,
}


class TestColumbusDeedParsing:
    """Parse a Franklin County Auditor sales point against the shared
    DeedsACRISProducer. Registration test above pins the same field map, so
    the two cannot drift. Production passes city_id="columbus", forcing the
    columbus branch (uppercase PARCELID + OWN1/OWNERNME1)."""

    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            yield DeedsACRISProducer()

    def test_live_newest_row_parses_dual_schema(self, deeds):
        ev = deeds.parse_socrata_row(dict(CB_DEED_ROW), city_id="columbus")
        assert ev is not None
        assert ev.city_id == "columbus"
        # doc_id resolves to PARCELID because Instrument_Number is null.
        assert ev.doc_id == "010-054436"
        assert ev.bbl == "010-054436"
        assert ev.document_amount == 360000.0
        assert ev.party1_grantor == "REESE JAMES M"
        assert ev.party2_grantee == "REESE JAMES M"
        assert ev.recorded_date is not None
        assert (ev.recorded_date.year, ev.recorded_date.month, ev.recorded_date.day) == (
            2025,
            7,
            16,
        )
        assert ev.latitude == pytest.approx(39.980748333568215)
        assert ev.longitude == pytest.approx(-83.01376102795739)
        assert ev.h3_res7 is not None

    def test_disambiguates_old_vs_new_price_column(self, deeds):
        # Both price columns present -> the mapped "new" side (Sale_Price)
        # wins. On the 25 rows where SALEPRICE is null but Sale_Price is set,
        # the row still prices correctly.
        row = dict(CB_DEED_ROW)
        row["SALEPRICE"] = None
        ev = deeds.parse_socrata_row(row, city_id="columbus")
        assert ev is not None
        assert ev.document_amount == 360000.0

    def test_autodetects_columbus_without_city_id(self, deeds):
        ev = deeds.parse_socrata_row(dict(CB_DEED_ROW))
        assert ev is not None
        assert ev.city_id == "columbus"
        assert ev.doc_id == "010-054436"

    def test_coordinate_fallback_is_null_geometry_safe(self, deeds):
        # The layer is point-geocoded so every row hase coords, but the parser
        # must tolerate a null-lat/lng row (deeds-precedent) rather than crash.
        row = dict(CB_DEED_ROW)
        row["latitude"] = None
        row["longitude"] = None
        ev = deeds.parse_socrata_row(row, city_id="columbus")
        assert ev is not None
        assert ev.doc_id == "010-054436"
        assert ev.h3_res7 is None
