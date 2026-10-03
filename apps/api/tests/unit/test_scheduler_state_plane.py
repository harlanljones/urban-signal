"""Rows placed from declared State Plane columns (2026-10-02).

A spec can declare that its rows carry their points as projected
coordinates: the CRS and the two columns that hold each row's x and y
(``state_plane_*``). A poll converts the point of each row the client left
unplaced, before a parcel join or the metro clip, and a backfill does the
same. Worcester's work orders are a table with no geometry. Boston's
licences have no other coordinates, and the licence producer converted them
itself until now. Aurora's permits and licences and Tempe's crime reports
carry the columns beside their geometry, so only a row without geometry is
converted (none in each feed's newest 1,000 rows on 2026-10-02).
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_job_name

WORCESTER = get_job_name(FeedType.COMPLAINTS_311, CityId.WORCESTER)

# Outside Worcester's City Hall (42.26259, -71.80229), in Massachusetts State
# Plane feet.
CITY_HALL = {"X_Coordinate": 574340.05, "Y_coordinate": 2920859.95}


@pytest.fixture
def scheduler():
    with patch("src.producers.base_producer.BaseKafkaProducer"):
        sched = MunicipalIngestionScheduler(dlq_producer=MagicMock(), rate_limit_delay_seconds=0.0, dedup_capacity=1000)
    for producer in sched.producers.values():
        producer.producer = MagicMock()
    sched.state_file = None
    return sched


def test_a_spec_naming_the_crs_and_both_columns_places_its_rows(scheduler):
    meta = scheduler.job_metadata
    assert meta[WORCESTER]["state_plane"] == {"crs": "EPSG:2249", "x_col": "X_Coordinate", "y_col": "Y_coordinate"}
    assert meta[get_job_name(FeedType.SLA, CityId.BOSTON)]["state_plane"] == {
        "crs": "EPSG:2249", "x_col": "gpsx", "y_col": "gpsy",
    }
    assert meta[get_job_name(FeedType.PERMITS, CityId.AURORA)]["state_plane"] == {
        "crs": "EPSG:2232", "x_col": "PropX", "y_col": "PropY",
    }
    # Stockton's and Boulder's licences name their layers' CRS but no
    # columns, and most specs declare nothing.
    assert meta[get_job_name(FeedType.SLA, CityId.STOCKTON)]["state_plane"] == {}
    assert meta[get_job_name(FeedType.SLA, CityId.BOULDER)]["state_plane"] == {}
    assert meta[get_job_name(FeedType.COMPLAINTS_311, CityId.LEXINGTON)]["state_plane"] == {}


def test_only_a_row_the_client_left_unplaced_is_converted(scheduler):
    placed = {"Service_Request_ID": 1, **CITY_HALL, "latitude": 42.2626, "longitude": -71.8023}
    unplaced = {"Service_Request_ID": 2, **CITY_HALL}

    rows = scheduler._place_state_plane_rows(WORCESTER, [placed, unplaced])

    assert rows[0] is placed
    assert rows[1]["latitude"] == pytest.approx(42.26259, abs=1e-6)
    assert rows[1]["longitude"] == pytest.approx(-71.80229, abs=1e-6)
    # The client's row itself is left as it was.
    assert "latitude" not in unplaced


@pytest.mark.parametrize(
    "x, y",
    [(None, 2920859.95), ("", 2920859.95), ("n/a", 2920859.95), (574340.05, None)],
    ids=["no-x", "blank-x", "unreadable-x", "no-y"],
)
def test_a_row_whose_columns_are_empty_or_unreadable_stays_unplaced(scheduler, x, y):
    (row,) = scheduler._place_state_plane_rows(WORCESTER, [{"Service_Request_ID": 3, "X_Coordinate": x, "Y_coordinate": y}])

    assert "latitude" not in row and "longitude" not in row


def test_boston_licences_land_where_the_licence_producer_put_them(scheduler):
    # Boston's CKAN resource writes its State Plane feet as text.
    licence = {
        "license_num": "LB-990001", "license_type": "CV7 Malt Wine Liq by Zip Restricted", "issued": "2026-09-29",
        "business_name": "Example Kitchen, Inc.", "dba_name": "Example Kitchen", "address": "100 Example ST",
        "city": "Roxbury", "status": "Active", "gpsx": "764720.2549378872", "gpsy": "2940110.4333568066",
    }
    producer = scheduler.producers["sla"]
    before = producer.parse_socrata_row(licence, city_id="boston")

    (placed,) = scheduler._place_state_plane_rows(get_job_name(FeedType.SLA, CityId.BOSTON), [licence])
    after = producer.parse_socrata_row(placed, city_id="boston")

    assert before is not None and after is not None
    assert (after.latitude, after.longitude) == (before.latitude, before.longitude)
    assert after.latitude == pytest.approx(42.3151, abs=0.001)


def test_an_aurora_permit_without_geometry_now_publishes_at_its_columns_point(scheduler):
    # Aurora's producer tests pin that such a row parses to nothing; the
    # poll now places it first. PropX/PropY reproduce the layer's own
    # geometry to within a metre.
    permit = {
        "OBJECTID": 990001, "FolderRSN": 9900001, "Permit_": "26-9900001-000-00",
        "InDate": "2026-09-28T17:55:05+00:00", "FolderDesc": "Limited Building Permit", "FolderGroupDesc": "Building",
        "SubDesc": "Electrical Permit", "FolderCondition": "", "IssueDate": "2026-09-28T17:55:05+00:00",
        "valuation": "10170", "PropX": 3216536.71206905, "PropY": 1706269.44191606, "Address": "100 E EXAMPLE PL",
    }
    producer = scheduler.producers["permits"]
    producer.arcgis.paginate = MagicMock(return_value=[[permit]])
    producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": None})

    result = scheduler.poll_job(get_job_name(FeedType.PERMITS, CityId.AURORA))

    assert result["records_published"] == 1
    scheduler.dlq_producer.route_to_dlq.assert_not_called()
    event = producer.producer.produce.call_args.kwargs["payload"]
    assert event.latitude == pytest.approx(39.77000229037668, abs=2e-5)
    assert event.longitude == pytest.approx(-104.72968677729655, abs=2e-5)
