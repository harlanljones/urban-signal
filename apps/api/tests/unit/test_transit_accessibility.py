"""Unit tests for US-442 transit accessibility scoring (GTFS stop-to-H3 k-ring).

Network-free: all inputs are synthetic GTFS row dicts; H3 operations run
through the real ``h3`` library (assertions use ``h3`` itself to derive
expected cells/distances rather than hardcoded hex strings).
"""

import math

import h3
import pytest

from src.spatial.transit_accessibility import (
    AM_PEAK_WINDOW_HOURS,
    CONNECTIVITY_HALF_SATURATION,
    LAMBDA_DECAY,
    TRANSIT_MODES,
    _parse_gtfs_hour,
    _weekday_service_fraction,
    aggregate_stops_to_hex,
    compute_stop_am_peak_frequency,
    connectivity_score,
    get_connectivity_score,
    get_peak_frequency,
    mode_mix,
    propagate_k_ring_decay,
    route_type_to_mode,
    score_feed,
)

BART_LAT, BART_LNG = 37.7749, -122.4194  # downtown SF, arbitrary "BART station"
RURAL_LAT, RURAL_LNG = 40.0, -120.0  # far away, distinct hex


def _origin_and_ring(k: int) -> tuple[str, str]:
    """A real H3 res-9 origin cell and one neighbor at exact grid distance k."""
    origin = h3.latlng_to_cell(BART_LAT, BART_LNG, 9)
    if k == 0:
        return origin, origin
    ring = list(h3.grid_ring(origin, k))
    return origin, ring[0]


class TestGtfsHourParsing:
    def test_parses_normal_hour(self):
        assert _parse_gtfs_hour("07:15:00") == 7

    def test_wraps_post_midnight_hours(self):
        assert _parse_gtfs_hour("25:10:00") == 1

    def test_none_for_empty_or_malformed(self):
        assert _parse_gtfs_hour("") is None
        assert _parse_gtfs_hour(None) is None
        assert _parse_gtfs_hour("not_a_time") is None


class TestWeekdayServiceFraction:
    def test_weekday_only_service_is_full_weight(self):
        calendar = [
            {
                "service_id": "WD",
                "monday": "1",
                "tuesday": "1",
                "wednesday": "1",
                "thursday": "1",
                "friday": "1",
                "saturday": "0",
                "sunday": "0",
            }
        ]
        assert _weekday_service_fraction(calendar) == {"WD": 1.0}

    def test_weekend_only_service_is_zero_weight(self):
        calendar = [
            {
                "service_id": "WE",
                "monday": "0",
                "tuesday": "0",
                "wednesday": "0",
                "thursday": "0",
                "friday": "0",
                "saturday": "1",
                "sunday": "1",
            }
        ]
        assert _weekday_service_fraction(calendar) == {"WE": 0.0}

    def test_partial_weekday_service(self):
        calendar = [
            {
                "service_id": "MWF",
                "monday": "1",
                "tuesday": "0",
                "wednesday": "1",
                "thursday": "0",
                "friday": "1",
            }
        ]
        assert _weekday_service_fraction(calendar) == pytest.approx({"MWF": 3.0 / 5.0})


class TestRouteTypeMode:
    @pytest.mark.parametrize(
        "route_type,expected",
        [
            ("0", "light_rail"),
            ("1", "heavy_rail"),
            ("2", "commuter_rail"),
            ("3", "bus"),
            ("4", "ferry"),
            (1, "heavy_rail"),  # int also accepted
        ],
    )
    def test_known_codes(self, route_type, expected):
        assert route_type_to_mode(route_type) == expected

    def test_unknown_code_falls_back_to_bus(self):
        assert route_type_to_mode("999") == "bus"
        assert route_type_to_mode(None) == "bus"


