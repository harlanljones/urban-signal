"""Per-city field maps for bike/pedestrian counter feeds (US-363 §2.8).

Two very different shapes hide behind "counter feed":

* **NYC ``ct66-47at``** — 15-minute directional counts, ``travelmode`` in
  {bike, pedestrian, scooter}, ``direction`` in {in, out}, ``counts``,
  ``status``. Re-probed 2026-08-28: **21,016,786 rows**, max ``timestamp``
  2026-08-27T05:00 (same-day freshness confirmed). The feed carries **no
  geometry** — ``sensor_id`` joins the sensor registry ``6up2-gnw8``
  (``lat``/``lon``, ``firstdata``/``lastdata``, ``travelmodes``,
  ``directional``; **67** sensors live, not the 41 the sweep doc cites), which
  the spec declares as a companion endpoint.
* **Seattle Fremont ``65db-xm6k``** — hourly, wide: one row per hour with
  ``fremont_bridge`` (total), ``fremont_bridge_nb``, ``fremont_bridge_sb``.
  121,211 rows, max ``date`` 2026-07-31T23:00 (~4-week lag, as documented).
  There is no sensor id and no geometry because there is exactly one sensor:
  the Fremont Bridge counter. Its coordinate is therefore a **constant** in
  this module, not a lookup — recorded with its provenance so a future editor
  does not mistake it for a metro-centroid placeholder.

Twenty-one million 15-minute rows must never become twenty-one million Kafka
events for a feature the sweep describes as "flow intensity per hex". The
producer aggregates to one observation per (sensor, travel mode, day) before
producing; these maps describe the *row* shape it aggregates from.
"""

from typing import Dict, List

# NYC DOT automated counts (`ct66-47at`) — long/narrow, one row per
# (sensor, mode, direction, 15-minute bucket, FLOW).
#
# Two findings from the 2026-08-28 probe that the sweep doc does not mention
# and that change how a day is summed:
#
# 1. `status` is one of raw / modified / deleted (18,579,562 / 2,435,656 /
#    1,568 rows). `deleted` rows are retracted observations and are filtered
#    server-side by the spec's `where`, not summed.
# 2. **A sensor carries more than one flow per direction.** Every
#    sensor/mode/direction on 2026-08-26 had exactly 2 distinct `flowid`s, and
#    they are not copies of each other — sensor 100009425 (Prospect Park West)
#    reported NB 71 and 1,682 on the two northbound flows and SB 1,358 and 222
#    on the two southbound ones, each over a full 96-row day. They are
#    separate live series (parallel devices/lanes at one location), not a
#    stale duplicate of a live one, so the daily rollup sums every flow. The
#    resulting ~3.3k bikes/day for PPW is the plausible order of magnitude;
#    de-duplicating to one flow per direction would halve it.
NYC_COUNTS_FIELD_MAP: Dict[str, List[str]] = {
    "asset_id": ["sensor_id"],
    "period": ["timestamp"],
    "count": ["counts"],
    "travel_mode": ["travelmode"],
    "direction": ["direction"],
    "status": ["status"],
    "granularity": ["granularity"],
}

# NYC DOT counter registry (`6up2-gnw8`) — the geometry side of the join.
NYC_COUNTER_REGISTRY_FIELD_MAP: Dict[str, List[str]] = {
    "asset_id": ["id"],
    "asset_name": ["name"],
    "latitude": ["lat", "latitude"],
    "longitude": ["lon", "longitude"],
    "travel_modes": ["travelmodes"],
    "first_data": ["firstdata"],
    "last_data": ["lastdata"],
}

# Seattle Fremont Bridge (`65db-xm6k`) — wide/hourly. The undirected total
# column is read for corroboration only and never produced alongside nb+sb:
# emitting all three would count the hex's flow twice.
SEATTLE_FREMONT_FIELD_MAP: Dict[str, List[str]] = {
    "period": ["date"],
    "count_total": ["fremont_bridge"],
    "count_northbound": ["fremont_bridge_nb"],
    "count_southbound": ["fremont_bridge_sb"],
}

SEATTLE_FREMONT_DIRECTION_COLUMNS: Dict[str, str] = {
    "fremont_bridge_nb": "northbound",
    "fremont_bridge_sb": "southbound",
}

# One structure, one coordinate. The SDOT Fremont Bridge bicycle counter
# (inductive loops in the bridge deck), Seattle. This is a real fixed asset,
# not a placeholder: it resolves to Seattle's NORTH_KING division bbox
# (47.645..47.745, -122.425..-122.28), which the interlock containment check
# already exercises.
SEATTLE_FREMONT_SENSOR = {
    "asset_id": "fremont_bridge",
    "asset_name": "Fremont Bridge Bicycle Counter",
    "latitude": 47.6478,
    "longitude": -122.3497,
    "travel_mode": "bike",
}

# Travel modes present in the live NYC feed, counted 2026-08-28:
#   bike 19,522,684 | pedestrian 1,480,644 | scooter 13,458
# The sweep doc says the feed is "bike/ped"; it is bike/ped/scooter, and
# `pedestrian` is spelled out, not `ped`. Unknown modes pass through verbatim
# so a new mode is visible in the feature store rather than silently folded
# into "bike".
KNOWN_TRAVEL_MODES = frozenset({"bike", "ped", "pedestrian", "scooter"})

_MODE_ALIASES = {"pedestrian": "ped"}


def normalize_travel_mode(raw: "str | None") -> str:
    """Canonicalize a travel-mode string; unknown values pass through."""
    if not raw:
        return "unknown"
    value = str(raw).strip().lower()
    return _MODE_ALIASES.get(value, value)


def counter_metric_name(travel_mode: "str | None") -> str:
    """Metric name for a mode's daily flow, e.g. ``bike`` -> ``bike_flow``."""
    return f"{normalize_travel_mode(travel_mode)}_flow"
