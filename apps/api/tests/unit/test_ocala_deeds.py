"""Ocala deeds from the Marion County parcels on the City's GIS server (2026-10-02).

The City of Ocala publishes the Marion County Property Appraiser's parcels,
"updated weekly from data provided by the Property Appraiser's office", each
with its latest sale: a year (``yr1``) and month (``mo1``) with no day, an OR
book and page, a price and the parcel's own point. The poll reads the current
month and the three before it, computed on the server: 7,472 sales on
2026-10-02 (July to September and one in October), leaving out 51 polygons
that carry a sale but no parcel number.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.cities.ocala import compose_deed_date
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "parcel", "yr1", "mo1", "pr_1", "bk1", "pg1", "INSIDE_X", "INSIDE_Y"]

FIELD_MAP = {
    "doc_id": ["parcel", "OBJECTID"],
    "document_amount": ["pr_1"],
    "bbl": ["parcel"],
    "latitude": ["INSIDE_Y"],
    "longitude": ["INSIDE_X"],
}

ORDER = "yr1 DESC, mo1 DESC, OBJECTID DESC"

MONTHS = (
    "yr1 * 12 + mo1 >= EXTRACT(YEAR FROM CURRENT_DATE) * 12 + EXTRACT(MONTH FROM CURRENT_DATE) - 3"
    " AND yr1 * 12 + mo1 <= EXTRACT(YEAR FROM CURRENT_DATE) * 12 + EXTRACT(MONTH FROM CURRENT_DATE)"
)

WHERE = f"parcel <> '' AND {MONTHS}"


def _spec():
    return get_dataset(CityId.OCALA, FeedType.DEEDS)


def _sale(**changes):
    """A parcel's latest sale as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 90001,
        "parcel": "9999-001-001",
        "yr1": 2026,
        "mo1": 8,
        "pr_1": 315000,
        "bk1": "9001",
        "pg1": "0101",
        "INSIDE_X": -82.1401,
        "INSIDE_Y": 29.1872,
        **changes,
    }


def test_ocala_reads_the_county_parcels_on_the_citys_server():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_ocala_deeds_url
    assert spec.endpoint == "https://gis.ocalafl.org/arcgis/rest/services/Public/Parcels/FeatureServer/0"
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    # The sale date is a month; the leaf composes it, so nothing is mapped.
    assert spec.watermark_col == ""
    assert "recorded_date" not in spec.field_map
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 250000)


def test_the_server_computes_a_window_of_whole_months():
    spec = _spec()
    # The current month and the three before it; a sale keyed for a later
    # month (one in November on 2026-10-02) stays out. So do 51 polygons with
    # a sale and no parcel number, some sharing a book and page ("DETH REGS"),
    # which would publish under no parcel and key as one another.
    assert spec.where == WHERE
    assert spec.order_by == ORDER


def test_the_request_names_its_columns_and_leaves_the_owners_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    assert not {"name", "add_1", "add_2", "add_3", "add_4", "city", "zip"} & set(select)


def test_each_parcel_publishes_once_per_deed():
    spec = _spec()
    assert (spec.id_keys, spec.composite_id) == (["parcel", "bk1", "pg1"], True)


def test_the_cap_covers_the_busiest_months():
    spec = _spec()
    # 7,472 sales on 2026-10-02; April to June 2026 held 9,946.
    assert spec.batch_limit == 15000
    assert spec.interval_seconds == 21600.0
    # A sale's date is the first of its month.
    assert spec.expected_cadence_days == 45
    assert spec.metro_clip is True


def test_compose_deed_date_stamps_the_first_of_the_month():
    assert compose_deed_date({"yr1": 2026, "mo1": 9}) == "2026-09-01"
    assert compose_deed_date({"yr1": "2026", "mo1": "7"}) == "2026-07-01"
    for bad in ({"yr1": 2026, "mo1": 0}, {"yr1": 2026, "mo1": 13}, {"yr1": None, "mo1": 9}, {"yr1": 2026}):
        assert compose_deed_date(bad) is None


class TestOcalaDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_parcel_on_the_first_of_its_month(self, deeds):
        event = deeds.parse_socrata_row(_sale(), city_id="ocala")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("ocala", "9999-001-001", "9999-001-001")
        assert event.recorded_date.date().isoformat() == "2026-08-01"
        assert event.document_amount == 315000.0
        assert (event.latitude, event.longitude) == (29.1872, -82.1401)
        assert event.h3_res9 is not None


class TestOcalaPoll:
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

    def test_a_poll_reads_the_months_and_skips_parcels_outside_the_metro(self, scheduler):
        producer = scheduler.producers["deeds"]
        rows = [
            _sale(OBJECTID=90003, parcel="9999-001-003", mo1=10, bk1="9050", pg1="0007"),
            _sale(),
            # A parcel west of the metro box, near Dunnellon.
            _sale(OBJECTID=90002, parcel="9999-001-002", mo1=7, INSIDE_X=-82.4612, INSIDE_Y=29.0491),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("deeds_ocala")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 2, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WHERE})"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert (kwargs["batch_size"], kwargs["max_records"]) == (1000, 15000)
        calls = producer.producer.produce.call_args_list
        assert [
            (call.kwargs["payload"].bbl, call.kwargs["payload"].recorded_date.date().isoformat()) for call in calls
        ] == [("9999-001-003", "2026-10-01"), ("9999-001-001", "2026-08-01")]

        # The next poll reads the same months and publishes none of them again.
        result = scheduler.poll_job("deeds_ocala")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 2)
