"""Orlando permits from the City's permit applications (2026-10-02).

The corpus read Orlando's permits from the statewide parcel layer with county
code 48, which is Levy County (the Department of Revenue numbers Orange County
58), and a parcel roll is not a permit stream. The City publishes its own
permit applications (``ryhf-m453``): 966,954 issued, 6,977 in the 90 days to
2026-10-02, newest 2026-09-23. The poll reads issued permits newest first.
Rows carry no point (one of those 6,977 has one), so each permit takes the
City's own address point for its address and the geocoder places the rest.
The poll leaves owners', contractors' and private providers' names on the
server.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.producers.scheduler import MunicipalIngestionScheduler
from src.spatial.city_registry import CityId, FeedType, get_dataset
from src.spatial.geocoder import GeoPoint, compose_geocode_query

COLUMNS = [
    "permit_number",
    # The work type ahead of the application type: "New Building Permit".
    "worktype || ' ' || application_type AS permit_kind",
    "application_type",
    "application_status",
    "estimated_cost",
    "permit_address",
    "parcel_number",
    "neighborhood",
    "processed_date",
    "issue_permit_date",
]

FIELD_MAP = {
    "job_id": ["permit_number"],
    "issuance_date": ["issue_permit_date"],
    "filing_date": ["processed_date"],
    "job_type": ["permit_kind", "application_type"],
    "status": ["application_status"],
    "cost": ["estimated_cost"],
    "address_street": ["permit_address"],
    "bbl": ["parcel_number"],
    "borough": ["neighborhood"],
}

ORDER = "issue_permit_date DESC, :id"

# City Hall, as the City's address points place it (synthetic permit values).
CITY_HALL = (28.538444, -81.379233)


def _spec():
    return get_dataset(CityId.ORLANDO, FeedType.PERMITS)


def _permit(**changes):
    """A permit as the Socrata client hands it on (synthetic values)."""
    return {
        "permit_number": "BLD2026-90001",
        "permit_kind": "New Building Permit",
        "application_type": "Building Permit",
        "application_status": "Open",
        "estimated_cost": "250000",
        "permit_address": "400 S ORANGE AVE",
        "parcel_number": "252229000000001",
        "neighborhood": "Downtown Orlando",
        "processed_date": "2026-09-01T00:00:00.000",
        "issue_permit_date": "2026-09-23T00:00:00.000",
        **changes,
    }


class _Geocoder:
    """Answers the queries it knows and records every query it is asked."""

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.queries = []

    def geocode(self, query):
        self.queries.append(query)
        point = self.answers.get(query)
        return GeoPoint(point[0], point[1], 1.0, "census:Exact") if point else None


def test_orlando_reads_the_citys_permit_applications():
    from src.config import settings

    spec = _spec()
    assert spec.endpoint == settings.socrata_orlando_permits_endpoint
    assert spec.endpoint == "https://data.cityoforlando.net/resource/ryhf-m453.json"
    assert (spec.platform, spec.ingestion_mode) == ("socrata", "incremental")
    assert (spec.watermark_col, spec.order_by) == ("issue_permit_date", ORDER)
    # Socrata sorts empty dates first under DESC; only issued permits are read.
    assert spec.where == "issue_permit_date IS NOT NULL"
    assert spec.id_keys == ["permit_number"]
    assert spec.field_map == FIELD_MAP
    assert (spec.interval_seconds, spec.expected_cadence_days) == (3600.0, 7)


def test_a_week_of_permits_landing_at_once_fits_one_poll():
    # A newest-first poll never reaches rows past its cap. The newest issue
    # date trailed the table's update by eight days on 2026-10-02, so a week
    # of permits can land at once: the seven working days to 2026-09-23
    # issued 1,000.
    assert _spec().batch_limit == 3000


def test_the_poll_names_its_columns_and_leaves_names_on_the_server():
    select = _spec().select.split(",")
    assert select == COLUMNS
    assert not {
        "property_owner_name", "parcel_owner_name", "contractor", "contractor_name",
        "contractor_address", "contractor_phone_number", "private_provider",
        "private_provider_company_name", "project_name",
    } & set(select)


def test_each_permit_takes_its_address_point_and_the_geocoder_places_the_rest():
    from src.config import settings

    spec = _spec()
    assert spec.parcel_join == {
        "parcel_layer": settings.arcgis_orlando_address_points_url,
        "join_key": "SitusAddress",
        "row_key": "permit_address",
    }
    assert spec.parcel_join["parcel_layer"].startswith(
        "https://services5.arcgis.com/mMuoPCaIYD4wEgDl/arcgis/rest/services/Address_Point/"
    )
    assert (spec.needs_geocode, spec.geocode_context) == (True, "Orlando, FL")
    # A clip runs before the geocoder and would drop every row it places.
    assert spec.metro_clip is False


def test_the_socrata_poll_sends_the_select():
    from src.producers.acquisition import _ADAPTER_REQUEST_KEYS
    from src.producers.socrata_client import SocrataClient

    assert "select" in _ADAPTER_REQUEST_KEYS["socrata"]
    client = SocrataClient()
    with patch.object(client, "fetch_records", return_value=[]) as fetch:
        list(client.paginate(_spec().endpoint, select=_spec().select))
    assert fetch.call_args.kwargs["select"] == _spec().select


class TestOrlandoPermitParsing:
    @pytest.fixture
    def permits(self):
        with patch("src.producers.dob_permits_producer.BaseKafkaProducer"):
            from src.producers.dob_permits_producer import DOBPermitsProducer

            return DOBPermitsProducer()

    def test_a_permit_is_published_at_its_address_point(self, permits):
        geocoder = _Geocoder()
        row = {**_permit(), "latitude": CITY_HALL[0], "longitude": CITY_HALL[1]}
        with patch("src.spatial.geocoder.get_geocoder", return_value=geocoder):
            event = permits.parse_socrata_row(row, city_id="orlando")

        assert event is not None
        assert (event.city_id, event.job_id) == ("orlando", "BLD2026-90001")
        assert (event.latitude, event.longitude) == CITY_HALL
        assert event.job_type.value == "NB"
        assert event.normalized_permit_type == "NEW_CONSTRUCTION"
        assert event.issuance_date.isoformat() == "2026-09-23T00:00:00"
        assert event.filing_date.date().isoformat() == "2026-09-01"
        assert (event.status, event.estimated_cost) == ("Open", 250000.0)
        assert (event.address_street, event.bbl) == ("400 S ORANGE AVE", "252229000000001")
        assert geocoder.queries == []

    def test_an_address_without_a_point_is_geocoded_in_orlando(self, permits):
        query = compose_geocode_query("400 S ORANGE AVE", "Orlando, FL")
        geocoder = _Geocoder({query: CITY_HALL})
        with patch("src.spatial.geocoder.get_geocoder", return_value=geocoder):
            event = permits.parse_socrata_row(_permit(), city_id="orlando")

        assert geocoder.queries == [query]
        assert (event.latitude, event.longitude) == CITY_HALL

    def test_a_permit_neither_places_is_not_published(self, permits):
        with patch("src.spatial.geocoder.get_geocoder", return_value=_Geocoder()):
            assert permits.parse_socrata_row(_permit(), city_id="orlando") is None

    def test_the_application_type_stands_in_for_a_missing_work_type(self, permits):
        row = {**_permit(permit_kind=None, application_type="Demolition Permit"),
               "latitude": CITY_HALL[0], "longitude": CITY_HALL[1]}
        event = permits.parse_socrata_row(row, city_id="orlando")

        assert event.job_type.value == "DM"
        assert event.normalized_permit_type == "DEMOLITION"


class TestOrlandoPermitPoll:
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

    def test_address_points_place_first_and_the_geocoder_takes_the_rest(self, scheduler):
        from src.config import settings

        producer = scheduler.producers["permits"]
        rows = [
            _permit(),
            # A new subdivision's address the geocoder knows.
            _permit(permit_number="ELE2026-90002", permit_kind="LowVoltage Electrical",
                    application_type="Electrical", permit_address="1000 NEW SUBDIVISION ST",
                    issue_permit_date="2026-09-22T00:00:00.000"),
            # An address neither knows.
            _permit(permit_number="MEC2026-90003", permit_kind="Repair Mechanical Permit",
                    application_type="Mechanical Permit", permit_address="1 NOWHERE ALY",
                    issue_permit_date="2026-09-22T00:00:00.000"),
        ]
        producer.socrata.paginate = MagicMock(return_value=[rows])
        producer.arcgis.fetch_centroid_index = MagicMock(return_value={"400 S ORANGE AVE": CITY_HALL})
        subdivision = compose_geocode_query("1000 NEW SUBDIVISION ST", "Orlando, FL")
        geocoder = _Geocoder({subdivision: (28.4012, -81.2299)})

        with patch("src.spatial.geocoder.get_geocoder", return_value=geocoder):
            result = scheduler.poll_job("permits_orlando")

        assert (result["records_fetched"], result["records_published"]) == (3, 2)
        assert scheduler.dlq_producer.route_to_dlq.call_count == 1
        join = producer.arcgis.fetch_centroid_index.call_args.kwargs
        assert (join["endpoint_url"], join["join_key"]) == (settings.arcgis_orlando_address_points_url, "SitusAddress")
        assert join["join_values"] == ["400 S ORANGE AVE", "1000 NEW SUBDIVISION ST", "1 NOWHERE ALY"]
        # The address point places City Hall's permit; the geocoder is asked
        # only for the other two.
        assert geocoder.queries == [subdivision, compose_geocode_query("1 NOWHERE ALY", "Orlando, FL")]
        kwargs = producer.socrata.paginate.call_args.kwargs
        assert (kwargs["order_by"], kwargs["select"]) == (ORDER, _spec().select)
        assert kwargs["where_clause"] == "(issue_permit_date IS NOT NULL)"
        events = [call.kwargs["payload"] for call in producer.producer.produce.call_args_list]
        assert [(e.job_id, e.latitude, e.longitude) for e in events] == [
            ("BLD2026-90001", *CITY_HALL),
            ("ELE2026-90002", 28.4012, -81.2299),
        ]
        assert scheduler.metrics["permits_orlando"].high_watermark == "2026-09-23T00:00:00"

        # The next poll reads the newest day again and publishes nothing new.
        producer.socrata.paginate = MagicMock(return_value=[rows[:1]])
        with patch("src.spatial.geocoder.get_geocoder", return_value=geocoder):
            again = scheduler.poll_job("permits_orlando")

        assert (again["records_published"], again["duplicates_skipped"]) == (0, 1)
        assert producer.socrata.paginate.call_args.kwargs["where_clause"] == (
            "(issue_permit_date IS NOT NULL) AND issue_permit_date >= '2026-09-23T00:00:00'"
        )
