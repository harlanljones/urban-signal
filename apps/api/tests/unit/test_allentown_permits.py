"""Allentown permits from the City's EnerGov permits view (2026-09-30).

The City's ArcGIS Online org, which also carries the parcel layer Allentown's
deeds come from, publishes its Tyler EnerGov building permits as points: one
row per permit issued since January 2025 (5,812 on 2026-09-30). ``ISSUEDATE``
holds the day at midnight UTC, but five of the 819 permits issued in the last
90 days carry a time of day, so a watermark on it could step past the rest of
its own day. Allentown reads the permits issued in the 90 days before each
poll instead. The site address is split across five columns, which the leaf
joins.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.cities.allentown import compose_permit_address
from src.spatial.city_registry import CityId, FeedType, get_dataset

COLUMNS = [
    "OBJECTID", "PERMITNUMBER", "WORKCLASS", "APPLYDATE", "ISSUEDATE", "STATUSNAME", "ADDRESSLINE1",
    "PREDIRECTION", "ADDRESSLINE2", "STREETTYPE", "POSTDIRECTION", "POSTALCODE", "PARCELNUMBER",
]

FIELD_MAP = {
    "job_id": ["PERMITNUMBER"],
    "issuance_date": ["ISSUEDATE"],
    "filing_date": ["APPLYDATE"],
    "job_type": ["WORKCLASS"],
    "status": ["STATUSNAME"],
    "address_street": ["address_street", "ADDRESSLINE2"],
    "zipcode": ["POSTALCODE"],
    "bbl": ["PARCELNUMBER"],
}

WINDOW = "ISSUEDATE >= CURRENT_DATE - INTERVAL '90' DAY AND ISSUEDATE <= CURRENT_TIMESTAMP"

ORDER = "ISSUEDATE DESC, PERMITNUMBER DESC"


def _spec():
    return get_dataset(CityId.ALLENTOWN, FeedType.PERMITS)


def _permit(**changes):
    """An issued permit as the ArcGIS client hands it on (synthetic values)."""
    return {
        "OBJECTID": 7,
        "PERMITNUMBER": "COA-BP-2026-99001",
        "WORKCLASS": "Residential",
        "APPLYDATE": "2026-09-24T12:42:57+00:00",
        "ISSUEDATE": "2026-09-29T00:00:00+00:00",
        "STATUSNAME": "Issued",
        "ADDRESSLINE1": "100",
        "PREDIRECTION": "N",
        "ADDRESSLINE2": "EXAMPLE",
        "STREETTYPE": "ST",
        "POSTDIRECTION": None,
        "POSTALCODE": "18102",
        "PARCELNUMBER": "999001000",
        "latitude": 40.6103,
        "longitude": -75.4617,
        **changes,
    }


def test_allentown_reads_the_citys_energov_permits_view():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.arcgis_allentown_permits_url
    assert spec.endpoint.startswith("https://services1.arcgis.com/WUqVDRuvIiIiH2Pl/")
    assert spec.endpoint.endswith("/EnerGov_Building_Permits_Current/FeatureServer/0")
    assert (spec.platform, spec.ingestion_mode) == ("arcgis", "snapshot")
    assert spec.watermark_col == "ISSUEDATE"
    assert (spec.oid_field, spec.max_record_count) == ("OBJECTID", 2000)
    assert spec.field_map == FIELD_MAP
    # Every row is a point; the client lifts it onto latitude/longitude.
    assert (spec.needs_geocode, spec.metro_clip) == (False, False)


def test_the_window_holds_ninety_days_of_issued_permits():
    spec = _spec()
    assert spec.where == WINDOW
    # The layer is reloaded with new object ids, so the permit number breaks
    # ties between permits issued the same day.
    assert spec.order_by == ORDER


def test_the_request_names_its_columns():
    # The layer carries no names; the unit and the city are left out too.
    assert _spec().select.split(",") == COLUMNS


def test_each_permit_publishes_once():
    # One row per permit: PERMITNUMBER never repeats.
    assert (_spec().id_keys, _spec().composite_id) == (["PERMITNUMBER"], False)


def test_the_window_fits_the_cap_and_a_nightly_reload():
    spec = _spec()
    # 819 permits in the window on 2026-09-30, and 737 to 1,016 in six
    # 90-day windows since the layer begins (the most April to June 2025).
    assert spec.batch_limit == 2000
    # The layer was reloaded at 00:47 UTC on 2026-09-30 with permits through
    # the day before, and none is issued at weekends, so the alarm (twice
    # the cadence) waits six days.
    assert spec.interval_seconds == 21600.0
    assert spec.expected_cadence_days == 3


class TestAllentownPermitAddress:
    def test_the_parts_join_into_one_street_address(self):
        assert compose_permit_address(_permit()) == "100 N EXAMPLE ST"
        assert compose_permit_address(_permit(PREDIRECTION=None, STREETTYPE="AVE", POSTDIRECTION="SW")) == (
            "100 EXAMPLE AVE SW"
        )

    def test_no_street_name_means_no_address(self):
        assert compose_permit_address(_permit(ADDRESSLINE2=" ")) is None


class TestAllentownPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_an_issued_permit_is_published_at_its_point(self, permits):
        from src.producers.arcgis_client import ArcGISClient

        attributes = {key: value for key, value in _permit().items() if key not in ("latitude", "longitude")}
        attributes["APPLYDATE"] = 1790253777000  # 2026-09-24 12:42:57 UTC
        attributes["ISSUEDATE"] = 1790640000000  # 2026-09-29 at midnight UTC
        row = ArcGISClient()._flatten_feature(
            {"attributes": attributes, "geometry": {"x": -75.4617, "y": 40.6103}},
            date_fields={"APPLYDATE", "ISSUEDATE"},
        )

        event = permits.parse_socrata_row(row, city_id="allentown")

        assert event is not None
        assert (event.city_id, event.job_id) == ("allentown", "COA-BP-2026-99001")
        assert event.address_street == "100 N EXAMPLE ST"
        assert (event.zipcode, event.bbl, event.status) == ("18102", "999001000", "Issued")
        assert event.issuance_date.isoformat() == "2026-09-29T00:00:00+00:00"
        assert event.filing_date.isoformat() == "2026-09-24T12:42:57+00:00"
        assert (round(event.latitude, 4), round(event.longitude, 4)) == (40.6103, -75.4617)
        # The class says residential or commercial, not the work, and the
        # layer carries no cost.
        assert (event.job_type.value, event.normalized_permit_type, event.estimated_cost) == (
            "OT", "MINOR_ALTERATION", 0.0,
        )


class TestAllentownPoll:
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

    def test_a_poll_publishes_each_permit_once(self, scheduler):
        producer = scheduler.producers["permits"]
        rows = [
            _permit(),
            # Issued the same day, and stamped with the time it was issued.
            _permit(OBJECTID=8, PERMITNUMBER="COA-BP-2026-99002", WORKCLASS="Commercial",
                    ISSUEDATE="2026-09-29T10:32:10+00:00", ADDRESSLINE1="200", PREDIRECTION=None,
                    ADDRESSLINE2="EXAMPLE", STREETTYPE="AVE", latitude=40.5815, longitude=-75.4776),
            _permit(OBJECTID=9, PERMITNUMBER="COA-BP-2026-99003", STATUSNAME="Complete",
                    ISSUEDATE="2026-09-28T00:00:00+00:00", latitude=40.5901, longitude=-75.5012),
        ]
        producer.arcgis.paginate = MagicMock(return_value=[rows])

        result = scheduler.poll_job("permits_allentown")

        assert (result["records_fetched"], result["records_published"], result["duplicates_skipped"]) == (3, 3, 0)
        scheduler.dlq_producer.route_to_dlq.assert_not_called()
        kwargs = producer.arcgis.paginate.call_args.kwargs
        assert kwargs["where_clause"] == f"({WINDOW})"
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, ",".join(COLUMNS))
        assert kwargs["max_records"] == 2000
        calls = producer.producer.produce.call_args_list
        assert [call.kwargs["key"] for call in calls] == [
            "allentown:COA-BP-2026-99001", "allentown:COA-BP-2026-99002", "allentown:COA-BP-2026-99003",
        ]
        assert [call.kwargs["payload"].address_street for call in calls] == [
            "100 N EXAMPLE ST", "200 EXAMPLE AVE", "100 N EXAMPLE ST",
        ]

        # The next poll reads the same window, and the stamped time costs
        # nothing: none of it is published again.
        result = scheduler.poll_job("permits_allentown")

        assert (result["records_published"], result["duplicates_skipped"]) == (0, 3)
        assert producer.arcgis.paginate.call_args.kwargs["where_clause"] == f"({WINDOW})"
