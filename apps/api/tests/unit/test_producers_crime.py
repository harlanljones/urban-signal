"""Unit tests for the US-71 crime incident feeds (CHI / SF / SEA / NYC).

Fixtures mirror live rows probed 2026-08-24 from each Socrata dataset.
"""

from unittest.mock import patch

import pytest

from src.producers.crime_incidents_producer import (
    CrimeIncidentsProducer,
    classify_offense_class,
)
from src.spatial.city_registry import REGISTRY, CityId, FeedType, get_dataset, get_job_name

CRIME_CITIES = (CityId.CHICAGO, CityId.SAN_FRANCISCO, CityId.SEATTLE, CityId.NYC)

CHICAGO_ROW = {
    "id": "14295750",
    "case_number": "JK375546",
    "date": "2026-08-16T00:00:00.000",
    "block": "082XX S PAULINA ST",
    "iucr": "0820",
    "primary_type": "THEFT",
    "description": "$500 AND UNDER",
    "location_description": "APARTMENT",
    "arrest": False,
    "domestic": False,
    "beat": "0614",
    "district": "006",
    "ward": "17",
    "community_area": "71",
    "year": "2026",
    "updated_on": "2026-08-23T15:41:51.000",
    "latitude": "41.744201882",
    "longitude": "-87.665713523",
    "location": {"latitude": "41.744201882", "longitude": "-87.665713523"},
}

SEATTLE_ROW = {
    "report_number": "2020-033090",
    "report_date_time": "2020-01-27T17:32:26.000",
    "offense_id": "12338382264",
    "offense_date": "2020-01-27T00:00:00.000",
    "nibrs_group_a_b": "A",
    "nibrs_crime_against_category": "PROPERTY",
    "offense_sub_category": "EXTORTION/FRAUD/FORGERY/BRIBERY (INCLUDES BAD CHECKS)",
    "block_address": "7XX BLOCK OF 19TH AVE E",
    "latitude": "47.62604294",
    "longitude": "-122.307308241278",
    "beat": "C2",
    "precinct": "East",
    "sector": "C",
    "neighborhood": "MILLER PARK",
    "reporting_area": "4887",
    "offense_category": "ALL OTHER",
    "nibrs_offense_code_description": "False Pretenses/Swindle/Confidence Game",
    "nibrs_offense_code": "26A",
    "census_block_2020": "6400.3016",
}

SF_ROW = {
    "row_id": "159286904134",
    "incident_datetime": "2026-08-19T15:10:00.000",
    "report_datetime": "2026-08-19T15:18:00.000",
    "incident_id": "1592869",
    "incident_number": "260476786",
    "cad_number": "262312278",
    "incident_category": "Assault",
    "incident_subcategory": "Simple Assault",
    "incident_description": "Battery",
    "resolution": "Open or Active",
    "intersection": "VALLEJO ST \\ VAN NESS AVE",
    "police_district": "Northern",
    "analysis_neighborhood": "Marina",
    "latitude": "37.79669189453125",
    "longitude": "-122.42359924316406",
    "point": {"type": "Point", "coordinates": [-122.423599243, 37.796691895]},
}

NYC_ROW = {
    "cmplnt_num": "321141941",
    "addr_pct_cd": "123",
    "boro_nm": "STATEN ISLAND",
    "cmplnt_fr_dt": "2026-03-02T00:00:00.000",
    "cmplnt_fr_tm": "00:08:00",
    "crm_atpt_cptd_cd": "COMPLETED",
    "juris_desc": "N.Y. POLICE DEPT",
    "law_cat_cd": "FELONY",
    "loc_of_occur_desc": "FRONT OF",
    "ofns_desc": "FELONY ASSAULT",
    "patrol_boro": "PATROL BORO STATEN ISLAND",
    "pd_desc": "ASSAULT POLICE/PEACE OFFICER",
    "prem_typ_desc": "RESIDENCE-HOUSE",
    "rpt_dt": "2026-03-02T00:00:00.000",
    "latitude": "40.526814",
    "longitude": "-74.177565",
    "lat_lon": {"latitude": "40.526814", "longitude": "-74.177565"},
}


@pytest.fixture
def producer():
    with patch("src.producers.crime_incidents_producer.BaseKafkaProducer"):
        return CrimeIncidentsProducer()


