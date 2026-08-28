from unittest.mock import MagicMock

from src.producers.nfip_producer import NfipProducer
from src.spatial.geography_crosswalk import GeographyPoint


def test_parse_claim_uses_census_tract_centroid_not_privacy_truncated_point():
    crosswalk = MagicMock()
    crosswalk.tract_point.return_value = GeographyPoint(
        "36061000100", "tract", "tract", 40.7128, -74.0060
    )
    crosswalk.city_for_point.return_value = "nyc"
    producer = NfipProducer(client=MagicMock(), crosswalk=crosswalk, indexer=MagicMock())
    producer.indexer.get_multi_res_hierarchy.return_value = {
        "h3_res7": "r7", "h3_res8": "r8", "h3_res9": "r9"
    }
    event, reason = producer.parse_claim({
        "id": 42,
        "dateOfLoss": "2024-01-02T00:00:00.000Z",
        "amountPaidOnBuildingClaim": "1200.50",
        "amountPaidOnContentsClaim": 10,
        "buildingDamageAmount": "1500",
        "floodEvent": "Hurricane Test",
        "ratedFloodZone": "AE",
        "censusGeoid": "360610001001",
        "reportedZipCode": "10001",
        "state": "NY",
        "occupancyType": 1,
        "waterDepth": "2.5",
        "latitude": 0.1,
        "longitude": -0.1,
    })
    assert reason is None
    assert event.claim_id == "42"
    assert event.city_id == "nyc"
    assert event.latitude == 40.7128 and event.longitude == -74.006
    assert event.geometry_source == "tract_centroid"
    assert event.amount_paid_building == 1200.5
    assert event.h3_res9 == "r9"


def test_parse_claim_routes_rows_without_registered_geometry_to_dlq_reason():
    crosswalk = MagicMock()
    crosswalk.tract_point.return_value = None
    crosswalk.zip_point.return_value = None
    producer = NfipProducer(client=MagicMock(), crosswalk=crosswalk, indexer=MagicMock())
    event, reason = producer.parse_claim({"id": 7, "dateOfLoss": "2024-01-02"})
    assert event is None
    assert "geometry" in reason


def test_run_stream_filters_from_watermark_and_emits_valid_claims():
    client = MagicMock()
    client.paginate.return_value = iter([[{"id": 1, "dateOfLoss": "2024-01-02"}]])
    crosswalk = MagicMock()
    crosswalk.tract_point.return_value = GeographyPoint("1", "tract", "x", 40.7, -74.0)
    crosswalk.city_for_point.return_value = "nyc"
    indexer = MagicMock()
    indexer.get_multi_res_hierarchy.return_value = {"h3_res7": "7", "h3_res8": "8", "h3_res9": "9"}
    producer = NfipProducer(client=client, crosswalk=crosswalk, indexer=indexer)
    producer.producer = MagicMock()
    assert producer.run_stream(since="2024-01-01", limit=10) == 1
    kwargs = client.paginate.call_args.kwargs
    assert "dateOfLoss ge '2024-01-01'" == kwargs["where_clause"]
    producer.producer.produce.assert_called_once()
