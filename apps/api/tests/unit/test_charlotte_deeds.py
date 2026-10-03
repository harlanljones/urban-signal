"""Charlotte deeds from Mecklenburg County's sales ledger (2026-09-30).

The county's ``TaxParcelSales`` layer, on the server that also carries its
permits, lists the county's recorded transfers on each parcel's polygon:
1,598,291 rows, one per transfer and parcel. Charlotte reads the transfers
dated in the 90 days before each poll (8,925 on 2026-09-30, the newest dated
2026-09-22), each at its parcel's centroid. The August sweep found no sales
feed: it read the City's server, and the county's old REST path answered 404.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = ["objectid", "parcelid", "transferid", "saleprice", "saledate", "deeddescription", "legalreference"]

FIELD_MAP = {
    "doc_id": ["legalreference", "transferid"],
    "recorded_date": ["saledate"],
    "document_amount": ["saleprice"],
    "bbl": ["parcelid"],
    "doc_type": ["deeddescription"],
}

WINDOW = "saledate >= CURRENT_DATE - INTERVAL '90' DAY AND saledate <= CURRENT_TIMESTAMP"

# A parcel's outline as the client asks for it (outSR=4326), near Uptown.
PARCEL_OUTLINE = {
    "rings": [[[-80.8436, 35.2268], [-80.8426, 35.2268], [-80.8426, 35.2274],
               [-80.8436, 35.2274], [-80.8436, 35.2268]]]
}


def _spec():
    return get_dataset(CityId.CHARLOTTE, FeedType.DEEDS)


def _sale(**changes):
    """A recorded transfer as the ArcGIS client hands it on (synthetic values)."""
    return {
        "objectid": 1,
        "parcelid": "00100001",
        "transferid": 9990001,
        "saleprice": 309500.0,
        "saledate": "2026-09-21T04:00:00+00:00",
        "deeddescription": "SPECIAL WARRANTY DEED",
        "legalreference": "99999-001",
        "latitude": 35.2271,
        "longitude": -80.8431,
        **changes,
    }


def test_charlotte_reads_the_countys_sales_ledger():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_charlotte_deeds_url
    assert spec.endpoint.startswith("https://meckgis.mecklenburgcountync.gov/")
    assert spec.endpoint.endswith("/TaxParcelSales/FeatureServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert spec.watermark_col == "saledate"
    assert spec.where == WINDOW
    assert spec.order_by == "saledate DESC, objectid DESC"
    assert spec.field_map == FIELD_MAP
    # Each row sits on its parcel's polygon, and the county is the metro.
    assert spec.needs_geocode is False
    assert (spec.parcel_join, spec.metro_clip) == ({}, False)
    assert (spec.oid_field, spec.max_record_count) == ("objectid", 2000)


def test_the_request_names_its_columns_and_leaves_the_parties_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    assert not {"grantor", "grantee"} & set(select)


def test_each_transfer_publishes_once_per_parcel_under_its_deed():
    spec = _spec()
    # A deed can cover many parcels (one covers 119 in the window) and a
    # transfer can repeat on several property rows of one parcel, so a row is
    # its transfer and parcel. The event carries the deed's book and page.
    assert (spec.id_keys, spec.composite_id) == (["transferid", "parcelid"], True)
    assert spec.field_map["doc_id"][0] == "legalreference"


def test_the_window_fits_the_cap_and_a_weekly_refresh():
    spec = _spec()
    # 8,925 transfers in the window on 2026-09-30, and 11,009 in the busiest
    # 90 days of the past year (April to June 2025).
    assert spec.batch_limit == 15000
    assert spec.interval_seconds == 21600.0
    # The ledger ran eight days behind and did not move within the day.
    assert spec.expected_cadence_days == 7


class TestCharlotteDeedParsing:
    @pytest.fixture
    def deeds(self):
        with patch("src.producers.deeds_acris_producer.BaseKafkaProducer"):
            from src.producers.deeds_acris_producer import DeedsACRISProducer

            return DeedsACRISProducer()

    @staticmethod
    def _row(**changes):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _sale(**changes).items() if key not in ("latitude", "longitude")}
        attributes["saledate"] = 1789963200000  # 2026-09-21 at midnight Eastern
        return ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": PARCEL_OUTLINE}, date_fields={"saledate"}
        )

    def test_a_transfer_is_published_at_its_parcels_centroid(self, deeds):
        event = deeds.parse_socrata_row(self._row(), city_id="charlotte")
        assert event is not None
        assert (event.city_id, event.doc_id, event.bbl) == ("charlotte", "99999-001", "00100001")
        assert event.recorded_date.isoformat() == "2026-09-21T04:00:00+00:00"
        assert (event.document_amount, event.doc_type) == (309500.0, "SPECIAL WARRANTY DEED")
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (35.2271, -80.8431)
        assert event.h3_res9 is not None

    def test_a_transfer_without_a_price_still_publishes(self, deeds):
        event = deeds.parse_socrata_row(self._row(saleprice=None, deeddescription="QUIT CLAIM"), city_id="charlotte")
        assert event is not None
        assert (event.doc_id, event.doc_type) == ("99999-001", "QUIT CLAIM")


class TestCharlottePoll:
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

    def test_a_poll_publishes_each_parcel_of_a_deed_once(self, scheduler):
        producer = scheduler.producers["deeds"]
        rows = [
            _sale(),
            # The same deed on a second parcel, and again on another property
            # row of that parcel.
            _sale(objectid=2, parcelid="00100002", latitude=35.2280, longitude=-80.8440),
            _sale(objectid=3, parcelid="00100002", latitude=35.2280, longitude=-80.8440),
            _sale(objectid=4, parcelid="00200001", transferid=9990002, legalreference="99999-002",
                  saleprice=0.0, deeddescription="QUIT CLAIM", saledate="2026-09-18T04:00:00+00:00",
                  latitude=35.4993, longitude=-80.8487),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("deeds_clt")

        assert (result["records_fetched"], result["records_published"], result["duplicates_skipped"]) == (4, 3, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == ("saledate DESC, objectid DESC", ",".join(COLUMNS))
        assert kwargs["max_records"] == 15000
        calls = producer.producer.produce.call_args_list
        assert [(call.kwargs["payload"].doc_id, call.kwargs["payload"].bbl) for call in calls] == [
            ("99999-001", "00100001"), ("99999-001", "00100002"), ("99999-002", "00200001"),
        ]
        # The deed's parcels share one key.
        assert [call.kwargs["key"] for call in calls] == [
            "charlotte:99999-001", "charlotte:99999-001", "charlotte:99999-002",
        ]

        # The next poll reads the same window and publishes none of it again.
        result = scheduler.poll_job("deeds_clt")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 4)
