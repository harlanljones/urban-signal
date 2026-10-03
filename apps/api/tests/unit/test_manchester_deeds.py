"""Manchester NH deeds from the City's parcels (2026-10-02).

The City GIS server publishes Manchester's 33,997 parcels as polygons,
refreshed daily, each with its latest sale: book and page, price and sale
date, written as text (``9/10/2026``). Text in that order does not compare
as dates, but the server casts it, so the poll reads the sales of the 90
days before each poll (521 on 2026-10-02, the newest dated 2026-09-17) and
keeps the ones inside the metro box. The assessor posts sales two to four
weeks after they close.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "ParcelID", "SaleDate", "SalePrice", "SaleBookPage", "LandUse"]

FIELD_MAP = {
    "doc_id": ["SaleBookPage", "ParcelID"],
    "recorded_date": ["SaleDate"],
    "document_amount": ["SalePrice"],
    "bbl": ["ParcelID"],
    "doc_type": ["LandUse"],
}

WINDOW = (
    "CAST(SaleDate AS DATE) >= CURRENT_DATE - INTERVAL '90' DAY"
    " AND CAST(SaleDate AS DATE) <= CURRENT_DATE"
    " AND Suppress_Internet_Access <> 'Yes'"
)


def _spec():
    return get_dataset(CityId.MANCHESTER, FeedType.DEEDS)


def _sale(**changes):
    """A parcel's latest sale as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 70001,
        "ParcelID": "0999-0001",
        "SaleDate": "9/10/2026",
        "SalePrice": 580000.0,
        "SaleBookPage": "9999/0001",
        "LandUse": "Single Fam",
        "latitude": 42.9956,
        "longitude": -71.4548,
        **changes,
    }


def test_manchester_reads_the_citys_parcels():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_manchester_deeds_url
    assert spec.endpoint == "https://ags.manchesternh.gov/agsgis7/rest/services/Community/Parcels/MapServer/0"
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert (spec.watermark_col, spec.watermark_type, spec.watermark_format) == ("SaleDate", "text", "%m/%d/%Y")
    assert spec.field_map == FIELD_MAP
    # The client takes each parcel's centroid; the layer covers the city.
    assert spec.needs_geocode is False
    assert (spec.parcel_join, spec.metro_clip) == ({}, True)
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)


def test_the_server_casts_the_text_dates_into_a_rolling_window():
    spec = _spec()
    # As text, ``9/9/2026`` sorts above ``9/17/2026`` and no ``>=`` reads a
    # window, so the dates are cast. The 58 parcels the City keeps off its
    # internet maps stay out (none had a sale in the window on 2026-10-02).
    assert spec.where == WINDOW
    # Paging follows the object ids: the sale dates cannot order the rows.
    assert spec.order_by == "OBJECTID"


def test_the_request_names_its_columns_and_leaves_the_owners_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # Owners and their mailing addresses stay on the server.
    assert not {
        "PrimaryOwnerName", "PrimaryOwnerAddress", "PrimaryOwnerAddress2", "PrimaryOwnerCity",
        "PrimaryOwnerState", "PrimaryOwnerZIP",
    } & set(select)


def test_each_sale_publishes_once_per_parcel():
    spec = _spec()
    # A deed can convey several parcels, so a row is its parcel, date and
    # book and page; 4 of the 521 rows in the window on 2026-10-02 repeated
    # one of those.
    assert (spec.id_keys, spec.composite_id) == (["ParcelID", "SaleDate", "SaleBookPage"], True)
    assert spec.field_map["doc_id"][0] == "SaleBookPage"


def test_the_window_fits_the_cap_and_the_posting_lag():
    spec = _spec()
    # 521 sales in the window on 2026-10-02; the 90 days from 2026-05-04
    # held 735.
    assert spec.batch_limit is None
    assert spec.interval_seconds == 21600.0
    # The newest sale was 15 days old on 2026-10-02 and August's were still
    # arriving, so the alarm waits six weeks.
    assert spec.expected_cadence_days == 21


class TestManchesterDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_parcels_centroid(self, deeds):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _sale().items() if key not in ("latitude", "longitude")}
        ring = [[-71.4551, 42.9954], [-71.4545, 42.9954], [-71.4545, 42.9958], [-71.4551, 42.9958], [-71.4551, 42.9954]]
        row = ArcGISClient()._flatten_feature({"attributes": attributes, "geometry": {"rings": [ring]}}, date_fields=set())

        event = deeds.parse_socrata_row(row, city_id="manchester")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("manchester", "9999/0001", "0999-0001")
        # The unpadded text date reads as the day.
        assert event.recorded_date.isoformat() == "2026-09-10T00:00:00+00:00"
        assert (event.document_amount, event.doc_type) == (580000.0, "SINGLE FAM")
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (42.9956, -71.4548)
        assert event.h3_res9 is not None

    def test_a_transfer_without_a_price_publishes_at_zero(self, deeds):
        event = deeds.parse_socrata_row(_sale(SalePrice=0.0, LandUse="Two Family"), city_id="manchester")

        assert event is not None
        assert (event.document_amount, event.doc_type) == (0.0, "TWO FAMILY")


class TestManchesterPoll:
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

    def test_a_poll_publishes_each_parcel_of_a_sale_inside_the_metro(self, scheduler):
        producer = scheduler.producers["deeds"]
        rows = [
            _sale(),
            # The same row listed twice.
            _sale(OBJECTID=70002),
            # The same deed's second parcel, a condominium unit.
            _sale(OBJECTID=70003, ParcelID="0999-0002", LandUse="Condo", latitude=42.9961, longitude=-71.4552),
            # A parcel at the south end of the city, below the metro box.
            _sale(OBJECTID=70004, ParcelID="0999-0003", SaleBookPage="9999/0002", SalePrice=340000.0,
                  latitude=42.9240, longitude=-71.4650),
            _sale(OBJECTID=70005, ParcelID="0999-0004", SaleBookPage="9999/0003", SaleDate="9/17/2026",
                  SalePrice=0.0, LandUse="Two Family", latitude=43.0151, longitude=-71.4702),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("deeds_manchester")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (5, 3, 1)
        assert result["duplicates_skipped"] == 1
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == ("OBJECTID", ",".join(COLUMNS))
        calls = producer.producer.produce.call_args_list
        assert [(call.kwargs["payload"].doc_id, call.kwargs["payload"].bbl) for call in calls] == [
            ("9999/0001", "0999-0001"), ("9999/0001", "0999-0002"), ("9999/0003", "0999-0004"),
        ]
        assert [call.kwargs["key"] for call in calls] == [
            "manchester:9999/0001", "manchester:9999/0001", "manchester:9999/0003",
        ]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_manchester")

        assert (result["records_published"], result["duplicates_skipped"], result["outside_metro"]) == (0, 4, 1)