def _synthetic_feed():
    """BART-like high-frequency AM-peak stop + rural low-frequency stop + weekend-only stop."""
    stops = [
        ("BART1", BART_LAT, BART_LNG, "Downtown BART"),
        ("RURAL1", RURAL_LAT, RURAL_LNG, "Rural Bus Stop"),
        ("WKND1", RURAL_LAT + 0.5, RURAL_LNG + 0.5, "Weekend Shuttle Stop"),
    ]
    routes = [
        {"route_id": "R_BART", "route_type": "1"},  # heavy rail
        {"route_id": "R_BUS", "route_type": "3"},  # bus
        {"route_id": "R_SHUTTLE", "route_type": "3"},
    ]
    # 20 BART trips/hour over the 2hr AM peak window == 40 trips, plus 2
    # rural bus trips/hour == 4 trips.
    trips = [{"trip_id": f"BT{i}", "route_id": "R_BART", "service_id": "WD"} for i in range(40)]
    trips += [{"trip_id": f"RT{i}", "route_id": "R_BUS", "service_id": "WD"} for i in range(4)]
    trips += [{"trip_id": "WKT1", "route_id": "R_SHUTTLE", "service_id": "WE"}]
    stop_times = [{"trip_id": t["trip_id"], "stop_id": "BART1", "arrival_time": "07:30:00"} for t in trips[:40]]
    stop_times += [{"trip_id": t["trip_id"], "stop_id": "RURAL1", "arrival_time": "08:00:00"} for t in trips[40:44]]
    stop_times += [{"trip_id": "WKT1", "stop_id": "WKND1", "arrival_time": "07:45:00"}]
    # An off-peak trip at the rural stop that must NOT count toward AM peak.
    stop_times += [{"trip_id": "RT_OFFPEAK", "stop_id": "RURAL1", "arrival_time": "14:00:00"}]
    trips += [{"trip_id": "RT_OFFPEAK", "route_id": "R_BUS", "service_id": "WD"}]
    calendar = [
        {
            "service_id": "WD",
            "monday": "1",
            "tuesday": "1",
            "wednesday": "1",
            "thursday": "1",
            "friday": "1",
            "saturday": "0",
            "sunday": "0",
        },
        {
            "service_id": "WE",
            "monday": "0",
            "tuesday": "0",
            "wednesday": "0",
            "thursday": "0",
            "friday": "0",
            "saturday": "1",
            "sunday": "1",
        },
    ]
    return {
        "stops": stops,
        "routes": routes,
        "trips": trips,
        "stop_times": stop_times,
        "calendar": calendar,
    }


class TestComputeStopAmPeakFrequency:
    def test_bart_stop_is_much_higher_frequency_than_rural(self):
        freq = compute_stop_am_peak_frequency(_synthetic_feed())
        assert freq["BART1"]["trips_per_hour"] == pytest.approx(20.0)  # 40 trips / 2hr
        assert freq["RURAL1"]["trips_per_hour"] == pytest.approx(2.0)  # 4 trips / 2hr
        assert freq["BART1"]["trips_per_hour"] > 5 * freq["RURAL1"]["trips_per_hour"]

    def test_weekend_only_stop_excluded_from_am_peak(self):
        freq = compute_stop_am_peak_frequency(_synthetic_feed())
        assert "WKND1" not in freq

    def test_offpeak_trip_not_counted(self):
        # RURAL1 has 4 AM-peak trips + 1 off-peak (14:00) trip; only the 4 count.
        freq = compute_stop_am_peak_frequency(_synthetic_feed())
        assert freq["RURAL1"]["trips_per_hour"] == pytest.approx(4.0 / AM_PEAK_WINDOW_HOURS)

    def test_mode_split_matches_route_type(self):
        freq = compute_stop_am_peak_frequency(_synthetic_feed())
        assert freq["BART1"]["mode_trips_per_hour"] == {"heavy_rail": pytest.approx(20.0)}
        assert freq["RURAL1"]["mode_trips_per_hour"] == {"bus": pytest.approx(2.0)}

    def test_missing_calendar_defaults_to_full_service(self):
        feed = _synthetic_feed()
        feed["calendar"] = []
        freq = compute_stop_am_peak_frequency(feed)
        # Without calendar rows every service defaults to full weight, so the
        # weekend-only stop now counts too.
        assert "WKND1" in freq


