"""Cape Coral deeds from the Lee County Property Appraiser's parcels (2026-10-02).

Lee County's parcel layer, edited nightly on the County's ArcGIS Online org,
holds each parcel's latest sale: its date, price and instrument number. The
poll reads the sales dated in the 90 days before it, county-wide (6,765 on
2026-10-02), at each parcel's own coordinates, and keeps the ones inside the
metro box (4,409); Bonita Springs, Lehigh Acres and the islands west of
Pine Island fall outside it. Sales reach the layer two to three weeks after
their date, and the window reads them when they do.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "STRAP", "S_1DATE", "S_1AMOUNT", "S_1OR_NUM", "SITECITY", "LATITUDE", "LONGITUDE"]

FIELD_MAP = {
    "doc_id": ["S_1OR_NUM", "STRAP"],
    "recorded_date": ["S_1DATE"],
    "document_amount": ["S_1AMOUNT"],
    "bbl": ["STRAP"],
    "borough": ["SITECITY"],
    "latitude": ["LATITUDE"],
    "longitude": ["LONGITUDE"],
}

WINDOW = "S_1DATE >= CURRENT_DATE - INTERVAL '90' DAY AND S_1DATE <= CURRENT_TIMESTAMP"


def _spec():
    return get_dataset(CityId.CAPE_CORAL, FeedType.DEEDS)


def _sale(**changes):
    """A parcel's latest sale as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 400001,
        "STRAP": "999990000000101000",
        "S_1DATE": "2026-09-25T04:00:00+00:00",
        "S_1AMOUNT": 325000.0,
        "S_1OR_NUM": "2099000249503",
        "SITECITY": "CAPE CORAL",
        "LATITUDE": 26.6301,
        "LONGITUDE": -81.9912,
        **changes,
    }


def test_cape_coral_reads_the_lee_county_parcels():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_cape_coral_deeds_url
    assert spec.endpoint.startswith("https://services2.arcgis.com/LvWGAAhHwbCJ2GMP/")
    assert spec.endpoint.endswith("/Lee_County_Parcels/FeatureServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert spec.watermark_col == "S_1DATE"
    assert spec.field_map == FIELD_MAP
    # Each parcel carries its own coordinates; the layer covers the county.
    assert spec.needs_geocode is False
    assert (spec.parcel_join, spec.metro_clip) == ({}, True)
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)


def test_the_poll_reads_the_last_ninety_days_newest_first():
    spec = _spec()
    assert spec.where == WINDOW
    assert spec.order_by == "S_1DATE DESC, OBJECTID DESC"


def test_the_request_names_its_columns_and_leaves_the_owners_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The owner block, their mailing address and the legal description stay
    # on the server.
    assert not {
        "O_NAME", "O_OTHERS", "O_CAREOF", "O_ADDR1", "O_ADDR2", "O_CITY", "O_STATE", "O_ZIP",
        "O_COUNTRY", "LEGAL", "SITEADDR", "Creator", "Editor",
    } & set(select)


def test_each_parcel_of_a_sale_publishes_once():
    spec = _spec()
    # One instrument can convey several parcels (6,117 instruments for the
    # 6,661 sales counted earlier on 2026-10-02).
    assert (spec.id_keys, spec.composite_id) == (["STRAP", "S_1DATE", "S_1OR_NUM"], True)
    assert spec.field_map["doc_id"][0] == "S_1OR_NUM"


def test_the_cap_holds_the_busiest_season_with_room():
    spec = _spec()
    # 6,765 sales in the window on 2026-10-02; the three months from March
    # to May 2026 held 11,253.
    assert spec.batch_limit == 17000
    assert spec.interval_seconds == 21600.0
    # The layer is edited nightly; sales reach it two to three weeks late.
    assert spec.expected_cadence_days == 7


class TestCapeCoralDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_parcels_coordinates(self, deeds):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {**_sale(), "S_1DATE": 1790308800000}
        ring = [[-81.9914, 26.6299], [-81.9910, 26.6299], [-81.9910, 26.6303], [-81.9914, 26.6303], [-81.9914, 26.6299]]
        row = ArcGISClient()._flatten_feature({"attributes": attributes, "geometry": {"rings": [ring]}}, date_fields={"S_1DATE"})

        event = deeds.parse_socrata_row(row, city_id="cape_coral")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("cape_coral", "2099000249503", "999990000000101000")
        # Sale dates are midnight in Lee County.
        assert event.recorded_date.isoformat() == "2026-09-25T04:00:00+00:00"
        assert (event.document_amount, event.doc_type) == (325000.0, "DEED")
        assert (event.latitude, event.longitude) == (26.6301, -81.9912)
        assert event.source_neighborhood == "CAPE CORAL"
        assert event.h3_res9 is not None


class TestCapeCoralPoll:
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

    def test_a_poll_publishes_the_sales_inside_the_metro(self, scheduler):
        producer = scheduler.producers["deeds"]
        rows = [
            _sale(),
            # The same instrument's second parcel.
            _sale(OBJECTID=400002, STRAP="999990000000102000", LATITUDE=26.6305, LONGITUDE=-81.9915),
            # A Lehigh Acres sale, east of the metro box.
            _sale(OBJECTID=400003, STRAP="999990000000201000", S_1OR_NUM="2099000246462", S_1AMOUNT=210000.0,
                  SITECITY="LEHIGH ACRES", LATITUDE=26.6043, LONGITUDE=-81.6420),
            _sale(OBJECTID=400004, STRAP="999990000000301000", S_1OR_NUM="2099000250401", S_1AMOUNT=3080153.0,
                  S_1DATE="2026-09-23T04:00:00+00:00", SITECITY="FORT MYERS", LATITUDE=26.6420, LONGITUDE=-81.8710),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("deeds_cape_coral")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (4, 3, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == ("S_1DATE DESC, OBJECTID DESC", ",".join(COLUMNS))
        calls = producer.producer.produce.call_args_list
        assert [(call.kwargs["payload"].doc_id, call.kwargs["payload"].bbl) for call in calls] == [
            ("2099000249503", "999990000000101000"),
            ("2099000249503", "999990000000102000"),
            ("2099000250401", "999990000000301000"),
        ]
        assert [call.kwargs["key"] for call in calls] == [
            "cape_coral:2099000249503", "cape_coral:2099000249503", "cape_coral:2099000250401",
        ]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_cape_coral")

        assert (result["records_published"], result["duplicates_skipped"], result["outside_metro"]) == (0, 3, 1)
