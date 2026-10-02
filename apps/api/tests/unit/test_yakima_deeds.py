"""Yakima deeds from the County Assessor's parcels (2026-10-02).

The City GIS server publishes the Yakima County Assessor's parcels,
105,110 polygons, each with its latest sale: the excise number, gross price
and sale date, written as text (``9/9/2026``). Text in that order does not
compare as dates, but the server casts it, so the poll reads the sales of
the 90 days before each poll (453 county-wide on 2026-10-02, the newest
dated 2026-09-23) and keeps the ones inside the metro box. The County's own
sales layers stopped in 2016 and 2024.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = [
    "OBJECTID", "ASSESSOR_NO", "SALE_DATE", "GROSS_SALE_PRICE", "EXCISE_NUMBER",
    "USE_CODE", "SITUS_CITY",
]

FIELD_MAP = {
    "doc_id": ["EXCISE_NUMBER", "ASSESSOR_NO"],
    "recorded_date": ["SALE_DATE"],
    "document_amount": ["GROSS_SALE_PRICE"],
    "bbl": ["ASSESSOR_NO"],
    "doc_type": ["USE_CODE"],
    "borough": ["SITUS_CITY"],
}

WINDOW = (
    "CAST(SALE_DATE AS DATE) >= CURRENT_DATE - INTERVAL '90' DAY"
    " AND CAST(SALE_DATE AS DATE) <= CURRENT_DATE"
)


def _spec():
    return get_dataset(CityId.YAKIMA, FeedType.DEEDS)


def _sale(**changes):
    """A parcel's latest sale as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 50001,
        "ASSESSOR_NO": "19990000001",
        "SALE_DATE": "9/9/2026",
        "GROSS_SALE_PRICE": 544000.0,
        "EXCISE_NUMBER": "E099001",
        "USE_CODE": "11 Single Unit",
        "SITUS_CITY": "YAKIMA",
        "latitude": 46.5912,
        "longitude": -120.5568,
        **changes,
    }


def test_yakima_reads_the_assessors_parcels_on_the_city_server():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_yakima_deeds_url
    assert spec.endpoint.startswith("https://gis.yakimawa.gov/arcgis/rest/services/Assessor/")
    assert spec.endpoint.endswith("/AssessorParcels/MapServer/1")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert (spec.watermark_col, spec.watermark_type, spec.watermark_format) == (
        "SALE_DATE", "text", "%m/%d/%Y",
    )
    assert spec.field_map == FIELD_MAP
    # The client takes each parcel's centroid; the layer covers the county.
    assert spec.needs_geocode is False
    assert (spec.parcel_join, spec.metro_clip) == ({}, True)
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)


def test_the_server_casts_the_text_dates_into_a_rolling_window():
    spec = _spec()
    # As text, ``9/9/2026`` sorts above ``9/23/2026`` and no ``>=`` reads a
    # window, so the dates are cast; the server answered the cast over every
    # row on 2026-10-02.
    assert spec.where == WINDOW
    # Paging follows the object ids: the sale dates cannot order the rows.
    assert spec.order_by == "OBJECTID"


def test_the_request_names_its_columns_and_leaves_the_people_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # Owners, their mailing addresses and the seller stay on the server.
    assert not {
        "FIRST_NAME", "MIDDLE_NAME", "LAST_NAME", "ORG_NAME", "ROLE", "ROLE_PERCENT",
        "MAILING_ADDR", "MAILING_CITY", "MAILING_STATE", "MAILING_ZIP", "GRANTOR_NAME",
    } & set(select)


def test_each_sale_publishes_once_per_parcel():
    spec = _spec()
    # A parcel with several owners repeats once per owner, and a sale can
    # convey several parcels, so a row is its parcel, date and excise number.
    assert (spec.id_keys, spec.composite_id) == (["ASSESSOR_NO", "SALE_DATE", "EXCISE_NUMBER"], True)
    assert spec.field_map["doc_id"][0] == "EXCISE_NUMBER"


def test_the_window_fits_the_cap_and_a_weekly_refresh():
    spec = _spec()
    # 453 sales in the window on 2026-10-02; the busiest three months of 2026
    # (April to June) held 594.
    assert spec.batch_limit is None
    assert spec.interval_seconds == 21600.0
    # Sales reach the layer about nine days after they close.
    assert spec.expected_cadence_days == 7


class TestYakimaDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_parcels_centroid(self, deeds):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _sale().items() if key not in ("latitude", "longitude")}
        ring = [[-120.5571, 46.5910], [-120.5565, 46.5910], [-120.5565, 46.5914], [-120.5571, 46.5914], [-120.5571, 46.5910]]
        row = ArcGISClient()._flatten_feature({"attributes": attributes, "geometry": {"rings": [ring]}}, date_fields=set())

        event = deeds.parse_socrata_row(row, city_id="yakima")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("yakima", "E099001", "19990000001")
        # The unpadded text date reads as the day.
        assert event.recorded_date.isoformat() == "2026-09-09T00:00:00+00:00"
        assert (event.document_amount, event.doc_type) == (544000.0, "11 SINGLE UNIT")
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (46.5912, -120.5568)
        assert event.h3_res9 is not None


class TestYakimaPoll:
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
            # The same parcel's second owner.
            _sale(OBJECTID=50002),
            # The same sale's second parcel.
            _sale(OBJECTID=50003, ASSESSOR_NO="19990000002", latitude=46.5915, longitude=-120.5575),
            # A sale in Toppenish, south-east of the metro box.
            _sale(OBJECTID=50004, ASSESSOR_NO="20990000003", EXCISE_NUMBER="E099002", GROSS_SALE_PRICE=90000.0,
                  SITUS_CITY="TOPPENISH", latitude=46.3774, longitude=-120.3087),
            _sale(OBJECTID=50005, ASSESSOR_NO="19990000004", EXCISE_NUMBER="E099003", SALE_DATE="9/23/2026",
                  GROSS_SALE_PRICE=100000.0, USE_CODE="91 Undeveloped Land", latitude=46.6181, longitude=-120.4402),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("deeds_yakima")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (5, 3, 1)
        assert result["duplicates_skipped"] == 1
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == ("OBJECTID", ",".join(COLUMNS))
        calls = producer.producer.produce.call_args_list
        assert [(call.kwargs["payload"].doc_id, call.kwargs["payload"].bbl) for call in calls] == [
            ("E099001", "19990000001"), ("E099001", "19990000002"), ("E099003", "19990000004"),
        ]
        assert [call.kwargs["key"] for call in calls] == ["yakima:E099001", "yakima:E099001", "yakima:E099003"]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_yakima")

        assert (result["records_published"], result["duplicates_skipped"], result["outside_metro"]) == (0, 4, 1)