class TestAggregateStopsToHex:
    def test_sums_weighted_stops_per_hex(self):
        feed = _synthetic_feed()
        stop_frequency = compute_stop_am_peak_frequency(feed)
        hex_agg = aggregate_stops_to_hex(feed["stops"], stop_frequency)
        bart_cell = h3.latlng_to_cell(BART_LAT, BART_LNG, 9)
        rural_cell = h3.latlng_to_cell(RURAL_LAT, RURAL_LNG, 9)
        assert hex_agg[bart_cell]["weighted_stops"] == pytest.approx(20.0)
        assert hex_agg[bart_cell]["stop_count"] == 1
        assert hex_agg[rural_cell]["weighted_stops"] == pytest.approx(2.0)

    def test_stop_with_no_am_peak_service_still_counted_as_stop(self):
        feed = _synthetic_feed()
        stop_frequency = compute_stop_am_peak_frequency(feed)
        hex_agg = aggregate_stops_to_hex(feed["stops"], stop_frequency)
        wknd_cell = h3.latlng_to_cell(RURAL_LAT + 0.5, RURAL_LNG + 0.5, 9)
        assert hex_agg[wknd_cell]["stop_count"] == 1
        assert hex_agg[wknd_cell]["weighted_stops"] == 0.0


class TestPropagateKRingDecay:
    def test_origin_hex_retains_full_weight(self):
        origin, _ = _origin_and_ring(0)
        hex_layer1 = {origin: {"weighted_stops": 10.0, "mode_trips_per_hour": {"bus": 10.0}}}
        propagated = propagate_k_ring_decay(hex_layer1, k_ring=3, lam=LAMBDA_DECAY)
        assert propagated[origin]["peak_frequency"] == pytest.approx(10.0)

    @pytest.mark.parametrize("k", [1, 2, 3])
    def test_decay_matches_expected_exponential_retention(self, k):
        origin, neighbor = _origin_and_ring(k)
        hex_layer1 = {origin: {"weighted_stops": 10.0, "mode_trips_per_hour": {}}}
        propagated = propagate_k_ring_decay(hex_layer1, k_ring=3, lam=LAMBDA_DECAY)
        expected = 10.0 * math.exp(-LAMBDA_DECAY * k)
        assert propagated[neighbor]["peak_frequency"] == pytest.approx(expected)

    def test_retention_roughly_matches_ticket_percentages(self):
        # lambda ~= 0.7: k=1 ~50%, k=2 ~25%, k=3 ~12%
        assert math.exp(-LAMBDA_DECAY * 1) == pytest.approx(0.50, abs=0.02)
        assert math.exp(-LAMBDA_DECAY * 2) == pytest.approx(0.25, abs=0.02)
        assert math.exp(-LAMBDA_DECAY * 3) == pytest.approx(0.12, abs=0.02)

    def test_beyond_k_ring_receives_nothing(self):
        origin = h3.latlng_to_cell(BART_LAT, BART_LNG, 9)
        far_neighbor = next(iter(h3.grid_ring(origin, 4)))
        hex_layer1 = {origin: {"weighted_stops": 10.0, "mode_trips_per_hour": {}}}
        propagated = propagate_k_ring_decay(hex_layer1, k_ring=3, lam=LAMBDA_DECAY)
        assert far_neighbor not in propagated

    def test_contributions_from_two_sources_accumulate(self):
        origin, neighbor = _origin_and_ring(1)
        # neighbor is itself a source too -> receives its own full weight
        # plus the k=1-decayed contribution from origin.
        hex_layer1 = {
            origin: {"weighted_stops": 10.0, "mode_trips_per_hour": {}},
            neighbor: {"weighted_stops": 5.0, "mode_trips_per_hour": {}},
        }
        propagated = propagate_k_ring_decay(hex_layer1, k_ring=3, lam=LAMBDA_DECAY)
        expected = 5.0 + 10.0 * math.exp(-LAMBDA_DECAY * 1)
        assert propagated[neighbor]["peak_frequency"] == pytest.approx(expected)

    def test_zero_weighted_stops_do_not_propagate(self):
        origin = h3.latlng_to_cell(BART_LAT, BART_LNG, 9)
        hex_layer1 = {origin: {"weighted_stops": 0.0, "mode_trips_per_hour": {}}}
        assert propagate_k_ring_decay(hex_layer1) == {}


