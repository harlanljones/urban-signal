"""Unit tests for the US-404 MTA GTFS-RT service-alerts client.

Network-free: a FeedMessage protobuf is built with the same dynamically
constructed descriptor and round-tripped through ``decode``, so the tests pin
the wire contract without a dependency on gtfs-realtime-bindings or the MTA
endpoint.
"""

import pytest

from src.producers.mta_gtfs_rt_client import (
    EFFECT_SEVERITY,
    MAX_SEVERITY,
    MtaGtfsRtClient,
    _gtfs_rt_descriptor,
)


def build_feed(entities):
    """Serialize a FeedMessage from a list of entity kwargs via the real descriptor."""
    FeedMessage, *_ = _gtfs_rt_descriptor()
    fm = FeedMessage()
    fm.header.gtfs_realtime_version = "2.0"
    for kw in entities:
        ent = fm.entity.add()
        ent.id = kw["id"]
        if kw.get("is_deleted"):
            ent.is_deleted = True
            continue
        alert = ent.alert
        header = kw.get("header_text")
        if header:
            alert.header_text.translation.add(text=header, language="en")
        alert.effect = kw["effect"]
        for ie in kw.get("informed_entity", []):
            sel = alert.informed_entity.add()
            if ie.get("stop_id"):
                sel.stop_id = ie["stop_id"]
            if ie.get("route_id"):
                sel.route_id = ie["route_id"]
            if ie.get("route_type") is not None:
                sel.route_type = ie["route_type"]
        for ap in kw.get("active_period", []):
            alert.active_period.add(start=ap[0], end=ap[1])
    return fm.SerializeToString()


class TestDecode:
    def test_round_trip_of_one_alert(self):
        payload = build_feed(
            [
                {
                    "id": "A1",
                    "header_text": "TRAIN DELAYED",
                    "effect": 3,
                    "informed_entity": [{"stop_id": "F14", "route_id": "A"}],
                    "active_period": [(1700000000, 1700003600)],
                }
            ]
        )
        alerts = MtaGtfsRtClient().decode(payload)
        assert len(alerts) == 1
        a = alerts[0]
        assert a["id"] == "A1"
        assert a["header_text"] == "TRAIN DELAYED"
        assert a["effect"] == 3
        assert a["informed_entity"] == [{"agency_id": "", "route_id": "A", "route_type": None, "stop_id": "F14"}]
        assert a["active_period"] == [{"start": 1700000000, "end": 1700003600}]

    def test_deleted_entities_are_skipped(self):
        payload = build_feed([{"id": "gone", "is_deleted": True}])
        assert MtaGtfsRtClient().decode(payload) == []

    def test_empty_feed_decodes_to_no_alerts(self):
        payload = build_feed([])
        assert MtaGtfsRtClient().decode(payload) == []


class TestClassification:
    def test_severity_weights_follow_the_ticket(self):
        assert EFFECT_SEVERITY[1] == 5   # NO_SERVICE      -> full
        assert EFFECT_SEVERITY[3] == 2   # SIGNIFICANT_DELAYS -> delay
        assert EFFECT_SEVERITY[2] == 3   # REDUCED_SERVICE -> partial
        assert EFFECT_SEVERITY[5] == 1   # MODIFIED_SERVICE -> planned
        assert MAX_SEVERITY == 5

    def test_per_station_max_severity(self):
        client = MtaGtfsRtClient()
        payload = build_feed(
            [
                {"id": "A1", "effect": 3, "informed_entity": [{"stop_id": "F14"}]},
                {"id": "A2", "effect": 1, "informed_entity": [{"stop_id": "F14"}, {"stop_id": "125"}]},
                {"id": "A3", "effect": 5, "informed_entity": [{"stop_id": "G08"}]},
            ]
        )
        alerts = client.decode(payload)
        stations = client.classify_alerts(alerts)
        # F14 hit by delay (2) and full (5) -> max 5
        assert stations["F14"]["max_severity"] == 5
        assert stations["125"]["max_severity"] == 5
        assert stations["G08"]["max_severity"] == 1
        assert len(stations["F14"]["alert_ids"]) == 2

    def test_station_reliability(self):
        stations = {
            "a": {"max_severity": 0},
            "b": {"max_severity": 5},
            "c": {"max_severity": 1},
        }
        rel = MtaGtfsRtClient.station_reliability(stations)
        assert rel["a"] == pytest.approx(1.0)
        assert rel["b"] == pytest.approx(0.0)
        assert rel["c"] == pytest.approx(0.8)

    def test_feed_reliability_index(self):
        stations = {"a": {"max_severity": 0}, "b": {"max_severity": 5}, "c": {"max_severity": 1}}
        assert MtaGtfsRtClient.feed_reliability_index(stations) == pytest.approx(2 / 3)
        assert MtaGtfsRtClient.feed_reliability_index({}) == 1.0
