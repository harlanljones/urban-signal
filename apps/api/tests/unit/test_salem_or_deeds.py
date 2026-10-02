"""Salem OR deeds from the Marion County Assessor's sales file for the year (2026-10-02).

The Assessor publishes one sales file a year, rebuilt by an automated
process: ``2026SalesData.csv`` held 6,481 rows on 2026-10-02, a row per sale,
account and situs. Its last four columns name the grantor and grantee and give
their addresses, and the spec never selects them. Salem reads the sales dated
in the 90 days before each poll, places each on its taxlot in the Assessor's
parcel layer and keeps the placed sales inside the metro box.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.producers.csv_client import CSVClient
from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset, resolve_endpoint

COLUMNS = ["sale_id", "account_number", "map_taxlot", "sale_date", "sale_price", "deed_type_code_description"]

FIELD_MAP = {
    "doc_id": ["sale_id"],
    "recorded_date": ["sale_date"],
    "document_amount": ["sale_price"],
    "bbl": ["map_taxlot"],
    "doc_type": ["deed_type_code_description"],
}

WINDOW = "sale_date >= CURRENT_DATE - INTERVAL '90' DAY AND sale_date <= CURRENT_DATE"

FILES = "https://apps.co.marion.or.us/AO/PropertySalesData/{}SalesData.csv"

PARCELS = "https://services3.arcgis.com/SXXjryU22GsO8OEC/arcgis/rest/services/Parcels/FeatureServer/0"

# The file's own column names, less the ones these tests do not need.
HEADER = [
    "Sale ID", "Deed Type Code Description", "Account Number", "Map Taxlot", "Code Area for Fragment(s) (Land)",
    "Sale Price", "Sale Date", "Situs Address", "Grantor (Seller) Name", "Grantor (Seller) Address",
    "Grantee (Buyer) Name", "Grantee (Buyer) Address",
]


def _spec():
    return get_dataset(CityId.SALEM_OR, FeedType.DEEDS)


def _line(sale, account, taxlot, date, price, deed="DEED", code_area="24000", situs="100 EXAMPLE ST NE"):
    """A line of the year's sales file: every field quoted, the parties synthetic."""
    values = [sale, deed, account, taxlot, code_area, price, date, situs, "GRANTOR A", "ADDRESS A", "GRANTEE B", "ADDRESS B"]
    return ",".join(f'"{value}"' for value in values)


def _file(lines):
    header = ",".join(f'"{name}"' for name in HEADER)
    return ("\r\n".join([header, *lines]) + "\r\n").encode()


def _day(days_ago):
    return (datetime.now(UTC).date() - timedelta(days=days_ago)).strftime("%m/%d/%Y")


def test_salem_reads_the_assessors_sales_file_for_the_year():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.csv_salem_or_deeds_endpoint
    assert spec.endpoint == FILES.format(2026)
    assert (spec.platform, spec.ingestion_mode) == ("csv", "snapshot")
    assert (spec.watermark_col, spec.watermark_format) == ("sale_date", "%m/%d/%Y")
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    # The file was rebuilt at 06:00 on 2026-10-02; its dense sales ran to
    # 2026-09-18.
    assert (spec.interval_seconds, spec.expected_cadence_days) == (86400.0, 14)


def test_the_year_turns_to_the_next_file_and_falls_back_while_it_is_missing():
    from datetime import date

    spec = _spec()
    assert spec.endpoint_by_year == {"2026": FILES.format(2026), "2027": FILES.format(2027)}
    assert resolve_endpoint(spec, today=date(2026, 12, 31)) == FILES.format(2026)
    assert resolve_endpoint(spec, today=date(2027, 1, 1)) == FILES.format(2027)
    # Until the county writes the new year's file, the poll reads the old one.
    assert spec.fallback_endpoints == [FILES.format(2026)]


def test_the_window_closes_at_today():
    spec = _spec()
    # Three sales were dated in November and December 2026.
    assert spec.where == WINDOW
    assert spec.order_by == "sale_date DESC"


def test_the_file_is_read_without_the_parties_or_the_situs():
    select = _spec().select.split(",")
    assert select == COLUMNS
    assert not {
        "grantor_seller_name", "grantor_seller_address", "grantee_buyer_name", "grantee_buyer_address", "situs_address",
    } & set(select)


def test_each_sale_is_its_sale_and_account():
    spec = _spec()
    # A sale repeats on a line per situs and code area of each account: 342
    # of the 1,544 lines dated in the window on 2026-10-02 repeated a sale and
    # an account, and publish once.
    assert (spec.id_keys, spec.composite_id) == (["sale_id", "account_number"], True)


