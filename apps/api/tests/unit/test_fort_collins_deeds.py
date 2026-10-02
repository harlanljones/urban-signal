"""Fort Collins deeds from the Larimer County Assessor's public sales table (2026-10-02).

The Assessor publishes its sales table as one CSV on Google Cloud Storage,
rebuilt overnight: every sale in the county by account, 661,961 rows, 101 MB.
Two of its eleven columns name the grantor and grantee, and the spec never
selects them. Fort Collins reads the sales dated in the 90 days before each
poll, places each on its account's parcel in the County's parcel layer and
keeps the placed sales inside the metro box.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.producers.csv_client import CSVClient
from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["parcelno", "accountno", "schedulenum", "receptionno", "saledate", "saleprice", "deeddescription"]

FIELD_MAP = {
    "doc_id": ["receptionno"],
    "recorded_date": ["saledate"],
    "document_amount": ["saleprice"],
    "bbl": ["parcelno"],
    "doc_type": ["deeddescription"],
}

WINDOW = "saledate >= CURRENT_DATE - INTERVAL '90' DAY AND saledate <= CURRENT_DATE"

PARCELS = "https://maps1.larimer.org/arcgis/rest/services/MapServices/Parcels/MapServer/3"

HEADER = (
    "PARCELNO,ACCOUNTNO,SCHEDULENUM,RECEPTIONNO,GRANTOR,GRANTEE,SALEPRICE,SALEDATE,DEEDCODE,DEEDDESCRIPTION,RUNDATE"
)


def _spec():
    return get_dataset(CityId.FORT_COLLINS, FeedType.DEEDS)


def _line(parcel, schedule, reception, date, price, code="SWD", deed="Special Warranty Deed", account="R"):
    """A line of the sales table: unquoted, the parties synthetic."""
    return ",".join([
        parcel, account + schedule, schedule, reception, "GRANTOR A", "GRANTEE B", price, date, code, deed,
        "2026-10-01 05:30:06",
    ])


def _file(lines):
    return ("\n".join([HEADER, *lines]) + "\n").encode()


def _day(days_ago, time="00:00:00"):
    return f"{datetime.now(UTC).date() - timedelta(days=days_ago)} {time}"


def test_fort_collins_reads_the_assessors_public_sales_table():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.csv_fort_collins_deeds_endpoint
    assert spec.endpoint == "https://storage.googleapis.com/lc-public/asr/assessor-public-sales.csv"
    assert (spec.platform, spec.ingestion_mode) == ("csv", "snapshot")
    assert (spec.watermark_col, spec.watermark_format) == ("saledate", "%Y-%m-%d %H:%M:%S")
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    # Sales reach the table weeks after their date: the newest was 24 days
    # old on 2026-10-02.
    assert (spec.interval_seconds, spec.expected_cadence_days) == (86400.0, 21)


def test_the_window_closes_at_today():
    spec = _spec()
    assert spec.where == WINDOW
    assert spec.order_by == "saledate DESC"


def test_the_table_is_read_without_the_parties():
    select = _spec().select.split(",")
    assert select == COLUMNS
    assert not {"grantor", "grantee"} & set(select)


def test_each_sale_is_its_reception_and_account():
    spec = _spec()
    # A deed over several accounts repeats its reception number; the pair
    # repeats for none of the window's rows.
    assert (spec.id_keys, spec.composite_id) == (["receptionno", "accountno"], True)


def test_each_sale_takes_its_accounts_parcel_and_the_box_keeps_fort_collinss():
    spec = _spec()
    # The schedule number is the account without its letter, and the layer
    # holds one parcel for each; condominium units share a parcel number.
    assert spec.parcel_join == {
        "parcel_layer": PARCELS, "join_key": "SCHEDNUM", "geometry_source": "centroid", "row_key": "schedulenum",
    }
    assert spec.metro_clip is True
    # 2,597 sales in the window on 2026-10-02; the 90 days from 2025-03-31
    # held 4,337, the most since October 2024.
    assert spec.batch_limit == 6000


def test_the_csv_client_reads_the_window_as_the_spec_asks():
    spec = _spec()
    payload = _file([
        _line("9999000001", "9999001", "20269999001", _day(4, "15:47:52"), "525000"),
        _line("9999000002", "0999002", "20269999002", _day(1), "0", "QC", "Quit Claim"),
        _line("9999000003", "9999003", "20259999003", _day(200), "410000"),
        _line("9999000004", "9999004", "20269999004", _day(0, "13:07:43"), "389000"),
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

    # Today's sale with a time of day waits for tomorrow's window.
    assert [row["schedulenum"] for row in rows] == ["0999002", "9999001"]
    # The parties never leave the reader.
    assert all(set(row) == set(COLUMNS) for row in rows)


class TestFortCollinsDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_parcel_with_its_deed_type(self, deeds):
        row = {
            "parcelno": "9999000001",
            "accountno": "R9999001",
            "schedulenum": "9999001",
            "receptionno": "20269999001",
            "saledate": "2026-09-04 15:47:52",
            "saleprice": "525000",
            "deeddescription": "Special Warranty Deed",
            # The parcel join's centroid, in Old Town.
            "latitude": 40.5872,
            "longitude": -105.0776,
        }

        event = deeds.parse_socrata_row(row, city_id="fort_collins")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("fort_collins", "20269999001", "9999000001")
        assert event.recorded_date.date().isoformat() == "2026-09-04"
        assert (event.document_amount, event.doc_type) == (525000.0, "SPECIAL WARRANTY DEED")
        assert (event.latitude, event.longitude) == (40.5872, -105.0776)
        assert event.h3_res9 is not None


class TestFortCollinsPoll:
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
            _line("9999000001", "9999001", "20269999001", _day(4), "525000"),
            # A condominium unit in the same building: its own schedule number.
            _line("9999000001", "0999002", "20269999002", _day(5), "312000"),
            # A sale in Loveland, south of the box.
            _line("9999000003", "9999003", "20269999003", _day(12), "455000", "WD", "Warranty Deed"),
            # A mobile home the parcel layer does not hold.
            _line("9999000004", "9999004", "20269999004", _day(15), "45000", "VOA", "Verification of Application", "M"),
            _line("9999000005", "9999005", "20259999005", _day(200), "410000"),
        ])
        producer.csv.http = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=payload)))
        centroids = {
            "9999001": (40.5872, -105.0776),
            "0999002": (40.5873, -105.0775),
            "9999003": (40.3978, -105.0750),
        }
        queries = []

        def answer(url, params):
            if not url.endswith("/query"):
                return {"fields": [{"name": "SCHEDNUM", "type": "esriFieldTypeString"}], "objectIdField": "OBJECTID"}
            queries.append(params["where"])
            asked = [value.strip("'") for value in params["where"].split("(", 1)[1].rstrip(")").split(",")]
            return {"features": [
                {"attributes": {"SCHEDNUM": key}, "geometry": {"x": centroids[key][1], "y": centroids[key][0]}}
                for key in asked if key in centroids
            ]}

        producer.arcgis._request_json = answer

        result = scheduler.poll_job("deeds_fort_collins")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (4, 2, 2)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        # Quoted, so a schedule number keeps its leading zero.
        assert queries == ["SCHEDNUM IN ('9999001','0999002','9999003','9999004')"]
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [(event.doc_id, event.latitude) for event in events] == [("20269999001", 40.5872), ("20269999002", 40.5873)]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_fort_collins")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 2)
