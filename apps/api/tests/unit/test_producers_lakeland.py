"""Unit tests for the Lakeland registration (US-286) and its leaf wiring.

Imports the lakeland module directly for containment, and reads the spine
REGISTRY for the permits feed the scheduler actually polls.
"""

from datetime import UTC, datetime
from unittest.mock import patch

from src.spatial.cities.lakeland import (
    LAKELAND_DIVISION_BBOXES,
    LAKELAND_DIVISIONS,
    LAKELAND_METRO_BBOX,
    LAKELAND_SUBMARKETS,
    get_lakeland_dataset,
    is_in_lakeland_metro,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType


class TestLakelandRegistration:
    def test_center_inside_metro_bbox(self):
        # Downtown Lakeland near Munn Park
        assert is_in_lakeland_metro(28.0395, -81.9498)

    def test_is_in_lakeland_metro_rejects_missing_coordinates(self):
        assert is_in_lakeland_metro(None, None) is False

    def test_division_bboxes_nest_inside_metro_bbox(self):
        for name, bbox in LAKELAND_DIVISION_BBOXES.items():
            assert bbox["min_lat"] >= LAKELAND_METRO_BBOX["min_lat"], name
            assert bbox["max_lat"] <= LAKELAND_METRO_BBOX["max_lat"], name
            assert bbox["min_lng"] >= LAKELAND_METRO_BBOX["min_lng"], name
            assert bbox["max_lng"] <= LAKELAND_METRO_BBOX["max_lng"], name

    def test_every_submarket_sits_inside_its_own_division(self):
        for name, meta in LAKELAND_SUBMARKETS.items():
            bbox = LAKELAND_DIVISION_BBOXES[meta.borough]
            assert bbox["min_lat"] <= meta.lat <= bbox["max_lat"], name
            assert bbox["min_lng"] <= meta.lng <= bbox["max_lng"], name

    def test_every_submarket_is_claimed_by_exactly_one_division(self):
        claimed = [s for d in LAKELAND_DIVISIONS.values() for s in d.submarkets]
        assert sorted(claimed) == sorted(LAKELAND_SUBMARKETS)

    def test_submarkets_carry_the_lakeland_city_id(self):
        assert {m.city_id for m in LAKELAND_SUBMARKETS.values()} == {"lakeland"}


class TestFeedRegistration:
    """Lakeland registers a verified ArcGIS permits feed; SLA falls back to SNAP in the spine."""

    def test_permits_spec_minimal_shape(self):
        spec = get_lakeland_dataset(FeedType.PERMITS)
        assert spec.platform == "arcgis"
        assert spec.producer_key == "permits"
        # For ArcGIS feeds, oid_field must be declared
        assert spec.oid_field is not None
        assert spec.interval_seconds > 0


    def test_permits_read_the_hosted_ims_layer(self):
        """The on-premises iMS MapServer reset every connection in September
        2026, and its empty field map dead-lettered every row even when it
        answered: ``PERMIT_NO`` is not in the producer's default id chain."""
        spec = REGISTRY[CityId.LAKELAND].datasets[FeedType.PERMITS]
        assert spec.endpoint == (
            "https://services1.arcgis.com/mcbQY5xNGGGM1vBX/arcgis/rest/services/"
            "IMS_Projects_Permits/FeatureServer/6"
        )
        # ISSUED stops at 2025-06-25; APPROVED carries every issuance since.
        assert spec.watermark_col == "APPROVED"
        assert spec.order_by == "APPROVED DESC,OBJECTID ASC"
        # The layer also holds 1,916 planning "Project" rows.
        assert spec.where == "TYPE = 'Permit'"
        assert spec.field_map["job_id"] == ["PERMIT_NO"]
        assert spec.field_map["issuance_date"] == ["APPROVED", "ISSUED"]

    def test_leaf_mirror_matches_the_registry(self):
        spec = REGISTRY[CityId.LAKELAND].datasets[FeedType.PERMITS]
        leaf = get_lakeland_dataset(FeedType.PERMITS)
        assert leaf.endpoint == spec.endpoint
        assert leaf.watermark_col == spec.watermark_col
        assert leaf.field_map == spec.field_map

    def test_applicant_names_are_never_mapped(self):
        spec = REGISTRY[CityId.LAKELAND].datasets[FeedType.PERMITS]
        candidates = {c for cols in spec.field_map.values() for c in cols}
        assert not candidates & {"APPLICANT_NAME", "CREATED_USER", "LAST_EDITED_USER"}


# A live permit (2026-09-30, approved newest first). Dates as ArcGISClient
# normalizes them; the applicant's name is replaced.
_PERMIT_LADOGA_DR = {
    "OBJECTID": 8484546,
    "TYPE": "Permit",
    "PERMIT_NO": "BLD26-05749",
    "DESCRIPTION": "PP INSP - REROOF",
    "SITE_ADDR": "2450 LADOGA DR",
    "SITE_CITY": "LAKELAND",
    "SITE_STATE": "FL",
    "SITE_ZIP": "33805",
    "PERMITORPROJECTTYPE": "Roof",
    "APPLICANT_NAME": "APPLICANT NAME REDACTED",
    "APPLIED": "2026-09-29T12:12:53+00:00",
    "APPROVED": "2026-09-29T19:40:02+00:00",
    "ISSUED": None,
    "JOBVALUE": 14000,
    "longitude": -81.91549865158234,
    "latitude": 28.116803418380393,
}


def test_permit_parses_from_the_hosted_layer():
    with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
        from src.producers.dob_permits_producer import DOBPermitsProducer

        event = DOBPermitsProducer().parse_socrata_row(_PERMIT_LADOGA_DR, city_id="lakeland")
    assert event is not None
    assert event.job_id == "BLD26-05749"
    assert event.address_street == "2450 LADOGA DR"
    assert event.zipcode == "33805"
    assert event.estimated_cost == 14000
    assert event.filing_date == datetime(2026, 9, 29, 12, 12, 53, tzinfo=UTC)
    assert event.issuance_date == datetime(2026, 9, 29, 19, 40, 2, tzinfo=UTC)
    assert "APPLICANT NAME REDACTED" not in event.model_dump_json()
