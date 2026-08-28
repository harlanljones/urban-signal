"""Contract tests for Pierce County, WA (ArcGIS permits/application layer)."""

from unittest.mock import patch

import pytest

from src.spatial.cities.pierce import (
    PIERCE_DIVISION_BBOXES,
    PIERCE_DIVISIONS,
    PIERCE_METRO_BBOX,
    PIERCE_SUBMARKETS,
    is_in_pierce_metro,
)
from src.spatial.city_registry import CityId, FeedType

# Recommended DatasetSpec.field_map for US-80. Every entry spells a
# camelCase column the shared producer fallback chains cannot reach;
# latitude/longitude need no entry because ArcGISClient lifts point geometry
# onto those exact keys (outSR=4326) before parsing. The two-date issuance
# chain keeps issuance_date populated on applications still under review
# (issuedDate null, ~13% of the Building/Land-Use set).
PIERCE_FIELD_MAP = {
    "job_id": ["applicationNumber"],
    "issuance_date": ["issuedDate", "applicationDate"],
    "filing_date": ["applicationDate"],
    "cost": ["buildingValuation", "projectValue"],
    "address_street": ["siteAddress"],
    "status": ["applicationStatus"],
    "job_type": ["applicationType", "workType", "buildingType"],
    "proposed_units": ["dwellingUnits"],
    "proposed_stories": ["stories"],
}

PIERCE_FEED_WHERE = (
    "applicationDept LIKE '%BUILDING%' OR "
    "applicationDept LIKE '%LAND USE%'"
)


def test_pierce_geometry_is_self_consistent():
    assert is_in_pierce_metro(47.2529, -122.4443)  # Tacoma center
    assert is_in_pierce_metro(47.16823073695617, -122.41028390952044)  # observed live-row
    assert is_in_pierce_metro(47.28801488006937, -122.59571643607437)  # observed live-row
    assert not is_in_pierce_metro(47.6062, -122.3321)  # Seattle, north of the county
    assert not is_in_pierce_metro(None, None)
    for name, bbox in PIERCE_DIVISION_BBOXES.items():
        assert bbox["min_lat"] >= PIERCE_METRO_BBOX["min_lat"], name
        assert bbox["max_lat"] <= PIERCE_METRO_BBOX["max_lat"], name
        assert bbox["min_lng"] >= PIERCE_METRO_BBOX["min_lng"], name
        assert bbox["max_lng"] <= PIERCE_METRO_BBOX["max_lng"], name
    claimed = [name for division in PIERCE_DIVISIONS.values() for name in division.submarkets]
    assert sorted(claimed) == sorted(PIERCE_SUBMARKETS)
    assert {meta.city_id for meta in PIERCE_SUBMARKETS.values()} == {"pierce"}


def test_pierce_registers_arcgis_permits_and_snap_sla():
    from src.spatial.city_registry import REGISTRY, get_dataset, normalize_city

    city = CityId.PIERCE
    assert normalize_city("pierce") is city
    assert normalize_city("pierce_county") is city
    assert normalize_city("tacoma") is city
    assert REGISTRY[city].job_suffix == "pco"
    assert set(REGISTRY[city].datasets) == {FeedType.PERMITS, FeedType.SLA}

    permits = REGISTRY[city].datasets[FeedType.PERMITS]
    assert permits.platform == "arcgis"
    # Watermark rides the issuance column so an accepted application that
    # later issues is re-ingested with its real issuance date.
    assert permits.watermark_col == "issuedDate"
    assert permits.interval_seconds == 300.0
    assert permits.producer_key == "permits"
    assert permits.expected_cadence_days == 7
    assert permits.oid_field == "OBJECTID"
    assert permits.max_record_count == 2000
    assert permits.where == PIERCE_FEED_WHERE
    assert permits.field_map == PIERCE_FIELD_MAP

    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.COMPLAINTS_311)
    with pytest.raises(KeyError, match="no.*feed"):
        get_dataset(city, FeedType.DEEDS)


