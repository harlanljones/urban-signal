"""Unit tests for the US-403 GtfsStaticClient (GTFS static schedule covariates).

Network-free: parsing is exercised on in-memory zips, catalog selection on
synthetic catalog records, and H3 tagging through the real H3SpatialIndexer
(assertions are on aggregate counts, which are cell-agnostic).
"""

import io
import os
import tempfile
import zipfile

import pytest

from src.producers.gtfs_static_client import (
    GtfsStaticClient,
    _bboxes_overlap,
    _feed_bbox,
    _in_bbox,
)

NYC_BBOX = {
    "min_lat": 40.50,
    "max_lat": 40.92,
    "min_lon": -74.26,
    "max_lon": -73.70,
}


def build_zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, text)
    return buf.getvalue()


GTFS_FILES = {
    "stops.txt": (
        "stop_id,stop_name,stop_lat,stop_lon\n"
        "S1,Main & 1st,40.71,-73.99\n"
        "S2,Main & 2nd,40.712,-73.988\n"
        "S3,Rural Outpost,41.5,-74.5\n"
        "S4,BadStop,not_a_lat,-73.9\n"
    ),
    "routes.txt": "route_id,route_short_name\nR1,1\nR2,2\n",
    "trips.txt": (
        "trip_id,route_id,service_id\n"
        "T1,R1,WD\n"
        "T2,R1,WD\n"
        "T3,R2,WE\n"
        "T4,R2,WD\n"
    ),
    "stop_times.txt": (
        "trip_id,stop_id,arrival_time,departure_time\n"
        "T1,S1,08:00:00,08:00:00\n"
        "T1,S2,08:05:00,08:05:00\n"
        "T2,S1,09:00:00,09:00:00\n"
        "T3,S2,10:00:00,10:00:00\n"
        "T4,S1,11:00:00,11:00:00\n"
    ),
    "calendar.txt": (
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday\n"
        "WD,1,1,1,1,1,0,0\n"
        "WE,0,0,0,0,0,1,1\n"
    ),
}


def _sum(rows, key):
    return sum(r.get(key, 0) for r in rows)


