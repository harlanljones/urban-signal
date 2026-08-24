"""Contract tests for Columbus, OH (ArcGIS building permits)."""

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

# Recommended DatasetSpec.extra["field_map"] for HJ-118. Every entry spells a
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


def test_columbus_registers_arcgis_permits_only():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.COLUMBUS
    assert normalize_city("columbus") is city
    assert normalize_city("columbus_oh") is city
    assert REGISTRY[city].job_suffix == "cmoh"
    assert set(REGISTRY[city].datasets) == {FeedType.PERMITS}

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
    assert permits.extra["expected_cadence_days"] == 7
    assert permits.extra["oid_field"] == "OBJECTID"
    assert permits.extra["max_record_count"] == 2000
    assert permits.extra["field_map"] == COLUMBUS_FIELD_MAP

    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.COMPLAINTS_311)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.DEEDS)


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
