"""Unit tests for the Gainesville leaf: spatial module + permits field map."""

from unittest.mock import patch

import pytest

from src.producers.field_maps import first_mapped
from src.spatial.cities.gainesville import FIELD_MAP as GAINESVILLE_PERMITS_FIELD_MAP
from src.spatial.cities.gainesville import (
    GAINESVILLE_DIVISION_BBOXES,
    GAINESVILLE_DIVISIONS,
    GAINESVILLE_METRO_BBOX,
    GAINESVILLE_SUBMARKETS,
    compose_permit_type,
    get_gainesville_dataset,
    is_in_gainesville_metro,
)
from src.spatial.city_registry import CityId, FeedType, get_dataset


class TestGainesvilleSpatial:
    def test_metro_contains_core_points(self):
        assert is_in_gainesville_metro(29.6516, -82.3248)  # downtown
        assert is_in_gainesville_metro(29.6530, -82.3380)  # midtown

    def test_metro_rejects_foreign(self):
        assert not is_in_gainesville_metro(27.9506, -82.4572)  # Tampa
        assert not is_in_gainesville_metro(None, None)

    def test_division_bboxes_nest_in_metro(self):
        for name, bbox in GAINESVILLE_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= GAINESVILLE_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= GAINESVILLE_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= GAINESVILLE_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= GAINESVILLE_METRO_BBOX["max_lng"], name

    def test_every_submarket_inside_its_division(self):
        for name, meta in GAINESVILLE_SUBMARKETS.items():
            bbox = GAINESVILLE_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_claimed_by_exactly_one_division(self):
        claimed = [s for d in GAINESVILLE_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(GAINESVILLE_SUBMARKETS)

    def test_submarkets_carry_city_id(self):
        assert {m.city_id for m in GAINESVILLE_SUBMARKETS.values()} == {"gainesville"}


class TestFeedRegistration:
    def test_permits_spec_reads_the_county_layer(self):
        spec = get_gainesville_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.endpoint.endswith("/BuildingPermitsCS/FeatureServer/0")
        assert spec.watermark_col == "IssueDate"
        assert spec.id_keys == ["Permit"]
        assert spec.producer_key == "permits"
        # The County loads permits days after they are issued, so each poll
        # re-reads its 90-day window, newest first.
        assert spec.ingestion_mode == "snapshot"
        assert spec.order_by == "IssueDate DESC, OBJECTID DESC"
        assert spec.field_map == GAINESVILLE_PERMITS_FIELD_MAP

    def test_leaf_spec_matches_the_registry(self):
        leaf = get_gainesville_dataset(FeedType.PERMITS)
        registered = get_dataset(CityId.GAINESVILLE, FeedType.PERMITS)
        for attr in (
            "endpoint", "platform", "watermark_col", "id_keys", "interval_seconds", "order_by", "select",
            "where", "field_map", "ingestion_mode", "oid_field", "batch_limit", "metro_clip",
        ):
            assert getattr(leaf, attr) == getattr(registered, attr), attr

    def test_select_leaves_out_people_and_free_text(self):
        columns = set(get_dataset(CityId.GAINESVILLE, FeedType.PERMITS).select.split(","))
        assert not columns & {
            "ApplicanName", "ApplicantCompanyName", "LicensedContractorName", "OwnerName",
            "WorkDescription", "CSpublicLink", "CSstaffLink",
        }

    def test_filter_keeps_building_work(self):
        where = get_dataset(CityId.GAINESVILLE, FeedType.PERMITS).where
        assert where.startswith("IssueDate >= CURRENT_DATE - INTERVAL '90' DAY AND IssueDate <= CURRENT_TIMESTAMP")
        for kind in ("Building Permit", "Mechanical Permit", "Electrical Permit", "Demolition Permit"):
            assert f"'{kind}'" in where
        for kind in ("Right-of-Way", "Irrigation Approval", "Tree Removal", "Construction Permit", "Temporary",
                     "Model Permit"):
            assert kind not in where

    def test_field_map_reads_live_columns(self):
        row = {
            "OBJECTID": 249228,
            "Permit": "B26-001677",
            "Permit_Type": "Building Permit",
            "Sub_Type": "New Construction",
            "Status": "Issued",
            "Parcel": "18914-001-000",
            "FULLADDR": "1 EXAMPLE RD",
            "IssueDate": "2026-10-01T00:00:00+00:00",
            "ApplicationDate": "2026-09-21T00:00:00+00:00",
        }
        assert first_mapped(row, GAINESVILLE_PERMITS_FIELD_MAP, "job_id") == "B26-001677"
        assert first_mapped(row, GAINESVILLE_PERMITS_FIELD_MAP, "issuance_date") == "2026-10-01T00:00:00+00:00"
        assert first_mapped(row, GAINESVILLE_PERMITS_FIELD_MAP, "filing_date") == "2026-09-21T00:00:00+00:00"
        assert first_mapped(row, GAINESVILLE_PERMITS_FIELD_MAP, "job_type") == "Building Permit"
        assert first_mapped(row, GAINESVILLE_PERMITS_FIELD_MAP, "status") == "Issued"
        assert first_mapped(row, GAINESVILLE_PERMITS_FIELD_MAP, "address_street") == "1 EXAMPLE RD"
        assert first_mapped(row, GAINESVILLE_PERMITS_FIELD_MAP, "bbl") == "18914-001-000"


@pytest.mark.parametrize(
    "permit_type,sub_type,expected",
    [
        ("Building Permit", "New Construction", "Building Permit: New Construction"),
        ("Building Permit", "Windows", "Building Permit: Windows"),
        # The County files a change of occupancy under its own type.
        ("Building Permit", "Renovation/Conversion", "Building Permit: Renovation"),
        # A trade's permit for a new building is the trade's.
        ("Mechanical Permit", "New Construction", None),
        ("Pool/Spa Permit", "New Construction", None),
        ("Building Permit", None, None),
    ],
)
def test_compose_permit_type(permit_type, sub_type, expected):
    assert compose_permit_type({"Permit_Type": permit_type, "Sub_Type": sub_type}) == expected


@pytest.fixture
def permits_producer():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        yield DOBPermitsProducer()


def _county_permit(permit_type: str, sub_type: str) -> dict:
    # A row as the ArcGIS client hands it over: dates in ISO form, the point
    # geometry lifted to latitude/longitude.
    return {
        "OBJECTID": 249228,
        "Permit": "B26-001677",
        "Permit_Type": permit_type,
        "Sub_Type": sub_type,
        "Status": "Issued",
        "Parcel": "06023-030-058",
        "FULLADDR": "202 NW 5TH ST",
        "IssueDate": "2026-10-01T00:00:00+00:00",
        "ApplicationDate": "2026-09-21T00:00:00+00:00",
        "latitude": 29.65495,
        "longitude": -82.33617,
    }


@patch(
    "src.producers.field_maps.resolve_field_map",
    lambda city, feed: GAINESVILLE_PERMITS_FIELD_MAP if (city == "gainesville" and feed == FeedType.PERMITS) else {},
)
@pytest.mark.parametrize(
    "permit_type,sub_type,job_type,normalized",
    [
        ("Building Permit", "New Construction", "NB", "NEW_CONSTRUCTION"),
        ("Building Permit", "Addition", "A2", "MAJOR_RENOVATION"),
        ("Building Permit", "Renovation/Conversion", "A2", "MINOR_ALTERATION"),
        ("Building Permit", "Windows", "OT", "MINOR_ALTERATION"),
        ("Electrical Permit", "New Construction", "A2", "MECHANICAL_ELECTRICAL_PLUMBING"),
        ("Mechanical Permit", "Alteration/Repair/Replace", "OT", "MECHANICAL_ELECTRICAL_PLUMBING"),
        ("Pool/Spa Permit", "New Construction", "OT", "MINOR_ALTERATION"),
        ("Demolition Permit", "Demolition", "DM", "DEMOLITION"),
        ("Sign Permit", "Sign Permit", "SG", "MINOR_ALTERATION"),
    ],
)
def test_county_permit_reads_its_type_and_point(permits_producer, permit_type, sub_type, job_type, normalized):
    with patch("src.spatial.geocoder.geocode_row_if_declared", return_value=(0.0, 0.0)) as geocode:
        event = permits_producer.parse_socrata_row(_county_permit(permit_type, sub_type), city_id="gainesville")
    assert event is not None
    assert event.city_id == "gainesville"
    assert event.job_id == "B26-001677"
    assert event.job_type == job_type
    assert event.normalized_permit_type == normalized
    assert event.status == "Issued"
    assert event.address_street == "202 NW 5TH ST"
    assert event.issuance_date is not None and event.issuance_date.date().isoformat() == "2026-10-01"
    assert event.latitude == pytest.approx(29.65495)
    assert event.longitude == pytest.approx(-82.33617)
    geocode.assert_not_called()
