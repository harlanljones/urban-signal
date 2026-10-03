"""Boulder deeds from the Boulder County Assessor's daily sales file (2026-10-02).

The Assessor rebuilds its data downloads at 4 a.m. every day. ``Sales.csv``
lists every sale in the county by account, with seven columns and none that
names a party: 752,371 rows, 50 MB. Boulder reads the sales dated in the 90
days before each poll, places each on its account's parcel in the County's
parcel layer and keeps the placed sales inside the metro box.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.producers.csv_client import CSVClient
from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["strap", "deednum", "tdate", "deed_type", "price"]

FIELD_MAP = {
    "doc_id": ["deednum"],
    "recorded_date": ["tdate"],
    "document_amount": ["price"],
    "bbl": ["strap"],
    "doc_type": ["deed_type"],
}

WINDOW = "tdate >= CURRENT_DATE - INTERVAL '90' DAY AND tdate <= CURRENT_DATE"

PARCELS = "https://maps.bouldercounty.org/arcgis/rest/services/PARCELS/PARCELS_OWNER/MapServer/0"

HEADER = '"strap","deedNum","Tdate","sales_cd","deed_type","price","status_cd"'


def _spec():
    return get_dataset(CityId.BOULDER, FeedType.DEEDS)


def _line(strap, deed, date, price, deed_type="WD", sales_cd="P"):
    """A line of ``Sales.csv`` (synthetic accounts and deed numbers)."""
    return f'"{strap}","{deed}","{date}","{sales_cd}","{deed_type}","{price}","A "'


def _file(lines):
    return ("\r\n".join([HEADER, *lines]) + "\r\n").encode()


def _day(days_ago):
    day = datetime.now(UTC).date() - timedelta(days=days_ago)
    return f"{day.month}/{day.day}/{day.year} 12:00:00 AM"


def test_boulder_reads_the_assessors_daily_sales_file():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.csv_boulder_deeds_endpoint
    assert spec.endpoint == "https://assessor.boco.solutions/ASR_PublicDataFiles/Sales.csv"
    assert (spec.platform, spec.ingestion_mode) == ("csv", "snapshot")
    # A plain file with a header: no zip member, comma-separated.
    assert (spec.zip_member, spec.delimiter, spec.columns) == (None, None, [])
    # Dates read '9/16/2026 12:00:00 AM'.
    assert (spec.watermark_col, spec.watermark_format) == ("tdate", "%m/%d/%Y %I:%M:%S %p")
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    # One download a day, rebuilt nightly; the dense sales ran to about two
    # weeks before 2026-10-02.
    assert (spec.interval_seconds, spec.expected_cadence_days) == (86400.0, 14)


def test_the_window_closes_at_today():
    spec = _spec()
    # Eight rows carry dates in the future, as far as 2057.
    assert spec.where == WINDOW
    assert spec.order_by == "tdate DESC"


def test_the_file_is_read_by_account_deed_and_date():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The qualification and status codes are not read.
    assert not {"sales_cd", "status_cd"} & set(select)


def test_each_sale_is_its_deed_and_account():
    spec = _spec()
    # A deed over several accounts repeats its number; the pair repeats for
    # none of the window's rows.
    assert (spec.id_keys, spec.composite_id) == (["deednum", "strap"], True)


def test_each_sale_takes_its_parcels_centroid_and_the_box_keeps_boulders():
    spec = _spec()
    # The join asks the layer for the account number alone; the owner and
    # mailing columns it also holds stay on the server.
    assert spec.parcel_join == {
        "parcel_layer": PARCELS, "join_key": "AccountNo", "geometry_source": "centroid", "row_key": "strap",
    }
    assert spec.metro_clip is True
    # 1,806 sales in the window on 2026-10-02; the 90 days from 2025-02-24
    # held 4,334, the most since October 2024.
    assert spec.batch_limit == 6000


def test_the_csv_client_reads_the_window_as_the_spec_asks():
    spec = _spec()
    payload = _file([
        _line("R9999001", "4999001", _day(4), "1700000"),
        _line("R9999002", "4999002", _day(0), "0", "QD", "U"),
        _line("R9999003", "4999003", _day(200), "150000"),
        _line("R9999004", "4999004", "9/20/2057 12:00:00 AM", "0"),
        _line("R9999005", "4999005", "", ""),
    ])
    client = CSVClient(httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=payload))))

    rows = [
        row
        for batch in client.paginate(
            spec.endpoint,
            where_clause=spec.where,
            order_by=spec.order_by,
            select=spec.select,
            watermark_col=spec.watermark_col,
            watermark_format=spec.watermark_format,
        )
        for row in batch
    ]

    assert [row["strap"] for row in rows] == ["R9999002", "R9999001"]
    assert all(set(row) == set(COLUMNS) for row in rows)


class TestBoulderDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_parcel_with_its_deed_type(self, deeds):
        row = {
            "strap": "R9999001",
            "deednum": "4999001",
            "tdate": "9/16/2026 12:00:00 AM",
            "deed_type": "WD",
            "price": "1700000",
            # The parcel join's centroid, near the Pearl Street Mall.
            "latitude": 40.0176,
            "longitude": -105.2797,
        }

        event = deeds.parse_socrata_row(row, city_id="boulder")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("boulder", "4999001", "R9999001")
        assert event.recorded_date.date().isoformat() == "2026-09-16"
        assert (event.document_amount, event.doc_type) == (1700000.0, "WD")
        assert (event.latitude, event.longitude) == (40.0176, -105.2797)
        assert event.h3_res9 is not None


class TestBoulderPoll:
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

    def test_a_poll_places_each_sale_on_its_parcel_and_keeps_the_metros(self, scheduler):
        """Through the real CSV and ArcGIS clients, with HTTP stubbed."""
        producer = scheduler.producers["deeds"]
        payload = _file([
            _line("R9999001", "4999001", _day(4), "1700000"),
            # The same deed over a second account.
            _line("R9999002", "4999001", _day(4), "1700000"),
            # A sale in Longmont, north-east of the box.
            _line("R9999003", "4999003", _day(12), "640000", "SW"),
            # An account the parcel layer does not hold.
            _line("R9999004", "4999004", _day(15), "0", "QD", "U"),
            _line("R9999005", "4999005", _day(200), "150000"),
        ])
        producer.csv.http = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=payload)))
        centroids = {
            "R9999001": (40.0176, -105.2797),
            "R9999002": (40.0181, -105.2790),
            "R9999003": (40.1672, -105.1019),
        }
        queries = []

        def answer(url, params):
            if not url.endswith("/query"):
                return {"fields": [{"name": "AccountNo", "type": "esriFieldTypeString"}], "objectIdField": "OBJECTID"}
            queries.append(params["where"])
            asked = [value.strip("'") for value in params["where"].split("(", 1)[1].rstrip(")").split(",")]
            return {"features": [
                {"attributes": {"AccountNo": key}, "geometry": {"x": centroids[key][1], "y": centroids[key][0]}}
                for key in asked if key in centroids
            ]}

        producer.arcgis._request_json = answer

        result = scheduler.poll_job("deeds_boulder")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (4, 2, 2)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        # Each account once, newest sale first, quoted: AccountNo is text.
        assert queries == ["AccountNo IN ('R9999001','R9999002','R9999003','R9999004')"]
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [(event.bbl, event.doc_id) for event in events] == [("R9999001", "4999001"), ("R9999002", "4999001")]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_boulder")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 2)
