"""Tucson deeds from the Pima County Assessor's sales files (2026-10-02).

The Assessor publishes its affidavits of sale as one zipped CSV per sale
year (``SALE2026.ZIP``, member ``Sale2026.csv``), rebuilt nightly, each row a
parcel of a sale with its affidavit's sequence number, price, deed type and
recording date, and no names or addresses. A file holds the sales that
closed in its year, so a sale recorded after New Year sits in the year
before's file. Tucson reads this year's file and last year's, keeps the
sales recorded in the 90 days before each poll (4,319 county-wide on
2026-10-02), places each on its parcel's centroid and keeps the ones inside
the metro box.
"""

from datetime import UTC, date, datetime, timedelta
from functools import partial
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.producers import csv_client
from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset, get_job_name

# The sales file's header, in file order.
HEADER = (
    "Parcel,SequenceNum,SaleDate,SalePrice,PropertyType,IntendedUse,Deed,Financing,ValidationDescription,"
    "BuyerSellerRelated,Solar,PersonalProperty,PartialInterest,RecordingDate,ParcelUse"
)

FIELD_MAP = {
    "doc_id": ["sequencenum"],
    "recorded_date": ["recordingdate"],
    "document_amount": ["saleprice"],
    "bbl": ["parcel"],
    "doc_type": ["deed"],
}

WINDOW = "recordingdate >= CURRENT_DATE - INTERVAL '90' DAY AND recordingdate <= CURRENT_DATE"

PARCEL_LAYER = "https://gisdata.pima.gov/arcgis1/rest/services/GISOpenData/LandRecords/MapServer/0"


def _spec():
    return get_dataset(CityId.TUCSON, FeedType.DEEDS)


def _line(parcel: str, sequence: str, sale_month: str, price: str, deed: str, recorded: date) -> str:
    """A sales file row (synthetic values)."""
    return (
        f"{parcel},{sequence},{sale_month},{price},Single Family,Primary Residence,{deed},New Loan(s),"
        f"Good Sale,No,No,No,No,{recorded.isoformat()},0111"
    )


def _sales_zip(year: int, *lines: str) -> bytes:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("disclaim.txt", "Not a legal record of sale.")
        archive.writestr(f"Sale{year}.csv", "\r\n".join([HEADER, *lines]) + "\r\n")
    return buf.getvalue()


def test_tucson_reads_pima_countys_sales_file_for_each_year():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.csv_tucson_deeds_endpoint
    assert spec.endpoint == "https://www.asr.pima.gov/Downloads/Data/sales/{year}//SALE{year}.ZIP"
    assert spec.zip_member == "Sale{year}.csv"
    assert (spec.platform, spec.ingestion_mode) == ("csv", "snapshot")
    # The client reads this year's file and last year's.
    assert csv_client.yearly_files(spec.endpoint, spec.zip_member, today=date(2026, 10, 2)) == [
        ("https://www.asr.pima.gov/Downloads/Data/sales/2026//SALE2026.ZIP", "Sale2026.csv"),
        ("https://www.asr.pima.gov/Downloads/Data/sales/2025//SALE2025.ZIP", "Sale2025.csv"),
    ]
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False


def test_the_window_holds_ninety_days_of_recordings():
    spec = _spec()
    # Recording dates are written 2026-09-25 and compare as text.
    assert (spec.watermark_col, spec.watermark_format) == ("recordingdate", None)
    assert spec.where == WINDOW
    assert spec.order_by == "recordingdate DESC"


def test_the_request_names_its_columns():
    # The file holds no names or addresses; the poll keeps five of its fifteen
    # columns.
    assert _spec().select.split(",") == ["parcel", "sequencenum", "saleprice", "deed", "recordingdate"]


def test_each_parcel_of_a_sale_publishes_once():
    spec = _spec()
    # One affidavit can convey several parcels: 12,863 sequence numbers
    # covered the 14,165 rows of the 2026 file, every sequence number and
    # parcel pair its own, and no pair is in both files.
    assert (spec.id_keys, spec.composite_id) == (["sequencenum", "parcel"], True)


def test_each_sale_takes_its_parcels_centroid_and_the_box_keeps_the_city():
    spec = _spec()
    # The County's parcel centroids, asked for the parcel number alone: the
    # layer's mailing columns stay on the server.
    assert spec.parcel_join == {
        "parcel_layer": PARCEL_LAYER,
        "join_key": "PARCEL",
        "geometry_source": "centroid",
        "row_key": "parcel",
    }
    # 2,592 of the 4,319 sales in the window on 2026-10-02 lay elsewhere in
    # the county.
    assert spec.metro_clip is True


