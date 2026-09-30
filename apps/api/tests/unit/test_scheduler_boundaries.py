"""The incremental filter's boundary, source column and zone, and the row ids
and parcel joins poll_job applies before parsing.

A date-only column stores one time for a whole day, so a strict ``>`` on its
watermark never read the rows a city published later that day; an ArcGIS
layer that declares a zone reads the stored UTC watermark as local time; and a
sale keyed by parcel alone collided with the parcel's next sale.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler


@pytest.fixture
def scheduler():
    with patch("src.producers.base_producer.BaseKafkaProducer"):
        sched = MunicipalIngestionScheduler(
            dlq_producer=MagicMock(), rate_limit_delay_seconds=0.0, dedup_capacity=1000
        )
    for producer in sched.producers.values():
        producer.producer = MagicMock()
    sched.state_file = None
    return sched


def _permit(job, issued, **extra):
    return {
        "job__": job,
        "latitude": "40.725",
        "longitude": "-73.997",
        "job_type": "A1",
        "initial_cost": "100000",
        "issuance_date": issued,
        **extra,
    }


def _where(producer, client="socrata"):
    return getattr(producer, client).paginate.call_args.kwargs["where_clause"]


class TestBoundary:
    def test_a_whole_hour_watermark_keeps_its_day(self, scheduler):
        producer = scheduler.producers["permits"]
        producer.socrata.paginate = MagicMock(return_value=[])
        scheduler.metrics["permits"].high_watermark = "2026-09-29T00:00:00"

        scheduler.poll_job("permits", limit=10)

        assert _where(producer) == "issuance_date >= '2026-09-29T00:00:00'"

    def test_a_timestamp_watermark_stays_strict(self, scheduler):
        producer = scheduler.producers["permits"]
        producer.socrata.paginate = MagicMock(return_value=[])
        scheduler.metrics["permits"].high_watermark = "2026-09-29T10:15:07"

        scheduler.poll_job("permits", limit=10)

        assert _where(producer) == "issuance_date > '2026-09-29T10:15:07'"

    def test_a_full_poll_stuck_on_its_boundary_steps_past_it(self, scheduler):
        producer = scheduler.producers["permits"]
        met = scheduler.metrics["permits"]
        met.high_watermark = "2026-09-29T00:00:00"
        boundary = [_permit(f"M{i}", "2026-09-29T00:00:00.000") for i in range(3)]
        producer.socrata.paginate = MagicMock(return_value=[boundary])

        scheduler.poll_job("permits", limit=3)

        assert met.high_watermark == "2026-09-29T00:00:00"
        assert met.boundary_stalled is True

        # The same rows again would stall forever: the next filter is strict.
        producer.socrata.paginate = MagicMock(return_value=[[_permit("M9", "2026-09-30T00:00:00.000")]])
        scheduler.poll_job("permits", limit=3)
        assert _where(producer) == "issuance_date > '2026-09-29T00:00:00'"

        # The watermark moved, so the boundary rule applies again.
        assert met.high_watermark == "2026-09-30T00:00:00"
        assert met.boundary_stalled is False
        producer.socrata.paginate = MagicMock(return_value=[])
        scheduler.poll_job("permits", limit=3)
        assert _where(producer) == "issuance_date >= '2026-09-30T00:00:00'"

    def test_a_stalled_timestamp_steps_to_the_next_second(self, scheduler):
        """Milwaukee's licence layer returns its refresh time as 01:23:59 but
        stores a finer one, so ``> 01:23:59`` kept matching every row."""
        producer = scheduler.producers["permits"]
        producer.socrata.paginate = MagicMock(return_value=[])
        met = scheduler.metrics["permits"]
        met.high_watermark = "2026-09-30T01:23:59"
        met.boundary_stalled = True

        scheduler.poll_job("permits", limit=3)

        assert _where(producer) == "issuance_date >= '2026-09-30T01:24:00'"

    def test_a_short_poll_is_not_a_stall(self, scheduler):
        producer = scheduler.producers["permits"]
        met = scheduler.metrics["permits"]
        met.high_watermark = "2026-09-29T00:00:00"
        producer.socrata.paginate = MagicMock(return_value=[[_permit("M1", "2026-09-29T00:00:00.000")]])

        scheduler.poll_job("permits", limit=3)

        assert met.boundary_stalled is False

    def test_a_newest_first_poll_never_steps_past(self, scheduler):
        """Newer rows would have come first, so a full page that left the
        watermark alone holds nothing newer to reach."""
        producer = scheduler.producers["permits"]
        met = scheduler.metrics["permits"]
        scheduler.job_metadata["permits"]["order_by"] = "issuance_date DESC"
        met.high_watermark = "2026-09-29T00:00:00"
        boundary = [_permit(f"M{i}", "2026-09-29T00:00:00.000") for i in range(3)]
        producer.socrata.paginate = MagicMock(return_value=[boundary])

        scheduler.poll_job("permits", limit=3)

        assert met.boundary_stalled is False


class TestWatermarkSource:
    def test_the_watermark_follows_the_filter_column(self, scheduler):
        """Connecticut's licences filter on a refresh date but date each event
        by its effective date: advancing from the event date re-read the whole
        refresh on every poll."""
        producer = scheduler.producers["permits"]
        scheduler.job_metadata["permits"]["watermark_col"] = "refreshed_at"
        producer.socrata.paginate = MagicMock(
            return_value=[[_permit("M1", "2026-01-05T00:00:00.000", refreshed_at="2026-09-29T08:00:00.000")]]
        )

        result = scheduler.poll_job("permits", limit=10)

        assert result["high_watermark"] == "2026-09-29T08:00:00"

    def test_the_event_date_stands_in_for_an_empty_column(self, scheduler):
        producer = scheduler.producers["permits"]
        scheduler.job_metadata["permits"]["watermark_col"] = "refreshed_at"
        producer.socrata.paginate = MagicMock(
            return_value=[[_permit("M1", "2026-09-28T09:30:00.000", refreshed_at=None)]]
        )

        result = scheduler.poll_job("permits", limit=10)

        assert result["high_watermark"] == "2026-09-28T09:30:00"


class TestLayerZone:
    def test_an_arcgis_filter_reads_in_the_layers_zone(self, scheduler):
        """DC's 311 layer declares Eastern time: 01:30 UTC is 21:30 the evening
        before, exact to the second."""
        producer = scheduler.producers["311"]
        producer.arcgis.paginate = MagicMock(return_value=[])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": "America/New_York"})
        scheduler.metrics["311_dc"].high_watermark = "2026-09-30T01:30:00"

        result = scheduler.poll_job("311_dc", limit=10)

        assert result["status"] == "SUCCESS"
        assert _where(producer, "arcgis") == "ADDDATE > timestamp '2026-09-29 21:30:00'"

    def test_an_unreadable_layer_fails_the_poll_not_the_scheduler(self, scheduler):
        producer = scheduler.producers["311"]
        producer.arcgis.paginate = MagicMock(return_value=[])
        producer.arcgis.get_layer_metadata = MagicMock(side_effect=RuntimeError("ArcGIS error 499"))
        scheduler.metrics["311_dc"].high_watermark = "2026-09-30T01:30:00"

        result = scheduler.poll_job("311_dc", limit=10)

        assert result["status"] == "ERROR"
        assert "499" in result["error"]
        producer.arcgis.paginate.assert_not_called()


class TestSaleRows:
    def test_a_composite_id_joins_every_key(self, scheduler):
        """Lynchburg's DocumentNo repeats across an instrument's parcels and
        LRSN across a parcel's sales: a row is the pair."""
        assert scheduler._extract_record_id(
            "deeds_lynchburg", {"LRSN": 8921, "DocumentNo": "260000257      "}
        ) == "deeds_lynchburg:8921|260000257"
        assert scheduler._extract_record_id(
            "deeds_lynchburg", {"LRSN": 17439, "DocumentNo": "260000257"}
        ) == "deeds_lynchburg:17439|260000257"
        assert scheduler._extract_record_id("deeds_lynchburg", {"LRSN": 8921}) == "deeds_lynchburg:8921|"

    def test_a_parcel_keeps_each_sale_and_drops_repeated_shapes(self, scheduler):
        """Stark County repeats a parcel's sale row for each of its shapes, and
        keying by parcel alone dropped the parcel's next sale."""
        first = {"PARID": "9999001", "INSTRUMENT_NUMBER": "202609290000001", "OBJECTID": 11}
        shape = {**first, "OBJECTID": 12}
        resale = {**first, "INSTRUMENT_NUMBER": "202610150000007", "OBJECTID": 13}

        ids = [scheduler._extract_record_id("deeds_canton", row) for row in (first, shape, resale)]

        assert ids == [
            "deeds_canton:9999001|202609290000001",
            "deeds_canton:9999001|202609290000001",
            "deeds_canton:9999001|202610150000007",
        ]
        # Object ids do not follow the transfer date, so the feed reads newest first.
        assert scheduler.job_metadata["deeds_canton"]["order_by"] == "TRANSFER_DATE DESC, OBJECTID DESC"

    def test_a_poll_places_sales_at_their_parcel_centroid(self, scheduler):
        producer = scheduler.producers["deeds"]
        rows = [
            {"LRSN": 14196, "DocumentNo": "260005545", "SaleDate": "2026-09-25T00:00:00+00:00",
             "SaleAmount": 180000.0, "ESRI_OID": 29},
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.fetch_centroid_index = MagicMock(return_value={"14196": (37.4136, -79.1422)})

        result = scheduler.poll_job("deeds_lynchburg", limit=10)

        assert result["records_published"] == 1
        kwargs = producer.arcgis.fetch_centroid_index.call_args.kwargs
        assert kwargs["join_key"] == "LRSN"
        assert kwargs["join_values"] == [14196]
        event = producer.producer.produce.call_args.kwargs["payload"]
        assert (event.latitude, event.longitude) == (37.4136, -79.1422)
        assert event.h3_res9 is not None

    def test_a_workbook_sale_joins_by_its_own_column_name(self, scheduler):
        """Richmond's workbook headers arrive lower-cased (``pin``) while its
        Parcels layer spells the field ``PIN``."""
        producer = scheduler.producers["deeds"]
        rows = [
            {"pin": "W0001234005", "transfer_date": "2026-09-22T00:00:00", "consideration": 285000,
             "deed_book": "ID2026", "deed_page": 21877, "deed_type": "Deed"},
        ]
        producer.excel.paginate = MagicMock(return_value=[rows])
        producer.arcgis.fetch_centroid_index = MagicMock(return_value={"W0001234005": (37.553, -77.462)})

        result = scheduler.poll_job("deeds_richmond", limit=10)

        assert result["records_published"] == 1
        assert producer.excel.paginate.call_args.kwargs["link_pattern"] == r"Assessor_Transfers_[0-9-]+\.xlsx$"
        kwargs = producer.arcgis.fetch_centroid_index.call_args.kwargs
        assert (kwargs["join_key"], kwargs["join_values"]) == ("PIN", ["W0001234005"])
        event = producer.producer.produce.call_args.kwargs["payload"]
        assert (event.latitude, event.longitude) == (37.553, -77.462)
        assert scheduler._extract_record_id("deeds_richmond", rows[0]) == (
            "deeds_richmond:W0001234005|2026-09-22T00:00:00|ID2026|21877"
        )
