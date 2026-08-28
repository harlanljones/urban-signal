from unittest.mock import MagicMock

from src.producers.ev_charging_producer import EvChargingProducer


def test_build_event_uses_open_date_and_port_counts():
    indexer = MagicMock()
    indexer.get_multi_res_hierarchy.return_value = {"h3_res7": "7", "h3_res8": "8", "h3_res9": "9"}
    producer = EvChargingProducer(client=MagicMock(), indexer=indexer)
    event = producer.build_event({
        "id": 17, "station_name": "Test Charge", "latitude": 40.7, "longitude": -74,
        "open_date": "2024-02-03", "status_code": "E", "access_code": "public",
        "ev_level2_evse_num": "4", "ev_dc_fast_num": 2, "street_address": "1 Main St",
        "zip": "10001", "state": "NY",
    })
    assert event.asset_id == "17"
    assert event.event_date.isoformat().startswith("2024-02-03")
    assert event.unit_count == 6 and event.fast_unit_count == 2
    assert event.date_is_detection is False


def test_build_event_marks_missing_open_date_as_detection():
    crosswalk = MagicMock()
    crosswalk.city_for_point.return_value = "nyc"
    producer = EvChargingProducer(client=MagicMock(), indexer=MagicMock(), crosswalk=crosswalk)
    producer.indexer.get_multi_res_hierarchy.return_value = {"h3_res7": "7", "h3_res8": "8", "h3_res9": "9"}
    event = producer.build_event({"id": 1, "latitude": 40, "longitude": -74, "last_updated": "2024-02-03"})
    assert event.date_is_detection is True
