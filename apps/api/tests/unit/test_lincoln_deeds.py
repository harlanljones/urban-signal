"""Lincoln deeds from the Lancaster County Assessor's sales (2026-10-02).

The City-County GIS server publishes the Assessor's property sales of the
last 12 months (3,980 on 2026-10-02), one point per sale with its instrument
number, parcel, price and recording date. Lincoln reads the sales recorded in
the 90 days before each poll (986 county-wide on 2026-10-02, the newest
recorded 2026-09-28) and keeps the ones inside the metro box. The County's
sales items on the Lincoln open data hub stop at 2018.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "InstNum", "PID", "InstType", "SalePrice", "RecordedDate"]

FIELD_MAP = {
    "doc_id": ["InstNum"],
    "recorded_date": ["RecordedDate"],
    "document_amount": ["SalePrice"],
    "bbl": ["PID"],
    "doc_type": ["InstType"],
}

WINDOW = "RecordedDate >= CURRENT_DATE - INTERVAL '90' DAY AND RecordedDate <= CURRENT_TIMESTAMP"

ORDER = "RecordedDate DESC, OBJECTID DESC"


def _spec():
    return get_dataset(CityId.LINCOLN, FeedType.DEEDS)


def _sale(**changes):
    """A recorded sale as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 3001,
        "InstNum": "2026099001",
        "PID": "1799999001000",
        "InstType": "WDEED",
        "SalePrice": 225000.0,
        "RecordedDate": "2026-09-28T00:00:00+00:00",
        "latitude": 40.7712,
        "longitude": -96.6519,
        **changes,
    }


def test_lincoln_reads_the_assessors_sales_on_the_city_county_server():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_lincoln_deeds_url
    assert spec.endpoint == (
        "https://gis.lincoln.ne.gov/public/rest/services/Assessor/PropertySales/FeatureServer/0"
    )
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 4000)
    assert spec.field_map == FIELD_MAP
    # Each sale is a point; the layer covers Lancaster County.
    assert spec.needs_geocode is False
    assert (spec.parcel_join, spec.metro_clip) == ({}, True)


def test_the_window_holds_ninety_days_of_recorded_sales():
    spec = _spec()
    assert spec.watermark_col == "RecordedDate"
    assert spec.where == WINDOW
    assert spec.order_by == ORDER


def test_the_request_names_its_columns_and_leaves_the_people_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The buyer, the seller, the layer's display name, the appraiser and the
    # photo stay on the server.
    assert not {"Name", "Grantor", "Grantee", "Appraiser", "PhotoPath"} & set(select)


def test_each_sale_publishes_once():
    # Each sale has its own instrument number; two of the 986 sales in the
    # window on 2026-10-02 were listed twice, parcel, price and day alike.
    assert (_spec().id_keys, _spec().composite_id) == (["InstNum"], False)


def test_the_cap_holds_the_busiest_window():
    spec = _spec()
    # 986 sales in the window on 2026-10-02; the 90 days from 2026-04-19 held
    # 1,371, the most the layer's 12 months hold.
    assert spec.batch_limit == 2500
    assert spec.interval_seconds == 21600.0
    # Sales reach the layer four to seven days after they are recorded.
    assert spec.expected_cadence_days == 7


class TestLincolnDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_point_with_its_parcel(self, deeds):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _sale().items() if key not in ("latitude", "longitude")}
        attributes["RecordedDate"] = 1790553600000  # 2026-09-28 00:00 UTC
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -96.6519, "y": 40.7712}},
            date_fields={"RecordedDate"},
        )

        event = deeds.parse_socrata_row(row, city_id="lincoln")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("lincoln", "2026099001", "1799999001000")
        assert event.recorded_date.isoformat() == "2026-09-28T00:00:00+00:00"
        assert (event.document_amount, event.doc_type) == (225000.0, "WDEED")
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (40.7712, -96.6519)
        assert event.h3_res9 is not None


class TestLincolnPoll:
    @pytest.fixture
    def scheduler(self):
        with patch("src.producers.base_producer.BaseKafkaProducer"):
            sched = MunicipalIngestionScheduler(
                dlq_producer=MagicMock(), rate_limit_delay_seconds=0.0, dedup_capacity=1000
            )
        for producer in sched.producers.values():
            producer.producer = MagicMock()
        sched.state_file = None
        return sched

    def test_a_poll_publishes_each_sale_inside_the_metro_once(self, scheduler):
        producer = scheduler.producers["deeds"]
        rows = [
            _sale(),
            # The same sale listed twice.
            _sale(OBJECTID=3002),
            # A sale in Hickman, south of the metro box.
            _sale(OBJECTID=3003, InstNum="2026099002", PID="1999999002000", SalePrice=310000.0,
                  latitude=40.6200, longitude=-96.6290),
            _sale(OBJECTID=3004, InstNum="2026099003", PID="1799999003000", InstType="TRDEED", SalePrice=94500.0,
                  RecordedDate="2026-09-24T00:00:00+00:00", latitude=40.8471, longitude=-96.6377),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("deeds_lincoln")

        assert (result["records_fetched"], result["records_published"]) == (4, 2)
        assert (result["duplicates_skipped"], result["outside_metro"]) == (1, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert kwargs["max_records"] == 2500
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == ["lincoln:2026099001", "lincoln:2026099003"]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_lincoln")

        assert (result["records_published"], result["duplicates_skipped"], result["outside_metro"]) == (0, 3, 1)
