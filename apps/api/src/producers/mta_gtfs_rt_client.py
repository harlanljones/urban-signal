"""MtaGtfsRtClient — thin protobuf poll of MTA NYC subway service alerts (US-404).

Polls the MTA GTFS-RT service alerts feed (keyless, protobuf binary), decodes
using the already-installed ``protobuf`` runtime with a dynamically constructed
descriptor (no ``gtfs-realtime-bindings`` dependency), and computes per-station
service reliability and alert severity for downstream H3 aggregation.

Alert severity weights (from the ticket):

    planned=1, delay=2, partial=3, full=5

The ``feed_reliability_index`` is the fraction of stations with no active
disruption (weighted severity ≤ 1).  ``station_reliability`` maps each
affected station to a float 0.0–1.0.
"""

from __future__ import annotations

from typing import Any

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

# ------------------------------------------------------------------ #
# GTFS-RT protobuf descriptor (subset for alerts)                    #
# Built once, cached.  Only the message types the MTA feed uses:     #
# FeedMessage → FeedEntity → Alert → TimeRange, EntitySelector,      #
# TranslatedString.                                                   #
# ------------------------------------------------------------------ #

_GTFS_RT_DESCRIPTOR: Any = None


def _gtfs_rt_descriptor() -> tuple:
    """Build and cache the GTFS-RT descriptor pool + message classes.

    Returns (FeedMessage, FeedEntity, Alert, TimeRange, EntitySelector,
    TranslatedString, Translation).
    """
    global _GTFS_RT_DESCRIPTOR
    if _GTFS_RT_DESCRIPTOR is not None:
        return _GTFS_RT_DESCRIPTOR

    fdp = descriptor_pb2.FileDescriptorProto()
    fdp.name = "gtfs_realtime.proto"
    fdp.package = "transit_realtime"
    fdp.syntax = "proto2"

    T = descriptor_pb2.FieldDescriptorProto
    O, R, Q = T.LABEL_OPTIONAL, T.LABEL_REPEATED, T.LABEL_REQUIRED

    def add_msg(name):
        return fdp.message_type.add(name=name)

    def add_field(msg, name, number, ftype, label, type_name=None):
        f = msg.field.add()
        f.name = name
        f.number = number
        f.type = ftype
        f.label = label
        if type_name:
            f.type_name = type_name
        return f

    tr = add_msg("TimeRange")
    add_field(tr, "start", 1, T.TYPE_UINT64, O)
    add_field(tr, "end", 2, T.TYPE_UINT64, O)

    trans = add_msg("Translation")
    add_field(trans, "text", 1, T.TYPE_STRING, Q)
    add_field(trans, "language", 2, T.TYPE_STRING, O)

    ts = add_msg("TranslatedString")
    add_field(ts, "translation", 1, T.TYPE_MESSAGE, R, ".transit_realtime.Translation")

    es = add_msg("EntitySelector")
    add_field(es, "agency_id", 1, T.TYPE_STRING, O)
    add_field(es, "route_id", 2, T.TYPE_STRING, O)
    add_field(es, "route_type", 3, T.TYPE_INT32, O)
    add_field(es, "stop_id", 5, T.TYPE_STRING, O)

    alert = add_msg("Alert")
    add_field(alert, "active_period", 1, T.TYPE_MESSAGE, R, ".transit_realtime.TimeRange")
    add_field(alert, "informed_entity", 5, T.TYPE_MESSAGE, R, ".transit_realtime.EntitySelector")
    add_field(alert, "header_text", 10, T.TYPE_MESSAGE, O, ".transit_realtime.TranslatedString")
    add_field(alert, "description_text", 11, T.TYPE_MESSAGE, O, ".transit_realtime.TranslatedString")
    add_field(alert, "cause", 7, T.TYPE_UINT64, O)
    add_field(alert, "effect", 8, T.TYPE_UINT64, O)

    fe = add_msg("FeedEntity")
    add_field(fe, "id", 1, T.TYPE_STRING, Q)
    add_field(fe, "is_deleted", 2, T.TYPE_BOOL, O)
    add_field(fe, "alert", 5, T.TYPE_MESSAGE, O, ".transit_realtime.Alert")

    fh = add_msg("FeedHeader")
    add_field(fh, "gtfs_realtime_version", 1, T.TYPE_STRING, Q)

    fm = add_msg("FeedMessage")
    add_field(fm, "header", 1, T.TYPE_MESSAGE, Q, ".transit_realtime.FeedHeader")
    add_field(fm, "entity", 2, T.TYPE_MESSAGE, R, ".transit_realtime.FeedEntity")

    pool = descriptor_pool.DescriptorPool()
    pool.Add(fdp)
    classes = {
        m.name: message_factory.GetMessageClass(
            pool.FindMessageTypeByName("transit_realtime." + m.name)
        )
        for m in fdp.message_type
    }

    _GTFS_RT_DESCRIPTOR = (
        classes["FeedMessage"],
        classes["FeedEntity"],
        classes["Alert"],
        classes["TimeRange"],
        classes["EntitySelector"],
        classes["TranslatedString"],
        classes["Translation"],
    )
    return _GTFS_RT_DESCRIPTOR


# ------------------------------------------------------------------ #
# GTFS-RT effect codes → severity weight                              #
# ------------------------------------------------------------------ #