def test_the_cap_reads_the_whole_window_once_a_day():
    spec = _spec()
    # 4,319 sales in the window on 2026-10-02; the 90 days from 2026-02-18
    # held 6,873.
    assert spec.batch_limit == 10000
    assert spec.interval_seconds == 86400.0
    # The newest recording was a week old on 2026-10-02.
    assert spec.expected_cadence_days == 10


class TestTucsonDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @staticmethod
    def _row(**changes):
        """A sale as the CSV client and the parcel join hand it on."""
        return {
            "parcel": "199990010",
            "sequencenum": "20262689001",
            "saleprice": "294600",
            "deed": "Warranty Deed",
            "recordingdate": "2026-09-25",
            # The parcel's centroid, downtown.
            "latitude": 32.2226,
            "longitude": -110.9723,
            **changes,
        }

    def test_a_sale_is_published_at_its_parcels_centroid(self, deeds):
        event = deeds.parse_socrata_row(self._row(), city_id="tucson")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("tucson", "20262689001", "199990010")
        assert event.recorded_date.date().isoformat() == "2026-09-25"
        assert (event.document_amount, event.doc_type) == (294600.0, "WARRANTY DEED")
        assert (event.latitude, event.longitude) == (32.2226, -110.9723)
        assert event.h3_res9 is not None

    def test_a_sale_without_a_price_publishes_at_zero(self, deeds):
        # 43 of the 1,727 sales published on 2026-10-02 had no price or zero.
        event = deeds.parse_socrata_row(self._row(saleprice="", deed="Quit Claim Deed"), city_id="tucson")

        assert event is not None
        assert (event.document_amount, event.doc_type) == (0.0, "QUIT CLAIM DEED")


class TestTucsonPoll:
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

    def test_a_poll_reads_both_years_and_publishes_each_sale_its_parcel_places_in_the_box(
        self, scheduler, monkeypatch
    ):
        today = datetime.now(UTC).date()
        year = today.year
        monkeypatch.setattr(csv_client, "yearly_files", partial(csv_client.yearly_files, today=today))
        files = {
            year: _sales_zip(
                year,
                # One affidavit, two parcels.
                _line("199990010", f"{year}0009001", f"{year}09", "412500", "Warranty Deed", today - timedelta(days=5)),
                _line("199990011", f"{year}0009001", f"{year}09", "412500", "Warranty Deed", today - timedelta(days=5)),
                # Recorded before the window.
                _line("199990012", f"{year}0009002", f"{year}01", "188000", "Warranty Deed",
                      today - timedelta(days=200)),
            ),
            year - 1: _sales_zip(
                year - 1,
                # Closed last year and recorded since.
                _line("199990013", f"{year}0009003", f"{year - 1}12", "301000", "Warranty Deed",
                      today - timedelta(days=20)),
                # In Green Valley, south of the metro box.
                _line("199990014", f"{year}0009004", f"{year - 1}12", "265000", "Warranty Deed",
                      today - timedelta(days=30)),
                # A parcel the centroid layer lacks.
                _line("199990015", f"{year}0009005", f"{year - 1}11", "", "Quit Claim Deed",
                      today - timedelta(days=10)),
            ),
        }
        requested: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requested.append(request.url.path)
            return httpx.Response(200, content=next(files[y] for y in files if str(y) in request.url.path),
                                  request=request)

        producer = scheduler.producers["deeds"]
        producer.csv.http = httpx.Client(transport=httpx.MockTransport(handler))
        producer.arcgis.fetch_centroid_index = MagicMock(return_value={
            "199990010": (32.2226, -110.9723), "199990011": (32.2229, -110.9719),
            "199990013": (32.2904, -110.9512), "199990014": (31.8801, -110.9912),
        })
        job = get_job_name(FeedType.DEEDS, CityId.TUCSON)

        result = scheduler.poll_job(job)

        assert requested == [f"/Downloads/Data/sales/{year}//SALE{year}.ZIP",
                             f"/Downloads/Data/sales/{year - 1}//SALE{year - 1}.ZIP"]
        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (5, 3, 2)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.fetch_centroid_index.call_args.kwargs
        assert (kwargs["endpoint_url"], kwargs["join_key"], kwargs["where"]) == (PARCEL_LAYER, "PARCEL", None)
        assert set(kwargs["join_values"]) == {"199990010", "199990011", "199990013", "199990014", "199990015"}
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [(event.doc_id, event.bbl) for event in events] == [
            (f"{year}0009001", "199990010"), (f"{year}0009001", "199990011"), (f"{year}0009003", "199990013"),
        ]

        # The next day's poll reads the same window and publishes none of it again.
        result = scheduler.poll_job(job)

        assert (result["records_published"], result["duplicates_skipped"], result["outside_metro"]) == (0, 3, 2)
