"""Tampa deeds from the City's copy of the Hillsborough County parcels (2026-10-02).

The City of Tampa's GIS server publishes the Hillsborough County Property
Appraiser's parcels, all 531,613 of them, each with its latest sale's date
and price. The poll reads the parcels whose sale falls in the 90 days before
it: 3,886 on 2026-10-02, 2,468 of them inside the metro box.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "FOLIO", "S_DATE", "AMT"]

FIELD_MAP = {
    "doc_id": ["FOLIO", "OBJECTID"],
    "recorded_date": ["S_DATE"],
    "document_amount": ["AMT"],
    "bbl": ["FOLIO"],
}

ORDER = "S_DATE DESC, OBJECTID DESC"

WINDOW = "S_DATE >= CURRENT_DATE - INTERVAL '90' DAY AND S_DATE <= CURRENT_TIMESTAMP"


def _spec():
    return get_dataset(CityId.TAMPA, FeedType.DEEDS)


def _sale(**changes):
    """A parcel's latest sale as the ArcGIS client hands it on (synthetic
    values; the client reduces the parcel polygon to its centroid)."""
    return {
        "OBJECTID": 90001,
        "FOLIO": "099999.0001",
        "S_DATE": "2026-09-08T00:00:00+00:00",
        "AMT": 424100.0,
        "latitude": 27.9506,
        "longitude": -82.4572,
        **changes,
    }


def test_tampa_reads_the_county_parcels_on_the_citys_server():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_tampa_deeds_url
    # Tampa's permits, licences and crime come from the same server.
    assert spec.endpoint == "https://arcgis.tampagov.net/arcgis/rest/services/Parcels/TaxParcel/FeatureServer/0"
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert spec.watermark_col == "S_DATE"
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 6000)


def test_the_window_holds_the_last_90_days():
    spec = _spec()
    assert spec.where == WINDOW
    assert spec.order_by == ORDER


def test_the_request_names_its_columns_and_leaves_the_owners_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The owner, the mailing address, the trade name and the legal
    # description stay on the server.
    assert not {"OWNER", "ADDR_1", "ADDR_2", "CITY", "STATE", "ZIP", "DBA", "LEGAL1", "LEGAL2"} & set(select)


def test_each_parcel_publishes_once_per_sale():
    spec = _spec()
    assert (spec.id_keys, spec.composite_id) == (["FOLIO", "S_DATE"], True)


def test_the_cap_covers_the_busiest_window():
    spec = _spec()
    # 3,886 sales in the window on 2026-10-02; May to July 2026 held 6,441.
    assert spec.batch_limit == 10000
    assert spec.interval_seconds == 21600.0
    # No refresh stamp: the newest sale was 14 days old on 2026-10-02.
    assert spec.expected_cadence_days == 30
    # About a third of the county's sales lie outside the box.
    assert spec.metro_clip is True


class TestTampaDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_parcel(self, deeds):
        event = deeds.parse_socrata_row(_sale(), city_id="tampa")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("tampa", "099999.0001", "099999.0001")
        assert event.recorded_date.date().isoformat() == "2026-09-08"
        assert event.document_amount == 424100.0
        assert (event.latitude, event.longitude) == (27.9506, -82.4572)
        assert event.h3_res9 is not None


class TestTampaPoll:
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

    def test_a_poll_skips_parcels_outside_the_metro(self, scheduler):
        producer = scheduler.producers["deeds"]
        rows = [
            _sale(),
            _sale(OBJECTID=90002, FOLIO="099999.0002", S_DATE="2026-08-14T00:00:00+00:00", AMT=310000.0,
                  latitude=28.0587, longitude=-82.4139),
            # A sale in Sun City Center, south of the box.
            _sale(OBJECTID=90003, FOLIO="099999.0003", latitude=27.7181, longitude=-82.3526),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("deeds_tampa")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 2, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert (kwargs["batch_size"], kwargs["max_records"]) == (1000, 10000)
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["payload"].bbl for call in calls] == ["099999.0001", "099999.0002"]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_tampa")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 2)
