"""Contract tests for the spatial enrichment worker's geocoder fallback (ADR 0004)."""

from unittest.mock import MagicMock, patch

import pytest

from src.consumers.spatial_enrichment_worker import SpatialEnrichmentWorker
from src.spatial.geocoder import GeoPoint


@pytest.fixture
def worker():
    with (
        patch("src.consumers.spatial_enrichment_worker.BaseKafkaConsumer"),
        patch("src.consumers.spatial_enrichment_worker.SpatialFeaturePipeline"),
    ):
        geocoder = MagicMock()
        geocoder.geocode.return_value = GeoPoint(36.92, -76.23, 0.95, "nominatim:way")
        return SpatialEnrichmentWorker(geocoder=geocoder)


def test_native_coordinates_stamped_and_enriched(worker):
    record = {"latitude": 36.95, "longitude": -76.30, "job_id": "J1"}
    worker.process_record(record, "permits", "k1")
    assert record["coord_source"] == "native"
    assert record["h3_res9"]


def test_address_only_record_geocodes_and_carries_provenance(worker):
    record = {
        "incident_id": "SR-1",
        "incident_address": "8020 Meadow Creek Road, Norfolk, VA",
    }
    worker.geocoder.geocode.assert_not_called()
    worker.process_record(record, "311", "k2")
    worker.geocoder.geocode.assert_called_once_with("8020 Meadow Creek Road, Norfolk, VA")
    assert record["latitude"] == 36.92
    assert record["longitude"] == -76.23
    assert record["coord_source"] == "nominatim:way"
    assert record["h3_res7"] and record["h3_res8"] and record["h3_res9"]


def test_below_floor_geocode_keeps_record_skipped(worker):
    worker.geocoder.geocode = MagicMock(return_value=None)  # miss or below floor
    record = {"incident_id": "SR-2", "address": "999 Nowhere St, Norfolk, VA"}
    worker.process_record(record, "311", "k3")
    assert "latitude" not in record
    assert "coord_source" not in record
    assert "h3_res9" not in record


def test_no_usable_address_still_skips_without_touching_geocoder(worker):
    record = {"incident_id": "SR-3", "location": "RIVER"}  # too short to trust
    worker.process_record(record, "311", "k4")
    worker.geocoder.geocode.assert_not_called()
    assert "h3_res9" not in record


def test_worker_without_geocoder_preserves_legacy_behavior():
    with (
        patch("src.consumers.spatial_enrichment_worker.BaseKafkaConsumer"),
        patch("src.consumers.spatial_enrichment_worker.SpatialFeaturePipeline"),
    ):
        legacy = SpatialEnrichmentWorker()
    record = {"incident_id": "SR-4", "address": "8020 Meadow Creek Road"}
    legacy.process_record(record, "311", "k5")
    assert "latitude" not in record and "h3_res9" not in record
