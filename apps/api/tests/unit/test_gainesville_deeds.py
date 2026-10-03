"""Gainesville deeds from the Alachua County Property Appraiser's nightly extract (2026-10-02).

The Property Appraiser rebuilds ``ACPA_CAMAData.zip`` every night (07:27 GMT
on 2026-10-01 and again on 2026-10-02). Its ``Sales.txt`` lists every sale
recorded in the county, a line per parcel, tab-delimited with a header and no
party names: 510,529 lines. Gainesville reads the sales dated in the 90 days
before each poll (2,486 on 2026-10-02), places each on its parcel's centroid
in the Property Appraiser's parcel layer and keeps the placed sales inside its
metro box (1,556).
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

COLUMNS = ["parcel", "prop_id", "sale_date", "sale_price", "sale_book", "sale_page", "sale_deed_type"]

FIELD_MAP = {
    "doc_id": ["parcel"],
    "recorded_date": ["sale_date"],
    "document_amount": ["sale_price"],
    "bbl": ["parcel"],
    "doc_type": ["sale_deed_type"],
}

WINDOW = "sale_date >= CURRENT_DATE - INTERVAL '90' DAY AND sale_date <= CURRENT_DATE"

PARCELS = "https://services.arcgis.com/cNo3jpluyt69V8Ek/arcgis/rest/services/PublicParcel/FeatureServer/0"

HEADER = [
    "Parcel", "prop_id", "Sale_Line_Num", "Sale_Date", "Sale_Price", "Sale_Vac_Imp", "Sale_Qualified",
    "Sale_Book", "Sale_Page", "Sale_Deed_Type", "DOR_Qual_Code",
]


def _spec():
    return get_dataset(CityId.GAINESVILLE, FeedType.DEEDS)


def _line(parcel, prop_id, date, price, book, page, deed, line_num=0):
    """A line of ``Sales.txt``: book, page and deed type are space-padded."""
    return "\t".join([
        parcel, str(prop_id), str(line_num), date, price, "No", "Q",
        f"{book:<20}", f"{page:<20}", f"{deed:<10}", "01-Qualified Examina of Deed",
    ])


def _extract(lines):
    """The nightly zip, its other members aside, with CRLF line endings."""
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Sales.txt", "\r\n".join(["\t".join(HEADER), *lines]) + "\r\n")
        zf.writestr("Owners.txt", "never read\r\n")
    return archive.getvalue()


def _day(days_ago):
    return (datetime.now(UTC).date() - timedelta(days=days_ago)).isoformat()


def test_gainesville_reads_the_property_appraisers_nightly_extract():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.csv_gainesville_deeds_endpoint
    assert spec.endpoint == "https://s3.amazonaws.com/acpa.cama/ACPA_CAMAData.zip"
    assert (spec.platform, spec.ingestion_mode) == ("csv", "snapshot")
    assert (spec.zip_member, spec.delimiter) == ("Sales.txt", "\t")
    assert (spec.watermark_col, spec.watermark_format) == ("sale_date", "%Y-%m-%d")
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    # One download a day, rebuilt nightly; sales arrive a week or two late.
    assert (spec.interval_seconds, spec.expected_cadence_days) == (86400.0, 7)


def test_the_window_closes_at_today():
    spec = _spec()
    # The upper bound keeps out the one sale keyed for 2079.
    assert spec.where == WINDOW
    assert spec.order_by == "sale_date DESC"


def test_the_extract_names_its_columns():
    # Sales.txt carries no party names; the line number and qualification
    # codes are not read.
    assert _spec().select.split(",") == COLUMNS


def test_each_deed_is_its_parcel_date_book_and_page():
    spec = _spec()
    # 125 lines of the 2,486 dated in the window on 2026-10-02 share a parcel
    # and a date with another; the line number renumbers when a parcel sells.
    assert (spec.id_keys, spec.composite_id) == (["parcel", "sale_date", "sale_book", "sale_page"], True)


def test_each_sale_takes_its_parcels_centroid_and_the_box_keeps_gainesvilles():
    spec = _spec()
    assert spec.parcel_join == {
        "parcel_layer": PARCELS, "join_key": "Prop_ID", "geometry_source": "centroid", "row_key": "prop_id",
    }
    assert spec.metro_clip is True
    # 2,486 sales in the window on 2026-10-02; the 90 days to 2025-08-26 held
    # 3,484, the most in two years.
    assert spec.batch_limit == 6000


def test_the_csv_client_reads_the_window_as_the_spec_asks():
    spec = _spec()
    payload = _extract([
        _line("09999-001-001", 900001, _day(4), "255000", "5293", "2737", "WD"),
        _line("09999-001-002", 900002, _day(0), "309000", "5294", "0101", "WD"),
        _line("09999-001-003", 900003, _day(200), "150000", "5100", "0001", "WD"),
        _line("09999-001-004", 900004, "2079-08-24", "120000", "5200", "0002", "WD"),
        _line("09999-001-005", 900005, "", "0", "", "", "WD"),
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
            delimiter=spec.delimiter,
        )
        for row in batch
    ]

    assert [row["parcel"] for row in rows] == ["09999-001-002", "09999-001-001"]
    assert all(set(row) == set(COLUMNS) for row in rows)
    assert rows[0]["sale_deed_type"] == "WD        "


class TestGainesvilleDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_parcel_with_its_deed_type(self, deeds):
        row = {
            "parcel": "09999-001-001",
            "prop_id": "900001",
            "sale_date": "2026-09-28",
            "sale_price": "255000",
            "sale_book": "5293                ",
            "sale_page": "2737                ",
            "sale_deed_type": "WD        ",
            # The parcel join's centroid, near the University of Florida.
            "latitude": 29.6516,
            "longitude": -82.3248,
        }

        event = deeds.parse_socrata_row(row, city_id="gainesville")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("gainesville", "09999-001-001", "09999-001-001")
        assert event.recorded_date.date().isoformat() == "2026-09-28"
        assert event.document_amount == 255000.0
        # The extract pads its codes to ten characters.
        assert event.doc_type == "WD"
        assert (event.latitude, event.longitude) == (29.6516, -82.3248)
        assert event.h3_res9 is not None


class TestGainesvillePoll:
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
            _line("09999-001-001", 900001, _day(4), "255000", "5293", "2737", "WD"),
            # A corrective deed for the same parcel on the same day.
            _line("09999-001-001", 900001, _day(4), "100", "5293", "2741", "QD", line_num=1),
            _line("09999-001-002", 900002, _day(30), "309000", "5280", "0101", "WD"),
            # A parcel in High Springs, north-west of the box.
            _line("09999-001-003", 900003, _day(12), "189000", "5290", "1010", "WD"),
            # A parcel the layer does not hold.
            _line("09999-001-004", 900004, _day(15), "0", "5289", "0500", "MS"),
            _line("09999-001-005", 900005, _day(200), "150000", "5100", "0001", "WD"),
        ])
        producer.csv.http = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=payload)))
        centroids = {900001: (29.6516, -82.3248), 900002: (29.6889, -82.3911), 900003: (29.8269, -82.5965)}
        queries = []

        def answer(url, params):
            if not url.endswith("/query"):
                return {"fields": [{"name": "Prop_ID", "type": "esriFieldTypeInteger"}], "objectIdField": "OBJECTID"}
            queries.append(params["where"])
            asked = [int(value) for value in params["where"].split("(", 1)[1].rstrip(")").split(",")]
            return {"features": [
                {"attributes": {"Prop_ID": prop_id}, "geometry": {"x": centroids[prop_id][1], "y": centroids[prop_id][0]}}
                for prop_id in asked if prop_id in centroids
            ]}

        producer.arcgis._request_json = answer

        result = scheduler.poll_job("deeds_gainesville")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (5, 3, 2)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        # Each parcel once, newest sale first, as a number: Prop_ID is an
        # integer column.
        assert queries == ["Prop_ID IN (900001,900003,900004,900002)"]
        # Both deeds of the first parcel publish: their book and page differ.
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [(event.bbl, event.doc_type, event.document_amount) for event in events] == [
            ("09999-001-001", "WD", 255000.0), ("09999-001-001", "QD", 100.0), ("09999-001-002", "WD", 309000.0),
        ]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_gainesville")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 3)
