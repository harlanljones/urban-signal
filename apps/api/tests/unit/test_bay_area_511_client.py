"""Unit tests for US-442 Bay511Client (511.org regional GTFS datafeeds).

Network-free: catalog normalization and the multi-operator merge are pure;
``fetch_all_operator_feeds`` is exercised with injected ``catalog_fn``/
``download_fn`` fakes instead of real HTTP calls.
"""

import io
import zipfile

from src.producers.bay_area_511_client import Bay511Client


def build_zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, text)
    return buf.getvalue()


def _operator_gtfs(stop_prefix_lat: float) -> bytes:
    """A tiny synthetic single-operator GTFS zip using deliberately colliding ids."""
    files = {
        "stops.txt": f"stop_id,stop_name,stop_lat,stop_lon\n1,Main St,{stop_prefix_lat},-122.4\n",
        "routes.txt": "route_id,route_type\n1,3\n",
        "trips.txt": "trip_id,route_id,service_id\n1,1,WD\n",
        "stop_times.txt": "trip_id,stop_id,arrival_time\n1,1,07:30:00\n",
        "calendar.txt": (
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday\n"
            "WD,1,1,1,1,1,0,0\n"
        ),
    }
    return build_zip(files)


class TestParseCatalog:
    def test_standard_operator_feeds_shape(self):
        data = {
            "OperatorFeeds": [
                {
                    "Operator": {"Id": "BA", "Name": "BART"},
                    "OperatorFeed": [{"Uri": "https://x.test/bart.zip"}],
                },
                {
                    "Operator": {"Id": "SF", "Name": "SFMTA"},
                    "OperatorFeed": [{"Uri": "https://x.test/sfmta.zip"}],
                },
            ]
        }
        entries = Bay511Client.parse_catalog(data)
        assert len(entries) == 2
        assert entries[0] == {"operator_id": "BA", "operator_name": "BART", "url": "https://x.test/bart.zip"}

    def test_singular_operator_feed_dict_accepted(self):
        data = {
            "OperatorFeeds": [
                {"Operator": {"Id": "VTA", "Name": "VTA"}, "OperatorFeed": {"Uri": "https://x.test/vta.zip"}}
            ]
        }
        entries = Bay511Client.parse_catalog(data)
        assert entries == [{"operator_id": "VTA", "operator_name": "VTA", "url": "https://x.test/vta.zip"}]

    def test_bare_list_accepted(self):
        data = [{"Operator": {"Id": "AC", "Name": "AC Transit"}, "OperatorFeed": [{"Url": "https://x.test/ac.zip"}]}]
        entries = Bay511Client.parse_catalog(data)
        assert entries == [{"operator_id": "AC", "operator_name": "AC Transit", "url": "https://x.test/ac.zip"}]

    def test_entry_without_url_is_dropped(self):
        data = {"OperatorFeeds": [{"Operator": {"Id": "X", "Name": "X"}, "OperatorFeed": [{}]}]}
        assert Bay511Client.parse_catalog(data) == []

    def test_entry_without_feeds_is_dropped(self):
        data = {"OperatorFeeds": [{"Operator": {"Id": "X", "Name": "X"}}]}
        assert Bay511Client.parse_catalog(data) == []

    def test_missing_operator_name_falls_back_to_id(self):
        data = {"OperatorFeeds": [{"OperatorReference": "SM", "OperatorFeed": [{"Uri": "https://x.test/sm.zip"}]}]}
        entries = Bay511Client.parse_catalog(data)
        assert entries == [{"operator_id": "SM", "operator_name": "SM", "url": "https://x.test/sm.zip"}]


class TestMergeOperatorFeeds:
    def test_colliding_stop_ids_are_namespaced_by_operator(self):
        from src.producers.gtfs_static_client import GtfsStaticClient

        bart_feed = GtfsStaticClient.parse_feed_zip(_operator_gtfs(37.8))
        vta_feed = GtfsStaticClient.parse_feed_zip(_operator_gtfs(37.3))
        merged = Bay511Client.merge_operator_feeds({"BART": bart_feed, "VTA": vta_feed})

        stop_ids = {s[0] for s in merged["stops"]}
        assert stop_ids == {"BART:1", "VTA:1"}
        assert len(merged["stops"]) == 2

    def test_trip_stop_time_service_ids_stay_joinable_after_prefixing(self):
        from src.producers.gtfs_static_client import GtfsStaticClient

        bart_feed = GtfsStaticClient.parse_feed_zip(_operator_gtfs(37.8))
        merged = Bay511Client.merge_operator_feeds({"BART": bart_feed})

        trip = merged["trips"][0]
        stop_time = merged["stop_times"][0]
        calendar_row = merged["calendar"][0]
        assert trip["trip_id"] == stop_time["trip_id"] == "BART:1"
        assert trip["service_id"] == calendar_row["service_id"] == "BART:WD"
        assert trip["route_id"] == merged["routes"][0]["route_id"] == "BART:1"

    def test_route_carries_operator_field(self):
        from src.producers.gtfs_static_client import GtfsStaticClient

        bart_feed = GtfsStaticClient.parse_feed_zip(_operator_gtfs(37.8))
        merged = Bay511Client.merge_operator_feeds({"BART": bart_feed})
        assert merged["routes"][0]["operator"] == "BART"

    def test_merge_is_usable_by_transit_accessibility_scoring(self):
        from src.producers.gtfs_static_client import GtfsStaticClient
        from src.spatial.transit_accessibility import score_feed

        bart_feed = GtfsStaticClient.parse_feed_zip(_operator_gtfs(37.8))
        vta_feed = GtfsStaticClient.parse_feed_zip(_operator_gtfs(37.3))
        merged = Bay511Client.merge_operator_feeds({"BART": bart_feed, "VTA": vta_feed})
        rows = score_feed(merged)
        assert len(rows) >= 2  # both operators' stops produce scored hexes
        assert all(r["transit_connectivity_score"] > 0 for r in rows if r["stop_count"] > 0)

    def test_empty_input_yields_empty_shape(self):
        merged = Bay511Client.merge_operator_feeds({})
        assert merged == {"stops": [], "routes": [], "trips": [], "stop_times": [], "calendar": []}


class TestFetchAllOperatorFeeds:
    def test_pipeline_downloads_and_merges_each_operator(self):
        catalog = [
            {"operator_id": "BA", "operator_name": "BART", "url": "https://x.test/bart.zip"},
            {"operator_id": "VTA", "operator_name": "VTA", "url": "https://x.test/vta.zip"},
        ]
        zips = {
            "https://x.test/bart.zip": _operator_gtfs(37.8),
            "https://x.test/vta.zip": _operator_gtfs(37.3),
        }
        client = Bay511Client(api_key="test-key")
        merged = client.fetch_all_operator_feeds(
            catalog_fn=lambda: catalog,
            download_fn=lambda url: zips[url],
        )
        stop_ids = {s[0] for s in merged["stops"]}
        assert stop_ids == {"BART:1", "VTA:1"}

    def test_pipeline_with_empty_catalog(self):
        client = Bay511Client(api_key="test-key")
        merged = client.fetch_all_operator_feeds(catalog_fn=list, download_fn=lambda url: b"")
        assert merged["stops"] == []
