"""Vancouver WA deeds from Clark County's taxlots (2026-10-02).

Clark County publishes its 196,272 taxlots as a hosted layer, each with its
latest sale's date, price and excise number; it replaces the County's own
MapServer, whose portal item is marked for deletion on 2026-10-12. The poll
reads the taxlots whose sale falls in the 90 days before it: 1,637 on
2026-10-02, 1,113 of them inside the metro box.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["OBJECTID", "Prop_id", "SaleDate", "SaleAmount", "SaleExcise", "SitusCity"]

FIELD_MAP = {
    "doc_id": ["SaleExcise", "Prop_id"],
    "recorded_date": ["SaleDate"],
    "document_amount": ["SaleAmount"],
    "bbl": ["Prop_id"],
    "borough": ["SitusCity"],
}

ORDER = "SaleDate DESC, OBJECTID DESC"

WINDOW = "SaleDate >= CURRENT_DATE - INTERVAL '90' DAY AND SaleDate <= CURRENT_TIMESTAMP"


def _spec():
    return get_dataset(CityId.VANCOUVER_WA, FeedType.DEEDS)


def _sale(**changes):
    """A taxlot's latest sale as the ArcGIS client hands it on (synthetic
    values; the client reduces the taxlot polygon to its centroid)."""
    return {
        "OBJECTID": 90001,
        "Prop_id": 999990001,
        "SaleDate": "2026-09-02T00:00:00+00:00",
        "SaleAmount": 485000.0,
        "SaleExcise": 999001,
        "SitusCity": "VANCOUVER",
        "latitude": 45.6387,
        "longitude": -122.6615,
        **changes,
    }


def test_vancouver_reads_clark_countys_taxlots():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_vancouver_wa_deeds_url
    assert spec.endpoint == (
        "https://services2.arcgis.com/ylxwjFBdCPBzP16d/arcgis/rest/services/TaxlotsforPublicUse/FeatureServer/0"
    )
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert spec.watermark_col == "SaleDate"
    # The layer carries no deed type: each sale publishes as a DEED.
    assert spec.field_map == FIELD_MAP
    assert spec.needs_geocode is False
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)


def test_the_window_holds_the_last_90_days():
    spec = _spec()
    # Part of the sale dates carry a time of day, so the window runs on the
    # server rather than on a watermark.
    assert spec.where == WINDOW
    assert spec.order_by == ORDER


def test_the_request_names_its_columns_and_leaves_the_owner_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The owner's id, the tax bill and the situs address stay on the server.
    assert not {"MainOwnerID", "TaxAmount", "SitusAddrs", "SitusAddrsFull", "LegalShort"} & set(select)


def test_each_taxlot_publishes_once_per_sale():
    spec = _spec()
    # One row per taxlot, its latest sale; a later sale changes the date. A
    # sale over several taxlots shares its excise number.
    assert (spec.id_keys, spec.composite_id) == (["Prop_id", "SaleDate"], True)


def test_the_cap_covers_the_busiest_window():
    spec = _spec()
    # 1,637 sales in the window on 2026-10-02; the 90 days from 2026-04-01
    # held 4,221. At most three pages of 2,000, read every six hours.
    assert spec.batch_limit == 6000
    assert spec.interval_seconds == 21600.0
    # Sales reach the layer weeks after their date: the newest was 21 days
    # old on 2026-10-02.
    assert spec.expected_cadence_days == 21
    # A third of the county's sales lie north and east of the box.
    assert spec.metro_clip is True


class TestVancouverDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    def test_a_sale_is_published_at_its_taxlot(self, deeds):
        event = deeds.parse_socrata_row(_sale(), city_id="vancouver_wa")

        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("vancouver_wa", "999001", "999990001")
        assert event.recorded_date.date().isoformat() == "2026-09-02"
        assert (event.document_amount, event.doc_type) == (485000.0, "DEED")
        assert (event.latitude, event.longitude) == (45.6387, -122.6615)
        assert event.h3_res9 is not None

    def test_a_sale_without_an_excise_number_keys_on_its_taxlot(self, deeds):
        event = deeds.parse_socrata_row(_sale(SaleExcise=None, SaleAmount=None), city_id="vancouver_wa")

        assert event is not None
        assert (event.doc_id, event.document_amount) == ("999990001", 0.0)


class TestVancouverPoll:
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

    def test_a_poll_skips_taxlots_outside_the_metro(self, scheduler):
        producer = scheduler.producers["deeds"]
        rows = [
            _sale(),
            _sale(OBJECTID=90002, Prop_id=999990002, SaleDate="2026-08-14T15:32:24+00:00", SaleAmount=0.0,
                  SaleExcise=999002, latitude=45.6652, longitude=-122.5554),
            # A sale in Battle Ground, north of the box.
            _sale(OBJECTID=90003, Prop_id=999990003, SitusCity="BATTLE GROUND", latitude=45.7809, longitude=-122.5335),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("deeds_vancouver_wa")

        assert (result["records_fetched"], result["records_published"], result["outside_metro"]) == (3, 2, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert (kwargs["batch_size"], kwargs["max_records"]) == (1000, 6000)
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["payload"].bbl for call in calls] == ["999990001", "999990002"]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_vancouver_wa")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 2)
