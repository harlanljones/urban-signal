"""Pierce County deeds from the county's weekly sales extract (2026-09-30).

Tacoma reads the Assessor-Treasurer's ``sale.zip`` for the sales its parcels
place inside the city. Pierce County's metro is the whole county, so it reads
the same lines, the sales dated in the 90 days before each poll (2,432 on
2026-09-30), and places each on its parcel anywhere in the county's tax
parcel layer. A sale whose parcel the layer lacks (most are mobile homes and
leaseholds) stays unplaced, and ``metro_clip`` skips it.
"""

import io
import zipfile
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset, get_job_name

# What the county's feed shares with Tacoma's: the file, how it is read, the
# window, the ids and the field map.
READS_LIKE_TACOMA = (
    "endpoint", "platform", "ingestion_mode", "zip_member", "delimiter", "columns", "select", "where",
    "watermark_col", "watermark_format", "watermark_type", "order_by", "id_keys", "composite_id",
    "field_map", "needs_geocode", "batch_limit", "interval_seconds", "expected_cadence_days",
)


def _spec():
    return get_dataset(CityId.PIERCE, FeedType.DEEDS)


def test_pierce_reads_the_county_sales_extract_as_tacoma_does():
    from src.config import settings

    spec, tacoma = _spec(), get_dataset(CityId.TACOMA, FeedType.DEEDS)
    # One file for the county, declared once.
    assert spec.endpoint == settings.csv_tacoma_deeds_endpoint
    assert spec.endpoint == "https://online.co.pierce.wa.us/datamart/sale.zip"
    for field in READS_LIKE_TACOMA:
        assert getattr(spec, field) == getattr(tacoma, field), field
    assert spec.select.split(",") == ["etn", "parcel_number", "sale_date", "sale_price", "deed_type"]
    assert not set(spec.select.split(",")) & {"grantor", "grantee"}
    # A full read of the county's window, with half again to spare, once a
    # day: the extract is rebuilt every Friday.
    assert (spec.batch_limit, spec.interval_seconds) == (5000, 86400.0)


def test_each_sale_takes_its_parcels_centroid_anywhere_in_the_county():
    from src.config import settings

    spec = _spec()
    # No filter on the parcels: every parcel in the layer is in the county.
    assert spec.parcel_join == {
        "parcel_layer": settings.arcgis_pierce_tax_parcels_url,
        "join_key": "TaxParcelNumber",
        "geometry_source": "centroid",
        "row_key": "parcel_number",
    }
    # A sale the layer cannot place is skipped, not dead-lettered.
    assert spec.metro_clip is True


class TestPiercePoll:
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

    def test_a_poll_keeps_every_sale_its_parcel_places_in_the_county(self, scheduler):
        today = datetime.now(UTC).date()
        recent = (today - timedelta(days=5)).strftime("%m/%d/%Y")
        stale = (today - timedelta(days=200)).strftime("%m/%d/%Y")
        lines = [
            f"9999901|1|0000000001|{recent}|451000.00|Statutory Warranty Deed|GRANTOR A|GRANTEE B|1|0||Improved|Residential",
            f"9999902|1|0000000002|{recent}|389000.00|Statutory Warranty Deed|GRANTOR C|GRANTEE D|1|0||Improved|Residential",
            f"9999903|1|0000000003|{recent}|85000.00|Bill of Sale|GRANTOR E|GRANTEE F|1|0||Improved|Residential",
            f"9999904|1|0000000004|{stale}|275000.00|Statutory Warranty Deed|GRANTOR G|GRANTEE H|1|0||Improved|Residential",
        ]
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("sale.txt", "\r\n".join(lines) + "\r\n")
        payload = archive.getvalue()
        producer = scheduler.producers["deeds"]
        producer.csv.http = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=payload)))
        # Downtown Tacoma, which the county's metro holds too, and Puyallup;
        # the third parcel has no polygon of its own, so the layer has none.
        producer.arcgis.fetch_centroid_index = MagicMock(
            return_value={"0000000001": (47.2529, -122.4443), "0000000002": (47.1854, -122.2929)}
        )
        job = get_job_name(FeedType.DEEDS, CityId.PIERCE)

        result = scheduler.poll_job(job)

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 2, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.fetch_centroid_index.call_args.kwargs
        assert kwargs["endpoint_url"].endswith("/Tax_Parcels/FeatureServer/0")
        assert kwargs["join_values"] == ["0000000001", "0000000002", "0000000003"]
        assert kwargs["where"] is None
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [(event.city_id, event.doc_id, event.bbl) for event in events] == [
            ("pierce", "9999901", "0000000001"), ("pierce", "9999902", "0000000002"),
        ]
        assert (events[1].latitude, events[1].longitude, events[1].document_amount) == (47.1854, -122.2929, 389000.0)

        # The next day's poll reads the same window and publishes none of it again.
        result = scheduler.poll_job(job)

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 2)