class TestConnectivityScore:
    def test_zero_raw_is_zero_not_none(self):
        assert connectivity_score(0.0) == 0.0
        assert connectivity_score(-5.0) == 0.0

    def test_half_saturation_crosses_fifty(self):
        assert connectivity_score(CONNECTIVITY_HALF_SATURATION) == pytest.approx(50.0)

    def test_monotonic_increasing_and_bounded(self):
        scores = [connectivity_score(x) for x in (0, 1, 5, 20, 50, 500, 1_000_000)]
        assert scores == sorted(scores)
        assert all(0.0 <= s < 100.0 for s in scores)


class TestModeMix:
    def test_fractions_sum_to_one(self):
        mix = mode_mix({"heavy_rail": 15.0, "bus": 5.0})
        assert sum(mix.values()) == pytest.approx(1.0)
        assert mix["heavy_rail"] == pytest.approx(0.75)
        assert mix["bus"] == pytest.approx(0.25)

    def test_empty_is_all_zero(self):
        mix = mode_mix({})
        assert set(mix) == set(TRANSIT_MODES)
        assert all(v == 0.0 for v in mix.values())


class TestScoreFeedIntegration:
    def test_bart_hex_outscores_rural_hex(self):
        rows = score_feed(_synthetic_feed())
        bart_cell = h3.latlng_to_cell(BART_LAT, BART_LNG, 9)
        rural_cell = h3.latlng_to_cell(RURAL_LAT, RURAL_LNG, 9)
        bart_score = get_connectivity_score(bart_cell, rows)
        rural_score = get_connectivity_score(rural_cell, rows)
        assert bart_score > rural_score > 0.0

    def test_hex_with_no_nearby_transit_scores_zero_not_missing(self):
        rows = score_feed(_synthetic_feed())
        far_away_cell = h3.latlng_to_cell(10.0, 10.0, 9)  # nowhere near any stop
        assert get_connectivity_score(far_away_cell, rows) == 0.0
        assert get_peak_frequency(far_away_cell, rows) == 0.0

    def test_mode_mix_present_on_output_rows(self):
        rows = score_feed(_synthetic_feed())
        bart_cell = h3.latlng_to_cell(BART_LAT, BART_LNG, 9)
        row = next(r for r in rows if r["h3_index"] == bart_cell)
        assert row["transit_mode_mix"]["heavy_rail"] == pytest.approx(1.0)

    def test_neighbor_hex_gets_propagated_but_lower_score(self):
        rows = score_feed(_synthetic_feed())
        bart_cell = h3.latlng_to_cell(BART_LAT, BART_LNG, 9)
        ring1_neighbor = next(iter(h3.grid_ring(bart_cell, 1)))
        neighbor_score = get_connectivity_score(ring1_neighbor, rows)
        bart_score = get_connectivity_score(bart_cell, rows)
        assert 0.0 < neighbor_score < bart_score

    def test_accepts_dict_index_form(self):
        rows = score_feed(_synthetic_feed())
        as_dict = {r["h3_index"]: r for r in rows}
        bart_cell = h3.latlng_to_cell(BART_LAT, BART_LNG, 9)
        assert get_connectivity_score(bart_cell, as_dict) == get_connectivity_score(bart_cell, rows)
