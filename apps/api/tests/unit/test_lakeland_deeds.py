"""Lakeland deeds from the Polk County Property Appraiser's nightly sales extract (2026-10-02).

The Property Appraiser rebuilds its bulk files every night: the sales member
of ``ftp_sales.zip`` was stamped 04:02 on 2026-10-02. ``ftp_sales.txt`` lists
every sale recorded in the county, a line per parcel and sale, comma-separated
and quoted with a header: 3,034,532 lines, 518 MB unpacked. Two of its fifteen
columns name the parties, and the spec never selects them. Lakeland reads the
sales dated in the 90 days before each poll on the parcels whose numbers can
reach its metro box (3,464 of the county's 8,450 on 2026-10-02), places each on
its parcel's centroid in the City's parcel layer and keeps the placed sales
inside the box (1,885).
"""

import io
import zipfile
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.producers.csv_client import CSVClient
from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["parcel_id", "saledt", "price", "book", "page", "trns_dscr"]

FIELD_MAP = {
    "doc_id": ["parcel_id"],
    "recorded_date": ["saledt"],
    "document_amount": ["price"],
    "bbl": ["parcel_id"],
    "doc_type": ["trns_dscr"],
}

PARCELS_IN_REACH = "parcel_id >= '23' AND parcel_id < '26'"

WINDOW = "saledt >= CURRENT_DATE - INTERVAL '90' DAY AND saledt <= CURRENT_DATE"

PARCELS = "https://arcgis.lakelandgov.net/maps/rest/services/LandBase/Parcels/MapServer/10"

HEADER = [
    "PARCEL_ID", "SALE_ID", "LN_NUM", "SALEDT", "PRICE", "BOOK", "PAGE", "SALETYPE", "TRNS_CD", "TRNS_DSCR",
    "INSTRTYP", "INSTRTYP_DSCR", "GRANTOR", "GRANTEE", "FORECLOSURE",
]


def _spec():
    return get_dataset(CityId.LAKELAND, FeedType.DEEDS)


def _line(parcel, date, price, book, page, deed="WARRANTY DEED", code="W ", sale_id=1):
    """A line of ``ftp_sales.txt``: every field quoted, the parties synthetic."""
    values = [
        parcel, str(sale_id), str(sale_id + 4), date, price, book, page, "I", code, deed, "01", "01  Qualified",
        "GRANTOR A", "GRANTEE B", "N",
    ]
    return ",".join(f'"{value}"' for value in values)


def _extract(lines):
    """The nightly zip: the member sits in a folder, with CRLF line endings."""
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        header = ",".join(f'"{name}"' for name in HEADER)
        zf.writestr("FTP_CAMA/ftp_sales.txt", "\r\n".join([header, *lines]) + "\r\n")
    return archive.getvalue()


def _day(days_ago):
    return (datetime.now(UTC).date() - timedelta(days=days_ago)).strftime("%m/%d/%Y")


def test_lakeland_reads_the_property_appraisers_nightly_sales_extract():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.csv_lakeland_deeds_endpoint
    assert spec.endpoint == (
        "https://www.polkflpa.gov/FTPPage/downloader.ashx?filename=ftp_sales.zip&dir=%5CAppraisalData%5C"
    )
    assert (spec.platform, spec.ingestion_mode) == ("csv", "snapshot")
    # The archive nests the member in a folder; the client matches its name.
    assert (spec.zip_member, spec.delimiter) == ("ftp_sales.txt", None)
    assert (spec.watermark_col, spec.watermark_format) == ("saledt", "%m/%d/%Y")
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    # One download a day, rebuilt nightly. The newest sale was eight days old
    # on 2026-10-02, and sales arrive up to weeks after their date.
    assert (spec.interval_seconds, spec.expected_cadence_days) == (86400.0, 14)


def test_the_window_closes_at_today_on_the_parcels_that_reach_the_box():
    spec = _spec()
    # A Polk parcel number starts with its range and township. On 2026-10-02
    # each of the City's 89,769 parcels touching the box started 23, 24 or 25,
    # and the 11,315 others it holds lie north-west and east of the box. The
    # parcel test runs first, so the other 59% of rows skip the date parse,
    # and the join asks about 3,464 parcels instead of 8,450.
    assert spec.where == f"{PARCELS_IN_REACH} AND {WINDOW}"
    assert spec.order_by == "saledt DESC"


def test_the_extract_is_read_without_the_parties():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The grantor and grantee are names; the sale and line numbers and the
    # qualification codes are not read either.
    assert not {"grantor", "grantee"} & set(select)


def test_each_deed_is_its_parcel_date_book_and_page():
    spec = _spec()
    # 222 of the 8,450 lines dated in the window on 2026-10-02 share a parcel
    # and a date with another, and a deed's book and page repeat across its
    # parcels; the four together repeat for none.
    assert (spec.id_keys, spec.composite_id) == (["parcel_id", "saledt", "book", "page"], True)