class TestZipParsing:
    def test_parse_feed_zip_extracts_all_five_files(self):
        feed = GtfsStaticClient.parse_feed_zip(build_zip(GTFS_FILES))
        assert len(feed["stops"]) == 3  # bad-coordinate row dropped
        assert len(feed["routes"]) == 2
        assert len(feed["trips"]) == 4
        assert len(feed["stop_times"]) == 5
        assert len(feed["calendar"]) == 2

    def test_parse_feed_zip_missing_calendar_is_empty_not_error(self):
        files = {k: v for k, v in GTFS_FILES.items() if k != "calendar.txt"}
        feed = GtfsStaticClient.parse_feed_zip(build_zip(files))
        assert feed["calendar"] == []

    def test_service_day_map(self):
        feed = GtfsStaticClient.parse_feed_zip(build_zip(GTFS_FILES))
        days = GtfsStaticClient._service_day_map(feed["calendar"])
        assert days == {"WD": 5.0, "WE": 2.0}

    def test_read_csv_is_empty_for_absent_file(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("stops.txt", "stop_id\nX\n")
        raw = buf.getvalue()
        fd, path = tempfile.mkstemp(suffix=".zip")
        try:
            os.write(fd, raw)
            os.close(fd)
            with zipfile.ZipFile(path) as z:
                assert GtfsStaticClient._read_csv(z, "routes.txt") == []
        finally:
            os.unlink(path)


class TestCovariateComputation:
    def test_bbox_filter_drops_outside_stops(self):
        feed = GtfsStaticClient.parse_feed_zip(build_zip(GTFS_FILES))
        rows = GtfsStaticClient.compute_covariates(feed, bbox=NYC_BBOX)
        assert _sum(rows, "stop_density") == 2  # S1 + S2; S3 outside bbox

    def test_service_frequency_is_weighted_daily_departures(self):
        feed = GtfsStaticClient.parse_feed_zip(build_zip(GTFS_FILES))
        rows = GtfsStaticClient.compute_covariates(feed, bbox=NYC_BBOX)
        # S1: T1(WD 5/7) + T2(WD 5/7) + T4(WD 5/7) = 15/7
        # S2: T1(WD 5/7) + T3(WE 2/7) = 7/7
        # total = 22/7
        assert _sum(rows, "service_frequency") == pytest.approx(22.0 / 7.0)

    def test_route_count_sums_per_stop(self):
        feed = GtfsStaticClient.parse_feed_zip(build_zip(GTFS_FILES))
        rows = GtfsStaticClient.compute_covariates(feed, bbox=NYC_BBOX)
        # S1 served by R1 (T1,T2) and R2 (T4) = 2 routes
        # S2 served by R1 (T1) and R2 (T3) = 2 routes
        assert _sum(rows, "route_count") == 4

    def test_no_bbox_keeps_all_valid_stops(self):
        feed = GtfsStaticClient.parse_feed_zip(build_zip(GTFS_FILES))
        rows = GtfsStaticClient.compute_covariates(feed)
        assert _sum(rows, "stop_density") == 3  # S1, S2, S3

    def test_covariate_dict_has_full_lineage_keys(self):
        feed = GtfsStaticClient.parse_feed_zip(build_zip(GTFS_FILES))
        rows = GtfsStaticClient.compute_covariates(feed, bbox=NYC_BBOX)
        assert rows
        row = rows[0]
        for key in ("h3_res7", "h3_res8", "h3_res9", "effective_h3", "effective_resolution"):
            assert key in row
        assert row["effective_h3"]
        assert row["effective_resolution"] in (7, 8, 9)

    def test_calendar_missing_defaults_to_daily(self):
        files = {k: v for k, v in GTFS_FILES.items() if k != "calendar.txt"}
        feed = GtfsStaticClient.parse_feed_zip(build_zip(files))
        rows = GtfsStaticClient.compute_covariates(feed, bbox=NYC_BBOX)
        # Without calendar every trip counts full-weight: 5 stop_times -> 5.0
        assert _sum(rows, "service_frequency") == pytest.approx(5.0)


class TestCatalogSelection:
    def test_select_feeds_for_bboxes_filters_by_overlap(self):
        catalog = [
            {"id": "mta", "locations": [{"bounding_box": {"min_lat": 40.0, "max_lat": 41.0, "min_lon": -74.5, "max_lon": -73.5}}]},
            {"id": "sf-muni", "locations": [{"bounding_box": {"min_lat": 37.0, "max_lat": 38.0, "min_lon": -123.0, "max_lon": -122.0}}]},
        ]
        hits = GtfsStaticClient.select_feeds_for_bboxes(catalog, [NYC_BBOX])
        assert [h["id"] for h in hits] == ["mta"]

    def test_no_bbox_returns_whole_catalog(self):
        catalog = [{"id": "a"}, {"id": "b"}]
        assert len(GtfsStaticClient.select_feeds_for_bboxes(catalog)) == 2

    def test_download_url_extraction(self):
        feed = {"urls": {"direct_download": "https://x.test/gtfs.zip", "static_current": "https://y.test/gtfs.zip"}}
        assert GtfsStaticClient.get_download_url(feed) == "https://x.test/gtfs.zip"
        feed2 = {"urls": {"static_current": "https://y.test/gtfs.zip"}}
        assert GtfsStaticClient.get_download_url(feed2) == "https://y.test/gtfs.zip"

    def test_provider_name(self):
        assert GtfsStaticClient.get_provider_name({"provider": {"name": "MTA"}}) == "MTA"
        assert GtfsStaticClient.get_provider_name({"id": "x"}) == "x"


class TestBboxHelpers:
    def test_in_bbox_inclusive_edges(self):
        assert _in_bbox(40.71, -73.99, NYC_BBOX)
        assert _in_bbox(41.5, -74.5, NYC_BBOX) is False
        assert _in_bbox(40.50, -74.26, NYC_BBOX)  # corner inclusive

    def test_bboxes_overlap(self):
        a = {"min_lat": 40.0, "max_lat": 41.0, "min_lon": -74.0, "max_lon": -73.0}
        b = {"min_lat": 40.5, "max_lat": 42.0, "min_lon": -74.5, "max_lon": -73.5}
        c = {"min_lat": 30.0, "max_lat": 31.0, "min_lon": -80.0, "max_lon": -79.0}
        assert _bboxes_overlap(a, b)
        assert not _bboxes_overlap(a, c)

    def test_feed_bbox_returns_first(self):
        feed = {"locations": [{"bounding_box": {"min_lat": 1, "max_lat": 2, "min_lon": 3, "max_lon": 4}}]}
        assert _feed_bbox(feed)["min_lat"] == 1.0
        assert _feed_bbox({"locations": []}) is None
