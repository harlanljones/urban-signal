"""Toledo deeds from the Lucas County Auditor's sales layer (2026-09-30).

The Auditor's ``Lucas_Sales`` layer, on its ArcGIS Online parcels service,
puts each recorded sale of real property in Lucas County at a point: 60,834
rows since December 2020, one per sale and parcel. Toledo reads the sales
recorded in the 90 days before each poll (2,296 on 2026-09-30, the newest
recorded 2026-09-25) and keeps the ones inside the metro box. Earlier probes
read the Auditor's own GIS server, whose public layers carry no sales.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "PARCELID", "RECORDDT", "SALEAMNT", "SALESID", "INSTRTYP"]

FIELD_MAP = {
    "doc_id": ["SALESID", "PARCELID"],
    "recorded_date": ["RECORDDT"],
    "document_amount": ["SALEAMNT"],
    "bbl": ["PARCELID"],
    "doc_type": ["INSTRTYP"],
}

WINDOW = "RECORDDT >= CURRENT_DATE - INTERVAL '90' DAY AND RECORDDT <= CURRENT_TIMESTAMP"


def _spec():
    return get_dataset(CityId.TOLEDO, FeedType.DEEDS)


def _sale(**changes):
    """A recorded sale as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 1,
        "PARCELID": "9900001",
        "RECORDDT": "2026-09-25T00:00:00+00:00",
        "SALEAMNT": 325000,
        "SALESID": "99000001",
        "INSTRTYP": "WD",
        "latitude": 41.6528,
        "longitude": -83.5379,
        **changes,
    }


def test_toledo_reads_the_auditors_sales_layer():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_toledo_deeds_url
    assert spec.endpoint.startswith("https://services3.arcgis.com/T8dczfwPixv79EgZ/")
    assert spec.endpoint.endswith("/Lucas_County_TaxParcels/FeatureServer/1")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert spec.watermark_col == "RECORDDT"
    assert spec.where == WINDOW
    assert spec.order_by == "RECORDDT DESC, OBJECTID DESC"
    assert spec.field_map == FIELD_MAP
    # Every sale is a point, and the layer covers the whole county.
    assert spec.needs_geocode is False
    assert (spec.parcel_join, spec.metro_clip) == ({}, True)
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)


def test_the_request_names_its_columns_and_leaves_the_parties_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    assert not {"GRANTOR", "GRANTEE"} & set(select)


def test_each_sale_publishes_once_per_parcel():
    spec = _spec()
    # A sale can convey several parcels (157 of the window's 2,014 sales do,
    # one of them 23), so a row is its sale and parcel. The event carries the
    # sale's number.
    assert (spec.id_keys, spec.composite_id) == (["SALESID", "PARCELID"], True)
    assert spec.field_map["doc_id"][0] == "SALESID"


def test_the_window_fits_the_cap_and_a_weekly_refresh():
    spec = _spec()
    # 2,296 sales in the window on 2026-09-30, and 2,628 in the busiest 90
    # days of the past year (July to September 2025).
    assert spec.batch_limit == 4000
    assert spec.interval_seconds == 21600.0
    # The layer was last rebuilt on Monday 2026-09-28 through the Friday before.
    assert spec.expected_cadence_days == 7


class TestToledoDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @staticmethod
    def _row(**changes):
        from src.producers.arcgis_client import ArcGISClient

        sale = _sale(**changes)
        attributes = {key: value for key, value in sale.items() if key not in ("latitude", "longitude")}
        attributes["RECORDDT"] = 1790294400000  # 2026-09-25, stored as midnight UTC
        geometry = {"x": sale["longitude"], "y": sale["latitude"]}
        return ArcGISClient()._flatten_feature({"attributes": attributes, "geometry": geometry}, date_fields={"RECORDDT"})

    def test_a_sale_is_published_at_its_point(self, deeds):
        event = deeds.parse_socrata_row(self._row(), city_id="toledo")
        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("toledo", "99000001", "9900001")
        assert event.recorded_date.isoformat() == "2026-09-25T00:00:00+00:00"
        assert (event.document_amount, event.doc_type) == (325000.0, "WD")
        assert (event.latitude, event.longitude) == (41.6528, -83.5379)
        assert event.h3_res9 is not None


class TestToledoPoll:
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
            # The same sale's second parcel.
            _sale(OBJECTID=2, PARCELID="9900002", latitude=41.6531, longitude=-83.5384),
            # A sale in Whitehouse, south-west of the metro box.
            _sale(OBJECTID=3, PARCELID="9900003", SALESID="99000002", latitude=41.5189, longitude=-83.8038),
            _sale(OBJECTID=4, PARCELID="9900004", SALESID="99000003", SALEAMNT=90000, INSTRTYP="QC",
                  RECORDDT="2026-09-24T00:00:00+00:00", latitude=41.6939, longitude=-83.5625),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("deeds_toledo")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (4, 3, 1)
        assert result["duplicates_skipped"] == 0
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == ("RECORDDT DESC, OBJECTID DESC", ",".join(COLUMNS))
        assert kwargs["max_records"] == 4000
        calls = producer.producer.produce.call_args_list
        assert [(call.kwargs["payload"].doc_id, call.kwargs["payload"].bbl) for call in calls] == [
            ("99000001", "9900001"), ("99000001", "9900002"), ("99000003", "9900004"),
        ]
        # The sale's parcels share one key.
        assert [call.kwargs["key"] for call in calls] == ["toledo:99000001", "toledo:99000001", "toledo:99000003"]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_toledo")

        assert (result["records_published"], result["duplicates_skipped"], result["outside_metro"]) == (0, 3, 1)