def _within(bbox, lat, lng):
    return (
        bbox["min_lat"] <= lat <= bbox["max_lat"]
        and bbox["min_lng"] <= lng <= bbox["max_lng"]
    )


def test_chicago_crime_row_parses(producer):
    event = producer.parse_socrata_row(CHICAGO_ROW)
    assert event is not None
    assert event.city_id == "chicago"
    assert event.incident_id == "14295750"
    assert event.offense_type == "THEFT"
    assert event.offense_class == "PART1"
    assert event.occurred_date is not None
    assert event.h3_res9


def test_seattle_crime_row_parses(producer):
    event = producer.parse_socrata_row(SEATTLE_ROW)
    assert event is not None
    assert event.city_id == "seattle"
    assert event.incident_id == "12338382264"
    assert event.offense_type == "False Pretenses/Swindle/Confidence Game"
    assert event.offense_class == "PART2"
    assert event.reported_date is not None
    assert event.h3_res9


def test_sf_crime_row_parses(producer):
    event = producer.parse_socrata_row(SF_ROW)
    assert event is not None
    assert event.city_id == "san_francisco"
    assert event.incident_id == "260476786"
    assert event.offense_type == "Assault"
    assert event.offense_class == "PART2"  # Simple Assault / Battery is Part-2
    assert event.source_neighborhood == "Marina"
    assert event.h3_res9


def test_sf_crime_row_coordinates_from_geojson_point(producer):
    row = {k: v for k, v in SF_ROW.items() if k not in ("latitude", "longitude")}
    event = producer.parse_socrata_row(row)
    assert event is not None
    assert event.latitude == pytest.approx(37.796691895)
    assert event.longitude == pytest.approx(-122.423599243)


def test_nyc_crime_row_parses(producer):
    event = producer.parse_socrata_row(NYC_ROW)
    assert event is not None
    assert event.city_id == "nyc"
    assert event.incident_id == "321141941"
    assert event.offense_type == "FELONY ASSAULT"
    assert event.offense_class == "PART1"
    assert event.borough is not None
    assert event.h3_res9


def test_all_crime_fixtures_land_inside_their_metro_bbox(producer):
    for city, row in (
        (CityId.CHICAGO, CHICAGO_ROW),
        (CityId.SEATTLE, SEATTLE_ROW),
        (CityId.SAN_FRANCISCO, SF_ROW),
        (CityId.NYC, NYC_ROW),
    ):
        event = producer.parse_socrata_row(row)
        assert event is not None, city
        assert _within(REGISTRY[city].metro_bbox, event.latitude, event.longitude), city


def test_crime_row_without_coordinates_is_dropped(producer):
    row = {"incident_category": "Burglary", "incident_number": "999", "latitude": "0.0", "longitude": "0.0"}
    assert producer.parse_socrata_row(row) is None


def test_classify_offense_class():
    assert classify_offense_class("THEFT", "$500 AND UNDER") == "PART1"
    assert classify_offense_class("FELONY ASSAULT", None) == "PART1"
    assert classify_offense_class("Assault", "Simple Assault") == "PART2"
    assert classify_offense_class("Assault", "Battery") == "PART2"
    assert classify_offense_class("ALL OTHER", "False Pretenses") == "PART2"


def test_crime_registration_scope_and_job_names():
    registered = {city: FeedType.CRIME in REGISTRY[city].datasets for city in CRIME_CITIES}
    assert registered == {city: True for city in CRIME_CITIES}
    # LA stays out (NIBRS-transition gap) and has no crime feed.
    assert FeedType.CRIME not in REGISTRY[CityId.LOS_ANGELES].datasets
    # NYC job names share the plain feed name; other metros are suffixed.
    assert get_job_name(FeedType.CRIME, CityId.NYC) == "crime"
    assert get_job_name(FeedType.CRIME, CityId.CHICAGO) == "crime_chicago"
    assert get_job_name(FeedType.CRIME, CityId.SAN_FRANCISCO) == "crime_sf"
    assert get_job_name(FeedType.CRIME, CityId.SEATTLE) == "crime_seattle"


def test_nyc_crime_declares_monthly_cadence():
    """G11: NYC's YTD crime set publishes monthly; alarm window is 60d."""
    spec = get_dataset(CityId.NYC, FeedType.CRIME)
    assert spec.extra["expected_cadence_days"] == 30
    assert spec.endpoint.endswith("5uac-w243.json")
    assert spec.topic == "raw.municipal.crime"