def test_each_sale_takes_its_taxlots_centroid_and_the_box_keeps_salems():
    spec = _spec()
    assert spec.parcel_join == {
        "parcel_layer": PARCELS, "join_key": "TAXLOT", "geometry_source": "centroid", "row_key": "map_taxlot",
    }
    assert spec.metro_clip is True
    # 1,544 lines in the window on 2026-10-02; the 90 days from 2026-04-20
    # held 3,092, the most since January 2025.
    assert spec.batch_limit == 5000


def test_the_csv_client_reads_the_window_as_the_spec_asks():
    spec = _spec()
    payload = _file([
        _line("99001", "999001", "072W99AA00100", _day(4), "416,000"),
        _line("99002", "999002", "072W99AA00200", _day(0), "0", ""),
        _line("99003", "999003", "072W99AA00300", _day(200), "150,000"),
        _line("99004", "999004", "072W99AA00400", _day(-60), "389,000"),
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

    assert [row["sale_id"] for row in rows] == ["99002", "99001"]
    # The parties and the situs never leave the reader.
    assert all(set(row) == set(COLUMNS) for row in rows)


class TestSalemDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_taxlot(self, deeds):
        row = {
            "sale_id": "99001",
            "account_number": "999001",
            "map_taxlot": "072W99AA00100",
            "sale_date": "09/17/2026",
            "sale_price": "416,000",
            "deed_type_code_description": "DEED",
            # The parcel join's centroid, near the Capitol Mall.
            "latitude": 44.9386,
            "longitude": -123.0302,
        }

        event = deeds.parse_socrata_row(row, city_id="salem_or")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("salem_or", "99001", "072W99AA00100")
        assert event.recorded_date.date().isoformat() == "2026-09-17"
        # The price carries a thousands separator.
        assert (event.document_amount, event.doc_type) == (416000.0, "DEED")
        assert (event.latitude, event.longitude) == (44.9386, -123.0302)
        assert event.h3_res9 is not None

    def test_a_sale_without_a_deed_type_is_a_deed(self, deeds):
        row = {"sale_id": "99002", "map_taxlot": "072W99AA00200", "sale_date": "09/17/2026", "sale_price": "0",
               "deed_type_code_description": "", "latitude": 44.9386, "longitude": -123.0302}

        event = deeds.parse_socrata_row(row, city_id="salem_or")

        assert event is not None
        assert event.doc_type == "DEED"


class TestSalemPoll:
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

    def test_a_poll_places_each_sale_on_its_taxlot_and_keeps_the_metros(self, scheduler):
        """Through the real CSV and ArcGIS clients, with HTTP stubbed."""
        producer = scheduler.producers["deeds"]
        payload = _file([
            _line("99001", "999001", "072W99AA00100", _day(4), "416,000"),
            # The same sale and account on a second code area: one sale.
            _line("99001", "999001", "072W99AA00100", _day(4), "416,000", code_area="24001"),
            # A sale in Woodburn, north-east of the box.
            _line("99003", "999003", "051W99AA00300", _day(12), "389,000"),
            # A taxlot the parcel layer does not hold yet.
            _line("99004", "999004", "073W99AA00400", _day(15), "0", "Trustee's Deed"),
            _line("99005", "999005", "072W99AA00500", _day(200), "150,000"),
        ])
        requested = []

        def download(request):
            requested.append(str(request.url))
            return httpx.Response(200, content=payload)

        producer.csv.http = httpx.Client(transport=httpx.MockTransport(download))
        centroids = {"072W99AA00100": (44.9386, -123.0302), "051W99AA00300": (45.1440, -122.8551)}
        queries = []

        def answer(url, params):
            if not url.endswith("/query"):
                return {"fields": [{"name": "TAXLOT", "type": "esriFieldTypeString"}], "objectIdField": "OBJECTID"}
            queries.append(params["where"])
            asked = [value.strip("'") for value in params["where"].split("(", 1)[1].rstrip(")").split(",")]
            return {"features": [
                {"attributes": {"TAXLOT": key}, "geometry": {"x": centroids[key][1], "y": centroids[key][0]}}
                for key in asked if key in centroids
            ]}

        producer.arcgis._request_json = answer

        result = scheduler.poll_job("deeds_salem_or")

        assert requested == [FILES.format(2026)]
        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (4, 1, 2)
        assert result["duplicates_skipped"] == 1
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        assert queries == ["TAXLOT IN ('072W99AA00100','051W99AA00300','073W99AA00400')"]
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [(event.doc_id, event.bbl, event.document_amount) for event in events] == [
            ("99001", "072W99AA00100", 416000.0)
        ]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_salem_or")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 2)
