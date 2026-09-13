"""Transit accessibility scoring — GTFS stop-to-H3 k-ring propagation (US-442).

Two-layer per-hex transit connectivity score computed from a parsed regional
GTFS feed (stops/routes/trips/stop_times/calendar — e.g. the merged output of
``Bay511Client.fetch_all_operator_feeds`` for the 32-operator SF Bay Area
511.org bundle). Pure compute, no I/O: every function here accepts already
-parsed GTFS rows and is exercised in tests without a network call.

Layer 1 — frequency-weighted stop density. Every stop maps to its H3 res-9
cell (``h3.latlng_to_cell``) and is weighted by its AM-peak (7:00-9:00)
trips/hour, itself weighted by the fraction of the Mon-Fri week the trip's
``calendar.txt`` service actually runs (a Saturday-only shuttle contributes
zero AM-peak commute frequency; this is the "GTFS calendar filtering excludes
non-service days" requirement). A hex with a 20-train/hour BART station scores
~10x a hex with a 2-bus/hour rural stop.

Layer 2 — k-ring exponential distance decay. Every hex with weighted stops
propagates its score to every hex within ``h3.grid_disk(cell, K_RING)``
(default k=3), decayed by ``exp(-LAMBDA_DECAY * grid_distance)``
(lambda≈0.7 gives k=1 ≈ 50%, k=2 ≈ 25%, k=3 ≈ 12% retention). Contributions
from multiple nearby stop-bearing hexes accumulate.

Composite output (``score_feed``): ``transit_connectivity_score`` (0-100,
saturating on decayed peak frequency), ``peak_frequency`` (raw decayed AM-peak
trips/hour accessible from the hex), ``transit_mode_mix`` (fraction of that
frequency by mode). Hexes untouched by any stop within k rings are simply
absent from the result — ``get_connectivity_score``/``get_peak_frequency``
return ``0.0`` (never ``None``) for any hex not present, so "no transit
access within 3 rings" reads as an explicit zero, not a missing value.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import h3

AM_PEAK_START_HOUR = 7
AM_PEAK_END_HOUR = 9  # exclusive upper bound: 7:00:00-8:59:59
AM_PEAK_WINDOW_HOURS = AM_PEAK_END_HOUR - AM_PEAK_START_HOUR

_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")

H3_RESOLUTION = 9
K_RING = 3
LAMBDA_DECAY = 0.7
# Decayed trips/hour at which transit_connectivity_score crosses 50.
CONNECTIVITY_HALF_SATURATION = 20.0

TRANSIT_MODES = ("heavy_rail", "light_rail", "bus", "ferry", "commuter_rail")

# GTFS route_type -> mode bucket (base codes 0-7; the official spec's rarer
# extended numeric codes and any unrecognized value fall back to "bus" as the
# most generic surface-transit catch-all).
_ROUTE_TYPE_MODE: dict[str, str] = {
    "0": "light_rail",     # Tram, streetcar, light rail
    "1": "heavy_rail",     # Subway/metro (e.g. BART)
    "2": "commuter_rail",  # Rail (e.g. Caltrain, SMART)
    "3": "bus",
    "4": "ferry",
    "5": "light_rail",     # Cable car (e.g. SF cable cars)
    "6": "light_rail",     # Gondola / aerial tramway
    "7": "light_rail",     # Funicular
}


def route_type_to_mode(route_type: str | int | None) -> str:
    """Map a GTFS ``route_type`` code to one of ``TRANSIT_MODES`` (default ``bus``)."""
    key = str(route_type).strip() if route_type is not None else ""
    return _ROUTE_TYPE_MODE.get(key, "bus")


def _parse_gtfs_hour(time_str: str) -> int | None:
    """First field of a GTFS ``HH:MM:SS`` time, mod 24.

    GTFS allows hours >= 24 for post-midnight trips of the prior service day;
    ``% 24`` folds those back onto a 0-23 wall-clock hour. Returns ``None`` for
    unparseable/empty input so a bad row is skipped rather than mis-bucketed.
    """
    if not time_str:
        return None
    head = time_str.strip().split(":", 1)[0]
    if not head.lstrip("-").isdigit():
        return None
    return int(head) % 24


def _weekday_service_fraction(calendar_rows: Iterable[Mapping[str, Any]] | None) -> dict[str, float]:
    """``service_id`` -> fraction (0.0-1.0) of Mon-Fri the service runs.

    AM-peak commute frequency is a weekday concept, so the denominator is 5
    (Mon-Fri) — distinct from ``GtfsStaticClient``'s 7-day denominator used
    for its all-week ``service_frequency`` covariate. A weekend-only service
    (e.g. a special-event shuttle) resolves to ``0.0`` and is excluded from
    AM-peak scoring entirely.
    """
    result: dict[str, float] = {}
    for row in calendar_rows or []:
        sid = (row.get("service_id") or "").strip()
        if not sid:
            continue
        active_days = sum(1 for d in _WEEKDAYS if str(row.get(d, "0")).strip() == "1")
        result[sid] = active_days / len(_WEEKDAYS)
    return result


def compute_stop_am_peak_frequency(feed: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-stop AM-peak (7-9a) trips/hour, weekday-weighted and split by mode.

    Returns ``stop_id -> {"trips_per_hour": float, "mode_trips_per_hour": {mode: float}}``.
    A stop with zero weekday AM-peak departures (e.g. a weekend-only stop, or
    one with no daytime service at all) is simply absent from the result.
    """
    trips = feed.get("trips") or []
    routes = feed.get("routes") or []
    stop_times = feed.get("stop_times") or []
    calendar = feed.get("calendar") or []

    weekday_fraction = _weekday_service_fraction(calendar)
    route_type_by_id = {(r.get("route_id") or "").strip(): r.get("route_type") for r in routes}

    trip_route: dict[str, str] = {}
    trip_service: dict[str, str] = {}
    for t in trips:
        tid = (t.get("trip_id") or "").strip()
        if not tid:
            continue
        trip_route[tid] = (t.get("route_id") or "").strip()
        trip_service[tid] = (t.get("service_id") or "").strip()

    stop_weighted: dict[str, float] = defaultdict(float)
    stop_mode_weighted: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for st in stop_times:
        tid = (st.get("trip_id") or "").strip()
        sid = (st.get("stop_id") or "").strip()
        if not tid or not sid:
            continue
        hour = _parse_gtfs_hour(st.get("arrival_time") or st.get("departure_time") or "")
        if hour is None or not (AM_PEAK_START_HOUR <= hour < AM_PEAK_END_HOUR):
            continue
        svc = trip_service.get(tid)
        # No calendar row for this service_id -> default to full weekday
        # service, mirroring GtfsStaticClient's "missing calendar = daily" rule.
        weight = weekday_fraction.get(svc, 1.0) if svc else 1.0
        if weight <= 0:
            continue
        stop_weighted[sid] += weight
        mode = route_type_to_mode(route_type_by_id.get(trip_route.get(tid)))
        stop_mode_weighted[sid][mode] += weight

    result: dict[str, dict[str, Any]] = {}
    for sid, weighted_count in stop_weighted.items():
        result[sid] = {
            "trips_per_hour": weighted_count / AM_PEAK_WINDOW_HOURS,
            "mode_trips_per_hour": {
                mode: value / AM_PEAK_WINDOW_HOURS for mode, value in stop_mode_weighted[sid].items()
            },
        }
    return result