def test_each_sale_takes_its_parcels_centroid_and_the_box_keeps_lakelands():
    spec = _spec()
    assert spec.parcel_join == {
        "parcel_layer": PARCELS, "join_key": "PARCELID", "geometry_source": "centroid", "row_key": "parcel_id",
    }
    assert spec.metro_clip is True
    # 3,464 sales in reach in the window on 2026-10-02, while the latest weeks
    # were still arriving; the 90 days from 2025-02-17 held 5,272, the most
    # since October 2024.
    assert spec.batch_limit == 8000


def test_the_csv_client_reads_the_window_as_the_spec_asks():
    spec = _spec()
    payload = _extract([
        _line("242816999999001010", _day(4), "255000", "13710", "1201"),
        _line("242816999999001020", _day(0), "309000", "13712", "0101"),
        _line("242816999999001030", _day(200), "150000", "13400", "0001"),
        _line("242816999999001040", "", "0", "", ""),
        # Haines City, and the county's north-west corner: out of reach.
        _line("272711999999001050", _day(2), "420000", "13711", "0202"),
        _line("222705999999001060", _day(3), "98000", "13711", "0303"),
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
            zip_member=spec.zip_member,
        )
        for row in batch
    ]

    assert [row["parcel_id"] for row in rows] == ["242816999999001020", "242816999999001010"]
    # The parties never leave the reader.
    assert all(set(row) == set(COLUMNS) for row in rows)


class TestLakelandDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_parcel_with_its_deed_type(self, deeds):
        row = {
            "parcel_id": "242816999999001010",
            "saledt": "09/22/2026",
            "price": "255000",
            "book": "13710",
            "page": "1201",
            "trns_dscr": "WARRANTY DEED",
            # The parcel join's centroid, near Lake Morton.
            "latitude": 28.0357,
            "longitude": -81.9493,
        }

        event = deeds.parse_socrata_row(row, city_id="lakeland")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("lakeland", "242816999999001010", "242816999999001010")
        assert event.recorded_date.date().isoformat() == "2026-09-22"
        assert (event.document_amount, event.doc_type) == (255000.0, "WARRANTY DEED")
        assert (event.latitude, event.longitude) == (28.0357, -81.9493)
        assert event.h3_res9 is not None


class TestLakelandPoll:
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
        payload = _extract([
            _line("242816999999001010", _day(4), "255000", "13710", "1201"),
            # A corrective deed for the same parcel on the same day.
            _line("242816999999001010", _day(4), "100", "13710", "1205", "CORRECTIVE DEED", "C ", sale_id=2),
            # A parcel in Polk City, north of the box.
            _line("252705999999002010", _day(12), "189000", "13702", "1010"),
            # A parcel in reach that the City's layer does not hold.
            _line("253020999999003010", _day(15), "0", "13700", "0500", "QUIT CLAIM", "Q "),
            # A parcel in Winter Haven, out of reach: never read.
            _line("262829999999006010", _day(9), "275000", "13705", "0700"),
            _line("242826999999004010", _day(30), "309000", "13680", "0101"),
            _line("242816999999005010", _day(200), "150000", "13400", "0001"),
        ])
        producer.csv.http = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=payload)))
        centroids = {
            "242816999999001010": (28.0357, -81.9493),
            "252705999999002010": (28.1825, -81.8240),
            "242826999999004010": (27.9861, -81.9590),
        }
        queries = []

        def answer(url, params):
            if not url.endswith("/query"):
                return {"fields": [{"name": "PARCELID", "type": "esriFieldTypeString"}], "objectIdField": "OBJECTID"}
            queries.append(params["where"])
            asked = [value.strip("'") for value in params["where"].split("(", 1)[1].rstrip(")").split(",")]
            return {"features": [
                {"attributes": {"PARCELID": parcel}, "geometry": {"x": centroids[parcel][1], "y": centroids[parcel][0]}}
                for parcel in asked if parcel in centroids
            ]}

        producer.arcgis._request_json = answer

        result = scheduler.poll_job("deeds_lakeland")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (5, 3, 2)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        # Each parcel in reach once, newest sale first, quoted: PARCELID is a
        # text column.
        assert queries == [
            "PARCELID IN ('242816999999001010','252705999999002010','253020999999003010','242826999999004010')"
        ]
        # Both deeds of the first parcel publish: their pages differ.
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [(event.bbl, event.doc_type, event.document_amount) for event in events] == [
            ("242816999999001010", "WARRANTY DEED", 255000.0),
            ("242816999999001010", "CORRECTIVE DEED", 100.0),
            ("242826999999004010", "WARRANTY DEED", 309000.0),
        ]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_lakeland")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 3)