PC_CONSTRUCTION_ROW = {
    # Live newest Building row via REST on 2026-08-24
    # (orderByFields=applicationDate DESC, where applicationDept LIKE
    # '%BUILDING%'), flattened exactly as ArcGISClient._flatten_feature
    # delivers it: attributes dict, point geometry lifted to
    # latitude/longitude, epoch-ms date fields re-encoded to ISO 8601 UTC.
    "OBJECTID": 681301,
    "applicationNumber": 1074869,
    "applicationType": "Construction Residential",
    "applicationStatus": "Accepted",
    "applicationDept": "*BUILDING*",
    "parcelNumber": "7745002082",
    "siteAddress": "9713 9715 14TH AVE E",
    "applicationDate": "2026-08-19T16:49:51+00:00",
    "issuedDate": None,
    "buildingValuation": 466960.16,
    "projectValue": None,
    "sqFtTotal": 3192,
    "dwellingUnits": "2",
    "stories": "2",
    "workType": "New Structure",
    "buildingType": "House/plex",
    "projectName": "Southeast Tacoma, Lots 8 & 9, Blk 53",
    "longitude": -122.41028390952044,
    "latitude": 47.16823073695617,
}

PC_ISSUED_ROW = {
    # Live newest Issued-status Building row via REST on 2026-08-24.
    # Mechanical trade ticket: issuedDate == applicationDate, no valuation.
    "OBJECTID": 681522,
    "applicationNumber": 1075318,
    "applicationType": "Mechanical",
    "applicationStatus": "Issued",
    "applicationDept": "*BUILDING*",
    "parcelNumber": "0221198025",
    "siteAddress": "4212 33RD STCT NW",
    "applicationDate": "2026-08-19T14:44:30+00:00",
    "issuedDate": "2026-08-19T14:44:30+00:00",
    "buildingValuation": None,
    "projectValue": None,
    "sqFtTotal": None,
    "dwellingUnits": None,
    "stories": None,
    "workType": None,
    "buildingType": None,
    "projectName": "Online Permit for:MECH",
    "longitude": -122.59571643607437,
    "latitude": 47.28801488006937,
}


class TestPiercePermitParsing:
    """Parse pins against the shared DOBPermitsProducer.

    ``resolve_field_map`` is patched with the exact map recommended for the
    registration because the registry entry itself lands with the spine; the
    registration test above asserts the spec carries this same literal, so the
    two cannot drift once US-80 is wired.
    """

    @pytest.fixture
    def producer(self):
        with (
            patch("src.producers.dob_permits_producer.BaseKafkaProducer"),
            patch(
                "src.producers.field_maps.resolve_field_map",
                return_value=PIERCE_FIELD_MAP,
            ),
        ):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            yield DOBPermitsProducer()

    def test_live_newest_row_parses_camelcase_schema(self, producer):
        event = producer.parse_socrata_row(dict(PC_CONSTRUCTION_ROW), city_id="pierce")
        assert event is not None
        assert event.city_id == "pierce"
        assert event.job_id == "1074869"  # applicationNumber, never str(OBJECTID)
        assert event.status == "Accepted"
        assert event.address_street == "9713 9715 14TH AVE E"
        assert event.estimated_cost == pytest.approx(466960.16)
        assert event.proposed_dwelling_units == 2
        # issuedDate is null on an accepted application; the two-date chain
        # falls back to applicationDate so the event still carries a date.
        assert event.issuance_date is not None
        assert (event.issuance_date.year, event.issuance_date.month, event.issuance_date.day) == (
            2026,
            8,
            19,
        )
        assert event.latitude == pytest.approx(47.16823073695617)
        assert event.longitude == pytest.approx(-122.41028390952044)

    def test_issued_row_uses_real_issuance_date(self, producer):
        event = producer.parse_socrata_row(dict(PC_ISSUED_ROW), city_id="pierce")
        assert event is not None
        assert event.job_id == "1075318"
        assert event.status == "Issued"
        assert event.estimated_cost == 0.0  # mechanical ticket, no valuation
        assert event.issuance_date is not None
        assert (event.issuance_date.year, event.issuance_date.month, event.issuance_date.day) == (
            2026,
            8,
            19,
        )

    def test_objectid_never_rescues_a_missing_application_number(self, producer):
        row = dict(PC_CONSTRUCTION_ROW)
        row.pop("applicationNumber")
        assert producer.parse_socrata_row(row, city_id="pierce") is None