def aggregate_stops_to_hex(
    stops: Iterable[tuple[str, float, float, str]],
    stop_frequency: Mapping[str, Mapping[str, Any]],
    resolution: int = H3_RESOLUTION,
) -> dict[str, dict[str, Any]]:
    """Layer 1: sum each hex's AM-peak weighted stop frequency (and per-mode split).

    Returns ``h3_index -> {"weighted_stops": float, "stop_count": int,
    "mode_trips_per_hour": {mode: float}}``. A stop with no AM-peak departures
    still counts toward ``stop_count`` but contributes ``0`` to
    ``weighted_stops``.
    """
    hex_agg: dict[str, dict[str, Any]] = {}
    for stop_id, lat, lng, _name in stops:
        cell = h3.latlng_to_cell(lat, lng, resolution)
        bucket = hex_agg.setdefault(
            cell,
            {"weighted_stops": 0.0, "stop_count": 0, "mode_trips_per_hour": defaultdict(float)},
        )
        bucket["stop_count"] += 1
        freq = stop_frequency.get(stop_id)
        if not freq:
            continue
        bucket["weighted_stops"] += freq["trips_per_hour"]
        for mode, value in freq["mode_trips_per_hour"].items():
            bucket["mode_trips_per_hour"][mode] += value
    return hex_agg


