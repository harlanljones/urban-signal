"""Charlotte permits from Mecklenburg County's Accela layer (2026-09-30).

The county's GIS server republishes the county's Accela building permits
every night as points, one row per permit and parcel, for Charlotte and the
county's six towns (58,961 rows since January 2024). Earlier probes looked
only at the city's server and found no bulk feed. ``issue_date`` holds the
day alone (midnight Eastern), the server rejects ISO literals, and it sorts
the 4,006 permits not yet issued first under ``issue_date DESC``.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = [
    "objectid", "permit_number", "issue_date", "type_of_work", "permit_status",
    "building_construction_cost_system", "project_address", "zip_code",
    "tax_jurisdiction", "cama_parcel_number",
]

FIELD_MAP = {
    "job_id": ["permit_number"],
    "issuance_date": ["issue_date"],
    "job_type": ["type_of_work"],
    "cost": ["building_construction_cost_system"],
    "status": ["permit_status"],
    "address_street": ["project_address"],
    "zipcode": ["zip_code"],
    "bbl": ["cama_parcel_number"],
    "borough": ["tax_jurisdiction"],
}

ORDER = "issue_date DESC,permit_number ASC,cama_parcel_number ASC"


def _spec():
    return get_dataset(CityId.CHARLOTTE, FeedType.PERMITS)


def _permit(**changes):
    """An issued permit as the ArcGIS client hands it on (synthetic values)."""
    return {
        "objectid": 1,
        "permit_number": "RES-NEW-26-999001",
        "issue_date": "2026-09-29T04:00:00+00:00",
        "type_of_work": "New",
        "permit_status": "Inspection Phase",
        "building_construction_cost_system": "197359.76",
        "project_address": "100 EXAMPLE ST CHARLOTTE NC 28202",
        "zip_code": "28202",
        "tax_jurisdiction": "CHARLOTTE",
        "cama_parcel_number": "11100001",
        "latitude": 35.2271,
        "longitude": -80.8431,
        **changes,
    }


def test_charlotte_reads_mecklenburg_countys_accela_permits():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_charlotte_permits_url
    assert spec.endpoint.startswith("https://meckgis.mecklenburgcountync.gov/")
    assert spec.endpoint.endswith("/BuildingPermits_Accela/FeatureServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "incremental")
    assert spec.watermark_col == "issue_date"
    assert (spec.oid_field, spec.max_record_count) == ("objectid", 2000)
    assert spec.field_map == FIELD_MAP
    # Every row is a point; the client lifts it onto latitude/longitude.
    assert spec.needs_geocode is False


def test_permits_not_yet_issued_stay_on_the_server():
    # The server sorts a null issue date first under ``issue_date DESC``, so
    # without the filter a first poll would read only unissued permits.
    assert _spec().where == "issue_date IS NOT NULL"


def test_the_request_names_its_columns_and_leaves_the_owner_out():
    select = _spec().select.split(",")
    assert select == COLUMNS
    # The layer also carries the owner's name, phone, mailing address and
    # email, and free-text descriptions.
    assert not [column for column in select if "owner" in column or "description" in column]


def test_each_permit_publishes_once_at_its_first_parcel():
    spec = _spec()
    # A permit spanning parcels has a row, and a point, per parcel. The
    # permit number keys the event, so its first parcel in this order stands
    # for it, and the order is total, so pages never shift under the offset.
    assert (spec.id_keys, spec.composite_id) == (["permit_number", "objectid"], False)
    assert spec.order_by == ORDER


def test_a_nightly_refresh_of_dated_days_polls_hourly():
    spec = _spec()
    # The layer is rebuilt overnight through the day before, so the newest
    # issue date is a day to two days old; the alarm (twice the cadence) waits
    # four days.
    assert spec.interval_seconds == 3600.0
    assert spec.expected_cadence_days == 2


def test_the_county_server_takes_ansi_literals_in_eastern_time():
    from src.producers.watermarks import ANSI_DATE_LITERAL_HOSTS, watermark_comparison

    assert "meckgis.mecklenburgcountync.gov" in ANSI_DATE_LITERAL_HOSTS
    assert watermark_comparison(
        "issue_date", ">=", "2026-09-29T04:00:00", _spec().endpoint, time_zone="America/New_York"
    ) == "issue_date >= timestamp '2026-09-29 00:00:00'"


class TestCharlottePermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_an_issued_permit_is_published_at_its_point(self, permits):
        event = permits.parse_socrata_row(_permit(), city_id="charlotte")
        assert event is not None
        assert (event.city_id, event.job_id) == ("charlotte", "RES-NEW-26-999001")
        assert (event.job_type.value, event.normalized_permit_type) == ("NB", "NEW_CONSTRUCTION")
        assert event.estimated_cost == pytest.approx(197359.76)
        assert (event.status, event.zipcode, event.bbl) == ("Inspection Phase", "28202", "11100001")
        assert event.address_street == "100 EXAMPLE ST CHARLOTTE NC 28202"
        assert event.issuance_date.isoformat() == "2026-09-29T04:00:00+00:00"
        assert (event.latitude, event.longitude) == (35.2271, -80.8431)
        assert (event.borough, event.source_neighborhood) == ("CHARLOTTE_CORE", "CHARLOTTE")

    def test_a_permit_far_from_the_citys_submarkets_keeps_its_towns_name(self, permits):
        # Davidson lies 30 km north of Uptown, beyond the 25 km the division
        # lookup snaps across and outside the city's box.
        event = permits.parse_socrata_row(
            _permit(tax_jurisdiction="DAVIDSON", latitude=35.4993, longitude=-80.8487),
            city_id="charlotte",
        )
        assert event is not None
        assert (event.borough, event.source_neighborhood) == ("DAVIDSON", "DAVIDSON")

    def test_an_equipment_changeout_without_a_cost_is_still_published(self, permits):
        event = permits.parse_socrata_row(
            _permit(type_of_work="Equipment Changeout", building_construction_cost_system=""),
            city_id="charlotte",
        )
        assert event is not None
        assert (event.job_type.value, event.estimated_cost) == ("OT", 0.0)


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

    def test_a_poll_publishes_each_permit_once_and_rereads_its_newest_day(self, scheduler):
        producer = scheduler.producers["permits"]
        rows = [
            _permit(),
            _permit(objectid=2, permit_number="COM-GBLD-26-999002", type_of_work="StandaloneBuilding",
                    cama_parcel_number="00300001A", latitude=35.2150, longitude=-80.8550),
            _permit(objectid=3, permit_number="COM-GBLD-26-999002", type_of_work="StandaloneBuilding",
                    cama_parcel_number="00300001B", latitude=35.2152, longitude=-80.8553),
            _permit(objectid=4, permit_number="RES-CHG-26-999003", type_of_work="Equipment Changeout",
                    building_construction_cost_system="", tax_jurisdiction="HUNTERSVILLE",
                    issue_date="2026-09-28T04:00:00+00:00", latitude=35.4107, longitude=-80.8429),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])
        producer.arcgis.get_layer_metadata = MagicMock(return_value={"time_zone": "America/New_York"})

        result = scheduler.poll_job("permits_clt")

        assert (result["records_fetched"], result["records_published"], result["duplicates_skipped"]) == (4, 3, 1)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == "(issue_date IS NOT NULL)"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [event.job_id for event in events] == [
            "RES-NEW-26-999001", "COM-GBLD-26-999002", "RES-CHG-26-999003",
        ]
        # The permit spanning two parcels stands at the first one.
        assert (events[1].bbl, events[1].latitude) == ("00300001A", 35.2150)
        assert scheduler.metrics["permits_clt"].high_watermark == "2026-09-29T04:00:00"

        # The newest day is read again in the layer's own zone; its permits
        # were published already.
        producer.arcgis.paginate = MagicMock(return_value=[[_permit()]])
        result = scheduler.poll_job("permits_clt")

        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == (
            "(issue_date IS NOT NULL) AND issue_date >= timestamp '2026-09-29 00:00:00'"
        )
        assert (result["records_published"], result["duplicates_skipped"]) == (0, 1)
