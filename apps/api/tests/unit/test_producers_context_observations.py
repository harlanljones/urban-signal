"""Unit tests for the US-363 §2.7/§2.8 context-observation producer.

Fixtures are byte-verbatim rows captured live on 2026-08-28 from
`5zyy-y8am`, `xq83-jr8c`, `teqw-tu6e`, `ct66-47at`, `6up2-gnw8` and
`65db-xm6k`. Spine-stable: nothing here asserts division resolution or
geocode-hook call counts.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.producers.context_observations_producer import (
    SOURCE_COUNTERS,
    SOURCE_ENERGY,
    ContextObservationsProducer,
)
from src.producers.field_maps_counters import (
    SEATTLE_FREMONT_SENSOR,
    counter_metric_name,
    normalize_travel_mode,
)
from src.producers.field_maps_energy_benchmark import (
    is_non_compliant,
    metrics_for,
    to_float,
)
from src.spatial.city_registry import (
    REGISTRY,
    CityId,
    FeedType,
    get_dataset,
)

# --------------------------------------------------------------------------- #
# Live fixtures (2026-08-28)                                                    #
# --------------------------------------------------------------------------- #

NYC_ENERGY_ROW = {
    "report_year": "2024",
    "property_id": "8139",
    "property_name": "200 (655 3rd Ave)",
    "address_1": "200  East  42nd  St.",
    "borough": "MANHATTAN",
    "postal_code": "10017",
    "latitude": "40.750698",
    "longitude": "-73.974306",
    "energy_star_score": "69",
    "site_eui_kbtu_ft": "87.6",
    "total_location_based_ghg": "2777.92",
    "total_location_based_ghg_1": "5.03",
    "property_gfa_calculated": "383165",
    "primary_property_type": "Office",
    "nta2020": "MN0603",
    "reason_s_for_no_score": "Not Available",
}

# The 2024 cohort's sentinel case: a real building whose ENERGY STAR cell is
# the string "Not Available". It must be dropped, not read as 0.
NYC_ENERGY_ROW_SENTINEL = {
    "report_year": "2024",
    "property_id": "7365",
    "property_name": "1155",
    "address_1": "1155  Avenue  of  the  Americas",
    "borough": "MANHATTAN",
    "postal_code": "10036",
    "latitude": "40.756631",
    "longitude": "-73.982826",
    "energy_star_score": "Not Available",
    "site_eui_kbtu_ft": "54.9",
    "total_location_based_ghg": "4031.96",
    "total_location_based_ghg_1": "10.03",
    "property_gfa_calculated": "694052",
    "primary_property_type": "Office",
    "nta2020": "MN0502",
}

CHICAGO_ENERGY_ROW = {
    "data_year": "2021",
    "id": "260184",
    "property_name": "Hampden Green Condominium Association",
    "reporting_status": "Submitted",
    "address": "2728 N HAMPDEN CT",
    "zip_code": "60614",
    "chicago_energy_rating": "1.5",
    "community_area": "LINCOLN PARK",
    "primary_property_type": "Multifamily Housing",
    "gross_floor_area_buildings_sq_ft": "170000",
    "energy_star_score": "37",
    "site_eui_kbtu_sq_ft": "117.6",
    "source_eui_kbtu_sq_ft": "161.6",
    "total_ghg_emissions_metric_tons_co2e": "1148.3",
    "ghg_intensity_kg_co2e_sq_ft": "8.2",
    "latitude": "41.92201051",
    "longitude": "-87.65461957",
    "location": {"latitude": "41.92201051", "longitude": "-87.65461957"},
    "row_id": "2021-260184",
}

SEATTLE_ENERGY_ROW = {
    "osebuildingid": "1",
    "datayear": "2024",
    "buildingname": "MAYFLOWER PARK HOTEL",
    "buildingtype": "NonResidential",
    "address": "405 OLIVE WAY",
    "city": "SEATTLE",
    "state": "WA",
    "zipcode": "98101",
    "latitude": "47.6122",
    "longitude": "-122.33799",
    "neighborhood": "DOWNTOWN",
    "energystarscore": "59",
    "siteeui_kbtu_sf": "61.70000076",
    "sourceeui_kbtu_sf": "121.4000015",
    "epapropertytype": "Hotel",
    "propertygfatotal": "88434",
    "compliancestatus": "Not Compliant",
    "totalghgemissions": "263.3",
    "ghgemissionsintensity": "2.98",
    "demolished": False,
}

# Four live NYC count rows: one sensor, both directions, both parallel flows,
# same 15-minute bucket.
NYC_COUNT_ROWS = [
    {
        "sensor_id": "100009425",
        "travelmode": "bike",
        "direction": "in",
        "flowid": "101009425",
        "timestamp": "2026-08-26T00:15:00.000",
        "granularity": "PT15M",
        "counts": "0",
        "status": "raw",
    },
    {
        "sensor_id": "100009425",
        "travelmode": "bike",
        "direction": "out",
        "flowid": "102009425",
        "timestamp": "2026-08-26T00:15:00.000",
        "granularity": "PT15M",
        "counts": "4",
        "status": "raw",
    },
    {
        "sensor_id": "100009425",
        "travelmode": "bike",
        "direction": "in",
        "flowid": "353237827",
        "timestamp": "2026-08-26T00:15:00.000",
        "granularity": "PT15M",
        "counts": "5",
        "status": "raw",
    },
    {
        "sensor_id": "100009425",
        "travelmode": "bike",
        "direction": "out",
        "flowid": "353237830",
        "timestamp": "2026-08-26T00:30:00.000",
        "granularity": "PT15M",
        "counts": "2",
        "status": "raw",
    },
]

NYC_SENSOR_ROWS = [
    {
        "id": "100005020",
        "name": "Manhattan Bridge 2012 Test Bike Counter",
        "lat": "40.69981",
        "lon": "-73.98589",
        "travelmodes": "bike",
        "directional": True,
    },
    {
        "id": "100009425",
        "name": "Prospect Park West",
        "lat": "40.66900",
        "lon": "-73.97400",
        "travelmodes": "bike",
        "directional": True,
    },
]

SEATTLE_FREMONT_ROWS = [
    {
        "date": "2026-07-31T22:00:00.000",
        "fremont_bridge": "150",
        "fremont_bridge_nb": "60",
        "fremont_bridge_sb": "90",
    },
    {
        "date": "2026-07-31T23:00:00.000",
        "fremont_bridge": "130",
        "fremont_bridge_nb": "45",
        "fremont_bridge_sb": "85",
    },
]


@pytest.fixture
def producer() -> ContextObservationsProducer:
    p = ContextObservationsProducer.__new__(ContextObservationsProducer)
    p.producer = MagicMock()
    p.socrata = MagicMock()
    p.arcgis = MagicMock()
    p.carto = MagicMock()
    p.ckan = MagicMock()
    from src.spatial.h3_indexer import H3SpatialIndexer

    p.spatial_indexer = H3SpatialIndexer()
    p._sensor_cache = {}
    return p


# --------------------------------------------------------------------------- #
# helpers                                                                       #
# --------------------------------------------------------------------------- #


class TestSentinelCoercion:
    @pytest.mark.parametrize(
        "raw",
        ["Not Available", "NA", "N/A", "Not Applicable", "", "  ", None, "-"],
    )
    def test_sentinels_become_none_not_zero(self, raw):
        assert to_float(raw) is None

    def test_real_numbers_survive(self):
        assert to_float("87.6") == pytest.approx(87.6)
        assert to_float("383,165") == pytest.approx(383165.0)
        assert to_float(59) == pytest.approx(59.0)

    def test_booleans_are_not_numbers(self):
        # Seattle's `demolished` is a real bool; reading it as 1.0/0.0 would
        # invent a metric.
        assert to_float(True) is None
        assert to_float(False) is None

    def test_compliance_classification(self):
        assert is_non_compliant("Not Compliant") is True
        assert is_non_compliant("Compliant") is False
        assert is_non_compliant("Not Available") is None


class TestTravelModeNormalization:
    def test_pedestrian_folds_to_ped(self):
        assert normalize_travel_mode("pedestrian") == "ped"

    def test_scooter_passes_through(self):
        # The live feed carries 13,458 scooter rows the sweep doc does not
        # mention; they must stay visible, not become bikes.
        assert normalize_travel_mode("scooter") == "scooter"
        assert counter_metric_name("scooter") == "scooter_flow"

    def test_metric_names(self):
        assert counter_metric_name("bike") == "bike_flow"
        assert counter_metric_name("pedestrian") == "ped_flow"


# --------------------------------------------------------------------------- #
# §2.7 energy benchmarking                                                      #
# --------------------------------------------------------------------------- #


class TestEnergyBenchmarkParsing:
    def test_nyc_row_fans_out_to_one_event_per_metric(self, producer):
        events = producer.parse_energy_row(NYC_ENERGY_ROW, city_id="nyc")
        by_metric = {e.metric: e for e in events}
        assert by_metric["energy_star_score"].value == pytest.approx(69.0)
        assert by_metric["site_eui"].value == pytest.approx(87.6)
        assert by_metric["ghg_total"].value == pytest.approx(2777.92)
        assert by_metric["ghg_intensity"].value == pytest.approx(5.03)
        assert by_metric["gross_floor_area"].value == pytest.approx(383165.0)
        assert all(e.source == SOURCE_ENERGY for e in events)
        assert all(e.city_id == "nyc" for e in events)

    def test_sentinel_metric_is_absent_not_zero(self, producer):
        events = producer.parse_energy_row(NYC_ENERGY_ROW_SENTINEL, city_id="nyc")
        metrics = {e.metric for e in events}
        assert "energy_star_score" not in metrics, (
            "a 'Not Available' ENERGY STAR cell became an observation — "
            "every hex mean would be dragged toward zero"
        )
        assert "site_eui" in metrics

    def test_period_bounds_span_the_report_year(self, producer):
        event = producer.parse_energy_row(NYC_ENERGY_ROW, city_id="nyc")[0]
        assert event.period_start == datetime(2024, 1, 1, tzinfo=UTC)
        assert event.period_end == datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC)
        assert event.period_type == "year"

    def test_observation_ids_are_deterministic_and_unique(self, producer):
        events = producer.parse_energy_row(NYC_ENERGY_ROW, city_id="nyc")
        ids = [e.observation_id for e in events]
        assert len(ids) == len(set(ids))
        assert "energy_benchmark:8139:2024:site_eui" in ids
        again = producer.parse_energy_row(NYC_ENERGY_ROW, city_id="nyc")
        assert [e.observation_id for e in again] == ids

    def test_coordinates_and_h3_are_populated(self, producer):
        event = producer.parse_energy_row(NYC_ENERGY_ROW, city_id="nyc")[0]
        assert event.latitude == pytest.approx(40.750698)
        assert event.longitude == pytest.approx(-73.974306)
        assert event.h3_res7 and event.h3_res8 and event.h3_res9

    def test_chicago_reads_native_and_nested_coordinates(self, producer):
        events = producer.parse_energy_row(CHICAGO_ENERGY_ROW, city_id="chicago")
        by_metric = {e.metric: e for e in events}
        assert by_metric["site_eui"].value == pytest.approx(117.6)
        assert by_metric["chicago_energy_rating"].value == pytest.approx(1.5)
        assert by_metric["site_eui"].latitude == pytest.approx(41.92201051)
        # `reporting_status: Submitted` is not in the non-compliant set.
        assert by_metric["non_compliant"].value == 0.0

    def test_chicago_falls_back_to_the_location_container(self, producer):
        row = dict(CHICAGO_ENERGY_ROW)
        row.pop("latitude")
        row.pop("longitude")
        event = producer.parse_energy_row(row, city_id="chicago")[0]
        assert event.latitude == pytest.approx(41.92201051)
        assert event.longitude == pytest.approx(-87.65461957)

    def test_seattle_emits_the_compliance_indicator(self, producer):
        events = producer.parse_energy_row(SEATTLE_ENERGY_ROW, city_id="seattle")
        by_metric = {e.metric: e for e in events}
        assert by_metric["non_compliant"].value == 1.0
        assert by_metric["non_compliant"].unit == "indicator"
        assert by_metric["ghg_intensity"].value == pytest.approx(2.98)
        assert by_metric["energy_star_score"].value == pytest.approx(59.0)

    def test_seattle_demolished_bool_never_becomes_a_metric(self, producer):
        events = producer.parse_energy_row(SEATTLE_ENERGY_ROW, city_id="seattle")
        assert "demolished" not in {e.metric for e in events}

    def test_row_without_a_report_year_yields_nothing(self, producer):
        row = dict(NYC_ENERGY_ROW)
        row.pop("report_year")
        assert producer.parse_energy_row(row, city_id="nyc") == []

    def test_row_without_an_asset_id_yields_nothing(self, producer):
        row = dict(NYC_ENERGY_ROW)
        row["property_id"] = "  "
        assert producer.parse_energy_row(row, city_id="nyc") == []

    def test_null_island_coordinates_are_dropped(self, producer):
        row = dict(NYC_ENERGY_ROW, latitude="0", longitude="0")
        event = producer.parse_energy_row(row, city_id="nyc")[0]
        assert event.latitude is None and event.longitude is None
        assert event.h3_res9 is None

    def test_metric_catalog_is_per_city(self):
        assert "chicago_energy_rating" in metrics_for("chicago")
        assert "chicago_energy_rating" not in metrics_for("nyc")
        assert metrics_for("atlantis") == {}


# --------------------------------------------------------------------------- #
# §2.8 counters                                                                 #
# --------------------------------------------------------------------------- #


class TestCounterAggregation:
    def test_fifteen_minute_rows_fold_to_one_day(self, producer):
        totals = producer.aggregate_count_rows(NYC_COUNT_ROWS, city_id="nyc")
        assert len(totals) == 1, "four rows for one sensor-day produced more than one observation"
        (sensor, mode, day), value = next(iter(totals.items()))
        assert sensor == "100009425"
        assert mode == "bike"
        assert day == datetime(2026, 8, 26, tzinfo=UTC)
        # Every parallel flow and both directions are summed: 0 + 4 + 5 + 2.
        assert value == pytest.approx(11.0)

    def test_modes_do_not_bleed_into_each_other(self, producer):
        rows = list(NYC_COUNT_ROWS) + [
            dict(NYC_COUNT_ROWS[0], travelmode="pedestrian", counts="40", flowid="9"),
        ]
        totals = producer.aggregate_count_rows(rows, city_id="nyc")
        assert set(m for _, m, _ in totals) == {"bike", "ped"}
        assert totals[("100009425", "ped", datetime(2026, 8, 26, tzinfo=UTC))] == pytest.approx(40.0)

    def test_unparseable_rows_are_skipped_not_zeroed(self, producer):
        rows = [
            dict(NYC_COUNT_ROWS[0], counts="Not Available"),
            dict(NYC_COUNT_ROWS[1], timestamp=""),
            dict(NYC_COUNT_ROWS[2], sensor_id=""),
        ]
        assert producer.aggregate_count_rows(rows, city_id="nyc") == {}

    def test_seattle_wide_rows_sum_directions_only(self, producer):
        totals = producer.aggregate_fremont_rows(SEATTLE_FREMONT_ROWS)
        key = ("fremont_bridge", "bike", datetime(2026, 7, 31, tzinfo=UTC))
        # 60+90+45+85 = 280. The undirected `fremont_bridge` totals (150, 130)
        # are deliberately excluded — including them would double-count.
        assert totals[key] == pytest.approx(280.0)
        assert len(totals) == 1

    def test_naive_timestamps_bucket_by_utc_not_host_timezone(self, producer):
        """A 22:00 row belongs to that calendar day everywhere.

        Socrata publishes floating (naive) timestamps. If they are left naive
        and later run through `astimezone`, the host's timezone decides the
        day — on a US-Pacific box a 22:00 row silently lands on tomorrow, and
        the daily rollup for two different developers disagrees.
        """
        totals = producer.aggregate_fremont_rows(SEATTLE_FREMONT_ROWS)
        days = {day for _, _, day in totals}
        assert days == {datetime(2026, 7, 31, tzinfo=UTC)}

    def test_counter_events_carry_registry_geometry(self, producer):
        totals = producer.aggregate_count_rows(NYC_COUNT_ROWS, city_id="nyc")
        sensors = {
            "100009425": {"latitude": 40.669, "longitude": -73.974, "asset_name": "Prospect Park West"}
        }
        events, unlocatable = producer.build_counter_events(totals, "nyc", sensors)
        assert not unlocatable
        assert len(events) == 1
        event = events[0]
        assert event.source == SOURCE_COUNTERS
        assert event.metric == "bike_flow"
        assert event.unit == "counts_per_day"
        assert event.period_type == "day"
        assert event.value == pytest.approx(11.0)
        assert event.latitude == pytest.approx(40.669)
        assert event.h3_res9
        assert event.observation_id == "bike_ped:100009425:2026-08-26:bike_flow"

    def test_sensor_missing_from_the_registry_is_reported_not_guessed(self, producer):
        totals = producer.aggregate_count_rows(NYC_COUNT_ROWS, city_id="nyc")
        events, unlocatable = producer.build_counter_events(totals, "nyc", sensors={})
        assert events == []
        assert unlocatable == [("100009425", "2026-08-26")]

    def test_registry_row_without_coordinates_is_unlocatable(self, producer):
        totals = producer.aggregate_count_rows(NYC_COUNT_ROWS, city_id="nyc")
        sensors = {"100009425": {"latitude": None, "longitude": None, "asset_name": "x"}}
        events, unlocatable = producer.build_counter_events(totals, "nyc", sensors)
        assert events == [] and unlocatable

    def test_fremont_sensor_constant_sits_inside_seattle(self, producer):
        from src.spatial.cities.seattle import SEATTLE_METRO_BBOX

        lat = SEATTLE_FREMONT_SENSOR["latitude"]
        lng = SEATTLE_FREMONT_SENSOR["longitude"]
        assert SEATTLE_METRO_BBOX["min_lat"] <= lat <= SEATTLE_METRO_BBOX["max_lat"]
        assert SEATTLE_METRO_BBOX["min_lng"] <= lng <= SEATTLE_METRO_BBOX["max_lng"]

    def test_sensor_registry_load_is_cached(self, producer):
        spec = get_dataset(CityId.NYC, FeedType.BIKE_PED)
        client = MagicMock()
        client.paginate.return_value = iter([NYC_SENSOR_ROWS])
        producer.socrata = client
        sensors = producer.load_sensor_registry("nyc", spec)
        assert sensors["100009425"]["latitude"] == pytest.approx(40.669)
        assert sensors["100009425"]["asset_name"] == "Prospect Park West"
        producer.load_sensor_registry("nyc", spec)
        assert client.paginate.call_count == 1


# --------------------------------------------------------------------------- #
# registration                                                                  #
# --------------------------------------------------------------------------- #


class TestRegistration:
    @pytest.mark.parametrize(
        "city,dataset_id",
        [
            (CityId.NYC, "5zyy-y8am"),
            (CityId.CHICAGO, "xq83-jr8c"),
            (CityId.SEATTLE, "teqw-tu6e"),
        ],
    )
    def test_energy_benchmark_registered(self, city, dataset_id):
        spec = get_dataset(city, FeedType.ENERGY_BENCHMARK)
        assert dataset_id in spec.endpoint
        assert spec.platform == "socrata"
        assert spec.producer_key == "energy_benchmark"
        assert spec.needs_geocode is False, "all three feeds publish native coordinates"
        assert spec.expected_cadence_days == 365
        assert spec.alarm_exempt is True and spec.alarm_exempt_reason

    @pytest.mark.parametrize(
        "city,dataset_id",
        [(CityId.NYC, "ct66-47at"), (CityId.SEATTLE, "65db-xm6k")],
    )
    def test_counters_registered(self, city, dataset_id):
        spec = get_dataset(city, FeedType.BIKE_PED)
        assert dataset_id in spec.endpoint
        assert spec.producer_key == "bike_ped"

    def test_nyc_counts_declare_the_sensor_registry_companion(self):
        spec = get_dataset(CityId.NYC, FeedType.BIKE_PED)
        assert "6up2-gnw8" in spec.companion_endpoints["sensor_registry"]

    def test_nyc_counts_filter_retracted_rows(self):
        spec = get_dataset(CityId.NYC, FeedType.BIKE_PED)
        assert spec.where == "status != 'deleted'"

    def test_seattle_counts_declare_the_wide_layout(self):
        spec = get_dataset(CityId.SEATTLE, FeedType.BIKE_PED)
        assert spec.companion_endpoints.get("wide_layout") is True

    def test_both_families_share_one_topic(self):
        from src.config import settings

        for city, feed in (
            (CityId.NYC, FeedType.ENERGY_BENCHMARK),
            (CityId.NYC, FeedType.BIKE_PED),
            (CityId.CHICAGO, FeedType.ENERGY_BENCHMARK),
            (CityId.SEATTLE, FeedType.ENERGY_BENCHMARK),
            (CityId.SEATTLE, FeedType.BIKE_PED),
        ):
            assert get_dataset(city, feed).topic == settings.topic_context_observations

    def test_no_other_city_silently_gained_these_feeds(self):
        registered = {
            cid.value
            for cid, reg in REGISTRY.items()
            if FeedType.ENERGY_BENCHMARK in reg.datasets or FeedType.BIKE_PED in reg.datasets
        }
        assert registered == {"nyc", "chicago", "seattle"}
