"""Wilmington deeds from New Hanover County's parcel points (2026-10-02).

The County GIS server that serves Wilmington's permits publishes the
County's parcels as points, 115,880 of them, each with its latest sale: the
date and price as text (``2026-09-11 00:00:00``, ``695000``), the instrument
(``WD`` for a warranty deed) and the municipality. The server casts the text
dates, so the poll reads the sales of the 90 days before each poll: 2,401 on
2026-10-02, every one inside the metro box, the newest dated 2026-09-23.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "PARID", "SALE_DATE", "SALE_INSTRUMENT", "SALE_PRICE", "MUNI"]

FIELD_MAP = {
    "doc_id": ["PARID", "OBJECTID"],
    "recorded_date": ["SALE_DATE"],
    "document_amount": ["SALE_PRICE"],
    "bbl": ["PARID"],
    "doc_type": ["SALE_INSTRUMENT"],
    "borough": ["MUNI"],
}

ORDER = "SALE_DATE DESC, OBJECTID DESC"

WINDOW = (
    "CAST(SALE_DATE AS DATE) >= CURRENT_DATE - INTERVAL '90' DAY"
    " AND CAST(SALE_DATE AS DATE) <= CURRENT_DATE"
)


def _spec():
    return get_dataset(CityId.WILMINGTON_NC, FeedType.DEEDS)


def _sale(**changes):
    """A parcel's latest sale as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 90001,
        "PARID": "R09999-001-001-000",
        "SALE_DATE": "2026-09-11 00:00:00",
        "SALE_INSTRUMENT": "WD",
        "SALE_PRICE": "695000",
        "MUNI": "WM",
        "latitude": 34.2357,
        "longitude": -77.9461,
        **changes,
    }


def test_wilmington_reads_the_countys_parcel_points():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_wilmington_nc_deeds_url
    # Wilmington's permits come from the same server.
    assert spec.endpoint.startswith("https://gis.nhcgov.com/server/rest/services/")
    assert spec.endpoint.endswith("/Layers/PropertyPoints4326/MapServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert (spec.watermark_col, spec.watermark_type, spec.watermark_format) == (
        "SALE_DATE", "text", "%Y-%m-%d %H:%M:%S",
    )
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    assert (spec.parcel_join, spec.metro_clip) == ({}, False)
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)


def test_the_server_casts_the_text_dates_into_a_rolling_window():
    spec = _spec()
    # Without the upper bound, two sales dated 2029 and 3025 would read too.
    assert spec.where == WINDOW
    # Year-first text sorts as dates, so the newest sales come first.
    assert spec.order_by == ORDER


def test_the_request_names_its_columns_and_leaves_the_owners_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The owner, the owner's mailing address and the legal description stay
    # on the server.
    assert not {
        "OWN1", "OWNER_NUM", "OWNER_STREET", "OWNER_STREETTYPE", "OWNER_DIR", "OWNER_UNITDESC",
        "OWNER_UNITNO", "OWNER_CITY", "OWNER_STATE", "OWNER_ZIP", "OWNER_COUNTRY",
        "OWNER_ADDR1", "OWNER_ADDR2", "OWNER_ADDR3", "LEGAL1",
    } & set(select)


def test_each_parcel_publishes_once_per_sale():
    spec = _spec()
    # A deed can convey several parcels, and its book and page repeat across
    # them, so a row is its parcel and sale date.
    assert (spec.id_keys, spec.composite_id) == (["PARID", "SALE_DATE"], True)


def test_the_cap_covers_the_busiest_window():
    spec = _spec()
    # 2,401 sales in the window on 2026-10-02; April to June 2026 held 2,898.
    assert spec.batch_limit == 4500
    assert spec.interval_seconds == 21600.0
    # No refresh stamp: the newest sale was nine days old, and three reads
    # over the night of 2026-10-02 found the layer unchanged.
    assert spec.expected_cadence_days == 30


class TestWilmingtonDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_parcel_point(self, deeds):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _sale().items() if key not in ("latitude", "longitude")}
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -77.9461, "y": 34.2357}}, date_fields=set()
        )

        event = deeds.parse_socrata_row(row, city_id="wilmington_nc")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("wilmington_nc", "R09999-001-001-000", "R09999-001-001-000")
        assert event.recorded_date.isoformat() == "2026-09-11T00:00:00"
        assert (event.document_amount, event.doc_type) == (695000.0, "WD")
        assert (event.latitude, event.longitude) == (34.2357, -77.9461)
        assert event.h3_res9 is not None


class TestWilmingtonPoll:
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

    def test_a_poll_publishes_each_parcel_of_a_sale_once(self, scheduler):
        producer = scheduler.producers["deeds"]
        rows = [
            _sale(PARID="R09999-001-002-000", SALE_DATE="2026-09-23 00:00:00", SALE_INSTRUMENT="QC",
                  SALE_PRICE="0", MUNI="CB", latitude=34.0352, longitude=-77.8936),
            _sale(),
            # The same deed's second parcel.
            _sale(OBJECTID=90002, PARID="R09999-001-003-000", latitude=34.2361, longitude=-77.9466),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("deeds_wilmington_nc")

        assert (result["records_fetched"], result["records_published"], result["duplicates_skipped"]) == (3, 3, 0)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert (kwargs["batch_size"], kwargs["max_records"]) == (1000, 4500)
        calls = producer.producer.produce.call_args_list
        assert [(call.kwargs["payload"].bbl, call.kwargs["payload"].doc_type) for call in calls] == [
            ("R09999-001-002-000", "QC"), ("R09999-001-001-000", "WD"), ("R09999-001-003-000", "WD"),
        ]
        assert scheduler.metrics["deeds_wilmington_nc"].high_watermark == "2026-09-23 00:00:00"

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_wilmington_nc")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 3)