def propagate_k_ring_decay(
    hex_layer1: Mapping[str, Mapping[str, Any]],
    k_ring: int = K_RING,
    lam: float = LAMBDA_DECAY,
) -> dict[str, dict[str, Any]]:
    """Layer 2: spread each stop-bearing hex's weighted frequency across its k-ring.

    For every hex with ``weighted_stops > 0``, every cell within
    ``h3.grid_disk(cell, k_ring)`` receives
    ``weighted_stops * exp(-lam * grid_distance)``; contributions from
    multiple source hexes accumulate. Returns
    ``h3_index -> {"peak_frequency": float, "mode_trips_per_hour": {mode: float}}``
    for every hex reached by at least one source within ``k_ring`` — a hex
    absent from the map has, by construction, no transit access within range.
    """
    propagated: dict[str, dict[str, Any]] = {}
    for source_cell, agg in hex_layer1.items():
        weighted = agg.get("weighted_stops", 0.0)
        if weighted <= 0:
            continue
        mode_freqs = agg.get("mode_trips_per_hour", {})
        for neighbor in h3.grid_disk(source_cell, k_ring):
            distance = h3.grid_distance(source_cell, neighbor)
            decay = math.exp(-lam * distance)
            bucket = propagated.setdefault(
                neighbor,
                {"peak_frequency": 0.0, "mode_trips_per_hour": defaultdict(float)},
            )
            bucket["peak_frequency"] += weighted * decay
            for mode, value in mode_freqs.items():
                bucket["mode_trips_per_hour"][mode] += value * decay
    return propagated


def connectivity_score(
    peak_frequency: float,
    half_saturation: float = CONNECTIVITY_HALF_SATURATION,
) -> float:
    """Saturating 0-100 composite: ``100 * raw / (raw + half_saturation)``.

    Monotonic increasing, exactly ``0.0`` at ``raw <= 0`` (never ``None``),
    and approaches but never reaches 100 as ``raw`` grows without bound.
    ``half_saturation`` is the decayed trips/hour value at which the score
    crosses 50.
    """
    if peak_frequency <= 0:
        return 0.0
    return round(100.0 * peak_frequency / (peak_frequency + half_saturation), 4)


def mode_mix(mode_trips_per_hour: Mapping[str, float]) -> dict[str, float]:
    """Fraction of decayed frequency per mode; sums to ~1.0, or all-0 when empty."""
    total = sum(mode_trips_per_hour.values())
    if total <= 0:
        return {mode: 0.0 for mode in TRANSIT_MODES}
    return {mode: round(mode_trips_per_hour.get(mode, 0.0) / total, 4) for mode in TRANSIT_MODES}


def score_feed(
    feed: Mapping[str, Any],
    resolution: int = H3_RESOLUTION,
    k_ring: int = K_RING,
    lam: float = LAMBDA_DECAY,
    half_saturation: float = CONNECTIVITY_HALF_SATURATION,
) -> list[dict[str, Any]]:
    """Full pipeline: a parsed regional GTFS feed -> per-hex composite scores.

    Each output row: ``h3_index``, ``transit_connectivity_score`` (0-100),
    ``peak_frequency`` (decayed AM-peak trips/hour), ``transit_mode_mix``
    (dict over ``TRANSIT_MODES``), and ``stop_count`` (raw, undecayed stop
    tally for the hex's own cell — ``0`` for a purely propagated neighbor).
    """
    stops = feed.get("stops") or []
    stop_frequency = compute_stop_am_peak_frequency(feed)
    hex_layer1 = aggregate_stops_to_hex(stops, stop_frequency, resolution=resolution)
    propagated = propagate_k_ring_decay(hex_layer1, k_ring=k_ring, lam=lam)

    rows: list[dict[str, Any]] = []
    for cell, agg in propagated.items():
        freq = agg["peak_frequency"]
        rows.append(
            {
                "h3_index": cell,
                "transit_connectivity_score": connectivity_score(freq, half_saturation),
                "peak_frequency": round(freq, 4),
                "transit_mode_mix": mode_mix(agg["mode_trips_per_hour"]),
                "stop_count": hex_layer1.get(cell, {}).get("stop_count", 0),
            }
        )
    return rows


def _index_rows(scored_rows: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]]) -> Mapping[str, Mapping[str, Any]]:
    if isinstance(scored_rows, Mapping):
        return scored_rows
    return {row["h3_index"]: row for row in scored_rows}


def get_connectivity_score(
    h3_index: str,
    scored_rows: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
) -> float:
    """Look up a hex's ``transit_connectivity_score``, defaulting to ``0.0`` (never ``None``)."""
    row = _index_rows(scored_rows).get(h3_index)
    return float(row["transit_connectivity_score"]) if row else 0.0


def get_peak_frequency(
    h3_index: str,
    scored_rows: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
) -> float:
    """Look up a hex's ``peak_frequency``, defaulting to ``0.0`` (never ``None``)."""
    row = _index_rows(scored_rows).get(h3_index)
    return float(row["peak_frequency"]) if row else 0.0