# GTFS-RT Alert.effect enum values used by MTA:
#   1 = NO_SERVICE        → full = 5
#   2 = REDUCED_SERVICE   → partial = 3
#   3 = SIGNIFICANT_DELAYS → delay = 2
#   4 = ADDITIONAL_SERVICE → planned = 1
#   5 = MODIFIED_SERVICE   → planned = 1
#   6 = OTHER_EFFECT       → planned = 1
#   7 = UNKNOWN_EFFECT     → planned = 1
#   8 = STOP_MOVED         → planned = 1
#   9 = NO_EFFECT          → planned = 1
EFFECT_SEVERITY: dict[int, int] = {
    1: 5,  # NO_SERVICE
    2: 3,  # REDUCED_SERVICE
    3: 2,  # SIGNIFICANT_DELAYS
    4: 1,  # ADDITIONAL_SERVICE
    5: 1,  # MODIFIED_SERVICE
    6: 1,  # OTHER_EFFECT
    7: 1,  # UNKNOWN_EFFECT
    8: 1,  # STOP_MOVED
    9: 1,  # NO_EFFECT
}

MAX_SEVERITY = 5


class MtaGtfsRtClient:
    """Thin client for MTA NYC subway GTFS-RT service alerts.

    Keyless, station-level.  Polls the MTA protobuf feed, decodes, and
    classifies alerts by severity per station.
    """

    FEED_URL = (
        "https://api-endpoint.mta.info/Dataservice"
        "/mtagtsfeeds/camsys%2Fsubway-alerts"
    )

    def __init__(
        self,
        feed_url: str | None = None,
        timeout_seconds: float = 30.0,
    ):
        self.feed_url = feed_url or self.FEED_URL
        self.timeout = timeout_seconds

    # ------------------------------------------------------------------ #
    # HTTP                                                                 #
    # ------------------------------------------------------------------ #

    def fetch(self) -> bytes:
        """GET the MTA GTFS-RT feed, return raw protobuf bytes."""
        import httpx

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as cl:
            resp = cl.get(self.feed_url)
            resp.raise_for_status()
            return resp.content

    # ------------------------------------------------------------------ #
    # protobuf decode                                                     #
    # ------------------------------------------------------------------ #

    def decode(self, payload: bytes) -> list[dict[str, Any]]:
        """Decode a GTFS-RT FeedMessage protobuf into alert dicts.

        Each alert dict::
            {id, header_text, description_text, effect, cause,
             active_period: [{start, end}],
             informed_entity: [{agency_id, route_id, route_type, stop_id}]}
        """
        FeedMessage, *_ = _gtfs_rt_descriptor()
        msg = FeedMessage()
        msg.ParseFromString(payload)

        alerts: list[dict[str, Any]] = []
        for entity in msg.entity:
            if entity.is_deleted or not entity.HasField("alert"):
                continue
            alert = entity.alert
            d: dict[str, Any] = {
                "id": entity.id,
                "header_text": _ts_text(alert.header_text) if alert.HasField("header_text") else "",
                "description_text": _ts_text(alert.description_text) if alert.HasField("description_text") else "",
                "effect": int(alert.effect) if alert.HasField("effect") else 0,
                "cause": int(alert.cause) if alert.HasField("cause") else 0,
                "active_period": [
                    {"start": p.start, "end": p.end}
                    for p in alert.active_period
                ],
                "informed_entity": [
                    {
                        "agency_id": e.agency_id,
                        "route_id": e.route_id,
                        "route_type": int(e.route_type) if e.HasField("route_type") else None,
                        "stop_id": e.stop_id,
                    }
                    for e in alert.informed_entity
                ],
            }
            alerts.append(d)
        return alerts

    # ------------------------------------------------------------------ #
    # classification                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def classify_alerts(
        alerts: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Per-station alert summary.

        Returns ``{station_id: {max_severity, effects, alert_ids}}``.
        """
        stations: dict[str, dict[str, Any]] = {}
        for alert in alerts:
            weight = EFFECT_SEVERITY.get(alert["effect"], 1)
            for entity in alert["informed_entity"]:
                sid = entity.get("stop_id")
                if not sid:
                    continue
                entry = stations.setdefault(
                    sid,
                    {"max_severity": 0, "effects": set(), "alert_ids": set()},
                )
                entry["max_severity"] = max(entry["max_severity"], weight)
                entry["effects"].add(alert["effect"])
                entry["alert_ids"].add(alert["id"])
        return stations

    @staticmethod
    def station_reliability(
        stations: dict[str, dict[str, Any]],
    ) -> dict[str, float]:
        """Per-station reliability index 0.0–1.0.

        1.0 = no active disruption, 0.0 = full service outage.
        """
        return {
            sid: 1.0 - (entry["max_severity"] / MAX_SEVERITY)
            for sid, entry in stations.items()
        }

    @staticmethod
    def feed_reliability_index(
        stations: dict[str, dict[str, Any]],
    ) -> float:
        """Fraction of affected stations with no or minimal disruption.

        Stations with ``max_severity ≤ 1`` (planned work only) count as
        reliable.
        """
        if not stations:
            return 1.0
        reliable = sum(1 for e in stations.values() if e["max_severity"] <= 1)
        return reliable / len(stations)


def _ts_text(ts) -> str:
    """Extract the first translation text from a TranslatedString."""
    if ts is None:
        return ""
    for t in ts.translation:
        if t.text:
            return t.text
    return ""